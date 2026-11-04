import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import app.razonador as modulo
from app.razonador import UMBRAL_DESARROLLO, Razonador, RazonadorInvalido

BASE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BACKEND = Path(__file__).resolve().parents[1]


def _falso(tabla: dict[str, list[float]] | None = None, umbral: float = 0.6, llamadas: list | None = None):
    """Razonador cuyos vectores salen de una tabla (o de un hash fijo) y se cuentan las corridas."""

    def codificar(textos):
        if llamadas is not None:
            llamadas.append(list(textos))
        filas = []
        for t in textos:
            v = np.array(tabla[t] if tabla and t in tabla else [1.0 + len(t) % 5, 1.0 + hash_estable(t) % 7, 0.5], float)
            filas.append(v / np.linalg.norm(v))
        return np.vstack(filas)

    return Razonador(codificar, version="v-falsa", umbral=umbral)


def hash_estable(t: str) -> int:
    return sum(ord(c) * (i + 1) for i, c in enumerate(t))


@pytest.fixture
def falso():
    return _falso()


@pytest.fixture
def falso_sinonimos():
    return _falso({"intrusión informática": [1, 0.1, 0], "ataque a la red": [1, 0.0, 0], "ventas de pan": [0, 0.2, 1]})


@pytest.mark.parametrize("n", [0, 1, 2, 3])
def test_pocos_textos_no_se_agrupan(n):
    llamadas = []
    r = _falso(llamadas=llamadas)
    assert r.temas([f"t{i}" for i in range(n)]) == [[i] for i in range(n)]
    assert llamadas == []


def test_temas_son_deterministas_y_no_pierden_textos(falso):
    t = [f"t{i}" for i in range(8)]
    assert falso.temas(t) == falso.temas(t)
    assert sorted(i for g in falso.temas(t) for i in g) == list(range(8))


def test_temas_separan_grupos_obvios_en_orden_estable():
    tabla = {f"a{i}": [1, 0.01 * i, 0] for i in range(4)} | {f"b{i}": [0, 0.01 * i, 1] for i in range(4)}
    textos = ["b0", "a0", "b1", "a1", "a2", "b2", "a3", "b3"]
    assert _falso(tabla).temas(textos) == [[0, 2, 5, 7], [1, 3, 4, 6]]


def test_temas_con_textos_repetidos_no_falla():
    assert _falso().temas(["x", "x", "x", "x", "x"]) == [[0, 1, 2, 3, 4]]


def test_descarta_el_caso_parecido_aunque_no_comparta_palabras(falso_sinonimos):
    assert falso_sinonimos.casos_libres(["intrusión informática", "ventas de pan"], ["ataque a la red"]) == ["ventas de pan"]


def test_casos_libres_sin_entregables_devuelve_todo_sin_correr_el_modelo():
    llamadas = []
    r = _falso(llamadas=llamadas)
    assert r.casos_libres(["b", "a", "c"], []) == ["b", "a", "c"]
    assert llamadas == []


def test_casos_libres_vacio_y_orden_de_entrada(falso_sinonimos):
    assert falso_sinonimos.casos_libres([], ["ataque a la red"]) == []
    casos = ["ventas de pan", "intrusión informática", "ventas de pan"]
    assert falso_sinonimos.casos_libres(casos, ["ataque a la red"]) == ["ventas de pan", "ventas de pan"]


def test_vectores_vacios(falso):
    assert falso.vectores([]).shape[0] == 0


def test_vectores_por_lotes_conservan_el_orden():
    llamadas = []
    r = _falso(llamadas=llamadas)
    textos = [f"texto {i}" for i in range(70)]
    v = r.vectores(textos)
    assert v.shape[0] == 70 and [len(x) for x in llamadas] == [32, 32, 6]
    assert np.allclose(v[40], r.vectores([textos[40]])[0])


def _carpeta(tmp_path, meta, *, onnx=True, tokenizer=True):
    c = tmp_path / "v1"
    (c / "onnx").mkdir(parents=True)
    if onnx:
        (c / "onnx" / "model.onnx").write_bytes(b"x")
    if tokenizer:
        (c / "tokenizer.json").write_text("{}", encoding="utf-8")
    if meta is not None:
        (c / "metadatos.json").write_text(json.dumps(meta), encoding="utf-8")
    return c


@pytest.fixture
def carpeta_con(tmp_path):
    cuenta = iter(range(100))
    return lambda meta, **kw: _carpeta(tmp_path / f"c{next(cuenta)}", meta, **kw)


@pytest.mark.parametrize("meta", [{"humo": True, "aprobado": False}, {"humo": False, "aprobado": False}])
def test_no_carga_modelo_sin_aprobar(carpeta_con, meta):
    with pytest.raises(RazonadorInvalido):
        Razonador.cargar(carpeta_con(meta), exigir_aprobado=True)


@pytest.mark.parametrize("meta", [
    {"humo": True, "aprobado": True, "umbral": 0.7},
    {"humo": False, "aprobado": False, "umbral": 0.7},
    {"humo": False, "aprobado": True, "umbral": None},
    {"aprobado": True, "umbral": 0.7},
])
def test_exigir_aprobado_rechaza_humo_no_aprobado_o_sin_umbral(carpeta_con, meta):
    with pytest.raises(RazonadorInvalido):
        Razonador.cargar(carpeta_con(meta), exigir_aprobado=True)


def test_carpeta_incompleta_o_ilegible(tmp_path, carpeta_con):
    bueno = {"humo": False, "aprobado": True, "umbral": 0.7}
    for nombre, kw in (("sin_onnx", {"onnx": False}), ("sin_tokenizer", {"tokenizer": False})):
        with pytest.raises(RazonadorInvalido):
            Razonador.cargar(_carpeta(tmp_path / nombre, bueno, **kw), exigir_aprobado=True)
    with pytest.raises(RazonadorInvalido, match="no existe"):
        Razonador.cargar(tmp_path / "nada", exigir_aprobado=False)
    with pytest.raises(RazonadorInvalido, match="metadatos"):
        Razonador.cargar(carpeta_con(None), exigir_aprobado=False)
    c = carpeta_con(bueno)
    (c / "metadatos.json").write_text("{no es json", encoding="utf-8")
    with pytest.raises(RazonadorInvalido, match="metadatos"):
        Razonador.cargar(c, exigir_aprobado=False)


def test_carga_aprobada_usa_umbral_y_longitud_de_metadatos(carpeta_con, monkeypatch):
    visto = {}
    monkeypatch.setattr(modulo, "_abrir", lambda ruta, longitud: visto.setdefault("l", longitud) and (lambda t: np.eye(len(t))))
    r = Razonador.cargar(carpeta_con({"version": "v9", "humo": False, "aprobado": True, "umbral": 0.73, "longitud_maxima": 64}),
                         exigir_aprobado=True)
    assert (r.version, r.umbral, visto["l"]) == ("v9", 0.73, 64)


def test_sin_umbral_en_desarrollo_usa_el_de_desarrollo(carpeta_con, monkeypatch):
    monkeypatch.setattr(modulo, "_abrir", lambda ruta, longitud: lambda t: np.eye(len(t)))
    r = Razonador.cargar(carpeta_con({"humo": True, "aprobado": False, "umbral": None}), exigir_aprobado=False)
    assert r.umbral == UMBRAL_DESARROLLO == 0.6


def test_importar_el_razonador_no_trae_pytorch():
    codigo = "import sys, app.razonador; print(any(m.split('.')[0] in ('torch', 'sentence_transformers') for m in sys.modules))"
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "False"


# --- con el modelo real (.venv-ciencia) ------------------------------------------------

FRASES = ["hola", "Analizar los datos de ventas de la empresa y proponer mejoras. " * 20]


@pytest.fixture(scope="module")
def modelo_humo(tmp_path_factory):
    from ciencia_datos.entrenar import entrenar

    return entrenar(["Identificar requisitos de un sistema.", "Analizar datos de ventas."] * 4, BASE,
                    tmp_path_factory.mktemp("m") / "v0", humo=True, ajuste=False)


@pytest.mark.modelo
def test_onnx_da_los_mismos_vectores_que_el_entrenamiento(modelo_humo):
    from sentence_transformers import SentenceTransformer

    meta = json.loads((modelo_humo / "metadatos.json").read_text(encoding="utf-8"))
    assert meta["longitud_maxima"] == 128
    st = SentenceTransformer(BASE, device="cpu")
    st.max_seq_length = meta["longitud_maxima"]
    esperado = st.encode(FRASES, normalize_embeddings=True)
    obtenido = Razonador.cargar(modelo_humo, exigir_aprobado=False).vectores(FRASES)
    assert np.allclose(obtenido, esperado, atol=1e-3)
