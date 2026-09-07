from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from src.db.session import create_engine_and_session, init_db
from src.models import Cancha, Cliente, Complejo, EstadoReserva, Reserva


@pytest.fixture
async def db_session():
    engine, session_factory = create_engine_and_session("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_complejo_and_canchas(db_session):
    complejo = Complejo(
        slug="maracana-futbol",
        nombre="Complejo Maracaná",
        hora_apertura=10,
        hora_cierre=23,
    )
    db_session.add(complejo)
    await db_session.commit()
    await db_session.refresh(complejo)

    assert complejo.id is not None
    assert complejo.slug == "maracana-futbol"
    assert complejo.hora_apertura == 10

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha Techada 1",
        tipo="Fútbol 5",
        duracion_minutos=60,
        precio=25000.0,
    )
    db_session.add(cancha)
    await db_session.commit()
    await db_session.refresh(cancha)

    assert cancha.id is not None
    assert cancha.duracion_minutos == 60
    assert cancha.precio == 25000.0
    assert cancha.complejo_id == complejo.id


@pytest.mark.asyncio
async def test_create_cliente_and_reserva(db_session):
    complejo = Complejo(slug="sede-central", nombre="Sede Central")
    db_session.add(complejo)
    await db_session.flush()

    cancha = Cancha(
        complejo_id=complejo.id,
        nombre="Cancha F7",
        tipo="Fútbol 7",
        duracion_minutos=60,
        precio=30000.0,
    )
    cliente = Cliente(
        telegram_id=987654321,
        nombre="Juan Pérez",
        telefono="1122334455",
        username="juanperez",
    )
    db_session.add_all([cancha, cliente])
    await db_session.flush()

    ahora = datetime.now(timezone.utc)
    reserva = Reserva(
        cancha_id=cancha.id,
        cliente_id=cliente.id,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(minutes=cancha.duracion_minutos),
        estado=EstadoReserva.CONFIRMADA.value,
        precio=cancha.precio,
        notas="Reserva confirmada por bot",
    )
    db_session.add(reserva)
    await db_session.commit()
    await db_session.refresh(reserva)

    assert reserva.id is not None
    assert reserva.estado == EstadoReserva.CONFIRMADA.value
    assert reserva.precio == 30000.0

    # Verificar consultas con relaciones
    stmt = select(Reserva).where(Reserva.id == reserva.id)
    resultado = await db_session.execute(stmt)
    reserva_cargada = resultado.scalar_one()

    assert reserva_cargada.cancha.nombre == "Cancha F7"
    assert reserva_cargada.cliente.nombre == "Juan Pérez"
