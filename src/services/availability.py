from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cancha import Cancha
from src.models.complejo import Complejo
from src.models.reserva import EstadoReserva, Reserva


@dataclass
class SlotDisponible:
    """Representa un turno libre listo para ser reservado."""
    cancha_id: int
    cancha_nombre: str
    tipo_cancha: str
    fecha: str  # YYYY-MM-DD
    hora_inicio: str  # HH:MM
    hora_fin: str  # HH:MM
    duracion_minutos: int
    precio: float


class AvailabilityService:
    """Servicio para calcular turnos disponibles respetando horarios y reservas confirmadas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_available_slots(
        self,
        complejo_id: int,
        target_date: date,
        tipo_cancha: str | None = None,
    ) -> list[SlotDisponible]:
        """Obtiene los turnos disponibles para un complejo en una fecha específica."""
        # 1. Obtener el complejo
        complejo_stmt = select(Complejo).where(
            Complejo.id == complejo_id,
            Complejo.activo == True,  # noqa: E712
        )
        res = await self.session.execute(complejo_stmt)
        complejo = res.scalar_one_or_none()
        if not complejo:
            return []

        # 2. Obtener canchas activas
        canchas_stmt = select(Cancha).where(
            Cancha.complejo_id == complejo_id,
            Cancha.activa == True,  # noqa: E712
        )
        if tipo_cancha:
            canchas_stmt = canchas_stmt.where(Cancha.tipo.ilike(f"%{tipo_cancha}%"))

        canchas_res = await self.session.execute(canchas_stmt)
        canchas = canchas_res.scalars().all()

        slots_disponibles: list[SlotDisponible] = []

        # 3. Para cada cancha, generar grilla y verificar reservas
        for cancha in canchas:
            # Obtener reservas activas para el día
            inicio_dia = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc)
            fin_dia = inicio_dia + timedelta(days=1)

            reservas_stmt = select(Reserva).where(
                Reserva.cancha_id == cancha.id,
                Reserva.estado == EstadoReserva.CONFIRMADA.value,
                Reserva.fecha_inicio >= inicio_dia,
                Reserva.fecha_inicio < fin_dia,
            )
            reservas_res = await self.session.execute(reservas_stmt)
            reservas_confirmadas = reservas_res.scalars().all()

            # Horas del complejo
            hora_actual_minutos = complejo.hora_apertura * 60
            hora_limite_minutos = complejo.hora_cierre * 60

            duracion = cancha.duracion_minutos
            while hora_actual_minutos + duracion <= hora_limite_minutos:
                h_inicio = hora_actual_minutos // 60
                m_inicio = hora_actual_minutos % 60

                slot_inicio_dt = datetime.combine(
                    target_date,
                    time(h_inicio, m_inicio),
                    tzinfo=timezone.utc,
                )
                slot_fin_dt = slot_inicio_dt + timedelta(minutes=duracion)

                # Verificar si se solapa con alguna reserva confirmada
                solapado = any(
                    reserva.fecha_inicio < slot_fin_dt and reserva.fecha_fin > slot_inicio_dt
                    for reserva in reservas_confirmadas
                )

                if not solapado:
                    slots_disponibles.append(
                        SlotDisponible(
                            cancha_id=cancha.id,
                            cancha_nombre=cancha.nombre,
                            tipo_cancha=cancha.tipo,
                            fecha=target_date.isoformat(),
                            hora_inicio=f"{h_inicio:02d}:{m_inicio:02d}",
                            hora_fin=f"{slot_fin_dt.hour:02d}:{slot_fin_dt.minute:02d}",
                            duracion_minutos=duracion,
                            precio=cancha.precio,
                        )
                    )

                hora_actual_minutos += duracion

        return slots_disponibles
