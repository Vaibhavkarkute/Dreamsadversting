from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List
from app.core.config import settings


def _q(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_quotation_pricing(
    items: List[Dict],
    additional_services_inr: float = 0.0,
    commission_rate: float = settings.PLATFORM_COMMISSION_RATE,
    gst_rate: float = settings.GST_TAX_RATE,
) -> Dict:
    """
    Server-side authoritative quotation & pricing engine.
    Considers media format, dimensions, campaign duration, vendor display rate,
    installation charges, printing/production charges, additional services,
    platform commission, and 18% GST. Never trusts frontend totals.
    """
    if not items:
        raise ValueError("Quotation must include at least one media asset.")

    subtotal_display = Decimal("0.00")
    installation_total = Decimal("0.00")
    printing_total = Decimal("0.00")
    production_total = Decimal("0.00")
    line_items = []

    for item in items:
        duration_months = max(1, int(item.get("duration_months", 1)))
        monthly_rate = Decimal(str(item["display_cost_pm"]))
        is_digital = bool(item.get("is_digital", False)) or item.get("format_code") == "LED"
        area_sqft = Decimal(str(item.get("area_sqft", 400)))

        inst_charge = (
            Decimal("0.00")
            if is_digital
            else Decimal(str(item.get("installation_cost", float(area_sqft * Decimal("4.0")))))
        )
        print_charge = (
            Decimal("0.00")
            if is_digital
            else Decimal(str(item.get("printing_cost", float(area_sqft * Decimal("12.0")))))
        )
        prod_charge = Decimal(str(item.get("production_cost", 0.0)))

        display_line = _q(monthly_rate * Decimal(duration_months))
        line_total = _q(display_line + inst_charge + print_charge + prod_charge)

        subtotal_display += display_line
        installation_total += inst_charge
        printing_total += print_charge
        production_total += prod_charge

        line_items.append(
            {
                "asset_id": item["id"],
                "title": item.get("title", item["id"]),
                "format_code": item.get("format_code", "FL"),
                "area_sqft": float(area_sqft),
                "duration_months": duration_months,
                "monthly_rate": float(_q(monthly_rate)),
                "display_subtotal": float(display_line),
                "installation_charge": float(_q(inst_charge)),
                "printing_charge": float(_q(print_charge)),
                "production_charge": float(_q(prod_charge)),
                "line_total": float(line_total),
            }
        )

    add_services = _q(Decimal(str(max(0.0, additional_services_inr))))
    base_cost = _q(subtotal_display + installation_total + printing_total + production_total + add_services)
    platform_commission = _q(subtotal_display * Decimal(str(commission_rate)))
    taxable_amount = _q(base_cost + platform_commission)
    gst_amount = _q(taxable_amount * Decimal(str(gst_rate)))
    cgst_amount = _q(gst_amount / Decimal("2"))
    sgst_amount = _q(gst_amount - cgst_amount)
    grand_total = _q(taxable_amount + gst_amount)

    return {
        "currency": "INR",
        "line_items": line_items,
        "subtotal_display": float(_q(subtotal_display)),
        "installation_total": float(_q(installation_total)),
        "printing_total": float(_q(printing_total)),
        "production_total": float(_q(production_total)),
        "additional_services_total": float(add_services),
        "platform_commission_rate": commission_rate,
        "platform_commission": float(platform_commission),
        "taxable_amount": float(taxable_amount),
        "gst_rate": gst_rate,
        "cgst_amount": float(cgst_amount),
        "sgst_amount": float(sgst_amount),
        "gst_amount": float(gst_amount),
        "grand_total": float(grand_total),
    }
