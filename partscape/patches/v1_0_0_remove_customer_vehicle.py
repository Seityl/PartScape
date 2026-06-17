"""
PartScape Patch — Remove the redundant Customer Vehicle DocType.

Vehicle already has a Customer link field, so Customer Vehicle (which was
only a thin wrapper around Vehicle with fetched fields) is unnecessary.
"""

import frappe


def execute():
    print("=" * 60)
    print("PartScape — Remove Customer Vehicle")
    print("=" * 60)

    # Delete any existing Customer Vehicle documents
    names = frappe.db.sql_list("SELECT name FROM `tabCustomer Vehicle`")
    print(f"[1/2] Deleting {len(names)} Customer Vehicle records...")
    for name in names:
        try:
            frappe.delete_doc("Customer Vehicle", name, ignore_permissions=True, force=True)
        except Exception:
            pass

    # Drop the obsolete table
    print("[2/2] Dropping obsolete table...")
    exists = frappe.db.sql(
        "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        "tabCustomer Vehicle",
    )
    if exists:
        frappe.db.sql_ddl("DROP TABLE `tabCustomer Vehicle`")
        print("  -> dropped tabCustomer Vehicle")
    else:
        print("  -> tabCustomer Vehicle already gone")

    frappe.db.commit()
    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
