import frappe
from frappe.model.document import Document
from frappe import _


class Vehicle(Document):
    def validate(self):
        if not self.vin:
            frappe.throw(_("VIN / Frame Number is required"))
        self.vin = self.vin.strip().upper()
        if self.chassis_number:
            self.chassis_number = self.chassis_number.strip().upper()

        self._auto_populate_from_variant()

    def _auto_populate_from_variant(self):
        """Copy engine code and transmission from the selected Engine Variant."""
        if not self.variant:
            self.engine_code = ""
            self.transmission = ""
            return

        variant = frappe.db.get_value(
            "Vehicle Engine Variant",
            self.variant,
            ["engine_code", "transmission"],
            as_dict=True,
        )
        if variant:
            self.engine_code = variant.engine_code or ""
            self.transmission = variant.transmission or ""

    def after_insert(self):
        # Trigger async VIN decode if not already decoded
        if not self.last_vin_decode and self.vin:
            frappe.enqueue(
                "partscape.api.vin_decoder.decode_vin",
                vin=self.vin,
                queue="long",
                job_name=f"decode_vin_{self.vin}"
            )


def validate_vehicle(doc, method):
    doc.validate()


def after_insert_vehicle(doc, method):
    doc.after_insert()
