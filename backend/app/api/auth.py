"""Rutas de códigos y sesiones. El middleware comprueba origen y sesión."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.auth.servicio import AuthError, normalizar_correo

router = APIRouter(prefix="/auth")


class PedidoCodigo(BaseModel):
    correo: str = Field(max_length=254)


class VerificarCodigo(PedidoCodigo):
    codigo: str = Field(max_length=64)


def servicio(request):
    if request.app.state.auth is None:
        raise AuthError(503, "Autenticación no configurada")
    return request.app.state.auth


@router.post("/codigo")
def pedir(datos: PedidoCodigo, request: Request):
    correo = normalizar_correo(datos.correo)
    if request.app.state.control is not None:
        request.app.state.control.correo_publico(correo, "codigo")
    servicio(request).pedir(datos.correo)
    return {"mensaje": "Se ha solicitado un código de acceso"}


@router.post("/verificar")
def verificar(datos: VerificarCodigo, request: Request, response: Response):
    correo = normalizar_correo(datos.correo)
    if request.app.state.control is not None:
        request.app.state.control.correo_publico(correo, "verificar")
    token = servicio(request).verificar(datos.correo, datos.codigo)
    request.state.usuario = correo
    response.set_cookie("sesion", token, max_age=7 * 24 * 3600,
                        httponly=True, secure=True, samesite="lax", path="/")
    return {"mensaje": "Sesión iniciada"}


@router.get("/yo")
def yo(request: Request):
    rol = "administrador" if request.state.usuario in request.app.state.config.administradores else "docente"
    return {"correo": request.state.usuario, "rol": rol}


@router.post("/salir")
def salir(request: Request, response: Response):
    servicio(request).salir(request.cookies.get("sesion"))
    response.delete_cookie("sesion", path="/", secure=True, httponly=True, samesite="lax")
    return {"mensaje": "Sesión cerrada"}
