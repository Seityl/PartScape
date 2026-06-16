"""
PartScape — Part Catalog Bulk Import

Usage:
    bench --site your-site.local execute partscape.data_import.import_part_catalog.import_from_csv --args "['/path/to/parts.csv', 'Toyota']"

CSV Expected Columns:
    brand, part_number, part_name, category, description,
    weight_kg, dimensions, estimated_cost_usd, vehicle_model, year_start, year_end,
    engine_code, steering_position, market_code

Optional columns for interchange:
    interchange_brand, interchange_part_number, quality_tier, relationship_type
"""

import csv
import os
import frappe
from frappe import _


def import_from_csv(file_path: str, default_vehicle_make: str = "Toyota"):
    """
    Import part catalog from CSV. Creates Part Catalog + Vehicle Part Applicability + Interchange edges.
    """
    if not os.path.exists(file_path):
        frappe.throw(_("File not found: {0}").format(file_path))

    make_doc = _ensure_make(default_vehicle_make)
    created_parts = 0
    created_applicability = 0
    created_interchange = 0

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                brand = row.get("brand", default_vehicle_make).strip()
                part_number = row.get("part_number", "").strip().upper()
                part_name = row.get("part_name", "").strip()
                if not brand or not part_number or not part_name:
                    continue

                brand_doc = _ensure_brand(brand)
                category_doc = _ensure_item_group(row.get("category", "General"))
                market_doc = _ensure_market(row.get("market_code", ""))

                # Upsert Part Catalog (composite identity: brand + part_number)
                existing = frappe.db.get_value("Part Catalog", {"brand": brand_doc, "part_number": part_number}, "name")
                if existing:
                    pc = frappe.get_doc("Part Catalog", existing)
                else:
                    is_oem = _is_oem_brand(brand, default_vehicle_make)
                    pc = frappe.get_doc({
                        "doctype": "Part Catalog",
                        "brand": brand_doc,
                        "part_number": part_number,
                        "part_name": part_name,
                        "oem_make": make_doc if is_oem else None,
                        "is_oem": 1 if is_oem else 0,
                        "category": category_doc,
                        "description": row.get("description", ""),
                        "weight_kg": _to_float(row.get("weight_kg")),
                        "dimensions": row.get("dimensions", ""),
                        "estimated_cost_usd": _to_float(row.get("estimated_cost_usd")),
                        "steering_position": row.get("steering_position", "Universal"),
                        "market_restriction": market_doc,
                    })
                    pc.insert(ignore_permissions=True)
                    created_parts += 1

                # Vehicle Part Applicability (only for OEM parts; aftermarket inherits via interchange)
                model = row.get("vehicle_model", "").strip()
                if model and pc.is_oem:
                    model_doc = _ensure_model(model, make_doc)
                    variant = row.get("engine_code", "").strip()
                    variant_doc = _ensure_variant(model_doc, variant) if variant else None

                    exists = frappe.db.exists("Vehicle Part Applicability", {
                        "part_catalog": pc.name,
                        "vehicle_model": model_doc,
                        "year_start": _to_int(row.get("year_start")),
                        "year_end": _to_int(row.get("year_end")),
                    })
                    if not exists:
                        va = frappe.get_doc({
                            "doctype": "Vehicle Part Applicability",
                            "part_catalog": pc.name,
                            "vehicle_model": model_doc,
                            "variant": variant_doc,
                            "year_start": _to_int(row.get("year_start")),
                            "year_end": _to_int(row.get("year_end")),
                            "steering_position": row.get("steering_position", "Universal"),
                            "market_code": row.get("market_code", ""),
                        })
                        va.insert(ignore_permissions=True)
                        created_applicability += 1

                # Interchange edge (optional columns)
                ix_brand = row.get("interchange_brand", "").strip()
                ix_part = row.get("interchange_part_number", "").strip()
                if ix_brand and ix_part:
                    ix_brand_doc = _ensure_brand(ix_brand)
                    # Ensure the interchange part exists in catalog too
                    ix_pc_name = frappe.db.get_value("Part Catalog", {"brand": ix_brand_doc, "part_number": ix_part}, "name")
                    if not ix_pc_name:
                        ix_pc = frappe.get_doc({
                            "doctype": "Part Catalog",
                            "brand": ix_brand_doc,
                            "part_number": ix_part,
                            "part_name": f"{ix_brand} {ix_part}",
                            "category": category_doc,
                            "is_oem": 0,
                        })
                        ix_pc.insert(ignore_permissions=True)
                        ix_pc_name = ix_pc.name

                    if not frappe.db.exists("Part Interchange", {
                        "part_a": pc.name,
                        "part_b": ix_pc_name,
                    }) and not frappe.db.exists("Part Interchange", {
                        "part_a": ix_pc_name,
                        "part_b": pc.name,
                    }):
                        ix = frappe.get_doc({
                            "doctype": "Part Interchange",
                            "part_a": pc.name,
                            "part_b": ix_pc_name,
                            "relationship_type": row.get("relationship_type", "Equivalent"),
                            "quality_tier": row.get("quality_tier", "Aftermarket"),
                            "confidence_score": 1.0,
                            "source": "Bulk Import",
                        })
                        ix.insert(ignore_permissions=True)
                        created_interchange += 1

            except Exception:
                frappe.log_error(title="Part Catalog Import Row Error", message=frappe.get_traceback())
                continue

    frappe.db.commit()
    return {
        "created_parts": created_parts,
        "created_applicability": created_applicability,
        "created_interchange": created_interchange,
    }


def _ensure_make(make_name: str) -> str:
    name = frappe.db.get_value("Vehicle Make", {"make_name": make_name}, "name")
    if name:
        return name
    doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": make_name})
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_brand(brand_name: str) -> str:
    if not brand_name:
        return None
    if frappe.db.exists("Brand", brand_name):
        return brand_name
    doc = frappe.get_doc({"doctype": "Brand", "brand": brand_name})
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_item_group(group_name: str) -> str:
    if not group_name:
        group_name = "General"
    if frappe.db.exists("Item Group", group_name):
        return group_name
    doc = frappe.get_doc({"doctype": "Item Group", "item_group_name": group_name, "is_group": 0})
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_market(market_code: str) -> str:
    if not market_code:
        return None
    existing = frappe.db.get_value("Market", {"market_code": market_code}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Market", "market_code": market_code, "market_name": market_code})
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_model(model_name: str, make_name: str) -> str:
    name = frappe.db.get_value("Vehicle Model", {"model_name": model_name, "make": make_name}, "name")
    if name:
        return name
    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_name,
        "steering_position": "RHD",
        "primary_market": "JDM",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_variant(model_name: str, engine_code: str) -> str:
    name = frappe.db.get_value("Vehicle Engine Variant", {"variant_name": engine_code, "model": model_name}, "name")
    if name:
        return name
    doc = frappe.get_doc({
        "doctype": "Vehicle Engine Variant",
        "variant_name": engine_code,
        "model": model_name,
        "engine_code": engine_code,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _is_oem_brand(brand: str, vehicle_make: str) -> bool:
    """Simple heuristic: brand matches vehicle make name -> OEM."""
    return brand.strip().lower() == vehicle_make.strip().lower()


def _to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _to_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


@frappe.whitelist()
def download_csv_template():
    """Return a CSV template string for Part Catalog import."""
    header = [
        "brand", "part_number", "part_name", "category", "description",
        "weight_kg", "dimensions", "estimated_cost_usd",
        "vehicle_model", "year_start", "year_end", "engine_code",
        "steering_position", "market_code", "interchange_brand", "interchange_part_number",
        "relationship_type", "quality_tier"
    ]
    sample = [
        "Toyota", "04465-26421", "Brake Pad Set, Disc", "Brake", "Front brake pad set for Hiace",
        "1.2", "145x55x18", "28.50",
        "Hiace", "2012", "2020", "1KD-FTV",
        "RHD", "JDM", "Bosch", "0 986 494 046",
        "Equivalent", "OEM Equivalent"
    ]
    return {
        "filename": "partscape_part_catalog_template.csv",
        "content": ",".join(header) + "\n" + ",".join(sample) + "\n"
    }
