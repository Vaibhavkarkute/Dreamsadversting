import hashlib
import hmac
import secrets
from typing import Dict, List, Set
from app.core.config import settings


class RazorpayPaymentService:
    """
    Server-side Razorpay order creation, HMAC-SHA256 verification, partial payment
    installment tracking, failed payment receipt blocking, webhook verification,
    duplicate payment prevention, refunds, and reconciliation.
    """

    def __init__(self):
        self.orders: Dict[str, Dict] = {}
        self.booking_ledgers: Dict[str, Dict] = {}
        self.processed_payments: Set[str] = set()
        self.processed_webhooks: Set[str] = set()
        self.refunds: Dict[str, Dict] = {}

    def init_booking_ledger(self, booking_id: str, total_payable_inr: float) -> Dict:
        if booking_id not in self.booking_ledgers:
            self.booking_ledgers[booking_id] = {
                "booking_id": booking_id,
                "total_payable_inr": round(total_payable_inr, 2),
                "amount_paid_inr": 0.0,
                "outstanding_balance_inr": round(total_payable_inr, 2),
                "payment_records": [],
                "reconciliation_status": "Pending",
            }
        return self.booking_ledgers[booking_id]

    def create_order(
        self,
        booking_id: str,
        amount_inr: float,
        customer_id: str,
        total_booking_payable: float = 0.0,
        partial: bool = False,
    ) -> Dict:
        if amount_inr <= 0:
            raise ValueError("Order amount must be greater than zero.")
        if total_booking_payable > 0:
            self.init_booking_ledger(booking_id, total_booking_payable)

        order_id = f"order_test_{secrets.token_hex(6)}"
        order = {
            "order_id": order_id,
            "booking_id": booking_id,
            "customer_id": customer_id,
            "amount_paise": int(round(amount_inr * 100)),
            "amount_inr": round(amount_inr, 2),
            "is_partial": partial,
            "currency": "INR",
            "mode": settings.RAZORPAY_MODE,
            "status": "created",
        }
        self.orders[order_id] = order
        return order

    @staticmethod
    def generate_payment_signature(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    def verify_payment(self, order_id: str, payment_id: str, signature: str) -> Dict:
        if payment_id in self.processed_payments:
            raise ValueError(f"Duplicate payment reference rejected: {payment_id}")
        if order_id not in self.orders:
            raise KeyError(f"Order {order_id} not found")

        order = self.orders[order_id]
        expected = self.generate_payment_signature(order_id, payment_id)
        if not hmac.compare_digest(expected, signature):
            order["status"] = "failed"
            # Record failed attempt; NEVER generate a paid receipt
            if order["booking_id"] in self.booking_ledgers:
                self.booking_ledgers[order["booking_id"]]["payment_records"].append(
                    {"payment_id": payment_id, "order_id": order_id, "amount_inr": order["amount_inr"], "status": "Failed"}
                )
            raise PermissionError("Razorpay signature verification failed. Paid receipt generation blocked.")

        self.processed_payments.add(payment_id)
        order["status"] = "paid"
        order["payment_id"] = payment_id

        b_id = order["booking_id"]
        ledger = self.init_booking_ledger(b_id, order["amount_inr"])
        ledger["amount_paid_inr"] = round(ledger["amount_paid_inr"] + order["amount_inr"], 2)
        ledger["outstanding_balance_inr"] = max(0.0, round(ledger["total_payable_inr"] - ledger["amount_paid_inr"], 2))
        ledger["reconciliation_status"] = (
            "Fully Reconciled" if ledger["outstanding_balance_inr"] == 0 else "Partially Paid"
        )
        ledger["payment_records"].append(
            {"payment_id": payment_id, "order_id": order_id, "amount_inr": order["amount_inr"], "status": "Verified"}
        )

        return {
            "verified": True,
            "order_id": order_id,
            "payment_id": payment_id,
            "booking_id": b_id,
            "amount_inr": order["amount_inr"],
            "outstanding_balance_inr": ledger["outstanding_balance_inr"],
            "reconciliation_status": ledger["reconciliation_status"],
        }

    def record_failed_payment(self, order_id: str, payment_id: str, reason: str) -> Dict:
        if order_id not in self.orders:
            raise KeyError(f"Order {order_id} not found")
        order = self.orders[order_id]
        order["status"] = "failed"
        b_id = order["booking_id"]
        if b_id in self.booking_ledgers:
            self.booking_ledgers[b_id]["payment_records"].append(
                {"payment_id": payment_id, "order_id": order_id, "amount_inr": order["amount_inr"], "status": "Failed", "reason": reason}
            )
        return {"order_id": order_id, "status": "failed", "receipt_allowed": False, "reason": reason}

    def verify_webhook(self, raw_body: bytes, header_signature: str, event_id: str) -> bool:
        if event_id in self.processed_webhooks:
            raise ValueError(f"Duplicate webhook event ignored: {event_id}")
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, header_signature):
            raise PermissionError("Invalid Razorpay webhook signature.")
        self.processed_webhooks.add(event_id)
        return True

    def initiate_refund(self, payment_id: str, amount_inr: float, reason: str) -> Dict:
        if payment_id not in self.processed_payments:
            raise ValueError("Cannot refund an unverified or failed payment.")
        refund_id = f"rfnd_test_{secrets.token_hex(5)}"
        record = {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "amount_inr": round(amount_inr, 2),
            "reason": reason,
            "status": "Refund Pending",
        }
        self.refunds[refund_id] = record
        return record
