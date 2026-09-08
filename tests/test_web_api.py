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


@pytest.mark.asyncio
async def test_listar_crear_editar_y_toggle_canchas(web_client):
    client, complejo = web_client

    # 1. Listar canchas iniciales
    resp = await client.get("/api/v1/canchas")
    assert resp.status_code == 200
    canchas_list = resp.json()
    assert len(canchas_list) >= 3

    # 2. Crear una nueva cancha
    nueva_cancha_data = {
        "nombre": "Cancha 3 Pádel Panorámica",
        "tipo": "Pádel",
        "duracion_minutos": 90,
        "precio": 25000.0,
        "activa": True,
    }
    create_resp = await client.post("/api/v1/canchas", json=nueva_cancha_data)
    assert create_resp.status_code == 201
    nueva_cancha = create_resp.json()
    cancha_id = nueva_cancha["id"]
    assert nueva_cancha["nombre"] == "Cancha 3 Pádel Panorámica"
    assert nueva_cancha["duracion_minutos"] == 90
    assert nueva_cancha["precio"] == 25000.0
    assert nueva_cancha["activa"] is True

    # 3. Editar la cancha (cambiar nombre y precio)
    edit_data = {
        "nombre": "Cancha 3 Pádel Pro",
        "precio": 28000.0,
    }
    edit_resp = await client.put(f"/api/v1/canchas/{cancha_id}", json=edit_data)
    assert edit_resp.status_code == 200
    edit_json = edit_resp.json()
    assert edit_json["nombre"] == "Cancha 3 Pádel Pro"
    assert edit_json["precio"] == 28000.0
    assert edit_json["duracion_minutos"] == 90

    # 4. Desactivar la cancha mediante toggle
    toggle_resp = await client.patch(f"/api/v1/canchas/{cancha_id}/toggle")
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["activa"] is False

    # Verificar que la cancha inactiva no aparece en la agenda
    fecha_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    agenda_resp = await client.get(f"/api/v1/agenda?fecha={fecha_str}")
    assert agenda_resp.status_code == 200
    canchas_agenda_ids = [ca["cancha"]["id"] for ca in agenda_resp.json()["canchas_agenda"]]
    assert cancha_id not in canchas_agenda_ids

    # 5. Reactivar la cancha
    toggle_back_resp = await client.patch(f"/api/v1/canchas/{cancha_id}/toggle")
    assert toggle_back_resp.status_code == 200
    assert toggle_back_resp.json()["activa"] is True

    # Verificar que ahora sí aparece en la agenda
    agenda_resp2 = await client.get(f"/api/v1/agenda?fecha={fecha_str}")
    canchas_agenda_ids2 = [ca["cancha"]["id"] for ca in agenda_resp2.json()["canchas_agenda"]]
    assert cancha_id in canchas_agenda_ids2

