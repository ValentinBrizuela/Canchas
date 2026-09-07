from unittest.mock import AsyncMock, MagicMock
import pytest
from src.ai.agent import BookingAgent
from src.ai.tools import BookingTools
from src.db.session import create_engine_and_session, init_db
from src.models import Cancha, Complejo


@pytest.fixture
async def db_session():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_direct_response_without_tools(db_session):
    mock_client = MagicMock()
    mock_generate = AsyncMock()

    # Respuesta simple sin function calls
    mock_response = MagicMock()
    mock_response.function_calls = None
    mock_response.text = "¡Hola! Bienvenido al complejo. ¿En qué te puedo ayudar?"
    mock_generate.return_value = mock_response

    mock_client.aio.models.generate_content = mock_generate

    tools = BookingTools(
        session=db_session,
        complejo_id=1,
        telegram_id=12345,
        cliente_nombre="Lucas",
    )
    agent = BookingAgent(
        client=mock_client,
        complejo_nombre="Complejo Test",
        tools=tools,
    )

    respuesta = await agent.chat("Hola, buenas tardes")
    assert respuesta == "¡Hola! Bienvenido al complejo. ¿En qué te puedo ayudar?"
    assert len(agent.history) == 2
    assert agent.history[0].role == "user"
    assert agent.history[1].role == "model"


@pytest.mark.asyncio
async def test_agent_tool_calling_flow(db_session):
    # Crear datos en DB
    complejo = Complejo(slug="test-ai", nombre="Complejo AI")
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha F5",
        tipo="Fútbol 5",
        duracion_minutos=60,
        precio=18000.0,
    )
    db_session.add(cancha)
    await db_session.commit()

    mock_client = MagicMock()
    mock_generate = AsyncMock()

    # 1era respuesta: solicita ejecutar `consultar_canchas_y_precios`
    call_mock = MagicMock()
    call_mock.name = "consultar_canchas_y_precios"
    call_mock.args = {}

    resp_with_tool = MagicMock()
    resp_with_tool.function_calls = [call_mock]

    # 2da respuesta: después de recibir la info, responde con el texto final
    final_resp = MagicMock()
    final_resp.function_calls = None
    final_resp.text = "Contamos con la Cancha F5 (Fútbol 5, 60 min) a $18.000 el turno."

    mock_generate.side_effect = [resp_with_tool, final_resp]
    mock_client.aio.models.generate_content = mock_generate

    tools = BookingTools(
        session=db_session,
        complejo_id=complejo.id,
        telegram_id=12345,
        cliente_nombre="Lucas",
    )
    agent = BookingAgent(
        client=mock_client,
        complejo_nombre="Complejo AI",
        tools=tools,
    )

    respuesta = await agent.chat("¿Qué canchas tienen y cuánto salen?")
    assert "Cancha F5" in respuesta
    assert "$18.000" in respuesta
    assert mock_generate.call_count == 2
