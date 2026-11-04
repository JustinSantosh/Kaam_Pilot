import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KP_", env_file=".env", extra="ignore")

    llm_model: str = ""
    llm_timeout_seconds: float = 30.0
    environment: Literal["development", "production"] = "development"
    owner_password: SecretStr = SecretStr("")
    owner_session_ttl_seconds: int = 8 * 60 * 60
    owner_cookie_secure: bool = False
    business_state: str = "CG"
    storage_dir: Path = Path("storage")
    followup_hours: float = 48.0
    chat_rate_limit_per_minute: int = 30
    sqlite_busy_timeout_ms: int = 5000
    cors_origins: list[str] = ["http://localhost:3000"]

    # Printed on quotations (Phase 06). Placeholders until the owner sets them.
    business_name: str = "Your Business Name"
    business_gstin: str = ""
    business_address: str = ""
    business_phone: str = ""
    quote_validity_days: int = 15
    advance_percent: int = 50

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> "Settings":
        if self.llm_timeout_seconds <= 0:
            raise ValueError("KP_LLM_TIMEOUT_SECONDS must be greater than zero")
        if self.owner_session_ttl_seconds <= 0:
            raise ValueError("KP_OWNER_SESSION_TTL_SECONDS must be greater than zero")
        if self.sqlite_busy_timeout_ms <= 0:
            raise ValueError("KP_SQLITE_BUSY_TIMEOUT_MS must be greater than zero")
        if self.chat_rate_limit_per_minute <= 0:
            raise ValueError("KP_CHAT_RATE_LIMIT_PER_MINUTE must be greater than zero")
        if self.environment == "production":
            password = self.owner_password.get_secret_value()
            if len(password) < 16:
                raise ValueError("KP_OWNER_PASSWORD must be at least 16 characters in production")
            if "*" in self.cors_origins:
                raise ValueError("KP_CORS_ORIGINS cannot contain '*' in production")
            if not self.owner_cookie_secure:
                raise ValueError("KP_OWNER_COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    # Provider SDKs read their keys (GOOGLE_API_KEY, OPENAI_API_KEY…) from os.environ, which
    # pydantic-settings doesn't populate. Real environment variables still win over .env.
    # KP_* stay out: Settings reads them from .env itself, and in os.environ they would also reach
    # Settings(_env_file=None), which is how tests opt out of .env.
    for key, value in dotenv_values(ENV_FILE).items():
        if value is not None and not key.startswith("KP_"):
            os.environ.setdefault(key, value)
    return Settings()
