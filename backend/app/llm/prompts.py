"""Constructor único de prompts (regla A3): nadie más arma mensajes para el modelo.

Todo prompt empieza con el sello de la asignatura y se ajusta al contexto de
8 192 tokens. Orden de recorte: ya generados (los más antiguos primero) ->
rúbrica (los indicadores del final primero). La clase nunca se recorta.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.agentes.mensajes import EstiloFacultad
from app.llm.cliente import ContextoExcedido
from app.silabo.contexto import ContextoClase

# Presupuesto por parte, en tokens (especificación §5.3). La salida (<= 3 500)
# la fija quien llama con `salida_max`.
PRESUPUESTO = {"instrucciones": 900, "clase": 900, "rubrica": 600, "perfil": 500, "ya_generado": 400}
CONTEXTO_MAX = 8192
MARGEN = 300


@dataclass(frozen=True)
class Sello:
    codigo_pf: str
    clase_id: str
    fecha: date

    def linea(self) -> str:
        return f"[Asignatura {self.codigo_pf} · Clase {self.clase_id} · {self.fecha:%d/%m/%Y}]"


def _lista(titulo: str, items: list[str]) -> str:
    if not items:
        return ""
    return titulo + "\n" + "\n".join(f"- {i}" for i in items)


def _seccion_clase(c: ContextoClase) -> str:
    ra = [f"{r.id}: {r.texto} (evidencia: {r.evidencia})" for r in c.ra]
    partes = [
        f"## Clase {c.clase_id} · {c.momento_titulo}",
        _lista("Contenidos:", c.contenidos),
        _lista("Actividades:", c.actividades),
        _lista("Resultados de aprendizaje:", ra),
    ]
    return "\n".join(p for p in partes if p)


def _seccion_rubrica(c: ContextoClase, n: int) -> str:
    filas = c.rubrica[:n]
    if not filas:
        return ""
    lineas = ["## Rúbrica"]
    for f in filas:
        niveles = "; ".join(f"{k}: {v}" for k, v in f.niveles.items())
        lineas.append(f"- {f.indicador} -> {niveles}")
    return "\n".join(lineas)


def _seccion_perfil(c: ContextoClase, e: EstiloFacultad) -> str:
    partes = [
        "## Perfil y territorio",
        f"Competencia del perfil: {c.competencia_perfil}",
        f"Problema del territorio: {c.problema.descripcion}",
        f"Reto: {c.problema.reto}",
        f"Producto final: {c.problema.producto_final}",
        _lista("Tipos de caso de la facultad:", e.tipos_de_caso),
        _lista("Software habitual:", e.software_habitual),
        f"Vocabulario: {e.vocabulario}" if e.vocabulario else "",
    ]
    return "\n".join(p for p in partes if p)


def _seccion_ya_generado(ya: list[str]) -> str:
    return _lista("## Ya generado (no repetir)", ya)


def construir_prompt(
    *,
    sello: Sello,
    instrucciones: str,
    contexto: ContextoClase,
    estilo: EstiloFacultad,
    ya_generado: list[str],
    pedido: str,
    salida_max: int,
    contar: Callable[[list[dict]], int],
) -> list[dict]:
    """Devuelve `[system, user]`; recorta si no cabe y falla si ni así."""
    system = {"role": "system", "content": f"{sello.linea()}\n{instrucciones}"}
    clase = _seccion_clase(contexto)
    perfil = _seccion_perfil(contexto, estilo)
    ya = list(ya_generado)
    n_rubrica = len(contexto.rubrica)

    def armar() -> list[dict]:
        partes = [clase, _seccion_rubrica(contexto, n_rubrica), perfil,
                  _seccion_ya_generado(ya), f"## Pedido\n{pedido}"]
        return [system, {"role": "user", "content": "\n\n".join(p for p in partes if p)}]

    def cabe(msgs: list[dict]) -> bool:
        return contar(msgs) + salida_max + MARGEN <= CONTEXTO_MAX

    msgs = armar()
    while not cabe(msgs) and ya:
        ya.pop(0)  # los más antiguos primero
        msgs = armar()
    while not cabe(msgs) and n_rubrica > 0:
        n_rubrica -= 1  # los indicadores del final primero
        msgs = armar()
    if not cabe(msgs):
        raise ContextoExcedido(f"la clase {sello.clase_id} no cabe en el contexto del modelo")
    return msgs
