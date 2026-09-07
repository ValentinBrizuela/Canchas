from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cancha import Cancha
from src.models.cliente import Cliente
from src.models.reserva import EstadoReserva, Reserva


class BookingError(Exception):
    """Excepción base para errores del servicio de reservas."""
    pass


class CourtNotFoundError(BookingError):
    """La cancha indicada no existe o está inactiva."""
    pass


class SlotAlreadyBookedError(BookingError):
    """El turno solicitado ya se encuentra ocupado."""
    pass


class BookingNotFoundError(BookingError):
    """La reserva solicitada no fue encontrada."""
    pass


class BookingService:
    """Servicio para la creación, cancelación y administración de reservas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_cliente(
        self,
        telegram_id: int,
        nombre: str,
        telefono: str | None = None,
        username: str | None = None,
    ) -> Cliente:
        """Busca un cliente por su telegram_id o lo crea si es su primera interacción."""
        stmt = select(Cliente).where(Cliente.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        cliente = res.scalar_one_or_none()

        if not cliente:
            cliente = Cliente(
                telegram_id=telegram_id,
                nombre=nombre,
                telefono=telefono,
                username=username,
            )
            self.session.add(cliente)
            await self.session.flush()
        else:
            # Actualizar datos si cambiaron
            if nombre and cliente.nombre != nombre:
                cliente.nombre = nombre
            if telefono and cliente.telefono != telefono:
                cliente.telefono = telefono
            if username and cliente.username != username:
                cliente.username = username

        return cliente

    async def create_booking(
        self,
        cancha_id: int,
        fecha_inicio: datetime,
        telegram_id: int,
        cliente_nombre: str,
        cliente_telefono: str | None = None,
        cliente_username: str | None = None,
        notas: str | None = None,
    ) -> Reserva:
        """Crea una reserva asegurando que no haya colisiones de horario."""
        # 1. Obtener cancha
        cancha_stmt = select(Cancha).where(Cancha.id == cancha_id, Cancha.activa == True)  # noqa: E712
        cancha_res = await self.session.execute(cancha_stmt)
        cancha = cancha_res.scalar_one_or_none()
        if not cancha:
            raise CourtNotFoundError(f"La cancha #{cancha_id} no existe o no está activa.")

        fecha_fin = fecha_inicio + timedelta(minutes=cancha.duracion_minutos)

        # 2. Validación estricta anti-solapamiento
        colision_stmt = select(Reserva).where(
            Reserva.cancha_id == cancha_id,
            Reserva.estado == EstadoReserva.CONFIRMADA.value,
            Reserva.fecha_inicio < fecha_fin,
            Reserva.fecha_fin > fecha_inicio,
        )
        colision_res = await self.session.execute(colision_stmt)
        if colision_res.first():
            raise SlotAlreadyBookedError(
                f"El turno seleccionado ({fecha_inicio.strftime('%H:%M')} a {fecha_fin.strftime('%H:%M')}) "
                f"ya se encuentra reservado."
            )

        # 3. Obtener o crear cliente
        cliente = await self.get_or_create_cliente(
            telegram_id=telegram_id,
            nombre=cliente_nombre,
            telefono=cliente_telefono,
            username=cliente_username,
        )

        # 4. Crear la reserva
        reserva = Reserva(
            cancha_id=cancha.id,
            cliente_id=cliente.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoReserva.CONFIRMADA.value,
            precio=cancha.precio,
            notas=notas,
        )
        self.session.add(reserva)
        await self.session.commit()
        await self.session.refresh(reserva)

        return reserva
