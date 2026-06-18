"""
PartScape Patch — Remove the legacy Item barcode custom field and move
Shelf / Rack Tags to the Inventory tab.

The legacy barcode value is intentionally dropped; new PartScape barcodes
are generated as random 13-digit EAN-13 codes in the standard Item Barcode
child table.
"""

import frappe


def execute():
    barcode_cf = "Item-partscape_barcode"
    if frappe.db.exists("Custom Field", barcode_cf):
        frappe.delete_doc("Custom Field", barcode_cf, force=1, ignore_permissions=True)
        frappe.db.commit()

    shelf_cf = "Item-item_shelf_racks"
    if frappe.db.exists("Custom Field", shelf_cf):
        cf = frappe.get_doc("Custom Field", shelf_cf)
        if cf.insert_after != "inventory_section":
            cf.insert_after = "inventory_section"
            cf.save(ignore_permissions=True)
            frappe.clear_cache(doctype="Item")
