from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "soundprint-api"
    cors_origins: list[str] = ["http://localhost:3000"]
    market: str = "US"
    database_url: str = "sqlite:///./soundprint.db"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    # Temporary in-memory cache for M0; Postgres lands in M1
    cache_ttl_seconds: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()
