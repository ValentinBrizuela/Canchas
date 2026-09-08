from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.complejo import Complejo


class Usuario(Base, TimestampMixin):
    """Modelo que representa a un usuario operador o administrador del panel web."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complejo_id: Mapped[int] = mapped_column(
        ForeignKey("complejos.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relación con el complejo
    complejo: Mapped["Complejo"] = relationship("Complejo")

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} username='{self.username}' rol='{self.rol}' activo={self.activo}>"
