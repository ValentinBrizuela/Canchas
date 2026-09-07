from datetime import date, datetime, time, timedelta, timezone
import pytest
from src.db.session import create_engine_and_session, init_db
from src.models import Cancha, Complejo, EstadoReserva, Reserva, Cliente
from src.services.availability import AvailabilityService


@pytest.fixture
async def db_session():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_slot_generation_and_filtering_busy_slots(db_session):
    # Complejo abre de 18 a 22 (4 horas)
    complejo = Complejo(
        slug="test-slots",
        nombre="Club San Martín",
        hora_apertura=18,
        hora_cierre=22,
    )
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha F5",
        tipo="Fútbol 5",
        duracion_minutos=60,
        precio=20000.0,
    )
    cliente = Cliente(
        telegram_id=12345,
        nombre="Carlos",
    )
    db_session.add_all([cancha, cliente])
    await db_session.flush()

    service = AvailabilityService(db_session)
    hoy = date(2026, 9, 10)

    # 1. Sin reservas: debe haber 4 turnos (18:00, 19:00, 20:00, 21:00)
    slots = await service.get_available_slots(complejo.id, hoy)
    assert len(slots) == 4
    assert [s.hora_inicio for s in slots] == ["18:00", "19:00", "20:00", "21:00"]

    # 2. Agregar reserva a las 19:00
    reserva = Reserva(
        cancha_id=cancha.id,
        cliente_id=cliente.id,
        fecha_inicio=datetime.combine(hoy, time(19, 0), tzinfo=timezone.utc),
        fecha_fin=datetime.combine(hoy, time(20, 0), tzinfo=timezone.utc),
        estado=EstadoReserva.CONFIRMADA.value,
        precio=20000.0,
    )
    db_session.add(reserva)
    await db_session.commit()

    # 3. Consultar nuevamente: el turno de las 19:00 ya no debe figurar
    slots_despues = await service.get_available_slots(complejo.id, hoy)
    assert len(slots_despues) == 3
    assert [s.hora_inicio for s in slots_despues] == ["18:00", "20:00", "21:00"]


@pytest.mark.asyncio
async def test_filter_by_field_type(db_session):
    complejo = Complejo(
        slug="multi-deporte",
        nombre="Multi Deporte",
        hora_apertura=18,
        hora_cierre=20,
    )
    db_session.add(complejo)
    await db_session.flush()

    cancha_f5 = Cancha(
        complejo_id=complejo.id,
        nombre="Fútbol 5",
        tipo="Fútbol 5",
        duracion_minutos=60,
    )
    cancha_padel = Cancha(
        complejo_id=complejo.id,
        nombre="Pádel Cristal",
        tipo="Pádel",
        duracion_minutos=60,
    )
    db_session.add_all([cancha_f5, cancha_padel])
    await db_session.commit()

    service = AvailabilityService(db_session)
    hoy = date(2026, 9, 10)

    # Filtrar solo Pádel
    slots_padel = await service.get_available_slots(complejo.id, hoy, tipo_cancha="Pádel")
    assert len(slots_padel) == 2
    assert all(s.tipo_cancha == "Pádel" for s in slots_padel)
