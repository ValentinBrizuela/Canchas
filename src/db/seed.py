import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import Cancha, Complejo, Usuario
from src.web.auth import hash_password

logger = logging.getLogger(__name__)


async def seed_initial_data(session: AsyncSession) -> Complejo:
    """Crea el complejo, canchas demo y usuario administrador por defecto si no existen."""
    settings = get_settings()

    stmt = select(Complejo).where(Complejo.slug == settings.DEFAULT_TENANT_SLUG)
    res = await session.execute(stmt)
    complejo = res.scalar_one_or_none()

    if not complejo:
        logger.info("Creando complejo demo: %s", settings.DEFAULT_TENANT_NAME)
        complejo = Complejo(
            slug=settings.DEFAULT_TENANT_SLUG,
            nombre=settings.DEFAULT_TENANT_NAME,
            direccion="Av. Libertador 1234",
            telefono="11-2345-6789",
            hora_apertura=9,
            hora_cierre=24,
        )
        session.add(complejo)
        await session.flush()

        # Crear canchas por defecto
        canchas_demo = [
            Cancha(
                complejo_id=complejo.id,
                nombre="Cancha 1 (Techada)",
                tipo="Fútbol 5",
                duracion_minutos=60,
                precio=22000.0,
            ),
            Cancha(
                complejo_id=complejo.id,
                nombre="Cancha 2 (Descubierta)",
                tipo="Fútbol 7",
                duracion_minutos=60,
                precio=30000.0,
            ),
            Cancha(
                complejo_id=complejo.id,
                nombre="Cancha de Pádel 1",
                tipo="Pádel",
                duracion_minutos=90,
                precio=24000.0,
            ),
        ]
        session.add_all(canchas_demo)
        await session.commit()
        await session.refresh(complejo)
        logger.info("Canchas demo creadas exitosamente.")

    # Verificar y crear usuario administrador por defecto si no existe
    user_stmt = select(Usuario).where(Usuario.username == "admin")
    res_user = await session.execute(user_stmt)
    admin_user = res_user.scalar_one_or_none()
    if not admin_user:
        logger.info("Creando usuario administrador inicial: admin")
        admin_user = Usuario(
            complejo_id=complejo.id,
            username="admin",
            email="admin@canchas.local",
            password_hash=hash_password(settings.ADMIN_DEFAULT_PASSWORD),
            nombre="Administrador Principal",
            rol="admin",
            activo=True,
        )
        session.add(admin_user)
        await session.commit()
        logger.info("Usuario administrador creado exitosamente.")

    return complejo

