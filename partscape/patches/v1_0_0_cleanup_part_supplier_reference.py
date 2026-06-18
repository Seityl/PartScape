"""
PartScape Patch — Clean up Part Supplier Reference.

- Deduplicate rows by (part_catalog, supplier, supplier_part_number).
- Enforce a unique constraint on that tuple.

This patch is resumable: if it dies after the INSERT but before the
DROP/RENAME, rerunning it will detect the populated temp table and
complete the swap.
"""

import frappe


def execute():
    table = "`tabPart Supplier Reference`"
    temp = "`tabPart Supplier Reference Dedup`"

    if not frappe.db.table_exists("Part Supplier Reference"):
        print("Part Supplier Reference table not found; skipping")
        return

    print("=" * 60)
    print("PartScape — Clean up Part Supplier Reference")
    print("=" * 60)

    # Resume path: temp table exists with data and original still exists.
    # Use cached=False so a stale client cache doesn't misreport existence.
    if frappe.db.table_exists("Part Supplier Reference Dedup", cached=False):
        temp_count = frappe.db.sql(f"SELECT COUNT(*) FROM {temp}")[0][0]
        original_count = frappe.db.count("Part Supplier Reference")
        if temp_count > 0:
            print(f"[resume] temp table has {temp_count} rows; original has {original_count}")
            print(f"[resume] completing table swap...")
            _swap_tables(table, temp)
            print("=" * 60)
            print("CLEANUP COMPLETE (resumed)")
            print("=" * 60)
            return
        else:
            print("[resume] temp table is empty; dropping and starting fresh")
            frappe.db.sql_ddl(f"DROP TABLE IF EXISTS {temp}")

    # Deduplicate via temp table with unique index.
    print("[1/3] Creating temp table with unique index...")
    frappe.db.sql_ddl(f"CREATE TABLE {temp} LIKE {table}")

    # CREATE TABLE ... LIKE copies indexes from the original table. If the
    # original already has ux_psr (e.g., patch was run before), skip re-adding.
    existing_indexes = {row[2] for row in frappe.db.sql(f"SHOW INDEX FROM {temp}")}
    if "ux_psr" not in existing_indexes:
        frappe.db.sql_ddl(
            f"ALTER TABLE {temp} ADD UNIQUE INDEX ux_psr ("
            f"part_catalog, supplier, supplier_part_number)"
        )

    print("[2/3] Deduplicating Part Supplier Reference rows...")
    original_count = frappe.db.count("Part Supplier Reference")
    print(f"  -> original rows: {original_count}")

    frappe.db.sql(f"INSERT IGNORE INTO {temp} SELECT * FROM {table} ORDER BY name")

    new_count = frappe.db.sql(f"SELECT COUNT(*) FROM {temp}")[0][0]
    print(f"  -> deduplicated rows: {new_count} (removed {original_count - new_count})")

    # Commit the heavy INSERT so progress is preserved if the process dies here.
    frappe.db.commit()
    print("  -> committed deduplicated data to temp table")

    print("[3/3] Swapping tables...")
    _swap_tables(table, temp)

    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)


def _swap_tables(table, temp):
    frappe.db.sql_ddl(f"DROP TABLE {table}")
    frappe.db.sql_ddl(f"RENAME TABLE {temp} TO {table}")

    # Verify unique index survived the rename.
    existing_indexes = {row[2] for row in frappe.db.sql(f"SHOW INDEX FROM {table}")}
    if "ux_psr" not in existing_indexes:
        frappe.db.sql_ddl(
            f"ALTER TABLE {table} ADD UNIQUE INDEX ux_psr ("
            f"part_catalog, supplier, supplier_part_number)"
        )
        print("  -> re-added unique index after rename")

    frappe.db.commit()
