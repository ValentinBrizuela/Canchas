# Canchas SaaS ⚽🎾🏆

Plataforma integral multi-complejo (SaaS) para la administración inteligente y reserva de turnos en complejos deportivos (fútbol, pádel, tenis y más). Incluye:
- **Panel Web de Administración** interactivo en tiempo real con autenticación segura JWT y métricas financieras/operativas.
- **Bot de Telegram 100% conversacional** potenciado por Inteligencia Artificial (**Google Gemini** y **OpenRouter**) con llamada a herramientas (*Function Calling*) para consultar disponibilidad y agendar reservas sin alucinaciones.

---

## 🚀 Características Principales

### 📊 Panel Web de Administración (FastAPI + Modern UI)
- **Agenda Interactiva**: Visualización por fecha y grilla horaria por cancha con estados en tiempo real (*Disponible*, *Reservado*, *Bloqueado*).
- **Métricas y KPIs en Vivo**: Canchas activas, reservas del día, porcentaje de ocupación estimada e ingresos proyectados actualizados al instante.
- **Operaciones Rápidas de Agenda**:
  - Reserva manual directa desde el calendario.
  - Bloqueo y desbloqueo de horarios por mantenimiento, clima o torneos.
  - Cancelación de turnos con liberación inmediata del cupo.
- **Gestión Integral de Canchas**: Creación y edición de espacios deportivos, cambio de tarifas, duración de turnos y conmutador (*toggle*) para activar o desactivar canchas de la agenda.
- **Filtros Dinámicos por Deporte**: Detección automática de disciplinas (Fútbol, Pádel, Tenis, etc.) con filtrado ágil en un clic.

### 🛡️ Seguridad y Autenticación
- **Control de Acceso mediante JWT**: Tokens de acceso Bearer protegidos y validados en cada petición a la API.
- **Hashing Criptográfico Robusto**: Contraseñas resguardadas con **PBKDF2-HMAC-SHA256** (100.000 iteraciones y sal aleatoria única).
- **Interfaz de Inicio de Sesión Moderna**: Pantalla `/login` con diseño *Dark Glassmorphic*, revelador de contraseñas y botón de autorrelleno para credenciales de demostración.
- **Protección Integral de API**: Rutas administrativas bloqueadas ante accesos no autorizados (`401 Unauthorized`) y redirección automática al login ante tokens expirados.

### 🤖 Bot de Telegram Conversacional con IA
- **Atención en Lenguaje Natural**: Los clientes consultan turnos disponibles y confirman reservas conversando naturalmente con el bot, sin menús rígidos.
- **Arquitectura de Agente con Function Calling**:
  - Consulta en tiempo real de canchas y slots libres según fecha y deporte.
  - Creación atómica de reservas validando conflictos de solapamiento.
  - Manejo de clientes (creación y vinculación automática por Telegram ID).
- **Soporte Multimodelo**: Integración con **Google Gemini 2.5 Flash** y **OpenRouter** (Llama 3.3 70B, etc.).

### ⚙️ Arquitectura y Backend
- **Python Asíncrono**: Desarrollado con `asyncio`, `FastAPI`, `SQLAlchemy 2.0 Async`, `aiosqlite` / `PostgreSQL` y `aiogram 3`.
- **Ejecución Concurrente**: Servidor Web REST y Bot de Telegram ejecutándose simultáneamente en el mismo servicio.
- **Diseño Multi-Tenant**: Estructura preparada para operar múltiples complejos deportivos de forma aislada.

---

## 🔑 Credenciales de Acceso por Defecto

Una vez desplegada la aplicación, el sistema inicializa automáticamente la base de datos con un complejo deportivo y usuario administrador de prueba:

| Servicio | URL / Acceso | Credenciales |
| :--- | :--- | :--- |
| **Panel de Administración** | `http://localhost:8000/` o `/login` | Usuario: `admin`<br>Contraseña: `admin123` |
| **Documentación API (Swagger)** | `http://localhost:8000/docs` | Acceso con token Bearer vía botón *Authorize* |
| **Documentación ReDoc** | `http://localhost:8000/redoc` | Consulta de esquemas y modelos OpenAPI |

---

## 🛠️ Requisitos Previos

- **Docker y Docker Compose** (método recomendado para desarrollo y producción).
- *Opcional (para desarrollo local sin Docker)*: Python 3.11+ con gestor de paquetes `pip`.

---

## 📦 Instalación y Puesta en Marcha

### Opción 1: Con Docker Compose (Recomendado)

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/ValentinBrizuela/Canchas.git
   cd Canchas
   ```

2. **Configurar variables de entorno**:
   Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```
   Edita `.env` para añadir tu clave de Telegram (`TELEGRAM_BOT_TOKEN`) y tu API Key de IA (`GEMINI_API_KEY` o `OPENROUTER_API_KEY`).
   > *Nota: Si no configuras el token de Telegram, el panel web funcionará normalmente y el bot se mantendrá en espera.*

3. **Construir y levantar los contenedores**:
   ```bash
   docker compose up --build -d
   ```

4. **Acceder a la aplicación**:
   - Abre tu navegador en **`http://localhost:8000`**.
   - Inicia sesión con `admin` / `admin123`.

---

### Opción 2: Ejecución Local en Python

1. **Crear y activar un entorno virtual**:
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar el archivo `.env`**:
   ```bash
   cp .env.example .env
   ```

4. **Ejecutar la aplicación**:
   ```bash
   python -m src.main
   ```

---

## ⚙️ Variables de Entorno

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `ENV` | Entorno de ejecución (`development`, `production`) | `development` |
| `LOG_LEVEL` | Nivel de registro de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `DATABASE_URL` | URI de conexión SQLAlchemy asíncrona | `sqlite+aiosqlite:///./data/canchas.db` |
| `TELEGRAM_BOT_TOKEN` | Token del bot provisto por [@BotFather](https://t.me/botfather) | `tu_token_aqui` |
| `AI_PROVIDER` | Proveedor de LLM conversacional (`gemini` o `openrouter`) | `openrouter` |
| `GEMINI_API_KEY` | API Key de Google AI Studio (requerido si `AI_PROVIDER=gemini`) | - |
| `GEMINI_MODEL` | Modelo de Google Gemini | `gemini-2.5-flash` |
| `OPENROUTER_API_KEY` | API Key de OpenRouter (requerido si `AI_PROVIDER=openrouter`) | - |
| `OPENROUTER_MODEL` | Identificador de modelo en OpenRouter | `meta-llama/llama-3.3-70b-instruct:free` |
| `DEFAULT_TENANT_SLUG` | Identificador único del complejo deportivo semilla | `demo-complejo` |
| `DEFAULT_TENANT_NAME` | Nombre visible del complejo deportivo | `Complejo Deportivo Demo` |
| `JWT_SECRET_KEY` | Clave secreta para firmar tokens de sesión JWT | `tu_clave_secreta_jwt_muy_segura` |
| `ADMIN_DEFAULT_PASSWORD` | Contraseña del usuario `admin` en la semilla | `admin123` |

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una amplia suite de pruebas automatizadas con **`pytest`** y `pytest-asyncio` que cubren hashing PBKDF2, flujo JWT, endpoints REST, servicios de disponibilidad y reservas, y agentes de IA:

### Ejecutar pruebas en Docker:
```bash
docker compose exec app pytest
```

### Ejecutar pruebas en entorno local:
```bash
pytest -v
```

---

## 📂 Estructura del Código

```text
Canchas/
├── data/                      # Base de datos SQLite persistida
├── src/
│   ├── ai/                    # Agentes conversacionales y Function Calling (Gemini / OpenRouter)
│   ├── bot/                   # Handlers y configuración de aiogram 3 para Telegram
│   ├── db/                    # Sesión SQLAlchemy async y scripts de seeding
│   ├── models/                # Modelos de dominio (Complejo, Cancha, Reserva, Cliente, Usuario)
│   ├── services/              # Lógica de negocio (disponibilidad de slots y reservas)
│   ├── web/                   # Aplicación FastAPI, endpoints REST y autenticación JWT
│   │   ├── api/               # Controladores de rutas (/api/v1)
│   │   ├── static/            # Frontend (HTML, CSS Dark Theme, Javascript vanilla)
│   │   ├── auth.py            # Hashing PBKDF2, JWT y dependencias FastAPI
│   │   └── schemas.py         # Modelos Pydantic de entrada y salida
│   ├── config.py              # Gestión centralizada de configuraciones
│   └── main.py                # Punto de entrada (Uvicorn + Telegram Polling)
├── tests/                     # Suite completa de tests unitarios y de integración
├── docker-compose.yml         # Orquestación de contenedores
├── Dockerfile                 # Definición de la imagen de producción
├── requirements.txt           # Dependencias fijadas del proyecto
└── README.md                  # Documentación del proyecto
```

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.
