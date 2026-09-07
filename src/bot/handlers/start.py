from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from src.bot.manager import agent_manager
from src.config import get_settings
from src.db.session import async_session
from src.models import Cliente, Complejo

router = Router(name="start_router")


async def get_or_default_complejo(session) -> Complejo:
    """Obtiene el complejo por defecto o crea uno si la base de datos está vacía."""
    settings = get_settings()
    stmt = select(Complejo).where(Complejo.slug == settings.DEFAULT_TENANT_SLUG)
    res = await session.execute(stmt)
    complejo = res.scalar_one_or_none()

    if not complejo:
        complejo = Complejo(
            slug=settings.DEFAULT_TENANT_SLUG,
            nombre=settings.DEFAULT_TENANT_NAME,
            hora_apertura=9,
            hora_cierre=24,
        )
        session.add(complejo)
        await session.commit()
        await session.refresh(complejo)

    return complejo


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Manejador del comando /start."""
    user = message.from_user
    if not user:
        return

    async with async_session() as session:
        complejo = await get_or_default_complejo(session)

        # Registrar o actualizar cliente
        cliente_stmt = select(Cliente).where(Cliente.telegram_id == user.id)
        res = await session.execute(cliente_stmt)
        cliente = res.scalar_one_or_none()
        if not cliente:
            cliente = Cliente(
                telegram_id=user.id,
                nombre=user.full_name or user.first_name,
                username=user.username,
            )
            session.add(cliente)
            await session.commit()

        # Reiniciar conversación para empezar limpio
        agent_manager.reset_agent(user.id, complejo.id)

    bienvenida = (
        f"⚽ ¡Hola <b>{user.first_name}</b>! Te damos la bienvenida a <b>{complejo.nombre}</b>.\n\n"
        f"Soy tu asistente virtual inteligente. Podés consultarme turnos disponibles, precios "
        f"o pedirme una reserva directamente hablándome como a cualquier persona.\n\n"
        f"💡 <i>Ejemplos de lo que podés escribirme:</i>\n"
        f"• <i>«¿Qué canchas tienen y cuánto salen?»</i>\n"
        f"• <i>«¿Tenés turno hoy a las 20hs para fútbol 5?»</i>\n"
        f"• <i>«Reservame el viernes a las 21hs»</i>\n"
        f"• <i>«¿Qué turnos tengo reservados?»</i>\n\n"
        f"Escribime cuando quieras y te ayudo al instante. 🏃‍♂️"
    )
    await message.answer(bienvenida)


@router.message(Command("ayuda"))
async def handle_ayuda(message: Message) -> None:
    """Manejador del comando /ayuda."""
    ayuda_texto = (
        "📖 <b>Guía de ayuda y uso del bot</b>\n\n"
        "Este asistente utiliza inteligencia artificial para entender tus pedidos de forma natural.\n\n"
        "<b>Comandos disponibles:</b>\n"
        "• /start - Iniciar o reiniciar la interacción\n"
        "• /ayuda - Ver esta guía de ayuda\n"
        "• /reiniciar - Borrar el historial de charla actual\n\n"
        "<b>Podés pedir cosas como:</b>\n"
        "• Consultar disponibilidad: <i>«¿Qué horarios tenés libres mañana para Pádel?»</i>\n"
        "• Reservar: <i>«Quiero la Cancha 1 el sábado a las 19»</i>\n"
        "• Ver tus turnos: <i>«Mostrame mis reservas»</i>\n"
        "• Cancelar: <i>«Quiero cancelar mi reserva del viernes»</i>\n"
    )
    await message.answer(ayuda_texto)


@router.message(Command("reiniciar"))
async def handle_reiniciar(message: Message) -> None:
    """Manejador del comando /reiniciar."""
    user = message.from_user
    if not user:
        return

    async with async_session() as session:
        complejo = await get_or_default_complejo(session)
        agent_manager.reset_agent(user.id, complejo.id)

    await message.answer("🔄 Conversación reiniciada. ¿En qué te puedo ayudar hoy?")
