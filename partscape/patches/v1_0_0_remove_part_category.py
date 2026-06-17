"""
PartScape Patch — Remove the Part Category DocType.

Part Category has been replaced by ERPNext's built-in Item Group.
This patch cleans up any leftover records, DB tables, and DocType metadata.
"""

import frappe


def _delete_records():
    print("[1/3] Deleting Part Category records...")
    if not frappe.db.table_exists("Part Category"):
        print("  -> table does not exist; nothing to delete")
        return
    names = frappe.db.sql_list("SELECT name FROM `tabPart Category`")
    for name in names:
        try:
            frappe.delete_doc("Part Category", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    print(f"  -> {len(names)} Part Category records removed")


def _drop_table():
    print("[2/3] Dropping Part Category table...")
    if frappe.db.table_exists("Part Category"):
        frappe.db.sql_ddl("DROP TABLE `tabPart Category`")
        print("  -> dropped tabPart Category")
    else:
        print("  -> table already gone")


def _delete_doctype():
    print("[3/3] Removing Part Category DocType metadata...")
    if frappe.db.exists("DocType", "Part Category"):
        frappe.delete_doc("DocType", "Part Category", ignore_permissions=True, force=True)
        print("  -> Part Category DocType removed")
    else:
        print("  -> DocType already removed")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Remove Part Category")
    print("=" * 60)

    _delete_records()
    _drop_table()
    _delete_doctype()
    frappe.db.commit()

    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
