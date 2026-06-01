from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PrimeTrade API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/primetrade"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-this-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    secure_refresh_cookie: bool = False
    auto_create_schema: bool = True
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    rate_limit_requests_per_minute: int = 60
    cache_ttl_seconds: int = 30
    external_api_timeout_seconds: float = 3.0
    external_api_retry_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
