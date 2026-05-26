"""
PartScape — Catalog Search API for Transactional Documents

Fast search over the 5.7M-record Part Catalog.
Optimizations:
  • Tiered search: exact → prefix → FULLTEXT (uses indexes where possible)
  • SQL_CALC_FOUND_ROWS for exact/prefix (fast, accurate count)
  • LIMIT+1 for FULLTEXT (fast, approximate pagination)
  • Cached total for empty-keyword searches
  • VIN decode result cached in Redis (5 min TTL)
  • Batched Item existence lookup
"""

import frappe
from frappe import _

# Cache key templates
CACHE_KEY_EMPTY_TOTAL = "partscape:search:empty_total"
CACHE_TTL_EMPTY_TOTAL = 3600  # 1 hour
CACHE_TTL_VIN = 300  # 5 minutes


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
    Returns lightweight dicts for the dialog grid with accurate total count
    where possible, and a has_more flag for approximate pagination.
    """
    keyword = (keyword or "").strip()
    brand = (brand or "").strip()
    category = (category or "").strip()
    vehicle_vin = (vehicle_vin or "").strip().upper()
    limit = min(max(limit, 1), 100)

    # VIN-based fitment filter (cached)
    applicable_part_names = None
    if vehicle_vin:
        applicable_part_names = _get_applicable_parts_from_vin(vehicle_vin)
        if applicable_part_names is not None and len(applicable_part_names) == 0:
            return {"data": [], "total": 0, "has_more": False, "limit": limit, "offset": offset}

    # Build optimized query
    rows, total, has_more = _search_parts(
        keyword=keyword,
        brand=brand,
        category=category,
        applicable_part_names=applicable_part_names,
        limit=limit,
        offset=offset,
    )

    # Batch-check Item existence
    _attach_item_codes(rows)

    return {
        "data": rows,
        "total": total,
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
    }


def _get_applicable_parts_from_vin(vehicle_vin: str):
    """Return set of Part Catalog names applicable to the decoded VIN (cached)."""
    cache_key = f"partscape:vin_parts:{vehicle_vin}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return set(cached) if cached != "__empty__" else set()

    from partscape.api.vin_decoder import decode_vin

    try:
        decoded = decode_vin(vehicle_vin)
    except Exception:
        return None

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
        frappe.cache().set_value(cache_key, "__empty__", expires_in_sec=CACHE_TTL_VIN)
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
    result = set(part_names) if part_names else set()
    frappe.cache().set_value(
        cache_key,
        list(result) if result else "__empty__",
        expires_in_sec=CACHE_TTL_VIN,
    )
    return result


def _search_parts(keyword, brand, category, applicable_part_names, limit, offset):
    """
    Tiered search strategy:
      1. Exact part_number match         (fastest — uses idx_part_number)
      2. Prefix part_number match        (fast — uses idx_part_number)
      3. Prefix part_name match          (fast — uses idx_part_name)
      4. FULLTEXT match on all columns   (fast — uses ft_search, LIMIT+1 for speed)
      5. Empty keyword — list all parts  (cached total)
    Returns (rows, total_count, has_more).
    """
    # Build common filter SQL + values
    brand_sql = " AND pc.brand = %s" if brand else ""
    brand_val = [brand] if brand else []
    category_sql = " AND pc.category = %s" if category else ""
    category_val = [category] if category else []

    fitment_sql = ""
    if applicable_part_names is not None:
        if not applicable_part_names:
            return [], 0, False
        names_list = list(applicable_part_names)[:1000]
        escaped_names = [frappe.db.escape(n) for n in names_list]
        fitment_sql = f" AND pc.name IN ({','.join(escaped_names)})"

    if keyword:
        # Tier 1: exact part_number
        rows, total, has_more = _execute_query(
            where_extra="pc.part_number = %s",
            values=[keyword],
            brand_sql=brand_sql,
            brand_val=brand_val,
            category_sql=category_sql,
            category_val=category_val,
            fitment_sql=fitment_sql,
            limit=limit,
            offset=offset,
            order_by="pc.part_number",
            use_calc_found_rows=True,
        )
        if rows:
            return rows, total, has_more

        # Tier 2: prefix on part_number
        rows, total, has_more = _execute_query(
            where_extra="pc.part_number LIKE %s",
            values=[f"{keyword}%"],
            brand_sql=brand_sql,
            brand_val=brand_val,
            category_sql=category_sql,
            category_val=category_val,
            fitment_sql=fitment_sql,
            limit=limit,
            offset=offset,
            order_by="pc.part_number",
            use_calc_found_rows=True,
        )
        if rows:
            return rows, total, has_more

        # Tier 3: prefix on part_name
        rows, total, has_more = _execute_query(
            where_extra="pc.part_name LIKE %s",
            values=[f"{keyword}%"],
            brand_sql=brand_sql,
            brand_val=brand_val,
            category_sql=category_sql,
            category_val=category_val,
            fitment_sql=fitment_sql,
            limit=limit,
            offset=offset,
            order_by="pc.part_name",
            use_calc_found_rows=True,
        )
        if rows:
            return rows, total, has_more

        # Tier 4: FULLTEXT fallback (covers general keyword search)
        # Append * to each word so partial matches work (e.g. "suzuk" → "suzuk*" matches "Suzuki").
        # Multi-word searches use AND (+) for relevance; single-word uses plain OR.
        words = keyword.split()
        if len(words) > 1:
            ft_keyword = " ".join(f"+{w}*" for w in words)
        else:
            ft_keyword = f"{keyword}*"
        rows, total, has_more = _execute_query(
            where_extra="MATCH(pc.part_number, pc.part_name, pc.brand) AGAINST(%s IN BOOLEAN MODE)",
            values=[ft_keyword],
            brand_sql=brand_sql,
            brand_val=brand_val,
            category_sql=category_sql,
            category_val=category_val,
            fitment_sql=fitment_sql,
            limit=limit,
            offset=offset,
            order_by="pc.name DESC",
            use_calc_found_rows=False,  # LIMIT+1 for speed on large resultsets
        )
        return rows, total, has_more

    # Tier 5: no keyword — list all parts, use cached total
    rows, total, has_more = _execute_empty_query(
        brand_sql=brand_sql,
        brand_val=brand_val,
        category_sql=category_sql,
        category_val=category_val,
        fitment_sql=fitment_sql,
        limit=limit,
        offset=offset,
    )
    return rows, total, has_more


def _execute_query(
    where_extra,
    values,
    brand_sql,
    brand_val,
    category_sql,
    category_val,
    fitment_sql,
    limit,
    offset,
    order_by,
    use_calc_found_rows=False,
):
    """Execute SELECT and return (rows, total_count, has_more)."""
    conditions = ["pc.is_active = 1"]
    all_values = []

    if where_extra:
        conditions.append(where_extra)
        all_values.extend(values)

    if brand_sql:
        conditions.append(brand_sql.lstrip(" AND"))
        all_values.extend(brand_val)

    if category_sql:
        conditions.append(category_sql.lstrip(" AND"))
        all_values.extend(category_val)

    where_clause = " AND ".join(conditions)

    if use_calc_found_rows:
        query = f"""
            SELECT SQL_CALC_FOUND_ROWS
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
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """
        all_values.extend([limit, offset])
        rows = frappe.db.sql(query, all_values, as_dict=True)
        total = frappe.db.sql("SELECT FOUND_ROWS()", pluck=True)[0]
        has_more = offset + len(rows) < total
        return rows, total, has_more

    # Fast path: fetch limit+1 rows to determine if there's a next page
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
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """
    all_values.extend([limit + 1, offset])
    rows = frappe.db.sql(query, all_values, as_dict=True)
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    total = offset + len(rows) + (1 if has_more else 0)
    return rows, total, has_more


def _execute_empty_query(brand_sql, brand_val, category_sql, category_val, fitment_sql, limit, offset):
    """Empty-keyword query: fast fetch + cached total (avoids SQL_CALC_FOUND_ROWS on 5.7M rows)."""
    conditions = ["pc.is_active = 1"]
    all_values = []

    if brand_sql:
        conditions.append(brand_sql.lstrip(" AND"))
        all_values.extend(brand_val)

    if category_sql:
        conditions.append(category_sql.lstrip(" AND"))
        all_values.extend(category_val)

    where_clause = " AND ".join(conditions)

    # Fetch rows without calc_found_rows — instant because ORDER BY name DESC uses PK index
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
        ORDER BY pc.name DESC
        LIMIT %s OFFSET %s
    """
    all_values.extend([limit + 1, offset])
    rows = frappe.db.sql(query, all_values, as_dict=True)
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    # Get total from cache or compute once
    cache_key = CACHE_KEY_EMPTY_TOTAL
    if brand_val:
        cache_key += f":brand={brand_val[0]}"
    if category_val:
        cache_key += f":cat={category_val[0]}"
    if fitment_sql:
        cache_key += ":fitment"

    total = frappe.cache().get_value(cache_key)
    if total is None:
        count_sql = f"SELECT COUNT(*) FROM `tabPart Catalog` pc WHERE {where_clause} {fitment_sql}"
        total = frappe.db.sql(count_sql, all_values[:-2], pluck=True)[0]
        frappe.cache().set_value(cache_key, total, expires_in_sec=CACHE_TTL_EMPTY_TOTAL)

    return rows, total, has_more


def _attach_item_codes(rows):
    """Batch lookup Item codes for a list of Part Catalog rows."""
    if not rows:
        return

    catalog_names = [r.part_catalog_name for r in rows]
    if not catalog_names:
        return

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
