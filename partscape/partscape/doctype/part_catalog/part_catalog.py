"""
PartScape — Part Catalog Controller

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
        self._validate_interchanges()

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
                "brand": self.brand,
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
        """Auto-set is_oem when Brand matches the OEM Make name."""
        if self.oem_make and self.brand:
            make_name = frappe.db.get_value("Vehicle Make", self.oem_make, "make_name")
            brand_name = frappe.db.get_value("Brand", self.brand, "brand") or self.brand
            if make_name and make_name.strip().lower() == brand_name.strip().lower():
                self.is_oem = 1
            else:
                self.is_oem = 0
        else:
            self.is_oem = 0

    def _normalize_fields(self):
        self.part_number = (self.part_number or "").strip().upper()
        if self.part_name:
            self.part_name = self.part_name.strip()

    def onload(self):
        """Show the linked ERPNext Stock Item, if any."""
        self.linked_item = frappe.db.get_value(
            "Item", {"part_catalog_reference": self.name}, "name"
        )

    def on_update(self):
        """Keep interchange relationships bidirectional."""
        self._sync_interchange_reverse_rows()

    # ---------------------------------------------------------------------------
    # Interchanges
    # ---------------------------------------------------------------------------

    def _validate_interchanges(self):
        """Prevent self-references and silently de-duplicate alternate parts."""
        seen = set()
        cleaned = []
        for row in self.interchanges or []:
            if not row.part:
                continue
            if row.part == self.name:
                frappe.throw(_("A part cannot be an interchange of itself."))
            if row.part in seen:
                continue
            seen.add(row.part)
            cleaned.append(row)
        self.interchanges = cleaned

    def _sync_interchange_reverse_rows(self):
        """Mirror interchange rows on the related Part Catalog records."""
        if frappe.flags.get("skip_part_catalog_interchange_sync"):
            return

        old_doc = self.get_doc_before_save()
        old_rows = self._interchange_rows_as_dict(old_doc)
        new_rows = self._interchange_rows_as_dict(self)

        changed_parts = set()

        # Parts that were removed: delete the reverse row from them.
        for other_part, old_row in old_rows.items():
            if other_part not in new_rows:
                self._remove_reverse_row(other_part)
                changed_parts.add(other_part)

        # Parts that are present (new or changed): add/update the reverse row.
        for other_part, new_row in new_rows.items():
            old_row = old_rows.get(other_part)
            if not old_row or self._interchange_row_changed(old_row, new_row):
                self._upsert_reverse_row(other_part, new_row)
                changed_parts.add(other_part)

        if changed_parts:
            frappe.msgprint(
                _("Interchange sync updated {0} related part(s).").format(
                    len(changed_parts)
                ),
                alert=True,
            )

    def _interchange_rows_as_dict(self, doc):
        """Return {other_part_name: row_dict} for a Part Catalog doc."""
        rows = getattr(doc, "interchanges", []) or []
        return {
            row.part: row
            for row in rows
            if row.part
        }

    def _interchange_row_changed(self, old_row, new_row):
        """Compare fields that must stay in sync on the reverse row."""
        return (old_row.get("relationship_type") or "") != (
            new_row.get("relationship_type") or ""
        )

    def _upsert_reverse_row(self, other_part: str, source_row):
        """Add or update the row on `other_part` that points back to this part."""
        try:
            other = frappe.get_doc("Part Catalog", other_part)
        except frappe.DoesNotExistError:
            return

        for row in other.interchanges or []:
            if row.part == self.name:
                row.relationship_type = source_row.relationship_type
                break
        else:
            other.append(
                "interchanges",
                {
                    "part": self.name,
                    "relationship_type": source_row.relationship_type,
                },
            )

        self._save_other_part(other)

    def _remove_reverse_row(self, other_part: str):
        """Remove the row on `other_part` that points back to this part."""
        try:
            other = frappe.get_doc("Part Catalog", other_part)
        except frappe.DoesNotExistError:
            return

        other.interchanges = [
            row for row in other.interchanges or [] if row.part != self.name
        ]

        if not other.interchanges:
            other.interchanges = []

        self._save_other_part(other)

    def _save_other_part(self, other):
        """Save a related Part Catalog doc without triggering reciprocal sync."""
        frappe.flags.skip_part_catalog_interchange_sync = True
        try:
            other.save(ignore_permissions=True)
        finally:
            frappe.flags.skip_part_catalog_interchange_sync = False
