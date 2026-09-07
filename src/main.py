"""Punto de entrada principal de la aplicación Canchas SaaS."""
import logging
from src.config import get_settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.LOG_LEVEL)
    logger.info("Iniciando Canchas SaaS en entorno: %s", settings.ENV)


if __name__ == "__main__":
    main()
