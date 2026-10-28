"""Presentación ordenada de cada herramienta: la misma para revisar y para exportar.

El contenido se guarda en jsonb, que no conserva el orden de las claves, y sus claves
son internas («clase_id», «numero_clase»). Aquí cada herramienta declara qué se muestra,
en qué orden y con qué título, como una lista de bloques:

- texto: {"tipo": "texto", "titulo", "texto"}
- lista: {"tipo": "lista", "titulo", "items": [str], "numerada": bool}
- tabla: {"tipo": "tabla", "titulo", "columnas": [str], "filas": [[str]]}
- grupo: {"tipo": "grupo", "titulo", "bloques": [...]}

Los cuestionarios (ítems con opciones) no pasan por aquí: tienen su propia vista.
"""
from collections.abc import Callable

NIVELES = {"receptivo": "Receptivo", "resolutivo": "Resolutivo", "reflexivo": "Reflexivo",
           "critico": "Crítico", "cocreativo": "Cocreativo"}
TITULOS = {
    "ideas_clave": "Ideas clave", "relacion_ra": "Relación con el RA", "errores_frecuentes": "Errores frecuentes",
    "autocomprobacion": "Autocomprobación", "que_se_pide": "Qué se pide", "como_se_valora": "Cómo se valora",
    "errores_comunes": "Errores comunes", "autochequeo": "Autochequeo", "conexion_ra": "Conexión con el RA",
    "preguntas_repaso": "Preguntas de repaso", "respuesta_orientativa": "Respuesta orientativa",
    "que_observar": "Qué observar", "como_prepararse": "Cómo prepararse", "producto_final": "Producto final",
    "politica_ia": "Política de IA", "clase_id": "Clase", "para_subir": "Para subir de nivel",
}
_OCULTAS = {"item_id", "escenario"}  # Datos internos del sistema, no para el estudiante.
SIN_POLITICA = "No indicada en el sílabo"


def _texto(titulo: str, texto) -> dict:
    return {"tipo": "texto", "titulo": titulo, "texto": str(texto)}


def _lista(titulo: str, items, numerada: bool = False) -> dict:
    return {"tipo": "lista", "titulo": titulo, "items": [str(x) for x in items or []], "numerada": numerada}


def _tabla(titulo: str, columnas: list[str], filas) -> dict:
    return {"tipo": "tabla", "titulo": titulo, "columnas": columnas,
            "filas": [[str(c) if c is not None else "" for c in f] for f in filas]}


def _grupo(titulo: str, bloques: list[dict]) -> dict:
    return {"tipo": "grupo", "titulo": titulo, "bloques": bloques}


def _fecha(iso) -> str:
    """«2026-10-14» → «14/10/2026»."""
    s = str(iso or "")
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) >= 10 else s


def _momento(c: dict) -> dict:
    return _texto("Momento", f"Momento {c['momento']} · {c.get('titulo', '')}".rstrip(" ·"))


def _rubrica(indicadores: list[dict], niveles: list[str]) -> dict:
    return _tabla("Rúbrica", ["Indicador", *(NIVELES.get(n, n) for n in niveles)],
                  [[f["indicador"], *(f["descriptores"].get(n, "") for n in niveles)] for f in indicadores])


def _ficha(c: dict) -> list[dict]:
    conceptual, aplicacion = c["conceptual"], c["aplicacion"]
    ejemplo = aplicacion["ejemplo"]
    return [
        _lista("Ideas clave", conceptual["ideas_clave"]),
        _texto("Relación con el RA", conceptual["relacion_ra"]),
        _lista("Errores frecuentes", conceptual["errores_frecuentes"]),
        _grupo("Ejemplo resuelto", [_texto("Enunciado", ejemplo["enunciado"]),
                                    _lista("Pasos", ejemplo["pasos"], numerada=True),
                                    _texto("Resultado", ejemplo["resultado"])]),
        _lista("Autocomprobación", aplicacion["autocomprobacion"], numerada=True),
    ]


def _repaso(c: dict) -> list[dict]:
    r = c["repaso"]
    return [
        *(_grupo(f"Clase {s['clase_id']}", [_lista("Ideas clave", s["ideas_clave"])]) for s in r["sesiones"]),
        _texto("Conexión con el RA", r["conexion_ra"]),
        _lista("Preguntas de repaso", r["preguntas_repaso"], numerada=True),
    ]


def _guia(c: dict) -> list[dict]:
    g = c["guia"]
    return [
        _texto("Qué se pide", g["que_se_pide"]),
        _tabla("Cómo se valora", ["Indicador", "Qué observar"],
               [[x["indicador"], x["que_observar"]] for x in g["como_se_valora"]]),
        _lista("Errores comunes", g["errores_comunes"]),
        _lista("Autochequeo", g["autochequeo"], numerada=True),
    ]


def _caso(c: dict) -> list[dict]:
    caso = c["caso"]
    return [
        _texto("Caso", caso["caso"]),
        _texto("Resultado de aprendizaje", caso["ra"]),
        *(_grupo(f"Pregunta {n} · {NIVELES.get(p['nivel'], p['nivel'])}",
                 [_texto("Pregunta", p["pregunta"]), _texto("Respuesta orientativa", p["respuesta_orientativa"])])
          for n, p in enumerate(caso["preguntas"], 1)),
    ]


def _guia_final(c: dict) -> list[dict]:
    g = c["guia_final"]
    return [
        _tabla("Ruta por momentos", ["Momento", "Aporte al producto final"], [[x["momento"], x["aporte"]] for x in g["ruta"]]),
        _tabla("Criterios", ["Indicador", "Cómo prepararse"], [[x["indicador"], x["como_prepararse"]] for x in g["criterios"]]),
        _lista("Recomendaciones", g["recomendaciones"]),
    ]


def _hoja_ruta(c: dict) -> list[dict]:
    p = c["periodo"]
    return [
        _texto("Asignatura", f"{c['asignatura']} ({c['codigo']})"),
        _texto("Periodo", f"{p['codigo']} · {_fecha(p['inicio'])} – {_fecha(p['fin'])}"),
        _tabla("Momentos", ["Momento", "Fechas", "RA", "Evidencia", "Política de IA"],
               [[f"{m['numero']}. {m['titulo']}", f"{_fecha(m['fecha_inicio'])} – {_fecha(m['fecha_fin'])}",
                 ", ".join(m["ra"]), m["evidencia"], m.get("politica_ia") or SIN_POLITICA] for m in c["momentos"]]),
        _tabla("Calendario de clases", ["Semana", "Clase", "Fecha", "Contenidos", "Entregables"],
               [[s["numero"], f"Clase {k['numero_clase']} · {k['clase_id']}", _fecha(k["fecha"]),
                 "; ".join(k["contenidos"]), "; ".join(k["entregables"])]
                for s in c["semanas"] for k in s["clases"]]),
        _texto("Producto final", c["producto_final"]),
    ]


def _autoevaluacion(c: dict) -> list[dict]:
    return [
        _texto("Instrucciones", c["instrucciones"]),
        _momento(c),
        _texto("Evidencia", c["evidencia"]),
        _lista("Resultados de aprendizaje", [f"{r['id']}: {r['texto']}" for r in c["ra"]]),
        _rubrica(c["indicadores"], c["niveles"]),
        _texto("Política de IA", c.get("politica_ia") or SIN_POLITICA),
    ]


def _autoevaluacion_final(c: dict) -> list[dict]:
    return [
        _texto("Instrucciones", c["instrucciones"]),
        _texto("Producto final", c["evidencia"]),
        _rubrica(c["indicadores"], c["niveles"]),
        _lista("Política de IA por momento",
               [f"Momento {p['momento']}: {p.get('politica_ia') or SIN_POLITICA}" for p in c["politica_ia"]]),
    ]


def _lista_evidencia(c: dict) -> list[dict]:
    return [
        _momento(c),
        _texto("Evidencia", c["evidencia"]),
        _lista("Entregables", c["entregables"]),
        _tabla("Antes de entregar, verifica", ["Indicador", "Mínimo esperado (nivel resolutivo)"],
               [[x["indicador"], x["referencia_resolutivo"]] for x in c["items"]]),
        _texto("Política de IA", c.get("politica_ia") or SIN_POLITICA),
    ]


VISTAS: dict[str, Callable[[dict], list[dict]]] = {
    "ficha_clase": _ficha, "repaso_momento": _repaso, "guia_evidencia": _guia, "estudio_caso": _caso,
    "guia_producto_final": _guia_final, "hoja_ruta": _hoja_ruta, "autoevaluacion_rubrica": _autoevaluacion,
    "autoevaluacion_final": _autoevaluacion_final, "lista_evidencia": _lista_evidencia,
}


def _titulo(clave: str) -> str:
    return TITULOS.get(clave, clave.replace("_", " ").capitalize())


def _generica(valor, titulo: str = "") -> list[dict]:
    """Respaldo para formas no previstas: claves ordenadas alfabéticamente y títulos legibles."""
    if isinstance(valor, dict):
        bloques = [b for k in sorted(valor) if k not in _OCULTAS and valor[k] not in (None, "", [], {})
                   for b in _generica(valor[k], _titulo(k))]
        return [_grupo(titulo, bloques)] if titulo else bloques
    if isinstance(valor, list):
        if all(not isinstance(x, (dict, list)) for x in valor):
            return [_lista(titulo, valor)]
        return [_grupo(f"{titulo} {n}".strip(), _generica(x)) for n, x in enumerate(valor, 1)]
    return [_texto(titulo, valor)]


def es_quiz(contenido) -> bool:
    return isinstance(contenido, list) and bool(contenido) and all(isinstance(i, dict) and "opciones" in i for i in contenido)


def presentar(herramienta: str, contenido) -> list[dict]:
    """Bloques ordenados de la herramienta; [] para cuestionarios (vista propia)."""
    if es_quiz(contenido):
        return []
    vista = VISTAS.get(herramienta)
    if vista and isinstance(contenido, dict):
        try:
            return vista(contenido)
        except (KeyError, TypeError, AttributeError):
            pass  # Contenido editado o de un esquema anterior: se muestra igual, sin perder nada.
    return _generica(contenido)
