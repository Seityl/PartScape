"""
PartScape — n8barr Automotive Model-Year Data Importer

Source: https://github.com/n8barr/automotive-model-year-data
License: CC-BY (requires attribution)
Format: MySQL dump (schema.sql + data.sql)
Records: ~7,267 model-years
Coverage: 1909–2026, US-market vehicles

Imports into:
- Vehicle Make
- Vehicle Model
"""

import re
import frappe
from frappe.utils import cint

DATA_SQL_PATH = frappe.get_app_path("partscape", "data_imports", "n8barr_data.sql")

BODY_STYLE_MAP = {
    "SUV": "SUV",
    "Sedan": "Sedan",
    "Pickup": "Pickup",
    "Van/Minivan": "Van",
    "Coupe": "Coupe",
    "Hatchback": "Hatch",
    "Convertible": "Convertible",
    "Wagon": "Wagon",
}


def _parse_sql_insert(sql_text: str):
    """Extract (year, make, model) tuples from INSERT statement."""
    # Find the VALUES(...) section
    match = re.search(r"VALUES\s+(.+);?\s*$", sql_text, re.DOTALL)
    if not match:
        return []

    values_text = match.group(1)
    # Each row is (year, 'make', 'model'),
    # Handle potential multi-line and trailing comma
    pattern = r"\(\s*(\d{4})\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)"
    rows = re.findall(pattern, values_text)
    return [(int(y), m.strip(), mo.strip()) for y, m, mo in rows]


def _get_or_create_make(make_name: str) -> str:
    existing = frappe.db.get_value("Vehicle Make", {"make_name": make_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "Vehicle Make",
        "make_name": make_name,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_model(make_name: str, model_name: str, make_docname: str,
                          year_start=None, year_end=None, body_type="Sedan") -> str:
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"

    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        doc = frappe.get_doc("Vehicle Model", existing)
        if year_start and (not doc.year_start or cint(year_start) < cint(doc.year_start)):
            doc.year_start = cint(year_start)
        if year_end and (not doc.year_end or cint(year_end) > cint(doc.year_end)):
            doc.year_end = cint(year_end)
        if body_type and body_type != "Sedan" and doc.body_type == "Sedan":
            doc.body_type = body_type
        doc.save(ignore_permissions=True)
        return existing

    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_docname,
        "model_code": model_code,
        "year_start": cint(year_start) if year_start else None,
        "year_end": cint(year_end) if year_end else None,
        "body_type": body_type,
        "steering_position": "LHD",
        "primary_market": "USDM",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — n8barr Automotive Model-Year Importer")
    print("Source: github.com/n8barr/automotive-model-year-data")
    print("=" * 60)

    with open(DATA_SQL_PATH, "r", encoding="utf-8") as f:
        sql_text = f.read()

    rows = _parse_sql_insert(sql_text)
    print(f"\nParsed {len(rows)} model-year records from SQL dump")

    # Group by make+model to get year ranges
    model_map = {}  # (make, model) -> {"years": [], "make_docname": None}

    for year, make, model in rows:
        key = (make, model)
        if key not in model_map:
            model_map[key] = {"years": [], "make_docname": None}
        model_map[key]["years"].append(year)

    print(f"Consolidated into {len(model_map)} unique make-model combinations")

    # Create makes first
    unique_makes = set(make for make, _ in model_map.keys())
    print(f"\nCreating {len(unique_makes)} Vehicle Makes...")
    make_count = 0
    for make_name in sorted(unique_makes):
        docname = _get_or_create_make(make_name)
        for key in model_map:
            if key[0] == make_name:
                model_map[key]["make_docname"] = docname
        make_count += 1
        if make_count % 50 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"  → {make_count} makes created/updated")

    # Create/update models with year ranges
    print(f"\nCreating {len(model_map)} Vehicle Models...")
    model_count = 0
    for (make, model), info in model_map.items():
        years = sorted(info["years"])
        year_start = years[0]
        year_end = years[-1]
        _get_or_create_model(make, model, info["make_docname"],
                             year_start=year_start, year_end=year_end)
        model_count += 1
        if model_count % 100 == 0:
            print(f"  → {model_count}/{len(model_map)} models...")
            frappe.db.commit()

    frappe.db.commit()
    print(f"  → {model_count} models created/updated")

    print("\n" + "=" * 60)
    print("n8barr IMPORT COMPLETE")
    print("=" * 60)
