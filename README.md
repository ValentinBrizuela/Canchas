# Canchas SaaS ⚽🎾

Plataforma multi-complejo (SaaS) para la gestión y reserva de turnos de canchas de fútbol y deportes, con bot de Telegram y asistente conversacional potenciado por Google Gemini.

## Características

- **Multi-Tenant (SaaS)**: Soporte para múltiples complejos deportivos.
- **Configuración flexible**: Duración de turnos y tarifas configurables por cancha.
- **Bot de Telegram 100% conversacional**: Los clientes reservan y consultan turnos hablando en lenguaje natural.
- **Agente con Google Gemini**: Invoca herramientas (*Function Calling*) para consultar disponibilidad y agendar turnos de forma precisa y sin alucinaciones.
- **Dockerizado**: Preparado para desarrollo y despliegue rápido con Docker y Docker Compose.
- **Backend Asíncrono en Python**: Desarrollado con SQLAlchemy 2.0 Async, aiosqlite/PostgreSQL y aiogram 3.

## Requisitos

- Python 3.11+
- Docker y Docker Compose (opcional para ejecución en contenedores)
