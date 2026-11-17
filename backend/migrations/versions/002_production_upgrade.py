"""Additive production upgrade migration: Single-Owner & 11-Role Staff, LED Slot Capacity,
Indian GST Config/HSN/8 Atomic Documents, Partial Payment Ledgers & Messaging Logs.

Revision ID: 002_production_upgrade
Revises: 001_initial_schema
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa

revision = "002_production_upgrade"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "gst_company_config" not in existing:
        op.create_table(
            "gst_company_config",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("legal_name", sa.String(255), nullable=False),
            sa.Column("gstin", sa.String(15), nullable=False),
            sa.Column("pan", sa.String(10), nullable=False),
            sa.Column("state_code", sa.String(2), nullable=False, server_default="27"),
            sa.Column("financial_year", sa.String(16), nullable=False),
            sa.Column("invoice_prefix", sa.String(16), nullable=False),
        )
    if "hsn_sac_mappings" not in existing:
        op.create_table(
            "hsn_sac_mappings",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("service_key", sa.String(64), unique=True, nullable=False),
            sa.Column("sac_code", sa.String(16), nullable=False),
            sa.Column("gst_rate", sa.Float, nullable=False),
            sa.Column("cess_rate", sa.Float, nullable=False, server_default="0"),
        )
    if "led_screen_configs" not in existing:
        op.create_table(
            "led_screen_configs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("asset_id", sa.Integer, sa.ForeignKey("media_assets.id"), unique=True, nullable=False),
            sa.Column("operating_hours_per_day", sa.Float, nullable=False),
            sa.Column("slot_duration_sec", sa.Integer, nullable=False),
            sa.Column("loop_duration_sec", sa.Integer, nullable=False),
            sa.Column("max_slots", sa.Integer, nullable=False),
        )
    if "led_slot_bookings" not in existing:
        op.create_table(
            "led_slot_bookings",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("booking_id", sa.Integer, sa.ForeignKey("bookings.id"), nullable=False),
            sa.Column("asset_id", sa.Integer, sa.ForeignKey("media_assets.id"), nullable=False),
            sa.Column("slots_booked", sa.Integer, nullable=False),
            sa.Column("start_date", sa.Date, nullable=False),
            sa.Column("end_date", sa.Date, nullable=False),
        )
    if "gst_documents" not in existing:
        op.create_table(
            "gst_documents",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("document_number", sa.String(64), unique=True, nullable=False),
            sa.Column("document_type", sa.String(64), nullable=False),
            sa.Column("financial_year", sa.String(16), nullable=False),
            sa.Column("booking_id", sa.Integer, sa.ForeignKey("bookings.id"), nullable=False),
            sa.Column("is_immutable", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("s3_pdf_key", sa.String(512), nullable=False),
        )
    if "message_delivery_logs" not in existing:
        op.create_table(
            "message_delivery_logs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("customer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("channel", sa.String(32), nullable=False),
            sa.Column("template_name", sa.String(128), nullable=False),
            sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
            sa.Column("status", sa.String(64), nullable=False),
            sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for tbl in ["message_delivery_logs", "gst_documents", "led_slot_bookings", "led_screen_configs", "hsn_sac_mappings", "gst_company_config"]:
        op.drop_table(tbl)
