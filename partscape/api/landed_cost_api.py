"""
PartScape — Landed Cost Calculator

Dominica typical customs formula (configurable):
    Landed XCD = (USD Cost * Exchange Rate) * (1 + Import Duty %) * (1 + VAT %)
"""

import frappe
from frappe import _

DEFAULT_EXCHANGE_RATE = 2.7  # USD to XCD fixed
DEFAULT_IMPORT_DUTY_PCT = 0.25
DEFAULT_VAT_PCT = 0.15


def get_rates():
    """Fetch configurable rates from PartScape Settings (or defaults)."""
    # Future: read from a "PartScape Settings" single doctype
    return {
        "exchange_rate": DEFAULT_EXCHANGE_RATE,
        "import_duty_pct": DEFAULT_IMPORT_DUTY_PCT,
        "vat_pct": DEFAULT_VAT_PCT,
    }


@frappe.whitelist()
def estimate_landed_cost(usd_amount: float, duty_pct: float = None, vat_pct: float = None) -> dict:
    """
    Estimate landed cost in XCD given a USD amount.
    """
    usd = float(usd_amount or 0)
    rates = get_rates()
    exchange = rates["exchange_rate"]
    duty = duty_pct if duty_pct is not None else rates["import_duty_pct"]
    vat = vat_pct if vat_pct is not None else rates["vat_pct"]

    base_xcd = usd * exchange
    after_duty = base_xcd * (1 + duty)
    landed_xcd = after_duty * (1 + vat)

    return {
        "usd_amount": usd,
        "exchange_rate": exchange,
        "base_xcd": round(base_xcd, 2),
        "import_duty_pct": duty,
        "vat_pct": vat,
        "landed_xcd": round(landed_xcd, 2),
    }
