import datetime
import hashlib
import hmac
import pytest
from app.core.security import check_permission
from app.main import MarketplacePlatformKernel
from app.workers.automation_tasks import ProductionAutomationWorker


@pytest.fixture
def kernel():
    return MarketplacePlatformKernel()


def test_prod_01_single_owner_invariant(kernel):
    owner = kernel.staff_service.bootstrap_master_owner("owner@dreamsadverstings.in", "OwnerSecret#2026", "Master Owner")
    assert owner["role"] == "owner"
    with pytest.raises(ValueError, match="SINGLE_OWNER_VIOLATION"):
        kernel.staff_service.bootstrap_master_owner("owner2@dreamsadverstings.in", "OwnerSecret#2026", "Second Owner")
    with pytest.raises(ValueError, match="SINGLE_OWNER_VIOLATION"):
        kernel.staff_service.add_employee(owner, "fakeowner@dreamsadverstings.in", "Pass#1234", "Fake Owner", "owner", "Exec")


def test_prod_02_11_role_staff_permissions(kernel):
    owner = kernel.staff_service.bootstrap_master_owner("owner@dreamsadverstings.in", "OwnerSecret#2026", "Master Owner")
    fin = kernel.staff_service.add_employee(owner, "fin@dreamsadverstings.in", "FinPass#2026", "Finance Mgr", "finance_manager", "Finance")
    sales = kernel.staff_service.add_employee(owner, "sales@dreamsadverstings.in", "SalesPass#2026", "Sales Exec", "sales_executive", "Sales")
    inv = kernel.staff_service.add_employee(owner, "inv@dreamsadverstings.in", "InvPass#2026", "Inventory Mgr", "inventory_manager", "Ops")

    with pytest.raises(PermissionError):
        kernel.gst_service.update_company_config(fin, {"gstin": "27FAKEGSTIN1234"})

    assert check_permission(sales["role"], "owner:financial_reports") is False
    assert check_permission(inv["role"], "manage:payments") is False
    assert check_permission(fin["role"], "manage:payments") is True
    assert check_permission(owner["role"], "owner:gst_config") is True


def test_prod_03_led_slot_capacity_partial_booking(kernel):
    led_asset = next(a for a in kernel.inventory if a["id"] == "DA-PUN-086")
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 31)

    kernel.booking_engine.place_booking_hold("BKG-LED-1", led_asset, "CUST-1", start, end, 600000.0, slots_requested=2)
    cap = kernel.booking_engine.led_engine.get_capacity_for_dates(led_asset["id"], start, end)
    assert cap["booked_slots"] == 2
    assert cap["available_slots"] == 10
    assert cap["is_bookable"] is True

    with pytest.raises(ValueError, match="LED_CAPACITY_EXCEEDED"):
        kernel.booking_engine.place_booking_hold("BKG-LED-FAIL", led_asset, "CUST-2", start, end, 3300000.0, slots_requested=11)


def test_prod_04_maintenance_block_prevents_booking(kernel):
    asset = kernel.inventory[0]
    start = datetime.date(2027, 1, 10)
    end = datetime.date(2027, 1, 20)
    kernel.booking_engine.add_maintenance_block(asset["id"], start, end, "Structural Wind-Load Inspection")
    avail = kernel.booking_engine.check_asset_availability(asset, start, end)
    assert avail["available"] is False


def test_prod_05_indian_gst_cgst_sgst_vs_igst(kernel):
    items = [
        {"service_key": "static_hoarding", "amount_inr": 100000.0},
        {"service_key": "printing_mounting", "amount_inr": 10000.0},
    ]
    intra = kernel.gst_service.calculate_gst_line_items(items, place_of_supply_state_code="27", discount_inr=0.0)
    assert intra["cgst_amount"] == 9600.0
    assert intra["sgst_amount"] == 9600.0
    assert intra["igst_amount"] == 0.0
    assert intra["grand_total"] == 129200.0

    inter = kernel.gst_service.calculate_gst_line_items(items, place_of_supply_state_code="29")
    assert inter["igst_amount"] == 19200.0


def test_prod_06_atomic_fy_invoice_and_immutability(kernel):
    cust = {"id": "CUST-1", "full_name": "Pune Brand Pvt Ltd", "gstin": "27AAACB1234F1Z2"}
    tax = kernel.gst_service.calculate_gst_line_items([{"service_key": "static_hoarding", "amount_inr": 140000.0}])
    inv1 = kernel.gst_service.issue_document("GST Tax Invoice", cust, "BKG-1", tax, payment_ref="pay_1")
    inv2 = kernel.gst_service.issue_document("GST Tax Invoice", cust, "BKG-2", tax, payment_ref="pay_2")
    assert inv1["document_number"] == "DA/2026-27/INV/0001"
    assert inv2["document_number"] == "DA/2026-27/INV/0002"
    with pytest.raises(PermissionError, match="IMMUTABLE_GST_DOCUMENT"):
        kernel.gst_service.modify_or_delete_invoice(inv1["document_number"], {"role": "finance_manager"})


def test_prod_07_partial_payments_and_failed_receipt_guard(kernel):
    b_id = "BKG-PARTIAL-1"
    o1 = kernel.payment_service.create_order(b_id, 100000.0, "CUST-1", total_booking_payable=250000.0, partial=True)
    sig1 = kernel.payment_service.generate_payment_signature(o1["order_id"], "pay_p1")
    res1 = kernel.payment_service.verify_payment(o1["order_id"], "pay_p1", sig1)
    assert res1["outstanding_balance_inr"] == 150000.0
    assert res1["reconciliation_status"] == "Partially Paid"

    o2 = kernel.payment_service.create_order(b_id, 150000.0, "CUST-1", total_booking_payable=250000.0, partial=True)
    fail = kernel.payment_service.record_failed_payment(o2["order_id"], "pay_fail_1", "Insufficient funds")
    assert fail["receipt_allowed"] is False


def test_prod_08_qr_scan_and_completed_order_review(kernel):
    qr_res = kernel.scan_qr_and_book_banner(
        qr_token_or_asset_id="DA-QR-DA-PUN-001",
        customer_id="CUST-QR-02",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 31),
        duration_months=1,
    )
    qr_bkg_id = qr_res["booking"]["id"]
    with pytest.raises(ValueError, match="ORDER_NOT_COMPLETED_FOR_REVIEW"):
        kernel.submit_order_review(qr_bkg_id, "CUST-QR-02", "Vikram", 5, 5, 5, "Title", "Comment")

    asset_001 = qr_res["qr_resolution"]["asset"]
    kernel.booking_engine.transition_status(qr_bkg_id, "Confirmed", "CUST-QR-02", asset=asset_001)
    kernel.booking_engine.transition_status(qr_bkg_id, "In Execution", "STAFF-OPS-01", asset=asset_001)
    kernel.booking_engine.transition_status(qr_bkg_id, "Completed", "STAFF-OPS-01", asset=asset_001)

    rev = kernel.submit_order_review(qr_bkg_id, "CUST-QR-02", "Vikram", 5, 5, 5, "Great", "Completed!")
    assert rev["verified_completed_order"] is True


def test_prod_09_map_3color_and_multi_portal_auth(kernel):
    summary = kernel.analytics_service.get_map_3color_summary()
    assert summary["counts"]["red"] + summary["counts"]["orange"] + summary["counts"]["green"] == 156

    o_sess = kernel.portal_auth_service.authenticate_portal(
        "admin", "owner@dreamsadverstings.in", "Owner#2026", two_factor_pin="123456"
    )
    assert o_sess["role"] == "owner"

    worker = ProductionAutomationWorker(kernel)
    digest = worker.generate_daily_owner_digest()
    assert digest["total_inventory"] == 156
