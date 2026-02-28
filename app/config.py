from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "GTD API"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./gtd.db"

    # API Key Management
    # If set, this key is required to create new API keys
    admin_key: str | None = None

    # Donor DB integration
    donor_db_url: str = ""
    donor_db_api_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
