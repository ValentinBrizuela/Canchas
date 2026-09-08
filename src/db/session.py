from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import os
from pathlib import Path
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

    # Si es SQLite con ruta de archivo relativa/absoluta, asegurar que la carpeta exista
    if "sqlite" in url and "///" in url and ":memory:" not in url:
        db_path = url.split("///")[1]
        parent_dir = Path(db_path).parent
        if str(parent_dir) not in ("", "."):
            parent_dir.mkdir(parents=True, exist_ok=True)

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


def _migrate_sqlite_schema(connection) -> None:
    """Aplica migraciones ligeras para SQLite para asegurar compatibilidad de columnas nullables."""
    if connection.dialect.name != "sqlite":
        return

    # 1. Migrar clientes.telegram_id si tiene NOT NULL
    res_clientes = connection.exec_driver_sql("PRAGMA table_info(clientes)").fetchall()
    info_clientes = {row[1]: row for row in res_clientes}
    if "telegram_id" in info_clientes and info_clientes["telegram_id"][3] == 1:
        connection.exec_driver_sql("PRAGMA foreign_keys=off")
        connection.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS clientes_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
                telegram_id BIGINT, 
                nombre VARCHAR(100) NOT NULL, 
                telefono VARCHAR(50), 
                username VARCHAR(100), 
                created_at DATETIME NOT NULL, 
                updated_at DATETIME NOT NULL
            )
        """)
        connection.exec_driver_sql(
            "INSERT INTO clientes_new SELECT id, telegram_id, nombre, telefono, username, created_at, updated_at FROM clientes"
        )
        connection.exec_driver_sql("DROP TABLE clientes")
        connection.exec_driver_sql("ALTER TABLE clientes_new RENAME TO clientes")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_clientes_telegram_id ON clientes (telegram_id)")
        connection.exec_driver_sql("PRAGMA foreign_keys=on")

    # 2. Migrar reservas.cliente_id si tiene NOT NULL
    res_reservas = connection.exec_driver_sql("PRAGMA table_info(reservas)").fetchall()
    info_reservas = {row[1]: row for row in res_reservas}
    if "cliente_id" in info_reservas and info_reservas["cliente_id"][3] == 1:
        connection.exec_driver_sql("PRAGMA foreign_keys=off")
        connection.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS reservas_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
                cancha_id INTEGER NOT NULL, 
                cliente_id INTEGER, 
                fecha_inicio DATETIME NOT NULL, 
                fecha_fin DATETIME NOT NULL, 
                estado VARCHAR(20) NOT NULL, 
                precio FLOAT NOT NULL, 
                notas VARCHAR(255), 
                created_at DATETIME NOT NULL, 
                updated_at DATETIME NOT NULL, 
                FOREIGN KEY(cancha_id) REFERENCES canchas (id) ON DELETE CASCADE, 
                FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
            )
        """)
        connection.exec_driver_sql(
            "INSERT INTO reservas_new SELECT id, cancha_id, cliente_id, fecha_inicio, fecha_fin, estado, precio, notas, created_at, updated_at FROM reservas"
        )
        connection.exec_driver_sql("DROP TABLE reservas")
        connection.exec_driver_sql("ALTER TABLE reservas_new RENAME TO reservas")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_reservas_cancha_id ON reservas (cancha_id)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_reservas_cliente_id ON reservas (cliente_id)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_reservas_fecha_inicio ON reservas (fecha_inicio)")
        connection.exec_driver_sql("PRAGMA foreign_keys=on")



async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """Crea todas las tablas registradas en la metadata de Base y ejecuta migraciones."""
    import src.models  # noqa: F401
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite_schema)

