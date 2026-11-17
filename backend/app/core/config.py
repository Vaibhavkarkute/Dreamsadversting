import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "DreamsAdverstings")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-secret-key-change-in-prod-987654321")
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET_KEY", "dev-only-refresh-secret-key-change-in-prod")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dreamsadverstings_test.db")
    RAZORPAY_MODE: str = os.getenv("RAZORPAY_MODE", "test")
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_dreamsadverstings")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_key_998877")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_dreamsadverstings_test")
    ENABLE_PARTIAL_PAYMENTS: bool = os.getenv("ENABLE_PARTIAL_PAYMENTS", "false").lower() == "true"
    BOOKING_HOLD_MINUTES: int = int(os.getenv("BOOKING_HOLD_MINUTES", "15"))
    PLATFORM_COMMISSION_RATE: float = float(os.getenv("PLATFORM_COMMISSION_RATE", "0.08"))
    GST_TAX_RATE: float = float(os.getenv("GST_TAX_RATE", "0.18"))
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp", ".pdf"])
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


settings = Settings()
