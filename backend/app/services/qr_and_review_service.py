import datetime
import urllib.parse
from typing import Dict, List, Optional


class QRBannerBookingService:
    """
    Generates deterministic QR code payloads for every billboard/hoarding/LED screen
    and processes instant Scan-QR-to-Book-Banner reservations.
    """

    def __init__(self, base_url: str = "https://dreamsadverstings.in"):
        self.base_url = base_url.rstrip("/")
        self.scan_logs: List[Dict] = []

    def generate_asset_qr_metadata(self, asset: Dict) -> Dict:
        asset_id = asset["id"]
        qr_token = f"DA-QR-{asset_id}"
        deep_link = f"{self.base_url}/qr-book?asset={urllib.parse.quote(asset_id)}&qr={urllib.parse.quote(qr_token)}"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={asset['lat']},{asset['lng']}"
        return {
            "asset_id": asset_id,
            "qr_token": qr_token,
            "deep_link": deep_link,
            "google_maps_pin_url": maps_url,
            "title": asset["title"],
            "area": asset["area"],
            "format_code": asset["format_code"],
            "dimensions_ft": f"{asset['width_ft']}x{asset['height_ft']}",
            "display_cost_pm": asset["display_cost_pm"],
        }

    def resolve_scanned_qr(self, qr_code_or_asset_id: str, inventory: List[Dict], scanner_ip: str = "0.0.0.0") -> Dict:
        raw = qr_code_or_asset_id.strip().upper()
        asset_id = raw.replace("DA-QR-", "") if raw.startswith("DA-QR-") else raw
        for item in inventory:
            if item["id"].upper() == asset_id:
                if item.get("status") != "Approved" or not item.get("vendor_verified", False):
                    raise PermissionError(f"QR_ASSET_NOT_APPROVED: Asset {asset_id} is not approved for public booking.")
                scan_event = {
                    "scan_id": f"SCAN-{len(self.scan_logs) + 1:04d}",
                    "asset_id": item["id"],
                    "qr_token": f"DA-QR-{item['id']}",
                    "scanner_ip": scanner_ip,
                    "scanned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                self.scan_logs.append(scan_event)
                return {
                    "scan_event": scan_event,
                    "asset": item,
                    "qr_metadata": self.generate_asset_qr_metadata(item),
                }
        raise KeyError(f"QR_ASSET_NOT_FOUND: No hoarding matches '{qr_code_or_asset_id}'.")


class CompletedOrderReviewService:
    """
    Manages verified customer reviews and star ratings for COMPLETED orders only,
    synchronizing website reviews with direct Google Maps review deep-links.
    """

    def __init__(self):
        self.reviews: Dict[str, Dict] = {}
        self.booking_review_index: Dict[str, str] = {}

    def submit_completed_order_review(
        self,
        booking: Dict,
        asset: Dict,
        customer_id: str,
        customer_name: str,
        rating: int,
        visibility_rating: int,
        mounting_quality_rating: int,
        title: str,
        comment: str,
        post_to_google_maps: bool = True,
    ) -> Dict:
        if booking["customer_id"] != customer_id:
            raise PermissionError("REVIEW_TENANT_VIOLATION: Customers may only review their own orders.")
        if booking["status"] != "Completed":
            raise ValueError(
                f"ORDER_NOT_COMPLETED_FOR_REVIEW: Booking {booking['id']} has status '{booking['status']}'. "
                "Only 'Completed' orders can be reviewed."
            )
        if (booking.get("booking_id") or booking.get("id")) in self.booking_review_index:
            raise ValueError(f"DUPLICATE_BOOKING_REVIEW: Booking {booking['id']} has already been reviewed.")
        if not (1 <= int(rating) <= 5):
            raise ValueError("INVALID_RATING: Rating must be between 1 and 5 stars.")

        review_id = f"REV-2026-{len(self.reviews) + 1:03d}"
        query_str = urllib.parse.quote(f"DreamsAdverstings {asset['title']} {asset['area']} Pune")
        google_maps_review_url = f"https://www.google.com/maps/search/?api=1&query={query_str}"
        google_maps_coords_url = f"https://www.google.com/maps/search/?api=1&query={asset['lat']},{asset['lng']}"

        record = {
            "id": review_id,
            "booking_id": (booking.get("booking_id") or booking.get("id")),
            "asset_id": asset["id"],
            "asset_title": asset["title"],
            "area": asset["area"],
            "customer_id": customer_id,
            "customer_name": customer_name,
            "rating": int(rating),
            "visibility_rating": max(1, min(5, int(visibility_rating))),
            "mounting_quality_rating": max(1, min(5, int(mounting_quality_rating))),
            "title": title.strip(),
            "comment": comment.strip(),
            "verified_completed_order": True,
            "published_on_website": True,
            "google_maps_sync_requested": bool(post_to_google_maps),
            "google_maps_review_url": google_maps_review_url,
            "google_maps_coords_url": google_maps_coords_url,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.reviews[review_id] = record
        self.booking_review_index[(booking.get("booking_id") or booking.get("id"))] = review_id
        return record

    def get_public_reviews_summary(self) -> Dict:
        items = list(self.reviews.values())
        count = len(items)
        avg = round(sum(r["rating"] for r in items) / count, 2) if count else 0.0
        vis_avg = round(sum(r["visibility_rating"] for r in items) / count, 2) if count else 0.0
        mnt_avg = round(sum(r["mounting_quality_rating"] for r in items) / count, 2) if count else 0.0
        return {
            "total_verified_reviews": count,
            "average_rating": avg,
            "average_visibility_rating": vis_avg,
            "average_mounting_quality_rating": mnt_avg,
            "google_maps_hq_review_url": "https://www.google.com/maps/search/?api=1&query=DreamsAdverstings+Pune+Maharashtra",
            "reviews": sorted(items, key=lambda x: x["created_at"], reverse=True),
        }
