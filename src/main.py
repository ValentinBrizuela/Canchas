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

    # 3. Configurar e iniciar servidor Web (FastAPI + Uvicorn)
    import uvicorn
    from src.web.app import create_web_app

    web_app = create_web_app()
    uvicorn_config = uvicorn.Config(
        app=web_app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Panel Web de Administración iniciado en http://0.0.0.0:8000")
    logger.info("Documentación interactiva Swagger disponible en http://0.0.0.0:8000/docs")

    # 4. Validar token de Telegram para iniciar Polling concurrentemente
    bot_enabled = bool(
        settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "tu_token_aqui"
    )

    tasks = [server.serve()]

    if bot_enabled:
        bot = create_bot()
        dp = create_dispatcher()
        logger.info("Iniciando recepción de mensajes en Telegram (Polling)...")

        async def run_bot_polling():
            try:
                await dp.start_polling(bot)
            finally:
                await bot.session.close()

        tasks.append(run_bot_polling())
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN no está configurado o tiene el valor por defecto. "
            "El bot de Telegram permanecerá inactivo, pero el Panel Web continuará operativo."
        )

    # 5. Ejecutar servicios concurrentemente
    await asyncio.gather(*tasks)


def main() -> None:
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
