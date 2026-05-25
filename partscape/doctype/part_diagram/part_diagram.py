"""
Partscape — Part Diagram Controller

Stores exploded view diagram images as private file attachments.
Deduplicated by SHA-256 hash of image content.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PartDiagram(Document):
    def validate(self):
        if not self.vehicle_model:
            frappe.throw(_("Vehicle Model is required."))
        if not self.diagram_number:
            frappe.throw(_("Diagram Number (hash) is required."))

    def on_trash(self):
        """Clean up attached file when diagram is deleted."""
        files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Part Diagram", "attached_to_name": self.name},
            fields=["name"],
        )
        for f in files:
            frappe.delete_doc("File", f.name, ignore_permissions=True)
