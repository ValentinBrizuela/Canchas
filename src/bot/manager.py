import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.ai.agent import BookingAgent
from src.ai.client import get_gemini_client
from src.ai.tools import BookingTools
from src.models import Complejo

logger = logging.getLogger(__name__)


class AgentManager:
    """Gestiona instancias de BookingAgent en memoria por usuario para mantener el contexto conversacional."""

    def __init__(self):
        self._agents: dict[tuple[int, int], BookingAgent] = {}
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def get_agent(
        self,
        session: AsyncSession,
        complejo: Complejo,
        telegram_id: int,
        cliente_nombre: str,
        cliente_username: str | None = None,
    ) -> BookingAgent:
        """Obtiene el agente existente o crea uno nuevo para el usuario."""
        key = (telegram_id, complejo.id)

        # Re-vinculamos los tools a la sesión actual de la base de datos
        tools = BookingTools(
            session=session,
            complejo_id=complejo.id,
            telegram_id=telegram_id,
            cliente_nombre=cliente_nombre,
            cliente_username=cliente_username,
        )

        if key in self._agents:
            agent = self._agents[key]
            # Actualizar las tools con la nueva sesión activa de DB
            agent.tools = tools
            agent.tool_map = {
                "consultar_canchas_y_precios": tools.consultar_canchas_y_precios,
                "consultar_disponibilidad": tools.consultar_disponibilidad,
                "crear_reserva": tools.crear_reserva,
                "consultar_mis_reservas": tools.consultar_mis_reservas,
                "cancelar_reserva": tools.cancelar_reserva,
            }
            return agent

        agent = BookingAgent(
            client=self.client,
            complejo_nombre=complejo.nombre,
            tools=tools,
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
