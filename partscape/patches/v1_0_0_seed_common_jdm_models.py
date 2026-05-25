"""
Patch: Seed common JDM vehicle models
Run once after install to populate Vehicle Make, Model, and Engine Variant.
"""

import frappe


DATA = [
    # (make, model, model_code, body, year_start, year_end, steering, market, variants)
    ("Toyota", "Hiace Van", "KDH201", "Van", 2012, 2020, "RHD", "JDM", [
        ("1KD-FTV", "2982 cc", "Diesel", "4AT", "2WD"),
        ("2KD-FTV", "2494 cc", "Diesel", "5MT", "2WD"),
        ("1GD-FTV", "2755 cc", "Diesel", "6AT", "2WD"),
    ]),
    ("Toyota", "Hilux", "GUN125", "Pickup", 2015, 2020, "RHD", "JDM", [
        ("2GD-FTV", "2393 cc", "Diesel", "6MT", "4WD"),
        ("1GD-FTV", "2755 cc", "Diesel", "6AT", "4WD"),
    ]),
    ("Toyota", "Vitz", "NCP91", "Hatch", 2005, 2010, "RHD", "JDM", [
        ("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD"),
        ("2SZ-FE", "1298 cc", "Petrol", "4AT", "2WD"),
    ]),
    ("Toyota", "Corolla Axio", "NZE141", "Sedan", 2007, 2012, "RHD", "JDM", [
        ("1NZ-FE", "1497 cc", "Petrol", "CVT", "2WD"),
    ]),
    ("Nissan", "AD Van", "VAY12", "Van", 2007, 2016, "RHD", "JDM", [
        ("CR12DE", "1240 cc", "Petrol", "4AT", "2WD"),
        ("HR15DE", "1498 cc", "Petrol", "4AT", "2WD"),
    ]),
    ("Nissan", "Note", "E11", "Hatch", 2005, 2012, "RHD", "JDM", [
        ("HR15DE", "1498 cc", "Petrol", "CVT", "2WD"),
    ]),
    ("Honda", "Fit", "GD1", "Hatch", 2005, 2008, "RHD", "JDM", [
        ("L13A", "1339 cc", "Petrol", "CVT", "2WD"),
        ("L15A", "1497 cc", "Petrol", "CVT", "2WD"),
    ]),
    ("Honda", "CR-V", "RE4", "SUV", 2007, 2012, "RHD", "JDM", [
        ("K24A", "2354 cc", "Petrol", "5AT", "4WD"),
    ]),
    ("Suzuki", "Swift", "ZC11S", "Hatch", 2005, 2010, "RHD", "JDM", [
        ("M13A", "1328 cc", "Petrol", "5MT", "2WD"),
    ]),
    ("Suzuki", "Swift", "ZC72S", "Hatch", 2010, 2017, "RHD", "JDM", [
        ("K12B", "1242 cc", "Petrol", "CVT", "2WD"),
    ]),
    ("Mitsubishi", "Pajero", "V93W", "SUV", 2007, 2020, "RHD", "JDM", [
        ("6G72", "2972 cc", "Petrol", "5AT", "4WD"),
        ("4M41", "3200 cc", "Diesel", "5AT", "4WD"),
    ]),
]


def execute():
    for make_name, model_name, model_code, body, ys, ye, steer, market, variants in DATA:
        make = _get_or_create_make(make_name)
        model = _get_or_create_model(make, model_name, model_code, body, ys, ye, steer, market)
        for engine_code, disp, fuel, trans, drive in variants:
            _get_or_create_variant(model, engine_code, disp, fuel, trans, drive)
    frappe.db.commit()


def _get_or_create_make(name):
    docname = frappe.db.get_value("Vehicle Make", {"make_name": name}, "name")
    if docname:
        return docname
    doc = frappe.get_doc({"doctype": "Vehicle Make", "make_name": name, "is_jdm_primary": 1})
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_model(make, name, code, body, ys, ye, steer, market):
    docname = frappe.db.get_value("Vehicle Model", {"model_name": name, "make": make}, "name")
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
    docname = frappe.db.get_value("Vehicle Engine Variant", {
        "variant_name": engine_code,
        "model": model,
    }, "name")
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
