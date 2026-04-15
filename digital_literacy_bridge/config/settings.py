"""Configuration settings for Digital Literacy Bridge."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DLBSettings(BaseSettings):
    """Digital Literacy Bridge settings loaded from environment variables."""

    # Database configuration
    dlb_database_url: str = Field(
        default="sqlite+aiosqlite:///./dlb.db",
        description="Database connection URL (async SQLite by default)",
    )
    dlb_echo_sql: bool = Field(
        default=False,
        description="Echo SQL statements to stdout for debugging",
    )

    # Application settings
    dlb_secret_key: str = Field(
        default="change-in-production",
        description="Secret key for session/cookie signing (use JWT if needed)",
    )
    dlb_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    dlb_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token expiration time in minutes",
    )

    # Content directories
    dlb_content_dir: str = Field(
        default="content/courses",
        description="Directory containing course YAML files",
    )
    dlb_i18n_dir: str = Field(
        default="content/i18n",
        description="Directory containing translation JSON files",
    )

    # CORS configuration
    dlb_allow_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins",
    )

    @field_validator("dlb_allow_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> list[str]:
        """Parse comma-separated origins string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="DLB_",
    )


@lru_cache
def get_dlb_settings() -> DLBSettings:
    """Return cached settings instance (singleton)."""
    return DLBSettings()
