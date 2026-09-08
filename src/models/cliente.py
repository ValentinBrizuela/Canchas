from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.reserva import Reserva


class Cliente(Base, TimestampMixin):
    """Modelo que representa a un cliente/jugador que interactúa mediante Telegram."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relación con las reservas hechas por el cliente
    reservas: Mapped[list["Reserva"]] = relationship(
        "Reserva",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Cliente id={self.id} telegram_id={self.telegram_id} nombre='{self.nombre}'>"
