"""
Patch: Seed comprehensive global vehicle makes + common JDM models.

Creates Vehicle Make records for all major manufacturers worldwide,
plus commonly imported JDM models pre-populated.
"""

import frappe


GLOBAL_MAKES = [
    # Japanese (primary JDM market)
    ("Toyota", "JPY", "JT,MR0,ML0,NMT,SJN"),
    ("Honda", "JPY", "JHM,MLH,SHH,LUC,NLA"),
    ("Nissan", "JPY", "JN1,JN6,MNT,SJN,ML0"),
    ("Suzuki", "JPY", "JSA,JST,MLC,TMA,TSM"),
    ("Mitsubishi", "JPY", "JA3,JA4,JLF,JMY,MMB"),
    ("Mazda", "JPY", "JM1,JM6,MM6,RFB,RF5"),
    ("Subaru", "JPY", "JF1,JF2,JF3,JF4,4S3"),
    ("Daihatsu", "JPY", "JD1,JD2,MLD"),
    ("Isuzu", "JPY", "JALE,JABC,JALC,LRA"),
    ("Lexus", "JPY", "JTH,JTJ,JTB,58T"),
    ("Infiniti", "JPY", "JNK,JN6,MN6"),
    ("Acura", "JPY", "19U,JH4,5J8"),
    # European
    ("Mercedes-Benz", "DEU", "WDB,WDD,WDC,4JG,NMB"),
    ("BMW", "DEU", "WBA,WBS,3AV,5UX,MMF"),
    ("Volkswagen", "DEU", "WVW,3VW,1VW,WV1,WV2"),
    ("Audi", "DEU", "WAU,WA1,TRU,WUA"),
    ("Porsche", "DEU", "WP0,WP1,WPO"),
    ("Volvo", "SWE", "YV1,YV4,LVY,7JR"),
    ("Land Rover", "GBR", "SAL,SAJ,SAR,LRB"),
    ("Jaguar", "GBR", "SAJ,SAD"),
    ("Peugeot", "FRA", "VF3,VF6,VF7,VFA"),
    ("Renault", "FRA", "VF1,VF2,ML1,SB1"),
    ("Citroen", "FRA", "VF7,VR7,8BB"),
    ("Fiat", "ITA", "ZFA,ZFB,3C3"),
    ("Alfa Romeo", "ITA", "ZAR"),
    # American
    ("Ford", "USA", "1FT,1FM,1FA,3FA,MAJ,MPA,WF0"),
    ("Chevrolet", "USA", "1GC,1G1,3GN,KL1"),
    ("Dodge", "USA", "1B3,1C3,2B3,3C3"),
    ("Jeep", "USA", "1J4,1C4,3C4"),
    ("Chrysler", "USA", "1C3,2C3,3C3"),
    ("GMC", "USA", "1GT,1G2,3G7"),
    ("Cadillac", "USA", "1G6"),
    ("Lincoln", "USA", "1LN,2LN"),
    ("Tesla", "USA", "5YJ,7SA,LRW,SFZ"),
    # Korean
    ("Hyundai", "KOR", "KMH,KM8,MLH,NLH,TMA"),
    ("Kia", "KOR", "KNA,KNB,KNC,MLH,3KP"),
    ("Genesis", "KOR", "KMT,NLH"),
    # Other
    ("Tata", "IND", "MAT,ME3"),
    ("Mahindra", "IND", "MA1,MA3"),
    ("Proton", "MYS", "PL1"),
    ("Perodua", "MYS", "PL8"),
    ("Holden", "AUS", "6G1,8AK"),
]

# Common JDM models to pre-seed
COMMON_JDM_MODELS = [
    # (make, model, model_code, body, year_start, year_end, steering, market, variants)
    ("Toyota", "Hiace Van", "KDH201", "Van", 2012, 2020, "RHD", "JDM", [("1KD-FTV", "2982 cc", "Diesel", "4AT", "2WD"), ("2KD-FTV", "2494 cc", "Diesel", "5MT", "2WD"), ("1GD-FTV", "2755 cc", "Diesel", "6AT", "2WD")]),
    ("Toyota", "Hiace Van", "TRH200", "Van", 2005, 2012, "RHD", "JDM", [("2TR-FE", "2694 cc", "Petrol", "4AT", "2WD")]),
    ("Toyota", "Hiace Regius", "KCH40", "Van", 1997, 2002, "RHD", "JDM", [("1KZ-TE", "2982 cc", "Diesel", "4AT", "2WD")]),
    ("Toyota", "Hilux", "GUN125", "Pickup", 2015, 2020, "RHD", "JDM", [("2GD-FTV", "2393 cc", "Diesel", "6MT", "4WD"), ("1GD-FTV", "2755 cc", "Diesel", "6AT", "4WD")]),
    ("Toyota", "Hilux", "KUN26", "Pickup", 2005, 2015, "RHD", "JDM", [("1KD-FTV", "2982 cc", "Diesel", "5MT", "4WD")]),
    ("Toyota", "Land Cruiser Prado", "GRJ150", "SUV", 2010, 2020, "RHD", "JDM", [("1GR-FE", "3956 cc", "Petrol", "5AT", "4WD")]),
    ("Toyota", "RAV4", "ACA31", "SUV", 2006, 2012, "RHD", "JDM", [("2AZ-FE", "2362 cc", "Petrol", "CVT", "4WD")]),
    ("Toyota", "RAV4", "ALA49", "SUV", 2013, 2020, "RHD", "JDM", [("2AD-FTV", "1998 cc", "Diesel", "6AT", "4WD")]),
    ("Toyota", "Corolla Axio", "NZE141", "Sedan", 2007, 2012, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Corolla Fielder", "NZE141G", "Wagon", 2007, 2012, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Vitz", "KSP90", "Hatch", 2005, 2010, "RHD", "JDM", [("1KR-FE", "996 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Vitz", "NCP91", "Hatch", 2005, 2010, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Vitz", "NLP130", "Hatch", 2011, 2020, "RHD", "JDM", [("1NR-FE", "1329 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Passo", "KGC10", "Hatch", 2005, 2010, "RHD", "JDM", [("1KR-FE", "996 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Probox", "NCP51V", "Van", 2002, 2014, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "4AT", "2WD")]),
    ("Toyota", "Succeed", "NCP51V", "Van", 2002, 2014, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "4AT", "2WD")]),
    ("Toyota", "Noah", "ZRR70", "MPV", 2007, 2014, "RHD", "JDM", [("3ZR-FE", "1986 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Voxy", "ZRR70", "MPV", 2007, 2014, "RHD", "JDM", [("3ZR-FE", "1986 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Wish", "ZNE10", "MPV", 2003, 2009, "RHD", "JDM", [("1ZZ-FE", "1794 cc", "Petrol", "4AT", "2WD")]),
    ("Toyota", "Premio", "NZT260", "Sedan", 2007, 2020, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Allion", "NZT260", "Sedan", 2007, 2020, "RHD", "JDM", [("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Toyota", "Mark X", "GRX120", "Sedan", 2004, 2009, "RHD", "JDM", [("4GR-FSE", "2499 cc", "Petrol", "6AT", "2WD")]),
    ("Toyota", "Vanguard", "GSA33W", "SUV", 2008, 2013, "RHD", "JDM", [("2GR-FE", "3456 cc", "Petrol", "5AT", "4WD")]),
    ("Toyota", "Harrier", "ACU30", "SUV", 2003, 2013, "RHD", "JDM", [("2AZ-FE", "2362 cc", "Petrol", "CVT", "2WD")]),
    ("Nissan", "AD Van", "VAY12", "Van", 2007, 2016, "RHD", "JDM", [("CR12DE", "1240 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "AD Van", "VJY12", "Van", 2007, 2016, "RHD", "JDM", [("MR18DE", "1798 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "AD Van", "VZNY12", "Van", 2007, 2016, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "NV150 AD", "VY12", "Van", 2013, 2020, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "Note", "E11", "Hatch", 2005, 2012, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "CVT", "2WD")]),
    ("Nissan", "Note", "E12", "Hatch", 2013, 2020, "RHD", "JDM", [("HR12DE", "1198 cc", "Petrol", "CVT", "2WD")]),
    ("Nissan", "Tiida Latio", "SC11", "Sedan", 2004, 2012, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "X-Trail", "T30", "SUV", 2003, 2007, "RHD", "JDM", [("QR20DE", "1998 cc", "Petrol", "4AT", "4WD")]),
    ("Nissan", "X-Trail", "T31", "SUV", 2007, 2013, "RHD", "JDM", [("MR20DE", "1997 cc", "Petrol", "CVT", "4WD")]),
    ("Nissan", "Serena", "C25", "MPV", 2005, 2010, "RHD", "JDM", [("MR20DE", "1997 cc", "Petrol", "CVT", "2WD")]),
    ("Nissan", "Caravan", "E25", "Van", 2001, 2012, "RHD", "JDM", [("QR20DE", "1998 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "Wingroad", "Y12", "Wagon", 2005, 2018, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "CVT", "2WD")]),
    ("Nissan", "Bluebird Sylphy", "G11", "Sedan", 2006, 2012, "RHD", "JDM", [("HR15DE", "1498 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "March", "K12", "Hatch", 2003, 2010, "RHD", "JDM", [("CR12DE", "1240 cc", "Petrol", "4AT", "2WD")]),
    ("Nissan", "Navara", "D40", "Pickup", 2005, 2015, "RHD", "JDM", [("YD25", "2488 cc", "Diesel", "6MT", "4WD")]),
    ("Honda", "Fit", "GD1", "Hatch", 2005, 2008, "RHD", "JDM", [("L13A", "1339 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit", "GD3", "Hatch", 2005, 2008, "RHD", "JDM", [("L15A", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit", "GE6", "Hatch", 2008, 2013, "RHD", "JDM", [("L13A", "1339 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit", "GE8", "Hatch", 2008, 2013, "RHD", "JDM", [("L15A", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit", "GK3", "Hatch", 2014, 2020, "RHD", "JDM", [("L13B", "1318 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit", "GK5", "Hatch", 2014, 2020, "RHD", "JDM", [("L15B", "1496 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Fit Shuttle", "GP2", "Wagon", 2011, 2016, "RHD", "JDM", [("L15A", "1497 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "CR-V", "RE4", "SUV", 2007, 2012, "RHD", "JDM", [("K24A", "2354 cc", "Petrol", "5AT", "4WD")]),
    ("Honda", "CR-V", "RM4", "SUV", 2013, 2020, "RHD", "JDM", [("R20A", "1997 cc", "Petrol", "5AT", "4WD")]),
    ("Honda", "HR-V", "RU1", "SUV", 2014, 2020, "RHD", "JDM", [("R18A", "1799 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Stream", "RN6", "MPV", 2006, 2014, "RHD", "JDM", [("R18A", "1799 cc", "Petrol", "5AT", "2WD")]),
    ("Honda", "Stepwgn", "RK1", "MPV", 2005, 2009, "RHD", "JDM", [("K20A", "1998 cc", "Petrol", "5AT", "2WD")]),
    ("Honda", "Stepwgn", "RP1", "MPV", 2015, 2020, "RHD", "JDM", [("R20A", "1997 cc", "Petrol", "CVT", "2WD")]),
    ("Honda", "Civic", "FD1", "Sedan", 2006, 2011, "RHD", "JDM", [("R18A", "1799 cc", "Petrol", "5AT", "2WD")]),
    ("Honda", "Civic", "FK2", "Hatch", 2012, 2017, "RHD", "JDM", [("R18Z", "1798 cc", "Petrol", "5AT", "2WD")]),
    ("Honda", "Accord", "CL7", "Sedan", 2003, 2008, "RHD", "JDM", [("K20A", "1998 cc", "Petrol", "5AT", "2WD")]),
    ("Honda", "Accord", "CU2", "Sedan", 2009, 2013, "RHD", "JDM", [("K24A", "2354 cc", "Petrol", "5AT", "2WD")]),
    ("Suzuki", "Swift", "ZC11S", "Hatch", 2005, 2010, "RHD", "JDM", [("M13A", "1328 cc", "Petrol", "5MT", "2WD")]),
    ("Suzuki", "Swift", "ZC21S", "Hatch", 2005, 2010, "RHD", "JDM", [("M15A", "1490 cc", "Petrol", "4AT", "2WD")]),
    ("Suzuki", "Swift", "ZC71S", "Hatch", 2010, 2017, "RHD", "JDM", [("K12B", "1242 cc", "Petrol", "CVT", "2WD")]),
    ("Suzuki", "Swift", "ZC33S", "Hatch", 2017, 2020, "RHD", "JDM", [("K14C", "1372 cc", "Petrol", "6MT", "2WD")]),
    ("Suzuki", "Alto", "HA25S", "Hatch", 2009, 2014, "RHD", "JDM", [("K6A", "657 cc", "Petrol", "CVT", "2WD")]),
    ("Suzuki", "Every", "DA64V", "Van", 2005, 2015, "RHD", "JDM", [("K6A", "657 cc", "Petrol", "4AT", "2WD")]),
    ("Suzuki", "Escudo", "TD54W", "SUV", 2005, 2015, "RHD", "JDM", [("J20A", "1995 cc", "Petrol", "4AT", "4WD")]),
    ("Suzuki", "Jimny", "JB23W", "SUV", 1998, 2018, "RHD", "JDM", [("K6A", "657 cc", "Petrol", "5MT", "4WD")]),
    ("Mitsubishi", "Lancer", "CS2A", "Sedan", 2003, 2010, "RHD", "JDM", [("4G15", "1468 cc", "Petrol", "5MT", "2WD")]),
    ("Mitsubishi", "Pajero", "V93W", "SUV", 2007, 2020, "RHD", "JDM", [("6G72", "2972 cc", "Petrol", "5AT", "4WD"), ("4M41", "3200 cc", "Diesel", "5AT", "4WD")]),
    ("Mitsubishi", "L200", "KB4T", "Pickup", 2005, 2015, "RHD", "JDM", [("4D56", "2477 cc", "Diesel", "5MT", "4WD")]),
    ("Mitsubishi", "Delica", "CV5W", "Van", 2007, 2020, "RHD", "JDM", [("4B12", "2360 cc", "Petrol", "CVT", "4WD")]),
    ("Mitsubishi", "Outlander", "CW5W", "SUV", 2007, 2012, "RHD", "JDM", [("4B12", "2360 cc", "Petrol", "CVT", "4WD")]),
    ("Volkswagen", "Golf", "1K", "Hatch", 2005, 2013, "RHD", "EUDM", [("BSE", "1595 cc", "Petrol", "5MT", "2WD")]),
    ("Volkswagen", "Polo", "9N", "Hatch", 2005, 2009, "RHD", "EUDM", [("BUD", "1198 cc", "Petrol", "5MT", "2WD")]),
    ("Volkswagen", "Passat", "B6", "Sedan", 2006, 2010, "RHD", "EUDM", [("BZB", "1798 cc", "Petrol", "6AT", "2WD")]),
    ("Volkswagen", "Tiguan", "5N", "SUV", 2009, 2015, "RHD", "EUDM", [("CBAB", "1968 cc", "Diesel", "6AT", "4WD")]),
    ("Ford", "Transit", "VM", "Van", 2006, 2014, "RHD", "EUDM", [("P8FA", "2198 cc", "Diesel", "6MT", "2WD")]),
    ("Ford", "Ranger", "PX", "Pickup", 2012, 2020, "RHD", "EUDM", [("P5AT", "3196 cc", "Diesel", "6AT", "4WD")]),
]


def execute():
    # 1. Seed all global makes
    for make_name, country, wmi in GLOBAL_MAKES:
        _get_or_create_make(make_name, country, wmi)

    # 2. Seed common JDM models
    for make_name, model_name, model_code, body, ys, ye, steer, market, variants in COMMON_JDM_MODELS:
        make = _get_or_create_make(make_name)
        model = _get_or_create_model(make, model_name, model_code, body, ys, ye, steer, market)
        for engine_code, disp, fuel, trans, drive in variants:
            _get_or_create_variant(model, engine_code, disp, fuel, trans, drive)

    frappe.db.commit()


def _get_or_create_make(name, country=None, wmi=None):
    docname = frappe.db.get_value("Vehicle Make", {"make_name": name}, "name")
    if docname:
        return docname
    doc = frappe.get_doc({
        "doctype": "Vehicle Make",
        "make_name": name,
        "country_of_origin": country,
        "wmi_codes": wmi,
        "is_jdm_primary": 1 if country == "JPY" else 0,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_model(make, name, code, body, ys, ye, steer, market):
    expected_name = f"{make}-{code}"
    docname = frappe.db.get_value("Vehicle Model", {"name": expected_name}, "name")
    if docname:
        return docname
    doc = frappe.get_doc({
        "doctype": "Vehicle Model",
        "model_name": name,
        "make": make,
        "model_code": code,
        "body_type": body,
        "year_start": ys,
        "year_end": ye,
        "steering_position": steer,
        "primary_market": market,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_variant(model, engine_code, disp, fuel, trans, drive):
    expected_name = f"{model}-{engine_code}"
    docname = frappe.db.get_value("Vehicle Engine Variant", {"name": expected_name}, "name")
    if docname:
        return docname
    doc = frappe.get_doc({
        "doctype": "Vehicle Engine Variant",
        "variant_name": engine_code,
        "model": model,
        "engine_code": engine_code,
        "displacement": disp,
        "fuel_type": fuel,
        "transmission": trans,
        "drivetrain": drive,
    })
    doc.insert(ignore_permissions=True)
    return doc.name
