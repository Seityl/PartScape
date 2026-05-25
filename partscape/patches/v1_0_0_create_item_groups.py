"""
PartScape Patch — Create curated auto-parts Item Group hierarchy.

Builds a standard industry hierarchy under 'Auto Parts' root group.
Idempotent: skips groups that already exist.
"""

import frappe


# Full auto-parts hierarchy: parent -> [children]
AUTO_PARTS_HIERARCHY = {
    "Auto Parts": {
        "is_group": 1,
        "children": {
            "Brake System": {
                "is_group": 1,
                "children": [
                    "Brake Pads & Shoes",
                    "Brake Discs & Rotors",
                    "Brake Calipers",
                    "Brake Drums",
                    "Brake Master Cylinder",
                    "Brake Hoses & Lines",
                ],
            },
            "Engine Components": {
                "is_group": 1,
                "children": [
                    "Engine Mounts",
                    "Timing Components",
                    "Gaskets & Seals",
                    "Pistons & Rings",
                    "Camshaft & Valvetrain",
                    "Belts & Chains",
                ],
            },
            "Cooling System": {
                "is_group": 1,
                "children": [
                    "Radiators",
                    "Water Pumps",
                    "Thermostats",
                    "Cooling Hoses",
                ],
            },
            "Fuel System": {
                "is_group": 1,
                "children": [
                    "Fuel Pumps",
                    "Fuel Injectors",
                    "Fuel Filters",
                    "Fuel Tanks",
                ],
            },
            "Exhaust System": {
                "is_group": 1,
                "children": [
                    "Catalytic Converters",
                    "Mufflers",
                    "Exhaust Pipes",
                    "Exhaust Manifolds",
                ],
            },
            "Suspension & Steering": {
                "is_group": 1,
                "children": [
                    "Shock Absorbers",
                    "Struts",
                    "Control Arms",
                    "Ball Joints",
                    "Tie Rods",
                    "Steering Rack",
                    "Suspension Springs",
                ],
            },
            "Transmission & Drivetrain": {
                "is_group": 1,
                "children": [
                    "Clutch Components",
                    "Gearbox Parts",
                    "CV Joints & Boots",
                    "Driveshafts",
                    "Differential",
                ],
            },
            "Electrical": {
                "is_group": 1,
                "children": [
                    "Alternators & Starters",
                    "Batteries",
                    "Sensors",
                    "Switches & Relays",
                    "Lighting",
                ],
            },
            "Body Parts": {
                "is_group": 1,
                "children": [
                    "Bumpers",
                    "Fenders",
                    "Hoods",
                    "Doors",
                    "Mirrors",
                    "Grilles",
                    "Body Lights",
                ],
            },
            "Interior": {
                "is_group": 1,
                "children": [
                    "Seats",
                    "Dashboard Components",
                    "Trim & Mats",
                ],
            },
            "Air Conditioning & Heating": {
                "is_group": 1,
                "children": [
                    "AC Compressors",
                    "AC Condensers",
                    "AC Evaporators",
                    "Heater Cores",
                ],
            },
            "Filters": {
                "is_group": 1,
                "children": [
                    "Oil Filters",
                    "Air Filters",
                    "Fuel Filters",
                    "Cabin Filters",
                ],
            },
            "Ignition System": {
                "is_group": 1,
                "children": [
                    "Spark Plugs",
                    "Ignition Coils",
                    "Distributors",
                ],
            },
            "Wheels & Tires": {
                "is_group": 1,
                "children": [
                    "Rims",
                    "Tires",
                    "Hubcaps",
                ],
            },
            "Oils & Fluids": {
                "is_group": 1,
                "children": [
                    "Engine Oil",
                    "Transmission Fluid",
                    "Brake Fluid",
                    "Coolant",
                ],
            },
            "Belts, Tensioners & Pulleys": {"is_group": 0},
            "Accessories": {
                "is_group": 1,
                "children": [
                    "General Accessories",
                ],
            },
            "Tools & Equipment": {"is_group": 0},
        },
    },
}


def execute():
    """Create the Auto Parts Item Group tree."""
    created = 0
    skipped = 0

    for root_name, root_def in AUTO_PARTS_HIERARCHY.items():
        root_parent = "All Item Groups"
        if not frappe.db.exists("Item Group", root_name):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": root_name,
                "parent_item_group": root_parent,
                "is_group": root_def.get("is_group", 0),
            }).insert(ignore_permissions=True)
            created += 1
        else:
            skipped += 1

        children = root_def.get("children", {})
        for child_name, child_def in children.items():
            if not frappe.db.exists("Item Group", child_name):
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": child_name,
                    "parent_item_group": root_name,
                    "is_group": child_def.get("is_group", 0),
                }).insert(ignore_permissions=True)
                created += 1
            else:
                skipped += 1

            # Leaf children
            leaf_children = child_def.get("children", [])
            for leaf_name in leaf_children:
                if not frappe.db.exists("Item Group", leaf_name):
                    frappe.get_doc({
                        "doctype": "Item Group",
                        "item_group_name": leaf_name,
                        "parent_item_group": child_name,
                        "is_group": 0,
                    }).insert(ignore_permissions=True)
                    created += 1
                else:
                    skipped += 1

    frappe.db.commit()
    print(f"Item Groups: {created} created, {skipped} already existed.")
