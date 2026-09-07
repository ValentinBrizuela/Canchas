"""Punto de entrada principal de la aplicación Canchas SaaS."""
import asyncio
import logging
from src.bot import create_bot, create_dispatcher
from src.config import get_settings
from src.db.seed import seed_initial_data
from src.db.session import async_session, init_db
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def run_app() -> None:
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)

    logger.info("==========================================")
    logger.info("Iniciando Canchas SaaS")
    logger.info("Entorno: %s", settings.ENV)
    logger.info("Base de datos: %s", settings.DATABASE_URL)
    logger.info("==========================================")

    # 1. Inicializar esquema de base de datos
    logger.info("Verificando e inicializando tablas en la base de datos...")
    await init_db()

    # 2. Cargar datos iniciales por defecto si no existen
    async with async_session() as session:
        complejo = await seed_initial_data(session)
        logger.info("Complejo activo: %s (slug: %s)", complejo.nombre, complejo.slug)

    # 3. Validar token de Telegram
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "tu_token_aqui":
        logger.warning(
            "TELEGRAM_BOT_TOKEN no está configurado en el archivo .env. "
            "El bot no iniciará polling hasta que configures un token válido de @BotFather."
        )
        return

    # 4. Iniciar Bot y Polling
    bot = create_bot()
    dp = create_dispatcher()

    logger.info("Iniciando recepción de mensajes en Telegram (Polling)...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
