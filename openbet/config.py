"""Configuration management for Openbet application."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Kalshi API Configuration
    kalshi_api_key: str
    kalshi_api_secret: str
    kalshi_base_url: str = "https://api.kalshi.com/v2"

    # LLM Provider API Keys
    anthropic_api_key: str
    openai_api_key: str
    xai_api_key: str
    google_api_key: str

    # Database Configuration
    database_path: str = "data/openbet.db"

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "openbet.log"

    # LLM Model Configuration
    default_llm_model_claude: str = "claude-3-5-sonnet-20241022"
    default_llm_model_openai: str = "gpt-4-turbo-preview"
    default_llm_model_grok: str = "grok-2-latest"
    default_llm_model_gemini: str = "gemini-1.5-pro"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_path_obj(self) -> Path:
        """Get database path as Path object."""
        return Path(self.database_path)

    def ensure_database_dir(self) -> None:
        """Ensure database directory exists."""
        self.database_path_obj.parent.mkdir(parents=True, exist_ok=True)


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function
settings = get_settings()
