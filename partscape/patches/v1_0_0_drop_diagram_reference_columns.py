"""
PartScape Patch — Drop orphaned diagram_reference columns from transactional
child tables.

The Custom Field docs were removed via fixture sync / force-delete, but the
underlying DB columns were left behind. This patch drops them cleanly.
"""

import frappe


TABLES = [
    "tabSales Order Item",
    "tabDelivery Note Item",
    "tabSales Invoice Item",
    "tabPurchase Order Item",
    "tabPurchase Receipt Item",
    "tabPurchase Invoice Item",
]


def execute():
    print("Dropping orphaned diagram_reference columns...")
    dropped = 0
    for table in TABLES:
        columns = {c["Field"].lower() for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`", as_dict=True)}
        if "diagram_reference" in columns:
            frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `diagram_reference`")
            print(f"  -> dropped from {table}")
            dropped += 1
    frappe.db.commit()
    print(f"Done. Dropped {dropped} orphaned columns.")
