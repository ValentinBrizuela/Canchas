"""Esquemas Pydantic para el API REST del panel de administración."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CanchaOut(BaseModel):
    id: int
    nombre: str
    tipo: str
    duracion_minutos: int
    precio: float
    activa: bool

    model_config = ConfigDict(from_attributes=True)


class CanchaCreateIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    tipo: str = Field(..., min_length=2, max_length=50)
    duracion_minutos: int = Field(60, ge=15, le=240)
    precio: float = Field(..., ge=0)
    activa: bool = Field(True)


class CanchaUpdateIn(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=100)
    tipo: str | None = Field(None, min_length=2, max_length=50)
    duracion_minutos: int | None = Field(None, ge=15, le=240)
    precio: float | None = Field(None, ge=0)
    activa: bool | None = None


class ComplejoOut(BaseModel):
    id: int
    slug: str
    nombre: str
    direccion: str | None
    telefono: str | None
    hora_apertura: int
    hora_cierre: int
    activo: bool
    canchas: list[CanchaOut] = []

    model_config = ConfigDict(from_attributes=True)


class SlotAgendaOut(BaseModel):
    hora_inicio: str  # HH:MM
    hora_fin: str     # HH:MM
    fecha_inicio_iso: str
    fecha_fin_iso: str
    cancha_id: int
    estado: str       # "libre", "confirmada", "bloqueada"
    reserva_id: int | None = None
    cliente_nombre: str | None = None
    cliente_telefono: str | None = None
    precio: float
    notas: str | None = None


class CanchaAgendaOut(BaseModel):
    cancha: CanchaOut
    slots: list[SlotAgendaOut]


class AgendaResponse(BaseModel):
    fecha: str  # YYYY-MM-DD
    complejo: ComplejoOut
    canchas_agenda: list[CanchaAgendaOut]


class ReservaManualIn(BaseModel):
    cancha_id: int
    fecha_inicio: datetime
    cliente_nombre: str = Field(..., min_length=2, max_length=100)
    cliente_telefono: str | None = Field(None, max_length=50)
    precio: float | None = None
    notas: str | None = Field(None, max_length=255)


class ReservaOut(BaseModel):
    id: int
    cancha_id: int
    cliente_id: int | None
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str
    precio: float
    notas: str | None

    model_config = ConfigDict(from_attributes=True)


class BloqueoIn(BaseModel):
    cancha_id: int
    fecha_inicio: datetime
    motivo: str = Field("Mantenimiento", max_length=255)


class KpiStatsOut(BaseModel):
    fecha: str
    total_canchas: int
    reservas_hoy: int
    bloqueos_hoy: int
    total_slots: int
    ocupacion_pct: float
    ingresos_hoy: float


class LoginIn(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre: str
    rol: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut

