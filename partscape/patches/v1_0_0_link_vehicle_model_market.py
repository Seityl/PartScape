"""
PartScape Patch — Convert Vehicle Model.primary_market from Select to Link (Market).

Creates standard Market records if missing and rewrites existing Vehicle Model
primary_market values as Market links.
"""

import frappe


MARKETS = [
    ("JDM", "Japanese Domestic Market", "Japan"),
    ("UKDM", "United Kingdom Domestic Market", "United Kingdom"),
    ("AUM", "Australian Market", "Australia"),
    ("USDM", "United States Domestic Market", "United States"),
    ("EUDM", "European Domestic Market", "Europe"),
    ("Global", "Global / Multiple Markets", "Global"),
]


def execute():
    print("=" * 60)
    print("PartScape — Link Vehicle Model.primary_market to Market")
    print("=" * 60)

    # 1. Ensure standard Market records exist
    print("[1/2] Ensuring Market records exist...")
    created = 0
    for code, name, country in MARKETS:
        if not frappe.db.exists("Market", code):
            frappe.get_doc({
                "doctype": "Market",
                "market_code": code,
                "market_name": name,
                "description": country,
            }).insert(ignore_permissions=True)
            created += 1
    print(f"  -> {created} new Market records created")

    # 2. Rewrite Vehicle Model primary_market Select values to Market links
    print("[2/2] Rewriting Vehicle Model primary_market values...")
    values = frappe.db.sql(
        "SELECT DISTINCT primary_market FROM `tabVehicle Model` "
        "WHERE primary_market IS NOT NULL AND primary_market != ''",
        as_dict=True,
    )
    updated = 0
    for row in values:
        code = (row.primary_market or "").strip()
        if not code:
            continue
        if not frappe.db.exists("Market", code):
            # Create on-the-fly for any unknown value
            frappe.get_doc({
                "doctype": "Market",
                "market_code": code,
                "market_name": code,
            }).insert(ignore_permissions=True)
        count = frappe.db.sql(
            "UPDATE `tabVehicle Model` SET primary_market = %s WHERE primary_market = %s",
            (code, code),
        )
        updated += frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(f"  -> {updated} Vehicle Model records updated")

    frappe.db.commit()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
