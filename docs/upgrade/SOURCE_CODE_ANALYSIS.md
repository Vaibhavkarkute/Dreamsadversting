# Source Code Analysis — DreamsAdverstings (Source A Baseline)

## 1. Directory & Architecture Overview
- **Frontend (`frontend/`)**: Next.js 14 App Router + TypeScript + Tailwind CSS + Framer Motion + Recharts + Leaflet/ArcGIS interactive Pune map (`frontend/public/interactive-marketplace.html`), covering 11 public pages, Customer Portal, Vendor Portal, and 22-module Admin Portal.
- **Backend (`backend/`)**: Python FastAPI domain kernel (`app/main.py`), PBKDF2-SHA256 + JWT (`app/core/security.py`), SQLAlchemy 2.0 34-table schema (`app/models/entities.py`), Alembic migration `001_initial_schema.py`, pricing engine (`app/services/pricing_engine.py`), booking engine (`app/services/booking_engine.py`), Razorpay test verifier (`app/services/payment_service.py`), and grounded AI Media Planner (`app/services/ai_planner.py`).
- **Database Seed (`backend/app/seed_data.json`)**: 156 real Pune inventory rows parsed from `Marquis_Pune_Inventory__List-_03.10.2026.xlsx` (150 static hoardings + 6 DOOH LED slots).
- **Infrastructure (`infrastructure/`)**: Dockerfiles, `docker-compose.yml`, Terraform AWS S3/ECS definitions, GitHub Actions CI/CD.

## 2. Strengths Identified in Source A
1. Clean separation of concerns across `core/`, `models/`, `services/`, `tests/`, and `migrations/`.
2. Strict vendor verification gate preventing unapproved inventory from appearing as bookable.
3. Authoritative server-side pricing calculations and Razorpay HMAC-SHA256 signature verification.
4. Full 156-unit Pune dataset with exact GPS coordinates, dimensions, and rates.

## 3. Gaps & Security Findings to Upgrade
1. **Owner vs Admin Isolation**: Source A allows multiple `admin` users without a single-master-owner invariant or granular 11-role staff permission boundaries.
2. **LED Slot Capacity**: Source A treats LED screens similarly to whole-asset holds instead of managing operating hours, loop duration, plays/day, and partial slot capacity.
3. **Indian GST & 8 Sequential Documents**: Source A computes basic 18% GST and 2 printable views, but lacks Maharashtra GSTIN/State Code (`27`) Place-of-Supply logic (CGST+SGST vs IGST), HSN/SAC mapping, discounts, atomic FY invoice sequencing, Credit/Debit Notes, Advance Receipt Vouchers, and immutable issued-invoice locking.
4. **Partial Payments & Reconciliation**: `ENABLE_PARTIAL_PAYMENTS` was disabled by default; needs multi-installment tracking, outstanding balances, and failed-payment receipt blocking.
5. **Meta WhatsApp Cloud API & AWS SES Automation**: Needs webhook signature verification (`X-Hub-Signature-256`), approved templates, opt-out consent management, retry queue, and non-destructive failure handling.
