"""
PartScape Patch — Clean up obsolete Part Catalog columns and custom fields.

Fields removed from the DocType / fixtures earlier but whose DB columns / custom
field docs survived because Frappe does not auto-delete custom fields that are
removed from fixtures, and because prior migrations failed part-way through.

This patch:
  1. Deletes leftover `diagram_reference` Custom Field docs on transactional
     child tables (Sales Order Item, Delivery Note Item, etc.).
  2. Drops the obsolete `diagram_reference` and `superseded_by` columns from
     `tabPart Catalog` if they still exist.

Idempotent: safe to re-run.
"""

import frappe


CUSTOM_FIELD_DOCTYPES = [
    "Sales Order Item",
    "Delivery Note Item",
    "Sales Invoice Item",
    "Purchase Order Item",
    "Purchase Receipt Item",
    "Purchase Invoice Item",
]


def _delete_diagram_reference_custom_fields():
    print("[1/2] Deleting leftover diagram_reference Custom Field docs...")
    deleted = 0
    for dt in CUSTOM_FIELD_DOCTYPES:
        name = f"{dt}-diagram_reference"
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
            deleted += 1
    frappe.db.commit()
    print(f"  -> {deleted} Custom Field docs deleted")


def _drop_obsolete_columns():
    print("[2/2] Dropping obsolete Part Catalog columns...")
    columns = {c["Field"].lower() for c in frappe.db.sql("SHOW COLUMNS FROM `tabPart Catalog`", as_dict=True)}
    dropped = []

    for col in ("diagram_reference", "superseded_by"):
        if col in columns:
            frappe.db.sql_ddl(f"ALTER TABLE `tabPart Catalog` DROP COLUMN `{col}`")
            dropped.append(col)

    frappe.db.commit()
    print(f"  -> dropped columns: {dropped if dropped else 'none'}")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Clean up obsolete Part Catalog columns")
    print("=" * 60)

    _delete_diagram_reference_custom_fields()
    _drop_obsolete_columns()

    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
