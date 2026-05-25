"""
Partscape — Part Catalog Controller

Universal parts registry. Identity is composite: (brand, part_number).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PartCatalog(Document):
    def validate(self):
        self._ensure_composite_uniqueness()
        self._auto_set_oem_flag()
        self._normalize_fields()

    def autoname(self):
        """Name = 'Brand PartNumber' for human-readable linking."""
        brand = (self.brand or "UNKNOWN").strip()
        part_no = (self.part_number or "N/A").strip()
        self.name = f"{brand} {part_no}"

    def _ensure_composite_uniqueness(self):
        """Prevent duplicate (brand, part_number) entries."""
        if not self.brand or not self.part_number:
            frappe.throw(_("Brand and Part Number are required."))

        existing = frappe.db.get_value(
            "Part Catalog",
            {
                "brand": self.brand.strip(),
                "part_number": self.part_number.strip(),
                "name": ("!=", self.name),
            },
            "name",
        )
        if existing:
            frappe.throw(
                _(
                    "Part Catalog entry already exists for {0} {1}: {2}"
                ).format(self.brand, self.part_number, existing)
            )

    def _auto_set_oem_flag(self):
        """Set is_oem if the brand matches the vehicle manufacturer name."""
        if self.vehicle_make and self.brand:
            make_name = frappe.db.get_value("Vehicle Make", self.vehicle_make, "make_name")
            if make_name and make_name.strip().lower() == self.brand.strip().lower():
                self.is_oem = 1
            else:
                # Only auto-clear if explicitly mismatched; preserve manual override otherwise
                pass

    def _normalize_fields(self):
        self.brand = (self.brand or "").strip()
        self.part_number = (self.part_number or "").strip().upper()
        if self.part_name:
            self.part_name = self.part_name.strip()

    def on_update(self):
        """If this part is OEM, ensure Vehicle Part Applicability records are consistent."""
        pass  # Placeholder for future sync logic
