"""
PartScape — Vehicle Part Applicability Controller

Links a Part Catalog entry (typically OEM) to a specific vehicle configuration.
Aftermarket alternatives inherit applicability through the interchange graph.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VehiclePartApplicability(Document):
    def validate(self):
        if not self.part_catalog:
            frappe.throw(_("Part Catalog is required."))
        if not self.vehicle_model:
            frappe.throw(_("Vehicle Model is required."))

        # Warn if linked part is not OEM — applicability should primarily be on OEM rows
        pc = frappe.db.get_value(
            "Part Catalog",
            self.part_catalog,
            ["is_oem", "brand", "vehicle_make"],
            as_dict=True,
        )
        if pc and not pc.is_oem:
            frappe.msgprint(
                _(
                    "Warning: {0} is not marked as OEM. "
                    "Vehicle applicability is typically stored on the OEM part row."
                ).format(self.part_catalog),
                indicator="orange",
                alert=True,
            )
