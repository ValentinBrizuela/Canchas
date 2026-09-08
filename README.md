# Canchas SaaS ⚽🎾

Plataforma para la gestión y reserva de canchas deportivas, que combina un **Panel Web de Administración** en tiempo real con un **Bot de Telegram conversacional** impulsado por IA (Google Gemini / OpenRouter).

---

## 🚀 Características

- **Panel Web en Tiempo Real**: Agenda interactiva por canchas, métricas de ocupación e ingresos, reserva manual y bloqueo de horarios.
- **Gestión de Canchas**: Configuración de tarifas, deportes (fútbol, pádel, tenis, etc.) y estados activa/inactiva.
- **Bot de Telegram con IA**: Reservas en lenguaje natural mediante *Function Calling* sin solapamientos ni alucinaciones.
- **Seguridad**: Autenticación con JWT, contraseñas protegidas con PBKDF2 y pantalla de login.
- **Backend Asíncrono**: Python 3.12, FastAPI, SQLAlchemy 2.0 Async, SQLite/PostgreSQL y aiogram 3.

---

## ⚡ Inicio Rápido con Docker

1. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   ```
   *(Opcional: agrega tus claves de Telegram e IA en `.env` si deseas activar el bot).*

2. **Iniciar la aplicación**:
   ```bash
   docker compose up -d --build
   ```

3. **Acceder**:
   - **Panel Web**: [http://localhost:8000](http://localhost:8000)
   - **Usuario**: `admin` | **Clave**: `admin123`
   - **Documentación API**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Pruebas

Ejecutar la suite de tests automatizados:
```bash
docker compose exec app pytest
```

---

## 🛠️ Ejecución Local (sin Docker)

```bash
python -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m src.main
```
