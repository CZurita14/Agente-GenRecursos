# P3a · Herramientas sin IA — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ofrecer las cuatro herramientas del catálogo que salen del sílabo tal cual, sin IA: hoja de ruta de la asignatura (#15), autoevaluación con la rúbrica del momento (#12), autoevaluación final (#17) y lista de verificación de la evidencia (#13).

**Architecture:** Generadores **puros** en `backend/app/herramientas/sin_ia.py`: reciben un `SilaboUTI` y el id del ámbito y devuelven el contenido en JSON. Ese contenido es texto del sílabo más textos de instrucción fijos. `ServicioRecursos.generar` los ejecuta **en la misma transacción**: crea un `trabajo` ya `listo`, con la instantánea del sílabo en `parametros`, y su `recurso`. Así el listado de trabajos y la unión trabajo-recurso siguen iguales y el worker nunca los toma. No hace falta migración: el esquema ya admite los ámbitos `momento` y `asignatura` y el estado `listo`.

**Tech Stack:** Python 3.13, Pydantic 2, FastAPI, PostgreSQL, pytest.

**Spec:** [spec v1.3](../../especificacion-generador-recursos-uti-v1.3.md) §8.2 y §9.4; [catálogo](../../catalogo-herramientas.md) #12, #13, #15 y #17.

## Global Constraints

- **No se inventa contenido:** cada texto viene del sílabo o es una instrucción fija del código. Sin llamadas al modelo.
- Ids de ámbito: momento = `M<n>` (por ejemplo, `M2`); asignatura = `asignatura`.
- Niveles de la rúbrica, en este orden: `receptivo`, `resolutivo`, `reflexivo`, `critico`, `cocreativo`.
- Toda herramienta lleva la política de IA que le corresponde: la del momento o, en la asignatura, la de cada momento.
- El formato final lo dará la plantilla académica (B3): el contenido es JSON estructurado, y su presentación HTML llega en P6.
- Estas herramientas **no se editan** (reproducen el sílabo): `PUT` responde `422`. Para cambiarlas se sube una versión nueva del sílabo.

## Review Focus

1. **Momento sin rúbrica o sílabo sin rúbrica final:** debe dar `422` claro, no un recurso vacío. Lo cubren `test_sin_rubrica_final_da_error` (T1) y `test_generar_final_sin_rubrica_422` (T2).
2. **Ámbito o herramienta que no corresponden** (`hoja_ruta` con ámbito `clase`, o `M9` inexistente): `422` sin crear nada a medias. Lo cubre `test_ambito_incorrecto_no_crea_nada` (T2).
3. **Pedido mixto** de herramientas con y sin IA en un mismo ámbito: en la práctica no ocurre, porque las de IA son de clase y las sin IA son de momento o asignatura. El ámbito decide, y una herramienta que no corresponde da `422`. Lo cubre la misma prueba.
4. **Sílabo actualizado:** el indicador `silabo_actualizado` de un recurso sin IA debe compararse regenerando con la instantánea original y con el sílabo actual. Lo cubre `test_silabo_actualizado_en_recurso_sin_ia` (T2).
5. **Lector sin permiso de escritura:** no puede generar (`403`), pero sí consultar. Lo cubre `test_lector_no_genera_sin_ia` (T2).

---

### Task 1: Generadores puros

**Files:** Create `backend/app/herramientas/sin_ia.py`, `backend/tests/test_sin_ia.py`.

**Interfaces — Produces:**
- `HERRAMIENTAS_SIN_IA: dict[str, str]`, con el id de la herramienta y su tipo de ámbito: `{"hoja_ruta": "asignatura", "autoevaluacion_rubrica": "momento", "autoevaluacion_final": "asignatura", "lista_evidencia": "momento"}`.
- `generar_sin_ia(herramienta: str, silabo: SilaboUTI, ambito_id: str) -> dict`. Lanza `ValueError` si la herramienta, el ámbito o el contenido requerido (la rúbrica) no existen.
- Contenidos:
  - `hoja_ruta`: `asignatura`, `codigo`, `periodo`, `semanas` (de `construir_menu`: número, inicio, fin y clases con id, día, fecha, momento, contenidos y entregables), `momentos` (número, título, fechas, RA, evidencia y política de IA) y `producto_final`.
  - `autoevaluacion_rubrica`: `momento`, `titulo`, `evidencia`, `ra` (id y texto), `niveles`, `indicadores` (`indicador`, `descriptores`, `para_subir`: nivel → descriptor del nivel siguiente; `null` en cocreativo), `instrucciones` y `politica_ia`.
  - `autoevaluacion_final`: la misma forma, a partir de `rubrica_producto_final`, con `evidencia = problema.producto_final`.
  - `lista_evidencia`: `momento`, `titulo`, `evidencia`, `entregables` (los de las sesiones del momento), `items` (`indicador` y `referencia_resolutivo`) y `politica_ia`.

- [ ] Pruebas, con la fixture (M2 y M3 de Datos):
  - `test_hoja_ruta_con_la_fixture`: semanas `[2, 3, 4]` y momentos `[2, 3]`.
  - `test_autoevaluacion_rubrica_m2`: los indicadores son los de la rúbrica de M2; `para_subir["receptivo"]` es el descriptor `resolutivo` y `para_subir["cocreativo"]` es `None`.
  - `test_autoevaluacion_final`: los indicadores son los de la rúbrica final.
  - `test_lista_evidencia_m3`: la evidencia es la de M3 y hay un ítem por indicador.
  - `test_textos_salen_del_silabo`: todo descriptor e indicador del contenido aparece literal en el sílabo.
  - `test_sin_rubrica_final_da_error`.
  - `test_ambito_inexistente`: `M9` y `asignatura` en una herramienta de momento dan `ValueError`.
- [ ] RED, implementación y GREEN; commit `feat(herramientas): generadores sin IA del sílabo (P3a)`.

### Task 2: Integración en la API

**Files:** Modify `backend/app/recursos/servicio.py`; Create `backend/tests/test_sin_ia_api.py`.

**Interfaces — Consumes:** `HERRAMIENTAS_SIN_IA` y `generar_sin_ia` (T1).
- `catalogo(ambito)`: en `momento` y `asignatura`, lista las herramientas sin IA de ese ámbito, ordenadas según `herramientas_recomendadas` del perfil.
- `generar`:
  - si todas las herramientas son sin IA y corresponden al ámbito, crea, por cada una y en la misma transacción, un `trabajo` (`estado='listo'`, `parametros` con `silabo` y `version_silabo`) y un `recurso` (`estado='listo'`, `evidencia={"origen": "silabo", "sin_ia": true, "ambito": …}`). Responde `202` con `estado: "listo"` y el `recurso_id`.
  - cualquier mezcla o ámbito que no corresponda da `422` sin efectos.
- `obtener`: para herramientas sin IA, `silabo_actualizado` resulta de comparar `generar_sin_ia` con la instantánea y con el sílabo actual.
- `editar`: las herramientas sin IA responden `422`.

- [ ] Pruebas HTTP:
  - `test_genera_hoja_ruta_al_instante`: `202`, trabajo `listo` en `/trabajos` y recurso legible.
  - `test_catalogo_por_ambito`.
  - `test_ambito_incorrecto_no_crea_nada`.
  - `test_generar_final_sin_rubrica_422`.
  - `test_no_se_editan`.
  - `test_silabo_actualizado_en_recurso_sin_ia`.
  - `test_lector_no_genera_sin_ia`.
  - `test_aislamiento`: el recurso de otra asignatura da `404`.
- [ ] RED, implementación y GREEN con la suite completa; commit `feat(recursos): herramientas sin IA generadas al instante`.

### Cierre

- Revisión final, la ruta crítica revisada por mí.
- `progress.md`: P3a y su bitácora.
- Pendiente para P3b: herramientas con IA de momento y asignatura, y H7 (techo del RA).
