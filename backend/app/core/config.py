"""Application settings loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FMCG Innovation Reaction Simulator"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./fmcg_sim.db"
    environment: str = "local"
    demo_mode: bool = False

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    default_num_consumers: int = 50
    default_num_rounds: int = 6
    llm_temperature: float = 0.2
    llm_seed: int = 42

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Optional single extra origin (e.g. a deployed frontend) appended at runtime.
    frontend_origin: str = ""

    # Observability (Phase 24)
    log_json: bool = False
    app_log_max_entries: int = 500

    def resolved_cors_origins(self) -> list[str]:
        origins = list(self.cors_origins)
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
