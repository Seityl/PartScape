"""
PartScape — TecDoc association importer (sample data).

Downloads the freely available TecDoc CSV slices from GitHub and rebuilds:
  - Vehicle Part Applicability (from articles_linkages.csv)
  - Part Interchange (from article_new_numbers.csv, article_replace_numbers.csv,
    article_cross_list.csv)

Source repositories:
  https://github.com/tecdocSQL/tecdocdatabase1Q2019
  https://github.com/tecdocSQL/tecdocdatabase2Q2018

Note: these GitHub repos contain sample-sized files, not the full TecDoc DVD.
The importer is written so the same code can be pointed at a full dump later.

Matching strategy:
  - Most Part Catalog records were imported with brand="TecDoc" because of a
    supplier-id mapping bug in the original TecDoc importer. Therefore
    associations are matched by part_number, preferring the TecDoc-branded
    catalog entry when duplicates exist.
  - Vehicle models are matched fuzzily because the PartScape vehicle master
    comes from NHTSA/US Car data while TecDoc uses its own model descriptions.
"""

import os
import re
import requests
import frappe
from frappe.utils import now


DATA_DIR = "/tmp/tecdoc_associations"
BATCH_SIZE = 5000

REPOS = {
    "1q2019": "https://raw.githubusercontent.com/tecdocSQL/tecdocdatabase1Q2019/main",
    "2q2018": "https://raw.githubusercontent.com/tecdocSQL/tecdocdatabase2Q2018/main",
}

SMALL_FILES = [
    ("1q2019", "suppliers.csv"),
    ("1q2019", "models.csv"),
    ("1q2019", "manufacturers.csv"),
    ("1q2019", "passengercars.csv"),
    ("1q2019", "commercialvehicles.csv"),
    ("1q2019", "motorbikes.csv"),
    ("1q2019", "engines.csv"),
    ("1q2019", "axles.csv"),
    ("1q2019", "articles_linkages.csv"),
    ("1q2019", "article_new_numbers.csv"),
    ("1q2019", "article_replace_numbers.csv"),
    ("2q2018", "article_cross_list.csv"),
]

ARTICLES_PARTS = [f"articles.csv.{i:03d}" for i in range(15)]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _download(url: str, dest: str) -> str:
    if os.path.exists(dest):
        return dest
    print(f"  downloading {os.path.basename(dest)} ...")
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return dest


def _local(repo: str, filename: str) -> str:
    return os.path.join(DATA_DIR, f"{repo}_{filename}")


def download_small_files():
    _ensure_dir()
    for repo, filename in SMALL_FILES:
        url = f"{REPOS[repo]}/{filename}"
        _download(url, _local(repo, filename))


def download_articles_parts():
    _ensure_dir()
    for part in ARTICLES_PARTS:
        url = f"{REPOS['1q2019']}/{part}"
        _download(url, _local("1q2019", part))


def _tsv_reader(path: str):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n\r").split("\t")


def load_supplier_map() -> dict:
    path = _local("1q2019", "suppliers.csv")
    supplier_map = {}
    for fields in _tsv_reader(path):
        if len(fields) < 7:
            continue
        supplier_id = fields[1].strip()
        brand = fields[3].strip() if fields[3].strip() else fields[6].strip()
        if supplier_id and brand:
            supplier_map[supplier_id] = brand
    return supplier_map


def _normalize_model_name(name: str) -> str:
    if not name:
        return ""
    # Remove parentheses and their contents
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Uppercase, strip, collapse spaces
    return re.sub(r"\s+", " ", name.strip()).upper()


def load_vehicle_model_map() -> dict:
    """Build a fuzzy lookup: make -> {normalized_partscape_name: vehicle_model_name}."""
    print("Loading Vehicle Model map...")
    rows = frappe.db.sql(
        "SELECT name, make, model_name FROM `tabVehicle Model`",
        as_dict=True,
    )
    model_map = {}
    for r in rows:
        make = (r.make or "").strip().upper()
        normalized = _normalize_model_name(r.model_name)
        if not make or not normalized:
            continue
        model_map.setdefault(make, {})[normalized] = r.name
    total = sum(len(v) for v in model_map.values())
    print(f"  -> {total} Vehicle Models loaded across {len(model_map)} makes")
    return model_map


def _fuzzy_match_vehicle_model(make: str, tecdoc_model: str, model_map: dict) -> str:
    make = (make or "").strip().upper()
    normalized_tecdoc = _normalize_model_name(tecdoc_model)
    if not make or not normalized_tecdoc:
        return None

    candidates = model_map.get(make, {})
    best_match = None
    best_len = 0
    for partscape_norm, model_name in candidates.items():
        if partscape_norm in normalized_tecdoc or normalized_tecdoc in partscape_norm:
            if len(partscape_norm) > best_len:
                best_len = len(partscape_norm)
                best_match = model_name
    return best_match


def load_part_catalog_map() -> dict:
    """part_number -> Part Catalog name, preferring TecDoc-branded records."""
    print("Loading Part Catalog map...")
    rows = frappe.db.sql(
        "SELECT name, brand, part_number FROM `tabPart Catalog`",
        as_dict=True,
    )
    catalog_map = {}
    for r in rows:
        pn = (r.part_number or "").strip().upper()
        if not pn:
            continue
        existing = catalog_map.get(pn)
        # Prefer the TecDoc-branded record; otherwise keep the first one seen
        if existing is None or (r.brand or "").strip().upper() == "TECDOC":
            catalog_map[pn] = r.name
    print(f"  -> {len(catalog_map)} unique part numbers loaded")
    return catalog_map


def _add_unique_indexes():
    print("Ensuring unique indexes...")
    frappe.db.sql(
        """
        ALTER TABLE `tabVehicle Part Applicability`
        ADD UNIQUE INDEX IF NOT EXISTS ux_vehicle_applicability (
            parent, vehicle_model, variant, year_start, year_end
        )
        """
    )
    frappe.db.commit()


def load_vehicle_maps() -> dict:
    """TecDoc vehicle id -> (make, model_name, year_start, year_end, description)."""
    models = {}
    for fields in _tsv_reader(_local("1q2019", "models.csv")):
        if len(fields) < 5:
            continue
        model_id = fields[0].strip()
        manufacturer_id = fields[1].strip()
        model_name = fields[4].strip()
        if model_id:
            models[model_id] = (manufacturer_id, model_name)

    manufacturers = {}
    for fields in _tsv_reader(_local("1q2019", "manufacturers.csv")):
        if len(fields) < 4:
            continue
        manufacturer_id = fields[0].strip()
        make_name = fields[3].strip()
        if manufacturer_id and make_name:
            manufacturers[manufacturer_id] = make_name

    def parse_year(date_str: str) -> int:
        if not date_str or date_str in ("0000-00-00", ""):
            return 0
        try:
            return int(date_str.split("-")[0])
        except Exception:
            return 0

    def build_car_map(path: str):
        result = {}
        for fields in _tsv_reader(path):
            if len(fields) < 6:
                continue
            car_id = fields[0].strip()
            model_id = fields[2].strip()
            from_year = parse_year(fields[5].strip())
            to_year = parse_year(fields[6].strip()) if len(fields) > 6 else 0
            description = fields[7].strip() if len(fields) > 7 else ""
            model_info = models.get(model_id)
            if not model_info:
                continue
            manufacturer_id, model_name = model_info
            make_name = manufacturers.get(manufacturer_id, "")
            if car_id and make_name and model_name:
                result[car_id] = (make_name, model_name, from_year, to_year, description)
        return result

    vehicle_maps = {
        "1": build_car_map(_local("1q2019", "passengercars.csv")),
        "2": build_car_map(_local("1q2019", "commercialvehicles.csv")),
        "3": build_car_map(_local("1q2019", "motorbikes.csv")),
        "4": {},
        "5": {},
    }

    engines = {}
    for fields in _tsv_reader(_local("1q2019", "engines.csv")):
        if len(fields) < 3:
            continue
        engine_id = fields[0].strip()
        description = fields[2].strip()
        if engine_id and description:
            engines[engine_id] = description
    vehicle_maps["4"] = engines

    axles = {}
    for fields in _tsv_reader(_local("1q2019", "axles.csv")):
        if len(fields) < 4:
            continue
        axle_id = fields[0].strip()
        description = fields[2].strip()
        if axle_id and description:
            axles[axle_id] = description
    vehicle_maps["5"] = axles

    return vehicle_maps


def import_vehicle_part_applicability(catalog_map: dict, model_map: dict, vehicle_maps: dict) -> int:
    print("\n[1/2] Importing Vehicle Part Applicability...")
    path = _local("1q2019", "articles_linkages.csv")
    total_imported = 0
    total_skipped = 0
    batch = []

    for fields in _tsv_reader(path):
        if len(fields) < 6:
            continue
        item_type = fields[0].strip()
        item_id = fields[1].strip()
        article_number = fields[4].strip().upper()

        part_catalog = catalog_map.get(article_number)
        if not part_catalog:
            total_skipped += 1
            continue

        vehicle_info = vehicle_maps.get(item_type, {}).get(item_id)
        if not vehicle_info:
            total_skipped += 1
            continue

        make, model_name, year_start, year_end, description = vehicle_info
        vehicle_model = _fuzzy_match_vehicle_model(make, model_name, model_map)
        if not vehicle_model:
            total_skipped += 1
            continue

        batch.append((
            part_catalog,
            vehicle_model,
            description[:140] if description else None,
            year_start or 0,
            year_end or 0,
        ))

        if len(batch) >= BATCH_SIZE:
            _insert_applicability_batch(batch)
            total_imported += len(batch)
            batch = []

    if batch:
        _insert_applicability_batch(batch)
        total_imported += len(batch)

    frappe.db.commit()
    print(f"  -> {total_imported} applicability rows imported, {total_skipped} skipped")
    return total_imported


def _insert_applicability_batch(batch: list):
    if not batch:
        return
    now_str = now()
    user = "Administrator"

    def esc(val: str) -> str:
        return (val or "").replace(chr(39), chr(39) + chr(39))

    values = ", ".join(
        f"('{frappe.generate_hash()[:10]}', '{now_str}', '{now_str}', '{user}', '{user}', 0, 0, "
        f"'{esc(pc)}', '{esc(vm)}', "
        f"{('NULL' if not variant else chr(39)+esc(variant)+chr(39))}, "
        f"{ys}, {ye}, 'Universal', NULL, "
        f"'{esc(pc)}', 'Part Catalog', 'applicable_vehicles')"
        for pc, vm, variant, ys, ye in batch
    )
    sql = f"""
        INSERT IGNORE INTO `tabVehicle Part Applicability`
        (name, creation, modified, modified_by, owner, docstatus, idx,
         part_catalog, vehicle_model, variant, year_start, year_end,
         steering_position, market_code,
         parent, parenttype, parentfield)
        VALUES {values}
    """
    frappe.db.sql(sql)


def collect_article_ids_from_interchange() -> set:
    article_ids = set()
    files = [
        _local("1q2019", "article_new_numbers.csv"),
        _local("1q2019", "article_replace_numbers.csv"),
        _local("2q2018", "article_cross_list.csv"),
    ]
    for path in files:
        for fields in _tsv_reader(path):
            if len(fields) < 2:
                continue
            article_ids.add(fields[0].strip())
    print(f"  -> {len(article_ids)} distinct article ids from interchange files")
    return article_ids


def build_article_map(article_ids: set) -> dict:
    """article_id -> part_number."""
    print("Building article id map (streaming articles.csv parts)...")
    article_map = {}
    for part in ARTICLES_PARTS:
        path = _local("1q2019", part)
        if not os.path.exists(path):
            print(f"  warning: {part} not found, skipping")
            continue
        for fields in _tsv_reader(path):
            if len(fields) < 3:
                continue
            article_id = fields[0].strip()
            if article_id not in article_ids:
                continue
            part_number = fields[1].strip().upper()
            if part_number:
                article_map[article_id] = part_number
                article_ids.discard(article_id)
                if not article_ids:
                    print("  -> all required article ids resolved early")
                    return article_map
        print(f"  processed {part}")
    print(f"  -> {len(article_map)} article ids resolved")
    return article_map


def import_part_interchange(catalog_map: dict, article_map: dict) -> int:
    print("\n[2/2] Importing Part Interchange...")
    total_imported = 0

    RELATIONSHIP_MAP = {
        "New Number": "Superseded By",
        "Replacement": "Equivalent",
        "Equivalent": "Equivalent",
    }

    def process_file(path: str, rel_type: str, source: str, target_idx: int = 1, target_supplier_idx: int = 2):
        nonlocal total_imported
        batch = []
        skipped = 0
        for fields in _tsv_reader(path):
            if len(fields) < 3:
                continue
            article_a = fields[0].strip()
            target_article = fields[target_idx].strip().upper()

            part_a = catalog_map.get(article_map.get(article_a))
            if not part_a:
                skipped += 1
                continue

            part_b = catalog_map.get(target_article)
            if not part_b:
                skipped += 1
                continue

            if part_a == part_b:
                skipped += 1
                continue

            rel_type = RELATIONSHIP_MAP.get(rel_type, rel_type)
            batch.append((part_a, part_b, rel_type, source))
            if len(batch) >= BATCH_SIZE:
                _insert_interchange_batch(batch)
                total_imported += len(batch)
                batch = []

        if batch:
            _insert_interchange_batch(batch)
            total_imported += len(batch)
        return skipped

    skipped = 0
    skipped += process_file(
        _local("1q2019", "article_new_numbers.csv"),
        "New Number",
        "TecDoc 1Q2019",
    )
    skipped += process_file(
        _local("1q2019", "article_replace_numbers.csv"),
        "Replacement",
        "TecDoc 1Q2019",
    )
    skipped += process_file(
        _local("2q2018", "article_cross_list.csv"),
        "Equivalent",
        "TecDoc 2Q2018",
    )

    frappe.db.commit()
    print(f"  -> {total_imported} interchange rows imported, {skipped} skipped")
    return total_imported


def _insert_interchange_batch(batch: list):
    if not batch:
        return
    now_str = now()
    user = "Administrator"

    def esc(val: str) -> str:
        return (val or "").replace(chr(39), chr(39) + chr(39))

    value_tuples = []
    for pa, pb, rel, src in batch:
        # Forward row: parent = pa, part = pb
        value_tuples.append(
            f"('{frappe.generate_hash()[:10]}', '{now_str}', '{now_str}', '{user}', '{user}', "
            f"0, 0, '{esc(pa)}', 'interchanges', 'Part Catalog', '{esc(pb)}', "
            f"'{esc(rel)}')"
        )
        # Reverse row: parent = pb, part = pa
        value_tuples.append(
            f"('{frappe.generate_hash()[:10]}', '{now_str}', '{now_str}', '{user}', '{user}', "
            f"0, 0, '{esc(pb)}', 'interchanges', 'Part Catalog', '{esc(pa)}', "
            f"'{esc(rel)}')"
        )

    values = ", ".join(value_tuples)
    sql = f"""
        INSERT IGNORE INTO `tabPart Catalog Interchange`
        (name, creation, modified, modified_by, owner, docstatus, idx,
         parent, parentfield, parenttype, part, relationship_type)
        VALUES {values}
    """
    frappe.db.sql(sql)


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — TecDoc Association Importer (sample data)")
    print("=" * 60)

    print("\n[0/4] Downloading source files...")
    download_small_files()
    print("  small files ready")

    print("\n[0/4] Preparing maps...")
    catalog_map = load_part_catalog_map()
    model_map = load_vehicle_model_map()
    vehicle_maps = load_vehicle_maps()

    print("\n[0/4] Adding deduplication indexes...")
    _add_unique_indexes()

    app_count = import_vehicle_part_applicability(catalog_map, model_map, vehicle_maps)

    print("\n[0/4] Downloading articles.csv parts for interchange mapping...")
    download_articles_parts()
    article_ids = collect_article_ids_from_interchange()
    article_map = build_article_map(article_ids)
    ix_count = import_part_interchange(catalog_map, article_map)

    print("\n" + "=" * 60)
    print("TECDOC ASSOCIATION IMPORT COMPLETE")
    print("=" * 60)
    print(f"Vehicle Part Applicability: {app_count}")
    print(f"Part Interchange:           {ix_count}")
    print("=" * 60)
