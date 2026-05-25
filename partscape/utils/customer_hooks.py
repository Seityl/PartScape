"""
PartScape — Customer Hooks

Keeps Customer.vehicles child table in sync with Vehicle.owner field.
"""

import frappe
from frappe import _


def validate_customer(doc, method):
    """
    Ensure only one vehicle is marked as primary.
    Also ensure Vehicle.owner matches this customer if linked.
    """
    if not hasattr(doc, 'vehicles') or not doc.vehicles:
        return
    primary_count = sum(1 for v in doc.vehicles if v.is_primary)
    if primary_count > 1:
        frappe.throw(_("A customer can only have one primary vehicle."))


def after_insert_customer(doc, method):
    _sync_customer_to_vehicles(doc)


def on_update_customer(doc, method):
    _sync_customer_to_vehicles(doc)


def _sync_customer_to_vehicles(customer_doc):
    """
    For each vehicle in the customer's child table, ensure Vehicle.owner points back.
    """
    if not hasattr(customer_doc, 'vehicles') or not customer_doc.vehicles:
        return
    for row in customer_doc.vehicles:
        if not row.vehicle:
            continue
        current_customer = frappe.db.get_value("Vehicle", row.vehicle, "customer")
        if current_customer != customer_doc.name:
            frappe.db.set_value("Vehicle", row.vehicle, "customer", customer_doc.name)

    # Also handle removals: if a vehicle was removed from customer, clear its customer link
    # (Only if the vehicle's customer is still this customer)
    # We check all vehicles that have this customer as customer but are NOT in the child table
    linked_vehicles = [r.vehicle for r in customer_doc.vehicles if r.vehicle]
    orphaned = frappe.get_all(
        "Vehicle",
        filters={"customer": customer_doc.name},
        fields=["name"],
    )
    for ov in orphaned:
        if ov.name not in linked_vehicles:
            frappe.db.set_value("Vehicle", ov.name, "customer", None)

    frappe.db.commit()
