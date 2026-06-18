import frappe
from frappe.model.document import Document
from frappe import _


class Vehicle(Document):
    def validate(self):
        if self.vin:
            self.vin = self.vin.strip().upper()
        if self.chassis_number:
            self.chassis_number = self.chassis_number.strip().upper()

        self._auto_populate_from_variant()

    def on_update(self):
        """Trigger a VIN decode when the VIN is added or changed."""
        if not self.vin:
            return

        old_vin = ""
        old_doc = self.get_doc_before_save()
        if old_doc:
            old_vin = (old_doc.vin or "").strip().upper()

        if self.vin != old_vin:
            frappe.enqueue(
                "partscape.api.vin_decoder.decode_vin",
                vin=self.vin,
                queue="long",
                job_name=f"decode_vin_{self.vin}",
            )

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
        if self.vin:
            frappe.enqueue(
                "partscape.api.vin_decoder.decode_vin",
                vin=self.vin,
                queue="long",
                job_name=f"decode_vin_{self.vin}",
            )


def validate_vehicle(doc, method):
    doc.validate()


def on_update_vehicle(doc, method):
    doc.on_update()


def after_insert_vehicle(doc, method):
    doc.after_insert()
