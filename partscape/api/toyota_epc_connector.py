"""
PartScape — Toyota EPC Web Connector

Source: https://toyota.epc-data.com/ (free web-based EPC)

Strategy:
- Query by frame number (JDM chassis number) to get the exact vehicle configuration.
- Parse the resulting HTML to extract model code, engine, transmission, color trim.
- Navigate to parts groups to extract OEM part numbers and descriptions.

Rate limit: 1 req/sec max. Cache everything in Part Catalog / VIN Decode Cache.
"""

import re
import time
import requests
import frappe
from frappe import _

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
# Parts Scraping
# ---------------------------------------------------------------------------

def get_parts_for_model(model_code: str, group: str = None, region: str = "general") -> list:
    """
    Fetch parts list for a given Toyota model code.
    If group is provided, filter to that parts group (e.g., 'brake', 'engine').
    Returns list of dicts with part_number, description.
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


# ---------------------------------------------------------------------------
# Admin Seeding Utility
# ---------------------------------------------------------------------------

@frappe.whitelist()
def seed_catalog_from_epc(model_code: str, region: str = "general"):
    """
    Admin utility: fetch all parts for a Toyota model code and create records.
    """
    parts = get_parts_for_model(model_code, region=region)
    created = 0

    make_doc = frappe.db.get_value("Vehicle Make", {"make_name": "Toyota"}, "name")
    if not make_doc:
        make_doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": "Toyota"}).insert().name

    brand_doc = frappe.db.get_value("Brand", {"brand": "Toyota"}, "name")
    if not brand_doc:
        brand_doc = frappe.get_doc({"doctype": "Brand", "brand": "Toyota"}).insert().name

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

    frappe.db.commit()
    return {
        "created": created,
        "scanned": len(parts),
    }
