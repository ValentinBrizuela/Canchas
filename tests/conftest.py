import pytest
from src.config import Settings
from src.logging_config import setup_logging


@pytest.fixture(autouse=True)
def configure_test_logging():
    """Configura logging en modo warning para no ensuciar la salida de los tests."""
    setup_logging(level="WARNING")


@pytest.fixture
def test_settings() -> Settings:
    """Configuración aislada para pruebas en memoria."""
    return Settings(
        ENV="testing",
        LOG_LEVEL="WARNING",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        TELEGRAM_BOT_TOKEN="test_token_12345",
        GEMINI_API_KEY="test_gemini_key",
        DEFAULT_TENANT_SLUG="test-complejo",
        DEFAULT_TENANT_NAME="Complejo de Pruebas",
    )


@pytest.fixture
async def db_session():
    """Sesión de base de datos aislada en memoria SQLite para tests."""
    from src.db.session import create_engine_and_session, init_db

    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()
