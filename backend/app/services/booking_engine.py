import datetime
import threading
from typing import Dict, List, Optional

VALID_BOOKING_STATUSES = [
    "Draft",
    "Enquiry Submitted",
    "Quotation Pending",
    "Quotation Sent",
    "Awaiting Approval",
    "Payment Pending",
    "Confirmed",
    "In Execution",
    "Completed",
    "Cancelled",
    "Refund Pending",
    "Refunded",
]

ALLOWED_TRANSITIONS = {
    "Draft": ["Enquiry Submitted", "Cancelled"],
    "Enquiry Submitted": ["Quotation Pending", "Cancelled"],
    "Quotation Pending": ["Quotation Sent", "Cancelled"],
    "Quotation Sent": ["Awaiting Approval", "Payment Pending", "Cancelled"],
    "Awaiting Approval": ["Payment Pending", "Cancelled"],
    "Payment Pending": ["Confirmed", "Cancelled"],
    "Confirmed": ["In Execution", "Cancelled", "Refund Pending"],
    "In Execution": ["Completed", "Refund Pending"],
    "Completed": [],
    "Cancelled": ["Refund Pending"],
    "Refund Pending": ["Refunded"],
    "Refunded": [],
}


class LEDSlotCapacityEngine:
    """
    Capacity-safe reservation engine for Digital LED (DOOH) screens.
    Manages operating hours, slot duration, loop duration, plays per day,
    booked slots, and available capacity — never marking an entire LED screen
    unavailable when only a portion of its advertising slots are booked.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.screen_configs: Dict[str, Dict] = {}
        self.slot_bookings: List[Dict] = []

    def configure_screen(
        self,
        asset_id: str,
        operating_hours_per_day: float = 17.0,
        slot_duration_sec: int = 10,
        loop_duration_sec: int = 120,
    ) -> Dict:
        if slot_duration_sec <= 0 or loop_duration_sec < slot_duration_sec:
            raise ValueError("Invalid slot/loop duration configuration.")
        max_slots_per_loop = loop_duration_sec // slot_duration_sec
        loops_per_day = int((operating_hours_per_day * 3600) // loop_duration_sec)
        cfg = {
            "asset_id": asset_id,
            "operating_hours_per_day": operating_hours_per_day,
            "slot_duration_sec": slot_duration_sec,
            "loop_duration_sec": loop_duration_sec,
            "max_slots": max_slots_per_loop,
            "plays_per_slot_per_day": loops_per_day,
        }
        self.screen_configs[asset_id] = cfg
        return cfg

    def get_capacity_for_dates(
        self,
        asset_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        now: Optional[datetime.datetime] = None,
    ) -> Dict:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        cfg = self.screen_configs.get(asset_id) or self.configure_screen(asset_id)
        booked = 0
        for sb in self.slot_bookings:
            if sb["asset_id"] != asset_id:
                continue
            if sb["status"] == "Cancelled":
                continue
            if sb["status"] == "Payment Pending" and sb.get("hold_expires_at") and sb["hold_expires_at"] <= now:
                continue
            if sb["start_date"] <= end_date and start_date <= sb["end_date"]:
                booked += sb["slots_booked"]
        available = max(0, cfg["max_slots"] - booked)
        return {
            **cfg,
            "booked_slots": booked,
            "available_slots": available,
            "is_bookable": available > 0,
        }

    def reserve_slots(
        self,
        booking_id: str,
        asset_id: str,
        customer_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        slots_requested: int = 1,
        hold_minutes: int = 15,
        now: Optional[datetime.datetime] = None,
    ) -> Dict:
        if slots_requested <= 0:
            raise ValueError("Must request at least 1 LED slot.")
        now = now or datetime.datetime.now(datetime.timezone.utc)
        with self._lock:
            cap = self.get_capacity_for_dates(asset_id, start_date, end_date, now=now)
            if slots_requested > cap["available_slots"]:
                raise ValueError(
                    f"LED_CAPACITY_EXCEEDED: Requested {slots_requested} slots on {asset_id}, "
                    f"but only {cap['available_slots']} of {cap['max_slots']} slots remain available."
                )
            record = {
                "booking_id": booking_id,
                "asset_id": asset_id,
                "customer_id": customer_id,
                "start_date": start_date,
                "end_date": end_date,
                "slots_booked": slots_requested,
                "plays_per_day_total": slots_requested * cap["plays_per_slot_per_day"],
                "status": "Payment Pending",
                "hold_expires_at": now + datetime.timedelta(minutes=hold_minutes),
            }
            self.slot_bookings.append(record)
            return record

    def confirm_slot_booking(self, booking_id: str):
        with self._lock:
            for sb in self.slot_bookings:
                if sb["booking_id"] == booking_id:
                    sb["status"] = "Confirmed"
                    sb["hold_expires_at"] = None
                    return sb
        raise KeyError(f"LED slot booking {booking_id} not found.")


class TransactionalBookingEngine:
    """
    Thread-safe transactional booking & availability coordinator for static hoardings & DOOH LED screens.
    Enforces maintenance blocks, overlapping static reservation prevention, and expired hold cleanup.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.bookings: Dict[str, Dict] = {}
        self.maintenance_blocks: List[Dict] = []
        self.history: List[Dict] = []
        self.led_engine = LEDSlotCapacityEngine()

    @staticmethod
    def _dates_overlap(start_a: datetime.date, end_a: datetime.date, start_b: datetime.date, end_b: datetime.date) -> bool:
        return start_a <= end_b and start_b <= end_a

    def add_maintenance_block(
        self, asset_id: str, start_date: datetime.date, end_date: datetime.date, reason: str
    ) -> Dict:
        block = {
            "block_id": f"MNT-{len(self.maintenance_blocks) + 1:03d}",
            "asset_id": asset_id,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
        }
        self.maintenance_blocks.append(block)
        return block

    def release_expired_holds(self, now: Optional[datetime.datetime] = None) -> int:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        released = 0
        with self._lock:
            for b_id, b in self.bookings.items():
                if b["status"] == "Payment Pending" and b.get("hold_expires_at") and b["hold_expires_at"] <= now:
                    b["status"] = "Cancelled"
                    released += 1
                    self.history.append(
                        {
                            "booking_id": b_id,
                            "from_status": "Payment Pending",
                            "to_status": "Cancelled",
                            "changed_by": "system_hold_reaper",
                            "timestamp": now.isoformat(),
                        }
                    )
        return released

    def check_asset_availability(
        self,
        asset: Dict,
        start_date: datetime.date,
        end_date: datetime.date,
        now: Optional[datetime.datetime] = None,
        exclude_booking_id: Optional[str] = None,
        slots_requested: int = 1,
    ) -> Dict:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        if end_date < start_date:
            return {"available": False, "reason": "End date cannot be earlier than start date."}

        if not asset.get("vendor_verified", False) or asset.get("status") != "Approved":
            return {"available": False, "reason": "Asset or vendor is not verified/approved for booking."}

        for blk in self.maintenance_blocks:
            if blk["asset_id"] == asset["id"] and self._dates_overlap(start_date, end_date, blk["start_date"], blk["end_date"]):
                return {"available": False, "reason": f"Asset under maintenance ({blk['reason']}) from {blk['start_date']} to {blk['end_date']}."}

        if asset.get("is_digital", False) or asset.get("format_code") == "LED":
            cap = self.led_engine.get_capacity_for_dates(asset["id"], start_date, end_date, now=now)
            if slots_requested > cap["available_slots"]:
                return {"available": False, "reason": f"LED_CAPACITY_EXCEEDED: Only {cap['available_slots']} LED slots available."}
            return {"available": True, "reason": "LED slots available", "led_capacity": cap}

        for b_id, b in self.bookings.items():
            if b_id == exclude_booking_id or b["asset_id"] != asset["id"]:
                continue
            status = b["status"]
            if status in ("Confirmed", "In Execution"):
                if self._dates_overlap(start_date, end_date, b["start_date"], b["end_date"]):
                    return {"available": False, "reason": f"Overlaps with confirmed booking {b_id}."}
            elif status == "Payment Pending" and b.get("hold_expires_at"):
                if b["hold_expires_at"] > now and self._dates_overlap(start_date, end_date, b["start_date"], b["end_date"]):
                    return {"available": False, "reason": f"Asset is on temporary booking hold ({b_id})."}

        return {"available": True, "reason": "Available"}

    def place_booking_hold(
        self,
        booking_id: str,
        asset: Dict,
        customer_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        total_payable: float,
        hold_minutes: int = 15,
        slots_requested: int = 1,
        now: Optional[datetime.datetime] = None,
    ) -> Dict:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        with self._lock:
            avail = self.check_asset_availability(
                asset, start_date, end_date, now=now, slots_requested=slots_requested
            )
            if not avail["available"]:
                raise ValueError(avail["reason"])

            if asset.get("is_digital", False) or asset.get("format_code") == "LED":
                self.led_engine.reserve_slots(
                    booking_id, asset["id"], customer_id, start_date, end_date, slots_requested, hold_minutes, now
                )

            expires_at = now + datetime.timedelta(minutes=hold_minutes)
            record = {
                "booking_id": booking_id,
                "asset_id": asset["id"],
                "vendor_id": asset.get("vendor_id", "VEND-001"),
                "customer_id": customer_id,
                "start_date": start_date,
                "end_date": end_date,
                "slots_booked": slots_requested if (asset.get("is_digital") or asset.get("format_code") == "LED") else 1,
                "status": "Payment Pending",
                "hold_expires_at": expires_at,
                "total_payable": round(float(total_payable), 2),
                "created_at": now,
            }
            self.bookings[booking_id] = record
            self.history.append(
                {
                    "booking_id": booking_id,
                    "from_status": "Quotation Sent",
                    "to_status": "Payment Pending",
                    "changed_by": customer_id,
                    "timestamp": now.isoformat(),
                }
            )
            return record

    def transition_status(
        self,
        booking_id: str,
        new_status: str,
        actor_id: str,
        asset: Optional[Dict] = None,
        now: Optional[datetime.datetime] = None,
    ) -> Dict:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        if new_status not in VALID_BOOKING_STATUSES:
            raise ValueError(f"Unsupported booking status: {new_status}")

        with self._lock:
            if booking_id not in self.bookings:
                raise KeyError(f"Booking {booking_id} not found")
            booking = self.bookings[booking_id]
            current = booking["status"]
            if new_status not in ALLOWED_TRANSITIONS.get(current, []):
                raise ValueError(f"Invalid status transition from '{current}' to '{new_status}'")

            if new_status == "Confirmed":
                if booking.get("hold_expires_at") and booking["hold_expires_at"] < now:
                    raise ValueError("Temporary booking hold has expired.")
                if asset is not None and not (asset.get("is_digital") or asset.get("format_code") == "LED"):
                    avail = self.check_asset_availability(
                        asset, booking["start_date"], booking["end_date"], now=now, exclude_booking_id=booking_id
                    )
                    if not avail["available"]:
                        raise ValueError(avail["reason"])
                if asset is not None and (asset.get("is_digital") or asset.get("format_code") == "LED"):
                    self.led_engine.confirm_slot_booking(booking_id)

            booking["status"] = new_status
            self.history.append(
                {
                    "booking_id": booking_id,
                    "from_status": current,
                    "to_status": new_status,
                    "changed_by": actor_id,
                    "timestamp": now.isoformat(),
                }
            )
            return booking
