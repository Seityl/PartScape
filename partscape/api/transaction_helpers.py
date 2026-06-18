"""
PartScape — Transaction Line Helpers

Consolidated endpoints for fetching the extra data needed when a user
selects a Part Catalog reference or Vehicle on a transactional child table.

Returning everything in one call lets the client show a single loading
overlay instead of many small async flickers.
"""

import frappe

from partscape.api.interchange_api import get_interchange_numbers
from partscape.api.landed_cost_api import estimate_landed_cost


@frappe.whitelist()
def get_part_catalog_line_details(part_catalog: str) -> dict:
    """
    Return all PartScape details needed for a transaction line when a
    Part Catalog reference is selected.

    Returns:
        {
            "brand": str,
            "part_number": str,
            "part_name": str,
            "estimated_cost_usd": float,
            "oem_make": str,
            "item_code": str,          # matching Item, if any
            "interchange_numbers": list[str],
            "landed_cost_xcd": float,  # estimated landed cost, if cost available
        }
    """
    if not part_catalog:
        return {}

    pc = frappe.db.get_value(
        "Part Catalog",
        part_catalog,
        ["brand", "part_number", "part_name", "estimated_cost_usd", "oem_make"],
        as_dict=True,
    )
    if not pc:
        return {}

    item_code = frappe.db.get_value(
        "Item", {"part_catalog_reference": part_catalog}, "name"
    )

    interchange_numbers = get_interchange_numbers(part_catalog)

    landed_cost_xcd = None
    if pc.estimated_cost_usd:
        landed = estimate_landed_cost(pc.estimated_cost_usd)
        landed_cost_xcd = landed.get("landed_xcd")

    return {
        "brand": pc.brand,
        "part_number": pc.part_number,
        "part_name": pc.part_name,
        "estimated_cost_usd": pc.estimated_cost_usd,
        "oem_make": pc.oem_make,
        "item_code": item_code,
        "interchange_numbers": interchange_numbers,
        "landed_cost_xcd": landed_cost_xcd,
    }


@frappe.whitelist()
def get_vehicle_line_details(vehicle: str) -> dict:
    """
    Return vehicle details needed for a transaction line.

    Returns:
        {"vin": str, "make": str, "model": str, "year": int}
    """
    if not vehicle:
        return {}

    return frappe.db.get_value(
        "Vehicle",
        vehicle,
        ["vin", "make", "model", "year"],
        as_dict=True,
    ) or {}
