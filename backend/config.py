"""
Application configuration module.
Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration for the AI Revenue Recovery system."""

    # App
    APP_NAME: str = "AI Revenue Recovery System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./revenue_recovery.db")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "revenue_recovery.db")

    # Google Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Retry Engine Settings
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))
    MIN_RETRY_INTERVAL_MINUTES: int = int(os.getenv("MIN_RETRY_INTERVAL_MINUTES", "30"))
    HIGH_CONFIDENCE_THRESHOLD: float = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.7"))
    MEDIUM_CONFIDENCE_THRESHOLD: float = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.4"))

    # ML Model
    MODEL_PATH: str = os.getenv("MODEL_PATH", "backend/ml/retry_model.pkl")
    FEATURE_COLUMNS_PATH: str = os.getenv("FEATURE_COLUMNS_PATH", "backend/ml/feature_columns.pkl")


settings = Settings()
