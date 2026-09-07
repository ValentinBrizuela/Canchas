from datetime import datetime, timedelta, timezone
import pytest
from src.db.session import create_engine_and_session, init_db
from src.models import Cancha, Complejo, EstadoReserva
from src.services.booking import (
    BookingError,
    BookingNotFoundError,
    BookingService,
    CourtNotFoundError,
    SlotAlreadyBookedError,
)


@pytest.fixture
async def db_session():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_booking_success_and_anticollision(db_session):
    complejo = Complejo(slug="sede-norte", nombre="Sede Norte")
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha 1",
        tipo="Fútbol 5",
        duracion_minutos=60,
        precio=22000.0,
    )
    db_session.add(cancha)
    await db_session.commit()

    service = BookingService(db_session)
    ahora = datetime.now(timezone.utc).replace(microsecond=0)

    # 1. Crear reserva exitosa
    reserva = await service.create_booking(
        cancha_id=cancha.id,
        fecha_inicio=ahora,
        telegram_id=111222,
        cliente_nombre="Martín Palermo",
        cliente_telefono="1144556677",
    )
    assert reserva.id is not None
    assert reserva.precio == 22000.0
    assert reserva.fecha_fin == ahora + timedelta(minutes=60)
    assert reserva.estado == EstadoReserva.CONFIRMADA.value

    # 2. Intentar reservar el mismo horario exacto -> Error de colisión
    with pytest.raises(SlotAlreadyBookedError):
        await service.create_booking(
            cancha_id=cancha.id,
            fecha_inicio=ahora,
            telegram_id=999888,
            cliente_nombre="Román Riquelme",
        )

    # 3. Intentar reservar un horario solapado (30 minutos después) -> Error de colisión
    with pytest.raises(SlotAlreadyBookedError):
        await service.create_booking(
            cancha_id=cancha.id,
            fecha_inicio=ahora + timedelta(minutes=30),
            telegram_id=999888,
            cliente_nombre="Román Riquelme",
        )

    # 4. Cancha inexistente -> CourtNotFoundError
    with pytest.raises(CourtNotFoundError):
        await service.create_booking(
            cancha_id=9999,
            fecha_inicio=ahora,
            telegram_id=111222,
            cliente_nombre="Martín",
        )


@pytest.mark.asyncio
async def test_customer_bookings_and_cancellation(db_session):
    complejo = Complejo(slug="sede-sur", nombre="Sede Sur")
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha 2",
        tipo="Fútbol 7",
        duracion_minutos=60,
    )
    db_session.add(cancha)
    await db_session.commit()

    service = BookingService(db_session)
    ahora = datetime.now(timezone.utc).replace(microsecond=0)

    # Crear reserva para cliente 1
    reserva = await service.create_booking(
        cancha_id=cancha.id,
        fecha_inicio=ahora,
        telegram_id=55555,
        cliente_nombre="Lionel Messi",
    )

    # Listar reservas activas
    reservas_cliente = await service.get_customer_bookings(telegram_id=55555)
    assert len(reservas_cliente) == 1
    assert reservas_cliente[0].id == reserva.id

    # Intentar cancelar con otro telegram_id -> Error de permiso
    with pytest.raises(BookingError, match="No tienes permiso"):
        await service.cancel_booking(reserva_id=reserva.id, telegram_id=99999)

    # Cancelar correctamente
    reserva_cancelada = await service.cancel_booking(reserva_id=reserva.id, telegram_id=55555)
    assert reserva_cancelada.estado == EstadoReserva.CANCELADA.value

    # Verificar que ya no figura en reservas activas
    reservas_activas = await service.get_customer_bookings(telegram_id=55555, only_active=True)
    assert len(reservas_activas) == 0

    # Inexistente
    with pytest.raises(BookingNotFoundError):
        await service.cancel_booking(reserva_id=88888)
