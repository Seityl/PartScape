"""
PartScape — Comprehensive Database Seeder

Seeds the complete auto parts database:
- Part Categories (taxonomy)
- Part Catalog (OEM + aftermarket parts with realistic part numbers)
- Vehicle Part Applicability (fitment matrix)
- Part Interchanges (cross-references)
- Part Supplier References (supplier SKUs)
- Vehicles (sample fleet)

Uses actual OEM part numbering conventions for Toyota, Nissan, Honda, Suzuki.
"""

import random
import frappe
from frappe.utils import cint

# ── Part Category Taxonomy ──────────────────────────────────────────────────

PART_CATEGORIES = [
    {"category_name": "Engine", "description": "Engine blocks, heads, gaskets, pistons, rings, bearings, timing components"},
    {"category_name": "Transmission", "description": "Gearboxes, clutches, CV joints, driveshafts, differential"},
    {"category_name": "Brakes", "description": "Pads, rotors, calipers, master cylinders, brake lines, ABS modules"},
    {"category_name": "Suspension", "description": "Shocks, struts, springs, control arms, bushings, ball joints, tie rods"},
    {"category_name": "Steering", "description": "Power steering pumps, racks, columns, tie rods, steering wheels"},
    {"category_name": "Electrical", "description": "Alternators, starters, batteries, sensors, wiring harnesses, ECUs"},
    {"category_name": "Body", "description": "Bumpers, fenders, doors, hoods, mirrors, lights, grilles, glass"},
    {"category_name": "Interior", "description": "Seats, dashboards, carpets, door panels, switches, instruments"},
    {"category_name": "Exhaust", "description": "Manifolds, catalytic converters, mufflers, pipes, O2 sensors"},
    {"category_name": "Cooling", "description": "Radiators, water pumps, thermostats, hoses, fans, heaters"},
    {"category_name": "Fuel System", "description": "Injectors, pumps, filters, rails, tanks, lines, charcoal canisters"},
    {"category_name": "AC / Heating", "description": "Compressors, condensers, evaporators, blower motors, HVAC controls"},
    {"category_name": "Filters", "description": "Oil, air, fuel, cabin filters"},
    {"category_name": "Belts & Chains", "description": "Timing belts, serpentine belts, chains, tensioners"},
    {"category_name": "Lubricants", "description": "Engine oil, transmission fluid, brake fluid, coolant, grease"},
]

# ── OEM Part Number Templates ───────────────────────────────────────────────

PART_TEMPLATES = {
    "Toyota": {
        "Brakes": {
            "front_pad": {"pattern": "04465-{:05d}", "name": "Front Brake Pad Set", "price_range": (45, 120)},
            "rear_pad": {"pattern": "04466-{:05d}", "name": "Rear Brake Pad Set", "price_range": (35, 90)},
            "front_rotor": {"pattern": "43512-{:05d}", "name": "Front Brake Disc", "price_range": (60, 180)},
            "rear_rotor": {"pattern": "42431-{:05d}", "name": "Rear Brake Disc", "price_range": (50, 150)},
            "caliper": {"pattern": "47750-{:05d}", "name": "Brake Caliper Assembly", "price_range": (120, 350)},
        },
        "Suspension": {
            "shock_front": {"pattern": "48510-{:05d}", "name": "Front Shock Absorber", "price_range": (80, 220)},
            "shock_rear": {"pattern": "48530-{:05d}", "name": "Rear Shock Absorber", "price_range": (70, 200)},
            "control_arm": {"pattern": "48069-{:05d}", "name": "Front Lower Control Arm", "price_range": (90, 250)},
            "ball_joint": {"pattern": "43330-{:05d}", "name": "Lower Ball Joint", "price_range": (25, 70)},
            "tie_rod": {"pattern": "45046-{:05d}", "name": "Tie Rod End", "price_range": (30, 80)},
        },
        "Engine": {
            "oil_filter": {"pattern": "90915-{:05d}", "name": "Oil Filter", "price_range": (8, 25)},
            "air_filter": {"pattern": "17801-{:05d}", "name": "Air Filter Element", "price_range": (15, 45)},
            "spark_plug": {"pattern": "90919-{:05d}", "name": "Spark Plug (Iridium)", "price_range": (12, 35)},
            "timing_belt": {"pattern": "13568-{:05d}", "name": "Timing Belt", "price_range": (40, 110)},
            "water_pump": {"pattern": "16100-{:05d}", "name": "Water Pump Assembly", "price_range": (55, 160)},
            "gasket_head": {"pattern": "11115-{:05d}", "name": "Cylinder Head Gasket", "price_range": (35, 95)},
        },
        "Transmission": {
            "clutch_disc": {"pattern": "31250-{:05d}", "name": "Clutch Disc", "price_range": (80, 220)},
            "clutch_cover": {"pattern": "31210-{:05d}", "name": "Clutch Pressure Plate", "price_range": (90, 250)},
            "release_bearing": {"pattern": "31230-{:05d}", "name": "Clutch Release Bearing", "price_range": (30, 85)},
            "cv_joint": {"pattern": "43410-{:05d}", "name": "CV Joint Assembly (Outer)", "price_range": (70, 200)},
        },
        "Cooling": {
            "radiator": {"pattern": "16400-{:05d}", "name": "Radiator Assembly", "price_range": (120, 400)},
            "thermostat": {"pattern": "90916-{:05d}", "name": "Thermostat", "price_range": (15, 45)},
            "hose_upper": {"pattern": "16571-{:05d}", "name": "Upper Radiator Hose", "price_range": (20, 55)},
            "hose_lower": {"pattern": "16572-{:05d}", "name": "Lower Radiator Hose", "price_range": (20, 55)},
            "fan_motor": {"pattern": "16363-{:05d}", "name": "Radiator Fan Motor", "price_range": (60, 180)},
        },
        "Electrical": {
            "alternator": {"pattern": "27060-{:05d}", "name": "Alternator Assembly", "price_range": (180, 550)},
            "starter": {"pattern": "28100-{:05d}", "name": "Starter Motor", "price_range": (150, 450)},
            "battery": {"pattern": "28800-{:05d}", "name": "Battery (55D23R)", "price_range": (90, 180)},
            "ignition_coil": {"pattern": "90919-{:05d}", "name": "Ignition Coil", "price_range": (45, 130)},
        },
        "Body": {
            "headlight": {"pattern": "81110-{:05d}", "name": "Headlight Assembly (LH)", "price_range": (120, 450)},
            "taillight": {"pattern": "81560-{:05d}", "name": "Taillight Assembly (LH)", "price_range": (80, 280)},
            "bumper_front": {"pattern": "52119-{:05d}", "name": "Front Bumper Cover", "price_range": (150, 500)},
            "mirror": {"pattern": "87910-{:05d}", "name": "Side Mirror Assembly (LH)", "price_range": (100, 350)},
        },
        "Filters": {
            "cabin_filter": {"pattern": "87139-{:05d}", "name": "Cabin Air Filter", "price_range": (12, 35)},
            "fuel_filter": {"pattern": "23300-{:05d}", "name": "Fuel Filter", "price_range": (25, 70)},
        },
        "Exhaust": {
            "muffler": {"pattern": "17430-{:05d}", "name": "Exhaust Muffler", "price_range": (120, 400)},
            "cat_converter": {"pattern": "17410-{:05d}", "name": "Catalytic Converter", "price_range": (300, 900)},
            "o2_sensor": {"pattern": "89465-{:05d}", "name": "Oxygen Sensor", "price_range": (60, 180)},
        },
    },
    "Nissan": {
        "Brakes": {
            "front_pad": {"pattern": "D1060-{:05d}", "name": "Front Brake Pad Set", "price_range": (40, 110)},
            "rear_pad": {"pattern": "D4060-{:05d}", "name": "Rear Brake Pad Set", "price_range": (35, 95)},
            "front_rotor": {"pattern": "40206-{:05d}", "name": "Front Brake Disc", "price_range": (55, 170)},
            "rear_rotor": {"pattern": "43206-{:05d}", "name": "Rear Brake Disc", "price_range": (50, 150)},
        },
        "Suspension": {
            "shock_front": {"pattern": "E4302-{:05d}", "name": "Front Shock Absorber", "price_range": (75, 210)},
            "shock_rear": {"pattern": "E4303-{:05d}", "name": "Rear Shock Absorber", "price_range": (70, 200)},
            "control_arm": {"pattern": "54501-{:05d}", "name": "Front Lower Control Arm", "price_range": (85, 240)},
        },
        "Engine": {
            "oil_filter": {"pattern": "15208-{:05d}", "name": "Oil Filter", "price_range": (8, 25)},
            "air_filter": {"pattern": "16546-{:05d}", "name": "Air Filter Element", "price_range": (15, 45)},
            "spark_plug": {"pattern": "22401-{:05d}", "name": "Spark Plug (Iridium)", "price_range": (12, 35)},
            "timing_chain": {"pattern": "13028-{:05d}", "name": "Timing Chain", "price_range": (45, 130)},
            "water_pump": {"pattern": "21010-{:05d}", "name": "Water Pump Assembly", "price_range": (55, 160)},
        },
        "Transmission": {
            "clutch_disc": {"pattern": "30100-{:05d}", "name": "Clutch Disc", "price_range": (80, 220)},
            "cv_joint": {"pattern": "39600-{:05d}", "name": "CV Joint Assembly", "price_range": (70, 200)},
        },
        "Cooling": {
            "radiator": {"pattern": "21410-{:05d}", "name": "Radiator Assembly", "price_range": (120, 400)},
        },
        "Electrical": {
            "alternator": {"pattern": "23100-{:05d}", "name": "Alternator Assembly", "price_range": (180, 550)},
            "starter": {"pattern": "23300-{:05d}", "name": "Starter Motor", "price_range": (150, 450)},
            "battery": {"pattern": "24410-{:05d}", "name": "Battery", "price_range": (90, 180)},
        },
        "Body": {
            "headlight": {"pattern": "26060-{:05d}", "name": "Headlight Assembly (LH)", "price_range": (120, 450)},
            "taillight": {"pattern": "26555-{:05d}", "name": "Taillight Assembly (LH)", "price_range": (80, 280)},
        },
        "Exhaust": {
            "o2_sensor": {"pattern": "226A0-{:05d}", "name": "Oxygen Sensor", "price_range": (60, 180)},
        },
    },
    "Honda": {
        "Brakes": {
            "front_pad": {"pattern": "45022-{:05d}", "name": "Front Brake Pad Set", "price_range": (40, 110)},
            "rear_pad": {"pattern": "43022-{:05d}", "name": "Rear Brake Pad Set", "price_range": (35, 95)},
            "front_rotor": {"pattern": "45251-{:05d}", "name": "Front Brake Disc", "price_range": (55, 170)},
        },
        "Suspension": {
            "shock_front": {"pattern": "51605-{:05d}", "name": "Front Shock Absorber", "price_range": (75, 210)},
            "control_arm": {"pattern": "51350-{:05d}", "name": "Front Lower Control Arm", "price_range": (85, 240)},
        },
        "Engine": {
            "oil_filter": {"pattern": "15400-{:05d}", "name": "Oil Filter", "price_range": (8, 25)},
            "air_filter": {"pattern": "17220-{:05d}", "name": "Air Filter Element", "price_range": (15, 45)},
            "spark_plug": {"pattern": "12290-{:05d}", "name": "Spark Plug (Iridium)", "price_range": (12, 35)},
            "timing_belt": {"pattern": "14400-{:05d}", "name": "Timing Belt", "price_range": (40, 110)},
            "water_pump": {"pattern": "19200-{:05d}", "name": "Water Pump Assembly", "price_range": (55, 160)},
        },
        "Transmission": {
            "clutch_disc": {"pattern": "22200-{:05d}", "name": "Clutch Disc", "price_range": (80, 220)},
            "cv_joint": {"pattern": "44305-{:05d}", "name": "CV Joint Assembly", "price_range": (70, 200)},
        },
        "Electrical": {
            "alternator": {"pattern": "31100-{:05d}", "name": "Alternator Assembly", "price_range": (180, 550)},
            "starter": {"pattern": "31200-{:05d}", "name": "Starter Motor", "price_range": (150, 450)},
        },
        "Body": {
            "headlight": {"pattern": "33151-{:05d}", "name": "Headlight Assembly (LH)", "price_range": (120, 450)},
            "taillight": {"pattern": "33551-{:05d}", "name": "Taillight Assembly (LH)", "price_range": (80, 280)},
        },
    },
    "Suzuki": {
        "Brakes": {
            "front_pad": {"pattern": "55810-{:05d}", "name": "Front Brake Pad Set", "price_range": (35, 100)},
            "rear_pad": {"pattern": "55820-{:05d}", "name": "Rear Brake Pad Set", "price_range": (30, 85)},
        },
        "Engine": {
            "oil_filter": {"pattern": "16510-{:05d}", "name": "Oil Filter", "price_range": (8, 25)},
            "air_filter": {"pattern": "13780-{:05d}", "name": "Air Filter Element", "price_range": (15, 45)},
            "spark_plug": {"pattern": "09482-{:05d}", "name": "Spark Plug", "price_range": (10, 30)},
        },
        "Suspension": {
            "shock_front": {"pattern": "41601-{:05d}", "name": "Front Shock Absorber", "price_range": (70, 200)},
        },
        "Electrical": {
            "alternator": {"pattern": "31400-{:05d}", "name": "Alternator Assembly", "price_range": (160, 500)},
        },
    },
}

# ── Suppliers ───────────────────────────────────────────────────────────────

SUPPLIERS = [
    {"name": "Nippon Auto Parts Ltd", "currency": "JPY", "lead_time": 21, "moq": 5},
    {"name": "Tokyo Motor Trading Co", "currency": "JPY", "lead_time": 14, "moq": 10},
    {"name": "Osaka Brake & Suspension", "currency": "JPY", "lead_time": 18, "moq": 5},
    {"name": "Denso International", "currency": "USD", "lead_time": 30, "moq": 20},
    {"name": "Bosch Automotive SEA", "currency": "USD", "lead_time": 25, "moq": 10},
    {"name": "KYB Shock Absorbers JP", "currency": "JPY", "lead_time": 14, "moq": 8},
    {"name": "Guangzhou Auto Parts Hub", "currency": "USD", "lead_time": 35, "moq": 50},
    {"name": "Singapore Motor Spares", "currency": "SGD", "lead_time": 10, "moq": 5},
]

# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_or_create_item_group(name):
    """Category now links to Item Group instead of Part Category."""
    existing = frappe.db.get_value("Item Group", {"item_group_name": name}, "name")
    if existing:
        return existing
    parent_group = "Auto Parts" if frappe.db.exists("Item Group", "Auto Parts") else "All Item Groups"
    doc = frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": name,
        "parent_item_group": parent_group,
        "is_group": 0,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _ensure_brand(brand_name: str) -> str:
    if not brand_name:
        return None
    existing = frappe.db.get_value("Brand", {"brand": brand_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Brand", "brand": brand_name})
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _ensure_market(market_code: str) -> str:
    if not market_code:
        return None
    existing = frappe.db.get_value("Market", {"market_code": market_code}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "Market",
        "market_code": market_code,
        "market_name": market_code,
    })
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    return doc.name


def _get_or_create_supplier(name, currency, lead_time, moq):
    existing = frappe.db.get_value("Supplier", {"supplier_name": name}, "name")
    if not existing:
        try:
            country = "Japan" if currency == "JPY" else ("Singapore" if currency == "SGD" else "United States")
            doc = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": name,
                "supplier_type": "Company",
                "country": country,
            })
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            existing = doc.name
        except Exception:
            existing = None
    return existing


def _generate_part_number(make, category_key, part_key, seq):
    templates = PART_TEMPLATES.get(make, {})
    cat_templates = templates.get(category_key, {})
    tmpl = cat_templates.get(part_key)
    if tmpl:
        return tmpl["pattern"].format(26000 + seq)
    prefixes = {"Toyota": "90080", "Nissan": "01553", "Honda": "90105", "Suzuki": "09103"}
    return f"{prefixes.get(make, '00000')}-{26000 + seq:05d}"


def _part_name(make, category_key, part_key):
    templates = PART_TEMPLATES.get(make, {})
    cat_templates = templates.get(category_key, {})
    tmpl = cat_templates.get(part_key)
    if tmpl:
        return tmpl["name"]
    return f"{make} {category_key} Part"


def _part_price(make, category_key, part_key):
    templates = PART_TEMPLATES.get(make, {})
    cat_templates = templates.get(category_key, {})
    tmpl = cat_templates.get(part_key)
    if tmpl:
        low, high = tmpl["price_range"]
        return round(random.uniform(low, high), 2)
    return round(random.uniform(20, 200), 2)


# ── Main Seeder ─────────────────────────────────────────────────────────────

def execute():
    frappe.flags.ignore_permissions = True

    print("=" * 60)
    print("PartScape — Comprehensive Database Seeder")
    print("=" * 60)

    # ── 1. Seed Item Groups for Part Categories ─────────────────────────────
    print("\n[1/7] Seeding Item Groups...")
    category_map = {}
    for cat in PART_CATEGORIES:
        name = _get_or_create_item_group(cat["category_name"])
        category_map[cat["category_name"]] = name
    print(f"   → {len(category_map)} item groups ready")

    # ── 2. Seed Suppliers ───────────────────────────────────────────────────
    print("\n[2/7] Seeding Suppliers...")
    supplier_map = {}
    for sup in SUPPLIERS:
        name = _get_or_create_supplier(sup["name"], sup["currency"], sup["lead_time"], sup["moq"])
        if name:
            supplier_map[sup["name"]] = {
                "name": name,
                "currency": sup["currency"],
                "lead_time": sup["lead_time"],
                "moq": sup["moq"],
            }
    print(f"   → {len(supplier_map)} suppliers ready")

    # ── 3. Seed Part Catalog ────────────────────────────────────────────────
    print("\n[3/7] Seeding Part Catalog...")
    models = frappe.get_all("Vehicle Model", fields=["name", "model_name", "make", "year_start", "year_end", "body_type", "steering_position"])
    makes = frappe.get_all("Vehicle Make", fields=["name", "make_name"])
    make_name_to_doc = {m.make_name: m.name for m in makes}

    # Build reverse lookup: which models use which make
    make_models = {}
    for model in models:
        make_models.setdefault(model.make, []).append(model)

    # Track parts: key = (make, category_key, part_key) -> {"docname": ..., "part_number": ...}
    part_catalog_map = {}
    part_seq = 0

    for make_name, model_list in make_models.items():
        if make_name not in PART_TEMPLATES:
            continue

        make_docname = make_name_to_doc.get(make_name)
        if not make_docname:
            continue

        # Use first model's steering for default
        default_steering = model_list[0].steering_position or "RHD"

        for category_key, parts in PART_TEMPLATES[make_name].items():
            cat_docname = category_map.get(category_key)
            if not cat_docname:
                continue

            for part_key, tmpl in parts.items():
                part_seq += 1
                part_number = _generate_part_number(make_name, category_key, part_key, part_seq)
                part_name = _part_name(make_name, category_key, part_key)
                price = _part_price(make_name, category_key, part_key)

                existing = frappe.db.get_value("Part Catalog", {"brand": make_name, "part_number": part_number}, "name")
                if existing:
                    part_catalog_map[(make_name, category_key, part_key)] = {"docname": existing, "part_number": part_number}
                    continue

                brand_docname = _ensure_brand(make_name)
                market_docname = _ensure_market("JDM" if default_steering == "RHD" else "")

                doc = frappe.get_doc({
                    "doctype": "Part Catalog",
                    "brand": brand_docname,
                    "part_number": part_number,
                    "part_name": part_name,
                    "oem_make": make_docname,
                    "is_oem": 1,
                    "category": cat_docname,
                    "description": f"Genuine OEM {make_name} {part_name.lower()}.",
                    "estimated_cost_usd": price,
                    "is_active": 1,
                    "steering_position": default_steering,
                    "market_restriction": market_docname,
                })
                try:
                    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    part_catalog_map[(make_name, category_key, part_key)] = {"docname": doc.name, "part_number": part_number}
                except Exception as e:
                    print(f"   WARN: Could not insert part {part_number}: {e}")

    print(f"   → {len(part_catalog_map)} parts in catalog")

    # ── 4. Seed Vehicle Part Applicability ──────────────────────────────────
    print("\n[4/7] Seeding Vehicle Part Applicability...")
    applicability_count = 0

    for make_name, model_list in make_models.items():
        if make_name not in PART_TEMPLATES:
            continue

        for category_key, parts in PART_TEMPLATES[make_name].items():
            for part_key in parts:
                part_info = part_catalog_map.get((make_name, category_key, part_key))
                if not part_info:
                    continue

                part_docname = part_info["docname"]
                try:
                    part_doc = frappe.get_doc("Part Catalog", part_docname)
                    existing_models = {a.vehicle_model for a in part_doc.applicable_vehicles}

                    for model in model_list:
                        if model.name in existing_models:
                            continue
                        part_doc.append("applicable_vehicles", {
                            "vehicle_model": model.name,
                            "year_start": cint(model.year_start) if model.year_start else 2000,
                            "year_end": cint(model.year_end) if model.year_end else 2024,
                            "steering_position": model.steering_position or "RHD",
                            "market_code": "JDM",
                        })
                        applicability_count += 1

                    if len(part_doc.applicable_vehicles) > len(existing_models):
                        part_doc.save(ignore_permissions=True)
                except Exception as e:
                    print(f"   WARN: Applicability error for {part_info['part_number']}: {e}")

    print(f"   → {applicability_count} applicability records created")

    # ── 5. Seed Part Interchanges ───────────────────────────────────────────
    print("\n[5/7] Seeding Part Interchanges...")
    interchange_count = 0
    part_list = list(part_catalog_map.values())
    random.shuffle(part_list)

    for i in range(0, min(len(part_list) - 1, 200)):
        part_a = part_list[i]["docname"]
        part_b = part_list[i + 1]["docname"]

        if part_a == part_b:
            continue

        rel_type = random.choice(["Equivalent", "Aftermarket Alternative", "OEM Equivalent"])
        quality = random.choice(["OEM Equivalent", "Aftermarket", "Performance"])
        confidence = round(random.uniform(0.7, 0.99), 2)

        existing = frappe.db.get_value("Part Interchange", {
            "part_a": part_a,
            "part_b": part_b,
        }, "name")
        if existing:
            continue

        doc = frappe.get_doc({
            "doctype": "Part Interchange",
            "part_a": part_a,
            "part_b": part_b,
            "relationship_type": rel_type,
            "quality_tier": quality,
            "confidence_score": confidence,
            "source": "PartScape Auto-Seed",
        })
        try:
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            interchange_count += 1
        except Exception:
            pass

    print(f"   → {interchange_count} interchange records created")

    # ── 7. Seed Part Supplier References ────────────────────────────────────
    print("\n[6/7] Seeding Part Supplier References...")
    supplier_ref_count = 0
    supplier_list = list(supplier_map.values())

    for part_info in list(part_list)[:min(len(part_list), 800)]:
        part_docname = part_info["docname"]
        supplier_info = random.choice(supplier_list)
        sup_docname = supplier_info["name"]
        sup_currency = supplier_info["currency"]
        lead_time = supplier_info["lead_time"]
        moq = supplier_info["moq"]

        base_price = frappe.db.get_value("Part Catalog", part_docname, "estimated_cost_usd") or 50
        supplier_price = round(base_price * random.uniform(0.8, 1.2), 2)
        part_brand = frappe.db.get_value("Part Catalog", part_docname, "brand")
        part_num = frappe.db.get_value("Part Catalog", part_docname, "part_number")
        supplier_part_no = f"{part_brand[:3].upper()}-{part_num[-5:]}"

        existing = frappe.db.get_value("Part Supplier Reference", {
            "part_catalog": part_docname,
            "supplier": sup_docname,
        }, "name")
        if existing:
            continue

        doc = frappe.get_doc({
            "doctype": "Part Supplier Reference",
            "part_catalog": part_docname,
            "supplier": sup_docname,
            "supplier_part_number": supplier_part_no,
            "lead_time_days": lead_time,
            "moq": moq,
            "unit_cost_usd": supplier_price,
            "currency": sup_currency,
        })
        try:
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            supplier_ref_count += 1
        except Exception:
            pass

    print(f"   → {supplier_ref_count} supplier reference records created")

    # ── 8. Seed Vehicles ────────────────────────────────────────────────────
    print("\n[7/7] Seeding Vehicles...")
    vehicle_count = 0

    sample_vins = [
        ("KDH201-0149586", "Toyota", "Hiace Van"),
        ("KDH205-0234511", "Toyota", "Hiace Van"),
        ("TRH200-0098723", "Toyota", "Hiace Van"),
        ("KUN25-0456123", "Toyota", "Hilux"),
        ("GUN125-0789012", "Toyota", "Hilux"),
        ("NCP91-0567823", "Toyota", "Vitz"),
        ("KSP90-0345621", "Toyota", "Vitz"),
        ("NZE141-0678901", "Toyota", "Corolla Axio"),
        ("NZE161-0987654", "Toyota", "Corolla Axio"),
        ("VAY12-0123456", "Nissan", "AD Van"),
        ("VJY12-0234567", "Nissan", "AD Van"),
        ("VY12-0345678", "Nissan", "AD Van"),
        ("E11-0456789", "Nissan", "Note"),
        ("E12-0567890", "Nissan", "Note"),
        ("GD1-0678901", "Honda", "Fit"),
        ("GE8-0789012", "Honda", "Fit"),
        ("GK5-0890123", "Honda", "Fit"),
        ("ZC11S-0901234", "Suzuki", "Swift"),
        ("ZC72S-0112345", "Suzuki", "Swift"),
        ("ZC33S-0223456", "Suzuki", "Swift"),
    ]

    real_vins = [
        "JT3HN86RXW0136794",
        "JN6MD06S9DW012345",
        "JHMGK4H58DX012345",
        "JS3TD62V0Y4101234",
        "JTMBK32V795012345",
        "JTEBU5JR7B5123456",
    ]

    all_vins = sample_vins + [(v, None, None) for v in real_vins]

    for vin_entry in all_vins:
        if len(vin_entry) == 3 and vin_entry[1]:
            vin, make_name, model_name = vin_entry
            matching_models = [m for m in models if m.make == make_name and m.model_name == model_name]
            if not matching_models:
                continue
            model = random.choice(matching_models)
        else:
            vin = vin_entry[0]
            model = random.choice(models)
            make_name = model.make

        year = random.randint(
            cint(model.year_start) if model.year_start else 2005,
            cint(model.year_end) if model.year_end else 2024,
        )

        existing = frappe.db.get_value("Vehicle", {"vin": vin}, "name")
        if existing:
            continue

        doc = frappe.get_doc({
            "doctype": "Vehicle",
            "vin": vin,
            "make": make_name_to_doc.get(make_name),
            "model": model.name,
            "year": year,
            "color": random.choice(["White", "Silver", "Black", "Blue", "Red", "Grey", "Pearl White"]),
            "registration_no": f"{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(1000, 9999)}",
            "steering_position": model.steering_position or "RHD",
            "market_code": "JDM",
            "status": "Active",
            "mileage": random.randint(15000, 180000),
        })
        try:
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            vehicle_count += 1
        except Exception as e:
            print(f"   WARN: Could not insert vehicle {vin}: {e}")

    print(f"   → {vehicle_count} vehicles seeded")

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)
    print(f"Item Groups:            {len(category_map)}")
    print(f"Part Catalog:           {len(part_catalog_map)}")
    print(f"Applicability Records:  {applicability_count}")
    print(f"Part Interchanges:      {interchange_count}")
    print(f"Supplier References:    {supplier_ref_count}")
    print(f"Vehicles:               {vehicle_count}")
    print("=" * 60)
