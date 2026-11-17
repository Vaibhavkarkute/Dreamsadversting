"""
FastAPI HTTP Router Layer connecting DreamsAdverstings REST endpoints
to MarketplacePlatformKernel and ProductionAutomationWorker.
"""
import datetime
from typing import Dict, List, Optional
from app.core.security import check_permission, decode_jwt_token
from app.main import MarketplacePlatformKernel
from app.workers.automation_tasks import ProductionAutomationWorker

try:
    from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
    from pydantic import BaseModel

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

kernel = MarketplacePlatformKernel()
automation_worker = ProductionAutomationWorker(kernel)


def create_fastapi_app():
    if not FASTAPI_AVAILABLE:
        return None

    app = FastAPI(
        title="DreamsAdverstings OOH/DOOH Marketplace API",
        version="2.0.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )
    router = APIRouter(prefix="/api/v1")

    def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = authorization.split(" ", 1)[1]
        try:
            return decode_jwt_token(token, expected_type="access")
        except Exception as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @router.get("/health")
    def healthcheck():
        return {"status": "healthy", "inventory_count": len(kernel.inventory)}

    @router.get("/inventory")
    def list_inventory(
        area: Optional[str] = None,
        format_code: Optional[str] = None,
        max_price: Optional[float] = None,
        immediate_only: bool = False,
    ):
        items = kernel.filter_inventory(
            area=area, format_code=format_code, max_price=max_price, immediate_only=immediate_only
        )
        return {"total": len(items), "items": items}

    @router.post("/automation/run-cycle")
    def trigger_automation_cycle(user: Dict = Depends(get_current_user)):
        if user.get("role") != "owner":
            raise HTTPException(status_code=403, detail="OWNER_ONLY: Only Master Owner can trigger manual automation cycle.")
        return automation_worker.run_full_automation_cycle()

    @router.get("/owner/dashboard")
    def owner_dashboard(user: Dict = Depends(get_current_user)):
        if not check_permission(user.get("role", ""), "owner:dashboard"):
            raise HTTPException(status_code=403, detail="OWNER_ONLY access required.")
        return automation_worker.generate_daily_owner_digest()


    @router.get("/qr/{qr_token_or_asset_id}")
    def resolve_qr_asset(qr_token_or_asset_id: str):
        try:
            return kernel.qr_service.resolve_scanned_qr(qr_token_or_asset_id, kernel.inventory)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/reviews")
    def list_verified_reviews():
        return kernel.review_service.get_public_reviews_summary()


    @router.get("/map/pins")
    def get_3color_map_pins(color: Optional[str] = None, area: Optional[str] = None):
        return kernel.analytics_service.get_map_3color_summary(color_filter=color, area=area)

    @router.get("/inventory/forecast")
    def get_daily_availability_forecast():
        return kernel.analytics_service.get_daily_availability_forecast()

    @router.get("/owner/area-sales")
    def get_area_wise_sales(period: str = "month"):
        return {
            "period_summary": kernel.analytics_service.get_period_sales_metrics(period),
            "area_breakdown": kernel.analytics_service.get_area_wise_sales_and_availability(),
            "expiry_notifications": kernel.analytics_service.get_expiry_notifications(),
        }


    @app.get("/")
    def root_index():
        return {
            "service": "DreamsAdverstings OOH/DOOH Marketplace API",
            "status": "running",
            "docs_url": "/api/v1/docs",
            "health_url": "/api/v1/health",
            "inventory_count": len(kernel.inventory),
        }

    app.include_router(router)
    return app


app = create_fastapi_app()
