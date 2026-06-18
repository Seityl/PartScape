"""
PartScape — Shelf / Rack API

Helpers for reading Item → Shelf / Rack tag assignments.
"""

import frappe


@frappe.whitelist()
def get_item_shelf_rack_tags(item_code: str, warehouse: str) -> list:
    """
    Return a list of Shelf / Rack codes assigned to an Item for a given warehouse.

    Example output:
        ["1A", "1B"]
    """
    if not item_code or not warehouse:
        return []

    rows = frappe.get_all(
        "Item Shelf Rack",
        filters={
            "parent": item_code,
            "parenttype": "Item",
            "warehouse": warehouse,
        },
        fields=["shelf_rack_code"],
        order_by="shelf_rack_code",
    )

    return sorted({r.shelf_rack_code for r in rows if r.shelf_rack_code})
