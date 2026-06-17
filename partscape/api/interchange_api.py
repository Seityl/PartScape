"""
PartScape — Interchange API

Reads interchange relationships stored as child-table rows on Part Catalog.
Each Part Catalog record has an "Alternate Parts" table; rows are kept
bidirectional, so any alternate listed on one part is also listed on the other.
"""

import frappe
from frappe import _


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_interchange_numbers(part_catalog: str) -> list:
    """
    Return a list of human-readable interchange strings for a given Part Catalog doc.

    Example output:
        ["Bosch 0 986 494 046 (OEM Equivalent)", "Akebono ACT1293 (Aftermarket)"]
    """
    if not part_catalog:
        return []

    rows = _find_interchange_rows(part_catalog)
    results = []
    for other, meta in rows.items():
        pc = frappe.db.get_value(
            "Part Catalog", other, ["brand", "part_number"], as_dict=True
        )
        if pc:
            results.append(f"{pc.brand} {pc.part_number} ({meta.quality_tier})")
    return results


@frappe.whitelist()
def find_equivalents(brand: str, part_number: str) -> list:
    """
    Find all equivalent parts for a given brand + part_number.

    Returns list of dicts with full Part Catalog info and relationship metadata.
    """
    if not brand or not part_number:
        return []

    source = frappe.db.get_value(
        "Part Catalog",
        {"brand": brand, "part_number": part_number},
        "name",
    )
    if not source:
        return []

    rows = _find_interchange_rows(source)
    results = []
    for other, meta in rows.items():
        pc = frappe.db.get_value(
            "Part Catalog",
            other,
            ["brand", "part_number", "part_name", "is_oem", "estimated_cost_usd"],
            as_dict=True,
        )
        if pc:
            results.append({
                "brand": pc.brand,
                "part_number": pc.part_number,
                "part_name": pc.part_name,
                "is_oem": pc.is_oem,
                "estimated_cost_usd": pc.estimated_cost_usd,
                "relationship_type": meta.relationship_type,
                "quality_tier": meta.quality_tier,
                "confidence_score": meta.confidence_score,
            })
    return results


@frappe.whitelist()
def find_oem_by_aftermarket(brand: str, part_number: str) -> list:
    """
    Reverse lookup: given an aftermarket brand + part number,
    return matching OEM parts via the interchange graph.
    """
    if not brand or not part_number:
        return []

    source = frappe.db.get_value(
        "Part Catalog",
        {"brand": brand, "part_number": part_number},
        "name",
    )
    if not source:
        return []

    rows = _find_interchange_rows(source)
    results = []
    for other, meta in rows.items():
        pc = frappe.db.get_value(
            "Part Catalog",
            other,
            ["brand", "part_number", "part_name", "is_oem", "oem_make"],
            as_dict=True,
        )
        if pc and pc.is_oem:
            oem_make_name = frappe.db.get_value("Vehicle Make", pc.oem_make, "make_name")
            results.append({
                "brand": pc.brand,
                "part_number": pc.part_number,
                "part_name": pc.part_name,
                "oem_make": oem_make_name or pc.oem_make,
                "quality_tier": meta.quality_tier,
                "confidence_score": meta.confidence_score,
            })
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_interchange_rows(part_catalog_name: str):
    """
    Return a dict of {other_part_name: row} for all interchanges of the given part.

    Queries both directions because child rows are stored per parent, and a part
    may appear as the child-row `part` on another Part Catalog record.
    """
    result = {}

    # Rows where the given part is the parent
    for row in frappe.get_all(
        "Part Catalog Interchange",
        filters={"parent": part_catalog_name},
        fields=["part", "relationship_type", "quality_tier", "confidence_score"],
    ):
        result[row.part] = row

    # Rows where the given part is the child (parent is the other part)
    for row in frappe.get_all(
        "Part Catalog Interchange",
        filters={"part": part_catalog_name},
        fields=["parent", "relationship_type", "quality_tier", "confidence_score"],
    ):
        if row.parent not in result:
            result[row.parent] = row

    return result
