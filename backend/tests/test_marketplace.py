import datetime
import pytest
from app.core.security import check_permission, decode_jwt_token
from app.main import MarketplacePlatformKernel
from app.services.pricing_engine import calculate_quotation_pricing


@pytest.fixture
def kernel():
    return MarketplacePlatformKernel()


def test_01_user_registration(kernel):
    user = kernel.register_user("brand@advertiser.in", "StrongPass#2026", "Aarav Deshmukh", role="customer")
    assert user["email"] == "brand@advertiser.in"
    assert user["role"] == "customer"
    assert "password_hash" not in user
    with pytest.raises(ValueError, match="Email already registered"):
        kernel.register_user("brand@advertiser.in", "StrongPass#2026", "Duplicate")


def test_02_user_login_and_jwt(kernel):
    kernel.register_user("login@advertiser.in", "SecureLogin#99", "Priya Kulkarni", role="customer")
    tokens = kernel.login_user("login@advertiser.in", "SecureLogin#99")
    assert "access_token" in tokens and "refresh_token" in tokens
    decoded = decode_jwt_token(tokens["access_token"], expected_type="access")
    assert decoded["role"] == "customer"
    with pytest.raises(PermissionError):
        kernel.login_user("login@advertiser.in", "WrongPassword123")


def test_03_role_permissions_rbac():
    assert check_permission("admin", "manage:settings") is True
    assert check_permission("sales_employee", "manage:quotations") is True
    assert check_permission("sales_employee", "manage:settings") is False
    assert check_permission("finance_employee", "manage:payments") is True
    assert check_permission("inventory_manager", "verify:vendors") is True
    assert check_permission("customer", "manage:inventory") is False
    assert check_permission("vendor", "vendor:inventory:create") is True


def test_04_inventory_management_and_vendor_verification_gate(kernel):
    vendor = kernel.register_user("owner@punehoardings.in", "VendorPass#2026", "Pune Media Owner", role="vendor")
    admin = kernel.register_user("admin@dreamsadverstings.in", "AdminPass#2026", "System Admin", role="admin")

    new_asset = kernel.vendor_submit_asset(
        vendor,
        {
            "title": "Baner High Street Facing Balewadi Demo Unipole",
            "area": "Baner",
            "format_code": "FL",
            "width_ft": 30,
            "height_ft": 20,
            "display_cost_pm": 210000,
        },
    )
    assert new_asset["status"] == "Pending Verification"

    # Unverified asset must NOT appear in public bookable inventory
    public_list = kernel.filter_inventory(area="Baner")
    assert all(a["id"] != new_asset["id"] for a in public_list)

    # Admin approves the asset -> now bookable
    approved_asset = kernel.admin_verify_asset(admin, new_asset["id"], "Approved")
    assert approved_asset["status"] == "Approved"
    public_after = kernel.filter_inventory(area="Baner")
    assert any(a["id"] == new_asset["id"] for a in public_after)


def test_05_media_filtering_marquis_pune_seed(kernel):
    assert len(kernel.inventory) == 156
    baner_assets = kernel.filter_inventory(area="Baner")
    assert len(baner_assets) >= 15
    dooh_assets = kernel.filter_inventory(format_code="LED")
    assert len(dooh_assets) == 6
    immediate_assets = kernel.filter_inventory(immediate_only=True)
    assert len(immediate_assets) >= 35
    budget_assets = kernel.filter_inventory(max_price=100000)
    assert all(a["display_cost_pm"] <= 100000 for a in budget_assets)


def test_06_quotation_calculations_backend_authoritative(kernel):
    sample_items = [kernel.inventory[0], kernel.inventory[83]]  # 1 static FL + 1 DOOH LED
    quote = calculate_quotation_pricing(
        [
            {**sample_items[0], "duration_months": 2},
            {**sample_items[1], "duration_months": 1},
        ],
        additional_services_inr=5000.0,
    )
    # Item 0: 140000 * 2 = 280000 display, 1600 inst, 4800 print
    # Item 1 (DOOH LED): 300000 * 1 = 300000 display, 0 inst, 0 print
    assert quote["subtotal_display"] == 580000.0
    assert quote["installation_total"] == 1600.0
    assert quote["printing_total"] == 4800.0
    assert quote["platform_commission"] == 46400.0  # 8% of 580,000
    assert quote["taxable_amount"] == 637800.0
    assert quote["gst_amount"] == 114804.0  # 18% GST
    assert quote["grand_total"] == 752604.0


def test_07_booking_availability_check(kernel):
    asset = kernel.inventory[0]  # Immediate availability
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 31)
    avail = kernel.booking_engine.check_asset_availability(asset, start, end)
    assert avail["available"] is True

    # Invalid date range rejected
    bad_avail = kernel.booking_engine.check_asset_availability(asset, end, start)
    assert bad_avail["available"] is False


def test_08_concurrent_booking_requests_and_overlap_prevention(kernel):
    asset = kernel.inventory[0]
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 31)

    hold1 = kernel.booking_engine.place_booking_hold(
        "BKG-001", asset, "USR-001", start, end, total_payable=175000.0
    )
    assert hold1["status"] == "Payment Pending"

    # Concurrent overlapping request for same asset & dates must fail
    with pytest.raises(ValueError, match="temporary booking hold"):
        kernel.booking_engine.place_booking_hold(
            "BKG-002",
            asset,
            "USR-002",
            datetime.date(2026, 12, 15),
            datetime.date(2027, 1, 15),
            total_payable=175000.0,
        )


def test_09_payment_verification_and_duplicate_prevention(kernel):
    order = kernel.payment_service.create_order("BKG-100", 200000.0, "USR-001")
    sig = kernel.payment_service.generate_payment_signature(order["order_id"], "pay_test_001")

    verified = kernel.payment_service.verify_payment(order["order_id"], "pay_test_001", sig)
    assert verified["verified"] is True

    # Duplicate payment reference rejected
    with pytest.raises(ValueError, match="Duplicate payment reference"):
        kernel.payment_service.verify_payment(order["order_id"], "pay_test_001", sig)

    # Tampered signature rejected
    order2 = kernel.payment_service.create_order("BKG-101", 150000.0, "USR-001")
    with pytest.raises(PermissionError, match="signature verification failed"):
        kernel.payment_service.verify_payment(order2["order_id"], "pay_test_002", "tampered_sig")


def test_10_webhook_signature_handling(kernel):
    import hashlib
    import hmac
    from app.core.config import settings

    raw_payload = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_99"}}}}'
    valid_sig = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_payload, hashlib.sha256
    ).hexdigest()

    assert kernel.payment_service.verify_webhook(raw_payload, valid_sig, "evt_001") is True
    with pytest.raises(ValueError, match="Duplicate webhook"):
        kernel.payment_service.verify_webhook(raw_payload, valid_sig, "evt_001")
    with pytest.raises(PermissionError, match="Invalid Razorpay webhook"):
        kernel.payment_service.verify_webhook(raw_payload, "bad_sig", "evt_002")


def test_11_file_upload_restrictions(kernel):
    res = kernel.validate_file_upload("proof_baner_hoarding.jpg", 2500000, "image/jpeg")
    assert "presigned_url" in res
    with pytest.raises(ValueError, match="Disallowed file extension"):
        kernel.validate_file_upload("malicious_script.exe", 1024, "application/octet-stream")
    with pytest.raises(ValueError, match="File size exceeds"):
        kernel.validate_file_upload("huge.png", 25 * 1024 * 1024, "image/png")


def test_12_campaign_and_booking_status_transitions(kernel):
    asset = kernel.inventory[2]
    start = datetime.date(2027, 1, 1)
    end = datetime.date(2027, 1, 31)
    kernel.booking_engine.place_booking_hold("BKG-300", asset, "USR-001", start, end, 95000.0)
    kernel.booking_engine.transition_status("BKG-300", "Confirmed", "USR-001", asset=asset)
    kernel.booking_engine.transition_status("BKG-300", "In Execution", "VEND-001")
    completed = kernel.booking_engine.transition_status("BKG-300", "Completed", "ADMIN-001")
    assert completed["status"] == "Completed"
    assert len([h for h in kernel.booking_engine.history if h["booking_id"] == "BKG-300"]) == 4


def test_13_customer_data_isolation(kernel):
    c1 = kernel.register_user("c1@brand.in", "Customer1#Pass", "Customer One", role="customer")
    c2 = kernel.register_user("c2@brand.in", "Customer2#Pass", "Customer Two", role="customer")
    asset = kernel.inventory[4]
    kernel.booking_engine.place_booking_hold(
        "BKG-C1", asset, c1["id"], datetime.date(2027, 2, 1), datetime.date(2027, 2, 28), 310000.0
    )
    own = kernel.get_customer_bookings(c1, c1["id"])
    assert len(own) == 1
    with pytest.raises(PermissionError, match="Customer data isolation"):
        kernel.get_customer_bookings(c2, c1["id"])


def test_14_vendor_data_isolation(kernel):
    v1 = kernel.register_user("v1@media.in", "Vendor1#Pass", "Vendor One", role="vendor")
    v2 = kernel.register_user("v2@media.in", "Vendor2#Pass", "Vendor Two", role="vendor")
    with pytest.raises(PermissionError, match="Vendor data isolation"):
        kernel.get_vendor_bookings(v2, v1["id"])


def test_15_admin_functionality_and_ai_planner(kernel):
    c1 = kernel.register_user("unauth@brand.in", "Customer#Pass9", "Regular User", role="customer")
    with pytest.raises(PermissionError, match="Unauthorized"):
        kernel.admin_verify_asset(c1, "DA-PUN-001", "Suspended")

    plan = kernel.ai_planner.recommend_shortlist(
        budget_inr=600000, preferred_areas=["Baner", "FC Road"], duration_months=1
    )
    assert plan["recommended_count"] >= 1
    assert all(item["status"] == "Approved" for item in plan["shortlist"])
