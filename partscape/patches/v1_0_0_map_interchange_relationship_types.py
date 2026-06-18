"""
PartScape Patch — Normalize Part Catalog Interchange relationship types.

Legacy values from the old pairwise interchange model and TecDoc imports
(New Number, Replacement, OEM Equivalent) are mapped to the current options.
"""

import frappe


RELATIONSHIP_MAP = {
    "New Number": "Superseded By",
    "Replacement": "Equivalent",
    "OEM Equivalent": "Equivalent",
}


def execute():
    if not frappe.db.table_exists("Part Catalog Interchange"):
        print("Part Catalog Interchange table not found; nothing to map")
        return

    print("Mapping interchange relationship types to current options...")

    # Add a temporary index so the mapping updates are fast and short-locked.
    frappe.db.sql_ddl(
        "ALTER TABLE `tabPart Catalog Interchange` "
        "ADD INDEX idx_part_catalog_interchange_relationship (relationship_type)"
    )

    total_updated = 0
    for old_value, new_value in RELATIONSHIP_MAP.items():
        frappe.db.sql(
            "UPDATE `tabPart Catalog Interchange` SET relationship_type = %s "
            "WHERE relationship_type = %s",
            (new_value, old_value),
        )
        updated = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
        frappe.db.commit()
        total_updated += updated
        print(f"  -> mapped {old_value} -> {new_value}: {updated} rows")

    # Drop the temporary index.
    frappe.db.sql_ddl(
        "ALTER TABLE `tabPart Catalog Interchange` "
        "DROP INDEX idx_part_catalog_interchange_relationship"
    )

    print(f"Total rows updated: {total_updated}")
