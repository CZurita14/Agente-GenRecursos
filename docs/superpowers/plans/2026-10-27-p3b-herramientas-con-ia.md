# P3b · Herramientas con IA de momento y asignatura — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar con el Qwen local las cinco herramientas con IA de momento y asignatura del catálogo: repaso integrador (#9), estudio de caso (#10), simulacro (#11), guía de la evidencia (#14) y guía del producto final (#16). Las cinco pasan por el verificador y el revisor, y respetan la integridad académica (§9.4).

**Architecture:** Todo el núcleo (prompts, sello, verificador, revisor, planificador y coordinador) trabaja con `ContextoClase`. En lugar de reescribirlo, se construye un **`ContextoClase` del ámbito**:
- **momento** (`clase_id = "M2"`): junta los contenidos, actividades y entregables de sus sesiones, con su RA, rúbrica y política;
- **asignatura** (`clase_id = "asignatura"`): todos los contenidos, la rúbrica final y el producto final como entregable.

El orquestador y el coordinador obtienen el contexto con `contexto_ambito`. Los workers nuevos siguen el patrón del worker de ficha (JSON de esquema cerrado, un lote por sección). El simulacro reutiliza el worker de cuestionario con el contexto del momento.

**Tech Stack:** Python 3.13, Pydantic 2, Qwen3-8B-AWQ en vLLM (salida `json_schema`), PostgreSQL, pytest.

**Spec:** [spec v1.3](../../especificacion-generador-recursos-uti-v1.3.md) §6, §8.2, §9.4 y §10; [catálogo](../../catalogo-herramientas.md) #9, #10, #11, #14 y #16. Se apoya en P1 (núcleo), P3a (ámbitos `M<n>` y `asignatura`) y la decisión C9 (escenarios distintos del entregable).

## Global Constraints

- Solo el Qwen local razona. Ninguna llamada pasa de 8 192 tokens (criterio 4); la sección del ámbito nunca se recorta.
- Ids de ámbito como en P3a: `M<n>` y `asignatura`.
- **§9.4 regla 1:** ninguna herramienta entrega la solución ni un borrador de un entregable. La evidencia del momento y el producto final cuentan como entregables (C9).
- **§9.4 regla 2:** si la política del momento excluye la IA en una evaluación, en ese momento solo se ofrece el **repaso integrador de momentos anteriores**. Las demás herramientas con IA de ese momento responden `422`.
- **§9.4 regla 3:** cada herramienta lleva la política de IA de su ámbito.
- **H8:** el simulacro se publica como **borrador** (`evidencia.borrador = true`), igual que el cuestionario, hasta cumplir 14/16 ítems sólidos.
- Fuera de alcance: H7 (techo del RA, requiere al área académica) y la plantilla final (B3).

## Review Focus

1. **Momento cuya política excluye la IA** (TIC M4: «sin asistencia de IA»): no se ofrecen simulacro, estudio de caso ni guía, y el repaso solo cubre momentos anteriores. Lo cubren `test_politica_restrictiva_tic_m4` (T2) y `test_generar_restringido_422` (T7).
2. **Guía de la evidencia que la resuelve:** es el mayor riesgo de integridad. Debe pasar por el revisor de integridad y, además, por un control determinista que la devuelva si copia el texto de la evidencia más allá de citarla. Lo cubre `test_guia_no_reproduce_la_evidencia` (T5).
3. **Estudio de caso con el escenario del evaluado:** el escenario lo asigna el planificador (C9) y el verificador comprueba que no comparta palabras clave con los entregables. Lo cubre `test_caso_distinto_del_evaluado` (T5).
4. **Momento sin sesiones, sin rúbrica o sin política** (TIC M3 sale con la política vacía): `contexto_ambito` no falla, y la herramienta que necesite la rúbrica responde `422`. Lo cubren `test_momento_sin_politica` (T1) y `test_politica_tic_m3` (T1, que primero averigua si es un defecto del lector).
5. **Reanudación tras una caída** con un trabajo de momento a medio hacer: debe comportarse como uno de clase. Lo cubre `test_retoma_trabajo_de_momento` (T3).

---

### Task 1: Contexto de momento y de asignatura

**Files:** Modify `backend/app/silabo/contexto.py`, `backend/app/llm/prompts.py`; Test `backend/tests/test_contexto_ambito.py`.

**Interfaces — Produces:**
- `contexto_momento(silabo, "M<n>") -> ContextoClase`:
  - `clase_id = "M<n>"`, `fecha = momento.fecha_inicio`;
  - `contenidos`: los de las sesiones, sin repetir y en orden;
  - `actividades`: una por sesión, con el texto con el docente y el práctico;
  - `entregables_momento = [evidencia] + entregables de las sesiones`;
  - lanza `KeyError` si el momento no existe.
- `contexto_asignatura(silabo) -> ContextoClase`:
  - `clase_id = "asignatura"`, `fecha = periodo.inicio`, `momento_titulo = nombre del PF`;
  - `contenidos`: todos, sin repetir;
  - `ra`: todos los RA;
  - `rubrica = rubrica_producto_final`;
  - `politica_ia`: las de los momentos, unidas como «M1: …; M2: …»;
  - `entregables_momento = [producto_final] + evidencias`.
- `contexto_ambito(silabo, Ambito) -> ContextoClase`: según el tipo, usa `contexto_clase`, `contexto_momento` o `contexto_asignatura`.
- `prompts._seccion_clase`: el título dice «Momento M2 · …» o «Asignatura · …» según el `clase_id`, y el sello dice «Momento M2» o «Asignatura».

- [x] Pruebas:
  - `test_contexto_momento_m3`: 4 sesiones de contenidos y la evidencia como primer entregable.
  - `test_contexto_asignatura`: todos los RA y la rúbrica final.
  - `test_momento_inexistente`: `KeyError`.
  - `test_momento_sin_politica`.
  - `test_politica_tic_m3`: averigua con el PDF real si la política de TIC M3 está vacía en el documento. Si es un defecto del lector, se corrige con su propia prueba en `tests/lector`.
  - `test_prompt_de_momento_cabe` (marca `servidor`): mide con `/tokenize` del vLLM real el prompt más grande de los dos sílabos, para todo ámbito y herramienta. Deben quedar ≥ 3 500 tokens para la salida.
- [x] RED, implementación y GREEN; commit `feat(silabo): contexto de momento y de asignatura`.

### Task 2: Política de IA restrictiva (§9.4 regla 2)

**Files:** Create `backend/app/herramientas/politica.py`; Test `backend/tests/test_politica_ia.py`.

**Interfaces — Produces:** `excluye_ia_en_evaluacion(politica: str) -> bool`, sobre el texto normalizado. Detecta «sin (asistencia|uso|apoyo) de (la )?IA», «no se permite (el uso de )?(la )?IA» y «prohibido el uso de (la )?IA». No se activa con «se permite… IA».

- [x] Pruebas:
  - `test_politica_restrictiva_tic_m4`: la política real de TIC M4 da `True`.
  - `test_politicas_permisivas`: las de Datos M1–M4 y TIC M1–M2 dan `False`.
  - Casos sintéticos de cada patrón y la frase vacía.
- [x] Commit `feat(herramientas): detección de política de IA restrictiva`.

### Task 3: Núcleo por ámbito

**Files:** Modify `backend/app/agentes/orquestador.py`, `backend/app/agentes/coordinador.py`, `backend/app/agentes/workers/__init__.py`, `backend/app/agentes/workers/base.py`.

**Interfaces:**
- `crear_trabajos` acepta los ámbitos `momento` y `asignatura` para las herramientas con IA de ese ámbito: `WORKERS_AMBITO: dict[str, str]`, con la herramienta y su tipo de ámbito.
- `procesar_uno` y `Coordinador.ejecutar` usan `contexto_ambito`.
- Cada worker declara `lotes: int`. El coordinador usa `planificar` si `worker.es_quiz` y, si no, `[[]] * worker.lotes`, en lugar de distinguir por nombre de herramienta.

- [x] Pruebas de regresión: toda la suite de P1 sigue en verde sin cambios de comportamiento para `cuestionario` y `ficha_clase`.
- [x] Pruebas nuevas:
  - `test_trabajo_de_momento_simulado`: un worker simulado de momento produce un recurso `listo`.
  - `test_retoma_trabajo_de_momento`: caída y reanudación.
- [x] Commit `refactor(agentes): núcleo por ámbito con lotes declarados por el worker`.

### Task 4: Simulacro

**Files:** Modify `backend/app/agentes/workers/__init__.py`; Test `backend/tests/test_simulacro.py`.

- El `simulacro` es el `WorkerCuestionario` con el contexto del momento. `cantidad` por defecto: 12. El solucionario son la clave, las justificaciones por opción y el razonamiento que ya trae cada ítem.
- La tabla de especificaciones se reparte sobre los contenidos del momento, y los focos salen de las actividades de todas sus sesiones.

- [x] Pruebas, con el cliente simulado:
  - `test_simulacro_m3`: 12 ítems con contenidos de las 4 sesiones de M3, la tabla del perfil y `borrador = true`.
  - `test_simulacro_con_clase_ajena_se_devuelve`: el verificador rechaza un contenido de otro momento.
- [x] Commit `feat(workers): simulacro por momento`.

### Task 5: Repaso integrador, guía de la evidencia y estudio de caso

**Files:** Create `backend/app/agentes/workers/momento.py`; Modify `backend/app/herramientas/esquemas.py`, `backend/app/agentes/verificador.py`, `backend/app/agentes/revisor.py`; Test `backend/tests/test_workers_momento.py`.

**Esquemas (JSON cerrado, `extra="forbid"`):**
- `repaso_momento`, 1 lote: `sesiones: [{clase_id (enum de las sesiones del momento), ideas_clave: 3–5}]`, `conexion_ra: str` y `preguntas_repaso: 3–5`.
- `guia_evidencia`, 1 lote:
  - `que_se_pide`: paráfrasis de la evidencia, ≤ 600 caracteres;
  - `como_se_valora: [{indicador (enum de la rúbrica), que_observar}]`;
  - `errores_comunes: 3–5`;
  - `autochequeo: 3–5` preguntas;
  - sin campo de «respuesta».
- `estudio_caso`, 1 lote: `caso` (≥ 300 caracteres, ambientado en el escenario asignado), `preguntas: [{nivel, pregunta, respuesta_orientativa}]` (3–6, de menor a mayor nivel) y `ra` (enum).

**Verificador** (`verificar_seccion(herramienta, contenido, contexto) -> list[str]`):
- ids, RA e indicadores que pertenecen al ámbito;
- frases prohibidas (§6.3);
- `guia_evidencia`: ninguna secuencia de 12 o más palabras copiada de la evidencia fuera de `que_se_pide`;
- `estudio_caso`: el caso no comparte palabras clave (≥ 6 letras) con los entregables, con la regla de `_casos_libres` (C9).

**Revisor:** `revisar_ficha` (solo integridad, con `CRITERIO_INTEGRIDAD`) se reutiliza para las tres herramientas.

- [x] Pruebas:
  - `test_repaso_m3`;
  - `test_guia_no_reproduce_la_evidencia`;
  - `test_caso_distinto_del_evaluado`;
  - `test_esquemas_rechazan_campos_extra`;
  - `test_revisor_devuelve_guia_que_resuelve` (revisor simulado).
- [x] Commit `feat(workers): repaso integrador, guía de la evidencia y estudio de caso`.

### Task 6: Guía del producto final (asignatura)

**Files:** Modify `backend/app/agentes/workers/momento.py`, `backend/app/herramientas/esquemas.py`; Test en `backend/tests/test_workers_momento.py`.

- Esquema `guia_producto_final`, 1 lote:
  - `ruta: [{momento (enum), aporte}]`, uno por momento;
  - `criterios: [{indicador (enum de la rúbrica final), como_prepararse}]`;
  - `recomendaciones: 3–5`.
- La ruta parte de las evidencias de cada momento, que el código pasa al prompt. El modelo solo redacta el aporte, sin resolver el producto.
- [x] Pruebas:
  - `test_guia_producto_final`: un elemento de la ruta por momento y criterios de la rúbrica final;
  - `test_sin_rubrica_final_422`.
- [x] Commit `feat(workers): guía del producto final`.

### Task 7: API — catálogo, generación y ediciones

**Files:** Modify `backend/app/recursos/servicio.py`, `backend/app/recursos/validacion.py`; Test `backend/tests/test_ia_ambito_api.py`.

- `catalogo(momento)`: las herramientas sin IA y con IA del ámbito. Si `excluye_ia_en_evaluacion(politica)` es verdadero, solo se ofrecen el repaso (de momentos anteriores) y las herramientas sin IA, y la respuesta lleva `restringido: true` con el motivo.
- `generar`:
  - con IA de momento o asignatura: encola como en clase;
  - en un momento restringido: `422`, salvo `repaso_momento` de un momento anterior;
  - pedidos mixtos (con y sin IA): `422`.
- `validar_contenido`: el simulacro se valida como el cuestionario; las tres secciones de T5 y la guía de T6 se validan contra su esquema y con `verificar_seccion`.
- [x] Pruebas:
  - `test_generar_simulacro_encola`;
  - `test_generar_restringido_422`;
  - `test_catalogo_restringido_tic_m4` (con el PDF real, si está disponible);
  - `test_edicion_de_guia_valida`;
  - `test_edicion_de_guia_que_copia_la_evidencia_se_rechaza`.
- [x] Commit `feat(recursos): herramientas con IA de momento y asignatura en la API`.

### Task 8: Humo real con Qwen (puerta: GPU y autorización del usuario)

**Files:** Modify `backend/tests/test_humo_servidor.py` (caso nuevo con marca `servidor`).

- Datos M3: `simulacro` (4 ítems), `guia_evidencia` y `estudio_caso`. Asignatura: `guia_producto_final`. Con `HUMO_GUARDAR`.
- [x] Registrar en `docs/prueba-calidad-silabo.md` §7:
  - estado de cada recurso;
  - devoluciones y sus motivos;
  - tokens máximos por llamada (≤ 8 192);
  - tiempos.
- [x] Commit `test: humo real de herramientas de momento`.

## Cierre

- Revisión final de toda la rama por un revisor independiente, con foco en la integridad (§9.4) y en los Review Focus 1–3.
- Actualizar `progress.md` y la tabla de cambios del spec si surge alguna decisión nueva.
- Quedan para después: H7 (techo del RA), las herramientas de clase restantes (#2, #3, #5–#8) y la plantilla (B3).
