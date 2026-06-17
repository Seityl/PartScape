"""
PartScape Patch — Migrate Part Catalog field changes.

Schema changes being applied:
  - brand           : Data -> Link -> Brand
  - category        : Link -> Part Category  -> Link -> Item Group
  - market_restriction : Data -> Link -> Market
  - vehicle_make    : renamed to oem_make
  - diagram_reference : removed

This patch:
  1. Ensures a Brand doc exists for every unique brand value and re-links.
  2. Converts existing category values (Part Category docnames) to their mapped
     Item Group values using bulk SQL updates.
  3. Ensures a Market doc exists for every unique market_restriction value and
     re-links.
  4. Renames the DB column vehicle_make -> oem_make so existing data is preserved.

The patch is idempotent: re-running it will not break already-migrated rows.
"""

import frappe


DEFAULT_ITEM_GROUP = "Auto Parts"


def _get_fallback_item_group() -> str:
    if frappe.db.exists("Item Group", DEFAULT_ITEM_GROUP):
        return DEFAULT_ITEM_GROUP
    fallback = frappe.db.get_value("Item Group", {}, "name")
    return fallback


def _map_category_to_item_group(category_name: str) -> str:
    """Best-effort mapping from an old Part Category name to an Item Group."""
    if not category_name:
        return None

    # Already an Item Group?
    if frappe.db.exists("Item Group", category_name):
        return category_name

    # Use the explicit mapping on the Part Category doc, if present.
    item_group = frappe.db.get_value("Part Category", category_name, "item_group")
    if item_group:
        return item_group

    # Fall back to the keyword-based mapper.
    try:
        from partscape.utils.category_mapper import map_category_to_item_group

        mapped = map_category_to_item_group(category_name)
        if mapped and frappe.db.exists("Item Group", mapped):
            return mapped
    except Exception:
        pass

    return None


def _migrate_brands():
    print("[1/4] Ensuring Brand docs for Part Catalog brands...")
    brands = frappe.db.sql(
        "SELECT DISTINCT brand FROM `tabPart Catalog` WHERE brand IS NOT NULL AND brand != ''",
        pluck=True,
    )
    created = 0
    for brand in brands:
        if not frappe.db.exists("Brand", brand):
            doc = frappe.get_doc({"doctype": "Brand", "brand": brand})
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            created += 1
    print(f"  -> {created} new Brand docs created, {len(brands)} total brands linked")


def _migrate_categories():
    print("[2/4] Mapping Part Catalog categories to Item Groups...")

    if not frappe.db.table_exists("Part Category"):
        print("  -> Part Category table not found; skipping category migration")
        return

    fallback = _get_fallback_item_group()

    # 1. Bulk-remap rows whose current category matches a Part Category with an
    #    explicit item_group mapping. This handles the vast majority of rows in
    #    a single statement and avoids thousands of per-value table scans.
    frappe.db.sql(
        """
        UPDATE `tabPart Catalog` pc
        JOIN `tabPart Category` pcat ON pc.category = pcat.name
        SET pc.category = pcat.item_group
        WHERE pcat.item_group IS NOT NULL AND pcat.item_group != ''
          AND pc.category != pcat.item_group
        """
    )
    frappe.db.commit()
    print("  -> bulk-mapped categories via Part Category.item_group linkage")

    # 2. Bulk-update any categories that still don't resolve to an Item Group
    #    to the fallback Item Group. The prior bulk remap already covered every
    #    Part Category with an explicit item_group mapping; the few leftovers
    #    (typos, synthetic labels, unmapped keywords) are collapsed to a valid
    #    Item Group in one statement instead of thousands of per-value updates.
    before = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT pc.category)
        FROM `tabPart Catalog` pc
        LEFT JOIN `tabItem Group` ig ON ig.name = pc.category
        WHERE pc.category IS NOT NULL AND pc.category != ''
          AND ig.name IS NULL
        """,
        pluck=True,
    )[0]

    if before:
        frappe.db.sql(
            """
            UPDATE `tabPart Catalog` pc
            LEFT JOIN `tabItem Group` ig ON ig.name = pc.category
            SET pc.category = %s
            WHERE pc.category IS NOT NULL AND pc.category != ''
              AND ig.name IS NULL
            """,
            (fallback,),
        )
        frappe.db.commit()
        print(f"  -> {before} remaining distinct categories collapsed to fallback '{fallback}'")
    else:
        print("  -> no remaining unmapped categories")


def _migrate_markets():
    print("[3/4] Ensuring Market docs for Part Catalog market restrictions...")
    markets = frappe.db.sql(
        """
        SELECT DISTINCT market_restriction
        FROM `tabPart Catalog`
        WHERE market_restriction IS NOT NULL AND market_restriction != ''
        """,
        pluck=True,
    )
    created = 0
    for market_code in markets:
        if not frappe.db.exists("Market", market_code):
            doc = frappe.get_doc({
                "doctype": "Market",
                "market_code": market_code,
                "market_name": market_code,
            })
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            created += 1
    print(f"  -> {created} new Market docs created, {len(markets)} total markets linked")


def _verify_oem_make_rename():
    print("[4/4] Verifying vehicle_make -> oem_make rename...")

    # Frappe DocType sync does not automatically rename DB columns when a
    # fieldname changes; it adds the new column and leaves the old one. We use
    # a direct DDL rename so existing data is preserved.
    columns = {c["Field"].lower() for c in frappe.db.sql("SHOW COLUMNS FROM `tabPart Catalog`", as_dict=True)}

    if "oem_make" in columns and "vehicle_make" in columns:
        # The new empty column was added by the DocType sync. Drop it, then
        # rename the old column so existing values are preserved.
        frappe.db.sql_ddl("ALTER TABLE `tabPart Catalog` DROP COLUMN `oem_make`")
        frappe.db.rename_column("Part Catalog", "vehicle_make", "oem_make")
        print("  -> renamed vehicle_make column to oem_make (preserved existing data)")
    elif "vehicle_make" in columns:
        frappe.db.rename_column("Part Catalog", "vehicle_make", "oem_make")
        print("  -> renamed vehicle_make column to oem_make (preserved existing data)")
    elif "oem_make" in columns:
        print("  -> oem_make column already present; nothing to rename")
    else:
        print("  -> neither vehicle_make nor oem_make column found; nothing to do")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Migrate Part Catalog Link Fields")
    print("=" * 60)

    _migrate_brands()
    _migrate_categories()
    _migrate_markets()
    _verify_oem_make_rename()

    frappe.db.commit()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
