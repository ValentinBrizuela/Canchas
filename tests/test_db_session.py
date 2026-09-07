import pytest
from sqlalchemy import text
from src.db.session import create_engine_and_session, init_db, Base


@pytest.mark.asyncio
async def test_database_session_and_init():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    await engine.dispose()
