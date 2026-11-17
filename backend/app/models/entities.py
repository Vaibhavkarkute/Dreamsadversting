import datetime
from typing import List
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TimestampSoftDeleteMixin:
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )
    is_deleted = Column(Boolean, default=False, nullable=False)


# 1. users
class User(Base, TimestampSoftDeleteMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    google_oauth_sub = Column(String(255), unique=True, nullable=True)


# 2. roles
class Role(Base, TimestampSoftDeleteMixin):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)


# 3. permissions
class Permission(Base, TimestampSoftDeleteMixin):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(128), unique=True, nullable=False, index=True)
    module = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)


# 4. user_roles
class UserRole(Base, TimestampSoftDeleteMixin):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


# 5. customer_profiles
class CustomerProfile(Base, TimestampSoftDeleteMixin):
    __tablename__ = "customer_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    gst_number = Column(String(32), nullable=True, index=True)
    industry = Column(String(128), nullable=True)
    billing_address = Column(Text, nullable=True)
    city = Column(String(128), default="Pune")


# 6. vendor_profiles
class VendorProfile(Base, TimestampSoftDeleteMixin):
    __tablename__ = "vendor_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String(255), nullable=False, index=True)
    gst_number = Column(String(32), nullable=True, index=True)
    pan_number = Column(String(20), nullable=True)
    pmc_license_no = Column(String(128), nullable=True)
    verification_status = Column(
        String(32), default="Pending Verification", nullable=False, index=True
    )  # Pending Verification, Under Review, Approved, Rejected, Suspended
    commission_rate = Column(Float, default=0.08, nullable=False)
    headquarters_city = Column(String(128), default="Pune")


# 7. vendor_documents
class VendorDocument(Base, TimestampSoftDeleteMixin):
    __tablename__ = "vendor_documents"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(64), nullable=False)  # GST, PMC_PERMIT, STRUCTURAL_SAFETY
    s3_key = Column(String(512), nullable=False)
    verification_status = Column(String(32), default="Pending Verification", nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)


# 8. cities
class City(Base, TimestampSoftDeleteMixin):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    state = Column(String(128), default="Maharashtra", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


# 9. areas
class Area(Base, TimestampSoftDeleteMixin):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    zone_code = Column(String(64), nullable=True)
    center_lat = Column(Float, nullable=True)
    center_lng = Column(Float, nullable=True)
    __table_args__ = (UniqueConstraint("city_id", "name", name="uq_city_area_name"),)


# 10. media_categories
class MediaCategory(Base, TimestampSoftDeleteMixin):
    __tablename__ = "media_categories"
    id = Column(Integer, primary_key=True)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_digital = Column(Boolean, default=False, nullable=False)
    typical_lead_days = Column(Integer, default=7, nullable=False)


# 11. media_assets
class MediaAsset(Base, TimestampSoftDeleteMixin):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True)
    asset_code = Column(String(64), unique=True, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor_profiles.id"), nullable=False, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("media_categories.id"), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    format_type = Column(String(32), nullable=False, index=True)  # FL, NL, BL, LED
    is_digital = Column(Boolean, default=False, nullable=False, index=True)
    width_ft = Column(Float, nullable=False)
    height_ft = Column(Float, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    area_sqft = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    verification_status = Column(
        String(32), default="Pending Verification", nullable=False, index=True
    )  # Pending Verification, Under Review, Approved, Rejected, Suspended
    is_demo_data = Column(Boolean, default=True, nullable=False)
    remark = Column(String(255), nullable=True)


# 12. media_images
class MediaImage(Base, TimestampSoftDeleteMixin):
    __tablename__ = "media_images"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    s3_url = Column(String(512), nullable=False)
    caption = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)


# 13. media_availability
class MediaAvailability(Base, TimestampSoftDeleteMixin):
    __tablename__ = "media_availability"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    available_from = Column(Date, nullable=False, index=True)
    available_to = Column(Date, nullable=True, index=True)
    is_immediate = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="Available", nullable=False)  # Available, Held, Booked, Blocked


# 14. media_pricing
class MediaPricing(Base, TimestampSoftDeleteMixin):
    __tablename__ = "media_pricing"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="CASCADE"), unique=True, nullable=False)
    display_cost_monthly = Column(Numeric(12, 2), nullable=False)
    installation_charge = Column(Numeric(12, 2), default=0, nullable=False)
    printing_charge = Column(Numeric(12, 2), default=0, nullable=False)
    production_charge = Column(Numeric(12, 2), default=0, nullable=False)
    min_booking_days = Column(Integer, default=30, nullable=False)
    currency = Column(String(8), default="INR", nullable=False)


# 15. campaigns
class Campaign(Base, TimestampSoftDeleteMixin):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    campaign_code = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    objective = Column(String(128), nullable=False)
    target_audience = Column(String(255), nullable=True)
    preferred_city = Column(String(128), default="Pune", nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget_inr = Column(Numeric(14, 2), nullable=False)
    status = Column(String(32), default="Draft", nullable=False, index=True)


# 16. campaign_assets
class CampaignAsset(Base, TimestampSoftDeleteMixin):
    __tablename__ = "campaign_assets"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    duration_months = Column(Integer, default=1, nullable=False)
    __table_args__ = (UniqueConstraint("campaign_id", "asset_id", name="uq_campaign_asset"),)


# 17. enquiries
class Enquiry(Base, TimestampSoftDeleteMixin):
    __tablename__ = "enquiries"
    id = Column(Integer, primary_key=True)
    enquiry_code = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(32), nullable=False)
    company_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(32), default="Enquiry Submitted", nullable=False, index=True)


# 18. quotations
class Quotation(Base, TimestampSoftDeleteMixin):
    __tablename__ = "quotations"
    id = Column(Integer, primary_key=True)
    quotation_number = Column(String(64), unique=True, nullable=False, index=True)
    enquiry_id = Column(Integer, ForeignKey("enquiries.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prepared_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subtotal_display = Column(Numeric(14, 2), nullable=False)
    installation_total = Column(Numeric(14, 2), nullable=False)
    printing_total = Column(Numeric(14, 2), nullable=False)
    additional_services_total = Column(Numeric(14, 2), default=0, nullable=False)
    platform_commission = Column(Numeric(14, 2), nullable=False)
    taxable_amount = Column(Numeric(14, 2), nullable=False)
    gst_amount = Column(Numeric(14, 2), nullable=False)
    grand_total = Column(Numeric(14, 2), nullable=False)
    valid_until = Column(Date, nullable=False)
    status = Column(String(32), default="Quotation Sent", nullable=False, index=True)


# 19. quotation_items
class QuotationItem(Base, TimestampSoftDeleteMixin):
    __tablename__ = "quotation_items"
    id = Column(Integer, primary_key=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id"), nullable=False)
    duration_months = Column(Integer, default=1, nullable=False)
    monthly_rate = Column(Numeric(12, 2), nullable=False)
    installation_charge = Column(Numeric(12, 2), nullable=False)
    printing_charge = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(14, 2), nullable=False)


# 20. bookings
class Booking(Base, TimestampSoftDeleteMixin):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    booking_code = Column(String(64), unique=True, nullable=False, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("media_assets.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    status = Column(
        String(32), default="Draft", nullable=False, index=True
    )  # Draft, Enquiry Submitted, Quotation Pending, Quotation Sent, Awaiting Approval, Payment Pending, Confirmed, In Execution, Completed, Cancelled, Refund Pending, Refunded
    hold_expires_at = Column(DateTime, nullable=True)
    total_payable = Column(Numeric(14, 2), nullable=False)
    __table_args__ = (
        Index("ix_booking_asset_dates_status", "asset_id", "start_date", "end_date", "status"),
    )


# 21. booking_status_history
class BookingStatusHistory(Base, TimestampSoftDeleteMixin):
    __tablename__ = "booking_status_history"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)


# 22. payments
class Payment(Base, TimestampSoftDeleteMixin):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    razorpay_order_id = Column(String(128), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(128), unique=True, nullable=True, index=True)
    razorpay_signature = Column(String(256), nullable=True)
    amount_inr = Column(Numeric(14, 2), nullable=False)
    status = Column(String(32), default="Created", nullable=False, index=True)  # Created, Verified, Failed
    idempotency_key = Column(String(128), unique=True, nullable=False)


# 23. refunds
class Refund(Base, TimestampSoftDeleteMixin):
    __tablename__ = "refunds"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    razorpay_refund_id = Column(String(128), unique=True, nullable=True)
    amount_inr = Column(Numeric(14, 2), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(32), default="Refund Pending", nullable=False)


# 24. invoices
class Invoice(Base, TimestampSoftDeleteMixin):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(64), unique=True, nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    taxable_amount = Column(Numeric(14, 2), nullable=False)
    cgst_amount = Column(Numeric(14, 2), nullable=False)
    sgst_amount = Column(Numeric(14, 2), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    pdf_s3_key = Column(String(512), nullable=True)


# 25. campaign_execution
class CampaignExecution(Base, TimestampSoftDeleteMixin):
    __tablename__ = "campaign_execution"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendor_profiles.id"), nullable=False, index=True)
    installation_date = Column(Date, nullable=True)
    execution_status = Column(
        String(32), default="Scheduled", nullable=False
    )  # Scheduled, Mounted, Proof Uploaded, Admin Verified, Completed
    verified_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)


# 26. proof_of_display
class ProofOfDisplay(Base, TimestampSoftDeleteMixin):
    __tablename__ = "proof_of_display"
    id = Column(Integer, primary_key=True)
    execution_id = Column(
        Integer, ForeignKey("campaign_execution.id", ondelete="CASCADE"), nullable=False, index=True
    )
    photo_s3_url = Column(String(512), nullable=False)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    admin_approved = Column(Boolean, default=False, nullable=False)


# 27. portfolios
class Portfolio(Base, TimestampSoftDeleteMixin):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    client_name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)  # OOH, DOOH, Transit, Mall, Brand Activation, Events
    location = Column(String(255), nullable=False)
    media_format = Column(String(128), nullable=False)
    duration = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    verified_outcome = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=True, nullable=False)


# 28. case_studies
class CaseStudy(Base, TimestampSoftDeleteMixin):
    __tablename__ = "case_studies"
    id = Column(Integer, primary_key=True)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    client_requirements = Column(Text, nullable=False)
    campaign_objectives = Column(Text, nullable=False)
    media_strategy = Column(Text, nullable=False)
    selected_locations = Column(Text, nullable=False)
    campaign_execution_notes = Column(Text, nullable=False)
    results_and_measurements = Column(Text, nullable=False)
    is_template = Column(Boolean, default=True, nullable=False)


# 29. client_logos
class ClientLogo(Base, TimestampSoftDeleteMixin):
    __tablename__ = "client_logos"
    id = Column(Integer, primary_key=True)
    brand_name = Column(String(255), nullable=False)
    industry = Column(String(128), nullable=True)
    logo_s3_url = Column(String(512), nullable=False)
    is_placeholder = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=1, nullable=False)


# 30. testimonials
class Testimonial(Base, TimestampSoftDeleteMixin):
    __tablename__ = "testimonials"
    id = Column(Integer, primary_key=True)
    author_name = Column(String(255), nullable=False)
    author_role = Column(String(128), nullable=False)
    company_name = Column(String(255), nullable=False)
    quote_text = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True, nullable=False)
    is_placeholder = Column(Boolean, default=True, nullable=False)


# 31. notifications
class Notification(Base, TimestampSoftDeleteMixin):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), default="in_app", nullable=False)  # in_app, email, whatsapp, sms
    event_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)


# 32. support_tickets
class SupportTicket(Base, TimestampSoftDeleteMixin):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    ticket_code = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(32), default="Normal", nullable=False)
    status = Column(String(32), default="Open", nullable=False, index=True)


# 33. audit_logs
class AuditLog(Base, TimestampSoftDeleteMixin):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_role = Column(String(64), nullable=False)
    action = Column(String(128), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False)
    ip_address = Column(String(64), nullable=True)
    metadata_json = Column(Text, nullable=True)


# 34. system_settings
class SystemSetting(Base, TimestampSoftDeleteMixin):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(128), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
