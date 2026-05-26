"""
PartScape — Catalog Search API for Transactional Documents

Fast search over the 5.7M-record Part Catalog.
Optimized: no COUNT query, batched Item lookups, targeted indexing hints.
"""

import frappe
from frappe import _


@frappe.whitelist()
def search_part_catalog_for_transaction(
    keyword: str = "",
    brand: str = "",
    category: str = "",
    vehicle_vin: str = "",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Search Part Catalog with optional VIN-based fitment filtering.
    Returns lightweight dicts for the dialog grid.
    Uses limit+1 to determine if more pages exist (avoids expensive COUNT).
    """
    keyword = (keyword or "").strip()
    brand = (brand or "").strip()
    category = (category or "").strip()
    vehicle_vin = (vehicle_vin or "").strip().upper()
    limit = min(max(limit, 1), 100)

    # VIN-based fitment filter (build list of applicable part names)
    applicable_part_names = None
    if vehicle_vin:
        applicable_part_names = _get_applicable_parts_from_vin(vehicle_vin)
        if applicable_part_names is not None and len(applicable_part_names) == 0:
            # VIN decoded but no applicable parts found
            return {"data": [], "total": 0, "limit": limit, "offset": offset}

    # Build optimized query
    rows = _search_parts(
        keyword=keyword,
        brand=brand,
        category=category,
        applicable_part_names=applicable_part_names,
        limit=limit,
        offset=offset,
    )

    # Batch-check Item existence
    _attach_item_codes(rows)

    # We fetched limit+1 rows; if we got limit+1, there's a next page
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return {
        "data": rows,
        "total": offset + len(rows) + (1 if has_more else 0),  # approximate
        "limit": limit,
        "offset": offset,
    }


def _get_applicable_parts_from_vin(vehicle_vin: str):
    """Return set of Part Catalog names applicable to the decoded VIN."""
    from partscape.api.vin_decoder import decode_vin

    try:
        decoded = decode_vin(vehicle_vin)
    except Exception:
        return None  # VIN decode failed, skip fitment filter

    make = decoded.get("make", "")
    model = decoded.get("model", "")
    if not make or not model:
        return None

    vehicle_models = frappe.get_all(
        "Vehicle Model",
        filters={"make": ("like", f"%{make}%"), "model_name": ("like", f"%{model}%")},
        fields=["name"],
        limit_page_length=20,
    )
    if not vehicle_models:
        return set()

    model_names = [frappe.db.escape(vm.name) for vm in vehicle_models]
    part_names = frappe.db.sql(
        f"""
        SELECT DISTINCT part_catalog
        FROM `tabVehicle Part Applicability`
        WHERE vehicle_model IN ({','.join(model_names)})
        """,
        pluck=True,
    )
    return set(part_names) if part_names else set()


def _search_parts(keyword, brand, category, applicable_part_names, limit, offset):
    """Optimized part search without COUNT."""
    conditions = ["pc.is_active = 1"]
    values = []

    # Keyword strategy: exact/part-number prefix is fast; fallback to LIKE
    if keyword:
        # Try exact part number match first (fastest)
        exact_match = frappe.db.sql(
            """
            SELECT name AS part_catalog_name, brand, part_number, part_name,
                   category, estimated_cost_usd, diagram_reference, images
            FROM `tabPart Catalog`
            WHERE is_active = 1 AND part_number = %s
            LIMIT %s
            """,
            (keyword, limit + 1),
            as_dict=True,
        )
        if exact_match:
            return exact_match

        # Try prefix match on part_number (can use index)
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

    where_clause = " AND ".join(conditions)

    # If we have a VIN fitment list, add it
    fitment_sql = ""
    if applicable_part_names is not None:
        if not applicable_part_names:
            return []
        # Batch fitment filter — chunk if huge
        names_list = list(applicable_part_names)
        if len(names_list) > 1000:
            names_list = names_list[:1000]  # cap to keep query fast
        escaped_names = [frappe.db.escape(n) for n in names_list]
        fitment_sql = f" AND pc.name IN ({','.join(escaped_names)})"

    # Main query — no ORDER BY when keyword search (avoids filesort on huge resultset)
    # Just return most recently imported parts when no keyword
    order_by = "ORDER BY pc.brand, pc.part_number" if keyword else "ORDER BY pc.name DESC"

    query = f"""
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
        {fitment_sql}
        {order_by}
        LIMIT %s OFFSET %s
    """
    query_values = list(values) + [limit + 1, offset]
    return frappe.db.sql(query, query_values, as_dict=True)


def _attach_item_codes(rows):
    """Batch lookup Item codes for a list of Part Catalog rows."""
    if not rows:
        return

    catalog_names = [r.part_catalog_name for r in rows]
    if not catalog_names:
        return

    # Chunk to avoid huge IN clause
    chunk_size = 500
    item_map = {}
    for i in range(0, len(catalog_names), chunk_size):
        chunk = catalog_names[i:i + chunk_size]
        escaped = [frappe.db.escape(n) for n in chunk]
        results = frappe.db.sql(
            f"""
            SELECT part_catalog_reference, name, item_name
            FROM tabItem
            WHERE part_catalog_reference IN ({','.join(escaped)})
            """,
            as_dict=True,
        )
        for r in results:
            item_map[r.part_catalog_reference] = (r.name, r.item_name)

    for row in rows:
        item = item_map.get(row.part_catalog_name)
        row["item_code"] = item[0] if item else None
        row["item_name"] = item[1] if item else None
        row["thumbnail"] = row.images


@frappe.whitelist()
def create_item_from_catalog_dialog(part_catalog_name: str) -> dict:
    """Called when user selects a Part Catalog entry from the dialog."""
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
