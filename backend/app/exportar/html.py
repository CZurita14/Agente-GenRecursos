"""HTML autónomo para Canvas (spec §13): un solo archivo, sin CDN ni recursos externos.

Seguridad: el contenido viene del modelo y del docente, así que TODO texto pasa por
`html.escape`. El JavaScript es fijo (no lleva datos del recurso): la autocorrección lee
atributos del DOM ya escapados.
"""
from html import escape

from app.silabo.contexto import ContextoClase

PIE = "Recurso generado con asistencia de IA y revisado por el docente"

NOMBRES = {
    "cuestionario": "Cuestionario", "simulacro": "Simulacro", "ficha_clase": "Ficha de clase",
    "repaso_momento": "Repaso integrador", "guia_evidencia": "Guía de la evidencia",
    "estudio_caso": "Estudio de caso", "guia_producto_final": "Guía del producto final",
    "hoja_ruta": "Hoja de ruta de la asignatura", "autoevaluacion_rubrica": "Autoevaluación con la rúbrica",
    "autoevaluacion_final": "Autoevaluación final", "lista_evidencia": "Lista de verificación de la evidencia",
}
# Títulos legibles de las claves más comunes; las demás se derivan del nombre de la clave.
TITULOS = {
    "ideas_clave": "Ideas clave", "relacion_ra": "Relación con el RA", "errores_frecuentes": "Errores frecuentes",
    "autocomprobacion": "Autocomprobación", "que_se_pide": "Qué se pide", "como_se_valora": "Cómo se valora",
    "errores_comunes": "Errores comunes", "autochequeo": "Autochequeo", "conexion_ra": "Conexión con el RA",
    "preguntas_repaso": "Preguntas de repaso", "respuesta_orientativa": "Respuesta orientativa",
    "que_observar": "Qué observar", "como_prepararse": "Cómo prepararse", "producto_final": "Producto final",
    "politica_ia": "Política de IA", "clase_id": "Clase", "para_subir": "Para subir de nivel",
}
_OCULTAS = {"item_id", "escenario"}  # Datos internos del sistema, no para el estudiante.

ESTILO = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:860px;margin:0 auto;padding:24px;
color:#2C1547;background:#F4F0F9;line-height:1.5}
header{border-bottom:4px solid #F57021;margin-bottom:24px}h1{margin:0 0 4px}h2{margin-top:28px}
.sub{color:#6E5987;margin:0 0 12px}section,fieldset{background:#fff;border:1px solid #E2D9EE;border-radius:12px;
padding:16px;margin:12px 0}legend{font-weight:700;padding:0 6px}label{display:block;padding:6px;border-radius:8px;
cursor:pointer}label:hover{background:#F4F0F9}.fb{display:none;margin-top:8px;padding:8px;border-radius:8px}
.ok{background:#E2F6ED;color:#046446}.mal{background:#FFE7EC;color:#B41437}.ctx{color:#6E5987;font-style:italic}
footer{margin-top:32px;border-top:1px solid #E2D9EE;padding-top:12px;font-size:13px;color:#6E5987}
"""
# Autocorrección: lee data-correcta (0/1) de la opción elegida y muestra su retroalimentación.
SCRIPT = """
document.querySelectorAll('fieldset[data-item]').forEach(function (f) {
  f.addEventListener('change', function (e) {
    var opcion = e.target.closest('label');
    var fb = f.querySelector('.fb');
    var bien = opcion.getAttribute('data-correcta') === '1';
    fb.className = 'fb ' + (bien ? 'ok' : 'mal');
    fb.textContent = (bien ? 'Correcto. ' : 'Revisa tu respuesta. ') + opcion.getAttribute('data-justificacion');
    fb.style.display = 'block';
  });
});
"""


def _titulo(clave: str) -> str:
    return TITULOS.get(clave, clave.replace("_", " ").capitalize())


def _valor(valor, nivel: int = 3) -> str:
    """Recorrido genérico y ordenado de dicts y listas; todo texto escapado."""
    if isinstance(valor, dict):
        return "".join(f"<h{nivel}>{escape(_titulo(k))}</h{nivel}>{_valor(v, min(nivel + 1, 6))}"
                       for k, v in valor.items() if k not in _OCULTAS and v not in (None, "", [], {}))
    if isinstance(valor, list):
        if all(not isinstance(x, (dict, list)) for x in valor):
            return "<ul>" + "".join(f"<li>{escape(str(x))}</li>" for x in valor) + "</ul>"
        return "".join(f"<section>{_valor(x, nivel)}</section>" for x in valor)
    return f"<p>{escape(str(valor))}</p>"


def _items(items: list[dict]) -> str:
    partes = []
    for n, item in enumerate(items, 1):
        opciones = "".join(
            f'<label data-correcta="{int(k == item.get("correcta"))}" '
            f'data-justificacion="{escape(str(o.get("justificacion", "")), quote=True)}">'
            f'<input type="radio" name="p{n}"> {escape(str(o.get("texto", "")))}</label>'
            for k, o in enumerate(item.get("opciones", [])))
        partes.append(
            f'<fieldset data-item><legend>Pregunta {n}</legend>'
            f'<p class="ctx">{escape(str(item.get("contexto", "")))}</p>'
            f'<p><strong>{escape(str(item.get("pregunta", "")))}</strong></p>{opciones}'
            f'<div class="fb" role="status"></div></fieldset>')
    return "".join(partes)


def exportar_html(recurso: dict, contexto: ContextoClase) -> str:
    herramienta = recurso["herramienta"]
    contenido = recurso["contenido"]
    es_quiz = isinstance(contenido, list) and all(isinstance(i, dict) and "opciones" in i for i in contenido)
    cuerpo = _items(contenido) if es_quiz else _valor(contenido, 2)
    ras = ", ".join(f"{r.id}: {r.texto}" for r in contexto.ra)
    pie = (f"<p>{escape(contexto.asignatura)} · {escape(contexto.clase_id)} · {contexto.fecha:%d/%m/%Y}</p>"
           f"<p><strong>Resultados de aprendizaje:</strong> {escape(ras)}</p>"
           f"<p><strong>Política de IA:</strong> {escape(contexto.politica_ia or 'No indicada en el sílabo')}</p>"
           f"<p><em>{escape(PIE)}</em></p>")
    titulo = NOMBRES.get(herramienta, herramienta)
    return (
        "<!DOCTYPE html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{escape(titulo)} · {escape(contexto.asignatura)}</title><style>{ESTILO}</style></head><body>"
        f"<header><h1>{escape(titulo)}</h1><p class=\"sub\">{escape(contexto.asignatura)} · "
        f"{escape(contexto.momento_titulo)}</p></header><main>{cuerpo}</main><footer>{pie}</footer>"
        + (f"<script>{SCRIPT}</script>" if es_quiz else "") + "</body></html>"
    )
