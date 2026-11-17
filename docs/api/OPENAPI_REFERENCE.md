# DreamsAdverstings REST API Reference (`/api/v1`)

## Authentication & RBAC
- `POST /api/v1/auth/register` — Register Customer or Vendor account
- `POST /api/v1/auth/login` — Issue JWT Access (30m) & Refresh (7d) tokens
- `POST /api/v1/auth/refresh` — Rotate refresh token
- `POST /api/v1/auth/forgot-password` & `POST /api/v1/auth/reset-password`

## Public & Marketplace Inventory
- `GET /api/v1/inventory` — Filter approved media assets by `city`, `area`, `format_code`, `min_price`, `max_price`, `is_immediate`, `is_digital`
- `GET /api/v1/inventory/{asset_code}` — Detailed asset specification, GPS coordinates, and availability calendar
- `POST /api/v1/ai-planner/recommend` — Grounded AI shortlist generator using approved database inventory

## Campaigns, Quotations & Transactional Bookings
- `POST /api/v1/campaigns` — Create campaign brief & shortlist
- `POST /api/v1/quotations/calculate` — Server-side authoritative pricing & 18% GST calculation
- `POST /api/v1/quotations/{id}/accept` — Accept quotation, recheck availability, and place 15-minute transactional booking hold
- `POST /api/v1/payments/razorpay/order` — Create Razorpay test order
- `POST /api/v1/payments/razorpay/verify` — Server-side HMAC-SHA256 signature verification & invoice generation
- `POST /api/v1/webhooks/razorpay` — Idempotent webhook event handler
