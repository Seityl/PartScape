"""
Partscape — Purchase Order Hooks
"""

import frappe
from frappe import _


def validate_purchase_order(doc, method):
    """
    Validate PO items: if part_catalog_reference is set, ensure consistency with vehicle.
    """
    for item in doc.items:
        if item.part_catalog_reference and item.vehicle:
            # Verify part applicability for this vehicle
            vehicle = frappe.get_doc("Vehicle", item.vehicle)
            if not vehicle.model:
                continue

            applicable = frappe.db.exists("Vehicle Part Applicability", {
                "part_catalog": item.part_catalog_reference,
                "vehicle_model": vehicle.model,
            })
            if not applicable:
                # Soft warning only; do not block (aftermarket parts may fit broadly)
                frappe.msgprint(
                    _(
                        "Row {0}: Part {1} does not have explicit applicability for {2} {3}. "
                        "Please verify fitment before ordering."
                    ).format(
                        item.idx,
                        item.part_catalog_reference,
                        vehicle.make,
                        vehicle.model,
                    ),
                    indicator="orange",
                    alert=True,
                )
