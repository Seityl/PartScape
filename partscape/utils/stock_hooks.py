"""
PartScape — Stock Entry Hooks
"""

import frappe
from frappe import _


def validate_stock_entry(doc, method):
    """
    Ensure job card reference and vehicle are populated on consumption entries.
    """
    if doc.purpose in ("Material Issue", "Material Consumption for Manufacture"):
        for item in doc.items:
            if not item.vehicle_consumed_by and doc.partscape_default_vehicle:
                item.vehicle_consumed_by = doc.partscape_default_vehicle
