import logging
from google import genai
from src.config import get_settings

logger = logging.getLogger(__name__)


def get_gemini_client(api_key: str | None = None) -> genai.Client:
    """Crea e inicializa una instancia del cliente de Google Gemini SDK."""
    settings = get_settings()
    key = api_key or settings.GEMINI_API_KEY

    if not key or key == "tu_api_key_aqui":
        logger.warning("GEMINI_API_KEY no configurada o usando valor por defecto.")

    return genai.Client(api_key=key)
