"""Application configuration settings."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Sports Intelligence Platform"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://sbd:sbddb@localhost:5432/sports_intel"
    REDIS_URL: str = "redis://localhost"
    
    BANKROLL: float = 2000.0
    # Plain string to avoid pydantic-settings JSON-parsing a list from env var
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list, parsed from comma-separated string."""
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        """Railway provides postgresql:// but asyncpg needs postgresql+asyncpg://."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()