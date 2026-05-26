"""
PartScape — Item Search API (List View)

Natural search over Items, searching both Item fields
(item_code, item_name, brand) and linked Part Catalog fields
(part_number, brand, part_name) with wildcard LIKE for in-word matching.
"""

import frappe
from frappe import _


@frappe.whitelist()
def search_items_by_catalog(keyword: str = "", limit: int = 500) -> list:
    """
    Return Item names whose own fields OR linked Part Catalog fields match the keyword.
    Uses wildcard LIKE ('%keyword%') so partial/in-word matches work (e.g. 'pad' → 'Brake Pad').
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    limit = min(max(limit, 1), 1000)
    like = f"%{keyword}%"

    items = frappe.db.sql(
        """
        SELECT DISTINCT i.name
        FROM tabItem i
        LEFT JOIN `tabPart Catalog` pc ON i.part_catalog_reference = pc.name
        WHERE i.disabled = 0
          AND (
              i.item_code LIKE %s OR
              i.item_name LIKE %s OR
              i.brand LIKE %s OR
              pc.part_number LIKE %s OR
              pc.brand LIKE %s OR
              pc.part_name LIKE %s
          )
        ORDER BY i.name DESC
        LIMIT %s
        """,
        (like, like, like, like, like, like, limit),
        as_dict=True,
    )

    return [r.name for r in items]
