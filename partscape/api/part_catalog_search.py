"""
PartScape — Catalog Search API for Transactional Documents

Search the 5.7M-record Part Catalog from PO/SO/DN/SI/PR/PI/Stock Entry.
Supports VIN-based fitment filtering.
"""

import frappe
from frappe import _


@frappe.whitelist()
def search_part_catalog_for_transaction(
    keyword: str = "",
    brand: str = "",
    category: str = "",
    vehicle_vin: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Search Part Catalog with optional VIN-based fitment filtering.
    Returns lightweight dicts for the dialog grid, plus total count.
    """
    keyword = (keyword or "").strip()
    brand = (brand or "").strip()
    category = (category or "").strip()
    vehicle_vin = (vehicle_vin or "").strip().upper()
    limit = min(max(limit, 1), 100)

    # Build base filters
    conditions = ["pc.is_active = 1"]
    values = []

    if keyword:
        conditions.append(
            "(pc.part_number LIKE %s OR pc.part_name LIKE %s OR pc.brand LIKE %s)"
        )
        like = f"%{keyword}%"
        values.extend([like, like, like])

    if brand:
        conditions.append("pc.brand = %s")
        values.append(brand)

    if category:
        conditions.append("pc.category = %s")
        values.append(category)

    # VIN-based fitment filter
    vehicle_filter_sql = ""
    if vehicle_vin:
        # Decode VIN to get make/model
        from partscape.api.vin_decoder import decode_vin
        try:
            decoded = decode_vin(vehicle_vin)
        except Exception:
            decoded = {}

        make = decoded.get("make", "")
        model = decoded.get("model", "")

        if make and model:
            # Find matching vehicle models
            vehicle_models = frappe.get_all(
                "Vehicle Model",
                filters={"make": ("like", f"%{make}%"), "model_name": ("like", f"%{model}%")},
                fields=["name"],
                limit_page_length=20,
            )
            if vehicle_models:
                model_names = [frappe.db.escape(vm.name) for vm in vehicle_models]
                vehicle_filter_sql = f"""
                    AND EXISTS (
                        SELECT 1 FROM `tabVehicle Part Applicability` vpa
                        WHERE vpa.part_catalog = pc.name
                        AND vpa.vehicle_model IN ({','.join(model_names)})
                    )
                """

    where_clause = " AND ".join(conditions)

    # Count query
    count_sql = f"""
        SELECT COUNT(*) FROM `tabPart Catalog` pc
        WHERE {where_clause}
        {vehicle_filter_sql}
    """
    total = frappe.db.sql(count_sql, values)[0][0] if values else frappe.db.sql(count_sql)[0][0]

    # Data query
    data_sql = f"""
        SELECT
            pc.name AS part_catalog_name,
            pc.brand,
            pc.part_number,
            pc.part_name,
            pc.category,
            pc.estimated_cost_usd,
            pc.diagram_reference,
            pc.images
        FROM `tabPart Catalog` pc
        WHERE {where_clause}
        {vehicle_filter_sql}
        ORDER BY pc.brand, pc.part_number
        LIMIT %s OFFSET %s
    """
    query_values = list(values) + [limit, offset]
    rows = frappe.db.sql(data_sql, query_values, as_dict=True)

    # Check which ones already have Items
    for row in rows:
        item = frappe.db.get_value(
            "Item",
            {"part_catalog_reference": row.part_catalog_name},
            ["name", "item_name"],
            as_dict=True,
        )
        row["item_code"] = item.name if item else None
        row["item_name"] = item.item_name if item else None
        # Thumbnail: use first image if available
        row["thumbnail"] = None
        if row.images:
            # images field is Attach Image (single) or could be a list
            # In Part Catalog, 'images' is Attach Image — single value
            row["thumbnail"] = row.images

    return {
        "data": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@frappe.whitelist()
def create_item_from_catalog_dialog(part_catalog_name: str) -> dict:
    """
    Called when user selects a Part Catalog entry from the dialog.
    Creates or finds the matching Item and returns its code + metadata.
    """
    from partscape.utils.item_factory import create_item_from_part_catalog

    item_code = create_item_from_part_catalog(part_catalog_name, create_if_missing=True)
    if not item_code:
        return {"error": "Unable to create Item from Part Catalog"}

    item = frappe.get_doc("Item", item_code)
    pc = frappe.get_doc("Part Catalog", part_catalog_name)

    return {
        "item_code": item_code,
        "item_name": item.item_name,
        "part_catalog_reference": part_catalog_name,
        "brand": pc.brand,
        "part_number": pc.part_number,
        "description": f"{pc.part_name} — {pc.brand} {pc.part_number}",
        "diagram_reference": pc.diagram_reference,
    }
