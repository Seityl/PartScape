"""
PartScape — Kaggle Qubdi Vehicles & Categories Importer

Source: https://www.kaggle.com/datasets/qubdidata/auto-parts-dataset
License: CC BY-NC 4.0 (non-commercial — used here for seed/demo data only)
Format: CSV files
Records: 1,615 vehicles, 665 categories

Imports into:
- Vehicle Make (new manufacturers)
- Vehicle Model (new models)
- Part Category (hierarchical category tree)
"""

import csv
import os

import frappe
from frappe.utils import cint

DATA_DIR = frappe.get_app_path("partscape", "data_imports", "kaggle")
VEHICLES_CSV = os.path.join(DATA_DIR, "vehicles.csv")
CATEGORIES_CSV = os.path.join(DATA_DIR, "product_category.csv")


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


def _get_or_create_model(make_name: str, model_name: str) -> str:
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"

    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        return existing

    make_docname = _get_or_create_make(make_name)
    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_docname,
        "model_code": model_code,
        "year_start": 1990,
        "year_end": 2026,
        "body_type": "Sedan",
        "steering_position": "LHD",
        "primary_market": "Global",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def import_vehicles() -> int:
    """Import vehicle makes and models from Kaggle vehicles.csv."""
    count = 0
    with open(VEHICLES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model_name = row.get("model_name", "").strip()
            manufacturer = row.get("manufacturer_name", "").strip()
            if not model_name or not manufacturer:
                continue
            _get_or_create_model(manufacturer, model_name)
            count += 1
            if count % 100 == 0:
                frappe.db.commit()
    frappe.db.commit()
    return count


def _get_or_create_category(category_name: str, parent_name: str = None) -> str:
    """Get or create a Part Category. Handles hierarchy."""
    if not category_name:
        return None

    # Check if exists
    filters = {"category_name": category_name}
    if parent_name:
        parent_doc = frappe.db.get_value("Part Category", {"category_name": parent_name}, "name")
        if parent_doc:
            filters["parent_category"] = parent_doc

    existing = frappe.db.get_value("Part Category", filters, "name")
    if existing:
        return existing

    doc_data = {
        "doctype": "Part Category",
        "category_name": category_name,
    }
    if parent_name:
        parent_doc = frappe.db.get_value("Part Category", {"category_name": parent_name}, "name")
        if parent_doc:
            doc_data["parent_category"] = parent_doc

    doc = frappe.get_doc(doc_data)
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def import_categories() -> int:
    """Import hierarchical part categories from Kaggle product_category.csv."""
    # Read all categories first
    categories = {}
    with open(CATEGORIES_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat_id = row.get("id", "").strip()
            cat_name = row.get("category_name", "").strip()
            parent_id = row.get("parent_category_id", "").strip()
            if cat_id and cat_name:
                categories[cat_id] = {
                    "name": cat_name,
                    "parent_id": parent_id if parent_id else None,
                }

    # Build id -> parent_name mapping
    id_to_name = {cid: info["name"] for cid, info in categories.items()}

    # Import in passes: first roots, then children
    imported = set()
    count = 0
    max_passes = 10

    for _ in range(max_passes):
        progress = False
        for cat_id, info in categories.items():
            if cat_id in imported:
                continue
            cat_name = info["name"]
            parent_id = info["parent_id"]
            parent_name = id_to_name.get(parent_id) if parent_id else None

            # If parent exists or is root, import
            if not parent_name or frappe.db.exists("Part Category", {"category_name": parent_name}):
                _get_or_create_category(cat_name, parent_name)
                imported.add(cat_id)
                count += 1
                progress = True
                if count % 50 == 0:
                    frappe.db.commit()

        frappe.db.commit()
        if not progress:
            break

    # Import any remaining (orphans)
    for cat_id, info in categories.items():
        if cat_id not in imported:
            _get_or_create_category(info["name"], None)
            count += 1

    frappe.db.commit()
    return count


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Kaggle Qubdi Vehicles & Categories Importer")
    print("Source: kaggle.com/datasets/qubdidata/auto-parts-dataset")
    print("License: CC BY-NC 4.0 (non-commercial)")
    print("=" * 60)

    print("\n[1/2] Importing vehicles...")
    vehicle_count = import_vehicles()
    print(f"  → {vehicle_count} vehicle models imported/updated")

    print("\n[2/2] Importing part categories...")
    category_count = import_categories()
    print(f"  → {category_count} categories imported/updated")

    print("\n" + "=" * 60)
    print("KAGGLE IMPORT COMPLETE")
    print("=" * 60)
    print(f"Vehicle Models:         {vehicle_count}")
    print(f"Part Categories:        {category_count}")
    print("=" * 60)
