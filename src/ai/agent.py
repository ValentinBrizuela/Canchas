import logging
from typing import Any
from google import genai
from google.genai import types

from src.ai.prompts import get_system_prompt
from src.ai.tools import BookingTools
from src.config import get_settings

logger = logging.getLogger(__name__)


class BookingAgent:
    """Orquestador conversacional que interactúa con Gemini y ejecuta herramientas."""

    def __init__(
        self,
        client: genai.Client,
        complejo_nombre: str,
        tools: BookingTools,
        model: str | None = None,
    ):
        self.client = client
        self.complejo_nombre = complejo_nombre
        self.tools = tools
        self.model = model or get_settings().GEMINI_MODEL
        self.system_prompt = get_system_prompt(complejo_nombre)
        self.history: list[types.Content] = []

        # Mapa de métodos invocables por nombre
        self.tool_map = {
            "consultar_canchas_y_precios": self.tools.consultar_canchas_y_precios,
            "consultar_disponibilidad": self.tools.consultar_disponibilidad,
            "crear_reserva": self.tools.crear_reserva,
            "consultar_mis_reservas": self.tools.consultar_mis_reservas,
            "cancelar_reserva": self.tools.cancelar_reserva,
        }

    async def chat(self, user_message: str) -> str:
        """Procesa un mensaje del usuario y orquesta el bucle con Gemini y Tools."""
        # 1. Registrar mensaje del usuario en el historial
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
        self.history.append(user_content)

        # 2. Configuración de llamada a Gemini
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=self.tools.get_tool_declarations(),
            temperature=0.3,
        )

        try:
            # Máximo de iteraciones en bucle de tools para prevenir ciclos infinitos
            max_iterations = 5
            for _ in range(max_iterations):
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=self.history,
                    config=config,
                )

                # Si el modelo no solicita function calls, devolver el texto final
                if not response.function_calls:
                    assistant_text = response.text or "Entendido."
                    if (
                        response.candidates
                        and hasattr(response.candidates[0], "content")
                        and isinstance(response.candidates[0].content, types.Content)
                    ):
                        self.history.append(response.candidates[0].content)
                    else:
                        self.history.append(
                            types.Content(
                                role="model",
                                parts=[types.Part.from_text(text=assistant_text)],
                            )
                        )
                    return assistant_text

                # El modelo solicitó invocar herramientas
                # Preservar candidate.content original para retener thought_signature y metadatos
                if (
                    response.candidates
                    and hasattr(response.candidates[0], "content")
                    and isinstance(response.candidates[0].content, types.Content)
                ):
                    self.history.append(response.candidates[0].content)
                else:
                    model_parts = []
                    for call in response.function_calls:
                        model_parts.append(
                            types.Part.from_function_call(
                                name=call.name,
                                args=call.args or {},
                            )
                        )
                    self.history.append(types.Content(role="model", parts=model_parts))

                # Ejecutar cada herramienta solicitada y armar las respuestas
                response_parts = []
                for call in response.function_calls:
                    fn_name = call.name
                    fn_args = call.args or {}
                    logger.info("Ejecutando tool: %s con args: %s", fn_name, fn_args)

                    handler = self.tool_map.get(fn_name)
                    if handler:
                        try:
                            result = await handler(**fn_args)
                        except Exception as err:
                            logger.error("Error al ejecutar tool %s: %s", fn_name, err)
                            result = {"error": f"Error al ejecutar la acción: {str(err)}"}
                    else:
                        result = {"error": f"Herramienta '{fn_name}' no encontrada."}

                    response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": result},
                        )
                    )

                # Agregar las respuestas de las funciones al historial para que Gemini continúe
                self.history.append(types.Content(role="user", parts=response_parts))

            return "Se alcanzó el límite de operaciones para esta consulta. ¿Podrías reiterar tu pedido?"

        except Exception as e:
            logger.error("Error en comunicación con Gemini: %s", e, exc_info=True)
            return (
                "Disculpá, ocurrió un inconveniente temporal al procesar tu mensaje. "
                "Por favor intentá nuevamente en unos instantes."
            )
