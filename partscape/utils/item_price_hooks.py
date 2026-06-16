"""
PartScape — Item Price hooks.
"""

import frappe


def validate_item_price(doc, method):
    """
    If the user entered a VAT-inclusive price, recalculate the net
    ERPNext price_list_rate from it.

    Formula: price_without_vat = price_with_vat / (1 + vat_rate)
    """
    if not doc.get("partscape_price_includes_vat"):
        return

    price_with_vat = doc.get("partscape_price_with_vat") or 0
    if not price_with_vat:
        return

    vat_rate = doc.get("partscape_vat_rate")
    if vat_rate is None:
        vat_rate = frappe.db.get_single_value("PartScape Settings", "default_vat_rate") or 0

    if vat_rate < 0:
        frappe.throw(frappe._("VAT rate cannot be negative."))

    # Avoid division by zero / negative: a -100% rate would zero the denominator.
    if vat_rate <= -100:
        frappe.throw(frappe._("VAT rate must be greater than -100%."))

    doc.price_list_rate = price_with_vat / (1 + (vat_rate / 100))


def before_insert_item_price(doc, method):
    """Default the VAT rate from PartScape Settings if not already set."""
    if doc.get("partscape_price_includes_vat") and doc.get("partscape_vat_rate") is None:
        default_vat = frappe.db.get_single_value("PartScape Settings", "default_vat_rate")
        if default_vat is not None:
            doc.partscape_vat_rate = default_vat
