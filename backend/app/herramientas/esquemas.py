"""Esquemas de las herramientas (spec §8.2): lo que el modelo llena y el código valida.

Cada herramienta tiene dos formas: el esquema JSON que se envía al servidor (salida
guiada) y el modelo Pydantic que valida lo recibido. El `item_id` nunca lo decide
el modelo: lo asigna el código según el plan.
"""
from typing import Literal

from pydantic import BaseModel, Field

Nivel = Literal["receptivo", "resolutivo", "reflexivo", "critico"]
NIVELES = ["receptivo", "resolutivo", "reflexivo", "critico"]


# --- Cuestionario -------------------------------------------------------------

class Opcion(BaseModel):
    texto: str
    justificacion: str
    error_que_representa: str


class _ItemSalida(BaseModel):
    """Ítem tal como lo entrega el modelo (sin `item_id`)."""
    nivel: Nivel
    ra: str
    contenido: str
    foco: str
    contexto: str
    pregunta: str = Field(min_length=25)
    opciones: list[Opcion] = Field(min_length=4, max_length=4)
    correcta: int = Field(ge=0, le=3)
    razonamiento: list[str]


class ItemCuestionario(_ItemSalida):
    item_id: str


class LoteCuestionario(BaseModel):
    items: list[_ItemSalida]


def esquema_cuestionario(n: int, ras: list[str], contenidos: list[str]) -> dict:
    """Esquema de un lote de `n` ítems; `ra` y `contenido` solo admiten los de la clase."""
    opcion = {"type": "object", "properties": {
        "texto": {"type": "string"}, "justificacion": {"type": "string"},
        "error_que_representa": {"type": "string"}},
        "required": ["texto", "justificacion", "error_que_representa"]}
    item = {"type": "object", "properties": {
        "nivel": {"type": "string", "enum": NIVELES},
        "ra": {"type": "string", "enum": list(ras)},
        "contenido": {"type": "string", "enum": list(contenidos)},
        "foco": {"type": "string"}, "contexto": {"type": "string"},
        "pregunta": {"type": "string", "minLength": 25},
        "opciones": {"type": "array", "minItems": 4, "maxItems": 4, "items": opcion},
        "correcta": {"type": "integer", "minimum": 0, "maximum": 3},
        "razonamiento": {"type": "array", "items": {"type": "string"}}},
        "required": ["nivel", "ra", "contenido", "foco", "contexto", "pregunta",
                     "opciones", "correcta", "razonamiento"]}
    return {"type": "object", "properties": {
        "items": {"type": "array", "minItems": n, "maxItems": n, "items": item}},
        "required": ["items"]}


# --- Ficha de clase -------------------------------------------------------------

class FichaConceptual(BaseModel):
    ideas_clave: list[str] = Field(min_length=3, max_length=6)
    relacion_ra: str
    errores_frecuentes: list[str] = Field(min_length=1)


class Ejemplo(BaseModel):
    enunciado: str
    pasos: list[str] = Field(min_length=1)
    resultado: str


class FichaAplicacion(BaseModel):
    ejemplo: Ejemplo
    autocomprobacion: list[str] = Field(min_length=3, max_length=5)


_LISTA = {"type": "array", "items": {"type": "string"}}

ESQUEMA_FICHA_CONCEPTUAL = {"type": "object", "properties": {
    "ideas_clave": {**_LISTA, "minItems": 3, "maxItems": 6},
    "relacion_ra": {"type": "string"},
    "errores_frecuentes": {**_LISTA, "minItems": 1}},
    "required": ["ideas_clave", "relacion_ra", "errores_frecuentes"]}

ESQUEMA_FICHA_APLICACION = {"type": "object", "properties": {
    "ejemplo": {"type": "object", "properties": {
        "enunciado": {"type": "string"}, "pasos": {**_LISTA, "minItems": 1},
        "resultado": {"type": "string"}},
        "required": ["enunciado", "pasos", "resultado"]},
    "autocomprobacion": {**_LISTA, "minItems": 3, "maxItems": 5}},
    "required": ["ejemplo", "autocomprobacion"]}
