import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agent import BookingAgent
from src.ai.client import get_gemini_client
from src.ai.openrouter import OpenRouterAgent, get_openrouter_client
from src.ai.tools import BookingTools
from src.config import get_settings
from src.models import Complejo

logger = logging.getLogger(__name__)


class AgentManager:
    """Gestiona instancias de agentes en memoria por usuario para mantener el contexto conversacional."""

    def __init__(self):
        self._agents: dict[tuple[int, int], Any] = {}
        self._gemini_client = None
        self._openrouter_client = None

    @property
    def gemini_client(self):
        if self._gemini_client is None:
            self._gemini_client = get_gemini_client()
        return self._gemini_client

    @property
    def openrouter_client(self):
        if self._openrouter_client is None:
            self._openrouter_client = get_openrouter_client()
        return self._openrouter_client

    def get_agent(
        self,
        session: AsyncSession,
        complejo: Complejo,
        telegram_id: int,
        cliente_nombre: str,
        cliente_username: str | None = None,
    ) -> Any:
        """Obtiene el agente existente o crea uno nuevo según el proveedor configurado."""
        key = (telegram_id, complejo.id)
        settings = get_settings()

        # Re-vinculamos los tools a la sesión actual de la base de datos
        tools = BookingTools(
            session=session,
            complejo_id=complejo.id,
            telegram_id=telegram_id,
            cliente_nombre=cliente_nombre,
            cliente_username=cliente_username,
        )

        tool_map = {
            "consultar_canchas_y_precios": tools.consultar_canchas_y_precios,
            "consultar_disponibilidad": tools.consultar_disponibilidad,
            "crear_reserva": tools.crear_reserva,
            "consultar_mis_reservas": tools.consultar_mis_reservas,
            "cancelar_reserva": tools.cancelar_reserva,
        }

        if key in self._agents:
            agent = self._agents[key]
            # Actualizar las tools con la nueva sesión activa de DB
            agent.tools = tools
            agent.tool_map = tool_map
            return agent

        # Crear nuevo agente según el proveedor seleccionado
        if settings.AI_PROVIDER == "openrouter":
            logger.info("Creando OpenRouterAgent para usuario %s (modelo: %s)", telegram_id, settings.OPENROUTER_MODEL)
            agent = OpenRouterAgent(
                client=self.openrouter_client,
                complejo_nombre=complejo.nombre,
                tools=tools,
                model=settings.OPENROUTER_MODEL,
            )
        else:
            logger.info("Creando BookingAgent (Gemini) para usuario %s (modelo: %s)", telegram_id, settings.GEMINI_MODEL)
            agent = BookingAgent(
                client=self.gemini_client,
                complejo_nombre=complejo.nombre,
                tools=tools,
                model=settings.GEMINI_MODEL,
            )

        self._agents[key] = agent
        return agent

    def reset_agent(self, telegram_id: int, complejo_id: int) -> None:
        """Reinicia el historial conversacional del usuario."""
        key = (telegram_id, complejo_id)
        if key in self._agents:
            del self._agents[key]


# Instancia singleton del gestor de agentes
agent_manager = AgentManager()
