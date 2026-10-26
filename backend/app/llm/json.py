"""Extracción y validación de JSON de las salidas del modelo."""
import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.cliente import ClienteLLM, JsonInvalido, Respuesta

T = TypeVar("T", bound=BaseModel)

REINTENTOS_JSON = 2

__all__ = ["JsonInvalido", "pedir_json", "ultimo_json"]


def ultimo_json(texto: str) -> dict:
    """Devuelve el último objeto JSON del texto, ignorando los bloques <think>."""
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S)
    bloques = re.findall(r"\{.*\}", texto, flags=re.S)
    return json.loads(bloques[-1])


def pedir_json(cliente: ClienteLLM, mensajes: list[dict], modelo: type[T], esquema: dict,
               **kw) -> tuple[T, Respuesta]:
    """Pide una salida guiada por esquema y la valida con Pydantic.

    Ante JSON inválido (incluida una salida cortada por `length`, que queda truncada) o un
    `ValidationError`, reintenta hasta 2 veces; después lanza `JsonInvalido`.
    """
    kw.setdefault("temperatura", 0.4)
    kw.setdefault("max_tokens", 3500)
    kw.setdefault("pensar", False)
    kw.setdefault("trabajo_id", None)
    kw.setdefault("asignatura_id", None)
    ultimo_error: Exception | None = None
    for _ in range(1 + REINTENTOS_JSON):
        respuesta = cliente.completar(mensajes, esquema=esquema, **kw)
        try:
            return modelo.model_validate(ultimo_json(respuesta.texto)), respuesta
        except (ValueError, IndexError) as error:  # JSONDecodeError y ValidationError son ValueError
            ultimo_error = error
    raise JsonInvalido(f"JSON inválido tras {1 + REINTENTOS_JSON} intentos: {ultimo_error}")
