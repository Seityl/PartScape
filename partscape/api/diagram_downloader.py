"""
PartScape — Generic Diagram Downloader

Utility for downloading exploded view diagram images from any EPC source
and persisting them as Part Diagram records linked to Part Catalog entries.

Supports:
- 7zap.com (multibrand)
- realoem.com (BMW + German brands)
- toyota.epc-data.com / nissan.epc-data.com (JDM brands)
- partsouq.com / amayama.com / megazip.net (genuine parts portals)
- Any source that serves diagram images via HTTP with predictable URLs

Copyright Note:
Exploded view diagrams are typically copyrighted by vehicle manufacturers.
This downloader is intended for internal business use by a licensed auto
repair/parts shop. It does not redistribute diagrams publicly.
"""

import hashlib
import time
import requests
import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from partscape.utils.parts_group import ensure_parts_group

DEFAULT_DELAY = 1.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def download_and_save_diagram(
    image_url: str,
    vehicle_model: str,
    parts_group: str = "",
    diagram_page: str = "",
    source_brand: str = "",
    callout_map: dict = None,
) -> dict:
    """
    Download a diagram image from any URL and save it as a Part Diagram record.
    Optionally link parts found on the diagram to the Part Diagram.

    Args:
        image_url: Direct URL to the diagram image (png/jpg/gif)
        vehicle_model: Link name of Vehicle Model doc
        parts_group: e.g. "Brake System"
        diagram_page: e.g. "B-15"
        source_brand: e.g. "Toyota", "7zap", "RealOEM"
        callout_map: Dict {callout_number: part_number} for linking parts

    Returns:
        {diagram_name, status, links_created}
    """
    if not image_url or not vehicle_model:
        return {"error": "image_url and vehicle_model are required"}

    # Download image
    img_bytes = _fetch_image(image_url)
    if not img_bytes:
        return {"error": f"Failed to download image from {image_url}"}

    # Save Part Diagram record
    diagram_name = _save_diagram_doc(
        image_bytes=img_bytes,
        vehicle_model=vehicle_model,
        parts_group=parts_group,
        diagram_page=diagram_page,
        source_url=image_url,
        source_brand=source_brand,
    )
    if not diagram_name:
        return {"error": "Failed to create Part Diagram record"}

    # Link parts to diagram
    links = 0
    if callout_map:
        for callout, part_identifier in callout_map.items():
            # part_identifier could be "Toyota 04465-26421" or just "04465-26421"
            # Try to find matching Part Catalog entry
            pc_name = _resolve_part_catalog(part_identifier, source_brand)
            if pc_name:
                _link_part_to_diagram(pc_name, diagram_name, callout)
                links += 1

    return {
        "diagram_name": diagram_name,
        "status": "created",
        "links_created": links,
    }


@frappe.whitelist()
def bulk_download_diagrams(diagram_list: list) -> dict:
    """
    Bulk download multiple diagrams.

    Args:
        diagram_list: List of dicts, each with keys:
            image_url, vehicle_model, parts_group, diagram_page, source_brand, callout_map

    Returns:
        {total, created, failed, total_links}
    """
    total = len(diagram_list)
    created = 0
    failed = 0
    total_links = 0

    for item in diagram_list:
        try:
            result = download_and_save_diagram(**item)
            if result.get("diagram_name"):
                created += 1
                total_links += result.get("links_created", 0)
            else:
                failed += 1
        except Exception as e:
            frappe.log_error(title="Bulk Diagram Download Error", message=str(e))
            failed += 1

    return {
        "total": total,
        "created": created,
        "failed": failed,
        "total_links": total_links,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_image(url: str, session=None) -> bytes:
    """Download image bytes with polite delay."""
    time.sleep(DEFAULT_DELAY)
    s = session or requests.Session()
    try:
        resp = s.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0)"},
            timeout=30,
        )
        resp.raise_for_status()
        # Validate it's actually an image
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            # Some sites return HTML error pages with 200 status
            return None
        return resp.content
    except Exception as e:
        frappe.log_error(title="Image Fetch Error", message=f"{url}: {e}")
        return None


def _save_diagram_doc(
    image_bytes: bytes,
    vehicle_model: str,
    parts_group: str,
    diagram_page: str,
    source_url: str,
    source_brand: str,
) -> str:
    """Create Part Diagram doc and attach image. Returns doc name."""
    parts_group = ensure_parts_group(parts_group)
    img_hash = hashlib.sha256(image_bytes).hexdigest()[:16]

    existing = frappe.db.get_value("Part Diagram", {"diagram_number": img_hash}, "name")
    if existing:
        return existing

    doc = frappe.get_doc({
        "doctype": "Part Diagram",
        "vehicle_model": vehicle_model,
        "parts_group": parts_group,
        "diagram_page": diagram_page,
        "diagram_number": img_hash,
        "source_url": source_url,
        "source_brand": source_brand,
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True)

    # Determine file extension from Content-Type or URL
    ext = _guess_extension(source_url)
    file_name = f"diagram_{img_hash}.{ext}"

    save_file(
        fname=file_name,
        content=image_bytes,
        dt="Part Diagram",
        dn=doc.name,
        is_private=1,
    )

    return doc.name


def _resolve_part_catalog(part_identifier: str, source_brand: str = "") -> str:
    """
    Find a Part Catalog doc name from an identifier string.
    part_identifier could be:
        - "Toyota 04465-26421"
        - "04465-26421" (requires source_brand)
        - "Bosch 0 986 494 046"
    """
    part_identifier = part_identifier.strip()

    # Try "Brand PartNumber" format
    parts = part_identifier.split(None, 1)
    if len(parts) == 2:
        brand, part_number = parts
        pc = frappe.db.get_value(
            "Part Catalog",
            {"brand": brand.strip(), "part_number": part_number.strip()},
            "name",
        )
        if pc:
            return pc

    # Fallback: use source_brand + part_identifier as part_number
    if source_brand:
        pc = frappe.db.get_value(
            "Part Catalog",
            {"brand": source_brand.strip(), "part_number": part_identifier},
            "name",
        )
        if pc:
            return pc

    # Last resort: search by part_number only across all brands
    pc = frappe.db.get_value("Part Catalog", {"part_number": part_identifier}, "name")
    return pc


def _link_part_to_diagram(part_catalog_name: str, diagram_name: str, callout_number: str):
    """Add a child table row on Part Catalog linking to a diagram."""
    pc = frappe.get_doc("Part Catalog", part_catalog_name)
    existing = [d for d in pc.diagrams if d.part_diagram == diagram_name]
    if existing:
        return

    pc.append("diagrams", {
        "part_diagram": diagram_name,
        "callout_number": callout_number,
        "parts_group": frappe.db.get_value("Part Diagram", diagram_name, "parts_group"),
    })
    pc.save(ignore_permissions=True)


def _guess_extension(url: str) -> str:
    """Guess file extension from URL or default to png."""
    url_lower = url.lower()
    for ext in ["png", "jpg", "jpeg", "gif", "webp", "bmp"]:
        if f".{ext}" in url_lower:
            return ext
    return "png"
