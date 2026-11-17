# Database Migration & Data Safety Plan

## 1. Pre-Migration Safety Checklist
1. Inspect existing 34 tables in `001_initial_schema.py` and verify all 156 Pune inventory rows.
2. Execute `scripts/backup_db.sh` (`pg_dump --format=custom`) before applying any DDL changes.
3. Apply `alembic upgrade head` on staging copy first; verify zero destructive drops (`DROP TABLE` is strictly forbidden).

## 2. New Tables Added in `002_production_upgrade.py`
- `gst_company_config`: Legal name, GSTIN, PAN, Maharashtra state code (`27`), FY, invoice prefix.
- `hsn_sac_mappings`: Configurable HSN/SAC codes and per-service GST/cess rates.
- `led_screen_configs` & `led_slot_bookings`: Operating hours, slot/loop duration, max slots, and slot-level reservations.
- `maintenance_blocks`: Date-range maintenance holds on physical assets.
- `invoice_sequences`: Atomic financial-year sequential document counters.
- `gst_documents`: Immutable storage for all 8 document types (Quotation, Booking Confirmation, Payment Receipt, Advance Receipt Voucher, GST Tax Invoice, Credit Note, Debit Note, Refund Confirmation).
- `staff_profiles` & `staff_assignments`: 11-role staff metadata, departments, and customer/campaign assignments.
- `customer_messaging_consent`, `whatsapp_templates`, `message_delivery_logs`: Opt-in/opt-out consent and idempotent delivery audit trail.
- `payment_reconciliations`: Multi-installment and Razorpay settlement reconciliation records.

## 3. Rollback Strategy
- `alembic downgrade 001_initial_schema` cleanly drops only the additive upgrade tables while preserving all original `001` tables and 156 Pune inventory records.
