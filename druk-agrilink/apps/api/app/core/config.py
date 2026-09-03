"""Application settings loaded from the environment (12-factor)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRUK_", env_file=".env", extra="ignore")

    app_name: str = "DrukAgriLink API"
    environment: str = "development"  # development | test | staging | production
    debug: bool = False

    database_url: str = "postgresql+psycopg://druk:druk_dev_only@localhost:5432/drukagrilink"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    cors_origins: str = "http://localhost:3000"

    redis_url: str = ""  # empty → in-process fallbacks (rate limit)

    # business parameters (admin-configurable defaults)
    platform_fee_percent: str = "2.0"
    delivery_discrepancy_tolerance_percent: str = "2.0"
    road_circuity_factor: str = "1.6"  # haversine → mountain-road approximation
    average_speed_kmh: str = "35"
    transport_cost_per_km_nu: str = "45"

    upload_max_bytes: int = 5 * 1024 * 1024
    upload_dir: str = "var/uploads"

    seed_demo_accounts: bool = True  # must be False in production

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.jwt_secret == "dev-only-change-me":
        raise RuntimeError("DRUK_JWT_SECRET must be set in production")
    if settings.is_production and settings.seed_demo_accounts:
        raise RuntimeError("Demo accounts must not be enabled in production")
    return settings
