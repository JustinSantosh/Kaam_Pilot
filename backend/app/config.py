from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KP_", env_file=".env", extra="ignore")

    llm_model: str = ""
    business_state: str = "CG"
    storage_dir: Path = Path("storage")
    followup_hours: float = 48.0
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
