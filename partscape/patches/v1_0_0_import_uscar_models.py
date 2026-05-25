"""
PartScape — US Car Models Data Importer

Source: https://github.com/abhionlyone/us-car-models-data
License: Free (public domain, no explicit license)
Format: CSV files per year (1992–2024)
Records: ~11,500 model-year records
Coverage: 1992–2024, US-market vehicles with body styles

Imports into:
- Vehicle Make
- Vehicle Model (with body type and year range)
"""

import csv
import json
import os
import re

import frappe
from frappe.utils import cint

DATA_DIR = frappe.get_app_path("partscape", "data_imports")

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


def _parse_body_styles(raw: str) -> str:
    """Parse body_styles JSON array and map to PartScape body_type."""
    if not raw or raw.strip() == '""':
        return "Sedan"

    # Clean up: remove outer quotes, unescape inner quotes
    cleaned = raw.strip().strip('"')
    cleaned = cleaned.replace('""', '"')

    try:
        styles = json.loads(cleaned)
        if isinstance(styles, list) and styles:
            first = styles[0]
            return BODY_STYLE_MAP.get(first, "Sedan")
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: try regex
    match = re.search(r'"([^"]+)"', raw)
    if match:
        return BODY_STYLE_MAP.get(match.group(1), "Sedan")

    return "Sedan"


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
                          year=None, body_type="Sedan") -> str:
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"

    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        doc = frappe.get_doc("Vehicle Model", existing)
        if year:
            y = cint(year)
            if not doc.year_start or y < cint(doc.year_start):
                doc.year_start = y
            if not doc.year_end or y > cint(doc.year_end):
                doc.year_end = y
        if body_type != "Sedan" and doc.body_type == "Sedan":
            doc.body_type = body_type
        doc.save(ignore_permissions=True)
        return existing

    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_docname,
        "model_code": model_code,
        "year_start": cint(year) if year else None,
        "year_end": cint(year) if year else None,
        "body_type": body_type,
        "steering_position": "LHD",
        "primary_market": "USDM",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — US Car Models Data Importer")
    print("Source: github.com/abhionlyone/us-car-models-data")
    print("=" * 60)

    # Find all uscar_*.csv files
    csv_files = sorted([
        f for f in os.listdir(DATA_DIR)
        if f.startswith("uscar_") and f.endswith(".csv")
    ])
    print(f"\nFound {len(csv_files)} CSV files: {', '.join(csv_files)}")

    # Collect all records
    all_records = []
    for csv_file in csv_files:
        filepath = os.path.join(DATA_DIR, csv_file)
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                continue
            for row in reader:
                if len(row) < 3:
                    continue
                year = row[0].strip()
                make = row[1].strip()
                model = row[2].strip()
                body_styles = row[3].strip() if len(row) > 3 else ""
                if year and make and model:
                    all_records.append((year, make, model, body_styles))

    print(f"Parsed {len(all_records)} model-year records")

    # Group by make+model to get year ranges and body types
    model_map = {}
    for year, make, model, body_styles in all_records:
        key = (make, model)
        if key not in model_map:
            model_map[key] = {"years": [], "body_types": set()}
        model_map[key]["years"].append(cint(year))
        body_type = _parse_body_styles(body_styles)
        if body_type != "Sedan":
            model_map[key]["body_types"].add(body_type)

    print(f"Consolidated into {len(model_map)} unique make-model combinations")

    # Create makes
    unique_makes = set(make for _, make, _, _ in all_records)
    print(f"\nCreating {len(unique_makes)} Vehicle Makes...")
    make_count = 0
    make_docnames = {}
    for make_name in sorted(unique_makes):
        make_docnames[make_name] = _get_or_create_make(make_name)
        make_count += 1
        if make_count % 50 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"  → {make_count} makes created/updated")

    # Create models
    print(f"\nCreating {len(model_map)} Vehicle Models...")
    model_count = 0
    for (make, model), info in model_map.items():
        years = sorted(info["years"])
        year_start = years[0]
        year_end = years[-1]
        # Pick the most specific body type (non-Sedan if available)
        body_type = "Sedan"
        if info["body_types"]:
            # Prefer specific types in order
            for preferred in ["Pickup", "SUV", "Van", "Coupe", "Hatch", "Convertible", "Wagon"]:
                if preferred in info["body_types"]:
                    body_type = preferred
                    break
            if body_type == "Sedan":
                body_type = list(info["body_types"])[0]

        _get_or_create_model(make, model, make_docnames[make],
                             year=year_start, body_type=body_type)
        model_count += 1
        if model_count % 200 == 0:
            print(f"  → {model_count}/{len(model_map)} models...")
            frappe.db.commit()

    frappe.db.commit()
    print(f"  → {model_count} models created/updated")

    print("\n" + "=" * 60)
    print("US CAR MODELS IMPORT COMPLETE")
    print("=" * 60)
