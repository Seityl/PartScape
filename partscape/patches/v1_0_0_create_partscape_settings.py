"""
PartScape Patch — Create default PartScape Settings record.
"""

import frappe


def execute():
    if frappe.db.exists("PartScape Settings"):
        return

    # Try to find sensible defaults from existing ERPNext setup
    settings = {"doctype": "PartScape Settings"}

    # Default warehouse
    wh = frappe.get_all("Warehouse", filters={"is_group": 0}, limit=1)
    if wh:
        settings["default_warehouse"] = wh[0].name

    # Default item group
    ig = frappe.get_all("Item Group", filters={"name": ["in", ["Products", "Raw Material", "Consumable"]]}, limit=1)
    if ig:
        settings["default_item_group"] = ig[0].name
    else:
        ig = frappe.get_all("Item Group", filters={"is_group": 0}, limit=1)
        if ig:
            settings["default_item_group"] = ig[0].name

    # Default UOM
    uom = frappe.get_all("UOM", filters={"name": "Nos"}, limit=1)
    if not uom:
        uom = frappe.get_all("UOM", limit=1)
    if uom:
        settings["default_uom"] = uom[0].name

    # Default income account
    income = frappe.get_all(
        "Account",
        filters={"account_type": ["in", ["Income Account", "Sales"]], "is_group": 0},
        limit=1,
    )
    if income:
        settings["default_income_account"] = income[0].name

    # Default expense account
    expense = frappe.get_all(
        "Account",
        filters={"account_type": ["in", ["Cost of Goods Sold", "Expense Account"]], "is_group": 0},
        limit=1,
    )
    if expense:
        settings["default_expense_account"] = expense[0].name

    # Default cost center
    cc = frappe.get_all("Cost Center", filters={"is_group": 0}, limit=1)
    if cc:
        settings["default_buying_cost_center"] = cc[0].name
        settings["default_selling_cost_center"] = cc[0].name

    doc = frappe.get_doc(settings)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Created PartScape Settings with defaults.")
