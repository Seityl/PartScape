"""
PartScape — Headless Browser EPC Scraper (Playwright)

Uses a real Chromium browser to navigate EPC sites that block simple HTTP requests.
Targets:
- toyota.epc-data.com
- nissan.epc-data.com (if available)
- partsouq.com
- 7zap.com

NOTE: These sites may have Terms of Service that prohibit scraping.
This tool is provided for educational/data-import purposes only.
Use responsibly and respect rate limits.
"""

import time
import re
import frappe
from frappe import _

# Lazy-import playwright to avoid import errors if not installed
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None
    PlaywrightTimeout = Exception


def _get_playwright():
    if sync_playwright is None:
        frappe.throw(_("Playwright is not installed. Run: pip install playwright && playwright install chromium"))
    return sync_playwright()


def scrape_toyota_epc_frame(frame_no: str, region: str = "general") -> dict:
    """
    Use Playwright to query toyota.epc-data.com by frame number.
    Returns vehicle config dict with parts list.
    """
    if not frame_no:
        return {}

    result = {
        "frame_no": frame_no,
        "make": "Toyota",
        "model": None,
        "model_code": None,
        "engine_code": None,
        "transmission": None,
        "parts": [],
    }

    try:
        with _get_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            # Navigate to search page
            search_url = f"https://toyota.epc-data.com/{region}/"
            page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Fill frame number and submit
            page.fill("input[name='frame']", frame_no)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Check for Cloudflare/interstitial
            if "Just a moment" in page.content() or "challenge" in page.content():
                browser.close()
                frappe.log_error(title="Toyota EPC Blocked", message="Cloudflare challenge detected")
                return result

            # Parse vehicle info page
            html = page.content()

            # Extract model info
            model_match = re.search(r"Model[\s:]+([^<(]+)\s*\(([^)]+)\)", html, re.I)
            if model_match:
                result["model"] = model_match.group(1).strip()
                result["model_code"] = model_match.group(2).strip()

            engine_match = re.search(r"Engine[\s:]+([A-Z0-9\-]+)", html, re.I)
            if engine_match:
                result["engine_code"] = engine_match.group(1).strip()

            trans_match = re.search(r"Transmission[\s:]+([^<\n]+)", html, re.I)
            if trans_match:
                result["transmission"] = trans_match.group(1).strip()

            # Extract parts from tables
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
            result["parts"] = parts

            browser.close()

    except PlaywrightTimeout:
        frappe.log_error(title="Toyota EPC Timeout", message=f"Frame {frame_no}: page load timed out")
    except Exception as e:
        frappe.log_error(title="Toyota EPC Scraper Error", message=f"Frame {frame_no}: {frappe.get_traceback()}")

    return result


@frappe.whitelist()
def test_epc_scraper(frame_no: str = "KDH201-0149586"):
    """Whitelist wrapper to test the EPC scraper from the browser console."""
    result = scrape_toyota_epc_frame(frame_no)
    return {
        "status": "ok" if result.get("model_code") else "no_data",
        "data": result,
    }


@frappe.whitelist()
def seed_from_epc_playwright(frame_no: str, region: str = "general"):
    """
    Admin utility: scrape a Toyota frame number and create real Part Catalog records.
    """
    data = scrape_toyota_epc_frame(frame_no, region)
    if not data.get("model_code"):
        return {"status": "error", "message": "Could not decode frame number"}

    make_doc = frappe.db.get_value("Vehicle Make", {"make_name": "Toyota"}, "name")
    if not make_doc:
        make_doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": "Toyota"}).insert().name

    brand_doc = frappe.db.get_value("Brand", {"brand": "Toyota"}, "name")
    if not brand_doc:
        brand_doc = frappe.get_doc({"doctype": "Brand", "brand": "Toyota"}).insert().name

    # Create/update vehicle model
    model_doc = frappe.db.get_value("Vehicle Model", {"model_code": data["model_code"]}, "name")
    if not model_doc:
        model_doc = frappe.get_doc({
            "doctype": "Vehicle Model",
            "model_name": data["model"],
            "make": make_doc,
            "model_code": data["model_code"],
            "steering_position": "RHD",
            "primary_market": "JDM",
        }).insert().name

    # Create parts
    parts_created = 0
    for p in data.get("parts", []):
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
        parts_created += 1

    frappe.db.commit()
    return {
        "status": "ok",
        "frame_no": frame_no,
        "model": data["model"],
        "model_code": data["model_code"],
        "parts_created": parts_created,
    }
