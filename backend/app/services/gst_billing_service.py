import datetime
import threading
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

REQUIRED_GST_DOCUMENT_TYPES = [
    "Quotation",
    "Booking Confirmation",
    "Payment Receipt",
    "Advance Receipt Voucher",
    "GST Tax Invoice",
    "Credit Note",
    "Debit Note",
    "Refund Confirmation",
]

DOC_PREFIX_MAP = {
    "Quotation": "QTN",
    "Booking Confirmation": "BKC",
    "Payment Receipt": "RCP",
    "Advance Receipt Voucher": "ADV",
    "GST Tax Invoice": "INV",
    "Credit Note": "CRN",
    "Debit Note": "DBN",
    "Refund Confirmation": "RFC",
}


def _q(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class IndianGSTBillingService:
    """
    Maharashtra-compliant Indian GST Billing & Atomic Document Generation Service.
    - Owner-controlled Company GST Configuration & HSN/SAC tax rate mapping.
    - Supports CGST + SGST (Intra-state Maharashtra 27) vs IGST (Inter-state),
      Cess, Discounts, Tax-Inclusive & Tax-Exclusive calculations.
    - Generates sequential, atomic financial-year document numbers for all 8 required documents.
    - Issued GST Tax Invoices are strictly immutable (employees cannot edit or delete).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.company_config: Dict = {
            "legal_name": "DreamsAdverstings Media Pvt. Ltd. (Configurable)",
            "gstin": "27AABCD1234E1Z5",
            "pan": "AABCD1234E",
            "registered_address": "Pune, Maharashtra, India",
            "state_code": "27",  # Maharashtra
            "billing_email": "billing@dreamsadverstings.in",
            "contact_phone": "+91-20-XXXX-XXXX",
            "financial_year": "2026-27",
            "invoice_prefix": "DA",
        }
        self.hsn_sac_catalog: Dict[str, Dict] = {
            "static_hoarding": {"sac_code": "998365", "description": "Sale of advertising space on outdoor hoardings", "gst_rate": 0.18, "cess_rate": 0.0},
            "dooh_led": {"sac_code": "998366", "description": "Digital Out-of-Home (DOOH) LED screen advertising", "gst_rate": 0.18, "cess_rate": 0.0},
            "printing_mounting": {"sac_code": "998399", "description": "Flex printing and site mounting services", "gst_rate": 0.12, "cess_rate": 0.0},
            "creative_design": {"sac_code": "998361", "description": "Advertising creative & campaign design", "gst_rate": 0.18, "cess_rate": 0.0},
        }
        self.fy_sequences: Dict[str, int] = {}
        self.documents: Dict[str, Dict] = {}

    def update_company_config(self, actor: Dict, updates: Dict) -> Dict:
        if actor.get("role") != "owner":
            raise PermissionError("OWNER_ONLY: Finance or regular staff cannot modify company GST configuration.")
        self.company_config.update(updates)
        return self.company_config

    def calculate_gst_line_items(
        self,
        items: List[Dict],
        place_of_supply_state_code: str = "27",
        discount_inr: float = 0.0,
        tax_inclusive: bool = False,
    ) -> Dict:
        if not items:
            raise ValueError("Billable items cannot be empty.")

        is_intra_state = str(place_of_supply_state_code).strip() == str(self.company_config["state_code"])
        total_gross = Decimal("0.00")
        total_taxable = Decimal("0.00")
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_igst = Decimal("0.00")
        total_cess = Decimal("0.00")
        computed_lines = []

        discount_dec = _q(Decimal(str(max(0.0, discount_inr))))

        for idx, item in enumerate(items):
            service_key = item.get("service_key", "static_hoarding")
            sac_info = self.hsn_sac_catalog.get(service_key, self.hsn_sac_catalog["static_hoarding"])
            gst_rate = Decimal(str(item.get("gst_rate", sac_info["gst_rate"])))
            cess_rate = Decimal(str(item.get("cess_rate", sac_info["cess_rate"])))
            raw_amount = _q(Decimal(str(item["amount_inr"])))

            # Apply discount proportionally or on first line
            line_disc = discount_dec if idx == 0 else Decimal("0.00")
            net_amount = max(Decimal("0.00"), raw_amount - line_disc)

            if tax_inclusive:
                divisor = Decimal("1.00") + gst_rate + cess_rate
                taxable_val = _q(net_amount / divisor)
            else:
                taxable_val = net_amount

            gst_amt = _q(taxable_val * gst_rate)
            cess_amt = _q(taxable_val * cess_rate)

            if is_intra_state:
                cgst = _q(gst_amt / Decimal("2"))
                sgst = gst_amt - cgst
                igst = Decimal("0.00")
            else:
                cgst = Decimal("0.00")
                sgst = Decimal("0.00")
                igst = gst_amt

            line_grand = _q(taxable_val + cgst + sgst + igst + cess_amt)

            total_gross += raw_amount
            total_taxable += taxable_val
            total_cgst += cgst
            total_sgst += sgst
            total_igst += igst
            total_cess += cess_amt

            computed_lines.append(
                {
                    "description": item.get("description", sac_info["description"]),
                    "sac_code": sac_info["sac_code"],
                    "gst_rate_pct": float(gst_rate * 100),
                    "taxable_value": float(taxable_val),
                    "cgst": float(cgst),
                    "sgst": float(sgst),
                    "igst": float(igst),
                    "cess": float(cess_amt),
                    "line_total": float(line_grand),
                }
            )

        grand_total = _q(total_taxable + total_cgst + total_sgst + total_igst + total_cess)

        return {
            "company_gstin": self.company_config["gstin"],
            "company_state_code": self.company_config["state_code"],
            "place_of_supply_state_code": place_of_supply_state_code,
            "supply_type": "Intra-State (CGST+SGST)" if is_intra_state else "Inter-State (IGST)",
            "tax_inclusive_input": tax_inclusive,
            "discount_inr": float(discount_dec),
            "taxable_value": float(_q(total_taxable)),
            "cgst_amount": float(_q(total_cgst)),
            "sgst_amount": float(_q(total_sgst)),
            "igst_amount": float(_q(total_igst)),
            "cess_amount": float(_q(total_cess)),
            "total_tax": float(_q(total_cgst + total_sgst + total_igst + total_cess)),
            "grand_total": float(grand_total),
            "lines": computed_lines,
        }

    def _next_atomic_number(self, doc_type: str) -> str:
        if doc_type not in REQUIRED_GST_DOCUMENT_TYPES:
            raise ValueError(f"Unsupported GST document type: {doc_type}")
        fy = self.company_config["financial_year"]
        prefix = self.company_config["invoice_prefix"]
        code = DOC_PREFIX_MAP[doc_type]
        seq_key = f"{fy}:{code}"
        with self._lock:
            current = self.fy_sequences.get(seq_key, 0) + 1
            self.fy_sequences[seq_key] = current
            return f"{prefix}/{fy}/{code}/{current:04d}"

    def issue_document(
        self,
        doc_type: str,
        customer: Dict,
        booking_id: str,
        tax_summary: Dict,
        payment_ref: Optional[str] = None,
        linked_invoice_no: Optional[str] = None,
    ) -> Dict:
        doc_number = self._next_atomic_number(doc_type)
        doc = {
            "document_number": doc_number,
            "document_type": doc_type,
            "financial_year": self.company_config["financial_year"],
            "booking_id": booking_id,
            "customer_id": customer.get("id"),
            "customer_name": customer.get("full_name") or customer.get("name"),
            "customer_gstin": customer.get("gstin"),
            "company_snapshot": dict(self.company_config),
            "tax_summary": tax_summary,
            "payment_ref": payment_ref,
            "linked_invoice_no": linked_invoice_no,
            "is_immutable": doc_type == "GST Tax Invoice",
            "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "s3_pdf_key": f"gst-documents/{self.company_config['financial_year']}/{doc_number.replace('/', '_')}.pdf",
        }
        self.documents[doc_number] = doc
        return doc

    def modify_or_delete_invoice(self, doc_number: str, actor: Dict):
        doc = self.documents.get(doc_number)
        if not doc:
            raise KeyError(f"Document {doc_number} not found.")
        if doc["is_immutable"]:
            raise PermissionError(
                "IMMUTABLE_GST_DOCUMENT: Issued GST Tax Invoices cannot be edited or deleted. "
                "Issue a Credit Note or Debit Note for statutory corrections."
            )
