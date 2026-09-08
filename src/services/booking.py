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
            Reserva.estado.in_([EstadoReserva.CONFIRMADA.value, EstadoReserva.BLOQUEADA.value]),
            Reserva.fecha_inicio < fecha_fin,
            Reserva.fecha_fin > fecha_inicio,
        )
        colision_res = await self.session.execute(colision_stmt)
        if colision_res.first():
            raise SlotAlreadyBookedError(
                f"El turno seleccionado ({fecha_inicio.strftime('%H:%M')} a {fecha_fin.strftime('%H:%M')}) "
                f"ya se encuentra reservado u ocupado."
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

    async def create_manual_booking(
        self,
        cancha_id: int,
        fecha_inicio: datetime,
        cliente_nombre: str,
        cliente_telefono: str | None = None,
        precio: float | None = None,
        notas: str | None = None,
    ) -> Reserva:
        """Crea una reserva manual desde el panel de administración web."""
        cancha_stmt = select(Cancha).where(Cancha.id == cancha_id, Cancha.activa == True)  # noqa: E712
        cancha_res = await self.session.execute(cancha_stmt)
        cancha = cancha_res.scalar_one_or_none()
        if not cancha:
            raise CourtNotFoundError(f"La cancha #{cancha_id} no existe o no está activa.")

        fecha_fin = fecha_inicio + timedelta(minutes=cancha.duracion_minutos)

        # Validación anti-solapamiento
        colision_stmt = select(Reserva).where(
            Reserva.cancha_id == cancha_id,
            Reserva.estado.in_([EstadoReserva.CONFIRMADA.value, EstadoReserva.BLOQUEADA.value]),
            Reserva.fecha_inicio < fecha_fin,
            Reserva.fecha_fin > fecha_inicio,
        )
        colision_res = await self.session.execute(colision_stmt)
        if colision_res.first():
            raise SlotAlreadyBookedError(
                f"El turno ({fecha_inicio.strftime('%H:%M')} a {fecha_fin.strftime('%H:%M')}) "
                f"ya está ocupado."
            )

        # Buscar cliente existente por teléfono o crear uno nuevo
        cliente = None
        if cliente_telefono:
            cliente_stmt = select(Cliente).where(Cliente.telefono == cliente_telefono)
            c_res = await self.session.execute(cliente_stmt)
            cliente = c_res.scalar_one_or_none()

        if not cliente:
            cliente = Cliente(
                telegram_id=None,
                nombre=cliente_nombre,
                telefono=cliente_telefono,
            )
            self.session.add(cliente)
            await self.session.flush()

        reserva = Reserva(
            cancha_id=cancha.id,
            cliente_id=cliente.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoReserva.CONFIRMADA.value,
            precio=precio if precio is not None else cancha.precio,
            notas=notas,
        )
        self.session.add(reserva)
        await self.session.commit()
        await self.session.refresh(reserva)
        return reserva

    async def bloquear_turno(
        self,
        cancha_id: int,
        fecha_inicio: datetime,
        motivo: str = "Mantenimiento",
    ) -> Reserva:
        """Bloquea un turno en la agenda impidiendo que sea reservado."""
        cancha_stmt = select(Cancha).where(Cancha.id == cancha_id, Cancha.activa == True)  # noqa: E712
        cancha_res = await self.session.execute(cancha_stmt)
        cancha = cancha_res.scalar_one_or_none()
        if not cancha:
            raise CourtNotFoundError(f"La cancha #{cancha_id} no existe o no está activa.")

        fecha_fin = fecha_inicio + timedelta(minutes=cancha.duracion_minutos)

        colision_stmt = select(Reserva).where(
            Reserva.cancha_id == cancha_id,
            Reserva.estado.in_([EstadoReserva.CONFIRMADA.value, EstadoReserva.BLOQUEADA.value]),
            Reserva.fecha_inicio < fecha_fin,
            Reserva.fecha_fin > fecha_inicio,
        )
        colision_res = await self.session.execute(colision_stmt)
        if colision_res.first():
            raise SlotAlreadyBookedError(
                f"No se puede bloquear: ya existe una reserva o bloqueo en ese horario."
            )

        bloqueo = Reserva(
            cancha_id=cancha.id,
            cliente_id=None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoReserva.BLOQUEADA.value,
            precio=0.0,
            notas=motivo,
        )
        self.session.add(bloqueo)
        await self.session.commit()
        await self.session.refresh(bloqueo)
        return bloqueo

    async def desbloquear_turno(self, reserva_id: int) -> Reserva:
        """Elimina o cancela un bloqueo activo."""
        stmt = select(Reserva).where(
            Reserva.id == reserva_id,
            Reserva.estado == EstadoReserva.BLOQUEADA.value,
        )
        res = await self.session.execute(stmt)
        bloqueo = res.scalar_one_or_none()
        if not bloqueo:
            raise BookingNotFoundError(f"No se encontró un bloqueo activo con ID #{reserva_id}.")

        bloqueo.estado = EstadoReserva.CANCELADA.value
        await self.session.commit()
        await self.session.refresh(bloqueo)
        return bloqueo

    async def get_customer_bookings(
        self,
        telegram_id: int,
        only_active: bool = True,
    ) -> list[Reserva]:
        """Retorna las reservas asociadas a un cliente por su telegram_id."""
        stmt = (
            select(Reserva)
            .join(Reserva.cliente)
            .where(Cliente.telegram_id == telegram_id)
            .order_by(Reserva.fecha_inicio.asc())
        )
        if only_active:
            stmt = stmt.where(Reserva.estado == EstadoReserva.CONFIRMADA.value)

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def cancel_booking(
        self,
        reserva_id: int,
        telegram_id: int | None = None,
    ) -> Reserva:
        """Cancela una reserva activa verificando titularidad si se pasa telegram_id."""
        stmt = select(Reserva).where(Reserva.id == reserva_id)
        res = await self.session.execute(stmt)
        reserva = res.scalar_one_or_none()

        if not reserva:
            raise BookingNotFoundError(f"No se encontró la reserva #{reserva_id}.")

        if telegram_id is not None:
            # Cargar cliente para validar titularidad
            cliente_stmt = select(Cliente).where(Cliente.id == reserva.cliente_id)
            cliente_res = await self.session.execute(cliente_stmt)
            cliente = cliente_res.scalar_one_or_none()
            if not cliente or cliente.telegram_id != telegram_id:
                raise BookingError("No tienes permiso para cancelar esta reserva.")

        if reserva.estado == EstadoReserva.CANCELADA.value:
            raise BookingError("La reserva ya se encontraba cancelada.")

        reserva.estado = EstadoReserva.CANCELADA.value
        await self.session.commit()
        await self.session.refresh(reserva)

        return reserva


