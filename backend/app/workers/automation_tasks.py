import datetime
from typing import Dict, List, Optional
from app.main import MarketplacePlatformKernel


class ProductionAutomationWorker:
    """
    Production background automation engine (executed via Redis/Celery or ECS Scheduled Task).
    Automates:
    1. Expired Booking Hold Reaper (releases stale 15-min holds on static & LED slots)
    2. Campaign Lifecycle Transitions (Confirmed -> In Execution on start_date)
    3. T-7 & T-1 Day Expiry Reminder Automation (Meta WhatsApp + AWS SES)
    4. Failed Message Retry Queue Processor (idempotent, non-destructive)
    5. Daily Owner Executive Revenue & GST Digest
    """

    def __init__(self, kernel: MarketplacePlatformKernel):
        self.kernel = kernel
        self.run_history: List[Dict] = []

    def run_expired_hold_reaper(self, now: Optional[datetime.datetime] = None) -> Dict:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        released_count = self.kernel.booking_engine.release_expired_holds(now=now)
        res = {"task": "expired_hold_reaper", "released_holds": released_count, "timestamp": now.isoformat()}
        self.run_history.append(res)
        return res

    def run_campaign_lifecycle_and_reminders(self, today: Optional[datetime.date] = None) -> Dict:
        today = today or datetime.date.today()
        activated = 0
        reminders_sent = 0

        for b_id, booking in self.kernel.booking_engine.bookings.items():
            if booking["status"] == "Confirmed" and booking["start_date"] <= today:
                self.kernel.booking_engine.transition_status(b_id, "In Execution", "system_automation_worker")
                activated += 1

            if booking["status"] == "In Execution":
                days_left = (booking["end_date"] - today).days
                if days_left in (7, 1):
                    idem = f"reminder-{b_id}-{days_left}d-{today.isoformat()}"
                    self.kernel.messaging_service.send_document_notification(
                        customer_id=booking["customer_id"],
                        channel="whatsapp",
                        template_name="campaign_reminder",
                        idempotency_key=idem,
                    )
                    reminders_sent += 1

        res = {
            "task": "campaign_lifecycle_and_reminders",
            "campaigns_activated": activated,
            "reminders_dispatched": reminders_sent,
            "date": today.isoformat(),
        }
        self.run_history.append(res)
        return res

    def run_failed_message_retry_processor(self) -> Dict:
        retried = 0
        for log in self.kernel.messaging_service.delivery_logs:
            if "Failed" in log["status"] and log["retry_count"] < 3:
                self.kernel.messaging_service.retry_failed_message(log["id"])
                retried += 1
        res = {"task": "failed_message_retry_processor", "retried_count": retried}
        self.run_history.append(res)
        return res

    def generate_daily_owner_digest(self) -> Dict:
        total_bookings = len(self.kernel.booking_engine.bookings)
        confirmed_val = sum(
            b["total_payable"]
            for b in self.kernel.booking_engine.bookings.values()
            if b["status"] in ("Confirmed", "In Execution", "Completed")
        )
        total_received = sum(
            ledger["amount_paid_inr"] for ledger in self.kernel.payment_service.booking_ledgers.values()
        )
        outstanding = sum(
            ledger["outstanding_balance_inr"] for ledger in self.kernel.payment_service.booking_ledgers.values()
        )
        digest = {
            "task": "daily_owner_executive_digest",
            "total_assets": len(self.kernel.inventory),
            "total_bookings": total_bookings,
            "confirmed_booking_value_inr": round(confirmed_val, 2),
            "amount_received_inr": round(total_received, 2),
            "outstanding_balance_inr": round(outstanding, 2),
            "gst_documents_issued": len(self.kernel.gst_service.documents),
        }
        self.run_history.append(digest)
        return digest

    def run_full_automation_cycle(
        self,
        now: Optional[datetime.datetime] = None,
        today: Optional[datetime.date] = None,
    ) -> Dict:
        r1 = self.run_expired_hold_reaper(now=now)
        r2 = self.run_campaign_lifecycle_and_reminders(today=today)
        r3 = self.run_failed_message_retry_processor()
        r4 = self.generate_daily_owner_digest()
        return {"cycle_status": "completed", "steps": [r1, r2, r3, r4]}
