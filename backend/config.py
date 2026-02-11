from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Sports Intelligence Platform"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./sports_intel.db"

    # Betting Configuration
    BANKROLL: float = 2000.0  # Initial bankroll for ROI calculation

    CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            # allow comma-separated list in env
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()