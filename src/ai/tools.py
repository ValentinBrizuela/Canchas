from datetime import date, datetime, time, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Cancha, Complejo
from src.services.availability import AvailabilityService
from src.services.booking import BookingError, BookingService


from google.genai import types


def get_booking_tool_declarations() -> list[types.Tool]:
    """Genera las declaraciones OpenAPI de herramientas para Gemini sin referencias a métodos ligados."""
    decls = [
        types.FunctionDeclaration(
            name="consultar_canchas_y_precios",
            description="Consulta la lista de canchas del complejo, sus tipos, duración de turno y precios.",
            parameters=types.Schema(type="OBJECT", properties={}),
        ),
        types.FunctionDeclaration(
            name="consultar_disponibilidad",
            description="Consulta los turnos y horarios disponibles para reservar en una fecha específica.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "fecha": types.Schema(
                        type="STRING",
                        description="Fecha en formato YYYY-MM-DD (por ejemplo '2026-09-10').",
                    ),
                    "tipo_cancha": types.Schema(
                        type="STRING",
                        description="Tipo o filtro opcional (por ejemplo 'Fútbol 5', 'Fútbol 7', 'Pádel').",
                    ),
                },
                required=["fecha"],
            ),
        ),
        types.FunctionDeclaration(
            name="crear_reserva",
            description="Crea y confirma una reserva de turno para el cliente actual.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "cancha_id": types.Schema(
                        type="INTEGER",
                        description="Identificador numérico de la cancha.",
                    ),
                    "fecha": types.Schema(
                        type="STRING",
                        description="Fecha del turno en formato YYYY-MM-DD (ej: '2026-09-10').",
                    ),
                    "hora_inicio": types.Schema(
                        type="STRING",
                        description="Hora de inicio del turno en formato HH:MM (ej: '19:00').",
                    ),
                    "notas": types.Schema(
                        type="STRING",
                        description="Observaciones o notas adicionales de la reserva.",
                    ),
                },
                required=["cancha_id", "fecha", "hora_inicio"],
            ),
        ),
        types.FunctionDeclaration(
            name="consultar_mis_reservas",
            description="Consulta todas las reservas activas y confirmadas del cliente actual.",
            parameters=types.Schema(type="OBJECT", properties={}),
        ),
        types.FunctionDeclaration(
            name="cancelar_reserva",
            description="Cancela una reserva activa del cliente actual.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "reserva_id": types.Schema(
                        type="INTEGER",
                        description="ID numérico de la reserva a cancelar.",
                    ),
                },
                required=["reserva_id"],
            ),
        ),
    ]
    return [types.Tool(function_declarations=decls)]


class BookingTools:
    """Proveedor de herramientas (tools) para el LLM con contexto de usuario y complejo."""

    def __init__(
        self,
        session: AsyncSession,
        complejo_id: int,
        telegram_id: int,
        cliente_nombre: str,
        cliente_username: str | None = None,
    ):
        self.session = session
        self.complejo_id = complejo_id
        self.telegram_id = telegram_id
        self.cliente_nombre = cliente_nombre
        self.cliente_username = cliente_username
        self.availability_service = AvailabilityService(session)
        self.booking_service = BookingService(session)

    async def consultar_canchas_y_precios(self) -> list[dict[str, Any]]:
        """Consulta la lista de canchas del complejo, sus tipos, duración de turno y precios."""
        stmt = select(Cancha).where(
            Cancha.complejo_id == self.complejo_id,
            Cancha.activa == True,  # noqa: E712
        )
        res = await self.session.execute(stmt)
        canchas = res.scalars().all()
        return [
            {
                "cancha_id": c.id,
                "nombre": c.nombre,
                "tipo": c.tipo,
                "duracion_minutos": c.duracion_minutos,
                "precio": c.precio,
            }
            for c in canchas
        ]

    async def consultar_disponibilidad(
        self,
        fecha: str,
        tipo_cancha: str = "",
    ) -> list[dict[str, Any]]:
        """Consulta los turnos y horarios disponibles para reservar en una fecha específica."""
        try:
            target_date = date.fromisoformat(fecha)
        except ValueError:
            return [{"error": f"Formato de fecha inválido ('{fecha}'). Debe ser YYYY-MM-DD."}]

        slots = await self.availability_service.get_available_slots(
            complejo_id=self.complejo_id,
            target_date=target_date,
            tipo_cancha=tipo_cancha if tipo_cancha else None,
        )

        return [
            {
                "cancha_id": s.cancha_id,
                "cancha_nombre": s.cancha_nombre,
                "tipo": s.tipo_cancha,
                "fecha": s.fecha,
                "hora_inicio": s.hora_inicio,
                "hora_fin": s.hora_fin,
                "duracion_minutos": s.duracion_minutos,
                "precio": s.precio,
            }
            for s in slots
        ]

    async def crear_reserva(
        self,
        cancha_id: int,
        fecha: str,
        hora_inicio: str,
        notas: str = "",
    ) -> dict[str, Any]:
        """Crea y confirma una reserva de turno para el cliente actual."""
        try:
            d = date.fromisoformat(fecha)
            partes_hora = [int(p) for p in hora_inicio.split(":")]
            t = time(partes_hora[0], partes_hora[1])
            fecha_inicio_dt = datetime.combine(d, t, tzinfo=timezone.utc)
        except Exception as e:
            return {"error": f"Fecha u hora inválida: {str(e)}"}

        try:
            reserva = await self.booking_service.create_booking(
                cancha_id=cancha_id,
                fecha_inicio=fecha_inicio_dt,
                telegram_id=self.telegram_id,
                cliente_nombre=self.cliente_nombre,
                cliente_username=self.cliente_username,
                notas=notas if notas else None,
            )
            return {
                "status": "success",
                "reserva_id": reserva.id,
                "cancha_id": reserva.cancha_id,
                "cancha_nombre": reserva.cancha.nombre if reserva.cancha else "",
                "fecha_inicio": reserva.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "fecha_fin": reserva.fecha_fin.strftime("%H:%M"),
                "precio": reserva.precio,
                "mensaje": "Reserva confirmada con éxito.",
            }
        except BookingError as e:
            return {"status": "error", "error": str(e)}

    async def consultar_mis_reservas(self) -> list[dict[str, Any]]:
        """Consulta todas las reservas activas y confirmadas del cliente actual."""
        reservas = await self.booking_service.get_customer_bookings(
            telegram_id=self.telegram_id,
            only_active=True,
        )
        return [
            {
                "reserva_id": r.id,
                "cancha_id": r.cancha_id,
                "cancha_nombre": r.cancha.nombre if r.cancha else "",
                "fecha_inicio": r.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "fecha_fin": r.fecha_fin.strftime("%H:%M"),
                "precio": r.precio,
                "estado": r.estado,
            }
            for r in reservas
        ]

    async def cancelar_reserva(self, reserva_id: int) -> dict[str, Any]:
        """Cancela una reserva activa del cliente actual."""
        try:
            reserva = await self.booking_service.cancel_booking(
                reserva_id=reserva_id,
                telegram_id=self.telegram_id,
            )
            return {
                "status": "success",
                "reserva_id": reserva.id,
                "mensaje": f"La reserva #{reserva.id} fue cancelada correctamente.",
            }
        except BookingError as e:
            return {"status": "error", "error": str(e)}

    def get_tool_declarations(self) -> list[Any]:
        """Retorna las declaraciones formales de herramientas listas para Gemini."""
        return get_booking_tool_declarations()
