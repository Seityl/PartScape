"""
PartScape Settings — Single DocType for app-wide defaults.

Includes defaults for auto-creating ERPNext Items from Part Catalog entries
and for label printing.
"""

import frappe
from frappe.model.document import Document


class PartScapeSettings(Document):
    pass
