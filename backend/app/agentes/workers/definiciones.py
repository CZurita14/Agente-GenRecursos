"""Qué es cada herramienta con IA para el coordinador (P3b): ámbito, forma y controles.

Separado de los workers (que solo generan) para que el coordinador no dependa de su
clase: las pruebas sustituyen workers sin perder esta metadata.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.agentes.verificador import verificar_ficha
from app.herramientas.esquemas import FichaAplicacion, FichaConceptual
from app.silabo.contexto import ContextoClase


@dataclass(frozen=True)
class Definicion:
    ambito: str                                   # clase, momento o asignatura
    es_quiz: bool = False                         # ítems planificados (cuestionario, simulacro)
    secciones: tuple[str, ...] = ()               # lote k → secciones[k - 1]
    modelos: tuple[type[BaseModel], ...] = ()     # esquema de cada sección
    verificar: Callable[[dict, ContextoClase], list[str]] = field(default=verificar_ficha)
    id_revision: str = "ficha"                    # clave del veredicto de integridad


DEFINICIONES: dict[str, Definicion] = {
    "cuestionario": Definicion("clase", es_quiz=True),
    "ficha_clase": Definicion("clase", secciones=("conceptual", "aplicacion"),
                              modelos=(FichaConceptual, FichaAplicacion)),
}
