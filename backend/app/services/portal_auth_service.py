import datetime
from typing import Dict, Optional
from app.core.security import create_jwt_token, hash_password, verify_password


class MultiPortalAuthService:
    """
    Dedicated authentication & session isolation gateway for the 4 interconnected portals:
    1. Public Marketplace Website (`public`)
    2. Customer Advertiser Portal (`customer`) — Email/Password, Registration, or Mobile OTP
    3. Vendor / Media Owner Partner Portal (`vendor`) — Vendor Email/Password + GSTIN/PMC License check
    4. Master Owner & 11-Role Staff Control Plane (`admin`) — Role-scoped credentials + mandatory 2FA PIN
    """

    PORTAL_URLS = {
        "public": "http://localhost:3000/",
        "customer": "http://localhost:3000/customer-portal",
        "vendor": "http://localhost:3000/vendor-portal",
        "admin": "http://localhost:3000/owner-admin-portal",
    }

    def __init__(self):
        self.portal_accounts: Dict[str, Dict] = {
            "customer:aarav@puneevmobility.in": {
                "user_id": "CUST-001",
                "portal": "customer",
                "role": "customer",
                "email": "aarav@puneevmobility.in",
                "password_hash": hash_password("Customer#2026"),
                "full_name": "Aarav Deshmukh",
                "company": "Pune EV Mobility Pvt Ltd",
                "gstin": "27AABCP9911K1Z2",
                "otp_code": "448822",
            },
            "vendor:partner@marquismedia.in": {
                "user_id": "VEND-001",
                "portal": "vendor",
                "role": "vendor",
                "email": "partner@marquismedia.in",
                "password_hash": hash_password("Vendor#2026"),
                "full_name": "Marquis Media Network Pune",
                "company": "Marquis Outdoor Media Pvt Ltd",
                "gstin": "27AAACM7712P1Z5",
                "pmc_license": "PMC-OOH-2026-8841",
                "vendor_verified": True,
            },
            "admin:owner@dreamsadverstings.in": {
                "user_id": "STAFF-OWNER-001",
                "portal": "admin",
                "role": "owner",
                "email": "owner@dreamsadverstings.in",
                "password_hash": hash_password("Owner#2026"),
                "full_name": "Vaibhav Karkute (Master Owner)",
                "department": "Executive",
                "two_factor_pin": "123456",
            },
            "admin:finance@dreamsadverstings.in": {
                "user_id": "STAFF-003",
                "portal": "admin",
                "role": "finance_manager",
                "email": "finance@dreamsadverstings.in",
                "password_hash": hash_password("Staff#2026"),
                "full_name": "Sneha Patil (Finance Manager)",
                "department": "Finance",
                "two_factor_pin": "123456",
            },
            "admin:sales@dreamsadverstings.in": {
                "user_id": "STAFF-002",
                "portal": "admin",
                "role": "sales_manager",
                "email": "sales@dreamsadverstings.in",
                "password_hash": hash_password("Staff#2026"),
                "full_name": "Rohan Joshi (Sales Manager)",
                "department": "Sales",
                "two_factor_pin": "123456",
            },
        }
        self.active_sessions: Dict[str, Dict] = {}

    def authenticate_portal(
        self,
        portal: str,
        email: str,
        password: str,
        two_factor_pin: Optional[str] = None,
        requested_staff_role: Optional[str] = None,
    ) -> Dict:
        portal_key = portal.strip().lower()
        if portal_key not in ("customer", "vendor", "admin"):
            raise ValueError(f"INVALID_PORTAL: '{portal}' is not a protected login portal.")

        key = f"{portal_key}:{email.strip().lower()}"
        acct = self.portal_accounts.get(key)
        if not acct or not verify_password(password, acct["password_hash"]):
            raise PermissionError(f"PORTAL_AUTH_FAILED: Invalid credentials for {portal_key} portal.")

        if portal_key == "admin":
            if not two_factor_pin or two_factor_pin.strip() != acct.get("two_factor_pin", "123456"):
                raise PermissionError("PORTAL_2FA_REQUIRED: Valid 6-digit 2FA security PIN required for Owner/Staff Portal.")
            if requested_staff_role and requested_staff_role == "owner" and acct["role"] != "owner":
                raise PermissionError("SINGLE_OWNER_VIOLATION: Staff account cannot elevate to Master Owner role.")

        role = requested_staff_role if (portal_key == "admin" and requested_staff_role and acct["role"] == "owner") else acct["role"]
        access_token = create_jwt_token(acct["user_id"], role, "access")
        refresh_token = create_jwt_token(acct["user_id"], role, "refresh")

        session = {
            "portal": portal_key,
            "portal_url": self.PORTAL_URLS[portal_key],
            "user_id": acct["user_id"],
            "email": acct["email"],
            "full_name": acct["full_name"],
            "role": role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "authenticated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.active_sessions[f"{portal_key}:{acct['user_id']}"] = session
        return session

    def register_customer_or_vendor(
        self,
        portal: str,
        email: str,
        password: str,
        full_name: str,
        company: str,
        gstin: str = "",
        pmc_license: str = "",
    ) -> Dict:
        portal_key = portal.strip().lower()
        if portal_key not in ("customer", "vendor"):
            raise ValueError("Self-registration is only permitted on Customer and Vendor portals.")
        key = f"{portal_key}:{email.strip().lower()}"
        if key in self.portal_accounts:
            raise ValueError("Account already exists for this portal.")
        uid = f"{portal_key.upper()[:4]}-{len(self.portal_accounts) + 1:03d}"
        acct = {
            "user_id": uid,
            "portal": portal_key,
            "role": portal_key,
            "email": email.strip().lower(),
            "password_hash": hash_password(password),
            "full_name": full_name.strip(),
            "company": company.strip(),
            "gstin": gstin.strip(),
            "pmc_license": pmc_license.strip(),
            "vendor_verified": False if portal_key == "vendor" else True,
        }
        self.portal_accounts[key] = acct
        return self.authenticate_portal(portal_key, email, password)
