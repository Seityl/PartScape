"""
PartScape Patch — Remove the Part Diagram / Part Catalog Diagram feature.

Cleans up all data and DB artifacts for:
  - Part Catalog Diagram (child table on Part Catalog)
  - Part Diagram
  - Parts Group (only used by diagrams)
"""

import frappe


def _delete_child_table_rows():
    print("[1/4] Deleting Part Catalog Diagram child table rows...")
    if not frappe.db.table_exists("Part Catalog Diagram"):
        print("  -> Part Catalog Diagram table not found; skipping")
        return
    count = frappe.db.sql("DELETE FROM `tabPart Catalog Diagram`")
    print("  -> deleted")


def _delete_part_diagrams():
    print("[2/4] Deleting Part Diagram records and attached files...")
    if not frappe.db.table_exists("Part Diagram"):
        print("  -> Part Diagram table not found; skipping")
        return
    names = frappe.db.sql_list("SELECT name FROM `tabPart Diagram`")
    for name in names:
        # Delete attached File records first so files are cleaned up.
        file_names = frappe.db.sql_list(
            "SELECT name FROM `tabFile` WHERE attached_to_doctype = 'Part Diagram' AND attached_to_name = %s",
            name,
        )
        for fname in file_names:
            try:
                frappe.delete_doc("File", fname, ignore_permissions=True, force=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("Part Diagram", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    print(f"  -> {len(names)} Part Diagram records removed")


def _delete_parts_groups():
    print("[3/4] Deleting Parts Group records...")
    if not frappe.db.table_exists("Parts Group"):
        print("  -> Parts Group table not found; skipping")
        return
    names = frappe.db.sql_list("SELECT name FROM `tabParts Group`")
    for name in names:
        try:
            frappe.delete_doc("Parts Group", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    print(f"  -> {len(names)} Parts Group records removed")


def _drop_tables():
    print("[4/4] Dropping obsolete tables...")
    tables = ["tabPart Catalog Diagram", "tabPart Diagram", "tabParts Group"]
    for table in tables:
        exists = frappe.db.sql(
            f"SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            table,
        )
        if exists:
            frappe.db.sql_ddl(f"DROP TABLE `{table}`")
            print(f"  -> dropped {table}")
        else:
            print(f"  -> {table} already gone")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Remove Diagram Feature")
    print("=" * 60)

    _delete_child_table_rows()
    _delete_part_diagrams()
    _delete_parts_groups()
    _drop_tables()
    frappe.db.commit()

    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
