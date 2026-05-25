"""
Partscape — Interchange API

Operates on the bidirectional Part Interchange graph.
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

    Given Part Catalog doc 'Toyota 04465-26421', walks the interchange graph
    and returns strings like:
        ["Bosch 0 986 494 046 (OEM Equivalent)", "Akebono ACT1293 (Aftermarket)"]
    """
    if not part_catalog:
        return []

    rows = _find_interchange_edges(part_catalog)
    results = []
    for r in rows:
        other = r.part_b if r.part_a == part_catalog else r.part_a
        pc = frappe.db.get_value("Part Catalog", other, ["brand", "part_number"], as_dict=True)
        if pc:
            results.append(f"{pc.brand} {pc.part_number} ({r.quality_tier})")
    return results


@frappe.whitelist()
def find_equivalents(brand: str, part_number: str) -> list:
    """
    Find all equivalent parts (OEM + aftermarket) for a given brand + part_number.

    Returns list of dicts with full Part Catalog info and relationship metadata.
    """
    if not brand or not part_number:
        return []

    # Find the source Part Catalog entry
    source = frappe.db.get_value(
        "Part Catalog",
        {"brand": brand, "part_number": part_number},
        "name",
    )
    if not source:
        return []

    edges = _find_interchange_edges(source)
    results = []
    for edge in edges:
        other_name = edge.part_b if edge.part_a == source else edge.part_a
        pc = frappe.db.get_value(
            "Part Catalog",
            other_name,
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
                "relationship_type": edge.relationship_type,
                "quality_tier": edge.quality_tier,
                "confidence_score": edge.confidence_score,
            })
    return results


@frappe.whitelist()
def find_oem_by_aftermarket(brand: str, part_number: str) -> list:
    """
    Reverse lookup: given an aftermarket brand + part number,
    return matching OEM parts (is_oem == 1) via the interchange graph.
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

    edges = _find_interchange_edges(source)
    results = []
    for edge in edges:
        other_name = edge.part_b if edge.part_a == source else edge.part_a
        pc = frappe.db.get_value(
            "Part Catalog",
            other_name,
            ["brand", "part_number", "part_name", "is_oem", "vehicle_make"],
            as_dict=True,
        )
        if pc and pc.is_oem:
            vehicle_make_name = frappe.db.get_value("Vehicle Make", pc.vehicle_make, "make_name")
            results.append({
                "brand": pc.brand,
                "part_number": pc.part_number,
                "part_name": pc.part_name,
                "vehicle_make": vehicle_make_name or pc.vehicle_make,
                "quality_tier": edge.quality_tier,
                "confidence_score": edge.confidence_score,
            })
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_interchange_edges(part_catalog_name: str):
    """
    Return all Part Interchange rows where part_catalog_name is either part_a or part_b.
    """
    edges = frappe.get_all(
        "Part Interchange",
        filters={"part_a": part_catalog_name},
        fields=["name", "part_a", "part_b", "relationship_type", "quality_tier", "confidence_score"],
        order_by="confidence_score desc",
    )
    edges += frappe.get_all(
        "Part Interchange",
        filters={"part_b": part_catalog_name},
        fields=["name", "part_a", "part_b", "relationship_type", "quality_tier", "confidence_score"],
        order_by="confidence_score desc",
    )
    return edges
