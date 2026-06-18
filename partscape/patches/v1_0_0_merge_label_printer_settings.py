"""
PartScape Patch — Merge Label Printer Settings into PartScape Settings.

Copies the existing default_label_size value from the legacy
Label Printer Settings single DocType into PartScape Settings.
The Label Printer Settings DocType is removed in the same release.
"""

import frappe


def execute():
    if not frappe.db.table_exists("Label Printer Settings"):
        print("Label Printer Settings table not found; nothing to migrate")
        return

    legacy_value = frappe.db.get_single_value("Label Printer Settings", "default_label_size")
    if not legacy_value:
        print("No default_label_size in Label Printer Settings; nothing to migrate")
        return

    settings = frappe.get_doc("PartScape Settings", "PartScape Settings")
    if not settings.default_label_size:
        settings.default_label_size = legacy_value
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Migrated default_label_size: {legacy_value}")
    else:
        print(f"PartScape Settings already has default_label_size: {settings.default_label_size}; skipping migration")
