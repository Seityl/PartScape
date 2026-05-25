"""
Partscape — Daily Data Pipeline

Scheduled via hooks.py scheduler_events.daily
"""

import frappe
from frappe.utils import now, add_days


def run_daily_sync():
    """
    Nightly sync pipeline:
    1. Decode pending VINs
    2. Auto-link orphan Items to Part Catalog
    3. Refresh interchange cache (if any external APIs configured)
    4. Recompute landed cost on draft POs
    """
    frappe.logger().info("Partscape: Starting daily sync pipeline")

    # 1. Pending VINs
    _process_pending_vins()

    # 2. Auto-link items
    from partscape.utils.item_factory import auto_link_items_to_catalog
    auto_link_items_to_catalog()

    # 3. Recompute draft PO landed costs
    _recompute_draft_po_costs()

    frappe.logger().info("Partscape: Daily sync pipeline complete")


def _process_pending_vins():
    from partscape.api.vin_decoder import decode_vin

    vehicles = frappe.get_all(
        "Vehicle",
        filters={
            "last_vin_decode": ("is", "not set"),
            "vin": ("is", "set"),
        },
        fields=["name", "vin"],
        limit_page_length=50,
    )
    for v in vehicles:
        try:
            decode_vin(v.vin)
            frappe.db.set_value("Vehicle", v.name, "last_vin_decode", now())
        except Exception:
            frappe.log_error(title="Partscape Daily VIN Decode Error", message=frappe.get_traceback())
    frappe.db.commit()


def _recompute_draft_po_costs():
    from partscape.api.landed_cost_api import estimate_landed_cost

    draft_pos = frappe.get_all(
        "Purchase Order",
        filters={"docstatus": 0},
        fields=["name"],
        limit_page_length=20,
    )
    for po in draft_pos:
        doc = frappe.get_doc("Purchase Order", po.name)
        changed = False
        for item in doc.items:
            if item.part_catalog_reference and item.estimated_cost_usd:
                try:
                    result = estimate_landed_cost(item.estimated_cost_usd)
                    item.estimated_landed_cost_xcd = result["landed_xcd"]
                    changed = True
                except Exception:
                    continue
        if changed:
            doc.save(ignore_permissions=True)
    frappe.db.commit()
