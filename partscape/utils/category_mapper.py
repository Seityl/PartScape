"""
PartScape — Part Category → Item Group Mapper

Maps the 688 TecDoc/Qubdi Part Categories to the curated ERPNext
Item Group hierarchy using keyword-based rules.
"""

import frappe
from frappe import _


# Keyword → Item Group mapping.
# Order matters: more specific keywords should come BEFORE broader ones.
CATEGORY_KEYWORDS = [
    # ── Brake System ──
    ("brake pad", "Brake Pads & Shoes"),
    ("brake shoe", "Brake Pads & Shoes"),
    ("brake disc", "Brake Discs & Rotors"),
    ("brake rotor", "Brake Discs & Rotors"),
    ("brake drum", "Brake Drums"),
    ("brake caliper", "Brake Calipers"),
    ("brake master", "Brake Master Cylinder"),
    ("brake cylinder", "Brake Master Cylinder"),
    ("brake hose", "Brake Hoses & Lines"),
    ("brake line", "Brake Hoses & Lines"),
    ("brake", "Brake System"),
    ("abs", "Brake System"),

    # ── Engine Components ──
    ("engine mount", "Engine Mounts"),
    ("timing belt", "Timing Components"),
    ("timing chain", "Timing Components"),
    ("timing", "Timing Components"),
    ("gasket", "Gaskets & Seals"),
    ("seal", "Gaskets & Seals"),
    ("piston", "Pistons & Rings"),
    ("camshaft", "Camshaft & Valvetrain"),
    ("valve", "Camshaft & Valvetrain"),
    ("rocker arm", "Camshaft & Valvetrain"),
    ("engine", "Engine Components"),
    ("cylinder head", "Engine Components"),
    ("crankshaft", "Engine Components"),
    ("connecting rod", "Engine Components"),

    # ── Cooling System ──
    ("radiator", "Radiators"),
    ("water pump", "Water Pumps"),
    ("thermostat", "Thermostats"),
    ("cooling hose", "Cooling Hoses"),
    ("coolant hose", "Cooling Hoses"),
    ("cooling", "Cooling System"),
    ("intercooler", "Cooling System"),
    ("charge air cooler", "Cooling System"),

    # ── Fuel System ──
    ("fuel pump", "Fuel Pumps"),
    ("fuel injector", "Fuel Injectors"),
    ("fuel filter", "Fuel Filters"),
    ("fuel tank", "Fuel Tanks"),
    ("fuel", "Fuel System"),
    ("carburetor", "Fuel System"),
    ("injection", "Fuel System"),
    ("gas system", "Fuel System"),

    # ── Exhaust System ──
    ("catalytic", "Catalytic Converters"),
    ("cat converter", "Catalytic Converters"),
    ("muffler", "Mufflers"),
    ("silencer", "Mufflers"),
    ("exhaust pipe", "Exhaust Pipes"),
    ("exhaust manifold", "Exhaust Manifolds"),
    ("exhaust", "Exhaust System"),
    ("downpipe", "Exhaust System"),

    # ── Suspension & Steering ──
    ("shock absorber", "Shock Absorbers"),
    ("shock", "Shock Absorbers"),
    ("strut", "Struts"),
    ("control arm", "Control Arms"),
    ("ball joint", "Ball Joints"),
    ("tie rod", "Tie Rods"),
    ("steering rack", "Steering Rack"),
    ("steering pump", "Steering Rack"),
    ("steering gear", "Steering Rack"),
    ("spring", "Suspension Springs"),
    ("coil spring", "Suspension Springs"),
    ("leaf spring", "Suspension Springs"),
    ("suspension", "Suspension & Steering"),
    ("steering", "Suspension & Steering"),
    ("stabilizer", "Suspension & Steering"),
    ("sway bar", "Suspension & Steering"),
    ("wishbone", "Suspension & Steering"),

    # ── Transmission & Drivetrain ──
    ("clutch", "Clutch Components"),
    ("gearbox", "Gearbox Parts"),
    ("transmission", "Gearbox Parts"),
    ("cv joint", "CV Joints & Boots"),
    ("driveshaft", "Driveshafts"),
    ("propeller shaft", "Driveshafts"),
    ("differential", "Differential"),
    ("cardan", "Driveshafts"),
    ("bridge", "Differential"),

    # ── Electrical ──
    ("alternator", "Alternators & Starters"),
    ("starter", "Alternators & Starters"),
    ("battery", "Batteries"),
    ("sensor", "Sensors"),
    ("switch", "Switches & Relays"),
    ("relay", "Switches & Relays"),
    ("headlight", "Lighting"),
    ("taillight", "Lighting"),
    ("fog light", "Lighting"),
    ("bulb", "Lighting"),
    ("lamp", "Lighting"),
    ("lighting", "Lighting"),
    ("electrical", "Electrical"),
    ("electricity", "Electrical"),
    ("wiper motor", "Electrical"),
    ("window lifter", "Electrical"),
    ("horn", "Electrical"),
    ("audio", "Electrical"),
    ("radio", "Electrical"),
    ("speaker", "Electrical"),

    # ── Body Parts ──
    ("bumper", "Bumpers"),
    ("fender", "Fenders"),
    ("hood", "Hoods"),
    ("bonnet", "Hoods"),
    ("door", "Doors"),
    ("mirror", "Mirrors"),
    ("grille", "Grilles"),
    ("body light", "Body Lights"),
    ("tail light", "Body Lights"),
    ("body", "Body Parts"),
    ("trunk", "Trunk and components"),
    ("boot lid", "Trunk and components"),
    ("radiator panel", "Body Parts"),
    ("protective", "Body Parts"),

    # ── Interior ──
    ("seat", "Seats"),
    ("dashboard", "Dashboard Components"),
    ("trim", "Trim & Mats"),
    ("mat", "Trim & Mats"),
    ("interior", "Interior"),
    ("ceiling", "Interior"),
    ("sun visor", "Interior"),
    ("armrest", "Interior"),
    ("console", "Interior"),

    # ── Air Conditioning & Heating ──
    ("compressor", "AC Compressors"),
    ("condenser", "AC Condensers"),
    ("evaporator", "AC Evaporators"),
    ("heater core", "Heater Cores"),
    ("heater radiator", "Heater Cores"),
    ("heater", "Air Conditioning & Heating"),
    ("air conditioner", "Air Conditioning & Heating"),
    ("ac ", "Air Conditioning & Heating"),
    ("climate", "Air Conditioning & Heating"),
    ("furnace", "Air Conditioning & Heating"),

    # ── Filters ──
    ("oil filter", "Oil Filters"),
    ("air filter", "Air Filters"),
    ("fuel filter", "Fuel Filters"),
    ("cabin filter", "Cabin Filters"),
    ("pollen filter", "Cabin Filters"),
    ("filter", "Filters"),

    # ── Ignition System ──
    ("spark plug", "Spark Plugs"),
    ("ignition coil", "Ignition Coils"),
    ("distributor", "Distributors"),
    ("ignition", "Ignition System"),
    ("coil", "Ignition Coils"),

    # ── Wheels & Tires ──
    ("rim", "Rims"),
    ("wheel", "Rims"),
    ("tire", "Tires"),
    ("tyre", "Tires"),
    ("hubcap", "Hubcaps"),

    # ── Oils & Fluids ──
    ("engine oil", "Engine Oil"),
    ("motor oil", "Engine Oil"),
    ("transmission fluid", "Transmission Fluid"),
    ("gear oil", "Transmission Fluid"),
    ("brake fluid", "Brake Fluid"),
    ("coolant", "Coolant"),
    ("antifreeze", "Coolant"),
    ("oil", "Oils & Fluids"),
    ("fluid", "Oils & Fluids"),
    ("grease", "Oils & Fluids"),
    ("lubricant", "Oils & Fluids"),

    # ── Belts, Tensioners & Pulleys ──
    ("tensioner", "Belts, Tensioners & Pulleys"),
    ("pulley", "Belts, Tensioners & Pulleys"),
    ("v-belt", "Belts, Tensioners & Pulleys"),
    ("serpentine", "Belts, Tensioners & Pulleys"),
    ("belt", "Belts, Tensioners & Pulleys"),

    # ── Accessories & Tools ──
    ("accessory", "Accessories"),
    ("car pump", "Accessories"),
    ("child seat", "Accessories"),
    ("phone holder", "Accessories"),
    ("roof rack", "Accessories"),
    ("towing", "Accessories"),
    ("trailer", "Accessories"),
    ("winch", "Accessories"),
    ("sticker", "Accessories"),
    ("sunshade", "Accessories"),
    ("seat cover", "Accessories"),
    ("tool", "Tools & Equipment"),
    ("equipment", "Tools & Equipment"),

    # ── Catch-alls for top-level categories ──
    ("check system", "Electrical"),
    ("control panel", "Electrical"),
    ("indicator", "Electrical"),
    ("moto equipment", "Accessories"),
    ("auto chemistry", "Oils & Fluids"),
    ("autochemistry", "Oils & Fluids"),
    ("painting", "Accessories"),
    ("polishing", "Accessories"),
    ("front bumper", "Bumpers"),
    ("rear bumper", "Rear bumpers and components"),
    ("turbo", "Engine Components"),
    ("supercharger", "Engine Components"),
    ("intake", "Engine Components"),
    ("airbag", "Body Parts"),
    ("windshield", "Body Parts"),
    ("window", "Body Parts"),
    ("glass", "Body Parts"),
    ("wiper", "Body Parts"),
]


def map_category_to_item_group(category_name: str) -> str:
    """
    Map a Part Category name to an Item Group using keyword matching.
    Returns the Item Group name or None if no match.
    """
    if not category_name:
        return None

    cat_lower = category_name.lower()

    for keyword, item_group in CATEGORY_KEYWORDS:
        if keyword in cat_lower:
            # Verify the Item Group exists
            if frappe.db.exists("Item Group", item_group):
                return item_group

    return None


def map_all_categories():
    """
    Run the mapper over all Part Categories and populate the
    item_group field. Returns stats.
    """
    categories = frappe.get_all(
        "Part Category",
        fields=["name", "category_name", "parent_category"],
        limit_page_length=0,
    )

    mapped = 0
    fallback_to_parent = 0
    unmapped = 0

    for cat in categories:
        # Try direct keyword match
        group = map_category_to_item_group(cat.category_name)

        # If no match, try parent category
        if not group and cat.parent_category:
            group = map_category_to_item_group(cat.parent_category)
            if group:
                fallback_to_parent += 1

        if group:
            frappe.db.set_value("Part Category", cat.name, "item_group", group)
            mapped += 1
        else:
            unmapped += 1

    frappe.db.commit()
    return {
        "total": len(categories),
        "mapped": mapped,
        "fallback_to_parent": fallback_to_parent,
        "unmapped": unmapped,
    }
