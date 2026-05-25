"""
PartScape — Generate Placeholder Diagram Images

Generates simple exploded-view-style placeholder images for all Part Diagram records
and attaches them via Frappe's file system. Also creates the app logo SVG.

These are generic placeholder diagrams (not copyrighted OEM content).
"""

import os
import random
import frappe
from frappe.utils.file_manager import save_file
from PIL import Image, ImageDraw, ImageFont


def _get_font(size):
    """Try to load a system font, fall back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_diagram_image(parts_group, diagram_number, width=800, height=600):
    """Generate a simple exploded-view placeholder diagram."""
    img = Image.new("RGB", (width, height), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = _get_font(24)
    draw.text((20, 15), f"{parts_group}", fill=(30, 30, 30), font=title_font)
    draw.text((20, 45), f"Diagram: {diagram_number}", fill=(100, 100, 100), font=_get_font(14))

    # Draw some "parts" as rectangles with callout circles
    random.seed(diagram_number)
    num_parts = random.randint(5, 15)
    colors = [
        (200, 80, 80), (80, 150, 80), (80, 80, 200), (200, 150, 50),
        (150, 50, 150), (50, 150, 150), (180, 100, 50), (100, 100, 100),
    ]

    for i in range(num_parts):
        x = random.randint(80, width - 180)
        y = random.randint(100, height - 120)
        w = random.randint(40, 120)
        h = random.randint(30, 80)
        color = colors[i % len(colors)]

        # Draw part shape
        draw.rectangle([x, y, x + w, y + h], fill=color, outline=(40, 40, 40), width=2)

        # Draw callout circle
        cx, cy = x + w + 25, y + h // 2
        draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
        draw.text((cx - 6, cy - 8), str(i + 1), fill=(40, 40, 40), font=_get_font(14))

        # Draw dashed line from part to callout
        for dx in range(0, 20, 4):
            draw.line([x + w + dx, cy, x + w + dx + 2, cy], fill=(100, 100, 100), width=1)

    # Footer
    draw.text((20, height - 30), "PartScape — Placeholder Diagram (internal use only)", fill=(150, 150, 150), font=_get_font(11))

    return img


def generate_logo_svg():
    """Generate the PartScape logo SVG."""
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="16" fill="#1a1a2e"/>
  <circle cx="50" cy="45" r="28" fill="none" stroke="#e94560" stroke-width="6"/>
  <path d="M50 17 L50 25 M50 65 L50 73 M22 45 L30 45 M70 45 L78 45" stroke="#e94560" stroke-width="6" stroke-linecap="round"/>
  <circle cx="50" cy="45" r="8" fill="#e94560"/>
  <text x="50" y="92" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="bold" fill="#fff">PS</text>
</svg>"""


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Generating Placeholder Diagram Images")
    print("=" * 60)

    # ── 1. Generate Logo SVG ────────────────────────────────────────────────
    print("\n[1/3] Creating app logo SVG...")
    logo_dir = os.path.join(frappe.get_app_path("partscape"), "public", "images")
    os.makedirs(logo_dir, exist_ok=True)
    logo_path = os.path.join(logo_dir, "partscape-logo.svg")
    with open(logo_path, "w") as f:
        f.write(generate_logo_svg())
    print(f"   → Logo saved to {logo_path}")

    # ── 2. Generate & Attach Diagram Images ─────────────────────────────────
    print("\n[2/3] Generating diagram placeholder images...")
    diagrams = frappe.get_all("Part Diagram", fields=["name", "parts_group", "diagram_number", "vehicle_model"])

    attached = 0
    skipped = 0

    for diag in diagrams:
        # Check if already has image
        existing_image = frappe.db.get_value("Part Diagram", diag.name, "diagram_image")
        if existing_image:
            skipped += 1
            continue

        # Generate image
        img = generate_diagram_image(diag.parts_group, diag.diagram_number)

        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Create file name
        safe_group = diag.parts_group.replace(" / ", "_").replace(" ", "_").replace("&", "and")
        file_name = f"{diag.vehicle_model}_{safe_group}_{diag.diagram_number}.png"

        # Save via Frappe file manager
        try:
            file_doc = save_file(
                fname=file_name,
                content=buffer.getvalue(),
                dt="Part Diagram",
                dn=diag.name,
                folder=None,
                decode=False,
                is_private=1,
            )

            # Update the Part Diagram record
            frappe.db.set_value("Part Diagram", diag.name, "diagram_image", file_doc.file_url)
            attached += 1

            if attached % 100 == 0:
                print(f"   → {attached} images attached...")
                frappe.db.commit()

        except Exception as e:
            print(f"   WARN: Could not attach image for {diag.name}: {e}")

    frappe.db.commit()
    print(f"   → {attached} new images attached, {skipped} already had images")

    # ── 3. Update Part Catalog Diagrams child table ─────────────────────────
    print("\n[3/3] Linking Part Catalog entries to diagram callouts...")
    part_diagram_links = 0

    # Get all parts and diagrams
    parts = frappe.get_all("Part Catalog", fields=["name", "brand", "part_number", "part_name"], limit=200)
    diagram_docs = frappe.get_all("Part Diagram", fields=["name", "parts_group", "vehicle_model"])

    for part in parts:
        # Find a relevant diagram
        brand = part.brand
        relevant = [d for d in diagram_docs if brand in d.vehicle_model]
        if not relevant:
            continue

        diag = random.choice(relevant)

        # Check if link already exists
        part_doc = frappe.get_doc("Part Catalog", part.name)
        already = any(d.part_diagram == diag.name for d in part_doc.diagrams)
        if already:
            continue

        callout = random.randint(1, 15)
        part_doc.append("diagrams", {
            "part_diagram": diag.name,
            "callout_number": str(callout),
            "parts_group": diag.parts_group,
        })
        try:
            part_doc.save(ignore_permissions=True)
            part_diagram_links += 1
        except Exception:
            pass

        if part_diagram_links % 50 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"   → {part_diagram_links} Part Catalog → Diagram links created")

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DIMAGE GENERATION COMPLETE")
    print("=" * 60)
    print(f"Logo SVG:               {logo_path}")
    print(f"Diagram Images:         {attached} new, {skipped} existing")
    print(f"Part→Diagram Links:     {part_diagram_links}")
    print("=" * 60)
