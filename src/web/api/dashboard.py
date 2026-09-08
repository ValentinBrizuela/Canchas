"""Rutas de API REST para el panel de administración de canchas."""
from datetime import date, datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.db.session import get_db
from src.models.cancha import Cancha
from src.models.complejo import Complejo
from src.models.reserva import EstadoReserva, Reserva
from src.services.booking import (
    BookingError,
    BookingNotFoundError,
    BookingService,
    CourtNotFoundError,
    SlotAlreadyBookedError,
)
from src.web.schemas import (
    AgendaResponse,
    BloqueoIn,
    CanchaAgendaOut,
    CanchaOut,
    ComplejoOut,
    KpiStatsOut,
    ReservaManualIn,
    ReservaOut,
    SlotAgendaOut,
)

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


async def get_active_complejo(session: AsyncSession) -> Complejo:
    settings = get_settings()
    stmt = (
        select(Complejo)
        .options(selectinload(Complejo.canchas))
        .where(Complejo.slug == settings.DEFAULT_TENANT_SLUG, Complejo.activo == True)  # noqa: E712
    )
    res = await session.execute(stmt)
    complejo = res.scalar_one_or_none()
    if not complejo:
        # Fallback al primer complejo activo
        fallback_stmt = select(Complejo).options(selectinload(Complejo.canchas)).where(Complejo.activo == True)  # noqa: E712
        res_fb = await session.execute(fallback_stmt)
        complejo = res_fb.scalar_one_or_none()

    if not complejo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún complejo activo configurado.",
        )
    return complejo


@router.get("/complejo", response_model=ComplejoOut)
async def get_complejo_actual(session: AsyncSession = Depends(get_db)):
    """Retorna información del complejo deportivo activo y sus canchas."""
    complejo = await get_active_complejo(session)
    return complejo


@router.get("/agenda", response_model=AgendaResponse)
async def get_agenda(
    fecha: str | None = Query(None, description="Fecha a consultar en formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db),
):
    """Retorna la matriz completa de turnos por cancha para la fecha especificada."""
    complejo = await get_active_complejo(session)

    if fecha:
        try:
            target_date = date.fromisoformat(fecha)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")
    else:
        target_date = datetime.now(timezone.utc).date()

    inicio_dia = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc)
    fin_dia = inicio_dia + timedelta(days=1)

    # Filtrar solo canchas activas
    canchas_activas = [c for c in complejo.canchas if c.activa]

    canchas_agenda: list[CanchaAgendaOut] = []

    for cancha in canchas_activas:
        # Consultar reservas del día para esta cancha
        reservas_stmt = (
            select(Reserva)
            .options(selectinload(Reserva.cliente))
            .where(
                Reserva.cancha_id == cancha.id,
                Reserva.estado.in_([EstadoReserva.CONFIRMADA.value, EstadoReserva.BLOQUEADA.value]),
                Reserva.fecha_inicio >= inicio_dia,
                Reserva.fecha_inicio < fin_dia,
            )
        )
        res = await session.execute(reservas_stmt)
        reservas_dia = res.scalars().all()

        slots: list[SlotAgendaOut] = []
        hora_actual_minutos = complejo.hora_apertura * 60
        hora_limite_minutos = complejo.hora_cierre * 60
        duracion = cancha.duracion_minutos

        while hora_actual_minutos + duracion <= hora_limite_minutos:
            h_inicio = hora_actual_minutos // 60
            m_inicio = hora_actual_minutos % 60

            slot_inicio_dt = datetime.combine(
                target_date,
                time(h_inicio, m_inicio),
                tzinfo=timezone.utc,
            )
            slot_fin_dt = slot_inicio_dt + timedelta(minutes=duracion)

            # Buscar si existe reserva o bloqueo en este slot
            reserva_solapada = next(
                (r for r in reservas_dia if r.fecha_inicio < slot_fin_dt and r.fecha_fin > slot_inicio_dt),
                None,
            )

            if reserva_solapada:
                if reserva_solapada.estado == EstadoReserva.CONFIRMADA.value:
                    slots.append(
                        SlotAgendaOut(
                            hora_inicio=f"{h_inicio:02d}:{m_inicio:02d}",
                            hora_fin=f"{slot_fin_dt.hour:02d}:{slot_fin_dt.minute:02d}",
                            fecha_inicio_iso=slot_inicio_dt.isoformat(),
                            fecha_fin_iso=slot_fin_dt.isoformat(),
                            cancha_id=cancha.id,
                            estado="confirmada",
                            reserva_id=reserva_solapada.id,
                            cliente_nombre=reserva_solapada.cliente.nombre if reserva_solapada.cliente else "Cliente Manual",
                            cliente_telefono=reserva_solapada.cliente.telefono if reserva_solapada.cliente else None,
                            precio=reserva_solapada.precio,
                            notas=reserva_solapada.notas,
                        )
                    )
                else:  # EstadoReserva.BLOQUEADA
                    slots.append(
                        SlotAgendaOut(
                            hora_inicio=f"{h_inicio:02d}:{m_inicio:02d}",
                            hora_fin=f"{slot_fin_dt.hour:02d}:{slot_fin_dt.minute:02d}",
                            fecha_inicio_iso=slot_inicio_dt.isoformat(),
                            fecha_fin_iso=slot_fin_dt.isoformat(),
                            cancha_id=cancha.id,
                            estado="bloqueada",
                            reserva_id=reserva_solapada.id,
                            cliente_nombre=None,
                            cliente_telefono=None,
                            precio=0.0,
                            notas=reserva_solapada.notas or "Mantenimiento / Bloqueo",
                        )
                    )
            else:
                slots.append(
                    SlotAgendaOut(
                        hora_inicio=f"{h_inicio:02d}:{m_inicio:02d}",
                        hora_fin=f"{slot_fin_dt.hour:02d}:{slot_fin_dt.minute:02d}",
                        fecha_inicio_iso=slot_inicio_dt.isoformat(),
                        fecha_fin_iso=slot_fin_dt.isoformat(),
                        cancha_id=cancha.id,
                        estado="libre",
                        reserva_id=None,
                        cliente_nombre=None,
                        cliente_telefono=None,
                        precio=cancha.precio,
                        notas=None,
                    )
                )

            hora_actual_minutos += duracion

        canchas_agenda.append(
            CanchaAgendaOut(
                cancha=CanchaOut.model_validate(cancha),
                slots=slots,
            )
        )

    return AgendaResponse(
        fecha=target_date.isoformat(),
        complejo=ComplejoOut.model_validate(complejo),
        canchas_agenda=canchas_agenda,
    )


@router.get("/kpis", response_model=KpiStatsOut)
async def get_kpis(
    fecha: str | None = Query(None, description="Fecha a consultar en formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db),
):
    """Calcula las métricas e indicadores de rendimiento clave para el día."""
    agenda = await get_agenda(fecha=fecha, session=session)

    total_canchas = len(agenda.canchas_agenda)
    reservas_hoy = 0
    bloqueos_hoy = 0
    total_slots = 0
    ingresos_hoy = 0.0

    for cancha_agenda in agenda.canchas_agenda:
        for slot in cancha_agenda.slots:
            total_slots += 1
            if slot.estado == "confirmada":
                reservas_hoy += 1
                ingresos_hoy += slot.precio
            elif slot.estado == "bloqueada":
                bloqueos_hoy += 1

    ocupacion_pct = round((reservas_hoy / total_slots * 100), 1) if total_slots > 0 else 0.0

    return KpiStatsOut(
        fecha=agenda.fecha,
        total_canchas=total_canchas,
        reservas_hoy=reservas_hoy,
        bloqueos_hoy=bloqueos_hoy,
        total_slots=total_slots,
        ocupacion_pct=ocupacion_pct,
        ingresos_hoy=ingresos_hoy,
    )


@router.post("/reservas", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
async def crear_reserva_manual(
    data: ReservaManualIn,
    session: AsyncSession = Depends(get_db),
):
    """Crea una reserva de forma manual desde el mostrador del panel web."""
    service = BookingService(session)
    try:
        reserva = await service.create_manual_booking(
            cancha_id=data.cancha_id,
            fecha_inicio=data.fecha_inicio,
            cliente_nombre=data.cliente_nombre,
            cliente_telefono=data.cliente_telefono,
            precio=data.precio,
            notas=data.notas,
        )
        return reserva
    except CourtNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SlotAlreadyBookedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reservas/{reserva_id}/cancelar", response_model=ReservaOut)
async def cancelar_reserva_admin(
    reserva_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Cancela una reserva existente sin requerir verificación de telegram_id (rol administrador)."""
    service = BookingService(session)
    try:
        reserva = await service.cancel_booking(reserva_id=reserva_id, telegram_id=None)
        return reserva
    except BookingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/bloqueos", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
async def bloquear_turno_admin(
    data: BloqueoIn,
    session: AsyncSession = Depends(get_db),
):
    """Bloquea un turno específico por motivos de mantenimiento, lluvia o torneo."""
    service = BookingService(session)
    try:
        bloqueo = await service.bloquear_turno(
            cancha_id=data.cancha_id,
            fecha_inicio=data.fecha_inicio,
            motivo=data.motivo,
        )
        return bloqueo
    except CourtNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SlotAlreadyBookedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/bloqueos/{reserva_id}/desbloquear", response_model=ReservaOut)
async def desbloquear_turno_admin(
    reserva_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Desbloquea un horario para que vuelva a estar libre en la agenda."""
    service = BookingService(session)
    try:
        bloqueo = await service.desbloquear_turno(reserva_id=reserva_id)
        return bloqueo
    except BookingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BookingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
