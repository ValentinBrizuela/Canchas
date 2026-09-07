from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno
    ENV: Literal["development", "testing", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # Base de Datos
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/canchas.db"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""

    # Proveedor de IA (gemini u openrouter)
    AI_PROVIDER: Literal["gemini", "openrouter"] = "gemini"

    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # OpenRouter AI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Multi-tenant / Complejo por defecto
    DEFAULT_TENANT_SLUG: str = "demo-complejo"
    DEFAULT_TENANT_NAME: str = "Complejo Deportivo Demo"


@lru_cache()
def get_settings() -> Settings:
    """Retorna una instancia única en caché de la configuración."""
    return Settings()
