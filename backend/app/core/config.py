"""Configuración de la aplicación cargada desde variables de entorno."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Hiperparámetros del modelo CALIBRADOS (no configurables por entorno) ---
# Se fijan aquí, hardcodeados, y NO se leen de variables de entorno: así ningún
# valor viejo en Coolify/.env (p. ej. MODEL_DECAY_XI=0.004) puede degradar la
# precisión ya validada por RPS walk-forward. Si hay que recalibrar, se cambia
# AQUÍ (y se revalida con `python -m app.data.backtest`). Ver MODEL_STUDY.md §4.1.
HISTORY_TEAM_FILTER = "any"  # usa todos los rivales: ratings estables y opponent-adjusted
MODEL_DECAY_XI = 0.0015  # decaimiento temporal (~vida media ~15 meses); bate la base por RPS
ELO_PRIOR_WEIGHT = 2.5  # ancla fuerte al Elo (predice mejor que el ranking FIFA)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://maya:maya@localhost:5432/maya_predice"
    # API pública: por defecto permite cualquier origen ("*"). Restringe en
    # producción poniendo las URLs (separadas por coma) si lo prefieres.
    cors_origins: str = "*"
    env: str = "development"
    model_version: str = "dixon-coles-v1"
    # Panel de administración: secreto para firmar los JWT (si vacío, usa admin_token).
    jwt_secret: str = ""
    jwt_expire_hours: int = 12
    # Respaldo/compatibilidad: si no hay jwt_secret, se firma con este.
    admin_token: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Acepta la cadena de Coolify/Heroku (`postgres://`, `postgresql://`) y la
        normaliza al driver async que usa la app (`postgresql+asyncpg://`)."""
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v.removeprefix("postgres://")
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v.removeprefix("postgresql://")
        return v

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

    # --- Fuentes de plantillas (jugadores, suplentes, entrenadores) ---
    # Lista de proveedores activos (consenso multi-fuente). Opciones:
    # apifootball, thesportsdb, wikidata, fixture, remote.
    player_sources: str = "fixture"
    apifootball_key: str = ""
    apifootball_host: str = "https://v3.football.api-sports.io"
    thesportsdb_key: str = "3"
    # Sportmonks (token en la variable SPAPI_TOKEN). Cachea cada consulta en la DB.
    spapi_token: str = ""
    sportmonks_base: str = "https://api.sportmonks.com/v3/football"
    sportmonks_cache_ttl_hours: int = 24  # <=0 = caché indefinida
    squads_fixture_path: str = "app/data/samples/squads_sample.json"
    squads_remote_url: str = ""

    @property
    def player_sources_list(self) -> list[str]:
        return [s.strip() for s in self.player_sources.split(",") if s.strip()]

    # --- Entrenamiento del modelo (histórico de resultados) ---
    history_source_url: str = (
        "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    )
    history_since_year: int = 2018

    # Estos tres NO son campos de entorno: son propiedades de solo lectura que
    # devuelven las constantes calibradas de arriba, blindadas frente a overrides.
    @property
    def history_team_filter(self) -> str:
        return HISTORY_TEAM_FILTER

    @property
    def model_decay_xi(self) -> float:
        return MODEL_DECAY_XI

    @property
    def elo_prior_weight(self) -> float:
        return ELO_PRIOR_WEIGHT

    # --- Ajuste por disponibilidad de jugadores ---
    enable_availability_adjustment: bool = True
    availability_adj_strength: float = 0.5

    # --- Ensamble con cuotas de mercado (The Odds API) ---
    # La señal más predictiva (núcleo del método de Opta). Mezcla la predicción del
    # modelo con la probabilidad implícita del mercado: P = ω·modelo + (1−ω)·mercado.
    enable_market_ensemble: bool = False
    odds_api_key: str = ""  # env ODDS_API_KEY (the-odds-api.com; capa gratuita 500/mes)
    odds_api_base: str = "https://api.the-odds-api.com/v4"
    odds_sport_key: str = "soccer_fifa_world_cup"
    odds_regions: str = "eu"
    odds_cache_ttl_hours: int = 6  # las cuotas varían; se refrescan cada 6 h (con caché)
    # ω = peso del MODELO (el mercado pesa 1−ω). Por defecto 0.4 (el mercado manda).
    # Aún no validado por RPS (no hay cuotas históricas) → configurable por entorno.
    ensemble_model_weight: float = 0.4

    # --- Simulación del torneo ---
    # 10.000 iteraciones (como el supercomputador de Opta): menos varianza en las
    # probabilidades de avance/campeón que con 5.000.
    simulation_iterations: int = 10000

    # --- Actualización en vivo (recálculo al terminar partidos) ---
    enable_live_updates: bool = True
    live_poll_minutes: int = 60  # cada cuánto se reingieren resultados durante el torneo

    # Carga inicial automática al arrancar (solo si la base está vacía).
    enable_bootstrap: bool = True

    # --- Notificaciones por email (suscriptores) ---
    notifications_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "maya-predice <no-reply@maya-predice.com>"
    smtp_start_tls: bool = True   # 587 = STARTTLS; para 465 usar smtp_use_tls
    smtp_use_tls: bool = False
    site_url: str = "https://maya-predice.netlify.app"  # enlaces en el email
    # URL pública de la API (para el enlace de baja en los emails).
    api_public_url: str = "http://localhost:8000/api/v1"

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
