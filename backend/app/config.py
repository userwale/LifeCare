"""
app/config.py – Application settings via Pydantic BaseSettings.
All values can be overridden with environment variables or a .env file.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "LifeCare API"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "change-me"

    # ── Security & JWT ───────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    otp_expire_minutes: int = 5

    # ── SMTP Mail Configuration ──────────────────────────────────────────────
    smtp_host: str = "smtp.mailtrap.io"
    smtp_port: int = 2525
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@lifecare.local"

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./lifecare.db"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL used by Alembic migrations."""
        url = self.database_url
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite")
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        return url

    # ── Admin seed account ────────────────────────────────────────────────────
    admin_username: str = "admin"
    admin_email: str = "admin@lifecare.local"
    admin_password: str = "Admin@12345"   # override in .env!

    # ── AI Model Paths ───────────────────────────────────────────────────────
    ai_yolo_model_path: str = "../Model_IA/best.pt"
    ai_posture_model_path: str = "../Model_IA/rf_model.pkl"
    ai_disease_model_path: str = "../Model_IA/disease_rf_model.pkl"

    @property
    def yolo_model_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.ai_yolo_model_path

    @property
    def posture_model_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.ai_posture_model_path

    @property
    def disease_model_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.ai_disease_model_path


settings = Settings()
