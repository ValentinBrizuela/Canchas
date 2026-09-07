import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configura el sistema de logging estructurado de la aplicación."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Reemplazar handlers existentes para evitar logs duplicados
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reducir verbosidad de librerías externas ruidosas
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
