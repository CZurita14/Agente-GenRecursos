# Simulación de sílabos y modelo `preliminar-1`: plan de implementación

> **Para quien ejecute:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendada) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** generar unos 198 sílabos simulados de las 29 carreras de grado y entrenar con ellos una primera versión del codificador, marcada como preliminar e imposible de cargar en producción.

**Arquitectura:** el código construye la estructura del sílabo (fechas, horas, sesiones e identificadores) y Qwen, fuera de línea, redacta solo los textos, por etapas. Los sílabos se guardan como `SilaboUTI` en JSON, con código `SIM-`. `entrenar` reconoce ese prefijo, separa 70/30 solo los simulados, reserva los reales como control y marca el modelo `preliminar: true`.

**Tecnología:** Python, Pydantic, `ClienteVLLM` y `pedir_json` para Qwen; numpy; sentence-transformers y ONNX para entrenar (`.venv-ciencia`).

**Especificación:** no hay documento aparte. Las decisiones están en la sección siguiente y parten del plan `docs/superpowers/plans/2026-11-04-razonador-entrenado.md`.

## Decisiones

| Decisión | Valor | Motivo |
|---|---|---|
| Carreras | Las de `nivel: grado` en `kb/catalogo.yaml`: 29 | Coinciden con la lista del usuario; las maestrías quedan fuera |
| Medio Ambiente (`FCMA`) | No se simula | No tiene carreras; entra sola cuando el catálogo las tenga |
| Cuota por carrera | `max(6, ceil(24 / carreras de la facultad))` | Al menos 6 por carrera y 24 por facultad |
| Total | FING 36, FADA 24, FACEAN 42, FCED 24, FCSBH 24, FCSH 24, FJCP 24 = **198** | La cuota limita el desequilibrio a 1,75:1 |
| Qué escribe Qwen | Solo textos de simulación, fuera de línea | Qwen sigue sin participar en vectores, entrenamiento ni evaluación |
| Textos reales en los prompts | Ninguno | Los reales solo aportan conteos, y así siguen sirviendo de control |
| Los 2 reales | No entrenan: quedan como `control_real` | Serían 1 % del corpus y son lo único real para comparar |
| Formato | JSON de `SilaboUTI`, sin PDF | No cambia el contrato; el lector de PDF no se ejercita |
| Bibliografía | Vacía | `fragmentos` no la usa, y así no se inventan referencias |

**Perfil estructural medido en los 2 reales** (solo conteos; dos sílabos son una muestra mínima):

| Campo | Rango |
|---|---|
| Momentos | 4 |
| Sesiones por momento | 1 a 4 (6 a 11 en total) |
| Resultados de aprendizaje | 3 a 4 |
| Metodologías | 3 a 4 |
| Contenidos por sesión | 1 a 3 |
| Filas de rúbrica por momento | 3 a 6 |
| Filas de rúbrica del producto final | 4 a 5 |
| Horas totales | 96 o 144 |

Cada sílabo real ocupa de 33 000 a 50 000 caracteres de JSON, más de lo que cabe en una respuesta con el contexto de 8192 tokens. Por eso se redacta por etapas: una llamada general y una por momento, 5 por sílabo. Con la propuesta de proyectos por carrera son unas 1020 llamadas.

**Fuera de este plan** (plan siguiente): regresión logística, MMR, herramienta de etiquetado, entrenamiento con pares docentes, comando de reentrenamiento, perfiles por carrera, separación de reales cuando haya suficientes. El equilibrio de lotes por facultad tampoco entra, porque la cuota ya lo acota.

## Restricciones globales

- Rama `p10/simulacion`, creada desde `p9/razonador`. Sin push. Nunca `git add -A`: `docs/propuestas/` no se versiona.
- Commits en español, terminados en `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Nunca imprimir textos de sílabos, reales ni simulados, en consola ni en informes; solo conteos. La única salida con texto es la muestra en `datos_cd/`, sin versionar.
- Nunca imprimir valores de `.env`.
- Modelo base: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, ya en caché. No descargar otro.
- Nada de `backend/app/` importa `ciencia_datos`, `torch` ni `sentence_transformers`.
- Sin `RAZONADOR_RUTA`, la generación queda idéntica.
- Un corpus sin códigos `SIM-` se comporta exactamente como hoy, con la misma separación y la misma huella.
- Pruebas normales, desde `backend/`: `../.venv/Scripts/python.exe -m pytest <ruta> -v`.
- Suite completa: `../.venv/Scripts/python.exe -m pytest -m "not servidor and not modelo" -q`.
- Pruebas con modelo: `HF_HUB_OFFLINE=1 ../.venv-ciencia/Scripts/python.exe -m pytest <ruta> -m modelo -v`.

## Foco de revisión

1. **Qwen repite textos entre carreras:** el lote debe mostrar esa repetición y el filtro debe sacarla del entrenamiento. Prueba en Tareas 5 y 7.
2. **Qwen inventa personas o contactos:** un sílabo con «Dr. Juan Pérez» o un correo se descarta y no se guarda. Prueba en Tarea 3.
3. **La corrida se corta a la mitad:** al repetirla no duplica ni deja JSON a medio escribir. Prueba en Tarea 4.
4. **Un simulado llega a producción o a una aprobación:** el cargador y `evaluar` lo rechazan, aunque alguien edite `aprobado: true`. Un PDF no puede usar el prefijo `SIM-`. Pruebas en Tarea 6.
5. **Cambia el catálogo:** al agregar una carrera, las demás conservan sus códigos y solo se genera lo nuevo. Prueba en Tarea 1.

---

### Tarea 1: Marca de origen y plan de simulación

**Archivos:**
- Crear: `backend/ciencia_datos/origen.py`, `backend/ciencia_datos/sim_plan.py`
- Probar: `backend/tests/test_cd_sim_plan.py`

**Interfaces:**
- Produce: `PREFIJO_SIMULADO = "SIM-"`; `es_simulado(codigo: str) -> bool`.
- Produce: `Cupo(sigla, facultad, carrera, indice)`, dataclass inmutable, con la propiedad `codigo -> str`, de forma `SIM-<SIGLA>-<SLUG>-<indice de 3 dígitos>`. `SLUG` sale de `normalizar(carrera)`, con guiones en lugar de espacios.
- Produce: `cuota(n_carreras: int) -> int`; `cupos(ruta_catalogo: Path) -> list[Cupo]`, en rotación entre facultades y, dentro de cada una, entre carreras.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_cuotas_del_catalogo_real():
    lista = cupos(CATALOGO)
    por_facultad = Counter(c.sigla for c in lista)
    assert por_facultad == {"FING": 36, "FADA": 24, "FACEAN": 42, "FCED": 24,
                            "FCSBH": 24, "FCSH": 24, "FJCP": 24}
    assert len(lista) == 198
    assert len({c.carrera for c in lista}) == 29

def test_excluye_posgrado_y_facultad_sin_carreras():
    lista = cupos(CATALOGO)
    assert not any(c.carrera.startswith("Maestría") for c in lista)
    assert "FCMA" not in {c.sigla for c in lista}

def test_los_primeros_20_cubren_las_7_facultades_sin_repetir_carrera():
    primeros = cupos(CATALOGO)[:20]
    assert len({c.sigla for c in primeros}) == 7
    assert len({c.carrera for c in primeros}) == 20

def test_los_codigos_son_unicos_y_marcados():
    codigos = [c.codigo for c in cupos(CATALOGO)]
    assert len(set(codigos)) == len(codigos)
    assert all(es_simulado(c) for c in codigos)
    assert not es_simulado("INF-101")

def test_agregar_una_carrera_conserva_los_codigos_de_las_demas(tmp_path):
    antes = {c.codigo for c in cupos(CATALOGO)}
    ruta = _catalogo_con_carrera_nueva(tmp_path, sigla="FCMA", carrera="Gestión Ambiental")
    despues = {c.codigo for c in cupos(ruta)}
    assert antes < despues
```

- [ ] **Paso 2:** ejecutar `../.venv/Scripts/python.exe -m pytest tests/test_cd_sim_plan.py -v`. Esperado: FALLA, el módulo no existe.
- [ ] **Paso 3:** implementar ambos módulos, con `normalizar` de `app.agentes.facultades`. La nueva carrera de `FCMA` recibe `max(6, 24) = 24` cupos, sin afectar a las demás.
- [ ] **Paso 4:** ejecutar las pruebas. Esperado: PASAN.
- [ ] **Paso 5:** commit `feat(ciencia-datos): cupos de simulación por facultad y carrera`.

### Tarea 2: Esqueleto determinista del sílabo

**Archivos:**
- Crear: `backend/ciencia_datos/sim_esqueleto.py`
- Probar: `backend/tests/test_cd_sim_esqueleto.py`

**Interfaces:**
- Consume: `Cupo` (Tarea 1).
- Produce: dataclasses inmutables `SesionBase(id, numero, fecha, semana_periodo, horas_docente, horas_practico, horas_autonomo)`, `MomentoBase(numero, fecha_inicio, fecha_fin, sesiones)` y `Esqueleto(codigo, horas_total, periodo, momentos, n_resultados, n_metodologias, n_filas_rubrica, n_filas_rubrica_pf, contenidos_por_sesion)`.
- Produce: `crear_esqueleto(cupo: Cupo, semilla: int = 42) -> Esqueleto`.

Valores fijos: periodo con código `SIM-2026`, 16 semanas desde 2026-03-02. Horas de `HorasPF`: contacto y práctico `total // 3`; autónomo, el resto. Créditos `total / 48`. El azar sale de `random.Random(f"{semilla}:{cupo.codigo}")`, nunca del azar global. Los rangos son los del perfil estructural.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_respeta_el_perfil_en_todos_los_cupos():
    for cupo in cupos(CATALOGO):
        e = crear_esqueleto(cupo)
        por_momento = [len(m.sesiones) for m in e.momentos]
        assert len(e.momentos) == 4
        assert all(1 <= n <= 4 for n in por_momento)
        assert 6 <= sum(por_momento) <= 11
        assert 3 <= e.n_resultados <= 4
        assert 3 <= e.n_metodologias <= 4
        assert e.horas_total in (96, 144)

def test_es_determinista_y_varia_entre_cupos():
    lista = cupos(CATALOGO)
    assert crear_esqueleto(lista[0]) == crear_esqueleto(lista[0])
    assert len({tuple(len(m.sesiones) for m in crear_esqueleto(c).momentos) for c in lista}) > 5

def test_fechas_dentro_del_periodo_y_en_orden():
    e = crear_esqueleto(cupos(CATALOGO)[0])
    fechas = [s.fecha for m in e.momentos for s in m.sesiones]
    assert fechas == sorted(fechas)
    assert e.periodo.inicio <= fechas[0] and fechas[-1] <= e.periodo.fin

def test_ids_de_sesion_unicos():
    e = crear_esqueleto(cupos(CATALOGO)[0])
    ids = [s.id for m in e.momentos for s in m.sesiones]
    assert len(set(ids)) == len(ids)
```

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** implementar `crear_esqueleto`.
- [ ] **Paso 4:** ejecutar las pruebas. Esperado: PASAN.
- [ ] **Paso 5:** commit `feat(ciencia-datos): esqueleto determinista del sílabo simulado`.

### Tarea 3: Redacción por etapas y ensamblado

**Archivos:**
- Crear: `backend/ciencia_datos/sim_redaccion.py`
- Modificar: `backend/ciencia_datos/corpus.py` (expone `tiene_datos_personales(texto) -> bool`, con el patrón ampliado)
- Probar: `backend/tests/test_cd_sim_redaccion.py`, `backend/tests/test_cd_corpus.py`

**Interfaces:**
- Consume: `Cupo`, `Esqueleto`; `pedir_json(cliente, mensajes, modelo, esquema, rol=..., temperatura=0.7)`, `ClienteSimulado`.
- Produce: modelos Pydantic `ProyectoPropuesto(nombre, nivel)`, `ProyectosPropuestos(proyectos)`, `GeneralRedactado`, `MomentoRedactado`.
- Produce: `proponer_proyectos(cliente, sigla, facultad, carrera, n) -> list[ProyectoPropuesto]`, con `rol="sim_proyectos"`.
- Produce: `redactar_silabo(cliente, cupo, proyecto, esqueleto) -> SilaboUTI`, con `rol="sim_general"` y `rol="sim_momento"`.
- Produce: `class SimulacionInvalida(Exception)`, sin texto de sílabo en el mensaje.

**Contenido de las etapas:**
- `GeneralRedactado`: `competencia_perfil`, `competencia_pf`, `metacompetencia`, resultados con su evidencia, `problema`, `pis`, `metodologias`, títulos de los 4 momentos y `rubrica_producto_final`.
- `MomentoRedactado`: `evidencia`, `recursos`, `politica_ia`, `rubrica` y, por sesión, contenidos, tres textos de actividad y entregables. El prompt recibe los resultados, el problema y el título del momento para mantener la coherencia.
- Las claves de `niveles` de la rúbrica son las de `backend/tests/fixtures/silabo_datos.json`.

**Reglas de los prompts:** están en español; el sílabo es ficticio; no hay personas, instituciones reales, correos, teléfonos ni citas; no se copia texto real. Solo reciben facultad, carrera, nombre y nivel del proyecto, y conteos.

**Ensamblado:** las listas con elementos de más se recortan al número del esqueleto. Con elementos de menos, o si `fragmentos` deja menos de 20, lanza `SimulacionInvalida`. Campos fijos: `uoc` Básica (niveles 1 a 3), Profesional (4 a 6) o Integración curricular (7 y 8); modalidad `Presencial`; versión `SIM`; bibliografía vacía; `facultad` y `carrera` con los nombres exactos del catálogo.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_ensambla_un_silabo_valido_con_cinco_llamadas():
    cliente = _cliente_valido()
    s = redactar_silabo(cliente, CUPO, PROYECTO, crear_esqueleto(CUPO))
    assert isinstance(s, SilaboUTI)
    assert s.proyecto_formativo.codigo == CUPO.codigo
    assert len(s.momentos) == 4
    assert len(cliente.llamadas) == 5
    assert s.bibliografia.basica == []

def test_la_facultad_simulada_esta_en_el_catalogo():
    s = redactar_silabo(_cliente_valido(), CUPO, PROYECTO, crear_esqueleto(CUPO))
    assert normalizar(s.facultad) in cargar_catalogo(CATALOGO)

def test_con_sesiones_de_menos_se_rechaza():
    with pytest.raises(SimulacionInvalida):
        redactar_silabo(_cliente_con_una_sesion(), CUPO, PROYECTO, crear_esqueleto(CUPO))

@pytest.mark.parametrize("texto", ["Dr. Juan Pérez explica el tema", "Escribir a ana@uti.edu.ec",
                                   "Mgs. María López", "Llamar al 0991234567"])
def test_datos_personales_inventados_descartan_el_silabo(texto):
    with pytest.raises(SimulacionInvalida):
        redactar_silabo(_cliente_valido(actividad=texto), CUPO, PROYECTO, crear_esqueleto(CUPO))

def test_el_error_no_contiene_texto_del_silabo():
    with pytest.raises(SimulacionInvalida) as e:
        redactar_silabo(_cliente_valido(actividad="Dr. Juan Pérez"), CUPO, PROYECTO, crear_esqueleto(CUPO))
    assert "Pérez" not in str(e.value)

def test_usa_los_roles_de_simulacion_sin_razonamiento():
    cliente = _cliente_valido()
    redactar_silabo(cliente, CUPO, PROYECTO, crear_esqueleto(CUPO))
    assert {l["rol"] for l in cliente.llamadas} == {"sim_general", "sim_momento"}
    assert all(l["pensar"] is False for l in cliente.llamadas)

def test_proyectos_repetidos_se_quitan():
    cliente = ClienteSimulado({"sim_proyectos": [_propuesta(["Redes", "redes ", "Bases de datos"])]})
    nombres = [p.nombre for p in proponer_proyectos(cliente, "FING", "Facultad", "Software", 2)]
    assert nombres == ["Redes", "Bases de datos"]
```

En `test_cd_corpus.py`, agregar que `fragmentos` descarta `Dra. Ana Ruiz` y conserva `Ing. de requisitos` y `Ingeniería Civil`: el patrón exige un título con punto seguido de una palabra con mayúscula inicial.

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** ampliar `_PERSONAL` con títulos seguidos de nombre propio (`Dr.`, `Dra.`, `Ing.`, `Mgs.`, `Msc.`, `PhD`, `Lic.`) y exponer `tiene_datos_personales`.
- [ ] **Paso 4:** implementar `sim_redaccion.py`. Comprobar todos los textos del sílabo, no solo los que usa `fragmentos`.
- [ ] **Paso 5:** ejecutar las pruebas y `tests/test_cd_corpus.py`. Esperado: PASAN.
- [ ] **Paso 6:** commit `feat(ciencia-datos): redacción por etapas de sílabos simulados`.

### Tarea 4: Comando `simular`, reanudable

**Archivos:**
- Crear: `backend/ciencia_datos/simular.py`
- Probar: `backend/tests/test_cd_simular.py`

**Interfaces:**
- Consume: Tareas 1 a 3; `Ajustes` de `app.config`; `ClienteVLLM(base_url, modelo, timeout_s, max_concurrencia, registrar, api_key)`.
- Produce: `generar(cliente, cupos, carpeta_silabos: Path, carpeta_trabajo: Path, hilos: int = 2, semilla: int = 42) -> Resumen`.
- Produce: `Resumen(generados, existentes, descartados, segundos)`.
- Produce: `_crear_cliente(ajustes: Ajustes) -> ClienteVLLM`, sustituible en las pruebas; el registro de llamadas es una función vacía, porque no hay trabajo ni base de datos.
- Produce: CLI `python -m ciencia_datos.simular --salida datos_cd [--limite N] [--hilos 2]`.

**Disposición:**
- `datos_cd/silabos_simulados/<SIGLA>/<SLUG>/<codigo>.json`: los sílabos.
- `datos_cd/simulacion/proyectos.json`: proyectos por carrera; se reutilizan al repetir.
- `datos_cd/simulacion/manifiesto.json`: modelo, semilla, temperatura, versión de los prompts y conteos.

Los dos archivos de trabajo van fuera de la carpeta de sílabos: `leer_con_origen` recorre subcarpetas y los contaría como rechazados.

**Comportamiento:**
- Escritura atómica: archivo temporal y `os.replace`.
- Un cupo cuyo JSON ya existe y valida se salta; un JSON dañado se regenera.
- `JsonInvalido` o `SimulacionInvalida` cuentan como descartados y la corrida sigue.
- `ServidorNoDisponible` detiene la corrida con código 2. Lo ya guardado se conserva.
- `--limite N` toma los primeros N cupos de `cupos()`, lo que da el piloto repartido.
- La consola solo imprime conteos.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_genera_y_valida_contra_el_contrato(tmp_path):
    r = generar(_cliente_valido(), CUPOS[:3], tmp_path / "s", tmp_path / "t")
    assert r.generados == 3
    archivos = list((tmp_path / "s").rglob("*.json"))
    assert len(archivos) == 3
    assert all(SilaboUTI.model_validate_json(a.read_bytes()) for a in archivos)

def test_leer_con_origen_no_ve_rechazados(tmp_path):
    generar(_cliente_valido(), CUPOS[:3], tmp_path / "s", tmp_path / "t")
    silabos, rechazados = leer_carpeta(tmp_path / "s")
    assert len(silabos) == 3 and rechazados == []

def test_reanudar_no_repite_ni_llama_de_nuevo(tmp_path):
    generar(_cliente_valido(), CUPOS[:3], tmp_path / "s", tmp_path / "t")
    otro = _cliente_valido()
    r = generar(otro, CUPOS[:3], tmp_path / "s", tmp_path / "t")
    assert (r.generados, r.existentes) == (0, 3)
    assert otro.llamadas == []

def test_un_json_danado_se_regenera(tmp_path):
    generar(_cliente_valido(), CUPOS[:1], tmp_path / "s", tmp_path / "t")
    next((tmp_path / "s").rglob("*.json")).write_text("{a medias", encoding="utf-8")
    assert generar(_cliente_valido(), CUPOS[:1], tmp_path / "s", tmp_path / "t").generados == 1

def test_un_descartado_no_detiene_la_corrida(tmp_path):
    r = generar(_cliente_que_falla_el_primero(), CUPOS[:3], tmp_path / "s", tmp_path / "t")
    assert (r.generados, r.descartados) == (2, 1)

def test_servidor_caido_conserva_lo_generado_y_sale_con_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(simular, "_crear_cliente", lambda a: _cliente_que_cae_tras(1))
    assert simular.main(["--salida", str(tmp_path), "--limite", "3", "--hilos", "1"]) == 2
    assert len(list((tmp_path / "silabos_simulados").rglob("*.json"))) == 1
    assert "Traceback" not in capsys.readouterr().err

def test_la_consola_no_imprime_texto(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(simular, "_crear_cliente", lambda a: _cliente_valido(actividad="TEXTO-SECRETO"))
    simular.main(["--salida", str(tmp_path), "--limite", "1"])
    assert "TEXTO-SECRETO" not in capsys.readouterr().out
```

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** implementar. `proyectos.json` se escribe bajo un candado de hilo, y se piden los proyectos de una carrera antes de redactar sus cupos.
- [ ] **Paso 4:** ejecutar las pruebas. Esperado: PASAN.
- [ ] **Paso 5:** commit `feat(ciencia-datos): comando simular reanudable`.

### Tarea 5: Filtro de casi repetidos y revisión del lote

**Archivos:**
- Crear: `backend/ciencia_datos/casi_repetidos.py`, `backend/ciencia_datos/revisar_lote.py`
- Probar: `backend/tests/test_cd_casi_repetidos.py`, `backend/tests/test_cd_revisar_lote.py`

**Interfaces:**
- Produce: `UMBRAL_CASI_REPETIDO = 0.95`.
- Produce: `filtrar(textos: list[str], vectores: np.ndarray, *, contra: np.ndarray | None = None, umbral: float = UMBRAL_CASI_REPETIDO) -> tuple[list[str], int]`: normaliza a L2, conserva el primero de cada grupo y quita lo que iguale o supere el umbral contra lo conservado o contra `contra`. Devuelve los textos y cuántos quitó.
- Produce: `revisar(silabos: list[SilaboUTI], vectorizar) -> dict`.
- Produce: `dictaminar_lote(informe: dict) -> list[str]`, los criterios incumplidos.
- Produce: CLI `python -m ciencia_datos.revisar_lote --silabos <dir> --salida datos_cd [--muestra 20]`, que escribe `simulacion/revision.json` y `simulacion/muestra-revision.csv`.

**El informe contiene:** sílabos por facultad y carrera; fragmentos por sílabo, mínimo y máximo; `fraccion_casi_repetidos`, global y entre carreras distintas; `fraccion_inicio_repetido`, la parte de fragmentos que comparte sus primeras 5 palabras con el 5 % o más del lote; datos personales detectados.

**Criterios propuestos para pasar el piloto, a confirmar con su resultado:**
- Datos personales detectados: 0.
- `fraccion_casi_repetidos` entre carreras distintas: menor que 0,10.
- `fraccion_inicio_repetido`: menor que 0,30.
- Fragmentos por sílabo: entre 20 y 80 en todos.
- Cobertura: todas las facultades del lote con sílabos.

**La muestra** es un CSV en `utf-8-sig` con las columnas `codigo,carrera,momento,tipo,texto,parece_real`, y `parece_real` vacía para el revisor. Toma fragmentos de todas las facultades. Es el único archivo con texto, y queda en `datos_cd/`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_filtrar_quita_casi_iguales_y_conserva_el_primero():
    v = np.array([[1, 0], [0.999, 0.01], [0, 1]], dtype=float)
    assert filtrar(["a", "b", "c"], v) == (["a", "c"], 1)

def test_filtrar_quita_lo_parecido_a_contra():
    v = np.array([[1, 0], [0, 1]], dtype=float)
    assert filtrar(["a", "b"], v, contra=np.array([[1, 0.001]])) == (["b"], 1)

def test_filtrar_acepta_lista_vacia():
    assert filtrar([], np.empty((0, 2))) == ([], 0)

def test_revisar_detecta_textos_repetidos_entre_carreras():
    informe = revisar(_lote_con_actividad_identica_en_dos_carreras(), _vectorizar_falso)
    assert informe["fraccion_casi_repetidos_entre_carreras"] > 0
    assert any("casi_repetidos" in c for c in dictaminar_lote(informe))

def test_lote_variado_pasa():
    assert dictaminar_lote(revisar(_lote_variado(), _vectorizar_falso)) == []

def test_el_informe_no_contiene_texto():
    informe = revisar(_lote_variado(actividad="TEXTO-SECRETO"), _vectorizar_falso)
    assert "TEXTO-SECRETO" not in json.dumps(informe, ensure_ascii=False)
```

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** implementar. `torch` y `sentence_transformers` se importan solo en el `vectorizar` real, dentro de la función.
- [ ] **Paso 4:** ejecutar las pruebas. Esperado: PASAN.
- [ ] **Paso 5:** commit `feat(ciencia-datos): filtro de casi repetidos y revisión del lote`.

### Tarea 6: Entrenamiento con origen y estado preliminar

**Archivos:**
- Modificar: `backend/ciencia_datos/separar.py`, `corpus.py`, `entrenar.py`, `evaluar.py`
- Modificar: `backend/app/razonador.py:74` (dentro de `if exigir_aprobado:`)
- Probar: `backend/tests/test_cd_separar.py`, `test_cd_corpus.py`, `test_cd_entrenar.py`, `test_cd_evaluar.py`, y las pruebas del razonador

**Interfaces:**
- Consume: `es_simulado`; `filtrar`.
- Produce: `Separacion.control: list[str]`, por omisión vacía.
- Produce: `separar_preliminar(codigo_a_facultad) -> Separacion`: los simulados van 70/30 por facultad; los reales, a `control`, sin entrenar.
- Produce: `leer_con_origen` y `leer_carpeta` aceptan `Path | list[Path]`; `--silabos` de `entrenar` acepta varias carpetas (`nargs="+"`). `por_carpeta` conserva su salida usando la carpeta raíz de cada ruta.
- Produce en `metadatos.json`: `preliminar: true`, `origen: {simulados, reales}`, `separacion.control_real`, `n_casi_repetidos_excluidos`.

**Reglas:**
- Un corpus con algún `SIM-` siempre produce `preliminar: true`. `cumple_minimo` se comprueba solo sobre los simulados.
- El filtro `filtrar` corre solo si hay simulados. `contra` son los textos de prueba y de control: nada de eso se parece a lo que entrena.
- `control_real` entra en la huella solo si no está vacío, para que un corpus sin simulados conserve su huella.
- Un PDF cuyo código empiece por `SIM-` se rechaza en `leer_con_origen`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_los_reales_van_a_control_y_nunca_entrenan():
    mapa = {f"SIM-A-{i}": "A" for i in range(10)} | {"REAL-1": "A", "REAL-2": "B"}
    s = separar_preliminar(mapa)
    assert s.control == ["REAL-1", "REAL-2"]
    assert not {"REAL-1", "REAL-2"} & (set(s.entrenamiento) | set(s.prueba))
    assert all(es_simulado(c) for c in s.prueba)

def test_sin_simulados_la_separacion_y_la_huella_no_cambian(tmp_path, monkeypatch, cuatro_silabos):
    meta = _entrenar_cli(tmp_path, monkeypatch, cuatro_silabos)
    assert "preliminar" not in meta or meta["preliminar"] is False
    assert "control_real" not in meta["separacion"]
    assert meta["huella_separacion"] == huella({"entrenamiento": meta["separacion"]["entrenamiento"],
                                                "prueba": meta["separacion"]["prueba"]})

def test_con_simulados_el_modelo_queda_preliminar_y_sin_textos_reales(tmp_path, monkeypatch, corpus_mixto):
    textos, meta = _entrenar_cli_mixto(tmp_path, monkeypatch, corpus_mixto)
    assert meta["preliminar"] is True and meta["aprobado"] is False
    assert meta["origen"] == {"simulados": 40, "reales": 2}
    assert not set(textos) & TEXTOS_REALES

def test_excluye_casi_repetidos_de_prueba_y_control(tmp_path, monkeypatch, corpus_con_casi_repetido):
    textos, meta = _entrenar_cli_mixto(tmp_path, monkeypatch, corpus_con_casi_repetido)
    assert TEXTO_CASI_IGUAL_AL_CONTROL not in textos
    assert meta["n_casi_repetidos_excluidos"] >= 1

def test_varias_carpetas_se_leen_juntas(tmp_path, dos_carpetas):
    silabos, _ = leer_carpeta(dos_carpetas)
    assert len(silabos) == 4

def test_un_pdf_no_puede_usar_el_prefijo_simulado(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "leer_silabo", lambda d: _silabo(codigo="SIM-FING-X-001"))
    (tmp_path / "a.pdf").write_bytes(b"%PDF")
    assert leer_carpeta(tmp_path) == ([], ["a.pdf"])

def test_evaluar_rechaza_un_modelo_preliminar_sin_tomar_candado(tmp_path):
    modelo = _modelo_falso(tmp_path, preliminar=True, humo=False)
    with pytest.raises(EntradaInvalida):
        ejecutar(modelo, tmp_path / "silabos", datos=tmp_path, salida=tmp_path / "s")
    assert not (modelo / "evaluacion.candado").exists()

def test_produccion_rechaza_un_preliminar_aunque_diga_aprobado(tmp_path):
    ruta = _carpeta_aprobada(tmp_path, preliminar=True)
    with pytest.raises(RazonadorInvalido, match="preliminar"):
        Razonador.cargar(ruta, exigir_aprobado=True)

def test_desarrollo_si_carga_un_preliminar(tmp_path):
    assert Razonador.cargar(_carpeta_valida(tmp_path, preliminar=True), exigir_aprobado=False)
```

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** implementar. Los vectores del filtro salen de `_vectorizar_base(base, textos)` en `entrenar.py`, que importa `sentence_transformers` dentro y se sustituye en las pruebas.
- [ ] **Paso 4:** ejecutar la suite completa. Esperado: todo pasa, y las pruebas existentes de `test_cd_entrenar.py` no cambian.
- [ ] **Paso 5:** commit `feat(ciencia-datos): modelo preliminar con simulados y control real`.

### Tarea 7: Informe preliminar

**Archivos:**
- Crear: `backend/ciencia_datos/preliminar.py`
- Modificar: `.gitignore` (agrega `pruebas/ciencia_datos/*-preliminar.json`)
- Probar: `backend/tests/test_cd_preliminar.py`

**Interfaces:**
- Consume: `metadatos.json` con `separacion` (Tarea 6); `vectores` de `evaluar`; `_silueta(X, etiquetas)` de `estadistica.py`.
- Produce: `ejecutar_preliminar(modelo: Path, base_modelo: Path, silabos: list[Path], salida: Path, vectorizar=vectores) -> dict`.
- Produce: CLI `python -m ciencia_datos.preliminar --modelo --base-modelo --silabos ... --salida`, que escribe `<version>-preliminar.json`.

**Medidas, para el ajustado y para el base, sobre los mismos textos:**
- `precision_5_carrera` y `precision_5_facultad`: entre los 5 vecinos más cercanos de otros sílabos, la parte de la misma carrera o facultad. Globales y por facultad.
- `silueta_facultad` y la misma silueta con etiquetas barajadas (semilla 42).
- `control_real`: para cada fragmento real, vecinos en la prueba simulada y parte de la misma facultad. Si esa facultad no tiene simulados, es `null`.

**Campos fijos del informe:**
- `apto_produccion: false`.
- `advertencia`: «Los textos los redactó Qwen a partir de la carrera: estas medidas indican coherencia técnica, no calidad. La aprobación exige sílabos reales y etiquetas docentes.»
- `n_control_real`, para que se vea que son solo 2.

No toma candado, no ajusta nada y no fija umbral. Nunca escribe `aprobado`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_informe_compara_ambos_modelos_y_nunca_aprueba(tmp_path):
    r = ejecutar_preliminar(MODELO, BASE, [SILABOS], tmp_path, vectorizar=_vectores_falsos)
    assert set(r["candidatos"]) == {"ajustado", "base"}
    assert r["apto_produccion"] is False
    assert "no calidad" in r["advertencia"]
    assert "umbral" not in json.loads((MODELO / "metadatos.json").read_text(encoding="utf-8")) or \
        json.loads((MODELO / "metadatos.json").read_text(encoding="utf-8"))["umbral"] is None

def test_precision_5_con_vecinos_conocidos():
    assert precision_k(_vectores_dos_grupos(), _etiquetas_dos_grupos(), _silabos_distintos(), k=1) == 1.0

def test_los_vecinos_del_mismo_silabo_no_cuentan():
    assert precision_k(_vectores_iguales_mismo_silabo(), ["A", "A"], ["s1", "s1"], k=1) is None

def test_facultad_real_sin_simulados_da_null(tmp_path):
    r = ejecutar_preliminar(MODELO_CONTROL_SIN_FACULTAD, BASE, [SILABOS], tmp_path, vectorizar=_vectores_falsos)
    assert r["candidatos"]["ajustado"]["control_real"]["precision_5_facultad"] is None

def test_rechaza_un_modelo_que_no_es_preliminar(tmp_path):
    with pytest.raises(EntradaInvalida):
        ejecutar_preliminar(MODELO_NO_PRELIMINAR, BASE, [SILABOS], tmp_path, vectorizar=_vectores_falsos)

def test_el_informe_no_lleva_texto(tmp_path):
    r = ejecutar_preliminar(MODELO, BASE, [SILABOS], tmp_path, vectorizar=_vectores_falsos)
    assert TEXTO_DE_PRUEBA not in json.dumps(r, ensure_ascii=False)
```

- [ ] **Paso 2:** ejecutar las pruebas. Esperado: FALLAN.
- [ ] **Paso 3:** implementar `precision_k(vectores, etiquetas, silabos, k=5) -> float | None` y `ejecutar_preliminar`.
- [ ] **Paso 4:** ejecutar las pruebas y la suite completa. Esperado: PASAN.
- [ ] **Paso 5:** actualizar `docs/ciencia-datos.md` con una sección «Simulación y modelo preliminar»: comandos de las Tareas 8 y 9, qué demuestra y qué no. Actualizar `progress.md`.
- [ ] **Paso 6:** commit `feat(ciencia-datos): informe del modelo preliminar`.

### Tarea 8: Piloto de 20 sílabos con Qwen

Tarea de operación. Necesita el servidor vLLM y una persona que revise. Los sílabos quedan en `datos_cd/`, sin versionar.

- [ ] **Paso 1:** comprobar que el servidor responde y sirve el modelo configurado, sin imprimir valores de `.env`. Si no responde, parar y avisar.
- [ ] **Paso 2:** ejecutar, desde `backend/`:

```bash
PYTHONUTF8=1 ../.venv/Scripts/python.exe -m ciencia_datos.simular --salida ../datos_cd --limite 20
```

Esperado: 20 generados o descartados en total, con las 7 facultades. Anotar los segundos por sílabo.

- [ ] **Paso 3:** ejecutar:

```bash
HF_HUB_OFFLINE=1 PYTHONUTF8=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.revisar_lote --silabos ../datos_cd/silabos_simulados --salida ../datos_cd
```

Esperado: `simulacion/revision.json` y `simulacion/muestra-revision.csv`.

- [ ] **Paso 4 (persona):** el usuario revisa `muestra-revision.csv` y marca `parece_real`. **Se detiene aquí hasta tener esa revisión.** Con su resultado: si pasa, se sigue a la Tarea 9. Si falla, se ajustan los prompts, se sube su versión y se borran los 20 sílabos del piloto, con confirmación del usuario. Máximo 3 rondas; después se vuelve a decidir.
- [ ] **Paso 5:** informar al usuario de los descartes, las medidas, los segundos por sílabo y la proyección para los 198.

### Tarea 9: Corrida completa y entrenamiento de `preliminar-1`

Tarea de operación. Requiere la Tarea 8 aprobada y que el usuario haya aceptado el tiempo estimado.

- [ ] **Paso 1:** ejecutar `simular` sin `--limite`. Se puede repetir si se corta. Esperado: 198 sílabos o una lista de descartados; repetir hasta que los descartados no bajen.
- [ ] **Paso 2:** ejecutar `revisar_lote` sobre el lote completo. Esperado: `dictaminar_lote` sin criterios incumplidos. Si falla, parar e informar.
- [ ] **Paso 3:** entrenar ambos candidatos, desde `backend/`:

```bash
HF_HUB_OFFLINE=1 PYTHONUTF8=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.entrenar --silabos ../Silabos ../datos_cd/silabos_simulados --salida ../modelos/preliminar-1
```

```bash
HF_HUB_OFFLINE=1 PYTHONUTF8=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.entrenar --silabos ../Silabos ../datos_cd/silabos_simulados --sin-ajuste --salida ../modelos/preliminar-1-base
```

Esperado: `preliminar: true` en ambos, `reales=2` y ningún texto en consola. Ambos usan la misma `huella_separacion`.

- [ ] **Paso 4:** ejecutar:

```bash
HF_HUB_OFFLINE=1 PYTHONUTF8=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.preliminar --modelo ../modelos/preliminar-1 --base-modelo ../modelos/preliminar-1-base --silabos ../Silabos ../datos_cd/silabos_simulados --salida ../pruebas/ciencia_datos
```

- [ ] **Paso 5:** comprobar la carga real: con `exigir_aprobado=False` el modelo carga y da vectores; con `exigir_aprobado=True` lanza `RazonadorInvalido`.
- [ ] **Paso 6:** ejecutar la suite completa y `-m modelo`. Esperado: sin fallos.
- [ ] **Paso 7:** informar al usuario con las cifras, si el ajustado superó al base y qué no demuestra. Actualizar `progress.md` y hacer commit `docs(ciencia-datos): resultado de preliminar-1`, sin datos ni modelos.
