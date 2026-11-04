"""Evaluación del codificador con el 30 % reservado, una sola vez por versión.

Compara el filtro por palabras actual (`_casos_libres`), TF-IDF, el modelo base y el
ajustado. El umbral se elige solo con el 70 % y se evalúa en el 30 %. Los informes
contienen cifras y huellas, nunca textos. Las métricas indefinidas se escriben como
`null` y nunca cumplen un criterio.

Los vectores salen del ONNX con `onnxruntime` y `tokenizers` (agrupación media con la
máscara y normalización L2) en `vectores`, que las pruebas reemplazan por vectores fijos.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from app.agentes.facultades import cargar_catalogo
from app.agentes.planificador import _casos_libres
from ciencia_datos.corpus import fragmentos, leer_carpeta
from ciencia_datos.entrenar import RAIZ, codigo_a_facultad

EXHAUSTIVIDAD_UMBRAL = 0.90  # al elegir el umbral con el 70 %
EXHAUSTIVIDAD_MINIMA = 0.85  # exigida en el 30 %
ALFA = 0.05
ARI_MINIMO = 0.80
SENTIDO_MINIMO = 0.80
KAPPA_MINIMO = 0.60
LONGITUD_MAXIMA = 128
SALIDA_POR_DEFECTO = RAIZ / "pruebas" / "ciencia_datos"
_SI = {"1", "si", "sí", "true", "verdadero", "s", "x", "yes"}
_NO = {"0", "no", "false", "falso", "n"}


class YaEvaluada(Exception):
    """La versión ya tiene informe real: el 30 % no se evalúa dos veces."""


# --- estadística --------------------------------------------------------------------


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson al 95 % para una proporción k/n."""
    if n <= 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centro - mitad, centro + mitad)


def _metricas(pred: np.ndarray, y: np.ndarray) -> dict:
    pred, y = np.asarray(pred, bool), np.asarray(y, bool)
    tp = int((pred & y).sum())
    precision = tp / pred.sum() if pred.sum() else math.nan
    exhaustividad = tp / y.sum() if y.sum() else math.nan
    if math.isnan(precision) or math.isnan(exhaustividad):
        f1 = math.nan
    else:
        f1 = 2 * precision * exhaustividad / (precision + exhaustividad) if tp else 0.0
    return {"precision": precision, "exhaustividad": exhaustividad, "f1": f1}


def elegir_umbral(sim, etiquetas, exhaustividad_min: float = EXHAUSTIVIDAD_UMBRAL) -> float:
    """Umbral (predice parecido si sim >= umbral) de máxima precisión con exhaustividad >= mínimo.

    En empate de precisión gana el umbral más bajo. Solo debe recibir el 70 %.
    """
    sim, y = np.asarray(sim, float), np.asarray(etiquetas, bool)
    if not y.any():
        raise ValueError("sin ejemplos positivos no hay umbral")
    mejor, mejor_precision = float(sim.min()), -1.0
    for t in sorted(set(sim.tolist())):
        pred = sim >= t
        m = _metricas(pred, y)
        if m["exhaustividad"] >= exhaustividad_min and m["precision"] > mejor_precision + 1e-12:
            mejor, mejor_precision = float(t), m["precision"]
    return mejor


def mcnemar(a_ok, b_ok) -> float:
    """Valor p exacto (bilateral) de McNemar entre dos clasificadores sobre los mismos pares."""
    a, b = np.asarray(a_ok, bool), np.asarray(b_ok, bool)
    solo_a, solo_b = int((a & ~b).sum()), int((~a & b).sum())
    n = solo_a + solo_b
    if n == 0:
        return 1.0
    cola = sum(math.comb(n, i) for i in range(min(solo_a, solo_b) + 1)) / 2**n
    return min(1.0, 2 * cola)


def kappa(a, b) -> float:
    """Kappa de Cohen entre dos docentes. NaN si no está definido."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0 or len(a) != len(b):
        return math.nan
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in set(a.tolist()) | set(b.tolist()))
    return math.nan if pe >= 1 else (po - pe) / (1 - pe)


def _agrupar(X, k: int, semilla: int) -> np.ndarray:
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, n_init=1, random_state=semilla).fit_predict(X)


def _silueta(X, etiquetas) -> float:
    from sklearn.metrics import silhouette_score

    return float(silhouette_score(X, etiquetas)) if len(set(etiquetas.tolist())) > 1 else math.nan


def silueta_frente_al_azar(X, k: int, veces: int = 30, semilla: int = 42) -> dict:
    """Silueta de k-medias frente a la de datos sin estructura (columnas barajadas, misma forma)."""
    X = np.asarray(X, float)
    real = _silueta(X, _agrupar(X, k, semilla))
    azar = np.random.default_rng(semilla)
    nulas = []
    for _ in range(veces):
        Y = np.column_stack([azar.permutation(X[:, j]) for j in range(X.shape[1])])
        nulas.append(_silueta(Y, _agrupar(Y, k, semilla)))
    p95 = float(np.nanpercentile(nulas, 95))
    return {"real": real, "p95": p95, "media_azar": float(np.nanmean(nulas)), "supera": bool(real > p95)}


def estabilidad(X, k: int, semillas: int = 20) -> float:
    """ARI medio entre las agrupaciones de k-medias con distintas semillas."""
    from sklearn.metrics import adjusted_rand_score

    X = np.asarray(X, float)
    etiquetas = [_agrupar(X, k, s) for s in range(semillas)]
    pares = [adjusted_rand_score(etiquetas[i], etiquetas[j]) for i in range(semillas) for j in range(i + 1, semillas)]
    return float(np.mean(pares)) if pares else math.nan


def _bueno(valor, minimo: float, estricto: bool = False) -> bool:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return False
    return valor > minimo if estricto else valor >= minimo


def dictaminar(medidas: dict) -> dict:
    """Aprobado solo si cumple todos los criterios; una medida ausente o NaN nunca cumple."""
    g = medidas.get
    criterios = {
        "exhaustividad": _bueno(g("exhaustividad"), EXHAUSTIVIDAD_MINIMA),
        "mcnemar": g("mcnemar_p") is not None and g("mcnemar_p") < ALFA,
        "silueta": g("silueta") is not None and g("silueta_p95") is not None
        and not math.isnan(g("silueta") + g("silueta_p95")) and g("silueta") > g("silueta_p95"),
        "estabilidad": _bueno(g("ari"), ARI_MINIMO),
        "grupos_con_sentido": _bueno(g("grupos_con_sentido"), SENTIDO_MINIMO),
        "kappa": _bueno(g("kappa"), KAPPA_MINIMO),
        "umbral_con_entrenamiento": g("umbral_con_entrenamiento") is True,
    }
    return {"aprobado": all(criterios.values()), "criterios": criterios}


# --- vectores -----------------------------------------------------------------------


def vectores(carpeta: Path, textos: list[str], lote: int = 32) -> np.ndarray:
    """Vectores de `textos` desde `carpeta/onnx/model.onnx`: media con máscara y norma L2."""
    import onnxruntime as ort
    from tokenizers import Tokenizer

    carpeta = Path(carpeta)
    tok = Tokenizer.from_file(str(carpeta / "tokenizer.json"))
    tok.enable_truncation(max_length=LONGITUD_MAXIMA)
    tok.enable_padding()
    sesion = ort.InferenceSession(str(carpeta / "onnx" / "model.onnx"), providers=["CPUExecutionProvider"])
    pedidas = {i.name for i in sesion.get_inputs()}
    salida = []
    for i in range(0, len(textos), lote):
        codificados = tok.encode_batch(textos[i : i + lote])
        ids = np.array([c.ids for c in codificados], dtype=np.int64)
        mascara = np.array([c.attention_mask for c in codificados], dtype=np.int64)
        entradas = {"input_ids": ids, "attention_mask": mascara, "token_type_ids": np.zeros_like(ids)}
        oculto = sesion.run(None, {k: v for k, v in entradas.items() if k in pedidas})[0]
        m = mascara[..., None].astype(oculto.dtype)
        media = (oculto * m).sum(axis=1) / np.maximum(m.sum(axis=1), 1)
        salida.append(media / np.maximum(np.linalg.norm(media, axis=1, keepdims=True), 1e-12))
    return np.vstack(salida) if salida else np.zeros((0, 0))


# --- etiquetas ----------------------------------------------------------------------


def _valor(texto: str) -> int | None:
    t = (texto or "").strip().lower()
    return 1 if t in _SI else 0 if t in _NO else None


def _leer_csv(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cargar_pares(ruta: Path, entrenamiento: list[str], prueba: list[str]) -> dict:
    """Pares únicos (caso, evidencia) con su grupo y etiqueta; solo conteos de lo descartado.

    Un par con docentes en desacuerdo queda fuera de umbral y métricas (se cuenta). El
    kappa usa los dos docentes con más pares y solo los pares que ambos etiquetaron.
    """
    grupo_de = {c: "entrenamiento" for c in entrenamiento} | {c: "prueba" for c in prueba}
    filas = _leer_csv(ruta)
    por_par: dict[tuple[str, str], list[tuple[str, str, int]]] = {}
    fuera_de_grupo = valor_invalido = 0
    for f in filas:
        grupo = grupo_de.get((f.get("codigo_pf") or "").strip())
        valor = _valor(f.get("parecido", ""))
        if grupo is None:
            fuera_de_grupo += 1
        elif valor is None:
            valor_invalido += 1
        else:
            por_par.setdefault((f["caso"], f["evidencia"]), []).append((f["docente"].strip(), grupo, valor))
    pares, desacuerdos, grupo_ambiguo = [], 0, 0
    for (caso, evidencia), votos in por_par.items():
        if len({g for _, g, _ in votos}) > 1:
            grupo_ambiguo += 1
        elif len({v for _, _, v in votos}) > 1:
            desacuerdos += 1
        else:
            pares.append({"caso": caso, "evidencia": evidencia, "grupo": votos[0][1], "etiqueta": votos[0][2]})
    cuenta = Counter(d for votos in por_par.values() for d in {d for d, _, _ in votos})
    docentes = [d for d, _ in sorted(cuenta.items(), key=lambda x: (-x[1], x[0]))[:2]]
    a, b = [], []
    if len(docentes) == 2:
        for votos in por_par.values():
            por_docente = {}
            for d, _, v in votos:
                por_docente.setdefault(d, set()).add(v)
            if all(len(por_docente.get(d, ())) == 1 for d in docentes):
                a.append(next(iter(por_docente[docentes[0]])))
                b.append(next(iter(por_docente[docentes[1]])))
    return {
        "pares": pares,
        "filas": len(filas),
        "filas_fuera_de_grupo": fuera_de_grupo,
        "filas_valor_invalido": valor_invalido,
        "pares_grupo_ambiguo": grupo_ambiguo,
        "pares_en_desacuerdo": desacuerdos,
        "pares_para_kappa": len(a),
        "kappa": kappa(a, b) if a else math.nan,
    }


def grupos_con_sentido(ruta: Path) -> dict:
    """Fracción de grupos que la mayoría estricta de docentes juzga con sentido."""
    votos: dict[str, list[int]] = {}
    for f in _leer_csv(ruta):
        v = _valor(f.get("tiene_sentido", ""))
        if v is not None and (f.get("grupo") or "").strip():
            votos.setdefault(f["grupo"].strip(), []).append(v)
    con = sum(1 for v in votos.values() if sum(v) * 2 > len(v))
    return {"n_grupos": len(votos), "fraccion": con / len(votos) if votos else math.nan}


# --- medición por modelo --------------------------------------------------------------


def _coseno(vec: dict[str, np.ndarray], pares: list[dict]) -> np.ndarray:
    return np.array([float(vec[p["caso"]] @ vec[p["evidencia"]]) for p in pares])


def _tfidf(pares_ent: list[dict], pares_pru: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    v = TfidfVectorizer().fit([t for p in pares_ent for t in (p["caso"], p["evidencia"])])

    def sims(pares):
        A, B = v.transform([p["caso"] for p in pares]), v.transform([p["evidencia"] for p in pares])
        return np.asarray(A.multiply(B).sum(axis=1)).ravel()

    return sims(pares_ent), sims(pares_pru)


def medir_puntaje(sim_ent, y_ent, sim_pru, y_pru) -> dict:
    """Umbral con el 70 % y métricas en el 30 % (con Wilson para la exhaustividad)."""
    y_ent, y_pru = np.asarray(y_ent, bool), np.asarray(y_pru, bool)
    try:
        umbral = elegir_umbral(sim_ent, y_ent)
    except ValueError:
        return {"umbral": None, "precision": None, "exhaustividad": None, "f1": None, "pred": None}
    pred = np.asarray(sim_pru) >= umbral
    m = _metricas(pred, y_pru)
    lo, hi = wilson(int((pred & y_pru).sum()), int(y_pru.sum()))
    return {"umbral": float(umbral), **m, "exhaustividad_ic95": [lo, hi], "pred": pred}


def dejar_fuera_pares(sim, y, facultades, exhaustividad_min: float = EXHAUSTIVIDAD_UMBRAL) -> dict:
    """Por facultad: umbral con las demás, métricas en ella. Informa la peor por F1.

    El codificador no se reentrena en cada vuelta (solo se reelige el umbral).
    """
    sim, y, fac = np.asarray(sim, float), np.asarray(y, bool), np.asarray(facultades)
    por_facultad = {}
    for f in sorted(set(fac.tolist())):
        dentro = fac == f
        try:
            t = elegir_umbral(sim[~dentro], y[~dentro], exhaustividad_min)
        except ValueError:
            por_facultad[f] = {"n": int(dentro.sum()), "umbral": None, "precision": None, "exhaustividad": None, "f1": None}
            continue
        por_facultad[f] = {"n": int(dentro.sum()), "umbral": t, **_metricas(sim[dentro] >= t, y[dentro])}
    validas = {f: m for f, m in por_facultad.items() if _bueno(m["f1"], -1)}
    peor = min(validas, key=lambda f: validas[f]["f1"]) if validas else None
    return {"por_facultad": por_facultad, "peor": peor, "peor_f1": validas[peor]["f1"] if peor else None}


def _evaluar_modelo(carpeta: Path, ent: list[dict], pru: list[dict], vectorizar) -> dict:
    textos = sorted({t for p in ent + pru for t in (p["caso"], p["evidencia"])})
    vec = dict(zip(textos, vectorizar(carpeta, textos)))
    y_ent, y_pru = [p["etiqueta"] for p in ent], [p["etiqueta"] for p in pru]
    return medir_puntaje(_coseno(vec, ent), y_ent, _coseno(vec, pru), y_pru) | {"_vec": vec}


# --- informes -----------------------------------------------------------------------


def _limpio(x):
    """Cifras para JSON: floats de Python, NaN o infinito como null."""
    if isinstance(x, dict):
        return {k: _limpio(v) for k, v in x.items() if not k.startswith("_")}
    if isinstance(x, (list, tuple)):
        return [_limpio(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _sha(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_informe(informe: dict, salida: Path, version: str, humo: bool, completo: bool = True) -> Path:
    """Un informe real por versión: su existencia es el cerrojo. El de humo se sobrescribe."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    sufijo = "-humo" if humo else "" if completo else "-incompleta"
    destino = salida / f"{version}{sufijo}.json"
    texto = json.dumps(_limpio(informe), ensure_ascii=False, indent=2)
    if sufijo:
        destino.write_text(texto, encoding="utf-8")
    else:
        try:
            with open(destino, "x", encoding="utf-8") as f:
                f.write(texto)
        except FileExistsError:
            raise YaEvaluada(version) from None
    return destino


def _reservar(salida: Path, version: str) -> None:
    """Marca la versión como vista antes de leer el 30 %: un fallo a medias no la libera."""
    salida.mkdir(parents=True, exist_ok=True)
    try:
        with open(salida / f"{version}.json", "x", encoding="utf-8") as f:
            json.dump({"version": version, "estado": "en curso", "aprobado": False}, f)
    except FileExistsError:
        raise YaEvaluada(version) from None


def _temas(vec_textos: np.ndarray, k: int) -> dict:
    k = min(k, len(vec_textos) - 1)
    if k < 2:
        return {"k": max(k, 0), "silueta": math.nan, "silueta_p95": math.nan, "ari": math.nan}
    s = silueta_frente_al_azar(vec_textos, k)
    return {"k": k, "silueta": s["real"], "silueta_p95": s["p95"], "silueta_media_azar": s["media_azar"],
            "ari": estabilidad(vec_textos, k)}


def ejecutar(
    modelo: Path,
    silabos: Path,
    *,
    base_modelo: Path | None = None,
    datos: Path = RAIZ / "datos_cd",
    salida: Path = SALIDA_POR_DEFECTO,
    humo: bool = False,
    k: int = 8,
    vectorizar=vectores,
) -> dict:
    """Evalúa `modelo` y escribe el informe. Lanza `YaEvaluada` si la versión ya se evaluó."""
    modelo, salida = Path(modelo), Path(salida)
    ruta_meta = modelo / "metadatos.json"
    meta = json.loads(ruta_meta.read_text(encoding="utf-8"))
    version = meta["version"]
    humo = humo or bool(meta.get("humo"))
    sep = meta["separacion"]
    if not humo and (salida / f"{version}.json").exists():
        raise YaEvaluada(version)

    pares_csv, temas_csv = Path(datos) / "pares.csv", Path(datos) / "temas.csv"
    faltan = [n for n, r in (("pares.csv", pares_csv), ("temas.csv", temas_csv)) if not r.exists()]
    informe = {
        "version": version, "humo": humo, "aprobado": False,
        "huella_separacion": meta.get("huella_separacion"),
        "huella_modelo": _sha(modelo / "onnx" / "model.onnx"),
        "n_silabos_prueba": len(sep["prueba"]),
    }
    if faltan and not humo:
        informe |= {"motivo": "faltan archivos de etiquetas: " + ", ".join(faltan)}
        informe["ruta"] = str(escribir_informe(informe, salida, version, False, completo=False))
        return informe

    lista, _ = leer_carpeta(Path(silabos))
    de_prueba = set(sep["prueba"])
    textos_prueba = sorted({f.texto for s in lista if s.proyecto_formativo.codigo in de_prueba for f in fragmentos(s)})

    if humo:
        # Solo lo que no necesita etiquetas.
        informe |= {"temas": _temas(vectorizar(modelo, textos_prueba), k) if len(textos_prueba) > 2 else {}}
        informe["ruta"] = str(escribir_informe(informe, salida, version, True))
        return informe

    _reservar(salida, version)
    cp = cargar_pares(pares_csv, sep["entrenamiento"], sep["prueba"])
    ent = [p for p in cp["pares"] if p["grupo"] == "entrenamiento"]
    pru = [p for p in cp["pares"] if p["grupo"] == "prueba"]
    y_pru = np.array([p["etiqueta"] for p in pru], bool)

    ajustado = _evaluar_modelo(modelo, ent, pru, vectorizar)
    base = _evaluar_modelo(Path(base_modelo), ent, pru, vectorizar) if base_modelo else None
    elegido, nombre, nota = ajustado, "ajustado", None
    if meta.get("ajuste") is False:
        nombre = "base"
    elif base is None:
        nota = "sin modelo base para comparar: no se puede decidir"
    elif not _bueno(ajustado["f1"], base["f1"] if base["f1"] is not None else math.inf, estricto=True):
        elegido, nombre, nota = base, "base", "el ajustado no supera al base en F1: se usa el base"
    carpeta_elegida = Path(base_modelo) if nombre == "base" and meta.get("ajuste") is not False else modelo

    ok = lambda m: (m["pred"] == y_pru) if m["pred"] is not None else None
    palabras = np.array([p["caso"] not in _casos_libres([p["caso"]], [p["evidencia"]]) for p in pru], bool)
    tf_ent, tf_pru = _tfidf(ent, pru) if ent and pru else (np.zeros(0), np.zeros(0))
    tfidf = medir_puntaje(tf_ent, [p["etiqueta"] for p in ent], tf_pru, y_pru) if ent and pru else None
    p_mc = mcnemar(ok(elegido), palabras == y_pru) if ok(elegido) is not None and len(pru) else None

    catalogo = cargar_catalogo(RAIZ / "kb" / "catalogo.yaml")
    mapa, _ = codigo_a_facultad(lista, catalogo)
    codigo_de = {}  # facultad de cada par: por el grupo de sus códigos
    for f in _leer_csv(pares_csv):
        codigo_de.setdefault((f["caso"], f["evidencia"]), (f.get("codigo_pf") or "").strip())
    todos = ent + pru
    vec = elegido["_vec"]
    fuera = dejar_fuera_pares(
        _coseno(vec, todos), [p["etiqueta"] for p in todos],
        [mapa.get(codigo_de.get((p["caso"], p["evidencia"])), "?") for p in todos],
    ) if todos else {}

    temas = _temas(vectorizar(carpeta_elegida, textos_prueba), k) if len(textos_prueba) > 2 else {}
    sentido = grupos_con_sentido(temas_csv)
    medidas = {
        "exhaustividad": elegido["exhaustividad"], "mcnemar_p": p_mc,
        "silueta": temas.get("silueta"), "silueta_p95": temas.get("silueta_p95"), "ari": temas.get("ari"),
        "grupos_con_sentido": sentido["fraccion"], "kappa": cp["kappa"],
        "umbral_con_entrenamiento": elegido["umbral"] is not None,
    }
    sin_decision = base is None and meta.get("ajuste") is not False
    veredicto = {"aprobado": False, "criterios": {}} if sin_decision else dictaminar(medidas)
    informe |= {
        "aprobado": veredicto["aprobado"], "criterios": veredicto["criterios"], "medidas": medidas,
        "modelo_elegido": nombre, "nota_modelo": nota, "umbral": elegido["umbral"],
        "n_pares_entrenamiento": len(ent), "n_pares_prueba": len(pru),
        "conteos": {k_: v for k_, v in cp.items() if k_ not in ("pares", "kappa")},
        "modelos": {
            "ajustado": {k_: v for k_, v in ajustado.items() if k_ not in ("pred", "_vec")},
            "base": {k_: v for k_, v in base.items() if k_ not in ("pred", "_vec")} if base else None,
            "tfidf": {k_: v for k_, v in tfidf.items() if k_ != "pred"} if tfidf else None,
            "filtro_palabras": _metricas(palabras, y_pru) if len(pru) else None,
        },
        "temas": temas, "n_grupos_temas": sentido["n_grupos"], "dejar_fuera": fuera,
    }
    informe["ruta"] = str(_sobrescribir_reservado(informe, salida, version))
    if informe["aprobado"]:
        meta_elegida = json.loads((carpeta_elegida / "metadatos.json").read_text(encoding="utf-8"))
        meta_elegida |= {"aprobado": True, "umbral": elegido["umbral"]}
        (carpeta_elegida / "metadatos.json").write_text(json.dumps(meta_elegida, ensure_ascii=False, indent=2), encoding="utf-8")
    return informe


def _sobrescribir_reservado(informe: dict, salida: Path, version: str) -> Path:
    destino = Path(salida) / f"{version}.json"
    destino.write_text(json.dumps(_limpio(informe), ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ciencia_datos.evaluar")
    p.add_argument("--modelo", type=Path, required=True)
    p.add_argument("--base-modelo", type=Path, help="carpeta ONNX del modelo base (exportado con --sin-ajuste)")
    p.add_argument("--silabos", type=Path, required=True)
    p.add_argument("--datos", type=Path, default=RAIZ / "datos_cd")
    p.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    p.add_argument("--k", type=int, default=8, help="número de temas")
    p.add_argument("--humo", action="store_true")
    a = p.parse_args(argv)
    try:
        r = ejecutar(a.modelo, a.silabos, base_modelo=a.base_modelo, datos=a.datos, salida=a.salida, humo=a.humo, k=a.k)
    except YaEvaluada as e:
        print(f"ya evaluada: {e}")
        return 1
    print(f"version={r['version']} humo={r['humo']} aprobado={r['aprobado']} informe={r['ruta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
