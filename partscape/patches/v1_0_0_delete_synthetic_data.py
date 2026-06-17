"""
PartScape — Delete All Synthetic/Fake Data

Removes all seeded synthetic data while preserving real imported data:
- Keeps: NHTSA/n8barr/abhionlyone/Kaggle vehicles, FPI parts
- Deletes: Synthetic parts, interchanges, seeded vehicles, fake suppliers
"""

import frappe


def execute():
    frappe.flags.ignore_permissions = True
    print("=" * 60)
    print("PartScape — Synthetic Data Cleanup")
    print("=" * 60)

    # ------------------------------------------------------------------
    # [1] Identify real parts (those with FPI supplier references)
    # ------------------------------------------------------------------
    print("\n[1/5] Identifying real parts...")
    fpi_part_names = frappe.db.sql_list("""
        SELECT DISTINCT part_catalog FROM `tabPart Supplier Reference`
        WHERE supplier = 'FPI Auto Parts'
    """)
    print(f"  → {len(fpi_part_names)} parts linked to FPI")

    # ------------------------------------------------------------------
    # [2] Delete all Part Catalog entries NOT linked to FPI
    # ------------------------------------------------------------------
    print("\n[2/5] Deleting synthetic Part Catalog entries...")
    all_part_names = frappe.db.sql_list("SELECT name FROM `tabPart Catalog`")
    synthetic_parts = [n for n in all_part_names if n not in fpi_part_names]
    print(f"  → {len(synthetic_parts)} synthetic parts to delete")

    batch_size = 100
    for i in range(0, len(synthetic_parts), batch_size):
        batch = synthetic_parts[i:i + batch_size]
        for name in batch:
            try:
                frappe.delete_doc("Part Catalog", name, ignore_permissions=True, force=True)
            except Exception as e:
                print(f"    WARN: Could not delete Part Catalog {name}: {e}")
        frappe.db.commit()
        print(f"  → Deleted batch {i//batch_size + 1}/{(len(synthetic_parts)//batch_size)+1}")

    # ------------------------------------------------------------------
    # [3] Delete all Part Interchanges (all are synthetic)
    # ------------------------------------------------------------------
    print("\n[3/5] Deleting synthetic Part Interchanges...")
    interchange_names = frappe.db.sql_list("SELECT name FROM `tabPart Interchange`")
    print(f"  → {len(interchange_names)} interchanges to delete")
    for i in range(0, len(interchange_names), batch_size):
        batch = interchange_names[i:i + batch_size]
        for name in batch:
            try:
                frappe.delete_doc("Part Interchange", name, ignore_permissions=True, force=True)
            except Exception:
                pass
        frappe.db.commit()

    # ------------------------------------------------------------------
    # [5] Delete synthetic suppliers and their refs
    # ------------------------------------------------------------------
    print("\n[4/5] Deleting synthetic suppliers and references...")
    synthetic_suppliers = [
        "Bosch Automotive SEA",
        "Denso International",
        "Guangzhou Auto Parts Hub",
        "KYB Shock Absorbers JP",
        "Nippon Auto Parts Ltd",
        "Osaka Brake & Suspension",
        "Singapore Motor Spares",
        "Tokyo Motor Trading Co",
    ]

    # Delete supplier refs first
    ref_names = frappe.db.sql_list("""
        SELECT name FROM `tabPart Supplier Reference`
        WHERE supplier IN %(suppliers)s
    """, {"suppliers": synthetic_suppliers})
    print(f"  → {len(ref_names)} synthetic supplier refs to delete")
    for name in ref_names:
        try:
            frappe.delete_doc("Part Supplier Reference", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    frappe.db.commit()

    # Delete suppliers
    for sup_name in synthetic_suppliers:
        try:
            sup_docname = frappe.db.get_value("Supplier", {"supplier_name": sup_name}, "name")
            if sup_docname:
                frappe.delete_doc("Supplier", sup_docname, ignore_permissions=True, force=True)
        except Exception:
            pass
    frappe.db.commit()

    # ------------------------------------------------------------------
    # [6] Delete synthetic vehicles (seeded ones with sample VINs)
    # ------------------------------------------------------------------
    print("\n[5/5] Deleting synthetic Vehicles...")
    # Synthetic vehicles were seeded with specific VIN patterns
    # They have colors like White, Silver, Black, Blue, Red, Grey, Pearl White
    # and are linked to the 26 seeded vehicles. We can identify them by checking
    # if their VIN starts with known patterns or if they have the synthetic flag.
    # Safer: delete vehicles that don't have a real VIN decode cache entry.
    # Even safer: the seeded vehicles had makes that are in our synthetic make list.
    synthetic_vehicle_vins = [
        "JTDBU4EE3B9123456", "5TDBK3EH8DS123456", "3N1AB7AP7KY123456",
        "MHKBA1AD0FJ123456", "JM1BL1H81A1123456", "WBA3A5G51ENS12345",
        "KMHDU4AD3AU123456", "NMTKHMBX0JR123456", "ML32A3HJ0JH123456",
        "JM1BK32F361234567", "5XYKT3A11DG123456", "3CZRE3H54AG123456",
        "JTDZN3EU5E3123456", "JTHBA1D23F5123456", "5N1AT2MKXEC123456",
        "2T3RFREV5EW123456", "WDB1260451A123456", "ZARFAEDN2G7123456",
        "WDDHF5KBXEA123456", "SALFP24N6EH123456", "WBAFR7C54CC123456",
        "WDDNG71X28A123456", "WAUWFAFL4EN123456", "ZFA25000002J12345",
        "SJNBFAC11A1234567", "VSKCVKH20JA123456",
    ]
    # Also include any vehicles with these VINs
    for vin in synthetic_vehicle_vins:
        try:
            vname = frappe.db.get_value("Vehicle", {"vin": vin}, "name")
            if vname:
                frappe.delete_doc("Vehicle", vname, ignore_permissions=True, force=True)
        except Exception:
            pass
    frappe.db.commit()

    # ------------------------------------------------------------------
    # [6] Clean up orphaned Vehicle Part Applicability child records
    # ------------------------------------------------------------------
    print("\n[6/6] Cleaning orphaned Vehicle Part Applicability records...")
    # These are child table rows in Part Catalog; if the parent was deleted,
    # Frappe should have cascade-deleted them. But let's verify.
    orphaned = frappe.db.sql("""
        SELECT name FROM `tabVehicle Part Applicability`
        WHERE parenttype = 'Part Catalog'
        AND parent NOT IN (SELECT name FROM `tabPart Catalog`)
    """)
    print(f"  → {len(orphaned)} orphaned applicability records to delete")
    for row in orphaned:
        try:
            frappe.db.delete("Vehicle Part Applicability", {"name": row[0]})
        except Exception:
            pass
    frappe.db.commit()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
    print(f"Synthetic parts deleted:        {len(synthetic_parts)}")
    print(f"Interchanges deleted:           {len(interchange_names)}")
    print(f"Supplier refs deleted:          {len(ref_names)}")
    print(f"Orphaned applicabilities:       {len(orphaned)}")
    print("=" * 60)
