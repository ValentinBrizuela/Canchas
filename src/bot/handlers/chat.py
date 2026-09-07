import logging
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from src.bot.handlers.start import get_or_default_complejo
from src.bot.manager import agent_manager
from src.db.session import async_session

logger = logging.getLogger(__name__)

router = Router(name="chat_router")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_conversational_message(message: Message) -> None:
    """Enruta cualquier mensaje de texto del cliente hacia el agente conversacional de Gemini."""
    user = message.from_user
    if not user or not message.text:
        return

    # Mostrar estado de "escribiendo..." en el chat de Telegram
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    try:
        async with async_session() as session:
            complejo = await get_or_default_complejo(session)

            agent = agent_manager.get_agent(
                session=session,
                complejo=complejo,
                telegram_id=user.id,
                cliente_nombre=user.full_name or user.first_name,
                cliente_username=user.username,
            )

            # Ejecutar el agente con Gemini y herramientas
            respuesta = await agent.chat(message.text)

            await message.answer(respuesta)

    except Exception as e:
        logger.error("Error al procesar mensaje de Telegram: %s", e, exc_info=True)
        await message.answer(
            "Disculpá, tuve un problema para procesar tu mensaje. "
            "Por favor volvé a intentar en unos instantes."
        )
