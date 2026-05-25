"""
Partscape — Part Interchange Controller

Bidirectional graph edge linking two Part Catalog entries.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PartInterchange(Document):
    def validate(self):
        if self.part_a == self.part_b:
            frappe.throw(_("Part A and Part B must be different parts."))

        self._prevent_duplicate_edge()

    def _prevent_duplicate_edge(self):
        """Prevent creating the same undirected edge twice (A-B and B-A)."""
        # Check for reverse edge
        reverse = frappe.db.get_value(
            "Part Interchange",
            {
                "part_a": self.part_b,
                "part_b": self.part_a,
                "name": ("!=", self.name),
            },
            "name",
        )
        if reverse:
            frappe.throw(
                _(
                    "Reverse interchange already exists: {0}. "
                    "Interchange is bidirectional — use the existing record."
                ).format(reverse)
            )

        # Also check same-direction duplicate
        same = frappe.db.get_value(
            "Part Interchange",
            {
                "part_a": self.part_a,
                "part_b": self.part_b,
                "name": ("!=", self.name),
            },
            "name",
        )
        if same:
            frappe.throw(
                _(
                    "Interchange already exists between these parts: {0}"
                ).format(same)
            )
