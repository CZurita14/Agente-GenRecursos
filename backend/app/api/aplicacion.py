"""Fábrica ASGI: salud pública y aplicación cerrada hasta autenticar (A2)."""
from contextlib import asynccontextmanager
from threading import BoundedSemaphore

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import psycopg

from app.agentes.facultades import cargar_catalogo, cargar_perfiles
from app.api.asignaturas import router as asignaturas_router
from app.api.auth import router as auth_router
from app.api.errores import registrar_errores
from app.auth.correo import transporte_correo
from app.auth.servicio import ServicioAuth
from app.config import RAIZ, Ajustes, ajustes
from app.db.conexion import conectar
from app.asignaturas.servicio import ServicioAsignaturas


def crear_app(config: Ajustes | None = None, *, transporte=None, auth=None, conexion=None, lector_pdf=None) -> FastAPI:
    config = config or ajustes()
    conexion = conexion or (lambda: conectar(config.database_url))

    @asynccontextmanager
    async def vida(app):
        directorio = config.agentes_dir
        if not directorio.is_absolute():
            directorio = RAIZ / directorio
        app.state.perfiles = cargar_perfiles(directorio)
        app.state.asignaturas = ServicioAsignaturas(conexion, cargar_catalogo(RAIZ / "kb/catalogo.yaml"),
                                                    app.state.perfiles)
        async with httpx.AsyncClient(timeout=5, transport=transporte,
                                     headers={"Authorization": f"Bearer {config.llm_api_key}"}) as cliente:
            app.state.ia = cliente
            yield

    app = FastAPI(lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = config
    app.state.pdf_cupos = BoundedSemaphore(2)
    if lector_pdf is None:
        from app.silabo.aislado import leer_pdf_aislado
        lector_pdf = leer_pdf_aislado
    app.state.lector_pdf = lector_pdf
    app.state.auth = auth
    if auth is None and config.auth_secreto is not None:
        app.state.auth = ServicioAuth(conexion,
                                      config.auth_secreto.get_secret_value(), transporte_correo(config))
    registrar_errores(app)
    app.include_router(auth_router)
    app.include_router(asignaturas_router)

    @app.middleware("http")
    async def acceso(request: Request, siguiente):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != config.api_origen:
                return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
        publica = ((request.url.path == "/salud")
                   or (request.method == "POST" and request.url.path in {"/auth/codigo", "/auth/verificar"}))
        if not publica:
            usuario = None
            if app.state.auth is not None and request.cookies.get("sesion"):
                try:
                    usuario = await run_in_threadpool(app.state.auth.identificar, request.cookies["sesion"])
                except psycopg.Error:
                    return JSONResponse({"detail": "Servicio temporalmente no disponible"}, status_code=503)
            if usuario is None:
                return JSONResponse({"detail": "Sesión requerida"}, status_code=401)
            request.state.usuario = usuario
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
