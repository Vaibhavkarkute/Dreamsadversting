# Production Security Checklist

- [x] **Password Hashing**: PBKDF2-HMAC-SHA256 (120,000 iterations) / Bcrypt with per-user cryptographic salt.
- [x] **JWT Strategy**: Short-lived Access Tokens (30 min) + Refresh Tokens (7 days) with separate signing keys and `jti` claims.
- [x] **Role-Based Access Control (RBAC)**: Enforced server-side across `admin`, `sales_employee`, `finance_employee`, `inventory_manager`, `vendor`, and `customer`.
- [x] **Tenant Data Isolation**: Customers and vendors can query only their own bookings, quotations, and payouts.
- [x] **Vendor Verification Gate**: Unverified vendors and `Pending Verification` assets cannot appear as bookable on the public marketplace.
- [x] **Authoritative Backend Pricing**: Frontend totals are never trusted; all display, installation, printing, commission, and 18% GST figures are computed on the backend.
- [x] **Razorpay Signature & Webhook Verification**: Server-side HMAC-SHA256 verification and idempotency keys block replay/duplicate payment processing.
- [x] **Upload Hardening**: Extension allowlist (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`), 10 MB size ceiling, and presigned S3 uploads.
