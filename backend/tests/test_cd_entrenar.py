import json

import pytest

from ciencia_datos import entrenar as modulo
from ciencia_datos.corpus import fragmentos, leer_carpeta
from ciencia_datos.entrenar import entrenar, main
from ciencia_datos.separar import separar

BASE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TEXTOS_SINTETICOS = [
    "Identificar los requisitos funcionales de un sistema de información.",
    "Diseñar un modelo de datos relacional para una tienda en línea.",
    "Calcular la resistencia equivalente de un circuito en serie.",
    "Analizar el flujo de caja de una empresa mediana.",
    "Elaborar un plano arquitectónico con criterios de accesibilidad.",
    "Aplicar pruebas unitarias a un servicio web.",
    "Interpretar el balance general de una organización.",
    "Representar gráficamente una distribución de frecuencias.",
]


def _carpeta(tmp_path, datos, codigos_y_facultades):
    carpeta = tmp_path / "silabos"
    carpeta.mkdir()
    for codigo, facultad in codigos_y_facultades:
        d = json.loads(json.dumps(datos))
        d["proyecto_formativo"]["codigo"] = codigo
        d["facultad"] = facultad
        # Texto propio de cada sílabo, para detectar cualquier fuga hacia entrenamiento.
        for r in d["resultados_aprendizaje"]:
            r["texto"] = f"Resultado propio del sílabo {codigo}"
        for m in d["momentos"]:
            m["evidencia"] = f"Evidencia propia del sílabo {codigo}"
        (carpeta / f"{codigo}.json").write_text(json.dumps(d), encoding="utf-8")
    return carpeta


@pytest.fixture
def dos_silabos(tmp_path, datos):
    return _carpeta(tmp_path, datos, [("PF-A", "FACULTAD DE INGENIERIAS"), ("PF-B", "FACULTAD DE INGENIERIAS")])


@pytest.fixture
def cuatro_silabos(tmp_path, datos):
    return _carpeta(tmp_path, datos, [(f"PF-{c}", "FACULTAD DE INGENIERIAS") for c in "ABCD"])


def _grupos(carpeta):
    silabos, _ = leer_carpeta(carpeta)
    mapa = {s.proyecto_formativo.codigo: "FING" for s in silabos}
    sep = separar(mapa)
    por_codigo = {s.proyecto_formativo.codigo: s for s in silabos}
    textos = lambda codigos: {f.texto for c in codigos for f in fragmentos(por_codigo[c])}
    return textos(sep.entrenamiento), textos(sep.prueba)


def _capturar_textos(monkeypatch):
    vistos: set[str] = set()

    def falso(textos, base, salida, **kw):
        vistos.update(textos)
        return salida

    monkeypatch.setattr(modulo, "entrenar", falso)
    return vistos


def test_cli_rechaza_pocos_silabos_sin_humo(tmp_path, dos_silabos):
    with pytest.raises(SystemExit, match="mínimo"):
        main(["--silabos", str(dos_silabos), "--salida", str(tmp_path / "v")])


def test_solo_entrena_con_el_grupo_de_entrenamiento(tmp_path, monkeypatch, cuatro_silabos):
    vistos = _capturar_textos(monkeypatch)
    main(["--silabos", str(cuatro_silabos), "--salida", str(tmp_path / "v"), "--humo"])
    entrenamiento, prueba = _grupos(cuatro_silabos)
    exclusivos_de_prueba = prueba - entrenamiento
    assert exclusivos_de_prueba and not vistos & exclusivos_de_prueba
    assert vistos == entrenamiento


def test_cli_solo_imprime_conteos_y_pasa_metadatos(tmp_path, monkeypatch, cuatro_silabos, capsys):
    recibido = {}

    def falso(textos, base, salida, **kw):
        recibido.update(kw)
        return salida

    monkeypatch.setattr(modulo, "entrenar", falso)
    main(["--silabos", str(cuatro_silabos), "--salida", str(tmp_path / "v"), "--humo", "--sin-ajuste"])
    salida = capsys.readouterr().out
    assert "propio del sílabo" not in salida and "sílabos=4" in salida
    meta = recibido["metadatos"]
    assert recibido["ajuste"] is False and recibido["humo"] is True
    assert (meta["n_entrenamiento"], meta["n_prueba"]) == (3, 1)
    assert set(meta["separacion"]) == {"entrenamiento", "prueba"}
    assert modulo.huella(meta["separacion"]) == meta["huella_separacion"]


def test_facultad_fuera_del_catalogo_conserva_su_nombre_normalizado(datos):
    from app.silabo.modelo import SilaboUTI

    datos["facultad"] = "Facultad Inventada"
    mapa, sin_sigla = modulo.codigo_a_facultad([SilaboUTI.model_validate(datos)], {})
    assert list(mapa.values()) == ["FACULTAD INVENTADA"] and sin_sigla == 1


@pytest.fixture(scope="module")
def modelo_humo(tmp_path_factory):
    return entrenar(TEXTOS_SINTETICOS, BASE, tmp_path_factory.mktemp("m") / "v0", humo=True)


@pytest.mark.modelo
def test_entrena_con_humo_y_deja_metadatos(modelo_humo):
    m = json.loads((modelo_humo / "metadatos.json").read_text(encoding="utf-8"))
    assert m["humo"] is True and m["aprobado"] is False and m["umbral"] is None
    assert m["ajuste"] is True and m["version"] == "v0" and m["base"] == BASE
    assert (modelo_humo / "onnx" / "model.onnx").exists()
    assert (modelo_humo / "tokenizer.json").exists()


@pytest.mark.modelo
def test_el_onnx_corre_con_frases_cortas_y_largas(modelo_humo):
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    sesion = ort.InferenceSession(str(modelo_humo / "onnx" / "model.onnx"))
    tok = Tokenizer.from_file(str(modelo_humo / "tokenizer.json"))
    nombres = {i.name for i in sesion.get_inputs()}
    assert {"input_ids", "attention_mask"} <= nombres
    for frase in ["Hola.", "Analizar los datos de ventas de la empresa. " * 12]:
        e = tok.encode(frase)
        entrada = {
            "input_ids": np.array([e.ids], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask], dtype=np.int64),
        }
        if "token_type_ids" in nombres:
            entrada["token_type_ids"] = np.array([e.type_ids], dtype=np.int64)
        (oculto,) = sesion.run(["last_hidden_state"], entrada)
        assert oculto.shape == (1, len(e.ids), 384) and np.isfinite(oculto).all()


@pytest.mark.modelo
def test_sin_ajuste_exporta_el_modelo_base(tmp_path):
    ruta = entrenar(TEXTOS_SINTETICOS, BASE, tmp_path / "base", ajuste=False)
    m = json.loads((ruta / "metadatos.json").read_text(encoding="utf-8"))
    assert m["ajuste"] is False and m["epocas"] == 0 and m["aprobado"] is False
    assert (ruta / "onnx" / "model.onnx").exists()
