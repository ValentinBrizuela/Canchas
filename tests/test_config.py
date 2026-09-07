import pytest
from src.config import Settings, get_settings


def test_settings_default_values():
    settings = Settings(_env_file=None)
    assert settings.ENV == "development"
    assert settings.LOG_LEVEL == "INFO"
    assert "canchas.db" in settings.DATABASE_URL
    assert settings.GEMINI_MODEL == "gemini-3.5-flash"
    assert settings.DEFAULT_TENANT_SLUG == "demo-complejo"


def test_get_settings_is_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
