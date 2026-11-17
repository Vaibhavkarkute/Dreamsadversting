import base64
import datetime
import hashlib
import hmac
import json
import secrets
from typing import Dict, List, Optional
from app.core.config import settings

STAFF_ROLES = [
    "owner",
    "sales_manager",
    "sales_executive",
    "finance_manager",
    "accounts_executive",
    "inventory_manager",
    "led_operations_manager",
    "vendor_manager",
    "campaign_manager",
    "installation_staff",
    "customer_support",
]

ALL_ROLES = STAFF_ROLES + ["vendor", "customer"]

# Strict Least-Privilege Role-Based Access Control Matrix
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    # Single Master Owner — Exclusive access to company-wide revenue, GST config, company settings, staff permissions, owner audit logs
    "owner": [
        "owner:dashboard",
        "owner:gst_config",
        "owner:company_settings",
        "owner:staff_manage",
        "owner:staff_permissions",
        "owner:revenue_all",
        "owner:financial_reports",
        "owner:audit_logs",
        "manage:users",
        "manage:vendors",
        "verify:vendors",
        "manage:inventory",
        "manage:locations",
        "manage:services",
        "manage:pricing",
        "manage:enquiries",
        "manage:quotations",
        "manage:campaigns",
        "manage:bookings",
        "manage:payments",
        "manage:invoices",
        "manage:refunds",
        "verify:execution",
        "manage:led_slots",
        "manage:messaging",
    ],
    "sales_manager": [
        "manage:enquiries",
        "manage:quotations",
        "manage:campaigns",
        "view:inventory",
        "view:customers",
        "view:bookings",
    ],
    "sales_executive": [
        "manage:enquiries",
        "manage:quotations",
        "view:inventory",
        "view:customers",
    ],
    # Finance team can manage payments, invoices & refunds, but MUST NOT change company GST configuration
    "finance_manager": [
        "manage:payments",
        "manage:invoices",
        "manage:refunds",
        "view:bookings",
        "view:quotations",
        "view:financial_summary",
    ],
    "accounts_executive": [
        "manage:payments",
        "manage:invoices",
        "view:bookings",
    ],
    # Inventory & LED managers CANNOT change payment records
    "inventory_manager": [
        "manage:inventory",
        "manage:locations",
        "manage:maintenance",
        "verify:vendors",
    ],
    "led_operations_manager": [
        "manage:led_slots",
        "manage:inventory",
        "view:campaigns",
    ],
    "vendor_manager": [
        "manage:vendors",
        "verify:vendors",
        "view:inventory",
    ],
    "campaign_manager": [
        "manage:campaigns",
        "verify:execution",
        "view:bookings",
        "view:inventory",
    ],
    "installation_staff": [
        "view:campaigns",
        "upload:proof_of_display",
    ],
    "customer_support": [
        "view:customers",
        "view:bookings",
        "manage:support_tickets",
    ],
    "admin": [
        "manage:settings", "manage:inventory", "verify:vendors", "manage:locations",
        "manage:quotations", "manage:payments", "manage:campaigns", "verify:execution",
    ],
    "sales_employee": ["manage:enquiries", "manage:quotations", "manage:campaigns", "view:inventory"],
    "finance_employee": ["manage:payments", "manage:invoices", "view:bookings"],
    "vendor": [
        "vendor:profile",
        "vendor:inventory:create",
        "vendor:inventory:own",
        "vendor:bookings:own",
        "vendor:proof:upload",
    ],
    "customer": [
        "customer:profile",
        "customer:campaigns:own",
        "customer:enquiries:own",
        "customer:quotations:own",
        "customer:bookings:own",
        "customer:payments:own",
        "customer:support:own",
    ],
}


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt_val = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_val.encode("utf-8"), 120000)
    return f"pbkdf2_sha256$120000${salt_val}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        _, iterations, salt_val, stored_hex = hashed_password.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt_val.encode("utf-8"), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), stored_hex)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt_token(
    subject: str,
    role: str,
    token_type: str = "access",
    expires_delta: Optional[datetime.timedelta] = None,
) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta is None:
        expires_delta = (
            datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            if token_type == "access"
            else datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    exp = now + expires_delta
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "permissions": ROLE_PERMISSIONS.get(role, []),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(8),
    }
    secret = settings.JWT_SECRET_KEY if token_type == "access" else settings.JWT_REFRESH_SECRET_KEY
    unsigned = f"{_b64url_encode(json.dumps(header).encode())}.{_b64url_encode(json.dumps(payload).encode())}"
    sig = hmac.new(secret.encode("utf-8"), unsigned.encode("utf-8"), hashlib.sha256).digest()
    return f"{unsigned}.{_b64url_encode(sig)}"


def decode_jwt_token(token: str, expected_type: str = "access") -> Dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token structure")
    secret = settings.JWT_SECRET_KEY if expected_type == "access" else settings.JWT_REFRESH_SECRET_KEY
    unsigned = f"{parts[0]}.{parts[1]}"
    expected_sig = hmac.new(secret.encode("utf-8"), unsigned.encode("utf-8"), hashlib.sha256).digest()
    actual_sig = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise PermissionError("Invalid token signature")
    payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    if payload.get("type") != expected_type:
        raise PermissionError(f"Expected {expected_type} token")
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if payload.get("exp", 0) < now_ts:
        raise PermissionError("Token has expired")
    return payload


def check_permission(user_role: str, required_permission: str, custom_permissions: Optional[List[str]] = None) -> bool:
    if user_role == "owner":
        return True
    perms = set(ROLE_PERMISSIONS.get(user_role, []))
    if custom_permissions:
        perms.update(custom_permissions)
    return required_permission in perms
