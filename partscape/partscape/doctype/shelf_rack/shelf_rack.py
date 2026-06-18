import frappe
from frappe import _
from frappe.model.document import Document


class ShelfRack(Document):
    def validate(self):
        self._set_title()
        self._enforce_unique_code_per_warehouse()

    def before_save(self):
        self._set_title()

    def _set_title(self):
        if not self.shelf_rack_code:
            return
        warehouse_name = ""
        if self.warehouse:
            warehouse_name = frappe.db.get_value("Warehouse", self.warehouse, "warehouse_name") or self.warehouse
        self.shelf_rack_title = f"{self.shelf_rack_code} - {warehouse_name}".strip(" -")

    def _enforce_unique_code_per_warehouse(self):
        if not self.shelf_rack_code or not self.warehouse:
            return

        filters = {
            "shelf_rack_code": self.shelf_rack_code,
            "warehouse": self.warehouse,
        }
        if not self.is_new():
            filters["name"] = ("!=", self.name)

        existing = frappe.db.exists("Shelf Rack", filters)
        if existing:
            frappe.throw(
                _(
                    "A Shelf / Rack with code {0} already exists in warehouse {1}."
                ).format(
                    frappe.bold(self.shelf_rack_code),
                    frappe.bold(self.warehouse),
                )
            )
