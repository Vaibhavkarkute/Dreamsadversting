import json
import os
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.security import check_permission, create_jwt_token, hash_password, verify_password
from app.services.ai_planner import AIMediaPlannerService
from app.services.booking_engine import TransactionalBookingEngine
from app.services.gst_billing_service import IndianGSTBillingService
from app.services.messaging_service import MessagingAutomationService
from app.services.payment_service import RazorpayPaymentService
from app.services.pricing_engine import calculate_quotation_pricing
from app.services.staff_service import StaffManagementService
from app.services.qr_and_review_service import QRBannerBookingService, CompletedOrderReviewService
from app.services.analytics_and_expiry_service import ProductionAnalyticsAndExpiryService


class MarketplacePlatformKernel:
    """
    Unified Production Marketplace Kernel integrating:
    - Single Master Owner + 11-Role Staff Management
    - Static Hoarding & LED Slot Capacity Reservation Engine
    - Maharashtra Indian GST Billing & 8 Sequential Atomic Documents
    - Razorpay Full/Partial Payments & Reconciliation
    - Meta WhatsApp Business Cloud API & AWS SES Automation
    - Grounded AI Media Planner
    """

    def __init__(self):
        seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
        with open(seed_path, "r", encoding="utf-8") as f:
            self.inventory: List[Dict] = json.load(f)

        self.users: Dict[str, Dict] = {}
        self.enquiries: Dict[str, Dict] = {}
        self.quotations: Dict[str, Dict] = {}
        self.audit_logs: List[Dict] = []

        self.staff_service = StaffManagementService()
        self.booking_engine = TransactionalBookingEngine()
        self.gst_service = IndianGSTBillingService()
        self.payment_service = RazorpayPaymentService()
        self.messaging_service = MessagingAutomationService()
        self.ai_planner = AIMediaPlannerService(self.inventory)
        self.qr_service = QRBannerBookingService()
        self.review_service = CompletedOrderReviewService()
        self.analytics_service = ProductionAnalyticsAndExpiryService(self.inventory)

        # Configure default LED screens from seed inventory
        for item in self.inventory:
            if item.get("is_digital") or item.get("format_code") == "LED":
                self.booking_engine.led_engine.configure_screen(item["id"], 17.0, 10, 120)

    def register_user(self, email: str, password: str, full_name: str, role: str = "customer") -> Dict:
        if role == "owner":
            raise ValueError("SINGLE_OWNER_VIOLATION: Use staff_service.bootstrap_master_owner for the single Owner.")
        email_clean = email.strip().lower()
        if email_clean in self.users:
            raise ValueError("Email already registered.")
        uid = f"USR-{len(self.users) + 1:03d}"
        user = {
            "id": uid,
            "email": email_clean,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "vendor_verified": True if role == "admin" else False,
        }
        self.users[email_clean] = user
        self._log_audit(uid, role, "user.register", "users", uid)
        return {k: v for k, v in user.items() if k != "password_hash"}

    def login_user(self, email: str, password: str) -> Dict:
        email_clean = email.strip().lower()
        user = self.users.get(email_clean)
        if not user or not verify_password(password, user["password_hash"]):
            raise PermissionError("Invalid email or password.")
        access = create_jwt_token(user["id"], user["role"], "access")
        refresh = create_jwt_token(user["id"], user["role"], "refresh")
        return {"access_token": access, "refresh_token": refresh, "user_id": user["id"], "role": user["role"]}

    def filter_inventory(
        self,
        area: Optional[str] = None,
        format_code: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        immediate_only: bool = False,
        include_unapproved: bool = False,
    ) -> List[Dict]:
        results = [
            item
            for item in self.inventory
            if include_unapproved or (item.get("status") == "Approved" and item.get("vendor_verified", False))
        ]
        if area:
            results = [i for i in results if area.lower() in i["area"].lower() or area.lower() in i["title"].lower()]
        if format_code:
            results = [i for i in results if i["format_code"].upper() == format_code.upper()]
        if min_price is not None:
            results = [i for i in results if i["display_cost_pm"] >= min_price]
        if max_price is not None:
            results = [i for i in results if i["display_cost_pm"] <= max_price]
        if immediate_only:
            results = [i for i in results if i["is_immediate"]]
        return results

    def vendor_submit_asset(self, vendor_user: Dict, asset_payload: Dict) -> Dict:
        if not check_permission(vendor_user["role"], "vendor:inventory:create"):
            raise PermissionError("User role not permitted to submit vendor inventory.")
        new_id = f"DA-PUN-{len(self.inventory) + 1:03d}"
        w = float(asset_payload["width_ft"])
        h = float(asset_payload["height_ft"])
        qty = int(asset_payload.get("qty", 1))
        record = {
            "id": new_id,
            "seq": len(self.inventory) + 1,
            "sr_no": str(len(self.inventory) + 1),
            "city": asset_payload.get("city", "Pune"),
            "area": asset_payload["area"],
            "media_category": asset_payload.get("media_category", "Outdoor Hoardings"),
            "title": asset_payload["title"],
            "format_code": asset_payload.get("format_code", "FL"),
            "is_digital": asset_payload.get("format_code") == "LED",
            "width_ft": w,
            "height_ft": h,
            "qty": qty,
            "area_sqft": round(w * h * qty, 2),
            "display_cost_pm": int(asset_payload["display_cost_pm"]),
            "installation_cost": int(asset_payload.get("installation_cost", w * h * qty * 4)),
            "printing_cost": int(asset_payload.get("printing_cost", w * h * qty * 12)),
            "availability": asset_payload.get("availability", "Immediate"),
            "is_immediate": asset_payload.get("availability", "Immediate") == "Immediate",
            "lat": float(asset_payload.get("lat", 18.5204)),
            "lng": float(asset_payload.get("lng", 73.8567)),
            "vendor_id": vendor_user["id"],
            "vendor_name": vendor_user.get("full_name", "Vendor"),
            "vendor_verified": bool(vendor_user.get("vendor_verified", False)),
            "status": "Pending Verification",
            "is_demo_data": True,
        }
        self.inventory.append(record)
        self._log_audit(vendor_user["id"], vendor_user["role"], "inventory.submit", "media_assets", new_id)
        return record

    def admin_verify_asset(self, admin_user: Dict, asset_id: str, new_status: str) -> Dict:
        if not check_permission(admin_user["role"], "manage:inventory"):
            raise PermissionError("Unauthorized: Inventory Manager or Owner role required.")
        for item in self.inventory:
            if item["id"] == asset_id:
                item["status"] = new_status
                if new_status == "Approved":
                    item["vendor_verified"] = True
                self._log_audit(admin_user["id"], admin_user["role"], f"asset.{new_status}", "media_assets", asset_id)
                return item
        raise KeyError(f"Asset {asset_id} not found")

    def validate_file_upload(self, filename: str, size_bytes: int, content_type: str) -> Dict:
        ext = os.path.splitext(filename.lower())[1]
        if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise ValueError(f"Disallowed file extension: {ext}")
        if size_bytes <= 0 or size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("File size exceeds 10 MB limit or is empty.")
        if not content_type.startswith(("image/", "application/pdf")):
            raise ValueError("Unsupported MIME content type.")
        return {"presigned_url": f"https://{settings.APP_NAME.lower()}-media.s3.ap-south-1.amazonaws.com/uploads/{filename}", "expires_in": 600}

    def get_customer_bookings(self, actor: Dict, target_customer_id: str) -> List[Dict]:
        if actor["role"] == "customer" and actor["id"] != target_customer_id:
            raise PermissionError("Customer data isolation violation.")
        return [b for b in self.booking_engine.bookings.values() if b["customer_id"] == target_customer_id]

    def get_vendor_bookings(self, actor: Dict, target_vendor_id: str) -> List[Dict]:
        if actor["role"] == "vendor" and actor["id"] != target_vendor_id:
            raise PermissionError("Vendor data isolation violation.")
        return [b for b in self.booking_engine.bookings.values() if b.get("vendor_id") == target_vendor_id]

    def _log_audit(self, actor_id: str, role: str, action: str, entity_type: str, entity_id: str):
        self.audit_logs.append(
            {"actor_id": actor_id, "role": role, "action": action, "entity_type": entity_type, "entity_id": entity_id}
        )


    def scan_qr_and_book_banner(
        self,
        qr_token_or_asset_id: str,
        customer_id: str,
        start_date,
        end_date,
        duration_months: int = 1,
        include_printing: bool = True,
    ) -> Dict:
        resolved = self.qr_service.resolve_scanned_qr(qr_token_or_asset_id, self.inventory)
        asset = resolved["asset"]
        quote = calculate_quotation_pricing([{**asset, "duration_months": duration_months}])
        booking_id = f"BKG-QR-{len(self.booking_engine.bookings) + 1:04d}"
        hold = self.booking_engine.place_booking_hold(
            booking_id=booking_id,
            asset=asset,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            total_payable=quote["grand_total"],
        )
        self.payment_service.init_booking_ledger(booking_id, quote["grand_total"])
        self._log_audit(customer_id, "customer", "qr.instant_booking_hold", "bookings", booking_id)
        hold["id"] = booking_id
        return {"qr_resolution": resolved, "pricing": quote, "booking": hold}

    def submit_order_review(
        self,
        booking_id: str,
        customer_id: str,
        customer_name: str,
        rating: int,
        visibility_rating: int,
        mounting_quality_rating: int,
        title: str,
        comment: str,
        post_to_google_maps: bool = True,
    ) -> Dict:
        if booking_id not in self.booking_engine.bookings:
            raise KeyError(f"Booking {booking_id} not found.")
        booking = self.booking_engine.bookings[booking_id]
        asset = next((a for a in self.inventory if a["id"] == booking["asset_id"]), self.inventory[0])
        rev = self.review_service.submit_completed_order_review(
            booking=booking,
            asset=asset,
            customer_id=customer_id,
            customer_name=customer_name,
            rating=rating,
            visibility_rating=visibility_rating,
            mounting_quality_rating=mounting_quality_rating,
            title=title,
            comment=comment,
            post_to_google_maps=post_to_google_maps,
        )
        self._log_audit(customer_id, "customer", "review.submitted", "completed_order_reviews", rev["id"])
        return rev


# Expose ASGI `app` on `app.main:app` for Uvicorn / Gunicorn startup
try:
    from app.api.routes import create_fastapi_app
    app = create_fastapi_app()
except Exception as _exc:
    app = None
