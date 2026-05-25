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
    settings = _get_settings()

    # Ensure brand exists in ERPNext
    if pc.brand and not frappe.db.exists("Brand", pc.brand):
        frappe.get_doc({"doctype": "Brand", "brand": pc.brand}).insert(ignore_permissions=True)

    item_dict = {
        "doctype": "Item",
        "item_code": item_code,
        "item_name": pc.part_name,
        "description": f"{pc.part_name} — {pc.brand} {pc.part_number}",
        "item_group": _map_category_to_item_group(pc.category, settings),
        "stock_uom": settings.get("default_uom") or "Nos",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "brand": pc.brand,
        "part_number": pc.part_number,
        "part_catalog_reference": pc.name,
        "quality_tier": "OEM" if pc.is_oem else "Aftermarket",
        "default_material_request_type": "Purchase",
        "valuation_method": "FIFO",
    }

    # Item Defaults
    defaults = _build_item_defaults(settings)
    if defaults:
        item_dict["item_defaults"] = defaults

    item = frappe.get_doc(item_dict)
    item.insert(ignore_permissions=True)

    # Link supplier references
    _link_supplier_items(item, pc.name)

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

def _get_settings() -> dict:
    """Read PartScape Settings; return empty dict if not configured."""
    if not frappe.db.exists("PartScape Settings"):
        return {}
    doc = frappe.get_doc("PartScape Settings")
    return {
        "default_warehouse": doc.get("default_warehouse"),
        "default_income_account": doc.get("default_income_account"),
        "default_expense_account": doc.get("default_expense_account"),
        "default_buying_cost_center": doc.get("default_buying_cost_center"),
        "default_selling_cost_center": doc.get("default_selling_cost_center"),
        "default_item_group": doc.get("default_item_group"),
        "default_uom": doc.get("default_uom"),
    }


def _build_item_defaults(settings: dict) -> list:
    """Build Item Defaults child table rows from PartScape Settings."""
    defaults = []
    company = frappe.defaults.get_user_default("Company")
    if not company:
        # Try to find any company
        companies = frappe.get_all("Company", limit=1)
        if companies:
            company = companies[0].name

    if not company:
        return defaults

    default_row = {"company": company}
    has_any = False

    if settings.get("default_warehouse"):
        default_row["default_warehouse"] = settings["default_warehouse"]
        has_any = True
    if settings.get("default_income_account"):
        default_row["income_account"] = settings["default_income_account"]
        has_any = True
    if settings.get("default_expense_account"):
        default_row["expense_account"] = settings["default_expense_account"]
        has_any = True
    if settings.get("default_buying_cost_center"):
        default_row["buying_cost_center"] = settings["default_buying_cost_center"]
        has_any = True
    if settings.get("default_selling_cost_center"):
        default_row["selling_cost_center"] = settings["default_selling_cost_center"]
        has_any = True

    if has_any:
        defaults.append(default_row)

    return defaults


def _link_supplier_items(item, part_catalog_name: str):
    """Populate Item Supplier child table from Part Supplier Reference."""
    supplier_refs = frappe.get_all(
        "Part Supplier Reference",
        filters={"part_catalog": part_catalog_name},
        fields=["supplier", "supplier_part_number"],
        limit=10,
    )
    for ref in supplier_refs:
        item.append("supplier_items", {
            "supplier": ref.supplier,
            "supplier_part_no": ref.supplier_part_number,
        })
    if supplier_refs:
        item.save(ignore_permissions=True)


def _generate_item_code(pc) -> str:
    """
    Generate a clean item code.
    Pattern: AD-{BRAND_ABBR}-{PART_NUMBER} (sanitized)
    """
    brand_abbr = (pc.brand or "UNK")[:4].upper()
    part_clean = (pc.part_number or "").replace("-", "").replace(" ", "").upper()
    if len(part_clean) > 15:
        part_clean = part_clean[:15]
    return f"AD-{brand_abbr}-{part_clean}"


def _map_category_to_item_group(category: str, settings: dict = None) -> str:
    """
    Map Part Catalog category to ERPNext Item Group.
    Priority:
      1. Cached item_group on the Part Category doc
      2. Keyword mapper (runtime fallback)
      3. PartScape Settings default_item_group
      4. PartScape Settings default_root_item_group
      5. Hard fallback 'Auto Parts'
    """
    from partscape.utils.category_mapper import map_category_to_item_group

    if not category:
        return _fallback_item_group(settings)

    # 1. Check cached mapping on Part Category
    cached = frappe.db.get_value("Part Category", {"category_name": category}, "item_group")
    if cached and frappe.db.exists("Item Group", cached):
        return cached

    # 2. Runtime keyword mapper
    mapped = map_category_to_item_group(category)
    if mapped:
        return mapped

    # 3-5. Fallback chain
    return _fallback_item_group(settings)


def _fallback_item_group(settings: dict = None) -> str:
    """Return the best available fallback Item Group."""
    if settings:
        if settings.get("default_item_group"):
            return settings["default_item_group"]
        if settings.get("default_root_item_group"):
            return settings["default_root_item_group"]
    return "Auto Parts"
