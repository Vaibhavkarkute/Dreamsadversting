# Production Upgrade Execution Plan (Phases 1–12)

1. **Phases 1–2**: Complete Source A analysis, gap matrix, backup script (`scripts/backup_db.sh`), and Alembic migration `002_production_upgrade.py`.
2. **Phases 3–4**: Upgrade `app/core/security.py` with Single-Owner enforcement and 11-role Staff RBAC + `app/services/staff_service.py`.
3. **Phase 5**: Upgrade `app/services/booking_engine.py` with maintenance blocks and `LEDSlotCapacityEngine` + calendar schedule generator.
4. **Phases 6–7**: Implement `app/services/gst_billing_service.py` (8 atomic GST documents, HSN/SAC, CGST/SGST/IGST) and upgrade `app/services/payment_service.py` (partial payments, failed payment guards, reconciliation).
5. **Phase 8**: Implement `app/services/messaging_service.py` (Meta WhatsApp Cloud API + AWS SES with consent, opt-out, webhook verification, and safe retry).
6. **Phases 9–12**: Integrate all upgraded services into `app/main.py`, upgrade the interactive Marketplace Web App (`dreamsadverstings_marketplace.html`), run full Pytest + `check_web_app.py` verification, and produce `COMPLETION_REPORT.md` + `dreamsadverstings_fullstack_source.zip`.
