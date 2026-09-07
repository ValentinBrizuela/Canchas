from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin, UTCDateTime

if TYPE_CHECKING:
    from src.models.cancha import Cancha
    from src.models.cliente import Cliente


class EstadoReserva(str, Enum):
    """Estados posibles para una reserva."""
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    COMPLETADA = "completada"


class Reserva(Base, TimestampMixin):
    """Modelo que representa una reserva de turno para una cancha."""

    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cancha_id: Mapped[int] = mapped_column(
        ForeignKey("canchas.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Franja horaria del turno (en timezone consciente, UTC recomendado)
    fecha_inicio: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        index=True,
        nullable=False,
    )
    fecha_fin: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        default=EstadoReserva.CONFIRMADA.value,
        nullable=False,
    )

    # Precio acordado al momento de reservar
    precio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Observaciones o notas adicionales
    notas: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relaciones
    cancha: Mapped["Cancha"] = relationship("Cancha", back_populates="reservas")
    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="reservas")

    def __repr__(self) -> str:
        return (
            f"<Reserva id={self.id} cancha_id={self.cancha_id} cliente_id={self.cliente_id} "
            f"inicio='{self.fecha_inicio}' estado='{self.estado}'>"
        )
