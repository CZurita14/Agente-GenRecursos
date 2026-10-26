"""Verificador determinista (spec §10.1), sin IA.

Revisa cada ítem entregado por un worker y devuelve sus fallos en español. La regla 1
(esquema) ya la garantizan la salida guiada y la validación Pydantic; la regla 8
(autoevaluación idéntica a la rúbrica) llega con su herramienta (P3).
"""
import re
from difflib import SequenceMatcher
from uuid import UUID

from app.agentes.mensajes import PlanItem
from app.herramientas.esquemas import ItemCuestionario
from app.silabo.contexto import ContextoClase

PROHIBIDAS = re.compile(
    r"\b(todas|ninguna) (de )?las anteriores\b|\btodas son correctas\b|\bninguna es correcta\b", re.I
)
UMBRAL_DUPLICADO = 0.8  # §10.1.6
MIN_PALABRAS_CONTEXTO = 15  # medido en la prueba de calidad v2
NIVELES_CON_CONTEXTO = {"resolutivo", "reflexivo", "critico"}
NIVELES_CON_PASOS = {"reflexivo", "critico"}
TOLERANCIA_DISTRIBUCION = 1  # §10.1.4

OTRA_ASIGNATURA = "entrega de otra asignatura"


def _normal(texto: str) -> str:
    return " ".join(texto.lower().split())


def _parecidas(a: str, b: str) -> bool:
    return SequenceMatcher(None, _normal(a), _normal(b)).ratio() >= UMBRAL_DUPLICADO


def verificar_items(
    items: list[ItemCuestionario],
    plan: list[PlanItem],
    contexto: ContextoClase,
    previos: list[str],
    asignatura_entrega: UUID,
    asignatura_trabajo: UUID,
) -> dict[str, list[str]]:
    """Fallos por `item_id` (lista vacía si el ítem pasa)."""
    if asignatura_entrega != asignatura_trabajo:  # A7: la entrega se descarta entera
        return {i.item_id: [OTRA_ASIGNATURA] for i in items}

    niveles_plan = {p.item_id: p.nivel for p in plan}
    ras = {r.id for r in contexto.ra}
    contenidos = {_normal(c) for c in contexto.contenidos}
    resultado: dict[str, list[str]] = {}
    vistas: list[str] = []  # preguntas anteriores dentro del lote

    for item in items:
        f: list[str] = []
        textos = [_normal(o.texto) for o in item.opciones]
        if len(item.opciones) != 4 or len(set(textos)) != len(textos):
            f.append("opciones duplicadas o distintas de cuatro")
        if item.ra not in ras:
            f.append(f"el resultado de aprendizaje {item.ra} no es de esta clase")
        if _normal(item.contenido) not in contenidos:
            f.append("el contenido no es de esta clase")
        if item.nivel in NIVELES_CON_CONTEXTO and len(item.contexto.split()) < MIN_PALABRAS_CONTEXTO:
            f.append(f"contexto profesional de menos de {MIN_PALABRAS_CONTEXTO} palabras")
        if item.nivel in NIVELES_CON_PASOS and len([p for p in item.razonamiento if p.strip()]) < 2:
            f.append("menos de dos pasos de razonamiento")
        if any(_parecidas(item.pregunta, otra) for otra in [*vistas, *previos]):
            f.append("enunciado casi duplicado de otro ya generado")
        if any(PROHIBIDAS.search(t) for t in [item.pregunta, *(o.texto for o in item.opciones)]):
            f.append("frase prohibida (todas/ninguna de las anteriores)")
        esperado = niveles_plan.get(item.item_id)
        if esperado is not None and item.nivel != esperado:
            f.append(f"nivel {item.nivel} distinto del planificado ({esperado})")
        resultado[item.item_id] = f
        vistas.append(item.pregunta)
    return resultado


def verificar_distribucion(items: list[ItemCuestionario], tabla: dict[str, int]) -> list[str]:
    """Regla 4: cantidad por nivel dentro de la tabla de especificaciones (±1)."""
    reales = {nivel: 0 for nivel in tabla}
    for item in items:
        reales[item.nivel] = reales.get(item.nivel, 0) + 1
    return [
        f"nivel {nivel}: {reales.get(nivel, 0)} ítems frente a {esperado} planificados"
        for nivel, esperado in tabla.items()
        if abs(reales.get(nivel, 0) - esperado) > TOLERANCIA_DISTRIBUCION
    ]


def _textos(valor) -> list[str]:
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return [t for v in valor.values() for t in _textos(v)]
    if isinstance(valor, list):
        return [t for v in valor for t in _textos(v)]
    return []


def verificar_ficha(ficha: dict, contexto: ContextoClase) -> list[str]:
    """Frases prohibidas y campos de texto vacíos en una sección de la ficha."""
    textos = _textos(ficha)
    fallos = []
    if any(not t.strip() for t in textos):
        fallos.append("hay campos vacíos")
    if any(PROHIBIDAS.search(t) for t in textos):
        fallos.append("frase prohibida (todas/ninguna de las anteriores)")
    return fallos
