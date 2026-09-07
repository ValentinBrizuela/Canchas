from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.complejo import Complejo
    from src.models.reserva import Reserva


# Tipos de cancha y duraciones típicas por defecto para facilitar la creación
DEFAULT_FIELD_PRESETS = {
    "futbol_5": {"tipo": "Fútbol 5", "duracion_minutos": 60},
    "futbol_7": {"tipo": "Fútbol 7", "duracion_minutos": 60},
    "futbol_11": {"tipo": "Fútbol 11", "duracion_minutos": 90},
    "padel": {"tipo": "Pádel", "duracion_minutos": 90},
}


class Cancha(Base, TimestampMixin):
    """Modelo que representa una cancha dentro de un complejo deportivo."""

    __tablename__ = "canchas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complejo_id: Mapped[int] = mapped_column(
        ForeignKey("complejos.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, default="Fútbol 5")

    # Duración de cada turno en minutos (60, 90, etc.)
    duracion_minutos: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Tarifa fija por turno
    precio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    complejo: Mapped["Complejo"] = relationship("Complejo", back_populates="canchas")
    reservas: Mapped[list["Reserva"]] = relationship(
        "Reserva",
        back_populates="cancha",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Cancha id={self.id} nombre='{self.nombre}' tipo='{self.tipo}' "
            f"duracion={self.duracion_minutos}m precio={self.precio}>"
        )
