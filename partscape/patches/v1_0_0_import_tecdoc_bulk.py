"""
PartScape — TecDoc 1Q2019 Bulk Importer

Source: /tmp/tecdoc1q2019 (cloned from tecdocSQL/tecdocdatabase1Q2019)
Records: 6.7M articles, 24.4M OEM numbers, 705 suppliers
Method: Bulk SQL INSERT for speed (bypasses Frappe controllers)

Imports:
- Suppliers → Supplier
- Articles → Part Catalog (bulk insert)
- OEM Numbers → Part Supplier Reference
"""

import csv
import os

import frappe

TECDOC_DIR = "/tmp/tecdoc1q2019"
BATCH_SIZE = 5000


def _get_existing_part_numbers() -> set:
    """Load existing part numbers into memory for deduplication."""
    print("  Loading existing part numbers...")
    existing = set()
    # Use SQL for speed
    rows = frappe.db.sql("SELECT part_number FROM `tabPart Catalog`", as_list=True)
    for row in rows:
        if row[0]:
            existing.add(row[0].strip().upper())
    print(f"  → {len(existing)} existing parts loaded")
    return existing


def _load_supplier_map() -> dict:
    """Load TecDoc supplier_id → supplier_name mapping."""
    supplier_map = {}
    with open(os.path.join(TECDOC_DIR, "suppliers.csv"), "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) >= 7:
                supplier_id = fields[0].strip()
                supplier_name = fields[3].strip() if fields[3] else fields[6].strip()
                supplier_map[supplier_id] = supplier_name
    return supplier_map


def _load_product_map() -> dict:
    """Load TecDoc product_id → category name mapping."""
    product_map = {}
    with open(os.path.join(TECDOC_DIR, "products.csv"), "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) >= 5:
                product_id = fields[0].strip()
                category_name = fields[2].strip() if fields[2] else fields[4].strip()
                product_map[product_id] = category_name
    return product_map


def _ensure_suppliers(supplier_map: dict) -> dict:
    """Create Frappe Supplier docs for TecDoc suppliers. Returns id→docname."""
    print("\n[1/4] Creating suppliers...")
    id_to_docname = {}
    group = frappe.db.get_value("Supplier Group", {}, "name") or "All Supplier Groups"

    for supplier_id, supplier_name in supplier_map.items():
        existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
        if existing:
            id_to_docname[supplier_id] = existing
        else:
            try:
                doc = frappe.get_doc({
                    "doctype": "Supplier",
                    "supplier_name": supplier_name,
                    "supplier_group": group,
                })
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                id_to_docname[supplier_id] = doc.name
            except Exception:
                id_to_docname[supplier_id] = supplier_name

    frappe.db.commit()
    print(f"  → {len(id_to_docname)} suppliers ready")
    return id_to_docname


def _ensure_categories(product_map: dict) -> dict:
    """Create Part Category docs. Returns name→docname."""
    print("\n[2/4] Creating categories...")
    name_to_docname = {}
    unique_categories = set(product_map.values())

    for cat_name in unique_categories:
        if not cat_name:
            continue
        existing = frappe.db.get_value("Part Category", {"category_name": cat_name}, "name")
        if existing:
            name_to_docname[cat_name] = existing
        else:
            try:
                doc = frappe.get_doc({
                    "doctype": "Part Category",
                    "category_name": cat_name,
                })
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                name_to_docname[cat_name] = doc.name
            except Exception:
                name_to_docname[cat_name] = cat_name

    frappe.db.commit()
    print(f"  → {len(name_to_docname)} categories ready")
    return name_to_docname


def import_articles() -> int:
    """Bulk import TecDoc articles into Part Catalog."""
    print("\n[3/4] Importing articles (bulk SQL)...")
    existing_parts = _get_existing_part_numbers()
    supplier_map = _load_supplier_map()
    product_map = _load_product_map()
    supplier_id_to_docname = _ensure_suppliers(supplier_map)
    category_name_to_docname = _ensure_categories(product_map)

    articles_file = os.path.join(TECDOC_DIR, "articles.csv")
    total_imported = 0
    total_skipped = 0
    batch = []
    batch_count = 0

    print(f"  Processing {articles_file}...")

    with open(articles_file, "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) < 22:
                continue

            article_id = fields[0].strip()
            part_number = fields[1].strip()
            supplier_id = fields[2].strip()
            product_id = fields[3].strip()
            description = fields[4].strip() if fields[4] else ""
            is_valid = fields[19].strip() if len(fields) > 19 else "1"

            if not part_number or is_valid != "1":
                continue

            # Deduplicate
            if part_number.upper() in existing_parts:
                total_skipped += 1
                continue

            # Get supplier and category
            supplier_name = supplier_map.get(supplier_id, "TecDoc")
            category_name = product_map.get(product_id, "General")
            category_docname = category_name_to_docname.get(category_name, "General")

            # Clean part number
            clean_pn = part_number.replace("'", "''")[:50]
            clean_desc = (description or part_number).replace("'", "''")[:200]
            clean_name = (description or part_number).replace("'", "''")[:100]

            batch.append((
                clean_pn,
                clean_name,
                clean_desc,
                supplier_name.replace("'", "''"),
                category_docname.replace("'", "''"),
            ))

            if len(batch) >= BATCH_SIZE:
                _insert_article_batch(batch)
                total_imported += len(batch)
                batch = []
                batch_count += 1
                if batch_count % 10 == 0:
                    frappe.db.commit()
                    print(f"    → {total_imported} imported, {total_skipped} skipped")

    # Insert remaining
    if batch:
        _insert_article_batch(batch)
        total_imported += len(batch)

    frappe.db.commit()
    print(f"  → {total_imported} articles imported, {total_skipped} skipped")
    return total_imported


def _insert_article_batch(batch: list):
    """Insert a batch of articles via raw SQL."""
    if not batch:
        return

    from frappe.utils import now
    now_str = now()
    user = "Administrator"

    values_list = []
    for pn, name, desc, brand, cat in batch:
        name_hash = frappe.generate_hash()[:10]
        values_list.append(
            f"('{name_hash}', '{now_str}', '{now_str}', '{user}', '{user}', 0, 0, '{brand}', '{pn}', '{name}', NULL, 0, '{cat}', '{desc}', NULL, NULL, NULL, NULL, 'Universal', NULL, 1, NULL)"
        )

    values = ", ".join(values_list)

    sql = f"""
        INSERT IGNORE INTO `tabPart Catalog`
        (name, creation, modified, modified_by, owner, docstatus, idx, brand, part_number, part_name, vehicle_make, is_oem, category, description, diagram_reference, weight_kg, dimensions, estimated_cost_usd, steering_position, market_restriction, is_active, images)
        VALUES {values}
    """
    frappe.db.sql(sql)


def import_oe_numbers() -> int:
    """Bulk import TecDoc OEM numbers as supplier references."""
    print("\n[4/4] Importing OEM numbers (bulk SQL)...")

    # Build article_id → part_number mapping
    article_to_pn = {}
    with open(os.path.join(TECDOC_DIR, "articles.csv"), "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) >= 2:
                article_id = fields[0].strip()
                part_number = fields[1].strip()
                if article_id and part_number:
                    article_to_pn[article_id] = part_number

    # Get existing supplier refs to avoid duplicates
    print("  Loading existing supplier references...")
    existing_refs = set()
    rows = frappe.db.sql("SELECT part_catalog, supplier_part_number FROM `tabPart Supplier Reference`", as_list=True)
    for row in rows:
        if row[0] and row[1]:
            existing_refs.add((row[0].strip(), row[1].strip()))
    print(f"  → {len(existing_refs)} existing refs loaded")

    oe_file = os.path.join(TECDOC_DIR, "article_oe_numbers.csv")
    total_imported = 0
    total_skipped = 0
    batch = []
    batch_count = 0

    print(f"  Processing {oe_file}...")

    with open(oe_file, "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) < 4:
                continue

            article_id = fields[0].strip()
            oe_number = fields[1].strip()

            if not article_id or not oe_number:
                continue

            part_number = article_to_pn.get(article_id)
            if not part_number:
                continue

            # Check if this ref already exists
            if (part_number, oe_number) in existing_refs:
                total_skipped += 1
                continue

            clean_pn = part_number.replace("'", "''")[:50]
            clean_oe = oe_number.replace("'", "''")[:50]

            batch.append((clean_pn, "TecDoc OEM", clean_oe))

            if len(batch) >= BATCH_SIZE:
                _insert_oe_batch(batch)
                total_imported += len(batch)
                batch = []
                batch_count += 1
                if batch_count % 100 == 0:
                    frappe.db.commit()
                    print(f"    → {total_imported} imported, {total_skipped} skipped")

    if batch:
        _insert_oe_batch(batch)
        total_imported += len(batch)

    frappe.db.commit()
    print(f"  → {total_imported} OEM refs imported, {total_skipped} skipped")
    return total_imported


def _insert_oe_batch(batch: list):
    """Insert a batch of OEM references via raw SQL."""
    if not batch:
        return

    from frappe.utils import now
    now_str = now()
    user = "Administrator"

    values_list = []
    for pn, supp, oe in batch:
        name_hash = frappe.generate_hash()[:10]
        values_list.append(
            f"('{name_hash}', '{now_str}', '{now_str}', '{user}', '{user}', 0, 0, '{pn}', '{supp}', '{oe}', 1, 7, 0.00, 'USD')"
        )

    values = ", ".join(values_list)

    sql = f"""
        INSERT IGNORE INTO `tabPart Supplier Reference`
        (name, creation, modified, modified_by, owner, docstatus, idx, part_catalog, supplier, supplier_part_number, moq, lead_time_days, unit_cost_usd, currency)
        VALUES {values}
    """
    frappe.db.sql(sql)


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — TecDoc 1Q2019 Bulk Importer")
    print("=" * 60)

    if not os.path.exists(os.path.join(TECDOC_DIR, "articles.csv")):
        print(f"ERROR: TecDoc data not found at {TECDOC_DIR}")
        return

    article_count = import_articles()
    oe_count = import_oe_numbers()

    print("\n" + "=" * 60)
    print("TECDOC IMPORT COMPLETE")
    print("=" * 60)
    print(f"Articles imported:      {article_count}")
    print(f"OEM references:         {oe_count}")
    print("=" * 60)
