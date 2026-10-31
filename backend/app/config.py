from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KP_", env_file=".env", extra="ignore")

    llm_model: str = ""
    business_state: str = "CG"
    storage_dir: Path = Path("storage")
    followup_hours: float = 48.0
    cors_origins: list[str] = ["http://localhost:3000"]

    # Printed on quotations (Phase 06). Placeholders until the owner sets them.
    business_name: str = "Your Business Name"
    business_gstin: str = ""
    business_address: str = ""
    business_phone: str = ""
    quote_validity_days: int = 15
    advance_percent: int = 50


@lru_cache
def get_settings() -> Settings:
    # Provider SDKs read their keys (GOOGLE_API_KEY, OPENAI_API_KEY…) from os.environ, which
    # pydantic-settings doesn't populate. Real environment variables still win over .env.
    load_dotenv(ENV_FILE, override=False)
    return Settings()
