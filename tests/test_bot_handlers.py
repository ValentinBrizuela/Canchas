from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import Chat, Message, User

from src.bot.handlers.chat import handle_conversational_message
from src.bot.handlers.start import handle_ayuda, handle_reiniciar, handle_start
from src.db.session import create_engine_and_session, init_db


@pytest.fixture
async def db_session():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


def create_mock_message(user_id=12345, first_name="Lautaro", text="/start"):
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        last_name="Martínez",
        username="lautarom",
    )
    chat = Chat(id=user_id, type="private")

    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.text = text
    message.answer = AsyncMock()
    message.bot = MagicMock()
    message.bot.send_chat_action = AsyncMock()

    return message


@pytest.mark.asyncio
async def test_handle_start_command(db_session):
    message = create_mock_message(user_id=999, first_name="Diego", text="/start")

    with patch("src.bot.handlers.start.async_session") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = db_session

        await handle_start(message)

        message.answer.assert_called_once()
        texto_enviado = message.answer.call_args[0][0]
        assert "Diego" in texto_enviado
        assert "¡Hola" in texto_enviado


@pytest.mark.asyncio
async def test_handle_ayuda_command():
    message = create_mock_message(text="/ayuda")
    await handle_ayuda(message)

    message.answer.assert_called_once()
    texto = message.answer.call_args[0][0]
    assert "Guía de ayuda" in texto
    assert "/start" in texto


@pytest.mark.asyncio
async def test_handle_reiniciar_command(db_session):
    message = create_mock_message(text="/reiniciar")

    with patch("src.bot.handlers.start.async_session") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = db_session

        await handle_reiniciar(message)

        message.answer.assert_called_once()
        texto = message.answer.call_args[0][0]
        assert "reiniciada" in texto


@pytest.mark.asyncio
async def test_handle_conversational_message(db_session):
    message = create_mock_message(text="Hola, ¿tienen canchas para hoy?")

    with patch("src.bot.handlers.chat.async_session") as mock_session_ctx, \
         patch("src.bot.handlers.chat.agent_manager.get_agent") as mock_get_agent:

        mock_session_ctx.return_value.__aenter__.return_value = db_session
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Sí, tenemos cancha a las 20:00.")
        mock_get_agent.return_value = mock_agent

        await handle_conversational_message(message)

        message.bot.send_chat_action.assert_called_once()
        mock_agent.chat.assert_called_once_with("Hola, ¿tienen canchas para hoy?")
        message.answer.assert_called_once_with("Sí, tenemos cancha a las 20:00.")
