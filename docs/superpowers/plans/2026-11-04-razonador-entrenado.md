# Razonador entrenado antes de Qwen: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entrenar y evaluar con separación 70/30 un modelo propio de vectores y agrupación que decida temas y casos antes de que Qwen redacte.

**Architecture:** El entrenamiento corre fuera de línea en `backend/ciencia_datos/`, fuera del paquete de producción, y produce un modelo versionado por carpeta. El proceso `worker` lo carga con ONNX, sin PyTorch, y el planificador lo usa para ordenar focos y descartar casos. Qwen no genera vectores y solo redacta a partir del plan. Todo queda apagado hasta que la evaluación apruebe.

**Tech Stack:** Python 3.13; sentence-transformers, scikit-learn y SciPy para entrenar; onnxruntime y tokenizers para producción; pytest.

**Spec:** No hay documento aparte. Las decisiones salen de la sesión del 2026-11-04 y de los artículos de BERT, SimCSE, E5, Steinley, Jain y Rousseeuw. Las aprobó el usuario como flujo: «el modelo entrenado decide temas, grupos y casos, y Qwen solo redacta».

## Decisiones y umbrales

**Flujo**

```text
Fuera de línea: PDF → SilaboUTI → fragmentos → 70/30 por sílabo → entrenar → evaluar → modelo aprobado
En cada trabajo: contexto → razonador (temas y casos) → plan guardado → Qwen redacta → controles → docente
```

**Datos mínimos.** Hoy hay 2 PDF, ambos de Ingenierías: solo alcanzan para la prueba de humo.

| Uso | Sílabos | Por qué |
|---|---|---|
| Humo (`--humo`) | 2 | Comprueba que el código corre; su resultado no vale como calidad |
| **Mínimo para entrenar** | **4 por facultad, en 5 facultades (20)** | Con 4 sale 3/1 por facultad; con los 2 del protocolo de alta sería 1/1 |
| Recomendado | 4 por facultad en las 8 (32) | Cubre todo el catálogo |
| 70/30 exacto por facultad | 10 por facultad en las 8 (80) | Solo si la universidad los entrega |

**Etiquetas docentes.** 500 pares (caso, evidencia) con al menos 40 % «parecido», para que el 30 % de prueba tenga unos 60 positivos (exhaustividad ±10 %). Dos docentes etiquetan por separado al menos 100 pares comunes para calcular kappa.

**Criterios de aprobación (propuestos; el usuario los confirma antes de la corrida real).**

| Medida | Criterio |
|---|---|
| Umbral de similitud | Se elige solo con el 70 %: máxima precisión con exhaustividad ≥ 0,90 |
| Filtro de casos en el 30 % | Exhaustividad ≥ 0,85 y McNemar p < 0,05 frente al filtro actual de palabras |
| Temas en el 30 % | Silueta sobre el percentil 95 del azar, ARI entre semillas ≥ 0,80 y ≥ 80 % de grupos con sentido según docentes |
| Acuerdo docente | Kappa de Cohen ≥ 0,60 |
| Ajuste fino | Se conserva solo si supera al modelo base en F1 de prueba; si no, se usa el base |
| Generalización | Se repite dejando fuera cada facultad y se informa la peor |

## Global Constraints

- Modelo base inicial: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, ya en la caché local. Descargar otro (E5) requiere autorización del usuario.
- Qwen no participa en vectores, entrenamiento ni evaluación.
- `modelos/`, `datos_cd/` y `.venv-ciencia/` se agregan a `.gitignore`. Los PDF siguen en `Silabos/`, sin versionar.
- Solo se lee `SilaboUTI`, y nunca se imprimen textos de los sílabos en la consola de entrenamiento ni en los informes.
- La separación se hace por `proyecto_formativo.codigo`, nunca por fragmento. Semilla fija 42.
- El 30 % de prueba se evalúa una sola vez por versión.
- Sin `RAZONADOR_RUTA`, la generación es idéntica a la actual. Un modelo con `humo: true` o sin aprobar no se carga con `ENTORNO=produccion`.
- Dependencias de entrenamiento en `[project.optional-dependencies].ciencia`; en producción solo `numpy`, `scikit-learn`, `onnxruntime` y `tokenizers`.
- Commits en español y terminados en `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No hacer push sin autorización.

## Review Focus

1. Clase con 0–3 fragmentos: no se agrupa; se usan los focos actuales, sin error. Prueba en Task 5.
2. `RAZONADOR_RUTA` apunta a un modelo ausente, dañado o no aprobado: el worker no arranca y lo dice; nunca sigue en silencio sin él. Prueba en Task 6.
3. Trabajo reanudado tras una caída con otro modelo instalado: conserva el plan guardado. Prueba en Task 6.
4. El razonador descarta todos los casos: cuestionario sin caso y momento con los de respaldo, como hoy. Prueba en Task 6.
5. Dos versiones del mismo sílabo: quedan del mismo lado de la separación. Prueba en Task 2.

---

### Task 1: Corpus sin datos personales

**Files:**
- Create: `backend/ciencia_datos/__init__.py`, `backend/ciencia_datos/corpus.py`
- Modify: `backend/pyproject.toml`, `.gitignore`
- Test: `backend/tests/test_cd_corpus.py`

**Interfaces:**
- Consumes: `SilaboUTI`, `leer_silabo(datos: bytes)` de `app/silabo/lector/ensamblar.py`
- Produces: `Fragmento(codigo_pf: str, facultad: str, carrera: str, momento: int | None, tipo: str, texto: str)`; `fragmentos(silabo: SilaboUTI) -> list[Fragmento]`; `leer_carpeta(carpeta: Path) -> tuple[list[SilaboUTI], list[str]]` (la segunda lista son nombres de archivo rechazados)

- [ ] **Step 1: Write the failing tests**

```python
def test_fragmentos_toma_solo_contenido_academico(silabo_datos):
    f = fragmentos(silabo_datos)
    assert {x.tipo for x in f} == {"contenido", "actividad", "resultado", "evidencia"}
    assert all(x.codigo_pf == silabo_datos.proyecto_formativo.codigo for x in f)

def test_fragmentos_sin_repetidos_ni_vacios(silabo_datos):
    textos = [x.texto for x in fragmentos(silabo_datos)]
    assert len(textos) == len(set(textos)) and all(t.strip() for t in textos)

@pytest.mark.parametrize("dato", ["ana@uti.edu.ec", "0987654321", "0000-0002-1825-0097"])
def test_descarta_fragmentos_con_datos_personales(silabo_datos, dato):
    assert dato not in str(fragmentos(_con_texto(silabo_datos, f"Contactar a {dato}")))
```

- [ ] **Step 2:** Run `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_cd_corpus.py -v`. Expected: FAIL con `ModuleNotFoundError: ciencia_datos`.
- [ ] **Step 3:** Implement `corpus.py`. Sale de `sesiones[].contenidos`, de los textos `docente`, `practico` y `autonomo`, de `resultados_aprendizaje[].texto` y de `momentos[].evidencia`. Descarta por expresión regular correos, ORCID y secuencias de 7 o más dígitos. Agrega las dependencias `ciencia` y las de producción, y las rutas a `.gitignore`.
- [ ] **Step 4:** Run the same command. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(ciencia-datos): corpus sin datos personales`.

### Task 2: Separación 70/30

**Files:**
- Create: `backend/ciencia_datos/separar.py`
- Test: `backend/tests/test_cd_separar.py`

**Interfaces:**
- Consumes: `cargar_catalogo`, `normalizar` de `app/agentes/facultades.py`
- Produces: `Separacion(entrenamiento: list[str], prueba: list[str], avisos: list[str])`; `separar(codigo_a_facultad: dict[str, str], proporcion: float = 0.7, semilla: int = 42) -> Separacion`; `dejar_fuera(codigo_a_facultad: dict[str, str]) -> dict[str, Separacion]`; `cumple_minimo(codigo_a_facultad: dict[str, str]) -> bool` con `MIN_POR_FACULTAD = 4` y `MIN_FACULTADES = 5`

- [ ] **Step 1: Write the failing tests**

```python
def test_ningun_sílabo_queda_en_ambos_grupos_y_es_estable():
    d = {f"PF{i}": ("FING" if i < 10 else "FACEAN") for i in range(20)}
    a, b = separar(d), separar(d)
    assert a == b and not set(a.entrenamiento) & set(a.prueba)
    assert len(a.prueba) == 6

def test_facultad_con_un_sílabo_va_a_entrenamiento_y_avisa():
    s = separar({"A": "FING"})
    assert s.entrenamiento == ["A"] and s.prueba == [] and s.avisos

def test_versiones_del_mismo_codigo_son_una_sola_clave():
    assert sorted(separar({"PF1": "FING", "PF2": "FING"}).entrenamiento + separar({"PF1": "FING", "PF2": "FING"}).prueba) == ["PF1", "PF2"]

def test_dejar_fuera_y_minimo():
    d = {f"F{f}-{i}": f"F{f}" for f in range(5) for i in range(4)}
    assert cumple_minimo(d) and not cumple_minimo({"A": "FING"})
    assert all(all(c.startswith(fac) for c in s.prueba) for fac, s in dejar_fuera(d).items())
```

- [ ] **Step 2:** Run `pytest tests/test_cd_separar.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement estratificado por facultad: orden por SHA-256 de `semilla:codigo`, y prueba = `round(n × 0,3)` por facultad con al menos 1 si `n ≥ 2`. `leer_carpeta` conserva la versión más reciente de cada código.
- [ ] **Step 4:** Run the same command. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(ciencia-datos): separación 70/30 por sílabo`.

### Task 3: Entrenamiento

**Files:**
- Create: `backend/ciencia_datos/entrenar.py`
- Modify: `backend/pyproject.toml` (marcador `modelo: requiere el modelo base en caché`)
- Test: `backend/tests/test_cd_entrenar.py`

**Interfaces:**
- Consumes: Tasks 1 y 2
- Produces: `entrenar(textos: list[str], base: str, salida: Path, *, epocas: int = 1, humo: bool = False) -> Path`; carpeta con `onnx/model.onnx`, `tokenizer.json` y `metadatos.json` (`version`, `base`, `humo`, `aprobado: false`, `n_silabos`, `n_fragmentos`, `huella_separacion`); CLI `python -m ciencia_datos.entrenar --silabos ../Silabos --salida ../modelos/<version> [--humo] [--sin-ajuste]`

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_rechaza_pocos_silabos_sin_humo(tmp_path, dos_silabos):
    with pytest.raises(SystemExit, match="mínimo"):
        main(["--silabos", str(dos_silabos), "--salida", str(tmp_path)])

@pytest.mark.modelo
def test_entrena_con_humo_y_deja_metadatos(tmp_path):
    ruta = entrenar(TEXTOS_SINTETICOS, BASE, tmp_path / "v0", humo=True)
    m = json.loads((ruta / "metadatos.json").read_text(encoding="utf-8"))
    assert m["humo"] is True and m["aprobado"] is False
    assert (ruta / "onnx" / "model.onnx").exists()

def test_solo_entrena_con_el_grupo_de_entrenamiento(tmp_path, monkeypatch, cuatro_silabos):
    vistos = _capturar_textos(monkeypatch)
    main(["--silabos", str(cuatro_silabos), "--salida", str(tmp_path), "--humo"])
    assert not vistos & textos_de_prueba(cuatro_silabos)
```

- [ ] **Step 2:** Run `pytest tests/test_cd_entrenar.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement SimCSE sin etiquetas: pares `(texto, texto)` con `MultipleNegativesRankingLoss`, dropout 0,1, temperatura 0,05 y lote 32. Usa la GPU de 4 GB si hay, y la CPU si no. `--sin-ajuste` exporta el modelo base para la comparación. Exporta con `SentenceTransformer(ruta, backend="onnx")`. Sin `--humo` exige `cumple_minimo`.
- [ ] **Step 4:** Run with `.venv-ciencia` and `HF_HUB_OFFLINE=1`. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(ciencia-datos): entrenamiento del codificador`.

### Task 4: Evaluación

**Files:**
- Create: `backend/ciencia_datos/evaluar.py`
- Test: `backend/tests/test_cd_evaluar.py`

**Interfaces:**
- Consumes: Tasks 1–3; `_casos_libres` de `app/agentes/planificador.py` como línea base
- Produces: `wilson(k, n) -> tuple[float, float]`; `elegir_umbral(sim, etiquetas, exhaustividad_min=0.90) -> float`; `mcnemar(a_ok, b_ok) -> float`; `kappa(a, b) -> float`; `silueta_frente_al_azar(X, k, veces=30, semilla=42) -> dict`; `estabilidad(X, k, semillas=20) -> float`; `dictaminar(medidas: dict) -> dict`; CLI que escribe `pruebas/ciencia_datos/<version>.json` (cifras y huellas, sin textos) y fija `aprobado` en `metadatos.json` solo si todo pasa

- [ ] **Step 1: Write the failing tests**

```python
def test_wilson_coincide_con_lo_calculado():
    assert wilson(14, 16) == pytest.approx((0.640, 0.965), abs=0.001)

def test_umbral_no_usa_la_prueba(monkeypatch):
    u = elegir_umbral(np.array([.9, .8, .3, .2]), np.array([1, 1, 0, 0]))
    assert .3 < u <= .8

def test_mcnemar_y_kappa():
    assert mcnemar([True] * 20 + [False] * 5, [False] * 20 + [False] * 5) < .05
    assert kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1

def test_datos_sin_estructura_no_superan_al_azar():
    X = np.random.default_rng(1).normal(size=(60, 32))
    r = silueta_frente_al_azar(X / np.linalg.norm(X, axis=1, keepdims=True), 4)
    assert r["real"] <= r["p95"] + 0.02

def test_dictamen_exige_todos_los_criterios():
    assert dictaminar(MEDIDAS_BUENAS)["aprobado"] is True
    assert dictaminar({**MEDIDAS_BUENAS, "kappa": .4})["aprobado"] is False

def test_segunda_evaluacion_de_la_misma_version_se_rechaza(tmp_path):
    assert evaluar_dos_veces(tmp_path) == "ya evaluada"
```

- [ ] **Step 2:** Run `pytest tests/test_cd_evaluar.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement con los umbrales de la tabla. Compara TF-IDF, modelo base y modelo ajustado, y calcula `dejar_fuera`. Las etiquetas salen de `datos_cd/pares.csv` (`caso,evidencia,codigo_pf,docente,parecido`). Con `--humo` escribe el informe, pero nunca aprueba.
- [ ] **Step 4:** Run the same command. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(ciencia-datos): evaluación con 30 % reservado`.

### Task 5: Razonador en producción

**Files:**
- Create: `backend/app/razonador.py`
- Test: `backend/tests/test_razonador.py`

**Interfaces:**
- Consumes: carpeta del Task 3
- Produces: `class Razonador` con `cargar(ruta: Path, *, exigir_aprobado: bool) -> Razonador`, `version: str`, `vectores(textos: list[str]) -> np.ndarray`, `temas(textos: list[str]) -> list[list[int]]`, `casos_libres(casos: list[str], entregables: list[str]) -> list[str]`; excepción `RazonadorInvalido`

- [ ] **Step 1: Write the failing tests** (con un `Razonador` falso de vectores fijos, salvo los marcados `modelo`)

```python
@pytest.mark.parametrize("n", [0, 1, 2, 3])
def test_pocos_textos_no_se_agrupan(falso, n):
    assert falso.temas([f"t{i}" for i in range(n)]) == [[i] for i in range(n)]

def test_temas_son_deterministas_y_no_pierden_textos(falso):
    t = [f"t{i}" for i in range(8)]
    assert falso.temas(t) == falso.temas(t)
    assert sorted(i for g in falso.temas(t) for i in g) == list(range(8))

def test_descarta_el_caso_parecido_aunque_no_comparta_palabras(falso_sinonimos):
    assert falso_sinonimos.casos_libres(["intrusión informática", "ventas de pan"], ["ataque a la red"]) == ["ventas de pan"]

@pytest.mark.parametrize("meta", [{"humo": True, "aprobado": False}, {"humo": False, "aprobado": False}])
def test_no_carga_modelo_sin_aprobar(carpeta_con, meta):
    with pytest.raises(RazonadorInvalido):
        Razonador.cargar(carpeta_con(meta), exigir_aprobado=True)

@pytest.mark.modelo
def test_onnx_da_los_mismos_vectores_que_el_entrenamiento(modelo_humo):
    assert np.allclose(Razonador.cargar(modelo_humo, exigir_aprobado=False).vectores(["hola"]), vectores_st(modelo_humo, ["hola"]), atol=1e-3)
```

- [ ] **Step 2:** Run `pytest tests/test_razonador.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement con `onnxruntime` y `tokenizers`, agrupación media y vectores normalizados. `temas` usa K-means con `random_state=42`, `n_init=20`, y elige k entre 2 y `min(8, n-1)` por silueta. `casos_libres` usa `metadatos["umbral"]`.
- [ ] **Step 4:** Run the same command. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(razonador): carga e inferencia sin PyTorch`.

### Task 6: El plan pasa por el razonador

**Files:**
- Modify: `backend/app/agentes/planificador.py`, `coordinador.py:69-71`, `orquestador.py:77-102`, `mensajes.py`, `evidencia.py`, `backend/app/chat/ajustes.py:202`, `backend/app/chat/ejecutor.py`, `backend/app/config.py`, `backend/app/operacion.py`, `backend/worker.py`
- Test: `backend/tests/test_planificador.py`, `test_coordinador.py`, `test_config.py`

**Interfaces:**
- Consumes: `Razonador` del Task 5
- Produces: `planificar(contexto, n, perfil, tam_lote=4, escenarios=(), razonador=None)`; `estilo_razonado(perfil, carrera, contexto, razonador) -> EstiloFacultad`; `procesar_uno(..., razonador=None)`; `Coordinador(perfil, workers, cliente, razonador=None)`; `PlanRazonado(Mensaje)` con `version: str`, `planes: list[list[PlanItem]]`; `PaqueteEvidencia.razonador_version: str | None = None`; `Ajustes.razonador_ruta: Path | None = None`

- [ ] **Step 1: Write the failing tests**

```python
def test_sin_razonador_el_plan_no_cambia(contexto):
    assert planificar(contexto, 12, "fundamentacion", razonador=None) == planificar(contexto, 12, "fundamentacion")

def test_cubre_todos_los_temas_antes_de_repetir(contexto_con_8_focos, falso_tres_temas):
    plan = [i for l in planificar(contexto_con_8_focos, 3, "fundamentacion", razonador=falso_tres_temas) for i in l]
    assert len({tema_de(i.foco) for i in plan}) == 3

def test_nunca_es_menos_estricto_que_el_filtro_de_palabras(contexto, falso_acepta_todo):
    e = estilo_razonado(PERFIL, "SOFTWARE", contexto_con_entregable("tienda en línea"), falso_acepta_todo)
    assert "tiempos de carga de una tienda en línea" not in e.escenarios

def test_todos_descartados_usa_el_comportamiento_actual(contexto, falso_rechaza_todo):
    e = estilo_razonado(PERFIL, "SOFTWARE", contexto, falso_rechaza_todo)
    assert e.escenarios == []
    assert escenario_para(tarea_con(e)) in ESCENARIOS_DE_RESPALDO

def test_reanudar_conserva_el_plan_guardado_con_otro_modelo(conn, trabajo_a_medias, razonador_v2):
    assert plan_usado(conn, trabajo_a_medias, razonador_v2) == plan_guardado(conn, trabajo_a_medias)

def test_worker_no_arranca_con_modelo_invalido(tmp_path):
    with pytest.raises(RazonadorInvalido):
        cargar_razonador(Ajustes(razonador_ruta=tmp_path / "no-existe", **BASE))

def test_evidencia_registra_la_version(trabajo_terminado):
    assert trabajo_terminado.evidencia["razonador_version"] == "v-prueba"
```

- [ ] **Step 2:** Run `pytest tests/test_planificador.py tests/test_coordinador.py tests/test_config.py -v`. Expected: FAIL en las nuevas.
- [ ] **Step 3:** Implement: `planificar` reordena `_focos` tomando un foco por tema en rotación. `estilo_razonado` aplica primero `_casos_libres` y después `razonador.casos_libres`, sobre los escenarios del estilo; así el planificador, `escenario_para` y el chat reciben el mismo resultado. La primera ejecución guarda `PlanRazonado` y las reanudaciones lo leen. `worker.py` carga el modelo una sola vez, con `exigir_aprobado=True` si `ENTORNO=produccion`. `validar_configuracion` comprueba la ruta.
- [ ] **Step 4:** Run `cd backend && ../.venv/Scripts/python.exe -m pytest -m "not servidor and not modelo" -q`. Expected: todo pasa, incluidas las 911 pruebas previas.
- [ ] **Step 5:** Commit: `feat(planificador): temas y casos del razonador, apagado por omisión`.

### Task 7: Despliegue, documentación y prueba de humo

**Files:**
- Create: `docs/ciencia-datos.md`
- Modify: `infra/compose.yaml`, `backend/Dockerfile` si corresponde, `docs/entrega-ti.md`, `docs/operacion.md`, `progress.md`, `backend/tests/test_infra_config.py`

**Interfaces:**
- Consumes: Tasks 1–6
- Produces: volumen de solo lectura `modelos` montado en el servicio `worker`; `RAZONADOR_RUTA` documentada y vacía por omisión

- [ ] **Step 1: Write the failing test**

```python
def test_compose_no_activa_el_razonador_por_omision():
    worker = compose()["services"]["worker"]
    assert not str(worker.get("environment", {}).get("RAZONADOR_RUTA", "")).strip("${}: ").replace("RAZONADOR_RUTA", "")
```

- [ ] **Step 2:** Run `pytest tests/test_infra_config.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement el volumen, la imagen sin PyTorch y `docs/ciencia-datos.md` con los datos mínimos, cómo etiquetar, los criterios y cómo leer el informe.
- [ ] **Step 4:** Corre la prueba de humo con los 2 sílabos locales:

```bash
cd backend && HF_HUB_OFFLINE=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.entrenar --silabos ../Silabos --salida ../modelos/humo --humo
```

Expected: `metadatos.json` con `humo: true` y `aprobado: false`. Luego `pytest -m modelo -v` pasa. El informe debe decir que no vale como evaluación de calidad.
- [ ] **Step 5:** Commit: `docs(ciencia-datos): entrega, operación y prueba de humo`.

## Corrida real (depende de personas, no de código)

- [ ] El área académica entrega al menos 20 sílabos según la tabla, y se dejan en `Silabos/`.
- [ ] El usuario confirma los criterios de aprobación.
- [ ] Docentes etiquetan los 500 pares.
- [ ] Se entrena, se evalúa una sola vez y se presenta el informe al usuario.
- [ ] Solo si aprueba y el usuario lo decide: TI instala el modelo y define `RAZONADOR_RUTA`.
- [ ] Se compara con y sin razonador en las mismas clases con Qwen real y revisión docente. La regresión logística multinivel se añade cuando existan esas 240 preguntas revisadas.

## Límites conocidos

- Con 20–32 sílabos habrá pocos miles de fragmentos, quizá insuficientes para que el ajuste fino supere al modelo base. Por eso compite contra él y puede perder.
- El razonador no corrige claves incorrectas: decide temas y casos, y Qwen sigue redactando las respuestas. Ese problema exige otro plan (ítems paramétricos, M1 y M2 del spec).
- Cambia lo que Qwen recibe, no lo que Qwen sabe. La mejora en las preguntas finales solo se conoce con la última comparación.
