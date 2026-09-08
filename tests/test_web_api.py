"""Pruebas para los endpoints de la API REST del Panel Web."""
from datetime import datetime, time, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.seed import seed_initial_data
from src.db.session import get_db
from src.web.app import create_web_app


@pytest.fixture
async def web_client(db_session: AsyncSession):
    """Cliente HTTP asíncrono para probar los endpoints de FastAPI con DB de prueba."""
    # Poblar datos iniciales
    complejo = await seed_initial_data(db_session)

    app = create_web_app()

    # Sobrescribir dependencia get_db para usar la sesión de test
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, complejo


@pytest.mark.asyncio
async def test_health_endpoint(web_client):
    client, _ = web_client
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "canchas-saas"}


@pytest.mark.asyncio
async def test_root_and_static_files(web_client):
    client, _ = web_client
    # Debe servir el index.html
    root_resp = await client.get("/")
    assert root_resp.status_code == 200
    assert "Canchas SaaS" in root_resp.text

    # Debe servir el archivo CSS
    css_resp = await client.get("/static/css/dashboard.css")
    assert css_resp.status_code == 200
    assert "--bg-body" in css_resp.text


@pytest.mark.asyncio
async def test_get_complejo(web_client):
    client, complejo = web_client
    response = await client.get("/api/v1/complejo")
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == complejo.nombre
    assert len(data["canchas"]) >= 3


@pytest.mark.asyncio
async def test_get_agenda_and_kpis(web_client):
    client, _ = web_client
    fecha_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    response = await client.get(f"/api/v1/agenda?fecha={fecha_str}")
    assert response.status_code == 200
    data = response.json()
    assert data["fecha"] == fecha_str
    assert len(data["canchas_agenda"]) >= 3

    # Todos los slots deben estar libres inicialmente
    first_cancha = data["canchas_agenda"][0]
    assert len(first_cancha["slots"]) > 0
    assert all(s["estado"] == "libre" for s in first_cancha["slots"])

    # KPIs iniciales
    kpi_resp = await client.get(f"/api/v1/kpis?fecha={fecha_str}")
    assert kpi_resp.status_code == 200
    kpi_data = kpi_resp.json()
    assert kpi_data["reservas_hoy"] == 0
    assert kpi_data["ingresos_hoy"] == 0.0


@pytest.mark.asyncio
async def test_crear_y_cancelar_reserva_manual(web_client):
    client, complejo = web_client
    cancha = complejo.canchas[0]
    target_dt = datetime.now(timezone.utc).replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # 1. Crear reserva manual desde la web
    payload = {
        "cancha_id": cancha.id,
        "fecha_inicio": target_dt.isoformat(),
        "cliente_nombre": "Carlos Mostrador",
        "cliente_telefono": "+5491100001111",
        "precio": cancha.precio,
        "notas": "Reserva telefónica",
    }
    resp = await client.post("/api/v1/reservas", json=payload)
    assert resp.status_code == 201
    reserva_data = resp.json()
    reserva_id = reserva_data["id"]
    assert reserva_data["estado"] == "confirmada"

    # 2. Consultar agenda para esa fecha y verificar estado
    fecha_str = target_dt.strftime("%Y-%m-%d")
    agenda_resp = await client.get(f"/api/v1/agenda?fecha={fecha_str}")
    assert agenda_resp.status_code == 200
    agenda_data = agenda_resp.json()
    cancha_agenda = next(ca for ca in agenda_data["canchas_agenda"] if ca["cancha"]["id"] == cancha.id)
    slot_reservado = next((s for s in cancha_agenda["slots"] if s["reserva_id"] == reserva_id), None)
    assert slot_reservado is not None
    assert slot_reservado["estado"] == "confirmada"
    assert slot_reservado["cliente_nombre"] == "Carlos Mostrador"

    # 3. Cancelar reserva
    cancel_resp = await client.post(f"/api/v1/reservas/{reserva_id}/cancelar")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["estado"] == "cancelada"


@pytest.mark.asyncio
async def test_bloquear_y_desbloquear_turno(web_client):
    client, complejo = web_client
    cancha = complejo.canchas[0]
    target_dt = datetime.now(timezone.utc).replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=2)

    # 1. Bloquear turno
    bloqueo_payload = {
        "cancha_id": cancha.id,
        "fecha_inicio": target_dt.isoformat(),
        "motivo": "Mantenimiento césped",
    }
    resp = await client.post("/api/v1/bloqueos", json=bloqueo_payload)
    assert resp.status_code == 201
    bloqueo_id = resp.json()["id"]
    assert resp.json()["estado"] == "bloqueada"

    # 2. Intentar reservar en el horario bloqueado (debe fallar 409 Conflict)
    reserva_payload = {
        "cancha_id": cancha.id,
        "fecha_inicio": target_dt.isoformat(),
        "cliente_nombre": "Intento Reserva",
    }
    resp_conflict = await client.post("/api/v1/reservas", json=reserva_payload)
    assert resp_conflict.status_code == 409

    # 3. Desbloquear turno
    resp_unblock = await client.post(f"/api/v1/bloqueos/{bloqueo_id}/desbloquear")
    assert resp_unblock.status_code == 200
    assert resp_unblock.json()["estado"] == "cancelada"
