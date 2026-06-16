"""
PartScape — Partsouq Scraper Stub

ETHICAL USE ONLY:
- Respect robots.txt
- Rate limit to <= 1 req/sec
- Cache pages for 30+ days
- Prefer reaching out to Partsouq for affiliate/data partnership before scraping.

Partsouq URLs use an encoded 'ssd' parameter. This is a base64-like state blob.
Reverse engineering it fully requires deobfuscating their frontend JS.
Instead, we use their public VIN lookup endpoint patterns as a reference
and recommend manual seeding or partnership for production.
"""

import re
import time
import frappe
from frappe import _

PARTSOUQ_BASE = "https://partsouq.com"
REQUEST_DELAY = 1.0  # seconds between requests


def get_partsouq_vin_url(vin: str, make: str = "Toyota") -> str:
    """
    Build a Partsouq VIN lookup URL.
    The 'ssd' parameter is opaque; this is a best-effort template.
    In practice, you need to capture the SSD from their UI session.
    """
    make_slug = make.lower().replace(" ", "-")
    return f"{PARTSOUQ_BASE}/en/catalog/genuine/vehicle?c={make}&vid=0&q={vin}"


def parse_partsouq_diagram_page(html: str) -> list:
    """
    Parse a Partsouq exploded diagram page HTML for part numbers and diagram image.
    Returns list of dicts: [{brand, part_number, description, diagram_url, price_usd}]
    """
    parts = []
    if not html:
        return parts

    # Extract diagram image URL
    diagram_url = None
    img_match = re.search(
        r'<img[^>]+src=["\']([^"\']+(?:diagram|illustration|image)[^"\']*\.(?:png|jpg|jpeg|gif))["\']',
        html, re.S | re.I
    )
    if img_match:
        diagram_url = img_match.group(1)
        if not diagram_url.startswith("http"):
            diagram_url = f"{PARTSOUQ_BASE}{diagram_url}"

    # Very basic regex fallback; real implementation needs BeautifulSoup
    pattern = re.compile(r"([0-9]{5}\-[0-9]{5})\s+.*?([0-9]+\.[0-9]{2})")
    for m in pattern.finditer(html):
        parts.append({
            "brand": "Toyota",  # Default; Partsouq page context reveals actual make
            "part_number": m.group(1),
            "price_usd": float(m.group(2)),
            "diagram_url": diagram_url,
            "source": "partsouq",
        })
    return parts


def respectful_get(url: str, session=None) -> str:
    """HTTP GET with polite delay."""
    import requests
    time.sleep(REQUEST_DELAY)
    s = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PartScape-Bot/1.0; +https://seityl.com/bot)"
    }
    try:
        r = s.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        frappe.log_error(title="Partsouq Scraping Error", message=str(e))
        return ""


@frappe.whitelist()
def seed_catalog_from_partsouq(vin: str, make: str = "Toyota"):
    """
    Whitelisted stub: attempt to fetch genuine catalog entries from Partsouq.
    WARNING: This may break if Partsouq changes their layout or blocks bots.
    """
    frappe.msgprint(
        _(
            "Partsouq scraping is not recommended for production. "
            "Consider using {make}.epc-data.com (free web EPC) or partnering with Partsouq."
        ).format(make=make),
        indicator="orange",
    )
    return {"status": "not_implemented", "message": f"Use {make}.epc-data.com connector instead."}
