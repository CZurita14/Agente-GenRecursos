import json

import pytest

from app.silabo.modelo import SilaboUTI
from ciencia_datos.corpus import fragmentos, leer_carpeta, tiene_datos_personales


@pytest.fixture
def silabo_datos(silabo) -> SilaboUTI:
    return silabo


def _con_texto(silabo: SilaboUTI, texto: str, limpio: str | None = None) -> SilaboUTI:
    d = silabo.model_dump(mode="json")
    for m in d["momentos"]:
        for s in m["sesiones"]:
            s["contenidos"] = [texto] + ([limpio] if limpio else [])
            s["docente"]["texto"] = texto
            s["practico"]["texto"] = texto
            s["autonomo"]["texto"] = texto
        m["evidencia"] = texto
    for r in d["resultados_aprendizaje"]:
        r["texto"] = texto
    return SilaboUTI.model_validate(d)


def test_fragmentos_toma_solo_contenido_academico(silabo_datos):
    f = fragmentos(silabo_datos)
    assert {x.tipo for x in f} == {"contenido", "actividad", "resultado", "evidencia"}
    assert all(x.codigo_pf == silabo_datos.proyecto_formativo.codigo for x in f)


def test_fragmentos_sin_repetidos_ni_vacios(silabo_datos):
    textos = [x.texto for x in fragmentos(silabo_datos)]
    assert len(textos) == len(set(textos)) and all(t.strip() for t in textos)


@pytest.mark.parametrize("dato", ["ana@uti.edu.ec", "0987654321", "0000-0002-1825-0097"])
def test_descarta_fragmentos_con_datos_personales(silabo_datos, dato):
    f = fragmentos(_con_texto(silabo_datos, f"Contactar a {dato}", "Tema académico limpio"))
    assert dato not in str(f)
    assert "Tema académico limpio" in [x.texto for x in f]


def test_descarta_titulos_con_nombre_propio_y_conserva_texto_academico(silabo_datos):
    f = fragmentos(_con_texto(silabo_datos, "Dra. Ana Ruiz", "Ing. de requisitos"))
    textos = [x.texto for x in f]
    assert "Ing. de requisitos" in textos
    assert not any("Ruiz" in t for t in textos)
    f = fragmentos(_con_texto(silabo_datos, "Ingeniería Civil"))
    assert "Ingeniería Civil" in [x.texto for x in f]


def test_tiene_datos_personales():
    assert tiene_datos_personales("Mgs. María López")
    assert tiene_datos_personales("PhD Carlos Mora")
    assert tiene_datos_personales("ana@uti.edu.ec")
    assert not tiene_datos_personales("Ing. de requisitos")
    assert not tiene_datos_personales("Ingeniería Civil")


def test_descarta_sin_imprimir_el_texto(silabo_datos):
    assert fragmentos(_con_texto(silabo_datos, "Escribir a ana@uti.edu.ec")) == []


def _escribir(carpeta, nombre, datos, codigo=None, aprobado=None, titulo=None):
    d = dict(datos)
    pf = dict(d["proyecto_formativo"])
    if codigo:
        pf["codigo"] = codigo
    if aprobado:
        pf["aprobado"] = aprobado
    if titulo:
        pf["nombre"] = titulo
    d["proyecto_formativo"] = pf
    (carpeta / nombre).write_text(json.dumps(d), encoding="utf-8")


def test_leer_carpeta_lee_json_y_rechaza_ilegibles(tmp_path, datos):
    _escribir(tmp_path, "a.json", datos)
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    (tmp_path / "falso.pdf").write_bytes(b"no es un pdf")
    (tmp_path / "otro.txt").write_text("ignorado", encoding="utf-8")
    silabos, rechazados = leer_carpeta(tmp_path)
    assert len(silabos) == 1
    assert rechazados == ["falso.pdf", "roto.json"]


def test_leer_carpeta_conserva_la_version_mas_reciente_por_codigo(tmp_path, datos):
    _escribir(tmp_path, "a.json", datos, codigo="X-1", aprobado="2024-01-01")
    _escribir(tmp_path, "b.json", datos, codigo="X-1", aprobado="2025-01-01")
    _escribir(tmp_path, "c.json", datos, codigo="Y-2", aprobado="2024-01-01", titulo="de c")
    _escribir(tmp_path, "d.json", datos, codigo="Y-2", aprobado="2024-01-01", titulo="de d")
    silabos, rechazados = leer_carpeta(tmp_path)
    assert rechazados == []
    por_codigo = {s.proyecto_formativo.codigo: s for s in silabos}
    assert set(por_codigo) == {"X-1", "Y-2"}
    assert por_codigo["X-1"].proyecto_formativo.aprobado.year == 2025
    assert por_codigo["Y-2"].proyecto_formativo.nombre == "de d"


def test_leer_carpeta_recorre_subcarpetas_y_conserva_una_version_por_codigo(tmp_path, datos):
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "c").mkdir()
    _escribir(tmp_path / "a" / "b", "x.json", datos, codigo="X-1", aprobado="2024-01-01")
    _escribir(tmp_path / "c", "y.json", datos, codigo="X-1", aprobado="2025-01-01")
    _escribir(tmp_path / "a", "z.json", datos, codigo="Z-9", aprobado="2024-01-01")
    (tmp_path / "c" / "roto.json").write_text("{no es json", encoding="utf-8")
    silabos, rechazados = leer_carpeta(tmp_path)
    por_codigo = {s.proyecto_formativo.codigo: s for s in silabos}
    assert set(por_codigo) == {"X-1", "Z-9"}
    assert por_codigo["X-1"].proyecto_formativo.aprobado.year == 2025
    assert rechazados == ["roto.json"]
