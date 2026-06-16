"""
Create missing Custom Field docs for Purchase Receipt Item.
Columns already exist in DB from prior run; just need the docs.
"""

import frappe


def execute():
    missing = [
        {
            "fieldname": "vin",
            "label": "VIN",
            "fieldtype": "Data",
            "insert_after": "part_catalog_reference",
        },
        {
            "fieldname": "alternative_part_numbers",
            "label": "Alternative Part Numbers",
            "fieldtype": "Data",
            "insert_after": "vin",
        },
        {
            "fieldname": "applicable_models",
            "label": "Applicable Models",
            "fieldtype": "Data",
            "insert_after": "alternative_part_numbers",
        },
    ]

    for field_def in missing:
        cf_name = f"Purchase Receipt Item-{field_def['fieldname']}"
        if frappe.db.exists("Custom Field", cf_name):
            continue
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Purchase Receipt Item",
            "module": "PartScape",
            "fieldname": field_def["fieldname"],
            "label": field_def["label"],
            "fieldtype": field_def["fieldtype"],
            "insert_after": field_def["insert_after"],
            "read_only": 0,
            "hidden": 0,
            "print_hide": 0,
            "is_system_generated": 1,
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"Created {cf_name}")

    frappe.db.commit()
