"""Application configuration settings."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Sports Intelligence Platform"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://sbd:sbddb@localhost:5432/sports_intel"
    
    # Betting Configuration
    BANKROLL: float = 2000.0  # Initial bankroll for ROI calculation
    
    # CORS origins as list of strings (comma-separated in .env)
    CORS_ORIGINS: list[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse comma-separated CORS origins from environment variable."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()