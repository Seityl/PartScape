"""
Patch: Create FULLTEXT index on Part Catalog for fast keyword search.

This index cannot be created via DocType JSON configuration,
so we apply it via a patch for new site installations.
"""

import frappe


def execute():
    table = "tabPart Catalog"
    index_name = "ft_search"

    # Check if index already exists
    existing = frappe.db.sql(
        "SELECT 1 FROM information_schema.STATISTICS WHERE table_name = %s AND index_name = %s",
        (table, index_name),
    )
    if existing:
        frappe.logger().info(f"Patch: FULLTEXT index '{index_name}' already exists on {table}")
        return

    frappe.db.sql(
        f"ALTER TABLE `{table}` ADD FULLTEXT INDEX {index_name} (part_number, part_name, brand)"
    )
    frappe.logger().info(f"Patch: Created FULLTEXT index '{index_name}' on {table}")
