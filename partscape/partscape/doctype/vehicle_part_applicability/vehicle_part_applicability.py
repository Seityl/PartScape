"""
PartScape — Vehicle Part Applicability Controller

Links a Part Catalog entry (typically OEM) to a specific vehicle configuration.
Aftermarket alternatives inherit applicability through the interchange graph.

Read-only fields (year_start, year_end, steering_position, market_code) are
auto-populated from the linked Vehicle Model record.
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

        self._auto_populate_from_vehicle_model()
        self._validate_variant_matches_model()

        # Warn if linked part is not OEM — applicability should primarily be on OEM rows
        pc = frappe.db.get_value(
            "Part Catalog",
            self.part_catalog,
            ["is_oem", "brand", "oem_make"],
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

    def _auto_populate_from_vehicle_model(self):
        """Copy year/steering/market fields from Vehicle Model."""
        model = frappe.db.get_value(
            "Vehicle Model",
            self.vehicle_model,
            ["year_start", "year_end", "steering_position", "primary_market"],
            as_dict=True,
        )
        if not model:
            return

        self.year_start = model.year_start
        self.year_end = model.year_end
        self.market_code = model.primary_market

        steering = model.steering_position
        if steering == "RHD":
            self.steering_position = "RHD"
        elif steering == "LHD":
            self.steering_position = "LHD"
        else:
            self.steering_position = "Universal"

    def _validate_variant_matches_model(self):
        """Ensure the selected engine variant belongs to the chosen vehicle model."""
        if not self.variant:
            return

        variant_model = frappe.db.get_value(
            "Vehicle Engine Variant", self.variant, "model"
        )
        if variant_model and variant_model != self.vehicle_model:
            frappe.throw(
                _(
                    "Variant {0} does not belong to Vehicle Model {1}."
                ).format(self.variant, self.vehicle_model)
            )
