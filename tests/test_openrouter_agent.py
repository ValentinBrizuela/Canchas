import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.ai.openrouter import OpenRouterAgent
from src.ai.tools import BookingTools
from src.bot.manager import AgentManager
from src.config import Settings
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
async def test_openrouter_agent_direct_response(db_session):
    mock_client = MagicMock()
    mock_create = AsyncMock()

    # Mock de respuesta simple sin tools
    mock_message = MagicMock()
    mock_message.tool_calls = None
    mock_message.content = "¡Hola! ¿En qué te puedo ayudar hoy?"

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_create.return_value = mock_response

    mock_client.chat.completions.create = mock_create

    tools = BookingTools(
        session=db_session,
        complejo_id=1,
        telegram_id=999,
        cliente_nombre="Valentin",
    )
    agent = OpenRouterAgent(
        client=mock_client,
        complejo_nombre="Complejo Demo",
        tools=tools,
        model="meta-llama/llama-3.3-70b-instruct:free",
    )

    respuesta = await agent.chat("Hola!")
    assert respuesta == "¡Hola! ¿En qué te puedo ayudar hoy?"
    assert len(agent.history) == 3  # system, user, assistant
    assert agent.history[1]["role"] == "user"
    assert agent.history[2]["role"] == "assistant"


@pytest.mark.asyncio
async def test_openrouter_agent_tool_calling_flow(db_session):
    complejo = Complejo(slug="openrouter-test", nombre="Complejo OpenRouter")
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha F5 Sintético",
        tipo="Fútbol 5",
        duracion_minutos=60,
        precio=25000.0,
    )
    db_session.add(cancha)
    await db_session.commit()

    mock_client = MagicMock()
    mock_create = AsyncMock()

    # Turno 1: el modelo devuelve un tool_call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc123"
    mock_tool_call.function.name = "consultar_canchas_y_precios"
    mock_tool_call.function.arguments = "{}"

    msg_with_tools = MagicMock()
    msg_with_tools.tool_calls = [mock_tool_call]
    msg_with_tools.model_dump.return_value = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "consultar_canchas_y_precios",
                    "arguments": "{}",
                },
            }
        ],
    }

    choice_1 = MagicMock(message=msg_with_tools)
    resp_1 = MagicMock(choices=[choice_1])

    # Turno 2: el modelo responde en texto final tras ver los resultados del tool
    final_msg = MagicMock()
    final_msg.tool_calls = None
    final_msg.content = "Contamos con la Cancha F5 Sintético a $25.000 la hora."
    choice_2 = MagicMock(message=final_msg)
    resp_2 = MagicMock(choices=[choice_2])

    mock_create.side_effect = [resp_1, resp_2]
    mock_client.chat.completions.create = mock_create

    tools = BookingTools(
        session=db_session,
        complejo_id=complejo.id,
        telegram_id=999,
        cliente_nombre="Valentin",
    )
    agent = OpenRouterAgent(
        client=mock_client,
        complejo_nombre=complejo.nombre,
        tools=tools,
        model="meta-llama/llama-3.3-70b-instruct:free",
    )

    respuesta = await agent.chat("¿Qué canchas tienen?")
    assert "Cancha F5 Sintético" in respuesta
    assert "$25.000" in respuesta
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_agent_manager_selects_openrouter_when_configured(db_session):
    complejo = Complejo(slug="test-factory", nombre="Sede Factory")
    manager = AgentManager()

    custom_settings = Settings(
        _env_file=None,
        AI_PROVIDER="openrouter",
        OPENROUTER_API_KEY="sk-or-test",
        OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
    )

    with patch("src.bot.manager.get_settings", return_value=custom_settings):
        agent = manager.get_agent(
            session=db_session,
            complejo=complejo,
            telegram_id=123,
            cliente_nombre="Carlos",
        )
        assert isinstance(agent, OpenRouterAgent)
        assert agent.model == "meta-llama/llama-3.3-70b-instruct:free"
