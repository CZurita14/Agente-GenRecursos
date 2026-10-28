"""P6b T2: HTML autónomo para Canvas (spec §13): escapado, sin recursos externos y con el pie."""
import re

from app.exportar.html import PIE, exportar_html
from app.herramientas.sin_ia import generar_sin_ia
from app.silabo.contexto import contexto_clase, contexto_por_id
from tests.test_generacion_api import HEADERS, entorno  # noqa: F401

MALICIOSO = '<script>alert(1)</script>"><img src=x onerror=alert(2)>'


def _item(i, pregunta="¿Qué prueba corresponde?"):
    return {"item_id": f"i{i}", "nivel": "resolutivo", "foco": "f", "ra": "RA2", "contenido": "C",
            "contexto": "Una empresa ficticia mide tiempos.", "pregunta": pregunta, "correcta": 1,
            "opciones": [{"texto": f"Opción {k}", "justificacion": f"Porque {k}", "error_que_representa": "e"}
                         for k in range(4)], "razonamiento": ["a", "b"]}


def _recurso(herramienta, contenido, ambito="M2-S1"):
    return {"herramienta": herramienta, "ambito_id": ambito, "contenido": contenido}


def test_html_cuestionario_autocorregible(silabo):
    html = exportar_html(_recurso("cuestionario", [_item(1), _item(2)]), contexto_clase(silabo, "M2-S1"))
    assert html.startswith("<!DOCTYPE html>") and "<script>" in html
    assert not re.search(r"\b(src|href)\s*=\s*[\"']?https?:", html)  # Sin recursos externos.
    assert "Opción 3" in html and "Porque 2" in html and 'data-correcta="1"' in html
    assert html.count('type="radio"') == 8


def test_html_escapa_contenido(silabo):
    html = exportar_html(_recurso("cuestionario", [_item(1, pregunta=MALICIOSO)]), contexto_clase(silabo, "M2-S1"))
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x" not in html and "onerror=alert(2)>" not in html


def test_html_pie_y_politica(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    html = exportar_html(_recurso("cuestionario", [_item(1)]), ctx)
    assert PIE == "Recurso generado con asistencia de IA y revisado por el docente"
    assert PIE in html and ctx.asignatura in html and "M2-S1" in html
    assert ctx.politica_ia[:40] in html and ctx.ra[0].id in html


def test_html_secciones(silabo):
    ficha = {"conceptual": {"ideas_clave": ["Idea A", "Idea B"], "relacion_ra": "Se relaciona", "errores_frecuentes": ["E1"]},
             "aplicacion": {"ejemplo": {"enunciado": "Enun", "pasos": ["P1"], "resultado": "R"}, "autocomprobacion": ["Q1"]}}
    html = exportar_html(_recurso("ficha_clase", ficha), contexto_clase(silabo, "M2-S1"))
    assert "Ideas clave" in html and "<li>Idea A</li>" in html and "Autocomprobación" in html
    assert html.index("Ideas clave") < html.index("Ejemplo resuelto") < html.index("Autocomprobación")
    assert "<ol><li>P1</li></ol>" in html
    hoja = generar_sin_ia("hoja_ruta", silabo, "asignatura")
    html = exportar_html(_recurso("hoja_ruta", hoja, "asignatura"), contexto_por_id(silabo, "asignatura"))
    assert "Calendario de clases" in html and "<table>" in html and "numero_clase" not in html.lower() and silabo.problema.producto_final[:30] in html


def _producir_validado(entorno):
    _, _, d, aid, producir = entorno
    recurso = producir()
    r = d.post(f"/asignaturas/{aid}/recursos/{recurso['id']}/validar", json={"revision": recurso["revision"]}, headers=HEADERS)
    assert r.status_code == 200
    return d, aid, recurso


def test_exportar_sin_validar_409(entorno):
    _, _, d, aid, producir = entorno
    recurso = producir()
    assert d.get(f"/asignaturas/{aid}/recursos/{recurso['id']}/exportar?formato=html").status_code == 409


def test_exportar_validado_200_attachment(entorno):
    d, aid, recurso = _producir_validado(entorno)
    r = d.get(f"/asignaturas/{aid}/recursos/{recurso['id']}/exportar?formato=html")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    disposicion = r.headers["content-disposition"]
    assert disposicion.startswith("attachment") and re.search(r'filename="cuestionario-M2-S1\.html"', disposicion)
    assert PIE in r.text


def test_formato_no_soportado_422(entorno):
    d, aid, recurso = _producir_validado(entorno)
    assert d.get(f"/asignaturas/{aid}/recursos/{recurso['id']}/exportar?formato=qti").status_code == 422
