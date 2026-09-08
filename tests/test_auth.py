"""Pruebas para el sistema de autenticación, hash de contraseñas y JWT."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.seed import seed_initial_data
from src.db.session import get_db
from src.web.app import create_web_app
from src.web.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    """Verifica que el hashing PBKDF2 con sal funcione y valide contraseñas."""
    password = "MiClaveSecreta123!"
    hashed = hash_password(password)

    # Debe tener formato pbkdf2_sha256$iterations$salt$hash
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(password, hashed) is True
    assert verify_password("ClaveErronea", hashed) is False

    # Dos hashes para la misma contraseña deben ser distintos por la sal aleatoria
    hashed2 = hash_password(password)
    assert hashed != hashed2
    assert verify_password(password, hashed2) is True


def test_jwt_token_flow():
    """Verifica la generación y decodificación de tokens JWT."""
    token = create_access_token(data={"sub": "admin", "rol": "admin"})
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "admin"
    assert payload["rol"] == "admin"
    assert "exp" in payload


@pytest.fixture
async def unauthenticated_client(db_session: AsyncSession):
    """Cliente HTTP sin dependencias de usuario sobrescritas para probar autenticación real."""
    await seed_initial_data(db_session)
    app = create_web_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_login_success(unauthenticated_client):
    """Verifica inicio de sesión exitoso con credenciales por defecto (admin/admin123)."""
    resp = await unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["rol"] == "admin"


@pytest.mark.asyncio
async def test_login_invalid_password(unauthenticated_client):
    """Verifica que contraseña incorrecta retorne 401."""
    resp = await unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password_incorrecto"},
    )
    assert resp.status_code == 401
    assert "Usuario o contraseña incorrectos" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(unauthenticated_client):
    """Verifica que usuario inexistente retorne 401."""
    resp = await unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "usuario_fantasma", "password": "cualquier_clave"},
    )
    assert resp.status_code == 401
    assert "Usuario o contraseña incorrectos" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_protected_routes_require_token(unauthenticated_client):
    """Verifica que rutas protegidas rechacen solicitudes sin cabecera Authorization."""
    # Intentar acceder a complejo sin token
    resp = await unauthenticated_client.get("/api/v1/complejo")
    assert resp.status_code == 401

    # Intentar acceder a me sin token
    resp_me = await unauthenticated_client.get("/api/v1/auth/me")
    assert resp_me.status_code == 401

    # Intentar acceder a agenda sin token
    resp_agenda = await unauthenticated_client.get("/api/v1/agenda?fecha=2026-09-08")
    assert resp_agenda.status_code == 401


@pytest.mark.asyncio
async def test_protected_routes_with_valid_token(unauthenticated_client):
    """Verifica que el flujo completo login -> Bearer token -> endpoint protegido funcione."""
    # 1. Login
    login_resp = await unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Consultar perfil actual (/auth/me)
    me_resp = await unauthenticated_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["username"] == "admin"
    assert user_data["nombre"] == "Administrador Principal"

    # 3. Consultar complejo
    complejo_resp = await unauthenticated_client.get("/api/v1/complejo", headers=headers)
    assert complejo_resp.status_code == 200
    assert "nombre" in complejo_resp.json()
