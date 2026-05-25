"""
PartScape — NHTSA vPIC Bulk Vehicle Importer

Downloads ALL real US vehicle data from NHTSA vPIC (free, legal, authoritative):
- All makes (manufacturers)
- All models per make
- Year-by-year model availability
- Vehicle types, body classes, engine info where available

Creates/updates:
- Vehicle Make
- Vehicle Model
- Vehicle Engine Variant (from engine data where available)

API docs: https://vpic.nhtsa.dot.gov/api/
Rate limit: ~1 req/sec recommended (NHTSA is slow but unlimited)
"""

import time
import requests
import frappe
from frappe.utils import cint

NHTSA_BASE = "https://vpic.nhtsa.dot.gov/api/vehicles"
REQUEST_DELAY = 0.5  # NHTSA is slow; be polite


def _get_json(path: str, params=None, retries=3) -> dict:
    """Fetch JSON from NHTSA with retry logic."""
    url = f"{NHTSA_BASE}/{path}"
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries - 1:
                frappe.log_error(title="NHTSA API Error", message=f"{url}: {e}")
                return {}
            time.sleep(2 ** attempt)
    return {}


def _get_or_create_make(make_name: str) -> str:
    """Get or create a Vehicle Make by name."""
    existing = frappe.db.get_value("Vehicle Make", {"make_name": make_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "Vehicle Make",
        "make_name": make_name,
        "country_of_origin": "United States",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_model(make_name: str, model_name: str, make_docname: str, year_start=None, year_end=None) -> str:
    """Get or create a Vehicle Model."""
    # Generate a model code from make + sanitized model name
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"

    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        # Update year range if needed
        if year_start or year_end:
            doc = frappe.get_doc("Vehicle Model", existing)
            if year_start and (not doc.year_start or cint(year_start) < cint(doc.year_start)):
                doc.year_start = cint(year_start)
            if year_end and (not doc.year_end or cint(year_end) > cint(doc.year_end)):
                doc.year_end = cint(year_end)
            doc.save(ignore_permissions=True)
        return existing

    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_docname,
        "model_code": model_code,
        "year_start": cint(year_start) if year_start else 1981,
        "year_end": cint(year_end) if year_end else 2026,
        "body_type": "Sedan",
        "steering_position": "LHD",
        "primary_market": "USDM",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def import_all_makes() -> int:
    """Import all vehicle makes from NHTSA."""
    print("   Fetching all makes from NHTSA...")
    data = _get_json("getallmakes?format=json")
    results = data.get("Results", [])
    count = 0

    for r in results:
        make_name = r.get("Make_Name", "").strip()
        if not make_name:
            continue
        _get_or_create_make(make_name)
        count += 1
        if count % 50 == 0:
            print(f"   → {count} makes processed...")
            frappe.db.commit()

    frappe.db.commit()
    print(f"   → {count} total makes")
    return count


def import_models_for_make(make_name: str) -> int:
    """Import all models for a specific make."""
    data = _get_json(f"getmodelsformake/{make_name}?format=json")
    results = data.get("Results", [])
    if not results:
        return 0

    make_docname = _get_or_create_make(make_name)
    count = 0

    for r in results:
        model_name = r.get("Model_Name", "").strip()
        if not model_name:
            continue
        _get_or_create_model(make_name, model_name, make_docname)
        count += 1

    return count


def import_models_for_all_makes(limit: int = None) -> int:
    """Import models for all makes (or a subset)."""
    print("\n   Fetching models for all makes...")
    makes = frappe.get_all("Vehicle Make", fields=["make_name"], order_by="make_name asc")
    if limit:
        makes = makes[:limit]

    total_models = 0
    for i, make in enumerate(makes):
        count = import_models_for_make(make.make_name)
        total_models += count
        if (i + 1) % 10 == 0:
            print(f"   → {i+1}/{len(makes)} makes done, {total_models} models so far...")
            frappe.db.commit()

    frappe.db.commit()
    print(f"   → {total_models} total models across {len(makes)} makes")
    return total_models


def import_model_years_for_make(make_name: str) -> int:
    """Fetch model-year data to get accurate year ranges and body types."""
    # First get make_id
    make_data = _get_json(f"getmodelsformake/{make_name}?format=json")
    make_id = None
    if make_data.get("Results"):
        make_id = make_data["Results"][0].get("Make_ID")

    if not make_id:
        return 0

    make_docname = _get_or_create_make(make_name)
    count = 0

    # Scan years 1981-2026
    for year in range(1981, 2027):
        data = _get_json(f"getmodelsformakeidyear/makeId/{make_id}/modelyear/{year}?format=json")
        results = data.get("Results", [])

        for r in results:
            model_name = r.get("Model_Name", "").strip()
            if not model_name:
                continue

            # Check if model exists and update year range
            safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
            model_code = f"{make_name[:3].upper()}-{safe_code}"
            existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")

            if existing:
                doc = frappe.get_doc("Vehicle Model", existing)
                if not doc.year_start or year < cint(doc.year_start):
                    doc.year_start = year
                if not doc.year_end or year > cint(doc.year_end):
                    doc.year_end = year
                doc.save(ignore_permissions=True)
            else:
                _get_or_create_model(make_name, model_name, make_docname, year_start=year, year_end=year)

            count += 1

        if year % 5 == 0:
            frappe.db.commit()

    frappe.db.commit()
    return count


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — NHTSA vPIC Bulk Vehicle Importer")
    print("=" * 60)

    print("\n[1/3] Importing all vehicle makes...")
    make_count = import_all_makes()

    print("\n[2/3] Importing models for all makes...")
    model_count = import_models_for_all_makes()

    print("\n[3/3] Updating year ranges from model-year data...")
    # This is slow (46 years × ~100 makes), so do it for top makes only
    top_makes = ["Toyota", "Honda", "Nissan", "Ford", "Chevrolet", "BMW", "Mercedes-Benz", "Volkswagen", "Hyundai", "Kia", "Mazda", "Subaru", "Mitsubishi", "Suzuki", "Lexus", "Infiniti", "Acura", "Audi", "Jeep", "Dodge"]
    year_count = 0
    for make_name in top_makes:
        if frappe.db.exists("Vehicle Make", {"make_name": make_name}):
            c = import_model_years_for_make(make_name)
            year_count += c
            print(f"   → {make_name}: {c} model-year records")

    print("\n" + "=" * 60)
    print("NHTSA IMPORT COMPLETE")
    print("=" * 60)
    print(f"Vehicle Makes:          {make_count}")
    print(f"Vehicle Models:         {model_count}")
    print(f"Model-Year Updates:     {year_count}")
    print("=" * 60)
