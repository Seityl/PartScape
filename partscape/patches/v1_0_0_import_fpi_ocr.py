"""
PartScape — FPI Auto Parts Catalog OCR Importer (Image-based PDFs)

Source: https://download.fpiautoparts.com
Method: Tesseract OCR on rendered PDF pages
Records: ~580 image-based PDFs

Imports into:
- Part Catalog
- Part Supplier Reference
"""

import os
import re
import urllib.request
import urllib.parse

import frappe
import pypdfium2 as pdfium

FPI_BASE_URL = "https://download.fpiautoparts.com"
DATA_DIR = frappe.get_app_path("partscape", "data_imports", "fpi_pdfs")

# Regex patterns for extracting data from OCR text
OEM_PATTERN = re.compile(r'\b(\d{5}-[A-Z0-9]{3,})\b')
YEAR_PATTERN = re.compile(r'(\d{4})\s*[-–]\s*(\d{4})')
SINGLE_YEAR_PATTERN = re.compile(r'\b(\d{4})\b')

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


def _ensure_category(category_name: str) -> str:
    if not category_name:
        category_name = "General"
    existing = frappe.db.get_value("Part Category", {"category_name": category_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Part Category", "category_name": category_name})
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _map_category(description: str) -> str:
    desc_upper = (description or "").upper()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in desc_upper:
            return category
    return "General"


def _get_or_create_make(make_name: str) -> str:
    existing = frappe.db.get_value("Vehicle Make", {"make_name": make_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": make_name})
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_model(make_name: str, model_name: str, year_start=None, year_end=None) -> str:
    safe_code = model_name.upper().replace(" ", "_").replace("-", "_")[:20]
    model_code = f"{make_name[:3].upper()}-{safe_code}"
    existing = frappe.db.get_value("Vehicle Model", {"model_code": model_code}, "name")
    if existing:
        return existing
    make_docname = _get_or_create_make(make_name)
    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": model_name,
        "make": make_docname,
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
    part_number = oem_number if oem_number and len(oem_number) > 5 else fpi_code
    if not part_number:
        return None

    category = _map_category(description)
    category_docname = _ensure_category(category)
    part_number = part_number.strip().replace(" ", "-").replace("/", "-")[:50]
    part_name = description.strip()[:100] if description else part_number
    brand = make_name if make_name else "FPI"

    existing = frappe.db.get_value("Part Catalog", {"part_number": part_number}, "name")
    if existing:
        return existing

    doc = frappe.get_doc({
        "doctype": "Part Catalog",
        "brand": brand,
        "part_number": part_number,
        "part_name": part_name,
        "description": description.strip()[:200],
        "category": category_docname,
        "vehicle_make": _get_or_create_make(make_name),
        "is_oem": 1 if oem_number and oem_number == part_number else 0,
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_supplier(supplier_name: str) -> str:
    existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
    if existing:
        return existing
    group = frappe.db.get_value("Supplier Group", {}, "name") or "All Supplier Groups"
    try:
        doc = frappe.get_doc({"doctype": "Supplier", "supplier_name": supplier_name, "supplier_group": group})
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        return doc.name
    except Exception:
        return supplier_name


def _create_supplier_reference(part_catalog: str, fpi_code: str, oem_number: str, description: str) -> str:
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
    if not part_catalog or not model_docname:
        return
    year_start = year_end = None
    if year_range:
        m = YEAR_PATTERN.match(str(year_range))
        if m:
            year_start = int(m.group(1))
            year_end = int(m.group(2))
        else:
            m = SINGLE_YEAR_PATTERN.search(str(year_range))
            if m:
                year_start = year_end = int(m.group(1))
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


def _parse_filename(filename: str):
    name = filename.replace(".pdf", "").strip()
    m = re.match(r'^([A-Z]+)\s+(.+?)\s+(\d{4})(?:\s*[-–]\s*(\d{4}))?', name)
    if m:
        return m.group(1), m.group(2).strip(), m.group(3), m.group(4)
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:]), None, None
    return name, "", None, None


def _ocr_pdf_page(pdf_path: str, page_index: int = 0) -> str:
    """Render a PDF page and OCR it with Tesseract."""
    import subprocess
    pdf = pdfium.PdfDocument(pdf_path)
    if page_index >= len(pdf):
        return ""
    page = pdf[page_index]
    bitmap = page.render(scale=3)
    pil_image = bitmap.to_pil()
    img_path = f"/tmp/fpi_ocr_{os.getpid()}_{page_index}.png"
    pil_image.save(img_path)
    result = subprocess.run(["tesseract", img_path, "-", "--psm", "6"],
                           capture_output=True, text=True)
    try:
        os.remove(img_path)
    except Exception:
        pass
    return result.stdout


def _extract_parts_from_ocr(ocr_text: str, make_name: str, model_name: str, year_start, year_end):
    """Extract part records from OCR text using regex."""
    parts = []
    lines = ocr_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Look for OEM number pattern
        oem_match = OEM_PATTERN.search(line)
        if not oem_match:
            continue
        oem_number = oem_match.group(1)
        # Try to extract description from the line
        # Typical format: [NO] [CODE] [DESCRIPTION] [MODEL] [YEAR] [OEM] ...
        # Split by spaces and look for description between code-like tokens and year
        tokens = line.split()
        description = ""
        fpi_code = ""
        year_range = ""
        # Try to find FPI code (typically 2-3 letters + digits + space + 2 letters)
        for i, token in enumerate(tokens):
            if re.match(r'^[A-Z]{2,3}\d{2,4}\s+[A-Z]{1,2}$', token):
                fpi_code = token
                if i + 1 < len(tokens) and not re.match(r'^\d{4}$', tokens[i + 1]):
                    description = tokens[i + 1]
            elif re.match(r'^[A-Z]{2,3}\d{2,4}[A-Z]{1,2}$', token):
                fpi_code = token
        # If no FPI code found, use a generated one
        if not fpi_code:
            fpi_code = f"FPI-{oem_number.split('-')[0]}"
        # Extract year from line
        year_match = YEAR_PATTERN.search(line)
        if year_match:
            year_range = f"{year_match.group(1)}-{year_match.group(2)}"
        else:
            single_year = SINGLE_YEAR_PATTERN.search(line)
            if single_year:
                year_range = single_year.group(1)
        # Fallback description from line content
        if not description:
            # Remove OEM number and known tokens, keep words
            cleaned = line.replace(oem_number, "")
            # Keep only alphabetic words that look like descriptions
            words = re.findall(r'[A-Z][A-Z\s]{2,30}', cleaned)
            if words:
                description = words[0].strip()
        if not description:
            description = "Auto Part"
        parts.append({
            "code": fpi_code,
            "description": description,
            "model": model_name,
            "year": year_range or f"{year_start}-{year_end}",
            "oem": oem_number,
        })
    return parts


def import_fpi_pdf_ocr(pdf_url: str, make_name: str = None, model_name: str = None,
                       year_start: int = None, year_end: int = None) -> dict:
    """Download and OCR-import a single FPI PDF catalog."""
    fname = os.path.basename(pdf_url)
    local_path = os.path.join(DATA_DIR, fname.replace(" ", "_"))
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(local_path):
        segments = pdf_url.split('/')
        encoded = '/'.join(urllib.parse.quote(seg, safe='') for seg in segments)
        full_url = f"{FPI_BASE_URL}/{encoded}"
        try:
            req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(local_path, 'wb') as f:
                    f.write(resp.read())
        except Exception as e:
            return {"status": "download_error", "error": str(e), "pdf": fname}

    if not make_name:
        make_name, model_name, year_start_str, year_end_str = _parse_filename(fname)
        if year_start_str:
            year_start = int(year_start_str)
        if year_end_str:
            year_end = int(year_end_str)

    # OCR all pages
    all_parts = []
    try:
        pdf = pdfium.PdfDocument(local_path)
        for page_idx in range(len(pdf)):
            ocr_text = _ocr_pdf_page(local_path, page_idx)
            page_parts = _extract_parts_from_ocr(ocr_text, make_name, model_name, year_start, year_end)
            all_parts.extend(page_parts)
    except Exception as e:
        return {"status": "ocr_error", "error": str(e), "pdf": fname}

    if not all_parts:
        return {"status": "no_data", "parts": 0, "pdf": fname}

    model_docname = None
    if model_name:
        model_docname = _get_or_create_model(make_name, model_name, year_start, year_end)

    part_count = 0
    ref_count = 0
    app_count = 0

    for part in all_parts:
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
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — FPI OCR Importer (Image-based PDFs)")
    print("=" * 60)

    # Get all PDF URLs from FPI website
    import subprocess
    result = subprocess.run(
        ["bash", "-c", "curl -sL 'https://download.fpiautoparts.com' | grep -oP 'href=\"fpi_update/catalog-model/[^\"]+\\.pdf\"' | sed 's/href=\"//;s/\"$//' | sort -u"],
        capture_output=True, text=True
    )
    all_urls = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]

    # Get already-imported text PDFs
    text_list_path = "/tmp/fpi_text_pdfs.txt"
    text_urls = set()
    if os.path.exists(text_list_path):
        with open(text_list_path, "r") as f:
            for line in f:
                if line.strip():
                    text_urls.add(line.strip().split('\t')[0])

    # Image-based PDFs = all - text
    image_urls = [u for u in all_urls if u not in text_urls]
    print(f"\nTotal PDFs: {len(all_urls)}")
    print(f"Text-based (already imported): {len(text_urls)}")
    print(f"Image-based (to OCR): {len(image_urls)}")

    total_parts = 0
    total_refs = 0
    total_apps = 0
    success_count = 0

    for i, pdf_url in enumerate(image_urls):
        print(f"\n[{i+1}/{len(image_urls)}] OCR {os.path.basename(pdf_url)}...")
        try:
            result = import_fpi_pdf_ocr(pdf_url)
            if result["status"] == "success":
                print(f"  → {result['parts']} parts, {result.get('references', 0)} refs, {result.get('applicabilities', 0)} apps")
                total_parts += result["parts"]
                total_refs += result.get("references", 0)
                total_apps += result.get("applicabilities", 0)
                success_count += 1
            else:
                print(f"  → {result['status']}: {result.get('error', 'unknown')}")
        except Exception as e:
            print(f"  → ERROR: {e}")
            frappe.log_error(title="FPI OCR Error", message=f"{pdf_url}: {e}")

    print("\n" + "=" * 60)
    print("FPI OCR IMPORT COMPLETE")
    print("=" * 60)
    print(f"PDFs processed:         {len(image_urls)}")
    print(f"Successful:             {success_count}")
    print(f"Parts imported:         {total_parts}")
    print(f"Supplier refs:          {total_refs}")
    print(f"Applicabilities:        {total_apps}")
    print("=" * 60)
