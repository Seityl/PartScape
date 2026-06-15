"""
Label Printer Settings — Single DocType for Brother QL-800 configuration.
"""

import frappe
from frappe.model.document import Document


class LabelPrinterSettings(Document):
    pass


def get_label_printer_settings():
    """Return the current Label Printer Settings document (or None)."""
    if not frappe.db.exists("Label Printer Settings"):
        return None
    return frappe.get_doc("Label Printer Settings")
