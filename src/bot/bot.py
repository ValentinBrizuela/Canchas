import logging
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import get_settings

logger = logging.getLogger(__name__)


def create_bot(token: str | None = None) -> Bot:
    """Crea la instancia de Bot de aiogram."""
    settings = get_settings()
    bot_token = token or settings.TELEGRAM_BOT_TOKEN

    if not bot_token or bot_token == "tu_token_aqui":
        logger.warning("TELEGRAM_BOT_TOKEN no configurado o usando valor por defecto.")

    return Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
