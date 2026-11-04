import csv
import hashlib
import json
import math

import numpy as np
import pytest

from ciencia_datos import evaluar as ev
from ciencia_datos.evaluar import (
    YaEvaluada, cargar_pares, dejar_fuera_pares, dictaminar, elegir_umbral, escribir_informe,
    estabilidad, grupos_con_sentido, kappa, mcnemar, silueta_frente_al_azar, wilson,
)
from ciencia_datos.separar import separar

MEDIDAS_BUENAS = {
    "exhaustividad": 0.9, "mcnemar_p": 0.01, "silueta": 0.3, "silueta_p95": 0.1, "ari": 0.9,
    "grupos_con_sentido": 0.9, "kappa": 0.7, "umbral_con_entrenamiento": True,
}


def test_wilson_coincide_con_lo_calculado():
    assert wilson(14, 16) == pytest.approx((0.640, 0.965), abs=0.001)


def test_umbral_no_usa_la_prueba():
    u = elegir_umbral(np.array([.9, .8, .3, .2]), np.array([1, 1, 0, 0]))
    assert .3 < u <= .8


def test_umbral_maxima_precision_con_exhaustividad_minima():
    sim = np.array([.95, .9, .85, .8, .7, .6, .5, .4, .3, .2])
    y = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 0])
    # Precisión 1 desde 0,5; con exhaustividad mínima 1 hace falta llegar a 0,5.
    assert elegir_umbral(sim, y, 1.0) == .5
    # Un positivo mal puesto fuerza a bajar el umbral y a perder precisión.
    y2 = np.array([1, 1, 0, 1, 0, 0, 0, 0, 0, 0])
    assert elegir_umbral(sim, y2, 1.0) == .8
    assert elegir_umbral(sim, y2, 0.5) == .9


def test_mcnemar_y_kappa():
    assert mcnemar([True] * 20 + [False] * 5, [False] * 20 + [False] * 5) < .05
    assert mcnemar([True, False], [True, False]) == 1.0
    assert kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1
    assert math.isnan(kappa([1, 1], [1, 1]))


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
                        ("grupos_con_sentido", .7), ("umbral_con_entrenamiento", False)]:
        assert dictaminar({**MEDIDAS_BUENAS, clave: malo})["aprobado"] is False, clave


def test_medida_indefinida_nunca_aprueba():
    for clave in MEDIDAS_BUENAS:
        assert dictaminar({**MEDIDAS_BUENAS, clave: None})["aprobado"] is False
        if clave != "umbral_con_entrenamiento":
            assert dictaminar({**MEDIDAS_BUENAS, clave: math.nan})["aprobado"] is False


def test_dejar_fuera_informa_la_peor_facultad():
    sim = np.array([.9, .8, .2, .1, .9, .1, .2, .8])
    y = np.array([1, 1, 0, 0, 1, 1, 0, 0])
    r = dejar_fuera_pares(sim, y, ["A"] * 4 + ["B"] * 4)
    assert r["peor"] == "B"
    assert r["peor_f1"] == r["por_facultad"]["B"]["f1"] < r["por_facultad"]["A"]["f1"]


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
    assert {(p["caso"], p["grupo"]) for p in r["pares"]} == {("c1", "entrenamiento"), ("c3", "prueba")}
    assert r["pares_para_kappa"] == 3 and 0 < r["kappa"] < 1


def test_grupos_con_sentido_por_mayoria(tmp_path):
    ruta = tmp_path / "temas.csv"
    _csv(ruta, [("g1", "ana", "si"), ("g1", "luis", "si"), ("g2", "ana", "no"), ("g2", "luis", "si")],
         ("grupo", "docente", "tiene_sentido"))
    assert grupos_con_sentido(ruta) == {"n_grupos": 2, "fraccion": .5}


def test_informe_real_se_rechaza_la_segunda_vez_y_el_humo_se_repite(tmp_path):
    escribir_informe({"v": 1}, tmp_path, "v1", humo=False)
    with pytest.raises(YaEvaluada):
        escribir_informe({"v": 2}, tmp_path, "v1", humo=False)
    escribir_informe({"v": 1}, tmp_path, "v1", humo=True)
    escribir_informe({"v": 2}, tmp_path, "v1", humo=True)
    assert json.loads((tmp_path / "v1-humo.json").read_text())["v"] == 2


def test_informe_escribe_nan_como_null_y_floats(tmp_path):
    ruta = escribir_informe({"a": np.float32(.5), "b": math.nan, "c": [np.float64(1)]}, tmp_path, "v", True)
    assert json.loads(ruta.read_text()) == {"a": .5, "b": None, "c": [1.0]}


# --- de extremo a extremo con vectores falsos ---------------------------------------


def _vector_falso(carpeta, textos):
    out = []
    for t in textos:
        azar = np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:8], 16))
        v = azar.normal(size=16)
        out.append(v / np.linalg.norm(v))
    return np.array(out)


@pytest.fixture
def entorno(tmp_path, datos):
    silabos = tmp_path / "silabos"
    silabos.mkdir()
    codigos = [f"PF-{c}" for c in "ABCDEFGH"]
    for c in codigos:
        d = json.loads(json.dumps(datos))
        d["proyecto_formativo"]["codigo"] = c
        d["facultad"] = "FACULTAD DE INGENIERIAS"
        for i, r in enumerate(d["resultados_aprendizaje"]):
            r["texto"] = f"Resultado {i} propio del sílabo {c}"
        (silabos / f"{c}.json").write_text(json.dumps(d), encoding="utf-8")
    sep = separar({c: "FING" for c in codigos})
    modelo = tmp_path / "modelo"
    (modelo / "onnx").mkdir(parents=True)
    (modelo / "onnx" / "model.onnx").write_bytes(b"onnx falso")
    (modelo / "metadatos.json").write_text(json.dumps({
        "version": "v-test", "humo": False, "aprobado": False, "umbral": None, "ajuste": False,
        "huella_separacion": "h", "separacion": {"entrenamiento": sep.entrenamiento, "prueba": sep.prueba},
    }))
    datos_cd = tmp_path / "datos_cd"
    datos_cd.mkdir()
    filas = [(f"caso secreto {i}", f"evidencia secreta {i}", codigos[i % 8], d, str(i % 2))
             for i in range(40) for d in ("ana", "luis")]
    _csv(datos_cd / "pares.csv", filas)
    _csv(datos_cd / "temas.csv", [("g1", "ana", "si"), ("g1", "luis", "si")], ("grupo", "docente", "tiene_sentido"))
    return {"modelo": modelo, "silabos": silabos, "datos": datos_cd, "salida": tmp_path / "pruebas"}


def _correr(e, **kw):
    return ev.ejecutar(e["modelo"], e["silabos"], datos=e["datos"], salida=e["salida"],
                       vectorizar=_vector_falso, k=3, **kw)


def evaluar_dos_veces(e):
    _correr(e)
    try:
        _correr(e)
    except YaEvaluada:
        return "ya evaluada"


def test_segunda_evaluacion_de_la_misma_version_se_rechaza(entorno):
    assert evaluar_dos_veces(entorno) == "ya evaluada"


def test_informe_real_sin_textos_y_con_conteos(entorno):
    r = _correr(entorno)
    contenido = (entorno["salida"] / "v-test.json").read_text(encoding="utf-8")
    assert "secret" not in contenido and "propio del sílabo" not in contenido
    assert r["humo"] is False and r["conteos"]["pares_en_desacuerdo"] == 0
    assert set(r["dejar_fuera"]) == {"por_facultad", "peor", "peor_f1"}


def test_sin_csv_el_informe_lo_dice_y_no_aprueba(entorno):
    (entorno["datos"] / "temas.csv").unlink()
    r = _correr(entorno)
    assert r["aprobado"] is False and "temas.csv" in r["motivo"]
    assert not (entorno["salida"] / "v-test.json").exists()  # no consume el cerrojo


def test_humo_nunca_aprueba_y_no_usa_etiquetas(entorno):
    (entorno["datos"] / "pares.csv").unlink()
    r = _correr(entorno, humo=True)
    assert r["humo"] is True and r["aprobado"] is False
    assert (entorno["salida"] / "v-test-humo.json").exists()
    _correr(entorno, humo=True)  # se puede repetir


def test_aprobado_en_metadatos_solo_si_todo_pasa(entorno):
    _correr(entorno)
    meta = json.loads((entorno["modelo"] / "metadatos.json").read_text())
    assert meta["aprobado"] is False and meta["umbral"] is None  # kappa y azar no alcanzan
