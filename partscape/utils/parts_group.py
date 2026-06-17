"""
PartScape — Parts Group utilities
"""

import frappe


def ensure_parts_group(name: str) -> str:
    """Ensure a Parts Group doc exists. Returns the doc name."""
    if not name:
        return None

    name = name.strip()
    if not name:
        return None

    if not frappe.db.exists("Parts Group", name):
        doc = frappe.get_doc({
            "doctype": "Parts Group",
            "parts_group_name": name,
        })
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

    return name
