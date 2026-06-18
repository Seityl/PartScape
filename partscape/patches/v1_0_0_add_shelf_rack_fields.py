"""
PartScape Patch — Add Shelf / Rack tagging fields to Item and Sales Order Item.
"""

import frappe


def execute():
    """Create custom fields for Item Shelf Rack child table on Item
    and read-only tag display on Sales Order Item."""

    fields_to_create = [
        {
            "dt": "Item",
            "fieldname": "item_shelf_racks",
            "label": "Shelf / Rack Tags",
            "fieldtype": "Table",
            "options": "Item Shelf Rack",
            "insert_after": "partscape_barcode",
            "read_only": 0,
        },
        {
            "dt": "Sales Order Item",
            "fieldname": "shelf_rack_tags",
            "label": "Shelf / Rack Tags",
            "fieldtype": "Data",
            "insert_after": "warehouse",
            "read_only": 1,
            "description": "Shelf / Rack tags for the selected item and warehouse",
        },
    ]

    created = 0
    for field_def in fields_to_create:
        cf_name = f"{field_def['dt']}-{field_def['fieldname']}"
        if frappe.db.exists("Custom Field", cf_name):
            continue

        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": field_def["dt"],
            "module": "PartScape",
            "fieldname": field_def["fieldname"],
            "label": field_def["label"],
            "fieldtype": field_def["fieldtype"],
            "options": field_def.get("options"),
            "insert_after": field_def["insert_after"],
            "read_only": field_def.get("read_only", 0),
            "hidden": 0,
            "print_hide": 0,
            "is_system_generated": 1,
            "description": field_def.get("description"),
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
        created += 1

    frappe.db.commit()
    print(f"Created {created} Shelf / Rack custom fields.")
