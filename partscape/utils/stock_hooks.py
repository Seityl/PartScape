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
        if not hasattr(doc, 'partscape_default_vehicle'):
            return
        for item in doc.items:
            if hasattr(item, 'vehicle_consumed_by') and not item.vehicle_consumed_by and doc.partscape_default_vehicle:
                item.vehicle_consumed_by = doc.partscape_default_vehicle
