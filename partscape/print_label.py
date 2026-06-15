"""
PartScape Label Printing — Brother QL-800 browser-native integration.

Generates barcode images and label PNGs on the server; the client opens the
OS print dialog so the user can select a locally attached Brother QL-800.
"""

import base64
import io
import shutil
import subprocess
from typing import Optional

import frappe
from frappe import _
from frappe.utils import cstr

# -----------------------------------------------------------------------------
# Label geometry (Brother QL-800 @ 300 dpi)
# -----------------------------------------------------------------------------
LABEL_SIZES = {
    "62mm continuous": {
        "mm": (62, 100),
        "px": (696, 1124),
    },
    "29mmx90mm": {
        "mm": (29, 90),
        "px": (306, 991),
    },
}

BARCODE_TYPES = {
    "Code128": "code128",
    "EAN13": "ean13",
    "UPCA": "upca",
}

# -----------------------------------------------------------------------------
# Barcode helpers
# -----------------------------------------------------------------------------

def _pick_barcode_type(value: str) -> str:
    """Pick EAN-13 for 12/13 digit numeric codes, otherwise Code 128."""
    digits = value.replace("-", "").strip()
    if digits.isdigit() and len(digits) in (12, 13):
        return "ean13"
    return "code128"


def _normalize_for_barcode(value: str, barcode_type: str) -> str:
    """Return a value that the chosen barcode symbology accepts."""
    value = cstr(value).strip()
    if barcode_type == "ean13":
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) == 12:
            # python-barcode calculates the check digit automatically
            return digits
        if len(digits) == 13:
            return digits
        frappe.throw(_("EAN-13 requires 12 or 13 numeric digits."))
    if barcode_type == "upca":
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) == 11:
            return digits
        if len(digits) == 12:
            return digits
        frappe.throw(_("UPC-A requires 11 or 12 numeric digits."))
    if barcode_type == "code128":
        if not value:
            frappe.throw(_("A value is required to generate a Code 128 barcode."))
        return value
    return value


def get_barcode_image(
    value: str,
    barcode_type: Optional[str] = None,
    width: int = 400,
    height: int = 180,
    show_text: bool = True,
) -> str:
    """
    Generate a barcode PNG and return it as a base64 data URI.

    The barcode is generated so its bars span the full requested width; the
    label's own white background provides the quiet zone, so internal quiet
    zones are removed to maximize horizontal usage.

    :param value: raw value to encode
    :param barcode_type: 'code128', 'ean13', 'upca' or None for auto
    :param width: target image width in pixels (used to pick module width)
    :param height: target image height in pixels (controls bar/text size)
    :param show_text: render human-readable text below bars
    :return: 'data:image/png;base64,...'
    """
    if not barcode_type:
        barcode_type = _pick_barcode_type(value)
    barcode_type = BARCODE_TYPES.get(barcode_type, barcode_type)

    value = _normalize_for_barcode(value, barcode_type)

    try:
        import barcode
        from barcode.writer import ImageWriter
        from PIL import Image
    except ImportError as exc:
        frappe.throw(_("Missing barcode/Pillow libraries: {0}").format(str(exc)))

    barcode_class = barcode.get_barcode_class(barcode_type)

    # Pick a module width so the encoded bars fill the requested width.
    value_len = len(value)
    if barcode_type == "ean13":
        modules = 95
    elif barcode_type == "upca":
        modules = 95
    else:
        # Code128: 11 modules per character + start/stop/check symbols.
        modules = 11 * value_len + 13
    module_width = max(2, round(width / max(modules, 1)))

    buffer = io.BytesIO()
    writer = ImageWriter()
    writer.set_options({
        "write_text": show_text,
        "text_distance": 4,
        "quiet_zone": 0,
        "module_width": module_width,
        "module_height": max(10, int(height * 0.55)),
        "font_size": max(12, int(height * 0.20)),
    })
    barcode_instance = barcode_class(value, writer=writer)
    barcode_instance.write(buffer)
    buffer.seek(0)

    img = Image.open(buffer).convert("L")
    out_buffer = io.BytesIO()
    img.save(out_buffer, format="PNG")
    out_buffer.seek(0)
    b64 = base64.b64encode(out_buffer.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


@frappe.whitelist()
def generate_barcode(item_code: str, barcode_type: Optional[str] = None) -> str:
    """
    Generate and persist a barcode for the given Item.

    :return: the barcode value stored on the Item
    """
    if not frappe.has_permission("Item", doc=item_code):
        frappe.throw(_("Not permitted to generate barcode for this item."))

    item = frappe.get_doc("Item", item_code)
    raw_value = item.part_number or item.item_code
    if not barcode_type:
        barcode_type = _pick_barcode_type(raw_value)

    value = _normalize_for_barcode(raw_value, barcode_type)
    item.partscape_barcode = value
    item.save(ignore_permissions=True)
    frappe.db.commit()

    # Touch the file cache so the print format can embed a fresh image
    get_barcode_image(value, barcode_type=barcode_type)

    return value


# -----------------------------------------------------------------------------
# Label context / rendering
# -----------------------------------------------------------------------------

def _get_company_context() -> dict:
    """Return company name and phone for the label header."""
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_value(
        "Company", {}, "name"
    )
    if not company:
        return {"company_name": "", "company_phone": ""}

    phone = ""
    for field in ("phone_no", "phone", "mobile_no"):
        phone = frappe.db.get_value("Company", company, field) or ""
        if phone:
            break
    return {"company_name": company, "company_phone": phone}


def _get_item_context(item_code: str) -> dict:
    """Collect Item data for the label template."""
    item = frappe.get_doc("Item", item_code)
    barcode_value = item.partscape_barcode
    if not barcode_value:
        barcode_value = generate_barcode(item_code)

    barcode_type = _pick_barcode_type(barcode_value)
    barcode_image = get_barcode_image(barcode_value, barcode_type=barcode_type)

    return {
        "doctype": "Item",
        "doc": item,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "brand": item.brand or "",
        "part_number": item.part_number or "",
        "category": item.item_group or "",
        "standard_rate": getattr(item, "standard_rate", None) or getattr(item, "valuation_rate", 0),
        "barcode_value": barcode_value,
        "barcode_image": barcode_image,
        **_get_company_context(),
    }


def _get_warehouse_context(warehouse_name: str) -> dict:
    """Collect Warehouse data for the label template."""
    wh = frappe.get_doc("Warehouse", warehouse_name)
    barcode_value = cstr(wh.warehouse_code or wh.warehouse_name).strip()
    barcode_type = _pick_barcode_type(barcode_value)
    barcode_image = get_barcode_image(barcode_value, barcode_type=barcode_type)

    return {
        "doctype": "Warehouse",
        "doc": wh,
        "warehouse_name": wh.warehouse_name,
        "warehouse_code": wh.warehouse_code or wh.name,
        "zone": wh.warehouse_zone or "",
        "address": wh.address_line_1 or "",
        "barcode_value": barcode_value,
        "barcode_image": barcode_image,
        **_get_company_context(),
    }


def _get_print_format_name(doctype: str, label_size: str) -> str:
    """Map DocType + label size to the PartScape print format name."""
    size_suffix = "62mm" if label_size == "62mm continuous" else "29mm"
    if doctype == "Item":
        return f"PartScape Item Label {size_suffix}"
    return f"PartScape Warehouse Label {size_suffix}"


def render_label_html(doctype: str, name: str, label_size: str) -> str:
    """Render the label Print Format as HTML (no Frappe print wrapper)."""
    print_format = _get_print_format_name(doctype, label_size)
    template = frappe.db.get_value("Print Format", print_format, "html")
    if not template:
        frappe.throw(_("Print Format {0} not found or has no HTML").format(print_format))

    doc = frappe.get_doc(doctype, name)
    html = frappe.render_template(template, {"doc": doc})
    return html


# -----------------------------------------------------------------------------
# HTML -> image conversion
# -----------------------------------------------------------------------------

def _html_to_image_with_wkhtmltoimage(html: str, label_size: str) -> bytes:
    """Convert label HTML to a PNG using wkhtmltoimage and reduce to grayscale."""
    from PIL import Image

    width_px, height_px = LABEL_SIZES[label_size]["px"]
    cmd = [
        "wkhtmltoimage",
        "--width",
        str(width_px),
        "--height",
        str(height_px),
        "--format",
        "png",
        "--enable-local-file-access",
        "--disable-smart-width",
        "-",
        "-",
    ]
    result = subprocess.run(
        cmd,
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"wkhtmltoimage failed ({result.returncode}): {result.stderr.decode('utf-8', errors='ignore')}"
        )

    img = Image.open(io.BytesIO(result.stdout)).convert("L")
    out_buffer = io.BytesIO()
    img.save(out_buffer, format="PNG")
    return out_buffer.getvalue()


def _html_to_image_with_pil(doctype: str, name: str, label_size: str) -> bytes:
    """
    Fallback renderer: draw a simple label directly with Pillow.

    Used when wkhtmltoimage is unavailable. Layout mirrors the print format.
    """
    from PIL import Image, ImageDraw, ImageFont

    width_px, height_px = LABEL_SIZES[label_size]["px"]
    img = Image.new("L", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    margin = 5
    y = margin

    if doctype == "Item":
        ctx = _get_item_context(name)
        draw.text((margin, y), ctx["company_name"], fill="black", font=font_medium)
        price_text = f"${ctx['standard_rate']:.2f}" if ctx.get("standard_rate") else ""
        if price_text:
            bbox = draw.textbbox((0, 0), price_text, font=font_medium)
            draw.text((width_px - margin - (bbox[2] - bbox[0]), y), price_text, fill="black", font=font_medium)
        y += 35
        if ctx.get("company_phone"):
            draw.text((margin, y), f"Tel: {ctx['company_phone']}", fill="black", font=font_small)
            y += 25
        draw.text((margin, y), ctx["item_name"], fill="black", font=font_large)
        y += 45
        draw.text((margin, y), ctx["brand"], fill="black", font=font_medium)
        y += 30
        draw.text((margin, y), ctx["category"], fill="black", font=font_medium)
        y += 30
        draw.text((margin, y), ctx["part_number"] or ctx["item_code"], fill="black", font=font_medium)
        y += 35
    else:
        ctx = _get_warehouse_context(name)
        draw.text((margin, y), ctx["company_name"], fill="black", font=font_medium)
        y += 35
        draw.text((margin, y), ctx["warehouse_name"], fill="black", font=font_large)
        y += 45
        draw.text((margin, y), ctx["warehouse_code"], fill="black", font=font_medium)
        y += 30
        if ctx.get("zone"):
            draw.text((margin, y), ctx["zone"], fill="black", font=font_medium)
            y += 30
        if ctx.get("address"):
            draw.text((margin, y), ctx["address"], fill="black", font=font_small)
            y += 25

    # Barcode
    barcode_type = _pick_barcode_type(ctx["barcode_value"])
    max_barcode_width = width_px - 2 * margin
    b64 = get_barcode_image(
        ctx["barcode_value"],
        barcode_type=barcode_type,
        width=max_barcode_width,
        height=160,
    ).split(",")[-1]
    barcode_bytes = base64.b64decode(b64)
    barcode_img = Image.open(io.BytesIO(barcode_bytes)).convert("L")
    # The returned image is tightly cropped; scale it down if it is too wide.
    if barcode_img.width > max_barcode_width:
        ratio = max_barcode_width / barcode_img.width
        barcode_img = barcode_img.resize(
            (max_barcode_width, int(barcode_img.height * ratio)), Image.LANCZOS
        )
    barcode_y = height_px - barcode_img.height - margin
    img.paste(barcode_img, (margin, barcode_y))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def html_to_image(doctype: str, name: str, label_size: str) -> bytes:
    """
    Convert the label HTML to a printer-ready PNG.

    Tries wkhtmltoimage first; falls back to a direct PIL renderer.
    """
    html = render_label_html(doctype, name, label_size)
    if shutil.which("wkhtmltoimage"):
        try:
            return _html_to_image_with_wkhtmltoimage(html, label_size)
        except Exception:
            frappe.log_error("wkhtmltoimage failed, using PIL fallback")
    return _html_to_image_with_pil(doctype, name, label_size)


# -----------------------------------------------------------------------------
# Public whitelisted method for browser printing
# -----------------------------------------------------------------------------

@frappe.whitelist()
def get_label_image(doctype: str, name: str, label_size: str) -> str:
    """
    Generate a label PNG and return it as a base64 data URI.

    The client opens the OS print dialog so the user can select the locally
    attached Brother QL-800.
    """
    if doctype not in ("Item", "Warehouse"):
        frappe.throw(_("Unsupported DocType for label printing."))

    if not frappe.has_permission(doctype, doc=name):
        frappe.throw(_("Not permitted to print labels for this {0}.").format(doctype))

    if label_size not in LABEL_SIZES:
        frappe.throw(_("Unsupported label size: {0}").format(label_size))

    image_bytes = html_to_image(doctype, name, label_size)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


@frappe.whitelist()
def get_label_pdf(doctype: str, name: str, label_size: str) -> str:
    """
    Generate a label PDF and return it as a base64 data URI.

    The PDF has the exact label page size embedded (62x100 mm or 29x90 mm),
    so the browser/OS print dialog defaults to the correct paper size and the
    label is not scaled down to A4/Letter.
    """
    if doctype not in ("Item", "Warehouse"):
        frappe.throw(_("Unsupported DocType for label printing."))

    if not frappe.has_permission(doctype, doc=name):
        frappe.throw(_("Not permitted to print labels for this {0}.").format(doctype))

    if label_size not in LABEL_SIZES:
        frappe.throw(_("Unsupported label size: {0}").format(label_size))

    if not shutil.which("wkhtmltopdf"):
        frappe.throw(_("wkhtmltopdf is required for PDF label generation."))

    html = render_label_html(doctype, name, label_size)
    width_mm, height_mm = LABEL_SIZES[label_size]["mm"]

    cmd = [
        "wkhtmltopdf",
        "--disable-smart-shrinking",
        "--page-width",
        f"{width_mm}mm",
        "--page-height",
        f"{height_mm}mm",
        "--margin-top",
        "0",
        "--margin-right",
        "0",
        "--margin-bottom",
        "0",
        "--margin-left",
        "0",
        "--enable-local-file-access",
        "--encoding",
        "utf-8",
        "-",
        "-",
    ]
    result = subprocess.run(
        cmd,
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"wkhtmltopdf failed ({result.returncode}): {result.stderr.decode('utf-8', errors='ignore')}"
        )

    b64 = base64.b64encode(result.stdout).decode("utf-8")
    return f"data:application/pdf;base64,{b64}"
