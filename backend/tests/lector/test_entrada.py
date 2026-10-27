"""Entrada y segmentación del lector (P2, Tarea 1)."""
import pytest

from app.silabo.lector import SilaboIlegible
from app.silabo.lector.entrada import SECCIONES_UTILES, abrir, segmentar
from tests.lector.conftest import datos_personales, fugas


def _pdf_en_blanco() -> bytes:
    """PDF válido de una página sin contenido, con su tabla xref calculada."""
    objetos = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"]
    salida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, cuerpo in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += b"%d 0 obj\n" % n + cuerpo + b"\nendobj\n"
    xref = len(salida)
    salida += b"xref\n0 4\n0000000000 65535 f \n"
    salida += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    salida += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref
    return bytes(salida)


@pytest.mark.parametrize("datos", [
    b"hola",
    b"%PDF" + b"0" * (50 * 1024 * 1024),
    b"%PDF-1.4 roto",
    _pdf_en_blanco(),
], ids=["no_pdf", "grande", "corrupto", "sin_texto"])
def test_rechazos_de_entrada(datos):
    with pytest.raises(SilaboIlegible) as e:
        abrir(datos)
    assert "Traceback" not in str(e.value) and e.value.motivo


def test_ignora_el_indice(pdf_real):
    with abrir(pdf_real("datos")) as pdf:
        assert segmentar(pdf)["II"][0].page_number == 2


@pytest.mark.parametrize("nombre", ["datos", "tic"])
def test_secciones_presentes(pdf_real, nombre):
    with abrir(pdf_real(nombre)) as pdf:
        secciones = segmentar(pdf)
    assert set(secciones) == set(SECCIONES_UTILES)
    assert all(secciones[s] for s in SECCIONES_UTILES)


@pytest.mark.parametrize("nombre", ["datos", "tic"])
def test_segmenta_por_posicion_no_por_pagina(pdf_real, nombre):
    # La portada muestra el nombre del docente (spec §7 lo permite para mostrar); que no
    # llegue al SilaboUTI lo prueba el criterio 5. Aquí: II-VI sin nada de la sección I.
    datos = pdf_real(nombre)
    personales = datos_personales(datos)
    assert len(personales) >= 3, "el helper no encontró los datos de la sección I"
    cuerpo = [s for s in SECCIONES_UTILES if s != "portada"]
    with abrir(datos) as pdf:
        secciones = segmentar(pdf)
        texto = "\n".join(p.extract_text() or "" for s in cuerpo for p in secciones[s])
        tablas = "\n".join(c or "" for s in cuerpo for p in secciones[s]
                           for t in p.extract_tables() for f in t for c in f)
    for fuente in (texto, tablas):
        assert "Nombres y apellidos" not in fuente and "ORCID" not in fuente.upper()
        n = fugas(fuente, personales)
        assert n == 0, f"{n} datos personales de la sección I fuera de ella"
