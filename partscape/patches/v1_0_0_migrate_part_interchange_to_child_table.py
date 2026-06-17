"""
PartScape Patch — Migrate Part Interchange pairs to Part Catalog child-table rows.

The old pairwise Part Interchange DocType is replaced by a child table on
Part Catalog. This patch copies every A-B edge into two child-table rows
(A->B and B->A) so each part lists its alternates directly.
"""

import frappe
from frappe.utils import now


BATCH_SIZE = 10000


def _row_value(row, field):
    val = row.get(field)
    if val is None:
        return "NULL"
    if field == "confidence_score":
        try:
            return str(float(val))
        except (ValueError, TypeError):
            return "NULL"
    return "'" + str(val).replace("'", "''") + "'"


def _insert_batch(rows, now_str, user):
    if not rows:
        return 0

    value_tuples = []
    for row in rows:
        # Forward row: parent = part_a, part = part_b
        value_tuples.append(
            f"('{frappe.generate_hash()[:10]}', '{now_str}', '{now_str}', '{user}', '{user}', "
            f"0, 0, {_row_value(row, 'part_a')}, 'interchanges', 'Part Catalog', "
            f"{_row_value(row, 'part_b')}, {_row_value(row, 'relationship_type')}, "
            f"{_row_value(row, 'quality_tier')}, {_row_value(row, 'confidence_score')}, "
            f"{_row_value(row, 'source')})"
        )
        # Reverse row: parent = part_b, part = part_a
        value_tuples.append(
            f"('{frappe.generate_hash()[:10]}', '{now_str}', '{now_str}', '{user}', '{user}', "
            f"0, 0, {_row_value(row, 'part_b')}, 'interchanges', 'Part Catalog', "
            f"{_row_value(row, 'part_a')}, {_row_value(row, 'relationship_type')}, "
            f"{_row_value(row, 'quality_tier')}, {_row_value(row, 'confidence_score')}, "
            f"{_row_value(row, 'source')})"
        )

    values = ", ".join(value_tuples)
    sql = f"""
        INSERT INTO `tabPart Catalog Interchange`
        (name, creation, modified, modified_by, owner, docstatus, idx,
         parent, parentfield, parenttype, part,
         relationship_type, quality_tier, confidence_score, source)
        VALUES {values}
    """
    frappe.db.sql(sql)
    return len(rows)


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Migrate Part Interchange to Child Table")
    print("=" * 60)

    if not frappe.db.table_exists("Part Interchange"):
        print("Part Interchange table not found; nothing to migrate")
        _cleanup_old_doctype()
        return

    total = frappe.db.count("Part Interchange")
    print(f"Found {total} Part Interchange rows to migrate")

    # Ensure a clean target table in case the patch is re-run.
    if frappe.db.table_exists("tabPart Catalog Interchange"):
        frappe.db.sql_ddl("TRUNCATE TABLE `tabPart Catalog Interchange`")
        print("Cleared existing Part Catalog Interchange rows")

    now_str = now()
    user = "Administrator"
    migrated = 0
    offset = 0

    while True:
        rows = frappe.db.sql(
            """
            SELECT part_a, part_b, relationship_type, quality_tier,
                   confidence_score, source
            FROM `tabPart Interchange`
            ORDER BY name
            LIMIT %s OFFSET %s
            """,
            (BATCH_SIZE, offset),
            as_dict=True,
        )
        if not rows:
            break

        count = _insert_batch(rows, now_str, user)
        migrated += count
        offset += BATCH_SIZE
        frappe.db.commit()
        print(f"  -> migrated batch: {migrated} edges ({migrated * 2} child rows)")

    print(f"Total edges migrated: {migrated}")

    _cleanup_old_doctype()
    frappe.db.commit()

    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


def _cleanup_old_doctype():
    print("\nCleaning up old Part Interchange artifacts...")

    if frappe.db.table_exists("Part Interchange"):
        frappe.db.sql_ddl("DROP TABLE `tabPart Interchange`")
        print("  -> dropped tabPart Interchange")

    if frappe.db.exists("DocType", "Part Interchange"):
        frappe.delete_doc("DocType", "Part Interchange", ignore_permissions=True, force=True)
        print("  -> removed Part Interchange DocType")
