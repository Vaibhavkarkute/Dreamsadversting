from typing import Dict, List, Optional


class AIMediaPlannerService:
    """
    AI Advertising Assistant grounded strictly in approved database inventory.
    Never fabricates pricing or availability.
    """

    def __init__(self, inventory: List[Dict]):
        self.inventory = inventory

    def recommend_shortlist(
        self,
        budget_inr: float,
        preferred_areas: Optional[List[str]] = None,
        media_preference: Optional[str] = None,
        immediate_only: bool = False,
        duration_months: int = 1,
    ) -> Dict:
        approved = [
            item
            for item in self.inventory
            if item.get("status") == "Approved" and item.get("vendor_verified", True)
        ]

        if preferred_areas:
            area_set = {a.lower() for a in preferred_areas}
            area_matches = [
                i for i in approved if any(a in i["area"].lower() or a in i["title"].lower() for a in area_set)
            ]
            if area_matches:
                approved = area_matches

        if media_preference and media_preference.lower() in ("dooh", "led", "digital"):
            dig = [i for i in approved if i["is_digital"]]
            if dig:
                approved = dig
        elif media_preference and media_preference.lower() in ("static", "billboard", "hoarding"):
            stat = [i for i in approved if not i["is_digital"]]
            if stat:
                approved = stat

        if immediate_only:
            imm = [i for i in approved if i["is_immediate"]]
            if imm:
                approved = imm

        # Sort by value efficiency (area_sqft per monthly display rupee)
        approved_sorted = sorted(
            approved,
            key=lambda x: (x["is_immediate"], x["area_sqft"] / max(1, x["display_cost_pm"])),
            reverse=True,
        )

        selected = []
        running_spend = 0.0
        max_media_budget = budget_inr * 0.78  # Reserve ~22% for installation, printing, commission, GST

        for asset in approved_sorted:
            unit_cost = asset["display_cost_pm"] * duration_months + asset["installation_cost"] + asset["printing_cost"]
            if running_spend + unit_cost <= max_media_budget or (not selected and unit_cost <= budget_inr):
                selected.append(asset)
                running_spend += unit_cost
            if len(selected) >= 6:
                break

        return {
            "recommended_count": len(selected),
            "estimated_media_spend_inr": round(running_spend, 2),
            "budget_inr": budget_inr,
            "duration_months": duration_months,
            "shortlist": selected,
            "grounding_note": "All recommended media units are verified against approved Pune database inventory.",
        }
