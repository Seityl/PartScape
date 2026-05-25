"""
PartScape — TecDoc Image Linker

Links available TecDoc product images to Part Catalog entries.

Data sources:
  - /tmp/tecdoc1q2019/images/           (26,410 JPG files)
  - /tmp/tecdoc1q2019/articles.csv      (article_id → part_number, supplier_id)
  - /tmp/tecdoc1q2019/article_mediainformation.csv  (Picture references)

Approach:
  1. Scan images/ directory into an in-memory set.
  2. Load Part Catalog part_numbers into memory for O(1) lookups.
  3. Load articles.csv into article_id → (part_number, supplier_id).
  4. Scan mediainformation.csv once; for Picture records with existing files,
     look up Part Catalog in memory and attach the image via fast file-copy
     + bulk SQL inserts for `tabFile`.
  5. Batch commit every 100 images.
"""

import os
import shutil

import frappe
from frappe.utils import now

TECDOC_DIR = "/tmp/tecdoc1q2019"
IMAGES_DIR = os.path.join(TECDOC_DIR, "images")
BATCH_COMMIT = 100


def _build_available_images() -> set:
    """Build a set of relative image paths: images/{supplier_id}/{c1}/{c2}/{filename}"""
    print("[1/4] Scanning available images...")
    available = set()
    for root, _dirs, files in os.walk(IMAGES_DIR):
        for fname in files:
            if not fname.upper().endswith(".JPG"):
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, TECDOC_DIR).replace(os.sep, "/")
            available.add(rel_path)
    print(f"  → {len(available)} JPG files found")
    return available


def _build_catalog_map() -> dict:
    """Load Part Catalog: part_number -> name (first match only)."""
    print("[2/4] Loading Part Catalog map...")
    catalog_map = {}
    rows = frappe.db.sql("SELECT part_number, name FROM `tabPart Catalog`", as_list=True)
    for pn, name in rows:
        if pn and pn.strip():
            catalog_map.setdefault(pn.strip(), name)
    print(f"  → {len(catalog_map)} part numbers loaded")
    return catalog_map


def _build_article_map() -> dict:
    """Load articles.csv: article_id -> (part_number, supplier_id)"""
    print("[3/4] Loading article map...")
    article_map = {}
    articles_file = os.path.join(TECDOC_DIR, "articles.csv")
    with open(articles_file, "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split("\t")
            if len(fields) < 3:
                continue
            article_id = fields[0].strip()
            part_number = fields[1].strip()
            supplier_id = fields[2].strip()
            if article_id and part_number and supplier_id:
                article_map[article_id] = (part_number, supplier_id)
    print(f"  → {len(article_map)} articles loaded")
    return article_map


def _insert_file_batch(batch: list):
    """Bulk insert File docs via raw SQL."""
    if not batch:
        return
    now_str = now()
    user = "Administrator"
    values_list = []
    for row in batch:
        name_hash, pic_name, file_url, catalog_name, file_size = row
        safe_pic = pic_name.replace("'", "''")
        safe_url = file_url.replace("'", "''")
        safe_cat = catalog_name.replace("'", "''")
        values_list.append(
            f"('{name_hash}', '{now_str}', '{now_str}', '{user}', '{user}', "
            f"0, 0, '{safe_pic}', '{safe_url}', '{safe_cat}', "
            f"{file_size}, 'Part Catalog', 0, '', 'Home')"
        )
    values = ", ".join(values_list)
    sql = f"""
        INSERT INTO `tabFile`
        (name, creation, modified, modified_by, owner, docstatus, idx,
         file_name, file_url, attached_to_name, file_size,
         attached_to_doctype, is_private, content_hash, folder)
        VALUES {values}
    """
    frappe.db.sql(sql)


def _link_images(available_images: set, catalog_map: dict, article_map: dict):
    """Scan mediainformation.csv and attach matching images."""
    print("[4/4] Linking images to Part Catalog...")

    files_path = frappe.get_site_path("public", "files")
    media_file = os.path.join(TECDOC_DIR, "article_mediainformation.csv")

    # Pre-load catalog entries that already have images to avoid per-row DB calls
    print("  Loading existing image assignments...")
    catalog_with_images = set()
    rows = frappe.db.sql(
        "SELECT name FROM `tabPart Catalog` WHERE images IS NOT NULL AND images != ''",
        as_list=True,
    )
    for row in rows:
        if row[0]:
            catalog_with_images.add(row[0])
    print(f"    → {len(catalog_with_images)} parts already have images")

    total_checked = 0
    total_matched = 0
    total_linked = 0
    total_skipped_no_catalog = 0
    total_skipped_has_image = 0
    file_batch = []

    with open(media_file, "r", encoding="utf-8") as f:
        for line in f:
            fields = line.strip().split("\t")
            if len(fields) < 10:
                continue

            article_id = fields[0].strip()
            doc_type = fields[1].strip()
            picture_name = fields[8].strip() if len(fields) > 8 else ""

            if doc_type != "Picture" or not picture_name:
                continue

            total_checked += 1

            article_data = article_map.get(article_id)
            if not article_data:
                continue

            part_number, supplier_id = article_data
            pic_upper = picture_name.upper()

            if len(pic_upper) < 2:
                continue

            rel_path = f"images/{supplier_id}/{pic_upper[0]}/{pic_upper[1]}/{pic_upper}"

            if rel_path not in available_images:
                continue

            total_matched += 1

            catalog_name = catalog_map.get(part_number)
            if not catalog_name:
                total_skipped_no_catalog += 1
                continue

            # Skip if already has an image
            if catalog_name in catalog_with_images:
                total_skipped_has_image += 1
                continue

            # Copy file to site public files
            abs_src = os.path.join(TECDOC_DIR, rel_path)
            unique_fname = f"{frappe.generate_hash()[:10]}_{pic_upper}"
            abs_dst = os.path.join(files_path, unique_fname)
            try:
                shutil.copy2(abs_src, abs_dst)
            except Exception as e:
                print(f"    ERROR copying {rel_path}: {e}")
                continue

            file_url = f"/files/{unique_fname}"
            file_size = os.path.getsize(abs_dst)
            name_hash = frappe.generate_hash()[:10]

            # Queue file doc for bulk insert
            file_batch.append((name_hash, pic_upper, file_url, catalog_name, file_size))

            # Update catalog image field immediately
            frappe.db.sql(
                "UPDATE `tabPart Catalog` SET images = %s WHERE name = %s",
                (file_url, catalog_name)
            )
            catalog_with_images.add(catalog_name)

            total_linked += 1

            if len(file_batch) >= BATCH_COMMIT:
                _insert_file_batch(file_batch)
                frappe.db.commit()
                file_batch = []
                print(
                    f"    → {total_linked} linked, "
                    f"{total_skipped_no_catalog} no-catalog, "
                    f"{total_skipped_has_image} already-has-image "
                    f"(checked {total_checked}, matched {total_matched})"
                )

    # Final batch
    if file_batch:
        _insert_file_batch(file_batch)
        frappe.db.commit()

    print(f"  → {total_linked} images linked")
    print(f"  → {total_skipped_no_catalog} skipped (no Part Catalog)")
    print(f"  → {total_skipped_has_image} skipped (already has image)")
    print(f"  → {total_matched} total image matches from {total_checked} Picture records")


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — TecDoc Image Linker")
    print("=" * 60)

    if not os.path.isdir(IMAGES_DIR):
        print(f"ERROR: Image directory not found: {IMAGES_DIR}")
        return

    available_images = _build_available_images()
    catalog_map = _build_catalog_map()
    article_map = _build_article_map()
    _link_images(available_images, catalog_map, article_map)

    print("\n" + "=" * 60)
    print("TECDOC IMAGE LINK COMPLETE")
    print("=" * 60)
