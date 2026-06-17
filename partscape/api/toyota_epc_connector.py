"""
PartScape — Toyota EPC Web Connector + Diagram Downloader

Source: https://toyota.epc-data.com/ (free web-based EPC)

Strategy:
- Query by frame number (JDM chassis number) to get the exact vehicle configuration.
- Parse the resulting HTML to extract model code, engine, transmission, color trim.
- Navigate to parts groups and diagrams to extract OEM part numbers and descriptions.
- DOWNLOAD exploded view diagram images locally into Part Diagram DocType.

Rate limit: 1 req/sec max. Cache everything in Part Catalog / VIN Decode Cache / Part Diagram.
"""

import re
import time
import hashlib
import requests
import frappe
from frappe import _

from partscape.utils.parts_group import ensure_parts_group

EPC_BASE = "https://toyota.epc-data.com"
REQUEST_DELAY = 1.0


def decode_frame_number(frame_no: str, region: str = "general") -> dict:
    """
    Query toyota.epc-data.com with a frame number.
    Returns vehicle configuration dict.

    Args:
        frame_no: e.g. 'GXE10-0088644' or 'JTEHT05J802063701'
        region: 'japan', 'general', 'europe', 'usa'
    """
    session = requests.Session()
    search_url = f"{EPC_BASE}/{region}/"
    try:
        resp = session.get(
            f"{search_url}?frame={frame_no}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0)"},
            timeout=20,
        )
        resp.raise_for_status()
        return _parse_frame_result(resp.text, frame_no)
    except Exception as e:
        frappe.log_error(title="Toyota EPC Frame Decode Error", message=str(e))
        return {}


def _parse_frame_result(html: str, frame_no: str) -> dict:
    """
    Parse the vehicle info page HTML.
    This is a stub — actual selectors depend on the site's HTML structure.
    """
    result = {
        "frame_no": frame_no,
        "source": "toyota.epc-data.com",
        "make": "Toyota",
        "model": None,
        "model_code": None,
        "engine_code": None,
        "transmission": None,
        "trim_code": None,
        "color_code": None,
        "production_date": None,
    }

    model_match = re.search(r"Model[:\s]+([^<(]+)\s*\(([^)]+)\)", html, re.I)
    if model_match:
        result["model"] = model_match.group(1).strip()
        result["model_code"] = model_match.group(2).strip()

    engine_match = re.search(r"Engine[:\s]+([A-Z0-9\-]+)", html, re.I)
    if engine_match:
        result["engine_code"] = engine_match.group(1).strip()

    trans_match = re.search(r"Transmission[:\s]+([^<\n]+)", html, re.I)
    if trans_match:
        result["transmission"] = trans_match.group(1).strip()

    return result


# ---------------------------------------------------------------------------
# Parts + Diagram Scraping
# ---------------------------------------------------------------------------

def get_parts_for_model(model_code: str, group: str = None, region: str = "general") -> list:
    """
    Fetch parts list for a given Toyota model code.
    If group is provided, filter to that parts group (e.g., 'brake', 'engine').
    Returns list of dicts with part_number, description, diagram_ref.
    """
    time.sleep(REQUEST_DELAY)
    parts = []

    url = f"{EPC_BASE}/{region}/model/{model_code}/"
    if group:
        url += f"group/{group}/"

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0)"},
            timeout=20,
        )
        resp.raise_for_status()
        parts = _parse_parts_list(resp.text)
    except Exception as e:
        frappe.log_error(title="Toyota EPC Parts Fetch Error", message=str(e))

    return parts


def _parse_parts_list(html: str) -> list:
    """
    Parse parts list HTML. Stub to be refined with real selectors.
    """
    parts = []
    rows = re.findall(
        r"<tr[^>]*>.*?<td[^>]*>([0-9\-]+)</td>\s*<td[^>]*>([^<]+)</td>.*?</tr>",
        html,
        re.S | re.I,
    )
    for part_no, desc in rows:
        parts.append({
            "part_number": part_no.strip(),
            "description": desc.strip(),
            "source": "toyota.epc-data.com",
        })
    return parts


def get_diagrams_for_model(model_code: str, group: str = None, region: str = "general") -> list:
    """
    Fetch diagram URLs for a given Toyota model code + parts group.
    Returns list of dicts: {diagram_url, diagram_page, parts_group, callout_map}
    """
    time.sleep(REQUEST_DELAY)
    diagrams = []

    url = f"{EPC_BASE}/{region}/model/{model_code}/"
    if group:
        url += f"group/{group}/"

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0)"},
            timeout=20,
        )
        resp.raise_for_status()
        diagrams = _parse_diagram_list(resp.text, model_code, group)
    except Exception as e:
        frappe.log_error(title="Toyota EPC Diagram Fetch Error", message=str(e))

    return diagrams


def _parse_diagram_list(html: str, model_code: str, group: str = None) -> list:
    """
    Parse diagram list HTML to extract image URLs and callout mappings.
    Stub — to be refined with real selectors after live inspection.
    """
    diagrams = []

    # Typical pattern: diagram images have URLs like /img/diagram/12345.png
    img_pattern = re.compile(
        r'<img[^>]+src=["\']([^"\']+diagram[^"\']+\.(?:png|jpg|jpeg|gif))["\'][^>]*>',
        re.S | re.I,
    )

    for match in img_pattern.finditer(html):
        img_url = match.group(1)
        if not img_url.startswith("http"):
            img_url = f"{EPC_BASE}{img_url}"

        # Try to extract diagram page / group from surrounding context
        # Look for nearby headings or caption text
        surrounding = html[max(0, match.start() - 500):match.end() + 500]
        page_match = re.search(r"[Pp]age\s+([A-Z0-9\-]+)", surrounding)
        group_match = re.search(r"[Gg]roup\s+([0-9]+)", surrounding)

        diagrams.append({
            "diagram_url": img_url,
            "diagram_page": page_match.group(1) if page_match else "",
            "parts_group": group or (group_match.group(1) if group_match else ""),
            "callout_map": _extract_callout_map(surrounding),
        })

    return diagrams


def _extract_callout_map(html_fragment: str) -> dict:
    """
    Extract callout_number → part_number mapping from HTML near a diagram.
    Returns dict: {callout_number: part_number}
    """
    callout_map = {}
    # Typical table pattern near diagram: callout number + part number
    rows = re.findall(
        r"<tr[^>]*>.*?<td[^>]*>([0-9]+)</td>\s*<td[^>]*>([0-9\-]+)</td>.*?</tr>",
        html_fragment,
        re.S | re.I,
    )
    for callout, part_no in rows:
        callout_map[callout.strip()] = part_no.strip()
    return callout_map


# ---------------------------------------------------------------------------
# Download & Persist Diagrams
# ---------------------------------------------------------------------------

def download_diagram(image_url: str, session=None) -> bytes:
    """
    Download a diagram image. Returns raw bytes or None on failure.
    """
    time.sleep(REQUEST_DELAY)
    s = session or requests.Session()
    try:
        resp = s.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0)"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        frappe.log_error(title="Diagram Download Error", message=f"{image_url}: {e}")
        return None


def save_diagram_to_doc(
    image_bytes: bytes,
    vehicle_model: str,
    parts_group: str,
    diagram_page: str,
    source_url: str,
    source_brand: str = "Toyota",
) -> str:
    """
    Save diagram image bytes to a Part Diagram DocType record.
    Returns the Part Diagram doc name.
    """
    if not image_bytes:
        return None

    parts_group = ensure_parts_group(parts_group)

    # Check for duplicate by hash
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

    # Save image as attachment
    file_name = f"{img_hash}.png"
    from frappe.utils.file_manager import save_file
    save_file(
        fname=file_name,
        content=image_bytes,
        dt="Part Diagram",
        dn=doc.name,
        is_private=1,
    )

    return doc.name


def link_part_to_diagram(part_catalog_name: str, diagram_name: str, callout_number: str):
    """
    Add a Part Catalog Diagram child table row linking a part to a diagram.
    """
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


# ---------------------------------------------------------------------------
# Admin Seeding Utility
# ---------------------------------------------------------------------------

@frappe.whitelist()
def seed_catalog_from_epc(model_code: str, region: str = "general", download_diagrams: bool = True):
    """
    Admin utility: fetch all parts + diagrams for a Toyota model code and create records.
    """
    parts = get_parts_for_model(model_code, region=region)
    created = 0
    diagrams_created = 0
    links_created = 0

    make_doc = frappe.db.get_value("Vehicle Make", {"make_name": "Toyota"}, "name")
    if not make_doc:
        make_doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": "Toyota"}).insert().name

    brand_doc = frappe.db.get_value("Brand", {"brand": "Toyota"}, "name")
    if not brand_doc:
        brand_doc = frappe.get_doc({"doctype": "Brand", "brand": "Toyota"}).insert().name

    # Resolve vehicle model from model_code
    model_doc = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")

    for p in parts:
        if frappe.db.exists("Part Catalog", {"brand": brand_doc, "part_number": p["part_number"]}):
            continue
        doc = frappe.get_doc({
            "doctype": "Part Catalog",
            "brand": brand_doc,
            "part_number": p["part_number"],
            "part_name": p["description"][:140],
            "description": p["description"],
            "oem_make": make_doc,
            "is_oem": 1,
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        created += 1

    # Download diagrams if requested
    if download_diagrams and model_doc:
        diagram_infos = get_diagrams_for_model(model_code, region=region)
        session = requests.Session()
        for dinfo in diagram_infos:
            img_bytes = download_diagram(dinfo["diagram_url"], session=session)
            if img_bytes:
                diagram_name = save_diagram_to_doc(
                    image_bytes=img_bytes,
                    vehicle_model=model_doc,
                    parts_group=dinfo["parts_group"],
                    diagram_page=dinfo["diagram_page"],
                    source_url=dinfo["diagram_url"],
                    source_brand="Toyota",
                )
                diagrams_created += 1

                # Link parts on this diagram to the diagram record
                for callout, part_no in dinfo.get("callout_map", {}).items():
                    pc_name = frappe.db.get_value(
                        "Part Catalog",
                        {"brand": "Toyota", "part_number": part_no},
                        "name",
                    )
                    if pc_name and diagram_name:
                        link_part_to_diagram(pc_name, diagram_name, callout)
                        links_created += 1

    frappe.db.commit()
    return {
        "created": created,
        "diagrams_created": diagrams_created,
        "links_created": links_created,
        "scanned": len(parts),
    }
