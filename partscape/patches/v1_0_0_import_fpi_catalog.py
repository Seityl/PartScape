"""
PartScape — FPI Auto Parts Catalog PDF Importer

Source: https://download.fpiautoparts.com
License: FPI catalogs are provided free for reference/download.
         Data is aftermarket parts with OEM cross-references.
Format: PDF catalogs per vehicle model
Records: Varies per PDF (20-200 parts each)

Imports into:
- Part Catalog
- Part Supplier Reference (FPI codes linked to OEM numbers)
- Vehicle Part Applicability
"""

import os
import re
import urllib.request
import urllib.parse

import frappe
import pdfplumber

FPI_BASE_URL = "https://download.fpiautoparts.com"
DATA_DIR = frappe.get_app_path("partscape", "data_imports", "fpi_pdfs")

# Category mapping from description keywords
CATEGORY_MAP = {
    "BUMPER": "Body - Bumpers",
    "GRILLE": "Body - Grilles",
    "HEAD LAMP": "Electrical - Lighting",
    "HEADLIGHT": "Electrical - Lighting",
    "TAIL LAMP": "Electrical - Lighting",
    "TAILLIGHT": "Electrical - Lighting",
    "FOG LAMP": "Electrical - Lighting",
    "FOG LIGHT": "Electrical - Lighting",
    "LAMP": "Electrical - Lighting",
    "MIRROR": "Body - Mirrors",
    "DOOR MIRROR": "Body - Mirrors",
    "FENDER": "Body - Fenders",
    "INNER FENDER": "Body - Fenders",
    "HOOD": "Body - Hood",
    "BONNET": "Body - Hood",
    "TRUNK": "Body - Trunk",
    "BOOT": "Body - Trunk",
    "DOOR": "Body - Doors",
    "SKIRT": "Body - Exterior Trim",
    "SPOILER": "Body - Exterior Trim",
    "GARNISH": "Body - Exterior Trim",
    "GRILL": "Body - Grilles",
    "RADIATOR": "Engine - Cooling",
    "CONDENSER": "Engine - Cooling",
    "FAN": "Engine - Cooling",
    "SHROUD": "Engine - Cooling",
    "ENGINE MOUNT": "Engine - Mounts",
    "MOUNTING": "Engine - Mounts",
    "BRAKE": "Brake System",
    "PAD": "Brake System",
    "ROTOR": "Brake System",
    "CALIPER": "Brake System",
    "SUSPENSION": "Suspension",
    "SHOCK": "Suspension",
    "STRUT": "Suspension",
    "CONTROL ARM": "Suspension",
    "BALL JOINT": "Suspension",
    "TIE ROD": "Steering",
    "RACK": "Steering",
    "FILTER": "Engine - Filters",
    "OIL FILTER": "Engine - Filters",
    "AIR FILTER": "Engine - Filters",
    "BELT": "Engine - Belts",
    "TIMING BELT": "Engine - Belts",
    "PLUG": "Engine - Ignition",
    "COIL": "Engine - Ignition",
    "ALTERNATOR": "Electrical - Charging",
    "STARTER": "Electrical - Starting",
    "BATTERY": "Electrical - Battery",
    "WIPER": "Body - Wipers",
    "COWL": "Body - Cowl",
    "WINDSHIELD": "Body - Glass",
    "GLASS": "Body - Glass",
    "HANDLE": "Body - Handles",
    "LOCK": "Body - Locks",
    "HATCH": "Body - Trunk",
    "TAILGATE": "Body - Trunk",
}


def _ensure_item_group(group_name: str) -> str:
    """Get or create an Item Group."""
    if not group_name:
        group_name = "General"
    existing = frappe.db.get_value("Item Group", {"item_group_name": group_name}, "name")
    if existing:
        return existing
    parent_group = "Auto Parts" if frappe.db.exists("Item Group", "Auto Parts") else "All Item Groups"
    doc = frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": group_name,
        "parent_item_group": parent_group,
        "is_group": 0,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _ensure_brand(brand_name: str) -> str:
    """Get or create a Brand doc."""
    if not brand_name:
        return None
    existing = frappe.db.get_value("Brand", {"brand": brand_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "Brand",
        "brand": brand_name,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _map_category(description: str) -> str:
    """Map part description to category."""
    desc_upper = (description or "").upper()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in desc_upper:
            return category
    return "General"


def _get_or_create_make(make_name: str) -> str:
    existing = frappe.db.get_value("Vehicle Make", {"make_name": make_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "Vehicle Make",
        "make_name": make_name,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_model(make_name: str, model_name: str, year_start=None, year_end=None) -> str:
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"

    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        return existing

    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": _get_or_create_make(make_name),
        "model_code": model_code,
        "year_start": year_start or 2000,
        "year_end": year_end or 2026,
        "body_type": "Sedan",
        "steering_position": "LHD",
        "primary_market": "Global",
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _create_part_catalog(description: str, oem_number: str, fpi_code: str,
                         model_name: str, year_range: str, make_name: str) -> str:
    """Create or update Part Catalog entry."""
    # Use OEM number as primary part number if valid, else FPI code
    part_number = oem_number if oem_number and len(oem_number) > 5 else fpi_code
    if not part_number:
        return None

    category = _map_category(description)
    category_docname = _ensure_item_group(category)

    # Clean part number
    part_number = part_number.strip().replace(" ", "-").replace("/", "-")[:50]
    part_name = description.strip()[:100] if description else part_number
    brand_name = make_name if make_name else "FPI"
    brand_docname = _ensure_brand(brand_name)

    existing = frappe.db.get_value("Part Catalog", {"part_number": part_number}, "name")
    if existing:
        return existing

    doc = frappe.get_doc({
        "doctype": "Part Catalog",
        "brand": brand_docname,
        "part_number": part_number,
        "part_name": part_name,
        "description": description.strip()[:200],
        "category": category_docname,
        "oem_make": _get_or_create_make(make_name),
        "is_oem": 1 if oem_number and oem_number == part_number else 0,
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_supplier(supplier_name: str) -> str:
    """Get or create a Supplier doc."""
    existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
    if existing:
        return existing
    # Find a valid supplier group
    group = frappe.db.get_value("Supplier Group", {}, "name")
    if not group:
        group = "All Supplier Groups"
    try:
        doc = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": group,
        })
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        return doc.name
    except Exception:
        return supplier_name


def _create_supplier_reference(part_catalog: str, fpi_code: str, oem_number: str,
                               description: str) -> str:
    """Create Supplier Reference linking FPI code to part."""
    if not part_catalog or not fpi_code:
        return None

    supplier = _get_or_create_supplier("FPI Auto Parts")

    existing = frappe.db.get_value("Part Supplier Reference",
        {"part_catalog": part_catalog, "supplier_part_number": fpi_code}, "name")
    if existing:
        return existing

    doc = frappe.get_doc({
        "doctype": "Part Supplier Reference",
        "part_catalog": part_catalog,
        "supplier": supplier,
        "supplier_part_number": fpi_code.strip()[:50],
        "oem_part_number": (oem_number or "").strip()[:50],
        "description": description.strip()[:200],
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _add_applicability_to_part(part_catalog: str, model_docname: str, year_range: str):
    """Add Vehicle Part Applicability to existing Part Catalog via append."""
    if not part_catalog or not model_docname:
        return

    # Parse year range
    year_start = None
    year_end = None
    if year_range:
        m = re.match(r'(\d{4})\s*[-–]\s*(\d{4})', str(year_range))
        if m:
            year_start = int(m.group(1))
            year_end = int(m.group(2))
        else:
            m = re.match(r'(\d{4})', str(year_range))
            if m:
                year_start = int(m.group(1))
                year_end = year_start

    # Check if already exists in child table
    existing = frappe.db.get_value("Vehicle Part Applicability",
        {"parent": part_catalog, "parenttype": "Part Catalog", "parentfield": "applicable_vehicles",
         "vehicle_model": model_docname}, "name")
    if existing:
        return

    try:
        doc = frappe.get_doc("Part Catalog", part_catalog)
        doc.append("applicable_vehicles", {
            "vehicle_model": model_docname,
            "year_start": year_start,
            "year_end": year_end,
            "steering_position": "Universal",
        })
        doc.save(ignore_permissions=True)
    except Exception:
        pass


def _parse_pdf_tables(pdf_path: str):
    """Extract parts data from FPI PDF using pdfplumber."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                # First row should be headers
                headers = [h.strip().upper() if h else "" for h in table[0]]
                # Map column indices
                try:
                    code_idx = next(i for i, h in enumerate(headers) if h in ("CODE", "PART NO", "PART NUMBER"))
                except StopIteration:
                    code_idx = 1
                try:
                    desc_idx = next(i for i, h in enumerate(headers) if h in ("DESCRIPTION", "DESCR", "PART NAME"))
                except StopIteration:
                    desc_idx = 2
                try:
                    model_idx = next(i for i, h in enumerate(headers) if h in ("MODEL", "VEHICLE"))
                except StopIteration:
                    model_idx = 3
                try:
                    year_idx = next(i for i, h in enumerate(headers) if h in ("YEAR", "YEARS"))
                except StopIteration:
                    year_idx = 4
                try:
                    oem_idx = next(i for i, h in enumerate(headers) if h in ("OEM", "OEM NO", "ORIGINAL"))
                except StopIteration:
                    oem_idx = 5

                for row in table[1:]:
                    if not row or len(row) < max(code_idx, desc_idx) + 1:
                        continue
                    code = row[code_idx].strip() if code_idx < len(row) and row[code_idx] else ""
                    desc = row[desc_idx].strip() if desc_idx < len(row) and row[desc_idx] else ""
                    model = row[model_idx].strip() if model_idx < len(row) and row[model_idx] else ""
                    year = row[year_idx].strip() if year_idx < len(row) and row[year_idx] else ""
                    oem = row[oem_idx].strip() if oem_idx < len(row) and row[oem_idx] else ""

                    if code and desc:
                        parts.append({
                            "code": code,
                            "description": desc,
                            "model": model,
                            "year": year,
                            "oem": oem,
                        })
    return parts


def _parse_filename(filename: str):
    """Parse make, model, year from PDF filename like 'HONDA CIVIC 2012-2013.pdf'."""
    # Remove .pdf and split
    name = filename.replace(".pdf", "").strip()
    # Pattern: MAKE MODEL YEAR-YEAR or MAKE MODEL YEAR
    m = re.match(r'^([A-Z]+)\s+(.+?)\s+(\d{4})(?:\s*[-–]\s*(\d{4}))?', name)
    if m:
        return m.group(1), m.group(2).strip(), m.group(3), m.group(4)
    # Fallback: just first word as make, rest as model
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:]), None, None
    return name, "", None, None


def import_fpi_pdf(pdf_url: str, make_name: str = None, model_name: str = None,
                   year_start: int = None, year_end: int = None) -> dict:
    """Download and import a single FPI PDF catalog."""
    fname = os.path.basename(pdf_url)
    local_path = os.path.join(DATA_DIR, fname.replace(" ", "_"))
    os.makedirs(DATA_DIR, exist_ok=True)

    # Download if not exists
    if not os.path.exists(local_path):
        full_url = f"{FPI_BASE_URL}/{urllib.parse.quote(pdf_url, safe='/')}"
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(local_path, 'wb') as f:
                f.write(resp.read())

    # Parse filename for make/model/year if not provided
    if not make_name:
        make_name, model_name, year_start_str, year_end_str = _parse_filename(fname)
        if year_start_str:
            year_start = int(year_start_str)
        if year_end_str:
            year_end = int(year_end_str)

    # Extract tables
    parts = _parse_pdf_tables(local_path)
    if not parts:
        return {"status": "no_data", "parts": 0, "pdf": fname}

    # Get or create vehicle model
    model_docname = None
    if model_name:
        model_docname = _get_or_create_model(make_name, model_name, year_start, year_end)

    # Import parts
    part_count = 0
    ref_count = 0
    app_count = 0

    for part in parts:
        part_catalog = _create_part_catalog(
            part["description"], part["oem"], part["code"],
            model_name or part["model"], part["year"] or f"{year_start}-{year_end}", make_name
        )
        if part_catalog:
            part_count += 1
            ref = _create_supplier_reference(part_catalog, part["code"], part["oem"], part["description"])
            if ref:
                ref_count += 1
            if model_docname:
                _add_applicability_to_part(part_catalog, model_docname, part["year"] or f"{year_start}-{year_end}")
                app_count += 1

        if part_count % 50 == 0:
            frappe.db.commit()

    frappe.db.commit()
    return {
        "status": "success",
        "pdf": fname,
        "parts": part_count,
        "references": ref_count,
        "applicabilities": app_count,
    }


def execute():
    """Import all text-based FPI PDFs found in the data directory."""
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — FPI Auto Parts Catalog Importer")
    print("Source: download.fpiautoparts.com")
    print("=" * 60)

    # Read list of text-based PDFs (generated by scanner)
    text_list_path = "/tmp/fpi_text_pdfs.txt"
    if os.path.exists(text_list_path):
        with open(text_list_path, "r") as f:
            pdf_urls = [line.strip().split('\t')[0] for line in f if line.strip()]
    else:
        # Fallback: known text-based PDFs
        pdf_urls = [
            "fpi_update/catalog-model/HONDA/HONDA CIVIC 2012-2013.pdf",
            "fpi_update/catalog-model/DAIHATSU/DAIHATSU CUORE-DELTA.pdf",
            "fpi_update/catalog-model/SUZUKI/SUZUKI SWIFT 2012-2014.pdf",
            "fpi_update/catalog-model/CHEVROLET/CHEVROLET CRUZE 2013.pdf",
        ]

    print(f"\nFound {len(pdf_urls)} text-based PDFs to import")

    total_parts = 0
    total_refs = 0
    total_apps = 0

    for i, pdf_url in enumerate(pdf_urls):
        print(f"\n[{i+1}/{len(pdf_urls)}] Importing {os.path.basename(pdf_url)}...")
        try:
            result = import_fpi_pdf(pdf_url)
            print(f"  → {result['parts']} parts, {result.get('references', 0)} refs, {result.get('applicabilities', 0)} apps")
            total_parts += result["parts"]
            total_refs += result.get("references", 0)
            total_apps += result.get("applicabilities", 0)
        except Exception as e:
            print(f"  → ERROR: {e}")
            frappe.log_error(title="FPI Import Error", message=f"{pdf_url}: {e}")

    print("\n" + "=" * 60)
    print("FPI IMPORT COMPLETE")
    print("=" * 60)
    print(f"PDFs processed:         {len(pdf_urls)}")
    print(f"Parts imported:         {total_parts}")
    print(f"Supplier refs:          {total_refs}")
    print(f"Applicabilities:        {total_apps}")
    print("=" * 60)
