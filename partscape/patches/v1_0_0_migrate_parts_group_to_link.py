"""
PartScape Patch — Standardise Parts Group values into a new Parts Group DocType.

Converts the `parts_group` field on Part Diagram and Part Catalog Diagram from
free-text Data into a Link to Parts Group, creating records for every distinct
existing value.
"""

import frappe


def _ensure_parts_groups():
    print("Ensuring Parts Group records exist...")
    groups = set()

    for table in ("tabPart Diagram", "tabPart Catalog Diagram"):
        rows = frappe.db.sql(
            f"SELECT DISTINCT parts_group FROM `{table}` WHERE parts_group IS NOT NULL AND parts_group != ''",
            pluck=True,
        )
        groups.update(rows)

    created = 0
    for group in groups:
        if not frappe.db.exists("Parts Group", group):
            doc = frappe.get_doc({
                "doctype": "Parts Group",
                "parts_group_name": group,
            })
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            created += 1

    print(f"  -> {created} new Parts Group records created, {len(groups)} total")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Migrate Parts Group to Link")
    print("=" * 60)

    _ensure_parts_groups()

    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
