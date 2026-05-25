"""
PartScape Patch — Add PartScape custom fields to all transactional child tables.
"""

import frappe


def execute():
    """Create missing custom fields for Sales Order, Delivery Note, Sales Invoice,
    Purchase Invoice, and Purchase Receipt child tables."""

    target_dts = [
        "Sales Order Item",
        "Delivery Note Item",
        "Sales Invoice Item",
        "Purchase Invoice Item",
        "Purchase Receipt Item",
    ]

    # Field definitions in display order
    fields = [
        {
            "fieldname": "vehicle",
            "label": "Vehicle",
            "fieldtype": "Link",
            "options": "Vehicle",
            "insert_after": "item_code",
        },
        {
            "fieldname": "part_catalog_reference",
            "label": "Part Catalog Reference",
            "fieldtype": "Link",
            "options": "Part Catalog",
            "insert_after": "vehicle",
        },
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
        {
            "fieldname": "diagram_reference",
            "label": "Diagram Reference",
            "fieldtype": "Data",
            "insert_after": "applicable_models",
        },
    ]

    created = 0
    for dt in target_dts:
        for field_def in fields:
            fieldname = field_def["fieldname"]
            cf_name = f"{dt}-{fieldname}"

            if frappe.db.exists("Custom Field", cf_name):
                continue

            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "module": "PartScape",
                "fieldname": fieldname,
                "label": field_def["label"],
                "fieldtype": field_def["fieldtype"],
                "options": field_def.get("options"),
                "insert_after": field_def["insert_after"],
                "read_only": 0,
                "hidden": 0,
                "print_hide": 0,
                "is_system_generated": 1,
            }).insert(ignore_permissions=True, ignore_if_duplicate=True)
            created += 1

    frappe.db.commit()
    print(f"Created {created} custom fields across {len(target_dts)} child tables.")
