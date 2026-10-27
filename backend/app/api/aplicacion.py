"""Fábrica ASGI: salud pública y aplicación cerrada hasta autenticar (A2)."""
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agentes.facultades import cargar_perfiles
from app.api.errores import registrar_errores
from app.config import RAIZ, Ajustes, ajustes


def crear_app(config: Ajustes | None = None, *, transporte=None) -> FastAPI:
    config = config or ajustes()

    @asynccontextmanager
    async def vida(app):
        directorio = config.agentes_dir
        if not directorio.is_absolute():
            directorio = RAIZ / directorio
        app.state.perfiles = cargar_perfiles(directorio)
        async with httpx.AsyncClient(timeout=5, transport=transporte,
                                     headers={"Authorization": f"Bearer {config.llm_api_key}"}) as cliente:
            app.state.ia = cliente
            yield

    app = FastAPI(lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)
    registrar_errores(app)

    @app.middleware("http")
    async def acceso(request: Request, siguiente):
        # A2 sustituirá este cierre por validación de sesión persistente.
        # No basta con presentar una cookie para entrar.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != config.api_origen:
                return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
        if request.url.path != "/salud":
            return JSONResponse({"detail": "Sesión requerida"}, status_code=401)
        return await siguiente(request)

    # CORS envuelve también los rechazos del control de acceso.
    app.add_middleware(CORSMiddleware, allow_origins=[config.api_origen],
                       allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Content-Type"])

    @app.get("/salud")
    async def salud():
        disponible = False
        try:
            r = await app.state.ia.get(config.llm_base_url.rstrip("/") + "/models")
            r.raise_for_status()
            datos = r.json()
            modelos = datos.get("data", []) if isinstance(datos, dict) else []
            disponible = isinstance(modelos, list) and any(
                isinstance(m, dict) and m.get("id") == config.llm_model
                and m.get("max_model_len") == 8192 for m in modelos)
        except (httpx.HTTPError, ValueError):
            pass
        return JSONResponse({"estado": "ok" if disponible else "degradado",
                             "ia": disponible, "agentes": sorted(app.state.perfiles)},
                            status_code=200 if disponible else 503)

    return app
