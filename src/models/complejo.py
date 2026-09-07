from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.cancha import Cancha


class Complejo(Base, TimestampMixin):
    """Modelo multi-tenant que representa una sede o complejo deportivo."""

    __tablename__ = "complejos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Horarios comerciales de apertura y cierre (en formato hora 0-24)
    hora_apertura: Mapped[int] = mapped_column(Integer, default=9, nullable=False)
    hora_cierre: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relación con las canchas del complejo
    canchas: Mapped[list["Cancha"]] = relationship(
        "Cancha",
        back_populates="complejo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Complejo id={self.id} slug='{self.slug}' nombre='{self.nombre}'>"
