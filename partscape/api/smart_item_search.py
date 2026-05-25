"""
PartScape — Smart Item Search

Extends the standard Item link field search to also match:
- Item.part_number (OEM / manufacturer part number)
- Item.part_catalog_reference (Part Catalog name)
- Item Supplier.supplier_part_no (supplier SKU)
"""

import frappe
from frappe import _


@frappe.whitelist()
def smart_item_search_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query for Item link fields in transactional documents.
    Searches item_code, item_name, part_number, part_catalog_reference,
    and supplier_part_no.
    """
    txt = (txt or "").strip()
    like_pattern = f"%{txt}%"

    # Build the UNION query
    sql = """
        SELECT DISTINCT
            item.name,
            item.item_name,
            item.brand,
            CONCAT(
                COALESCE(item.part_number, ''),
                CASE WHEN item.part_number IS NOT NULL AND item.part_catalog_reference IS NOT NULL THEN ' | ' ELSE '' END,
                COALESCE(item.part_catalog_reference, '')
            ) AS extra_info
        FROM `tabItem` item
        WHERE item.disabled = 0
            AND (
                item.name LIKE %(txt)s
                OR item.item_name LIKE %(txt)s
                OR item.brand LIKE %(txt)s
                OR item.description LIKE %(txt)s
                OR item.part_number LIKE %(txt)s
                OR item.part_catalog_reference LIKE %(txt)s
                OR EXISTS (
                    SELECT 1 FROM `tabItem Supplier` its
                    WHERE its.parent = item.name
                    AND its.supplier_part_no LIKE %(txt)s
                )
            )
        ORDER BY
            CASE WHEN item.name LIKE %(txt)s THEN 0 ELSE 1 END,
            CASE WHEN item.part_number LIKE %(txt)s THEN 0 ELSE 1 END,
            item.name
        LIMIT %(start)s, %(page_len)s
    """

    results = frappe.db.sql(
        sql,
        {"txt": like_pattern, "start": int(start), "page_len": int(page_len)},
        as_list=True,
    )
    return results
