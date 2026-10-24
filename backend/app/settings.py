"""Configurazione da variabili d'ambiente. Valori di default pensati per lo sviluppo locale."""
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db"))
    models_dir: Path = field(default_factory=lambda: Path(os.getenv("MODELS_DIR", REPO_ROOT / "models")))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", REPO_ROOT / "data")))
    # mock: gli agenti producono un output simulato, senza chiavi API. live: chiamate reali tramite il gateway LiteLLM.
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "mock"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://gateway:4000/v1"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "sk-local"))
    # API di gestione del gateway (senza /v1): il worker vi sincronizza il catalogo LLM
    llm_admin_url: str = field(default_factory=lambda: os.getenv("LLM_ADMIN_URL", "http://gateway:4000"))
    timezone: str = field(default_factory=lambda: os.getenv("APP_TIMEZONE", "Europe/Rome"))
    poll_seconds: int = field(default_factory=lambda: int(os.getenv("WORKER_POLL_SECONDS", "30")))
    reload_minutes: int = field(default_factory=lambda: int(os.getenv("WORKER_RELOAD_MINUTES", "5")))


settings = Settings()
