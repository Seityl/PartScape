"""
PartScape Patch — Simplify Vehicle.status options to Active/Inactive.

Converts any legacy statuses (Workshop, Scrapped, Sold) to Inactive.
"""

import frappe


def execute():
    print("Simplifying Vehicle.status values to Active/Inactive...")
    legacy = frappe.get_all(
        "Vehicle",
        filters={"status": ["not in", ["Active", "Inactive"]]},
        pluck="name",
    )
    for name in legacy:
        frappe.db.set_value("Vehicle", name, "status", "Inactive", update_modified=False)
    print(f"  -> {len(legacy)} Vehicle records updated")
    frappe.db.commit()
