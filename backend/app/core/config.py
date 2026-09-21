from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://railboard:railboard@postgres:5432/railboard"
    redis_url: str = "redis://redis:6379/0"

    db_api_client_id: str = ""
    db_api_key: str = ""
    db_api_base_url: str = "https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2"

    stations_cache_ttl_seconds: int = 300

    # Public MOTIS instance, routes over static GTFS data -- no dependency on
    # DB's live backend, unlike the two approaches that didn't work out (see
    # app/adapters/motis.py for why).
    motis_base_url: str = "https://api.transitous.org"
    journeys_cache_ttl_seconds: int = 60

    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    seat_hold_minutes: int = 10

    rate_limit_window_seconds: int = 60
    rate_limit_auth_per_minute: int = 10
    rate_limit_search_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
