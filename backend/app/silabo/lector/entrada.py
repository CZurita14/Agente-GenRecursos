"""Entrada del lector: validación del PDF y segmentación por secciones (spec §7).

Las secciones I (perfil del docente) y VII (firmas) se recortan del área de la
página antes de extraer texto o tablas: sus datos nunca entran al proceso.
"""
import io
import re

import pdfplumber

from app.silabo.lector.errores import SilaboIlegible

TAMANO_MAXIMO = 50 * 1024 * 1024
MINIMO_CARACTERES = 200
# Los sílabos reales tienen 10-15 páginas; el tope evita que un PDF malicioso agote memoria.
MAX_PAGINAS = 60
# El pie «Sílabo … Generado por <usuario> el <fecha> · Página n de m» identifica a una persona.
_PIE = re.compile(r"Generado por|Página \d+ de \d+")
SECCIONES_UTILES = ("portada", "II", "III", "IV", "V", "VI")
_ORDEN = ("I", "II", "III", "IV", "V", "VI", "VII")
_TITULO = re.compile(r"^(I|II|III|IV|V|VI|VII)\.\s+[A-ZÁÉÍÓÚÑ ]+$")


def abrir(datos: bytes) -> pdfplumber.PDF:
    """Abre el PDF tras comprobar firma, tamaño y capa de texto."""
    if not datos.startswith(b"%PDF"):
        raise SilaboIlegible("El archivo no es un PDF.")
    if len(datos) > TAMANO_MAXIMO:
        raise SilaboIlegible("El PDF supera los 50 MB.")
    pdf = None
    try:
        pdf = pdfplumber.open(io.BytesIO(datos))
        if len(pdf.pages) > MAX_PAGINAS:
            raise SilaboIlegible(f"El PDF tiene más de {MAX_PAGINAS} páginas; no parece un sílabo.")
        caracteres = 0
        for pagina in pdf.pages:
            caracteres += len(pagina.chars)
            if caracteres >= MINIMO_CARACTERES:
                return pdf
        raise SilaboIlegible("El PDF no tiene texto seleccionable (¿es un escaneo?).")
    except SilaboIlegible:
        if pdf is not None:
            pdf.close()
        raise
    except Exception:
        if pdf is not None:
            pdf.close()
        # Cifrado o corrupto: no se reenvía el detalle de la biblioteca.
        raise SilaboIlegible("El PDF está dañado o protegido y no se puede leer.") from None


def _titulos(pdf) -> dict[str, tuple[int, float]]:
    """Última aparición de cada título de sección: (índice de página, top).

    La primera aparición está en el índice de la portada; la última es la real.
    """
    hallados: dict[str, tuple[int, float]] = {}
    for indice, pagina in enumerate(pdf.pages):
        lineas: dict[int, list[dict]] = {}
        for palabra in pagina.extract_words():
            lineas.setdefault(round(palabra["top"]), []).append(palabra)
        for top in sorted(lineas):
            palabras = sorted(lineas[top], key=lambda p: p["x0"])
            m = _TITULO.match(" ".join(p["text"] for p in palabras))
            if m:
                hallados[m.group(1)] = (indice, min(p["top"] for p in palabras))
    return hallados


def _inicio_pie(pagina) -> float:
    """Top de la primera línea del pie de página (o el alto de la página si no tiene)."""
    tops = [m["top"] for m in pagina.search(_PIE.pattern)]
    return min(tops) - 1 if tops else pagina.height


def _recortes(pdf, desde: tuple[int, float], hasta: tuple[int, float] | None) -> list:
    """Páginas recortadas entre dos posiciones, sin el pie (hasta=None: fin del documento)."""
    fin = hasta or (len(pdf.pages) - 1, pdf.pages[-1].height)
    partes = []
    for indice in range(desde[0], fin[0] + 1):
        pagina = pdf.pages[indice]
        arriba = desde[1] if indice == desde[0] else 0
        abajo = min(fin[1] if indice == fin[0] else pagina.height, _inicio_pie(pagina))
        if abajo - arriba > 1:
            # within_bbox (no crop): descarta lo que solo roza el borde, como el pie o la sección vecina.
            partes.append(pagina.within_bbox((0, arriba, pagina.width, abajo)))
    return partes


def segmentar(pdf) -> dict[str, list]:
    """Páginas recortadas de cada sección útil; I y VII no se devuelven."""
    titulos = _titulos(pdf)
    faltan = [n for n in _ORDEN if n not in titulos]
    if faltan:
        raise SilaboIlegible("No se reconoce la plantilla institucional del sílabo.")
    posiciones = [titulos[n] for n in _ORDEN]
    if posiciones != sorted(posiciones):
        raise SilaboIlegible("No se reconoce la plantilla institucional del sílabo.")
    secciones = {"portada": _recortes(pdf, (0, 0), titulos["I"])}
    for k, nombre in enumerate(_ORDEN):
        if nombre in SECCIONES_UTILES:
            siguiente = titulos[_ORDEN[k + 1]] if k + 1 < len(_ORDEN) else None
            secciones[nombre] = _recortes(pdf, titulos[nombre], siguiente)
    return secciones


def seccion_privada(pdf, nombre: str) -> list:
    """Recorte de la sección I o VII. Solo para pruebas de no-fuga: nunca se extrae en producción."""
    titulos = _titulos(pdf)
    k = _ORDEN.index(nombre)
    return _recortes(pdf, titulos[nombre], titulos[_ORDEN[k + 1]] if k + 1 < len(_ORDEN) else None)
