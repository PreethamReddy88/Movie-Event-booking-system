"""Application settings loaded from environment variables.

Uses pydantic-settings so every value can be overridden via .env or
real env vars in production.
"""

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    # For local dev without Postgres, set to: sqlite+aiosqlite:///./movie_booking.db
    DATABASE_URL: str = "sqlite+aiosqlite:///./movie_booking.db"
    DATABASE_URL_SYNC: str = "sqlite:///./movie_booking.db"

    # ── Redis ──
    # Set to "fake" to use an in-memory dict instead of real Redis.
    REDIS_URL: str = "fake"

    # ── JWT ──
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── App ──
    APP_NAME: str = "MovieBookingAPI"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]


settings = Settings()
