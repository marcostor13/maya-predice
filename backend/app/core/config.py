"""Configuración de la aplicación cargada desde variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://maya:maya@localhost:5432/maya_predice"
    cors_origins: str = "http://localhost:4200"
    env: str = "development"
    model_version: str = "dixon-coles-v1"

    # --- Ingesta de datos oficiales ---
    # Fuente primaria: openfootball (dominio público, derivada del calendario FIFA).
    data_source_url: str = (
        "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    )
    # Verificación diaria: hora UTC a la que corre el job (06:00 UTC ≈ tras
    # finalizar todos los partidos del día anterior en Norteamérica).
    sync_hour_utc: int = 6
    sync_minute_utc: int = 0
    enable_scheduler: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
