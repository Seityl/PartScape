"""
PartScape — Item Factory

Creates or links ERPNext Item records from Part Catalog entries.
"""

import frappe
from frappe import _


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_item_from_part_catalog(part_catalog_name: str, create_if_missing: bool = True) -> str:
    """
    Given a Part Catalog doc name, find or create an ERPNext Item.
    Returns the Item code.
    """
    pc = frappe.get_doc("Part Catalog", part_catalog_name)
    if not pc:
        frappe.throw(_("Part Catalog not found"))

    # Try to find existing item by brand + part_number
    existing = frappe.db.get_value(
        "Item",
        {"brand": pc.brand, "part_number": pc.part_number},
        "name",
    )
    if existing:
        item = frappe.get_doc("Item", existing)
        if not item.part_catalog_reference:
            item.part_catalog_reference = pc.name
            item.save(ignore_permissions=True)
        return item.name

    if not create_if_missing:
        return None

    item_code = _generate_item_code(pc)

    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_code,
        "item_name": pc.part_name,
        "description": f"{pc.part_name} — {pc.brand} {pc.part_number}",
        "item_group": _map_category_to_item_group(pc.category),
        "stock_uom": "Nos",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "brand": pc.brand,
        "part_number": pc.part_number,
        "part_catalog_reference": pc.name,
        "quality_tier": "OEM" if pc.is_oem else "Aftermarket",
        "default_material_request_type": "Purchase",
        "valuation_method": "FIFO",
    })

    item.insert(ignore_permissions=True)
    frappe.msgprint(_("Created Item {0} from Part Catalog").format(item.item_code))
    return item.name


@frappe.whitelist()
def auto_link_items_to_catalog():
    """
    Scheduled / admin utility:
    Find existing Items with empty part_catalog_reference but matching brand + part_number
    in Part Catalog, and link them.
    """
    items = frappe.get_all(
        "Item",
        filters={
            "part_catalog_reference": ("is", "not set"),
            "brand": ("is", "set"),
            "part_number": ("is", "set"),
        },
        fields=["name", "brand", "part_number"],
        limit_page_length=500,
    )

    linked = 0
    for item in items:
        catalog = frappe.db.get_value(
            "Part Catalog",
            {"brand": item.brand, "part_number": item.part_number},
            "name",
        )
        if catalog:
            frappe.db.set_value("Item", item.name, "part_catalog_reference", catalog)
            linked += 1

    frappe.db.commit()
    return {"linked": linked, "scanned": len(items)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_item_code(pc) -> str:
    """
    Generate a clean item code.
    Pattern: ADP-{BRAND_ABBR}-{PART_NUMBER} (sanitized)
    """
    brand_abbr = (pc.brand or "UNK")[:4].upper()
    part_clean = (pc.part_number or "").replace("-", "").replace(" ", "").upper()
    if len(part_clean) > 15:
        part_clean = part_clean[:15]
    return f"ADP-{brand_abbr}-{part_clean}"


def _map_category_to_item_group(category: str) -> str:
    """
    Map Part Catalog category to ERPNext Item Group.
    Falls back to 'Auto Parts' if not found.
    """
    if not category:
        return "Auto Parts"

    mapping = {
        "Brake": "Brake System",
        "Suspension": "Suspension & Steering",
        "Engine": "Engine Components",
        "Electrical": "Electrical",
        "Body": "Body Parts",
        "Transmission": "Transmission",
        "Cooling": "Cooling System",
        "Fuel": "Fuel System",
        "Exhaust": "Exhaust System",
        "Interior": "Interior Parts",
    }
    if category in mapping:
        return mapping[category]

    groups = frappe.get_all("Item Group", filters={"name": ("like", f"%{category}%")}, limit=1)
    if groups:
        return groups[0].name

    return "Auto Parts"
