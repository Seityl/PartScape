"""
Partscape — VIN Decoder Service

Strategy: Cache-first with fallback chain.
- Primary: NHTSA vPIC (free, US-market 17-char VINs)
- Fallback: JDM frame-number prefix lookup (manual mapping)
- Cache: VIN Decode Cache DocType (90-day TTL)
"""

import json
import requests
import frappe
from frappe.utils import now, add_days, cint
from frappe import _

NHTSA_VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"
JDM_FRAME_PREFIXES = {
    # Toyota Hiace (H200 series)
    "KDH201": {"make": "Toyota", "model": "Hiace Van", "engine_code": "2KD-FTV", "fuel": "Diesel", "steering": "RHD"},
    "KDH205": {"make": "Toyota", "model": "Hiace Van", "engine_code": "2KD-FTV", "fuel": "Diesel", "steering": "RHD"},
    "KDH206": {"make": "Toyota", "model": "Hiace Van", "engine_code": "1KD-FTV", "fuel": "Diesel", "steering": "RHD"},
    "TRH200": {"make": "Toyota", "model": "Hiace Van", "engine_code": "2TR-FE", "fuel": "Petrol", "steering": "RHD"},
    "GDH201": {"make": "Toyota", "model": "Hiace Van", "engine_code": "1GD-FTV", "fuel": "Diesel", "steering": "RHD"},
    # Toyota Hilux
    "KUN25":  {"make": "Toyota", "model": "Hilux", "engine_code": "2KD-FTV", "fuel": "Diesel", "steering": "RHD"},
    "KUN26":  {"make": "Toyota", "model": "Hilux", "engine_code": "1KD-FTV", "fuel": "Diesel", "steering": "RHD"},
    "GUN125": {"make": "Toyota", "model": "Hilux", "engine_code": "2GD-FTV", "fuel": "Diesel", "steering": "RHD"},
    # Toyota Vitz / Yaris
    "KSP90":  {"make": "Toyota", "model": "Vitz", "engine_code": "1KR-FE", "fuel": "Petrol", "steering": "RHD"},
    "SCP90":  {"make": "Toyota", "model": "Vitz", "engine_code": "2SZ-FE", "fuel": "Petrol", "steering": "RHD"},
    "NCP91":  {"make": "Toyota", "model": "Vitz", "engine_code": "1NZ-FE", "fuel": "Petrol", "steering": "RHD"},
    "NLP130": {"make": "Toyota", "model": "Vitz", "engine_code": "1NR-FE", "fuel": "Petrol", "steering": "RHD"},
    # Toyota Corolla Axio / Fielder
    "NZE141": {"make": "Toyota", "model": "Corolla Axio", "engine_code": "1NZ-FE", "fuel": "Petrol", "steering": "RHD"},
    "NZE144": {"make": "Toyota", "model": "Corolla Axio", "engine_code": "1NZ-FE", "fuel": "Petrol", "steering": "RHD"},
    "ZRE142": {"make": "Toyota", "model": "Corolla Axio", "engine_code": "2ZR-FE", "fuel": "Petrol", "steering": "RHD"},
    "NZE161": {"make": "Toyota", "model": "Corolla Axio", "engine_code": "1NZ-FE", "fuel": "Petrol", "steering": "RHD"},
    "NRE161": {"make": "Toyota", "model": "Corolla Axio", "engine_code": "1NR-FE", "fuel": "Petrol", "steering": "RHD"},
    # Nissan AD Van / NV150 AD
    "VAY12":  {"make": "Nissan", "model": "AD Van", "engine_code": "CR12DE", "fuel": "Petrol", "steering": "RHD"},
    "VJY12":  {"make": "Nissan", "model": "AD Van", "engine_code": "MR18DE", "fuel": "Petrol", "steering": "RHD"},
    "VZNY12": {"make": "Nissan", "model": "AD Van", "engine_code": "HR15DE", "fuel": "Petrol", "steering": "RHD"},
    "VY12":   {"make": "Nissan", "model": "AD Van", "engine_code": "HR15DE", "fuel": "Petrol", "steering": "RHD"},
    # Nissan Note
    "E11":    {"make": "Nissan", "model": "Note", "engine_code": "HR15DE", "fuel": "Petrol", "steering": "RHD"},
    "E12":    {"make": "Nissan", "model": "Note", "engine_code": "HR12DE", "fuel": "Petrol", "steering": "RHD"},
    # Honda Fit
    "GD1":    {"make": "Honda", "model": "Fit", "engine_code": "L13A", "fuel": "Petrol", "steering": "RHD"},
    "GD3":    {"make": "Honda", "model": "Fit", "engine_code": "L15A", "fuel": "Petrol", "steering": "RHD"},
    "GE6":    {"make": "Honda", "model": "Fit", "engine_code": "L13A", "fuel": "Petrol", "steering": "RHD"},
    "GE8":    {"make": "Honda", "model": "Fit", "engine_code": "L15A", "fuel": "Petrol", "steering": "RHD"},
    "GK3":    {"make": "Honda", "model": "Fit", "engine_code": "L13B", "fuel": "Petrol", "steering": "RHD"},
    "GK5":    {"make": "Honda", "model": "Fit", "engine_code": "L15B", "fuel": "Petrol", "steering": "RHD"},
    # Suzuki Swift
    "ZC11S":  {"make": "Suzuki", "model": "Swift", "engine_code": "M13A", "fuel": "Petrol", "steering": "RHD"},
    "ZC21S":  {"make": "Suzuki", "model": "Swift", "engine_code": "M15A", "fuel": "Petrol", "steering": "RHD"},
    "ZC71S":  {"make": "Suzuki", "model": "Swift", "engine_code": "K12B", "fuel": "Petrol", "steering": "RHD"},
    "ZC72S":  {"make": "Suzuki", "model": "Swift", "engine_code": "K12B", "fuel": "Petrol", "steering": "RHD"},
    "ZC33S":  {"make": "Suzuki", "model": "Swift", "engine_code": "K14C", "fuel": "Petrol", "steering": "RHD"},
}


def decode_vin(vin: str, force_refresh: bool = False) -> dict:
    """
    Main entry point. Returns decoded vehicle dict.
    Caches results in VIN Decode Cache for 90 days.
    """
    vin = (vin or "").strip().upper()
    if not vin:
        frappe.throw(_("VIN/Chassis number is required"))

    # 1. Check cache
    if not force_refresh:
        cache = frappe.db.get_value(
            "VIN Decode Cache",
            {"vin": vin},
            ["name", "decoded_json", "last_decoded"],
            as_dict=True,
        )
        if cache and cache.last_decoded and cache.last_decoded >= add_days(now(), -90):
            frappe.db.set_value("VIN Decode Cache", cache.name, "hit_count", cache.hit_count + 1) if hasattr(cache, 'hit_count') else None
            return json.loads(cache.decoded_json or "{}")

    # 2. Try NHTSA (17-char VINs)
    result = {}
    if len(vin) == 17:
        result = _decode_nhtsa(vin)

    # 3. Fallback: JDM frame number prefix
    if not result:
        result = _decode_jdm_frame(vin)

    # 4. Persist cache
    _persist_cache(vin, result, source="NHTSA" if len(vin) == 17 and result else "JDM_MANUAL")
    return result


def _decode_nhtsa(vin: str) -> dict:
    """Call NHTSA vPIC API."""
    try:
        url = NHTSA_VPIC_URL.format(vin=vin)
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("Results"):
            r = data["Results"][0]
            return {
                "vin": vin,
                "make": r.get("Make", ""),
                "model": r.get("Model", ""),
                "year": cint(r.get("ModelYear", 0)),
                "engine_code": r.get("EngineModel", ""),
                "engine_cylinders": cint(r.get("EngineCylinders", 0)),
                "engine_displacement": r.get("DisplacementL", ""),
                "transmission": r.get("TransmissionStyle", ""),
                "steering_location": r.get("SteeringLocation", ""),
                "body_class": r.get("BodyClass", ""),
                "fuel_type": r.get("FuelTypePrimary", ""),
                "plant": r.get("PlantCity", ""),
                "raw": r,
            }
    except Exception as e:
        frappe.log_error(title="NHTSA VIN Decode Failed", message=frappe.get_traceback())
    return {}


def _decode_jdm_frame(frame_no: str) -> dict:
    """
    Japanese frame numbers are often {prefix}-{serial}.
    We match the prefix against our manual mapping table.
    """
    # Normalize: remove hyphen, uppercase
    clean = frame_no.replace("-", "").upper()

    # Try longest prefix match
    for prefix in sorted(JDM_FRAME_PREFIXES.keys(), key=len, reverse=True):
        if clean.startswith(prefix):
            info = JDM_FRAME_PREFIXES[prefix].copy()
            info["vin"] = frame_no
            info["frame_prefix"] = prefix
            info["source"] = "JDM_MANUAL"
            return info

    return {}


def _persist_cache(vin: str, result: dict, source: str):
    """Upsert VIN Decode Cache document."""
    if not result:
        return

    existing = frappe.db.get_value("VIN Decode Cache", {"vin": vin}, "name")
    payload = json.dumps(result, default=str)

    if existing:
        doc = frappe.get_doc("VIN Decode Cache", existing)
        doc.decoded_json = payload
        doc.make = result.get("make", "")
        doc.model = result.get("model", "")
        doc.year = cint(result.get("year", 0))
        doc.engine_code = result.get("engine_code", "")
        doc.steering_location = result.get("steering_location", "")
        doc.source_api = source
        doc.last_decoded = now()
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "VIN Decode Cache",
            "vin": vin,
            "decoded_json": payload,
            "make": result.get("make", ""),
            "model": result.get("model", ""),
            "year": cint(result.get("year", 0)),
            "engine_code": result.get("engine_code", ""),
            "steering_location": result.get("steering_location", ""),
            "source_api": source,
            "last_decoded": now(),
            "hit_count": 1,
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()


@frappe.whitelist()
def decode_vin_api(vin: str, force_refresh: bool = False):
    """Whitelist wrapper for client-side calls."""
    return decode_vin(vin, force_refresh=force_refresh)


def process_pending_vin_decodes():
    """Scheduled job: find Vehicles without decoded data and process them."""
    pending = frappe.get_all(
        "Vehicle",
        filters={"last_vin_decode": ("is", "not set")},
        fields=["name", "vin"],
        limit_page_length=100,
    )
    for v in pending:
        if v.vin:
            try:
                decode_vin(v.vin)
                frappe.db.set_value("Vehicle", v.name, "last_vin_decode", now())
            except Exception:
                frappe.log_error(title="Pending VIN Decode Error", message=frappe.get_traceback())
    frappe.db.commit()
