import csv
import hashlib
import json
import math
import re

import numpy as np
import pytest

from ciencia_datos import evaluar as ev
from ciencia_datos.entrenar import huella
from ciencia_datos.evaluar import (
    YaEvaluada, cargar_pares, dictaminar, elegir_umbral, escribir_informe,
    estabilidad, grupos_con_sentido, kappa, mcnemar, medir_puntaje, silueta_frente_al_azar, wilson,
)
from ciencia_datos.separar import dejar_fuera, separar

MEDIDAS_BUENAS = {
    "exhaustividad": 0.9, "mcnemar_p": 0.01, "solo_modelo": 30, "solo_filtro": 5,
    "silueta": 0.3, "silueta_p95": 0.1, "ari": 0.9, "grupos_con_sentido": 0.9, "kappa": 0.7,
    "pares_para_kappa": 150, "positivos_prueba": 80,
}


def test_wilson_coincide_con_lo_calculado():
    assert wilson(14, 16) == pytest.approx((0.640, 0.965), abs=0.001)


def test_umbral_no_usa_la_prueba():
    u = elegir_umbral(np.array([.9, .8, .3, .2]), np.array([1, 1, 0, 0]))
    assert .3 < u <= .8


def test_umbral_maxima_precision_con_exhaustividad_minima():
    sim = np.array([.95, .9, .85, .8, .7, .6, .5, .4, .3, .2])
    y = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 0])
    assert elegir_umbral(sim, y, 1.0) == .5
    y2 = np.array([1, 1, 0, 1, 0, 0, 0, 0, 0, 0])
    assert elegir_umbral(sim, y2, 1.0) == .8
    assert elegir_umbral(sim, y2, 0.5) == .9


def test_umbral_no_cambia_con_las_etiquetas_de_prueba():
    sim_ent, y_ent = np.array([.9, .8, .3, .2]), np.array([1, 1, 0, 0])
    sim_pru = np.array([.9, .6, .5, .1])
    a = medir_puntaje(sim_ent, y_ent, sim_pru, [1, 1, 0, 0])
    b = medir_puntaje(sim_ent, y_ent, sim_pru, [0, 1, 1, 1])
    assert a["umbral"] == b["umbral"]


def test_mcnemar_y_kappa():
    assert mcnemar([True] * 20 + [False] * 5, [False] * 20 + [False] * 5) < .05
    assert mcnemar([True, False], [True, False]) == 1.0
    assert kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1
    assert math.isnan(kappa([1, 1], [1, 1]))


def test_mcnemar_conteos_dan_la_direccion():
    assert ev.mcnemar_conteos([True, True, False, False], [False, False, True, False]) == (2, 1)


def test_kappa_con_acuerdo_parcial():
    assert kappa([1, 1, 0, 0], [1, 0, 0, 0]) == pytest.approx(0.5)


def test_datos_sin_estructura_no_superan_al_azar():
    X = np.random.default_rng(1).normal(size=(60, 32))
    r = silueta_frente_al_azar(X / np.linalg.norm(X, axis=1, keepdims=True), 4)
    assert r["real"] <= r["p95"] + 0.02


def test_datos_con_grupos_claros_superan_al_azar_y_son_estables():
    azar = np.random.default_rng(3)
    centros = np.eye(4, 16) * 5
    X = np.vstack([c + azar.normal(scale=.3, size=(20, 16)) for c in centros])
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    assert silueta_frente_al_azar(X, 4)["supera"] is True
    assert estabilidad(X, 4) > .95


def test_dictamen_exige_todos_los_criterios():
    assert dictaminar(MEDIDAS_BUENAS)["aprobado"] is True
    assert dictaminar({**MEDIDAS_BUENAS, "kappa": .4})["aprobado"] is False
    for clave, malo in [("exhaustividad", .8), ("mcnemar_p", .05), ("silueta", .1), ("ari", .7),
                        ("grupos_con_sentido", .7)]:
        assert dictaminar({**MEDIDAS_BUENAS, clave: malo})["aprobado"] is False, clave


def test_un_modelo_peor_que_el_filtro_se_rechaza_aunque_p_sea_pequeno():
    peor = {**MEDIDAS_BUENAS, "mcnemar_p": 1.9e-06, "solo_modelo": 3, "solo_filtro": 40}
    assert dictaminar(peor)["aprobado"] is False
    assert dictaminar({**MEDIDAS_BUENAS, "solo_modelo": 5, "solo_filtro": 5})["aprobado"] is False


def test_sin_muestra_minima_no_se_aprueba():
    assert dictaminar({**MEDIDAS_BUENAS, "pares_para_kappa": 99})["aprobado"] is False
    assert dictaminar({**MEDIDAS_BUENAS, "positivos_prueba": 59})["aprobado"] is False
    assert dictaminar({**MEDIDAS_BUENAS, "pares_para_kappa": 100, "positivos_prueba": 60})["aprobado"] is True


def test_medida_indefinida_nunca_aprueba():
    for clave in MEDIDAS_BUENAS:
        assert dictaminar({**MEDIDAS_BUENAS, clave: None})["aprobado"] is False
        if clave not in ("pares_para_kappa", "positivos_prueba", "solo_modelo", "solo_filtro"):
            assert dictaminar({**MEDIDAS_BUENAS, clave: math.nan})["aprobado"] is False


def test_dejar_fuera_usa_el_plan_de_separar_y_no_oculta_la_peor():
    mapa = {"PF-1": "A", "PF-2": "A", "PF-3": "B", "PF-4": "B"}
    sim = np.array([.9, .8, .2, .1, .9, .1, .2, .8])
    y = np.array([1, 1, 0, 0, 1, 1, 0, 0])
    codigos = ["PF-1", "PF-2", "PF-1", "PF-2", "PF-3", "PF-4", "PF-3", "PF-4"]
    r = ev.dejar_fuera_pares(sim, y, codigos, dejar_fuera(mapa))
    assert r["peor"] == "B"
    assert r["peor_f1"] == r["por_facultad"]["B"]["f1"] < r["por_facultad"]["A"]["f1"]


def test_f1_cero_cuando_hay_positivos_y_ningun_acierto():
    m = ev.metricas(np.array([0, 0, 1, 1], bool), np.array([1, 1, 0, 0], bool))
    assert m["f1"] == 0.0
    assert math.isnan(ev.metricas(np.array([1, 0], bool), np.array([0, 0], bool))["f1"])


def test_dejar_fuera_lista_las_facultades_excluidas():
    mapa = {"PF-1": "A", "PF-2": "B"}
    r = ev.dejar_fuera_pares(np.array([.9, .1]), np.array([0, 0]), ["PF-1", "PF-2"], dejar_fuera(mapa))
    assert sorted(r["excluidas"]) == ["A", "B"] and r["peor"] is None


def _csv(ruta, filas, cabecera=("caso", "evidencia", "codigo_pf", "docente", "parecido")):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)


def test_cargar_pares_cuenta_rechazos_desacuerdos_y_kappa(tmp_path):
    ruta = tmp_path / "pares.csv"
    _csv(ruta, [
        ("c1", "e1", "PF-A", "ana", "1"), ("c1", "e1", "PF-A", "luis", "1"),
        ("c2", "e2", "PF-A", "ana", "0"), ("c2", "e2", "PF-A", "luis", "1"),  # desacuerdo
        ("c3", "e3", "PF-B", "ana", "0"), ("c3", "e3", "PF-B", "luis", "0"),
        ("c4", "e4", "PF-X", "ana", "1"),  # código en ningún grupo
        ("c5", "e5", "PF-B", "ana", "tal vez"),  # valor inválido
    ])
    r = cargar_pares(ruta, ["PF-A"], ["PF-B"])
    assert r["filas_fuera_de_grupo"] == 1 and r["filas_valor_invalido"] == 1
    assert r["pares_en_desacuerdo"] == 1
    assert {(p["caso"], p["grupo"], p["codigo"]) for p in r["pares"]} == {
        ("c1", "entrenamiento", "PF-A"), ("c3", "prueba", "PF-B")}
    assert r["pares_para_kappa"] == 3 and 0 < r["kappa"] < 1


def _temas(ruta, filas):
    _csv(ruta, filas, ("huella_temas", "grupo", "docente", "tiene_sentido"))


def test_grupos_con_sentido_solo_cuenta_la_huella_del_modelo(tmp_path):
    ruta = tmp_path / "temas.csv"
    _temas(ruta, [("H", "0", "ana", "si"), ("H", "0", "luis", "si"), ("H", "1", "ana", "no"), ("H", "1", "luis", "si"),
                  ("otra", "0", "ana", "no"), ("otra", "1", "ana", "no")])
    assert grupos_con_sentido(ruta, "H", {"0", "1"}) == {"n_grupos": 2, "fraccion": .5}


def test_grupos_sin_juzgar_o_de_mas_dejan_la_fraccion_indefinida(tmp_path):
    ruta = tmp_path / "temas.csv"
    _temas(ruta, [("H", "0", "ana", "si")])  # 1 de 8 grupos juzgado
    assert math.isnan(grupos_con_sentido(ruta, "H", {str(i) for i in range(8)})["fraccion"])
    assert math.isnan(grupos_con_sentido(ruta, "H", set())["fraccion"])  # sobra el grupo 0
    assert math.isnan(grupos_con_sentido(ruta, "otra", {"0"})["fraccion"])  # huella sin filas


def test_informe_se_escribe_por_version_y_el_humo_aparte(tmp_path):
    assert escribir_informe({"v": 1}, tmp_path, "v1", humo=False).name == "v1.json"
    assert escribir_informe({"v": 1}, tmp_path, "v1", humo=True).name == "v1-humo.json"
    assert escribir_informe({"v": 1}, tmp_path, "v1", humo=False, completo=False).name == "v1-incompleta.json"


def test_informe_escribe_nan_como_null_y_floats(tmp_path):
    ruta = escribir_informe({"a": np.float32(.5), "b": math.nan, "c": [np.float64(1)]}, tmp_path, "v", True)
    assert json.loads(ruta.read_text()) == {"a": .5, "b": None, "c": [1.0]}


# --- de extremo a extremo con vectores falsos ---------------------------------------

DIM = 32


def _azar(clave: str):
    return np.random.default_rng(int(hashlib.sha256(clave.encode()).hexdigest()[:8], 16))


def _unitario(v):
    return v / np.linalg.norm(v)


def _vector_falso(bueno: str):
    """Los pares «parecidos» comparten vector solo en la carpeta `bueno`; el resto es azar."""

    def vectorizar(carpeta, textos):
        salida = []
        for t in textos:
            m = re.search(r"(caso|evidencia) secret[oa] (\d+)$", t)
            if m is None:  # fragmentos de sílabo: tres temas claros
                centro = np.eye(DIM)[int(hashlib.sha256(t.encode()).hexdigest(), 16) % 3] * 5
                salida.append(_unitario(centro + _azar(t).normal(scale=.3, size=DIM)))
                continue
            i = int(m.group(2))
            if i % 2 == 1 and carpeta.name == bueno:
                salida.append(_unitario(_azar(f"u{i}").normal(size=DIM) + _azar(t).normal(scale=.1, size=DIM)))
            else:
                salida.append(_unitario(_azar(t).normal(size=DIM)))
        return np.array(salida)

    return vectorizar


FACULTADES = ["FACULTAD DE INGENIERIAS"] * 4 + ["FACULTAD DE CIENCIAS"] * 4


def _carpeta_modelo(ruta, version, ajuste, sep, huella_sep=None, humo=False):
    (ruta / "onnx").mkdir(parents=True)
    (ruta / "onnx" / "model.onnx").write_bytes(f"onnx {version}".encode())
    separacion = {"entrenamiento": sep.entrenamiento, "prueba": sep.prueba}
    (ruta / "metadatos.json").write_text(json.dumps({
        "version": version, "humo": humo, "aprobado": False, "umbral": None, "ajuste": ajuste,
        "huella_separacion": huella_sep or huella(separacion), "separacion": separacion,
    }))


@pytest.fixture
def entorno(tmp_path, datos):
    silabos = tmp_path / "silabos"
    silabos.mkdir()
    codigos = [f"PF-{c}" for c in "ABCDEFGH"]
    for c, fac in zip(codigos, FACULTADES):
        d = json.loads(json.dumps(datos))
        d["proyecto_formativo"]["codigo"] = c
        d["facultad"] = fac
        for i, r in enumerate(d["resultados_aprendizaje"]):
            r["texto"] = f"Resultado {i} propio del sílabo {c}"
        (silabos / f"{c}.json").write_text(json.dumps(d), encoding="utf-8")
    sep = separar({c: "FING" if i < 4 else "FCIE" for i, c in enumerate(codigos)})
    _carpeta_modelo(tmp_path / "ajustado", "v-aj", True, sep)
    _carpeta_modelo(tmp_path / "base", "v-base", False, sep)
    datos_cd = tmp_path / "datos_cd"
    datos_cd.mkdir()
    filas = [(f"caso secreto {i}", f"evidencia secreta {i}", codigos[(i // 2) % 8], d, str(i % 2))
             for i in range(600) for d in ("ana", "luis")]
    _csv(datos_cd / "pares.csv", filas)
    return {"ajustado": tmp_path / "ajustado", "base": tmp_path / "base", "silabos": silabos,
            "datos": datos_cd, "salida": tmp_path / "pruebas", "tmp": tmp_path}


def _correr(e, modelo="ajustado", base="base", bueno="ajustado", **kw):
    return ev.ejecutar(e[modelo], e["silabos"], base_modelo=e[base] if base else None, datos=e["datos"],
                       salida=kw.pop("salida", e["salida"]), vectorizar=_vector_falso(bueno), k=3, **kw)


def _juzgar_temas(e, modelo, sentido="si", bueno="ajustado"):
    """Paso 1 (temas-para-revisar) y los docentes lo juzgan (paso 2 los lee evaluar)."""
    r = ev.temas_para_revisar(e[modelo], e["silabos"], e["datos"] / f"temas-revision-{modelo}.csv",
                              k=3, vectorizar=_vector_falso(bueno))
    _temas(e["datos"] / "temas.csv", [(r["huella"], str(g), d, sentido) for g in range(r["k"]) for d in ("ana", "luis")])
    return r


def _meta(e, modelo):
    return json.loads((e[modelo] / "metadatos.json").read_text())


def test_aprueba_y_escribe_aprobado_y_umbral_solo_en_la_carpeta_elegida(entorno):
    _juzgar_temas(entorno, "ajustado")
    r = _correr(entorno)
    assert r["aprobado"] is True, r
    assert r["modelo_elegido"] == "ajustado" and r["candidatos"].keys() == {"ajustado", "base"}
    assert r["huella_modelo_elegido"] == r["huella_modelo"]
    aj, base = _meta(entorno, "ajustado"), _meta(entorno, "base")
    assert aj["aprobado"] is True and aj["umbral"] is not None
    assert base["aprobado"] is False and base["umbral"] is None


def test_gana_el_base_cuando_el_ajustado_no_lo_supera(entorno):
    _juzgar_temas(entorno, "base", bueno="base")
    r = _correr(entorno, bueno="base")
    assert r["modelo_elegido"] == "base" and "no supera" in r["nota_modelo"]
    assert r["huella_modelo_elegido"] != r["huella_modelo"]
    assert r["aprobado"] is True, r
    assert _meta(entorno, "base")["aprobado"] is True and _meta(entorno, "ajustado")["aprobado"] is False
    assert r["dejar_fuera"]["codificador"] == "base" and "generalizacion_del_ajustado" not in r["dejar_fuera"]


def test_sin_temas_juzgados_de_la_huella_elegida_no_aprueba(entorno):
    _juzgar_temas(entorno, "base", bueno="base")  # juzgaron los temas del otro modelo
    r = _correr(entorno)
    assert r["aprobado"] is False
    escrito = json.loads((entorno["salida"] / "v-aj.json").read_text())
    assert escrito["medidas"]["grupos_con_sentido"] is None and escrito["criterios"]["grupos_con_sentido"] is False
    assert _meta(entorno, "ajustado")["umbral"] is None


def test_el_ajustado_que_gana_informa_que_su_generalizacion_no_se_midio(entorno):
    _juzgar_temas(entorno, "ajustado")
    r = _correr(entorno)
    assert r["dejar_fuera"]["codificador"] == "base"
    assert r["dejar_fuera"]["generalizacion_del_ajustado"] == "no medida"


def test_informe_real_sin_textos_y_con_conteos(entorno):
    _juzgar_temas(entorno, "ajustado")
    r = _correr(entorno)
    contenido = (entorno["salida"] / "v-aj.json").read_text(encoding="utf-8")
    assert "secret" not in contenido and "propio del sílabo" not in contenido
    assert r["humo"] is False and r["conteos"]["pares_en_desacuerdo"] == 0
    assert r["temas"]["k_reducido"] is False and r["n_silabos_prueba"] == 2
    assert "umbral_con_entrenamiento" not in r["medidas"]


def test_segunda_evaluacion_se_rechaza_tambien_con_otra_salida(entorno):
    _juzgar_temas(entorno, "ajustado")
    _correr(entorno)
    with pytest.raises(YaEvaluada):
        _correr(entorno)
    with pytest.raises(YaEvaluada):
        _correr(entorno, salida=entorno["tmp"] / "otra")
    assert (entorno["ajustado"] / "evaluacion.candado").exists()
    assert (entorno["base"] / "evaluacion.candado").exists()


def test_el_candado_del_base_tambien_cuenta(entorno):
    _juzgar_temas(entorno, "base")
    _correr(entorno, modelo="base", base=None)  # el base evaluado solo
    with pytest.raises(YaEvaluada):
        _correr(entorno)
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()


def test_humo_se_rechaza_sobre_una_version_real_y_al_reves(entorno):
    with pytest.raises(ValueError, match="humo"):
        _correr(entorno, humo=True)
    meta = _meta(entorno, "ajustado")
    (entorno["ajustado"] / "metadatos.json").write_text(json.dumps({**meta, "humo": True}))
    with pytest.raises(ValueError, match="humo"):
        _correr(entorno)
    assert not (entorno["salida"] / "v-aj.json").exists()
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()


def test_humo_nunca_aprueba_no_usa_etiquetas_y_se_repite(entorno):
    meta = _meta(entorno, "ajustado")
    (entorno["ajustado"] / "metadatos.json").write_text(json.dumps({**meta, "humo": True}))
    (entorno["datos"] / "pares.csv").unlink()
    r = _correr(entorno, base=None, humo=True)
    assert r["humo"] is True and r["aprobado"] is False
    assert (entorno["salida"] / "v-aj-humo.json").exists()
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()
    _correr(entorno, base=None, humo=True)


def test_base_invalido_se_rechaza_antes_de_tomar_candados(entorno):
    for cambio in ({"ajuste": True}, {"humo": True}, {"huella_separacion": "otra"}):
        meta = _meta(entorno, "base")
        (entorno["base"] / "metadatos.json").write_text(json.dumps({**meta, **cambio}))
        with pytest.raises(ValueError, match="base"):
            _correr(entorno)
        (entorno["base"] / "metadatos.json").write_text(json.dumps(meta))
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()


def test_sin_csv_el_informe_lo_dice_no_aprueba_y_no_toma_candado(entorno):
    r = _correr(entorno)  # sin temas.csv
    assert r["aprobado"] is False and "temas.csv" in r["motivo"]
    assert (entorno["salida"] / "v-aj-incompleta.json").exists()
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()


def test_encabezados_invalidos_se_rechazan_antes_del_candado(entorno):
    _csv(entorno["datos"] / "temas.csv", [("0", "ana", "si")], ("grupo", "docente", "tiene_sentido"))
    with pytest.raises(ValueError, match="temas.csv"):
        _correr(entorno)
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()


def test_huella_de_separacion_que_no_coincide_no_aprueba(entorno):
    sep = _meta(entorno, "ajustado")["separacion"]
    for nombre in ("ajustado", "base"):
        (entorno[nombre] / "metadatos.json").write_text(json.dumps({**_meta(entorno, nombre), "huella_separacion": "x"}))
    _juzgar_temas(entorno, "ajustado")
    r = _correr(entorno)
    assert r["aprobado"] is False and any("huella" in p for p in r["problemas"])


def test_silabo_de_prueba_ausente_no_aprueba(entorno):
    _juzgar_temas(entorno, "ajustado")
    prueba = _meta(entorno, "ajustado")["separacion"]["prueba"][0]
    (entorno["silabos"] / f"{prueba}.json").unlink()
    r = _correr(entorno)
    assert r["aprobado"] is False and r["n_silabos_prueba"] == 1 and any("ausente" in p for p in r["problemas"])


def test_temas_para_revisar_escribe_huella_grupo_texto_sin_candado(entorno):
    destino = entorno["datos"] / "rev.csv"
    r = ev.temas_para_revisar(entorno["ajustado"], entorno["silabos"], destino, k=3, vectorizar=_vector_falso("ajustado"))
    filas = list(csv.DictReader(open(destino, encoding="utf-8")))
    assert filas and set(filas[0]) == {"huella_temas", "grupo", "texto"}
    assert {f["huella_temas"] for f in filas} == {r["huella"]}
    assert {f["grupo"] for f in filas} == {"0", "1", "2"} and r["k_reducido"] is False
    assert not (entorno["ajustado"] / "evaluacion.candado").exists()
    # misma huella al repetir; otro modelo, otra huella
    again = ev.temas_para_revisar(entorno["ajustado"], entorno["silabos"], destino, k=3, vectorizar=_vector_falso("ajustado"))
    otro = ev.temas_para_revisar(entorno["base"], entorno["silabos"], destino, k=3, vectorizar=_vector_falso("ajustado"))
    assert again["huella"] == r["huella"] != otro["huella"]


def test_k_reducido_por_pocos_textos_se_informa(entorno):
    r = ev.temas_para_revisar(entorno["ajustado"], entorno["silabos"], entorno["datos"] / "rev.csv", k=500,
                              vectorizar=_vector_falso("ajustado"))
    assert r["k_reducido"] is True and r["k"] < 500
