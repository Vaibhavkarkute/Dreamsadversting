import datetime
from typing import Dict, List, Optional
from app.core.security import STAFF_ROLES, check_permission, hash_password


class StaffManagementService:
    """
    Manages the single Master Owner account and 11-role staff hierarchy.
    - Enforces SINGLE_OWNER invariant: cannot create more than one 'owner' account.
    - Only the Owner may add employees, change roles/permissions, disable staff access,
      or view staff activity & performance metrics.
    """

    def __init__(self):
        self.owner_id: Optional[str] = None
        self.staff: Dict[str, Dict] = {}
        self.activity_logs: List[Dict] = []

    def bootstrap_master_owner(self, email: str, password: str, full_name: str) -> Dict:
        if self.owner_id is not None:
            raise ValueError("SINGLE_OWNER_VIOLATION: Master Owner account already exists.")
        owner_id = "STAFF-OWNER-001"
        self.owner_id = owner_id
        record = {
            "id": owner_id,
            "email": email.strip().lower(),
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": "owner",
            "department": "Executive",
            "custom_permissions": [],
            "assigned_campaigns": [],
            "assigned_customers": [],
            "is_active": True,
            "deals_closed": 0,
            "revenue_managed_inr": 0.0,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.staff[owner_id] = record
        self._log(owner_id, "owner.bootstrap", "Master Owner initialized")
        return {k: v for k, v in record.items() if k != "password_hash"}

    def add_employee(
        self,
        actor: Dict,
        email: str,
        password: str,
        full_name: str,
        role: str,
        department: str,
        custom_permissions: Optional[List[str]] = None,
    ) -> Dict:
        if actor.get("role") != "owner":
            raise PermissionError("OWNER_ONLY: Only the Master Owner can add staff employees.")
        if role == "owner":
            raise ValueError("SINGLE_OWNER_VIOLATION: Cannot create a second Owner account.")
        if role not in STAFF_ROLES:
            raise ValueError(f"Invalid staff role '{role}'. Must be one of {STAFF_ROLES}.")
        email_clean = email.strip().lower()
        if any(s["email"] == email_clean for s in self.staff.values()):
            raise ValueError(f"Staff email {email_clean} already exists.")

        emp_id = f"STAFF-{len(self.staff) + 1:03d}"
        record = {
            "id": emp_id,
            "email": email_clean,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "department": department,
            "custom_permissions": custom_permissions or [],
            "assigned_campaigns": [],
            "assigned_customers": [],
            "is_active": True,
            "deals_closed": 0,
            "revenue_managed_inr": 0.0,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.staff[emp_id] = record
        self._log(actor["id"], "staff.create", f"Created {emp_id} ({role}) in {department}")
        return {k: v for k, v in record.items() if k != "password_hash"}

    def assign_work(
        self,
        actor: Dict,
        emp_id: str,
        campaign_id: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Dict:
        if actor.get("role") != "owner" and not check_permission(actor.get("role", ""), "manage:campaigns"):
            raise PermissionError("Unauthorized to assign staff workloads.")
        if emp_id not in self.staff:
            raise KeyError(f"Employee {emp_id} not found.")
        emp = self.staff[emp_id]
        if campaign_id and campaign_id not in emp["assigned_campaigns"]:
            emp["assigned_campaigns"].append(campaign_id)
        if customer_id and customer_id not in emp["assigned_customers"]:
            emp["assigned_customers"].append(customer_id)
        self._log(actor["id"], "staff.assign", f"Assigned {campaign_id or customer_id} to {emp_id}")
        return emp

    def set_access_status(self, actor: Dict, emp_id: str, is_active: bool) -> Dict:
        if actor.get("role") != "owner":
            raise PermissionError("OWNER_ONLY: Only the Master Owner can enable/disable staff access.")
        if emp_id == self.owner_id:
            raise ValueError("Cannot disable the Master Owner account.")
        if emp_id not in self.staff:
            raise KeyError(f"Employee {emp_id} not found.")
        self.staff[emp_id]["is_active"] = is_active
        self._log(actor["id"], "staff.access_toggle", f"Set {emp_id} is_active={is_active}")
        return self.staff[emp_id]

    def _log(self, actor_id: str, action: str, detail: str):
        self.activity_logs.append(
            {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "actor_id": actor_id,
                "action": action,
                "detail": detail,
            }
        )
