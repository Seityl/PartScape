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
