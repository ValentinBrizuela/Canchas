import json
import logging
from typing import Any
from openai import AsyncOpenAI

from src.ai.prompts import get_system_prompt
from src.ai.tools import BookingTools
from src.config import get_settings

logger = logging.getLogger(__name__)


def get_openrouter_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncOpenAI:
    """Crea un cliente asíncrono configurado para OpenRouter."""
    settings = get_settings()
    key = api_key or settings.OPENROUTER_API_KEY
    url = base_url or settings.OPENROUTER_BASE_URL

    if not key or key == "tu_openrouter_key_aqui":
        logger.warning("OPENROUTER_API_KEY no configurada o usando valor por defecto.")
        key = key or "sk-or-placeholder"

    return AsyncOpenAI(
        api_key=key,
        base_url=url,
        default_headers={
            "HTTP-Referer": "https://github.com/canchas-saas",
            "X-Title": "Canchas SaaS Telegram Bot",
        },
    )


class OpenRouterAgent:
    """Orquestador conversacional para modelos servidos a través de OpenRouter."""

    def __init__(
        self,
        client: AsyncOpenAI,
        complejo_nombre: str,
        tools: BookingTools,
        model: str | None = None,
    ):
        self.client = client
        self.complejo_nombre = complejo_nombre
        self.tools = tools
        self.model = model or get_settings().OPENROUTER_MODEL
        self.system_prompt = get_system_prompt(complejo_nombre)

        # Historial de mensajes en formato OpenAI
        self.history: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Mapa de ejecución de herramientas
        self.tool_map = {
            "consultar_canchas_y_precios": self.tools.consultar_canchas_y_precios,
            "consultar_disponibilidad": self.tools.consultar_disponibilidad,
            "crear_reserva": self.tools.crear_reserva,
            "consultar_mis_reservas": self.tools.consultar_mis_reservas,
            "cancelar_reserva": self.tools.cancelar_reserva,
        }

    async def chat(self, user_message: str) -> str:
        """Procesa un mensaje del usuario y orquesta el bucle de herramientas en OpenRouter."""
        self.history.append({"role": "user", "content": user_message})

        tools = self.tools.get_openai_tools()

        try:
            max_iterations = 5
            for _ in range(max_iterations):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=tools,
                    temperature=0.3,
                )

                choice = response.choices[0]
                message = choice.message

                # Si el modelo no solicitó tools, devolver el texto final
                if not message.tool_calls:
                    assistant_text = message.content or "Entendido."
                    self.history.append({"role": "assistant", "content": assistant_text})
                    return assistant_text

                # El modelo solicitó invocar herramientas
                self.history.append(message.model_dump(exclude_unset=True))

                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    raw_args = tool_call.function.arguments or "{}"
                    try:
                        fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        fn_args = {}

                    logger.info("OpenRouter tool: %s con args: %s", fn_name, fn_args)

                    handler = self.tool_map.get(fn_name)
                    if handler:
                        try:
                            result = await handler(**fn_args)
                        except Exception as err:
                            logger.error("Error al ejecutar tool %s: %s", fn_name, err)
                            result = {"error": f"Error al ejecutar la acción: {str(err)}"}
                    else:
                        result = {"error": f"Herramienta '{fn_name}' no encontrada."}

                    self.history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": fn_name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            return "Se alcanzó el límite de operaciones para esta consulta. ¿Podrías reiterar tu pedido?"

        except Exception as e:
            logger.error("Error en comunicación con OpenRouter: %s", e, exc_info=True)
            return (
                "Disculpá, ocurrió un inconveniente temporal al procesar tu mensaje con OpenRouter. "
                "Por favor intentá nuevamente en unos instantes."
            )
