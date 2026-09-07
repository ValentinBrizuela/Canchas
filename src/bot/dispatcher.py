import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    """Crea y configura el Dispatcher de aiogram con almacenamiento en memoria."""
    dp = Dispatcher(storage=MemoryStorage())

    @dp.startup()
    async def on_startup():
        logger.info("Bot de Telegram iniciado correctamente.")

    @dp.shutdown()
    async def on_shutdown():
        logger.info("Bot de Telegram detenido.")

    return dp
