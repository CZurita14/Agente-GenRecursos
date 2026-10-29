# P2 · Lector del sílabo y menú — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el PDF institucional del sílabo en un `SilaboUTI` sin IA ni datos personales, y construir con él el menú de clases por semana y día.

**Architecture:** El lector vive en `backend/app/silabo/lector/`. Primero **segmenta** el PDF por la posición vertical de los títulos de sección y descarta las secciones I y VII *antes* de extraer nada. Después, unos **analizadores puros** convierten tablas y texto, ya como listas de Python, en piezas del contrato; se prueban con datos sintéticos versionables. Al final, un **ensamblador** produce el `SilaboUTI`. El menú (`backend/app/silabo/menu.py`) es una función pura sobre el `SilaboUTI`.

**Tech Stack:** Python 3.13, `pdfplumber` 0.11 (ya instalado en `.venv`; se declara en `pyproject.toml`), Pydantic 2, pytest.

**Spec:** [especificacion-generador-recursos-uti-v1.2.md](../../especificacion-generador-recursos-uti-v1.2.md) §7, §8.1, §2.2 y [mapeo-silabo.md](../../mapeo-silabo.md) §2–§6. Contrato: `backend/app/silabo/modelo.py` (T3 del P1, **no se modifica**). Hoja de ruta: [§7.3](2026-10-26-analisis-y-hoja-de-ruta-fase1.md).

## Global Constraints

- Entrada: bytes que empiezan con `%PDF`, de 50 MB (`50 * 1024 * 1024`) como máximo y con capa de texto; si no, `SilaboIlegible` (P4 la traduce a `422`).
- Datos mínimos: facultad, carrera, nombre y código del PF, y al menos un momento con una sesión fechada; si faltan, `SilaboIlegible`.
- **Secciones I (perfil del docente) y VII (firmas): nunca se extraen.** Se recortan del área de la página antes de `extract_text`/`extract_tables`. Ninguna prueba, log ni mensaje de error imprime texto de esas secciones.
- Los PDF reales están en `Silabos/` (en `.gitignore`) y **nunca se versionan**. Las pruebas con PDF reales se omiten si el archivo no existe y sus `assert` no muestran valores leídos de I o VII.
- `semana_periodo`: semanas desde el lunes de la semana de `periodo.inicio` (2026-10-05 = semana 1).
- Id de sesión: `M<momento>-S<n>`; la numeración del sílabo se reinicia en cada momento.
- Entregables: se detectan «TAREA n», «PAE n» y «EVALUACIÓN COGNITIVA n» (sin distinguir mayúsculas ni tildes) en las actividades de la sesión.
- Niveles de la rúbrica, claves exactas: `receptivo`, `resolutivo`, `reflexivo`, `critico`, `cocreativo`.
- Texto: se conserva tal cual (mayúsculas sostenidas, LaTeX `$H_0$`, frases que empiezan a la mitad). Solo se normaliza para comparar.

## Review Focus

1. **Tabla de la sección I en la misma página que el título de la sección II** (ocurre en la página 2 de los dos sílabos): si se segmenta por página, se filtran los datos del docente. Se cubre con `test_segmenta_por_posicion_no_por_pagina` (Tarea 1).
2. **El índice de la página 1 repite los 7 títulos:** si se toma la primera aparición, todas las secciones empiezan en la portada. Se cubre con `test_ignora_el_indice` (Tarea 1).
3. **Fila de sesión partida entre páginas:** la continuación no tiene «Sesión N – fecha» y debe unirse a la fila anterior, no crear una sesión vacía. Se cubre con `test_fila_partida_se_une` (Tarea 3).
4. **Encabezados de columna que varían entre sílabos** («Trabajo autónomo» frente a «Actividades de trabajo autónomo»; «Hora s» partido): las columnas se identifican por palabra clave normalizada, no por posición fija. Se cubre con `test_columnas_por_palabra_clave` (Tarea 3).
5. **PDF escaneado, protegido o que no es PDF** (un `.docx` renombrado): debe dar un error claro, no una traza. Se cubre con `test_rechazos_de_entrada` (Tarea 1).

## Puertas del usuario

- Autorizar que las pruebas lean en local los PDF de `Silabos/` (nunca se versionan). Sin esa autorización, las Tareas 5 y 6 solo corren con datos sintéticos.
- Queda **fuera** de este plan la ruta de respaldo con IA (L7 de la hoja de ruta): no hay sílabos de otra plantilla con qué probarla (bloqueo B7). Se planifica cuando llegue uno.

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `backend/app/silabo/lector/__init__.py` | Exporta `leer_silabo` y `SilaboIlegible` |
| `backend/app/silabo/lector/errores.py` | `SilaboIlegible(ValueError)` con `motivo: str` |
| `backend/app/silabo/lector/entrada.py` | Validación de bytes y segmentación por secciones |
| `backend/app/silabo/lector/texto.py` | Utilidades puras: `normalizar_clave`, `fecha_dmy`, `horas`, `entregables_en` |
| `backend/app/silabo/lector/presentacion.py` | Portada, sección II y sección III → campos de cabecera |
| `backend/app/silabo/lector/momentos.py` | Sección IV → `list[Momento]` (sesiones + rúbricas) |
| `backend/app/silabo/lector/cierre.py` | Sección V (rúbrica del producto final) y sección VI (bibliografía) |
| `backend/app/silabo/lector/ensamblar.py` | `leer_silabo(datos: bytes) -> SilaboUTI` |
| `backend/app/silabo/menu.py` | `construir_menu` y `clases_cambiadas` |
| `backend/tests/lector/` | Pruebas sintéticas por analizador + `test_reales.py` con los PDF locales |

Los analizadores reciben **tablas** (`list[list[str | None]]`, como las da `pdfplumber`) y **texto**, nunca el PDF. Por eso sus pruebas son sintéticas y versionables.

---

### Task 1: Entrada y segmentación (L1)

**Files:**
- Create: `backend/app/silabo/lector/{__init__,errores,entrada}.py`, `backend/tests/lector/__init__.py`, `backend/tests/lector/test_entrada.py`, `backend/tests/lector/conftest.py`
- Modify: `backend/pyproject.toml` (añadir `"pdfplumber>=0.11"` a `dependencies`)

**Interfaces:**
- Produces:
  - `class SilaboIlegible(ValueError)`: `__init__(self, motivo: str)`; `self.motivo` es un texto en español para el docente, **sin** contenido del PDF.
  - `def abrir(datos: bytes) -> pdfplumber.PDF`: valida `%PDF`, el tamaño y que la suma de caracteres de las páginas sea mayor que 200 (capa de texto). Cualquier excepción de `pdfplumber` (cifrado, PDF corrupto) se convierte en `SilaboIlegible`.
  - `SECCIONES_UTILES = ("portada", "II", "III", "IV", "V", "VI")`
  - `def segmentar(pdf) -> dict[str, list]`: a cada sección útil le asigna su lista de **páginas recortadas** (`page.crop(bbox)`) en orden. Las secciones I y VII no aparecen en el resultado.
- Helper de pruebas en `backend/tests/lector/conftest.py`: `datos_personales(datos: bytes) -> set[str]` (ver Step 1).
- Fixture en `backend/tests/lector/conftest.py`: `pdf_real(nombre)`, que devuelve los bytes de `Silabos/Software/AnalisisDatos-Ingenieria/silabo_Datos_Software-signed.pdf` (`"datos"`) o de `Silabos/Software/TIC-Ingenieria/TIC-Ingenieria.pdf` (`"tic"`), o hace `pytest.skip` si no existen.

Algoritmo de `segmentar`, que es lo que el código no deja decidir:
1. Recorre todas las páginas con `extract_words()` y localiza los títulos con `^(I|II|III|IV|V|VI|VII)\.\s+[A-ZÁÉÍÓÚÑ ]+$`, uniendo las palabras de una misma línea por su `top`.
2. Para cada número toma la **última** aparición (la primera está en el índice de la página 1).
3. Una sección va desde su título (`top` en su página) hasta el título siguiente. Las páginas intermedias van completas, y en la página del título siguiente se recorta hasta su `top`.
4. La portada es todo lo anterior al título I.

- [ ] **Step 1: Escribir las pruebas que fallan** en `test_entrada.py`:
  - `test_rechazos_de_entrada` (parametrizada): `b"hola"`; `b"%PDF" + b"0" * (50 * 1024 * 1024)`; `b"%PDF-1.4 roto"` (PDF corrupto); y `PDF_SIN_TEXTO`, un PDF válido de una página en blanco, escrito como constante de bytes en la prueba (unos 300 bytes: catálogo, páginas, una página sin contenido, xref y trailer). Cada caso lanza `SilaboIlegible` y `str(e)` no contiene `"Traceback"`.
  - `test_ignora_el_indice(pdf_real)`: con `"datos"`, `segmentar(abrir(...))["II"][0].page_number == 2`.
  - `test_segmenta_por_posicion_no_por_pagina(pdf_real)`: para `"datos"` y `"tic"`, el texto de todas las secciones útiles juntas **no** contiene `"Nombres y apellidos"` ni `"ORCID"`, ni ninguno de los **datos personales**: los valores de las filas de la sección I cuyo rótulo empieza por nombre, correo, teléfono u ORCID, partidos en tokens de 4 letras o más. Para obtenerlos, la prueba usa el helper `datos_personales(pdf) -> set[str]` de `tests/lector/conftest.py`, que recorta la sección I por su cuenta y nunca imprime nada. El mensaje de error solo da el **número** de fugas.
  - `test_secciones_presentes(pdf_real)`: las 6 claves de `SECCIONES_UTILES` existen y ninguna está vacía.
- [ ] **Step 2:** `cd backend && ../.venv/Scripts/python.exe -m pytest tests/lector/test_entrada.py -v` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3:** Implementar `errores.py`, `entrada.py` y `__init__.py` según las interfaces; añadir `pdfplumber` a `pyproject.toml`.
- [ ] **Step 4:** Repetir el comando → PASS (con los PDF locales presentes).
- [ ] **Step 5: Commit** `feat(lector): entrada validada y segmentación por posición sin secciones I y VII`.

---

### Task 2: Utilidades de texto y presentación (L2)

**Files:**
- Create: `backend/app/silabo/lector/texto.py`, `backend/app/silabo/lector/presentacion.py`, `backend/tests/lector/test_texto.py`, `backend/tests/lector/test_presentacion.py`

**Interfaces:**
- Consumes: `segmentar` (Tarea 1), solo en el ensamblador; aquí, tablas y texto.
- Produces:
  - `normalizar_clave(texto: str) -> str`: mayúsculas, sin tildes, espacios colapsados y sin saltos (reutiliza `app.agentes.facultades.normalizar` y además quita `\n`).
  - `fecha_dmy(texto: str) -> date`: `"07/10/2026"` → `date(2026, 10, 7)`.
  - `horas(texto: str | None) -> float`: `None`, `""` o `"0"` dan `0.0`; `"5"` da `5.0`; `"1,5"` da `1.5`.
  - `entregables_en(*textos: str) -> list[str]`: devuelve las coincidencias en su forma canónica, `"TAREA 1"`, `"PAE 2"`, `"EVALUACIÓN COGNITIVA 1"`, en orden de aparición y sin duplicados.
  - `semana_periodo(fecha: date, inicio: date) -> int`: semana 1 = la del lunes de `inicio`.
  - `leer_cabecera(portada: str, tablas_ii: list, tablas_iii: list, texto_iii: str) -> dict`: devuelve las claves `facultad, carrera, periodo, proyecto_formativo, competencia_perfil, competencia_pf, metacompetencia, resultados_aprendizaje, problema, pis, metodologias`, con los tipos de `SilaboUTI` en forma de dict. El horario `"Miércoles 20:00 a 20:59"` da `{"dia": "miercoles", "inicio": "20:00", "fin": "20:59"}`. La metacompetencia es la fila marcada con `X`. Problema, PIS y metodologías están en la página 4, junto al título IV. El ensamblador le pasa a `leer_cabecera` las tablas de III más las de IV anteriores a la primera tabla «Momento 1», y `leer_cabecera` las localiza por su rótulo, sin importar en qué sección cayeron.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_texto.py`: `fecha_dmy`, `horas` (los 4 casos de arriba), `semana_periodo(date(2026,10,7), date(2026,10,5)) == 1`, `semana_periodo(date(2026,11,11), date(2026,10,5)) == 6`, `entregables_en("Elaborar TAREA 1 – infografía", "pae 1 y Evaluación cognitiva 1") == ["TAREA 1", "PAE 1", "EVALUACIÓN COGNITIVA 1"]`.
  - `test_presentacion.py`: tablas sintéticas construidas en la prueba con la forma de `pdfplumber` (filas con `None` en las celdas combinadas). Comprueba `nivel == 3`, `horas.total == 144`, `horario[0].dia == "miercoles"`, que `competencia_pf == ""` cuando la celda está vacía (caso TIC) y que el RA se lee con su evidencia.
- [ ] **Step 2:** `pytest tests/lector/test_texto.py tests/lector/test_presentacion.py -v` → FAIL.
- [ ] **Step 3:** Implementar. Las celdas se localizan por su rótulo (`normalizar_clave(celda).startswith(...)`), nunca por índice fijo de fila.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat(lector): utilidades de texto y lectura de la presentación`.

---

### Task 3: Momentos, sesiones y rúbricas (L3 + L4 de momento)

**Files:**
- Create: `backend/app/silabo/lector/momentos.py`, `backend/tests/lector/test_momentos.py`

**Interfaces:**
- Consumes: `texto.py` (Tarea 2).
- Produces:
  - `leer_momentos(tablas_iv: list[list[list[str | None]]], texto_iv: str, inicio_periodo: date) -> list[dict]`: un dict por momento con las claves de `Momento` (`numero, titulo, fecha_inicio, fecha_fin, ra, evidencia, recursos, politica_ia, rubrica, sesiones`). Cada sesión trae `id`, `numero`, `fecha`, `semana_periodo`, `docente{texto, horas, asincronica?}`, `practico`, `autonomo`, `contenidos` y `entregables`.
  - Columnas de la tabla de sesiones, identificadas por palabra clave normalizada del encabezado: `SESION` → sesión y fecha; `DOCENTE` → docente; `PRACTICO` → práctico; `AUTONOMO` → autónomo; `CONTENIDO` → contenidos; `HORA` → las horas de la actividad inmediatamente a su izquierda.
  - La asincrónica: dentro de la celda del docente, el texto desde «Otras actividades con el docente (N h)» se separa en `asincronica={"texto": …, "horas": N}`.
  - Contenidos: líneas con viñeta (`•`, `-`, `●`) o, si no hay, la celda completa como un elemento.
  - Rúbrica: las filas después de un encabezado `Indicador | Receptivo | … | Cocreativo` se convierten en `{"indicador", "niveles": {receptivo…cocreativo}}`; termina en la siguiente tabla de «Momento N» o al cambiar de sección.
  - `ra`: los `RA\d+` que aparecen en la cabecera del momento, en orden.

- [ ] **Step 1: Escribir las pruebas que fallan** (tablas sintéticas):
  - `test_sesion_basica`: una fila `["Sesión 1\n07/10/2026", "Clase …", None, "6", "Práctica JASP", "4", "TAREA 1 – …", "2", "• Datos unidimensionales"]` da `id == "M1-S1"`, `fecha == date(2026,10,7)`, `semana_periodo == 1`, `docente.horas == 6.0` y `entregables == ["TAREA 1"]`.
  - `test_fila_partida_se_une`: la fila siguiente tiene la primera celda vacía y más texto en la columna de contenidos; el resultado sigue teniendo 1 sesión, con los contenidos de ambas filas.
  - `test_columnas_por_palabra_clave`: el mismo caso, con el encabezado `"Actividades de trabajo autónomo"` y `"Hora s"`, da el mismo resultado.
  - `test_asincronica_separada`: la celda del docente con `"… Otras actividades con el docente (5 h): foro"` da `asincronica.horas == 5.0`.
  - `test_rubrica_cinco_niveles`: 3 filas de indicadores dan 3 `FilaRubrica` con las 5 claves exactas.
  - `test_latex_intacto`: `"$H_0/H_1$"` llega igual a `contenidos`.
  - `test_fila_total_se_ignora`: la fila que empieza con `"Total"` no crea sesión.
- [ ] **Step 2:** `pytest tests/lector/test_momentos.py -v` → FAIL.
- [ ] **Step 3:** Implementar `leer_momentos`.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat(lector): momentos, sesiones partidas, asincrónicas y rúbricas`.

---

### Task 4: Evaluación final y bibliografía (L4)

**Files:**
- Create: `backend/app/silabo/lector/cierre.py`, `backend/tests/lector/test_cierre.py`

**Interfaces:**
- Produces:
  - `leer_rubrica_final(tablas_v: list) -> list[dict]`: reutiliza el lector de rúbricas de la Tarea 3; para eso, expone en `momentos.py` la función `leer_rubrica(filas: list[list[str | None]]) -> list[dict]`.
  - `leer_bibliografia(tablas_vi: list, texto_vi: str) -> dict`: `{"basica": [...], "complementaria": [...]}`, una referencia por fila, sin inventar ni completar datos.

- [ ] **Step 1:** Pruebas sintéticas `test_rubrica_final` (2 indicadores) y `test_bibliografia_dos_listas` (las filas bajo «Básica» y «Complementaria» van a su lista; el enlace se conserva dentro del texto).
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat(lector): rúbrica del producto final y bibliografía`.

---

### Task 5: Ensamblado y criterios 1 y 5 (L5)

**Files:**
- Create: `backend/app/silabo/lector/ensamblar.py`, `backend/tests/lector/test_reales.py`
- Modify: `backend/app/silabo/lector/__init__.py` (exportar `leer_silabo`)

**Interfaces:**
- Consumes: Tareas 1–4.
- Produces: `def leer_silabo(datos: bytes) -> SilaboUTI`. Abre, segmenta, llama a los analizadores y valida con `SilaboUTI.model_validate`. Una `ValidationError` o la falta de los datos mínimos se convierte en `SilaboIlegible`, con un motivo que nombra el **campo**, nunca su valor. No escribe el PDF en disco: borrar el archivo subido le corresponde a P4.

- [ ] **Step 1: Escribir las pruebas que fallan** en `test_reales.py` (se omiten sin los PDF):
  - `test_criterio_1_datos`: 4 momentos; 11 sesiones con los ids y las fechas de `mapeo-silabo.md` §4.1 (de `M1-S1` el 07/10 a `M4-S3` el 11/11); `M3-S4.semana_periodo == 4`; `carrera == "SOFTWARE"`; `proyecto_formativo.codigo == "B26-SOFT-3-56146-1727"`; `proyecto_formativo.nivel == 3`; cada momento tiene una rúbrica no vacía con las 5 claves.
  - `test_criterio_1_tic`: 4 momentos; 6 sesiones según §4.2; `M1.ra == ["RA1", "RA2"]`; `M2-S2.entregables` contiene `"PAE 1"` y `"EVALUACIÓN COGNITIVA 1"`; `competencia_pf == ""`.
  - `test_criterio_5_sin_datos_personales` (para los dos PDF): `leer_silabo(...).model_dump_json()` no contiene `@`, ni la cadena `"orcid"` (sin distinguir mayúsculas), ni secuencias de 9 o más dígitos, ni ninguno de los tokens de `datos_personales(pdf)` (Tarea 1).
  - `test_fixture_coincide_con_el_lector`: la fixture versionada `tests/fixtures/silabo_datos.json` (M2 y M3) coincide campo por campo con los momentos 2 y 3 que lee `leer_silabo` del PDF de Datos. Si difieren, se corrige el lector; la fixture se transcribió a mano del PDF en T3.
  - `test_pdf_invalido_da_silabo_ilegible`: `leer_silabo(b"no es pdf")` lanza `SilaboIlegible`.
- [ ] **Step 2:** `pytest tests/lector -v` → FAIL.
- [ ] **Step 3:** Implementar `ensamblar.py`.
- [ ] **Step 4:** `pytest -q` → toda la suite PASS.
- [ ] **Step 5: Commit** `feat(lector): leer_silabo ensamblado con los criterios 1 y 5`.

---

### Task 6: Menú por semana y versiones (L6)

**Files:**
- Create: `backend/app/silabo/menu.py`, `backend/tests/test_menu.py`

**Interfaces:**
- Consumes: `SilaboUTI`, `contexto_clase` (`app/silabo/contexto.py`).
- Produces:
  - `class ClaseMenu(BaseInmutable)`: `clase_id: str`, `numero_clase: int` (orden cronológico 1…N en la asignatura), `dia: str` (`"lun"`…`"dom"`), `fecha: date`, `momento: int`, `momento_titulo: str`, `contenidos: list[str]`, `ra: list[str]`, `entregables: list[str]`.
  - `class SemanaMenu(BaseInmutable)`: `numero: int`, `inicio: date` (lunes), `fin: date` (domingo), `clases: list[ClaseMenu]`, `cierra_momentos: list[int]` (los momentos cuya última sesión cae en esa semana).
  - `def construir_menu(silabo: SilaboUTI) -> list[SemanaMenu]`: solo las semanas que tienen clases, en orden.
  - `def clases_cambiadas(anterior: SilaboUTI, nuevo: SilaboUTI) -> set[str]`: los ids cuyo `contexto_clase` difiere, más los ids nuevos. Solo se comparan sílabos del mismo `proyecto_formativo.codigo`; si los códigos difieren, `ValueError`.
  - El estado de cada clase (sin generar, en cola, …) **no** es parte de esta función: lo agrega P4 desde la base de datos.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_menu_con_la_fixture`: con la fixture (M2 y M3 de Datos), las semanas son `[2, 3, 4]`; la semana 2 va del 12/10 al 18/10 y tiene `M2-S1` (`"mie"`, 14/10) y `M2-S2` (`"jue"`); `cierra_momentos` de la semana 2 es `[2]`.
  - `test_numero_de_clase_cronologico`: `numero_clase` es 1, 2, 3… en orden de fecha a lo largo de toda la asignatura.
  - `test_criterio_2_reales` (se omite sin los PDF): Datos da 6 semanas y TIC da 4.
  - `test_version_marca_solo_lo_cambiado`: una copia de la fixture con un contenido distinto en `M3-S2` da `clases_cambiadas(...) == {"M3-S2"}`; con la misma fixture, el resultado es `set()`.
  - `test_versiones_de_otra_asignatura`: códigos distintos dan `ValueError`.
- [ ] **Step 2:** `pytest tests/test_menu.py -v` → FAIL. **Step 3:** Implementar. **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5: Commit** `feat(silabo): menú por semana y día con detección de clases cambiadas`.

---

## Cierre del P2

- Actualizar `progress.md`: tablero P2, criterios 1, 2 y 5, y bitácora.
- El criterio 5 queda completo con el P1 (prompts) y la Tarea 5 (lector).
- La ruta de respaldo con IA (L7) sigue pendiente del bloqueo B7.
