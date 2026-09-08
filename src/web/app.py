"""Aplicación FastAPI principal para el panel web y API REST."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.api.dashboard import router as dashboard_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_web_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI para el SaaS."""
    app = FastAPI(
        title="Canchas SaaS - Panel de Administración",
        description="Sistema de gestión y agenda interactiva para complejos deportivos.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware CORS para permitir interacción fluida
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rutas API
    app.include_router(dashboard_router)

    # Servir archivos estáticos si existe la carpeta
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": "canchas-saas"}

    @app.get("/", include_in_schema=False)
    async def index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {
            "message": "Panel Web Canchas SaaS activo. Visita /docs para la documentación de API."
        }

    return app


app = create_web_app()
