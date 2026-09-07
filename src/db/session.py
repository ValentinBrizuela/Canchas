from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import get_settings


class UTCDateTime(TypeDecorator):
    """Garantiza que los datetimes se almacenen y recuperen con tzinfo=timezone.utc."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos de SQLAlchemy."""
    pass


class TimestampMixin:
    """Mixin que añade marcas de tiempo creadas y actualizadas en UTC."""

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def create_engine_and_session(database_url: str | None = None) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Crea el engine async y la fábrica de sesiones para la base de datos."""
    settings = get_settings()
    url = database_url or settings.DATABASE_URL

    # Argumentos específicos para SQLite en modo async
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}

    engine = create_async_engine(
        url,
        echo=False,
        connect_args=connect_args,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    return engine, session_factory


# Instancias por defecto de la aplicación
engine, async_session = create_engine_and_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador asíncrono para inyectar o manejar la sesión de base de datos."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """Crea todas las tablas registradas en la metadata de Base."""
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
