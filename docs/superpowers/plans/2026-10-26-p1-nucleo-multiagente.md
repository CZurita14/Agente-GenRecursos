# P1 · Núcleo multiagente — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un proceso `worker` toma un trabajo de la cola en PostgreSQL. El agente de facultad lo descompone en lotes, los workers de `cuestionario` y `ficha_clase` generan, el verificador y el revisor controlan, y el resultado queda guardado como recurso con su paquete de evidencia. Todos los pasos se registran como mensajes tipados.

**Architecture:** Python con Pydantic y psycopg 3, sin frameworks de agentes (spec §3.6).
- Cada rol (§3.2) es una clase o función con entradas y salidas tipadas.
- El coordinador los encadena según §3.3.
- Un solo cliente de IA aplica presupuesto, reintentos y registro.
- La cola usa `FOR UPDATE SKIP LOCKED` con lease y un carril por asignatura.
- Las pruebas usan un cliente de IA simulado; una prueba de humo opcional va contra el Qwen real.

**Tech Stack:** Python 3.14 (`.venv`), pydantic ≥ 2.12, pydantic-settings ≥ 2.11, psycopg[binary] ≥ 3.2.10, **openai ≥ 1.100** (SDK oficial, como en el documento de conexión del servidor), httpx ≥ 0.28 (para `/tokenize` y las pruebas), PyYAML ≥ 6.0.2, pytest ≥ 8.4. PostgreSQL 18 (`genrecursos-db`, `127.0.0.1:15432`).

**Motor de IA (confirmado el 2026-10-26):** el razonamiento y la generación corren **solo en el servidor local de la universidad**: vLLM `Qwen/Qwen3-8B-AWQ` en `http://172.16.8.69:8000/v1`, con API compatible con OpenAI y sin clave (el SDK exige el campo; se envía `"no-se-necesita"`). Comprobado desde la máquina de desarrollo:
- `GET /v1/models` → `max_model_len` 8192.
- `POST /tokenize` (en la raíz, sin `/v1`) → `count`.
- Con `enable_thinking: true` el razonamiento llega **dentro de `content` entre `<think>…</think>`**: el servidor no tiene el separador de razonamiento activado y el campo `reasoning` viene vacío. El razonamiento sale en inglés aunque el pedido sea en español.

No se usa ningún proveedor externo.

**Spec:** [`docs/especificacion-generador-recursos-uti-v1.2.md`](../../especificacion-generador-recursos-uti-v1.2.md) (§3, §4, §5, §6, §10, §11) · contrato del sílabo en [`docs/mapeo-silabo.md`](../../mapeo-silabo.md) §3 · análisis previo en [`2026-10-26-analisis-y-hoja-de-ruta-fase1.md`](2026-10-26-analisis-y-hoja-de-ruta-fase1.md) (hallazgos H1–H6).

## Global Constraints

- Contexto máximo del modelo: **8 192 tokens** (entrada + salida). Ninguna llamada lo supera (criterio 4).
- `LLM_BASE_URL` y `LLM_MODEL` van solo en configuración, **nunca con valor por defecto en el código** (§5.1).
- Toda llamada con esquema lleva `repetition_penalty: 1.05`. Ante JSON inválido, **hasta 2 reintentos** (§5.2).
- Uso por rol (§5.2):

  | Rol | Temperatura | Razonamiento | Salida |
  |---|---|---|---|
  | Workers | 0,4 | no | esquema |
  | Revisor | 0 | sí | texto libre con JSON al final |

- Presupuesto por parte (§5.3): instrucciones 900 · clase 900 · rúbrica 600 · perfil+territorio+estilo 500 · ya generados 400 · salida ≤ 3 500 · margen ≥ 300.
- Orden de recorte del contexto: ya generados → rúbrica → **nunca la clase** (H3).
- Lotes: **4 ítems** de cuestionario por llamada; ficha en **2 secciones**; el revisor trabaja de a **1 ítem por llamada**. El spec decía 3, pero la ronda v3 midió hasta 3 420 tokens y 125,6 s por ítem con razonamiento (R1 en la [revisión](2026-10-26-revision-planes-y-especializacion.md)).
- Límite de tiempo por llamada **según el rol**: workers y coordinador 120 s; revisor 240 s. Lease del trabajo: **360 s**, mayor que la llamada más larga. Un reintento ante error de red; después el trabajo pasa a `en_espera` (§5.4).
- Estados de un trabajo (§11): `en_cola | generando | verificando | revisando | listo | requiere_revision | error | en_espera`.
- Máximo **2 reintentos por lote** ante fallo de verificación y **2 rondas de devolución por ítem** del revisor (§3.3).
- Aislamiento A1–A8 (§3.8): cada mensaje lleva `trabajo_id` y `asignatura_id`; los workers no guardan estado; los prompts se arman solo en `llm/prompts.py` y empiezan con el sello de la asignatura.
- Ningún nombre, correo, teléfono ni ORCID del docente entra en un prompt (criterio 5). El contrato `SilaboUTI` no tiene esos campos.
- PostgreSQL en todos los entornos, nunca SQLite (H1). La asignatura se identifica con un `asignatura_id` UUID (H2).
- Idioma del código: identificadores en español, como en `pruebas/` y `kb/`.

## Review Focus

1. **El proceso `worker` muere a mitad de un trabajo** → al vencer el lease otro worker lo retoma desde el último lote guardado, sin duplicar ni perder ítems (prueba en la Tarea 13).
2. **Qwen devuelve JSON truncado o inválido** (bucle de espacios, `finish_reason=length`) → 2 reintentos. Si sigue fallando, el trabajo termina en `error` con un motivo legible, sin quedar en bucle (Tarea 6 y Tarea 14).
3. **Una clase con contenidos o rúbrica muy largos** → el prompt se recorta y nunca pasa de 8 192 tokens. Si la clase sola no cabe, el trabajo termina en `error` con el motivo "contexto excedido" (Tarea 7).
4. **El docente pulsa dos veces "Generar"** (dos trabajos de la misma asignatura a la vez) → el carril los serializa y ambos terminan (Tarea 4).
5. **El revisor no devuelve un JSON legible** → se reintenta una vez. Si sigue sin veredicto, el ítem llega como `requiere_revision` con el motivo "revisor sin veredicto"; nunca se da por aprobado (Tarea 12).

---

## Equipo de ejecución

El plan se ejecuta con **superpowers:subagent-driven-development**. Es el mismo patrón que construye el producto: un coordinador delega, cada entrega pasa por revisión y, si no cumple, vuelve al mismo implementador con observaciones concretas (máximo 2 rondas).

| Rol | Quién | Modelo | Skills | Responsabilidad | No hace |
|---|---|---|---|---|---|
| **Coordinador** | Sesión principal de Claude Code | Opus 5.5 | `subagent-driven-development`, `verification-before-completion` | Arma el encargo de cada tarea, lanza las olas, recibe los veredictos, devuelve con observaciones, marca los checkboxes, integra las ramas de las olas paralelas y escala al usuario | No escribe código de producto |
| **Implementador** | Subagente `general-purpose`, nuevo por tarea | Según la tarea (sonnet u opus) | `test-driven-development` | Escribe la prueba, la ve fallar, implementa, la ve pasar y hace commit en su rama | No toca archivos de otras tareas ni cambia interfaces ya entregadas |
| **Revisor de especificación** | Subagente `general-purpose`, nuevo | sonnet | — | Comprueba la entrega contra el texto de la tarea, las Global Constraints y la sección del spec citada: ¿están todas las pruebas pedidas?, ¿coinciden los valores exactos (8 192, 1.05, 0.8, ±1…)?, ¿hay algo de más? | No opina de estilo |
| **Revisor de código** | Subagente `general-purpose`, nuevo | sonnet, u opus en tareas críticas | `requesting-code-review` | Revisa correctitud, concurrencia, aislamiento A1–A8, manejo de errores, legibilidad y que el código siga el estilo de `pruebas/` y `kb/` | No reescribe; devuelve hallazgos |
| **Explorador** | Subagente `Explore` (solo lectura) | haiku | — | Busca textos y valores en `pruebas/` y `docs/` cuando una tarea los necesita (fixture, plantillas, esquemas de v3) | No edita |
| **Revisor final** | Subagente `general-purpose`, nuevo | opus | `requesting-code-review`, `verification-before-completion` | Revisa la rama completa del P1: corre `pytest -v`, recorre los criterios 3, 4, 5, 6, 7, 8, 11 y 14 y los 5 puntos del Review Focus | — |
| **Usuario (Christian)** | Persona | — | — | Puertas: encender Docker, aprobar el remoto y cualquier push, ejecutar la prueba de humo dentro de la red UTI, decidir cuando un revisor y el implementador no se ponen de acuerdo tras 2 rondas | — |

**Ciclo por tarea:**

```text
Coordinador ── encargo (texto de la tarea + Global Constraints + Interfaces de las dependencias)
     ▼
Implementador (rama p1/tN, worktree si la ola es paralela) ── TDD ── commit
     ▼
Revisor de especificación ──► ¿cumple? ── no ──► Coordinador devuelve al MISMO implementador (SendMessage)
     ▼ sí                                               (máx. 2 rondas; luego escala al usuario)
Revisor de código ─────────► ¿cumple? ── no ──► ídem
     ▼ sí
Coordinador: merge de p1/tN en p1/nucleo, marca los checkboxes, desbloquea las tareas que dependían de ella
```

**Encargo que recibe cada implementador** (el coordinador lo arma; el implementador no lee el plan completo):

1. El texto íntegro de su tarea.
2. Las Global Constraints.
3. Los bloques *Interfaces · Produces* de las tareas de las que depende.
4. Las rutas del spec y de `pruebas/` indicadas en su fila "Lee".
5. La instrucción: "no modifiques archivos fuera de tu lista **Files**; si necesitas cambiar una interfaz ya entregada, detente y repórtalo".

## Olas de ejecución

Las tareas de una misma ola no dependen entre sí y se lanzan **en paralelo**, cada una en su propio worktree (`isolation: "worktree"`). La ola siguiente arranca cuando el coordinador integró la anterior.

| Ola | Tareas | Depende de | Puerta del usuario antes de empezar |
|---|---|---|---|
| 0 | T1 Repositorio y configuración | — | Aprobar `git init` y el remoto (sin push) |
| 1 | T2 Migraciones · T3 Contrato del sílabo · T6 Cliente de IA | T1 | Encender Docker Desktop (`docker compose up -d db`) |
| 2 | T4 Cola | T2 | — |
| 3 | T5 Mensajes | T3, T4 | — |
| 4 | T7 Prompts · T8 Facultades · T9 Planificador | T5 (+ T6 para T7) | — |
| 5 | T10 Workers | T6, T7, T9 | — |
| 6 | T11 Verificador · T12 Revisor | T10 | — |
| 7 | T13 Coordinador de facultad | T8, T11, T12 | — |
| 8 | T14 Orquestador y proceso worker | T13 | — |
| 9 | T15 Humo con Qwen real | T14 | Estar en la red UTI y autorizar `LLM_REAL=1` |
| Final | Revisión de la rama completa | T1–T15 | Decidir el push de `p1/nucleo` |

## Asignación por tarea

| Tarea | Rol del producto que construye (§3.2) | Implementador | Revisor de código | Explorador | Lee además del encargo |
|---|---|---|---|---|---|
| T1 | Infraestructura | sonnet | sonnet | — | spec §14 (configuración) |
| T2 | Persistencia de cola, trazas y recursos | sonnet | sonnet | — | `kb/schema.sql`, spec §11 |
| T3 | Contrato con el **Lector** (P2) | sonnet | sonnet | Sí: extrae los textos de `CLASES` en `pruebas/prueba_calidad*.py` para la fixture | `mapeo-silabo.md` §3–§6 |
| T4 | **Cola** (patrón `DurableLaneQueue` de Hive) | **opus** | **opus** (concurrencia) | — | spec §3.6, `arquitectura-agentica-hive.md` §4.4 |
| T5 | **Mensajes** entre agentes | sonnet | sonnet | — | spec §3.7 |
| T6 | Cliente de IA (`llm/`) | sonnet | sonnet | Sí: `llamar` y `ultimo_json` de `pruebas/prueba_calidad_v2.py` | spec §5.1–§5.4, `uti-llm-server` |
| T7 | Constructor único de prompts (A3) | sonnet | **opus** (aislamiento y datos personales) | — | spec §3.8, §5.3 |
| T8 | **Agente de facultad**: perfil y enrutamiento | haiku | sonnet | — | spec §4.1–§4.3, `kb/catalogo.yaml` |
| T9 | **Planificador** | sonnet | sonnet | — | spec §6, §9.3 |
| T10 | **Workers** `cuestionario` y `ficha_clase` | **opus** | **opus** | Sí: `PLANTILLAS` y `esquema_lote` de `pruebas/prueba_calidad_v3.py` | spec §6.3, §8.2, `catalogo-herramientas.md`, `prueba-calidad-silabo.md` |
| T11 | **Verificador** | sonnet | sonnet | Sí: `verificar` de `pruebas/prueba_calidad_v2.py` | spec §10.1 |
| T12 | **Revisor** (IA) | **opus** | **opus** | Sí: `revisar` de `pruebas/prueba_calidad_v3.py` | spec §10.2, §9.4 |
| T13 | **Coordinador de facultad** y evidencia | **opus** | **opus** | — | spec §3.3, §10.3, `arquitectura-agentica-hive.md` §4.4 |
| T14 | **Orquestador** y proceso `worker` | **opus** | **opus** (hilos, aislamiento criterio 14) | — | spec §3.6, §3.8 |
| T15 | Validación contra el servidor real | sonnet | sonnet | — | `prueba-calidad-silabo.md` (para anotar resultados) |

**Criterio para elegir el modelo:**
- **opus** donde un error se propaga a todo lo demás: concurrencia, ciclo del coordinador, aislamiento, prompts del worker y del revisor (de ellos depende la calidad pedagógica).
- **sonnet** para tareas mecánicas con pruebas que dejan poco margen.
- **haiku** solo para la tarea más pequeña (T8) y para buscar texto.

**Escalamiento:**

| Situación | Qué hace el coordinador |
|---|---|
| El revisor rechaza 2 veces la misma tarea | Detiene la ola y presenta al usuario el desacuerdo, con ambas posiciones |
| Un implementador necesita cambiar una interfaz ya entregada | Pausa y decide con el usuario; si se aprueba, actualiza el plan y avisa a las tareas afectadas |
| Fallo de infraestructura (Docker apagado, sin red UTI) | No se reintenta en bucle: se pide la puerta al usuario |
| Conflicto de merge entre worktrees de una ola | Lo resuelve el coordinador y, si toca lógica, lo revisa el revisor de código de la tarea afectada |

---

## Estructura de archivos

```text
Agente-GeneradorRecursos/
├── .gitignore                         (modificar: rea/, .pytest_cache/)
├── .env.example                       (modificar: variables del backend)
├── agentes/
│   ├── ingenierias.yaml               perfil de facultad (§4.1)
│   └── general.yaml                   agente sin catálogo
└── backend/
    ├── pyproject.toml
    ├── worker.py                      punto de entrada del proceso worker
    ├── app/
    │   ├── config.py                  Ajustes desde el entorno
    │   ├── db/
    │   │   ├── conexion.py            conectar()
    │   │   ├── migrar.py              aplicar_migraciones()
    │   │   └── migraciones/
    │   │       ├── 000_catalogo.sql   copia de kb/schema.sql
    │   │       └── 001_nucleo.sql     asignatura, trabajo, mensaje, llamada_llm, recurso
    │   ├── silabo/
    │   │   ├── modelo.py              SilaboUTI (contrato con P2)
    │   │   └── contexto.py            ContextoClase y contexto_clase()
    │   ├── cola/trabajos.py           cola con leases y carriles
    │   ├── llm/
    │   │   ├── cliente.py             ClienteLLM, ClienteVLLM, ClienteSimulado
    │   │   ├── json.py                pedir_json(), ultimo_json()
    │   │   └── prompts.py             Sello, construir_prompt() (A3, §5.3)
    │   ├── herramientas/esquemas.py   ItemCuestionario, FichaClase y esquemas JSON
    │   └── agentes/
    │       ├── mensajes.py            Encargo … Cierre + guardar/leer
    │       ├── facultades.py          PerfilFacultad, cargar_perfiles(), enrutar()
    │       ├── planificador.py        tabla de especificaciones y lotes
    │       ├── verificador.py         reglas §10.1 + A7
    │       ├── revisor.py             revisión a ciegas + integridad
    │       ├── evidencia.py           PaqueteEvidencia
    │       ├── coordinador.py         ciclo §3.3
    │       ├── orquestador.py         crear_trabajos(), procesar_uno()
    │       └── workers/
    │           ├── base.py            Worker (protocolo)
    │           ├── cuestionario.py
    │           └── ficha_clase.py
    └── tests/
        ├── conftest.py                esquema PostgreSQL temporal por sesión de pruebas
        ├── fixtures/silabo_datos.json SilaboUTI anonimizado (Análisis de Datos)
        └── test_*.py                  una por módulo
```

---

### Task 1: Repositorio, entorno y configuración

> **Ejecución:** Ola 0 · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet) + código (sonnet) · Puerta del usuario: aprobar `git init -b main` y el remoto (sin push) · Desbloquea: T2, T3, T6

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/tests/conftest.py`, `backend/tests/test_config.py`
- Modify: `.gitignore`, `.env.example`

**Interfaces:**
- Produces: `class Ajustes(BaseSettings)` con `database_url: str`, `llm_base_url: str`, `llm_model: str` (las tres obligatorias, sin valor por defecto), `llm_api_key: str = "no-se-necesita"`, `llm_max_concurrencia: int = 4`, `llm_timeout_s: float = 120`, `llm_timeout_revisor_s: float = 240`, `lease_s: int = 360`, `agentes_dir: Path = Path("agentes")`. Lee `.env` de la raíz del proyecto. `def ajustes() -> Ajustes` con `lru_cache`.
- Produces (conftest): fixture `conn` (psycopg `Connection`, autocommit, `search_path` en un esquema `prueba_<hex>` con las migraciones aplicadas; el esquema se borra al terminar) y fixture `nueva_conexion() -> Connection` sobre el mismo esquema, para las pruebas de concurrencia. La fixture `conn` depende de la Tarea 2: hasta entonces solo existe `test_config.py`.

- [ ] **Step 1: Crear el repositorio propio del proyecto.** En `C:\Users\Chris\Desktop\CIA\Agente-GeneradorRecursos` ejecutar `git init -b main` y `git remote add origin https://github.com/CZurita14/Agente-GenRecursos.git`. **No hacer push sin permiso del usuario.** Añadir al `.gitignore`: `rea/`, `.pytest_cache/`, `pruebas/__pycache__/`.
- [ ] **Step 2: `pyproject.toml`.** Proyecto `genrecursos-backend`, `requires-python = ">=3.12"`, las dependencias del Tech Stack y `[tool.pytest.ini_options] testpaths = ["tests"]`, `markers = ["servidor: requiere el servidor de IA real"]`. Instalar con `.venv/Scripts/python -m pip install -e backend[dev]`.
- [ ] **Step 3: Escribir la prueba que falla.**

```python
def test_url_y_modelo_son_obligatorios(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("LLM_MODEL", "m")
    with pytest.raises(ValidationError):
        Ajustes(_env_file=None)

def test_valores_por_defecto(monkeypatch):
    for k, v in {"DATABASE_URL": "postgresql://x", "LLM_BASE_URL": "http://h/v1", "LLM_MODEL": "m"}.items():
        monkeypatch.setenv(k, v)
    a = Ajustes(_env_file=None)
    assert (a.llm_max_concurrencia, a.llm_timeout_s, a.llm_timeout_revisor_s, a.lease_s) == (4, 120, 240, 360)
    assert a.lease_s > a.llm_timeout_revisor_s
```

- [ ] **Step 4:** `cd backend; ../.venv/Scripts/python -m pytest tests/test_config.py -v` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 5:** Implementar `config.py`. Añadir a `.env.example`: `DATABASE_URL=postgresql://genrecursos:cambiar@127.0.0.1:15432/genrecursos`, `LLM_BASE_URL=http://172.16.8.69:8000/v1`, `LLM_MODEL=Qwen/Qwen3-8B-AWQ`, `LLM_MAX_CONCURRENCIA=4`, `AGENTES_DIR=agentes`.
- [ ] **Step 6:** La prueba → PASS.
- [ ] **Step 7: Commit:** `git add .gitignore .env.example backend docs kb pruebas/*.py docker-compose.yml` → `git commit -m "chore: repositorio del proyecto y configuración del backend"`. Antes de confirmar, comprobar con `git status` que no se incluyan `Silabos/`, `.env` ni `rea/`.

---

### Task 2: Migraciones y esquema del núcleo

> **Ejecución:** Ola 1 (en paralelo con T3 y T6, worktree propio) · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet) + código (sonnet) · Puerta del usuario: Docker Desktop encendido y `genrecursos-db` sano · Desbloquea: T4

**Files:**
- Create: `backend/app/db/conexion.py`, `backend/app/db/migrar.py`, `backend/app/db/migraciones/000_catalogo.sql` (copia literal de `kb/schema.sql`), `backend/app/db/migraciones/001_nucleo.sql`, `backend/tests/test_migraciones.py`

**Interfaces:**
- Produces: `conectar(url: str | None = None) -> psycopg.Connection` (por defecto usa `ajustes().database_url`, con `row_factory=dict_row`); `aplicar_migraciones(conn) -> list[str]` (aplica en orden los `.sql` que falten, los anota en la tabla `migracion(nombre text primary key, aplicada timestamptz)` y devuelve los nombres aplicados).
- Produces (tablas de `001_nucleo.sql`):
  - `asignatura(id uuid pk default gen_random_uuid(), dueno text not null, codigo_pf text not null, version_silabo text not null, agente text not null, silabo jsonb not null, creado timestamptz default now(), unique(dueno, codigo_pf))`
  - `trabajo(id uuid pk default gen_random_uuid(), asignatura_id uuid not null references asignatura, agente text not null, ambito_tipo text not null check (ambito_tipo in ('clase','momento','asignatura')), ambito_id text not null, herramienta text not null, parametros jsonb not null default '{}', estado text not null default 'en_cola' check (estado in (los 8 estados)), lotes_total int default 0, lotes_hechos int default 0, rondas_revision int default 0, intentos int default 0, worker_id text, lease_hasta timestamptz, disponible_desde timestamptz not null default now(), tokens_entrada int default 0, tokens_salida int default 0, error text, creado timestamptz default now(), actualizado timestamptz default now())`
  - `create unique index trabajo_carril on trabajo(asignatura_id) where estado in ('generando','verificando','revisando')`. Este índice impone el carril A6 aunque dos workers tomen trabajos a la vez.
  - `mensaje(id bigserial pk, trabajo_id uuid not null references trabajo, asignatura_id uuid not null, tipo text not null, cuerpo jsonb not null, creado timestamptz default now())`
  - `llamada_llm(id bigserial pk, trabajo_id uuid, asignatura_id uuid, rol text not null, tokens_entrada int not null, tokens_salida int not null, segundos real not null, ok boolean not null, creado timestamptz default now())`
  - `recurso(id uuid pk default gen_random_uuid(), trabajo_id uuid not null unique references trabajo, asignatura_id uuid not null, ambito_id text not null, herramienta text not null, version_silabo text not null, version_esquema int not null default 1, contenido jsonb not null, evidencia jsonb not null, estado text not null check (estado in ('listo','requiere_revision')), creado timestamptz default now())`

- [ ] **Step 1: Escribir las pruebas que fallan** (`test_migraciones.py`):
  - `test_crea_tablas`: tras la fixture `conn`, `information_schema.tables` del esquema contiene `{facultad, carrera, asignatura, trabajo, mensaje, llamada_llm, recurso, migracion}`.
  - `test_idempotente`: una segunda llamada a `aplicar_migraciones(conn)` devuelve `[]`.
- [ ] **Step 2:** Encender Docker Desktop y ejecutar `docker compose up -d db`. Correr `pytest tests/test_migraciones.py -v` → FAIL.
- [ ] **Step 3:** Implementar `conexion.py`, `migrar.py` y los dos `.sql`. Completar la fixture `conn` del conftest: `CREATE SCHEMA prueba_<uuid4().hex[:8]>`, `SET search_path`, `aplicar_migraciones`, y `DROP SCHEMA … CASCADE` al final.
- [ ] **Step 4:** Las pruebas → PASS.
- [ ] **Step 5: Commit** `feat(db): esquema del núcleo con cola y carril por asignatura`.

---

### Task 3: Contrato `SilaboUTI` y contexto de una clase

> **Ejecución:** Ola 1 (en paralelo con T2 y T6, worktree propio) · Antes: **Explorador** `Explore` **haiku** extrae de `pruebas/prueba_calidad*.py` los textos de `CLASES` (sin datos personales) y se los entrega al implementador · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; verifica campo a campo contra `mapeo-silabo.md` §3) + código (sonnet) · Desbloquea: T5, y el P2 (lector), que puede arrancar en paralelo con este contrato

**Files:**
- Create: `backend/app/silabo/modelo.py`, `backend/app/silabo/contexto.py`, `backend/tests/fixtures/silabo_datos.json`, `backend/tests/test_silabo.py`

**Interfaces:**
- Produces: modelos Pydantic **inmutables** con exactamente los campos de `mapeo-silabo.md` §3: `SilaboUTI`, `Periodo`, `ProyectoFormativo`, `ResultadoAprendizaje(id, texto, evidencia)`, `Problema(descripcion, reto, producto_final)`, `Momento`, `FilaRubrica(indicador, niveles: dict[str, str])`, `Sesion(id, numero, fecha: date, semana_periodo, docente, practico, autonomo, contenidos: list[str], entregables: list[str])`.
  - **No incluye** el perfil del docente ni las firmas.
  - `competencia_pf` y `competencia_perfil` aceptan cadena vacía.
  - `model_config = ConfigDict(frozen=True, extra="forbid")`: un campo de más, como `correo`, hace fallar la validación.
- Produces: `class ContextoClase(BaseModel, frozen=True)` con `codigo_pf, version_silabo, asignatura, carrera, nivel: int, clase_id, fecha: date, momento_titulo, contenidos: list[str], actividades: list[str], ra: list[ResultadoAprendizaje], rubrica: list[FilaRubrica], competencia_perfil, problema: Problema, politica_ia, entregables_momento: list[str]` y `def contexto_clase(silabo: SilaboUTI, clase_id: str) -> ContextoClase`. Lanza `KeyError` si la clase no existe.
  - `actividades` incluye los textos de docente, asincrónica, práctico y autónomo que no estén vacíos, porque distinguen dos clases con el mismo contenido (§9.3).

- [ ] **Step 1: Crear la fixture.** `silabo_datos.json` lleva el sílabo de Análisis de Datos con los momentos M2 y M3 completos. Los textos se copian de `CLASES` en `pruebas/prueba_calidad.py` y de la tabla §4.1 del mapeo, incluido `$H_0/H_1$` tal cual. Debe incluir M2-S1 y M2-S2, que comparten contenido y tienen actividades distintas. `competencia_pf` va vacía. No lleva ningún dato personal.
- [ ] **Step 2: Escribir las pruebas que fallan:**

```python
def test_fixture_valida(silabo): assert silabo.proyecto_formativo.codigo == "B26-SOFT-3-56146-1727"
def test_rechaza_campos_personales(datos):
    datos["docente"] = {"correo": "x@uti.edu.ec"}
    with pytest.raises(ValidationError): SilaboUTI.model_validate(datos)
def test_contexto_m2_s1(silabo):
    c = contexto_clase(silabo, "M2-S1")
    assert [r.id for r in c.ra] == ["RA2"] and c.nivel == 3
def test_clases_con_mismo_contenido_difieren_en_actividades(silabo):
    a, b = contexto_clase(silabo, "M2-S1"), contexto_clase(silabo, "M2-S2")
    assert a.actividades != b.actividades
def test_latex_se_conserva(silabo):
    assert "$H_0" in " ".join(contexto_clase(silabo, "M3-S3").actividades + contexto_clase(silabo, "M3-S3").contenidos)
def test_clase_inexistente(silabo):
    with pytest.raises(KeyError): contexto_clase(silabo, "M9-S9")
```

- [ ] **Step 3:** → FAIL. **Step 4:** Implementar. **Step 5:** → PASS.
- [ ] **Step 6: Commit** `feat(silabo): contrato SilaboUTI y contexto por clase`.

---

### Task 4: Cola con leases y carriles

> **Ejecución:** Ola 2 · Implementador `general-purpose` **opus** · Revisores: especificación (sonnet) + código (**opus**; foco en carreras entre workers, en el índice `trabajo_carril` y en el paréntesis del `OR`) · Desbloquea: T5

**Files:**
- Create: `backend/app/cola/trabajos.py`, `backend/tests/test_cola.py`

**Interfaces:**
- Consumes: tabla `trabajo` (Tarea 2).
- Produces:
  - `@dataclass(frozen=True) class Ambito: tipo: Literal["clase","momento","asignatura"]; id: str`
  - `@dataclass(frozen=True) class Trabajo` con los campos de la tabla.
  - `encolar(conn, *, asignatura_id: UUID, agente: str, ambito: Ambito, herramienta: str, parametros: dict) -> UUID`
  - `tomar_siguiente(conn, worker_id: str, lease_s: int) -> Trabajo | None`
  - `renovar_lease(conn, trabajo_id: UUID, worker_id: str, lease_s: int) -> bool`: devuelve `False` si el trabajo ya no es de ese worker.
  - `registrar_avance(conn, trabajo_id: UUID, *, estado: str | None = None, lotes_total: int | None = None, lotes_hechos: int | None = None, rondas_revision: int | None = None, tokens: tuple[int, int] = (0, 0)) -> None`: suma los tokens.
  - `terminar(conn, trabajo_id: UUID, estado: Literal["listo","requiere_revision","error"], error: str | None = None) -> None`: borra el lease.
  - `poner_en_espera(conn, trabajo_id: UUID) -> datetime`: suma 1 a `intentos`, fija `disponible_desde = now() + min(30·2^(intentos−1), 600) s` y la devuelve.
  - `listar(conn, asignatura_id: UUID) -> list[Trabajo]`

`tomar_siguiente` candidatos, en orden de `creado`:
- trabajos en `en_cola` o `en_espera` con `disponible_desde <= now()`;
- trabajos en `generando`, `verificando` o `revisando` con `lease_hasta < now()` (worker caído).

Se excluyen las asignaturas que ya tienen un trabajo activo con lease vigente. Se usa `FOR UPDATE SKIP LOCKED LIMIT 1` y se pasa a `generando` con el nuevo lease. Si el `UPDATE` choca con `trabajo_carril` (`UniqueViolation`), se deshace y se devuelve `None`. Atención: las condiciones con `OR` van entre paréntesis antes del `AND NOT EXISTS`.

- [ ] **Step 1: Escribir las pruebas que fallan** (con un helper `asignatura(conn)` que inserta una asignatura mínima):
  - `test_fifo`: encolar A y luego B en asignaturas distintas → `tomar_siguiente` devuelve A y luego B; una tercera llamada devuelve `None`.
  - `test_skip_locked`: dos conexiones (`nueva_conexion`) con dos trabajos de asignaturas distintas → cada conexión obtiene un trabajo diferente.
  - `test_carril_por_asignatura` (Review Focus 4): dos trabajos de la misma asignatura → el primer `tomar_siguiente` da el 1.º y el segundo da `None`. Tras `terminar(…, "listo")`, el siguiente da el 2.º.
  - `test_lease_vencido_se_retoma`: tomar con `lease_s=1`, esperar 1,2 s → otro `worker_id` lo toma y `renovar_lease` del primero devuelve `False`.
  - `test_en_espera_con_backoff`: `poner_en_espera` dos veces → `intentos == 2` y `disponible_desde ≈ now()+60 s`. Mientras tanto `tomar_siguiente` da `None`.
  - `test_tokens_se_acumulan`: dos `registrar_avance(tokens=(100, 50))` → `(200, 100)`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat(cola): trabajos con lease, carril por asignatura y espera creciente`.

---

### Task 5: Mensajes tipados entre agentes

> **Ejecución:** Ola 3 · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; los 6 mensajes de la tabla §3.7, sin faltantes ni sobrantes) + código (sonnet) · Desbloquea: T7, T8, T9

**Files:**
- Create: `backend/app/agentes/mensajes.py`, `backend/tests/test_mensajes.py`

**Interfaces:**
- Consumes: `Ambito` (Tarea 4), `ContextoClase` (Tarea 3), `EstiloFacultad` (Tarea 8). Para evitar el ciclo, `EstiloFacultad` se define en `mensajes.py` y `facultades.py` la importa.
- Produces (todas con `ConfigDict(frozen=True)` y heredando de `Mensaje(trabajo_id: UUID, asignatura_id: UUID)`), según la tabla de §3.7:
  - `EstiloFacultad(tipos_de_caso: list[str], software_habitual: list[str], vocabulario: str = "")`
  - `PlanItem(item_id: str, nivel: Literal["receptivo","resolutivo","reflexivo","critico"], foco: str)`
  - `Encargo(codigo_pf, version_silabo, carrera, nivel: int, ambito: Ambito, herramienta: str, perfil_dificultad: str, instrucciones: str = "")`
  - `TareaLote(lote: int, ronda: int, contexto: ContextoClase, estilo: EstiloFacultad, plan: list[PlanItem], ya_generado: list[str], resultados_calculados: list[str] = [], devoluciones: list["Devolucion"] = [])`
  - `EntregaLote(lote: int, ronda: int, contenido: list[dict[str, Any]], tokens: tuple[int, int])`
  - `Devolucion(item_id: str, motivo: str, ronda: int)`
  - `ResultadoItem(item_id: str, fallos_verificacion: list[str], revisor: Literal["ok","devuelto","sin_veredicto","no_aplica"], motivo: str = "")` y `Veredicto(resultados: list[ResultadoItem])`
  - `Cierre(recurso_id: UUID, estado: Literal["listo","requiere_revision"], tokens: tuple[int, int])`
  - `guardar(conn, m: Mensaje) -> None` (inserta `tipo=type(m).__name__` y `cuerpo=m.model_dump(mode="json")`) y `leer(conn, trabajo_id: UUID, tipo: type[M] | None = None) -> list[Mensaje]` (en orden de `id`, reconstruido con el tipo correcto).

- [ ] **Step 1: Escribir las pruebas que fallan:** `test_inmutable` (asignar un campo lanza `ValidationError`); `test_ida_y_vuelta` (guardar `Encargo`, `TareaLote` y `Cierre` → `leer` devuelve objetos iguales y en orden); `test_filtrar_por_tipo` (`leer(conn, t, Devolucion)` devuelve solo devoluciones).
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): mensajes tipados e inmutables con traza en PostgreSQL`.

---

### Task 6: Cliente de IA

> **Ejecución:** Ola 1 (en paralelo con T2 y T3, worktree propio; no necesita la base de datos) · Antes: **Explorador** `Explore` **haiku** entrega `llamar` y `ultimo_json` de `pruebas/prueba_calidad_v2.py` · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; valores 1.05, 8192, 300, 120 s, 1 reintento de red, 2 de JSON) + código (sonnet) · Desbloquea: T7, T10, T12

**Files:**
- Create: `backend/app/llm/cliente.py`, `backend/app/llm/json.py`, `backend/tests/test_llm_cliente.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Respuesta: texto: str; razonamiento: str; tokens_entrada: int; tokens_salida: int; segundos: float`.
    - `texto` nunca contiene el bloque `<think>…</think>`.
    - `razonamiento` toma el campo `reasoning`/`reasoning_content` si el servidor lo llena; si no, el contenido de `<think>`.
    - El razonamiento se guarda en el paquete de evidencia solo si es útil para auditar al revisor; nunca se muestra al estudiante.
  - `class ServidorNoDisponible(Exception)`, `class JsonInvalido(Exception)`, `class ContextoExcedido(Exception)` (los usan `prompts.py` y el orquestador)
  - `class ClienteLLM(Protocol)`:
    - `contar_tokens(mensajes: list[dict]) -> int`
    - `completar(mensajes: list[dict], *, rol: str, esquema: dict | None, temperatura: float, max_tokens: int, pensar: bool, trabajo_id: UUID | None, asignatura_id: UUID | None, timeout_s: float | None = None) -> Respuesta`. Si `timeout_s` es `None`, usa el del constructor. El revisor pasa `ajustes().llm_timeout_revisor_s`.
  - `class ClienteVLLM(ClienteLLM)`: `__init__(self, base_url: str, modelo: str, timeout_s: float, max_concurrencia: int, registrar: Callable[[dict], None], api_key: str = "no-se-necesita", transporte: httpx.BaseTransport | None = None)`.
    - Las completions usan el SDK `openai.OpenAI(base_url=…, api_key=…, timeout=timeout_s, max_retries=0, http_client=httpx.Client(transport=transporte))`. `max_retries=0` porque la política de reintentos es la nuestra, no la del SDK.
    - Los campos que no son de OpenAI van en `extra_body`: `chat_template_kwargs` y `repetition_penalty`.
    - Sin `stream`: en la Fase 1 ninguna salida se muestra token a token.
    - `contar_tokens` hace `POST {base_url sin "/v1"}/tokenize` con `{"model", "messages"}` y lee `count`.
    - `completar`:
      - pone `max_tokens = min(max_tokens, 8192 − entrada − 300)` (H4); si ese valor queda < 256, lanza `ContextoExcedido`;
      - envía `repetition_penalty: 1.05` y `response_format` solo cuando hay esquema;
      - envía `chat_template_kwargs.enable_thinking = pensar`;
      - aplica un `threading.BoundedSemaphore(max_concurrencia)`;
      - ante `httpx.TransportError` o una respuesta 5xx hace **un** reintento y luego lanza `ServidorNoDisponible`;
      - llama a `registrar({...})` con los campos de `llamada_llm`, haya éxito o no (A8).
  - `class ClienteSimulado(ClienteLLM)`: `__init__(self, respuestas: dict[str, list[str] | Callable[[list[dict]], str]])`, indexadas por `rol`. Cuenta los tokens como `len(texto) // 4`. Guarda `self.llamadas: list[dict]` con los mensajes, el rol y los parámetros, para las pruebas. Una lista vacía para un rol lanza `AssertionError`.
  - `json.py`:
    - `pedir_json(cliente, mensajes, modelo: type[T], esquema: dict, **kw) -> tuple[T, Respuesta]`: valida con Pydantic; ante JSON inválido, `finish_reason=length` o `ValidationError`, reintenta hasta 2 veces y después lanza `JsonInvalido`.
    - `ultimo_json(texto: str) -> dict`: se porta de `pruebas/prueba_calidad_v2.py:101`.

- [ ] **Step 1: Escribir las pruebas que fallan** (con `httpx.MockTransport`):
  - `test_payload_con_esquema`: el cuerpo enviado tiene `repetition_penalty == 1.05`, `response_format.type == "json_schema"` y `chat_template_kwargs == {"enable_thinking": False}`.
  - `test_max_tokens_respeta_contexto`: con `/tokenize` devolviendo 5 000 y `max_tokens=6500` pedidos → se envían 2 892 (8192 − 5000 − 300).
  - `test_un_reintento_y_servidor_no_disponible`: dos `ConnectError` seguidos → `ServidorNoDisponible`. El transporte se llamó 2 veces y `registrar` recibió `ok=False`.
  - `test_pedir_json_reintenta_dos_veces` (Review Focus 2): un `ClienteSimulado` que devuelve `"{" + " " * 50` tres veces → `JsonInvalido` tras 3 llamadas. Si devuelve inválido y luego válido → ok con 2 llamadas.
  - `test_ultimo_json_ignora_think`: `"<think>{\"a\":1}</think> razono… {\"b\": 2}"` → `{"b": 2}`.
  - `test_separa_razonamiento_en_content` (forma real del servidor al 2026-10-26): `content = "<think>\nOkay, 17*3…\n</think>\n\n51"` y `reasoning = null` → `texto == "51"` y `razonamiento` empieza con `"Okay"`.
  - `test_separa_razonamiento_en_campo` (por si TI activa el separador): `content = "51"` y `reasoning = "Okay…"` → el mismo resultado.
  - `test_extra_body`: el cuerpo enviado por el SDK contiene `chat_template_kwargs` y `repetition_penalty` en el primer nivel del JSON, como los espera vLLM.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(llm): cliente vLLM con presupuesto, reintentos y registro de uso`.

---

### Task 7: Constructor único de prompts

> **Ejecución:** Ola 4 (en paralelo con T8 y T9, worktree propio) · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; presupuesto §5.3 y orden de recorte H3) + código (**opus**; aislamiento A3 y ausencia de datos personales, criterio 5) · Desbloquea: T10, T12

**Files:**
- Create: `backend/app/llm/prompts.py`, `backend/tests/test_prompts.py`

**Interfaces:**
- Consumes: `ContextoClase` (Tarea 3), `ClienteLLM.contar_tokens` (Tarea 6).
- Produces:
  - `PRESUPUESTO = {"instrucciones": 900, "clase": 900, "rubrica": 600, "perfil": 500, "ya_generado": 400}`, `CONTEXTO_MAX = 8192`, `MARGEN = 300`
  - Importa `ContextoExcedido` de `llm/cliente.py` (Tarea 6).
  - `@dataclass(frozen=True) class Sello: codigo_pf: str; clase_id: str; fecha: date`, con `def linea(self) -> str` que devuelve `f"[Asignatura {codigo_pf} · Clase {clase_id} · {fecha:%d/%m/%Y}]"`.
  - `construir_prompt(*, sello: Sello, instrucciones: str, contexto: ContextoClase, estilo: EstiloFacultad, ya_generado: list[str], pedido: str, salida_max: int, contar: Callable[[list[dict]], int]) -> list[dict]`
    - Devuelve `[system, user]`. El `system` empieza con `sello.linea()` y lleva las instrucciones.
    - El `user` lleva, en este orden: clase (contenidos, actividades, RA), rúbrica, perfil (competencia, problema del territorio, estilo de la facultad), ya generados y pedido.
    - Si `contar(mensajes) + salida_max + MARGEN > CONTEXTO_MAX`, recorta en este orden: ya generados (los más antiguos primero), después la rúbrica (indicadores del final primero). Si aun así no cabe, lanza `ContextoExcedido("la clase M3-S4 no cabe en el contexto del modelo")`.
  - Es el **único** lugar del código que arma mensajes para el modelo (A3). Workers y revisor lo usan.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_sello_primero`: `msgs[0]["content"].startswith("[Asignatura B26-SOFT-3-56146-1727 · Clase M3-S4 · 29/10/2026]")`.
  - `test_recorta_ya_generado_antes_que_rubrica` (Review Focus 3): con un `contar` que devuelve `len(texto)//4`, 200 enunciados ya generados y `salida_max=3500` → el resultado cabe; la rúbrica sigue completa y quedan menos de 200 enunciados.
  - `test_nunca_recorta_la_clase`: con contenidos de 40 000 caracteres → `ContextoExcedido`.
  - `test_sin_datos_personales` (criterio 5): sobre todos los prompts de la fixture, ningún texto coincide con `r"[\w.]+@[\w.]+|\+?\d[\d\s-]{8,}|ORCID|\d{4}-\d{4}-\d{4}-\d{3}[\dX]"`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(llm): constructor único de prompts con sello y presupuesto`.

---

### Task 8: Perfiles de facultad y enrutamiento

> **Ejecución:** Ola 4 (en paralelo con T7 y T9, worktree propio) · Implementador `general-purpose` **haiku** · Revisores: especificación (sonnet; ejemplo de §4.1 literal en `ingenierias.yaml`) + código (sonnet) · Desbloquea: T13, T14

**Files:**
- Create: `agentes/ingenierias.yaml`, `agentes/general.yaml`, `backend/app/agentes/facultades.py`, `backend/tests/test_facultades.py`

**Interfaces:**
- Consumes: `EstiloFacultad` (Tarea 5); `kb/catalogo.yaml`.
- Produces:
  - `class PerfilFacultad(BaseModel, frozen=True): id: str; facultad: str | None; estilo: EstiloFacultad; carreras: dict[str, EstiloFacultad] = {}; herramientas_recomendadas: dict[str, list[str]]`
    - `carreras` usa como clave el nombre normalizado de la carrera de `kb/catalogo.yaml`. Cada entrada solo trae lo que cambia frente a la facultad (R4).
  - `estilo_para(perfil: PerfilFacultad, carrera: str) -> EstiloFacultad`:
    - parte del estilo de la facultad;
    - las listas no vacías de la carrera **reemplazan** a las de la facultad;
    - `vocabulario` de la carrera, si existe, reemplaza al de la facultad.
    - Una carrera sin ajustes, o desconocida, recibe el estilo de la facultad.
    - El coordinador (T13) usa siempre `estilo_para` para armar la `TareaLote`; nunca `perfil.estilo` directo.
  - `cargar_perfiles(directorio: Path) -> dict[str, PerfilFacultad]`: exige que exista `general`.
  - `cargar_catalogo(ruta: Path) -> dict[str, str]`: mapea cada nombre normalizado (el nombre y sus `nombres_alt`) a su sigla.
  - `normalizar(texto) -> str`: mayúsculas, sin tildes, espacios colapsados.
  - `enrutar(nombre_facultad: str, catalogo: dict[str, str], perfiles: dict[str, PerfilFacultad]) -> str`: devuelve el `id` del perfil cuya `facultad` es la sigla encontrada. Si no la encuentra, devuelve `"general"`.
  - Contenido de `ingenierias.yaml`: el ejemplo de §4.1, más una sección `carreras:` con `software` (`software_habitual: [JASP, Numiqo, Git, Visual Studio Code]`, tomado de los sílabos de Software) y `tecnologias de la informacion` (sus casos de ciberseguridad y selección de soluciones TI, del sílabo de TIC). Las demás carreras quedan sin ajustes hasta su alta. Contenido de `general.yaml`: `id: general`, `facultad: null`, estilo con listas vacías, recomendadas `clase: [ficha_clase, cuestionario]`.

- [ ] **Step 1: Escribir las pruebas que fallan** (criterio 3): `enrutar("FACULTAD DE INGENIERIAS")`, `enrutar("Facultad de Ingenierías")` y `enrutar("facultad  de ingenierías")` → `"ingenierias"`; `enrutar("FACULTAD DE ASTRONOMÍA")` → `"general"`; `cargar_perfiles` sobre una carpeta sin `general.yaml` → `ValueError`. Además:
  - `test_estilo_por_carrera`: `estilo_para(fing, "SOFTWARE").software_habitual` contiene `"JASP"`.
  - `test_carrera_sin_ajustes_hereda`: `estilo_para(fing, "CIVIL") == fing.estilo`.
  - `test_carrera_desconocida`: `estilo_para(fing, "ASTRONAUTICA") == fing.estilo`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): perfiles de facultad y enrutamiento con agente general`.

---

### Task 9: Planificador (tabla de especificaciones y lotes)

> **Ejecución:** Ola 4 (en paralelo con T7 y T8, worktree propio) · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; porcentajes exactos de §6.2 y método del mayor resto) + código (sonnet) · Desbloquea: T10

**Files:**
- Create: `backend/app/agentes/planificador.py`, `backend/tests/test_planificador.py`

**Interfaces:**
- Consumes: `PlanItem` (Tarea 5), `ContextoClase` (Tarea 3).
- Produces:
  - `PERFILES = {"fundamentacion": {"receptivo": .20, "resolutivo": .40, "reflexivo": .30, "critico": .10}, "profesional": {…: .10, .30, .35, .25}, "avanzado": {…: 0, .20, .40, .40}}`. "Crítico/Cocreativo" se agrupa en `critico`.
  - `perfil_por_nivel(nivel: int, posgrado: bool = False) -> str`: niveles 1–3 → fundamentación, 4–7 → profesional, 8 o más o posgrado → avanzado.
  - `tabla_especificaciones(n: int, perfil: str) -> dict[str, int]`: método del mayor resto. La suma siempre es `n`.
  - `planificar(contexto: ContextoClase, n: int, perfil: str, tam_lote: int = 4) -> list[list[PlanItem]]`:
    - ids `i1…in`, ordenados de menor a mayor nivel;
    - cada `foco` rota entre las `actividades` y los `contenidos` de la clase (§9.3);
    - lotes de `tam_lote`.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_tabla_12_fundamentacion` (criterio 6): `tabla_especificaciones(12, "fundamentacion") == {"receptivo": 2, "resolutivo": 5, "reflexivo": 4, "critico": 1}`.
  - `test_suma_siempre_n`: con `n` de 1 a 30 y los 3 perfiles, la suma es `n`.
  - `test_lotes_de_4`: `planificar(ctx, 12, …)` → 3 lotes de 4 e ids únicos `i1…i12`.
  - `test_focos_distintos_m2s1_m2s2` (criterio 9): el conjunto de focos de M2-S1 es distinto del de M2-S2.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): planificador con tabla de especificaciones por perfil`.

---

### Task 10: Esquemas de herramientas y workers `cuestionario` y `ficha_clase`

> **Ejecución:** Ola 5 · Antes: **Explorador** `Explore` **haiku** entrega `PLANTILLAS` y `esquema_lote` de `pruebas/prueba_calidad_v3.py` y las conclusiones de `prueba-calidad-silabo.md` · Implementador `general-purpose` **opus** · Revisores: especificación (sonnet; reglas §6.3, lotes de 4, barajado M3) + código (**opus**; workers sin estado A2, calidad pedagógica del prompt) · Desbloquea: T11, T12

**Files:**
- Create: `backend/app/herramientas/esquemas.py`, `backend/app/agentes/workers/base.py`, `backend/app/agentes/workers/cuestionario.py`, `backend/app/agentes/workers/ficha_clase.py`, `backend/tests/test_workers.py`

**Interfaces:**
- Consumes: `TareaLote`, `EntregaLote` (Tarea 5), `construir_prompt`, `Sello` (Tarea 7), `pedir_json` (Tarea 6).
- Produces:
  - `Opcion(texto, justificacion, error_que_representa)`
  - `ItemCuestionario(item_id, nivel, ra, contenido, foco, contexto, pregunta, opciones: list[Opcion], correcta: int, razonamiento: list[str])`
  - `esquema_cuestionario(n: int, ras: list[str], contenidos: list[str]) -> dict`: como `esquema_lote` de `pruebas/prueba_calidad_v3.py:43`, pero `ra` y `contenido` son `enum` con los valores de la clase. Así el esquema obliga a cumplir la regla 3 de §10.1.
  - `FichaConceptual(ideas_clave: list[str] (3–6), relacion_ra: str, errores_frecuentes: list[str])` y `FichaAplicacion(ejemplo: {enunciado, pasos: list[str], resultado}, autocomprobacion: list[str] (3–5))`, con sus esquemas.
  - `class Worker(Protocol): herramienta: str; def generar(self, tarea: TareaLote, cliente: ClienteLLM) -> EntregaLote`. Los workers no tienen atributos de instancia con contenido (A2).
  - `WorkerCuestionario`:
    - el pedido lleva las plantillas por nivel de `pruebas/prueba_calidad_v3.py:35` y las `devoluciones` con su motivo;
    - el código asigna `item_id` según el plan, sin importar lo que devuelva el modelo;
    - **baraja las opciones por código** con `random.Random(f"{trabajo_id}-{item_id}")` y actualiza `correcta` (§5.2, M3).
  - `WorkerFichaClase`: lote 1 → `FichaConceptual`, lote 2 → `FichaAplicacion`.
  - `WORKERS: dict[str, Worker] = {"cuestionario": …, "ficha_clase": …}`

- [ ] **Step 1: Escribir las pruebas que fallan** (con `ClienteSimulado` y la fixture):
  - `test_cuestionario_lote`: un lote de 4 → `EntregaLote` con 4 ítems e `item_id`s iguales a los del plan; el rol registrado es `"worker"` con `temperatura == 0.4` y `pensar is False`.
  - `test_baraja_opciones`: el simulado siempre pone `correcta=0` → en 40 ítems `correcta` toma al menos 3 valores distintos, y `opciones[correcta]` es el texto que originalmente iba en la posición 0.
  - `test_devolucion_llega_al_prompt`: una `TareaLote` con `Devolucion(motivo="dos respuestas defendibles")` → ese motivo aparece en el último mensaje enviado.
  - `test_sin_estado`: dos tareas de asignaturas distintas con el mismo worker → el prompt de la 2.ª no contiene ningún texto de la 1.ª (A2).
  - `test_ficha_dos_secciones`: lotes 1 y 2 → validan como `FichaConceptual` y `FichaAplicacion`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(workers): cuestionario y ficha de clase con barajado por código`.

---

### Task 11: Verificador determinista

> **Ejecución:** Ola 6 (en paralelo con T12, worktree propio) · Antes: **Explorador** `Explore` **haiku** entrega `verificar` de `pruebas/prueba_calidad_v2.py` · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; reglas 1–7 de §10.1 una por una, umbral 0,8, regla A7) + código (sonnet) · Desbloquea: T13

**Files:**
- Create: `backend/app/agentes/verificador.py`, `backend/tests/test_verificador.py`

**Interfaces:**
- Consumes: `ItemCuestionario` (Tarea 10), `ContextoClase`, `PlanItem`.
- Produces:
  - `PROHIBIDAS = re.compile(r"\b(todas|ninguna) de las anteriores\b|\btodas son correctas\b|\bninguna es correcta\b", re.I)`
  - `UMBRAL_DUPLICADO = 0.8` (§10.1.6)
  - `MIN_PALABRAS_CONTEXTO = 15` (medido en la prueba v2)
  - `verificar_items(items: list[ItemCuestionario], plan: list[PlanItem], contexto: ContextoClase, previos: list[str], asignatura_entrega: UUID, asignatura_trabajo: UUID) -> dict[str, list[str]]`: devuelve los fallos por `item_id`, con el texto de cada fallo en español.
    - Regla 1: el esquema ya validado.
    - Regla 2: 4 opciones sin duplicados.
    - Regla 3: `ra` y `contenido` existen en la clase.
    - Regla 5: contexto de al menos 15 palabras desde resolutivo; 2 o más pasos de razonamiento desde reflexivo.
    - Regla 6: similitud con `difflib` ≥ 0,8 frente a los demás ítems y a `previos`.
    - Regla 7: frases prohibidas.
    - El nivel coincide con el del plan.
    - A7: si `asignatura_entrega != asignatura_trabajo`, todos los ítems fallan con "entrega de otra asignatura".
  - `verificar_distribucion(items, tabla: dict[str, int]) -> list[str]`: regla 4, tolerancia ±1 por nivel.
  - `verificar_ficha(ficha: dict, contexto) -> list[str]`: frases prohibidas y campos no vacíos.

- [ ] **Step 1: Escribir las pruebas que fallan:** una prueba por regla, cada una con un ítem sembrado que viola solo esa regla (`test_regla_2_opciones_duplicadas`, `test_regla_3_ra_ajeno`, `test_regla_5_sin_contexto`, `test_regla_5_un_paso`, `test_regla_6_casi_duplicado_de_previo`, `test_regla_7_todas_las_anteriores`, `test_nivel_distinto_al_plan`, `test_a7_otra_asignatura`, `test_distribucion_fuera_de_tolerancia`). Además, `test_item_correcto_sin_fallos`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): verificador determinista §10.1 con pertenencia A7`.

---

### Task 12: Revisor a ciegas y de integridad

> **Ejecución:** Ola 6 (en paralelo con T11, worktree propio) · Antes: **Explorador** `Explore` **haiku** entrega `revisar` de `pruebas/prueba_calidad_v3.py` · Implementador `general-purpose` **opus** · Revisores: especificación (sonnet; §10.2 y §9.4, grupos de 3, temperatura 0) + código (**opus**; que la clave nunca llegue al prompt y que la integridad académica no se pueda saltar) · Desbloquea: T13

**Files:**
- Create: `backend/app/agentes/revisor.py`, `backend/tests/test_revisor.py`

**Interfaces:**
- Consumes: `construir_prompt` (Tarea 7), `ultimo_json` (Tarea 6), `ItemCuestionario`, `ResultadoItem` (Tarea 5).
- Produces:
  - `revisar_items(items: list[ItemCuestionario], contexto: ContextoClase, cliente, *, trabajo_id, asignatura_id) -> list[ResultadoItem]`
    - Revisa **1 ítem por llamada** (R1). Rol `"revisor"`, `pensar=True`, `temperatura=0`, `esquema=None`, `timeout_s=ajustes().llm_timeout_revisor_s`.
    - El prompt muestra contexto, pregunta y opciones, y **nunca** muestra `correcta`, `justificacion`, `error_que_representa` ni `razonamiento`.
    - Pide un veredicto por opción, como en `pruebas/prueba_calidad_v3.py:63`, y además `resuelve_entregable: bool` frente a `contexto.entregables_momento`.
    - El modelo razona en inglés, pero el prompt exige que el `motivo` del JSON final esté **en español**, porque llega al docente.
    - El JSON se extrae de `Respuesta.texto`, que ya viene sin `<think>`.
    - Los tokens del razonamiento cuentan contra los 8 192: por eso el `max_tokens` es dinámico (H4).
    - `ok` solo si las opciones marcadas como verdaderas son exactamente `[correcta]` y `resuelve_entregable` es falso. En otro caso `devuelto`, con un motivo concreto: "el revisor considera correctas las opciones 1 y 3", "resuelve el entregable PAE 1".
    - Si el JSON es ilegible, reintenta una vez; después `sin_veredicto` con el motivo "revisor sin veredicto" (Review Focus 5).
  - `revisar_ficha(ficha: dict, contexto, cliente, …) -> ResultadoItem`: solo integridad (§10.2, 2.º punto), con `item_id="ficha"`.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_prompt_a_ciegas`: el texto enviado no contiene `"correcta"`, ninguna `justificacion` ni `error_que_representa`.
  - `test_ok_si_coincide`, `test_devuelto_dos_respuestas` (criterio 7, ítem sembrado) y `test_devuelto_resuelve_entregable` (criterio 8).
  - `test_sin_veredicto_tras_reintento`: el simulado devuelve "no sé" dos veces → `revisor == "sin_veredicto"` y 2 llamadas.
  - `test_un_item_por_llamada`: 7 ítems → 7 llamadas, cada una con `timeout_s == 240`.
  - `test_pide_motivo_en_espanol`: el prompt enviado contiene la instrucción de redactar `motivo` en español.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): revisor a ciegas con control de integridad académica`.

---

### Task 13: Coordinador de facultad y paquete de evidencia

> **Ejecución:** Ola 7 · Implementador `general-purpose` **opus** · Revisores: especificación (sonnet; los 8 pasos de §3.3, máximos de 2 reintentos y 2 rondas, campos de §10.3) + código (**opus**; reanudación tras una caída, transacciones, que no se escriba el recurso sin lease) · Desbloquea: T14

**Files:**
- Create: `backend/app/agentes/evidencia.py`, `backend/app/agentes/coordinador.py`, `backend/tests/test_coordinador.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces:
  - `class PaqueteEvidencia(BaseModel)` con los campos de §10.3: `clase_id, momento, ra: list[str], contenidos, agente, perfil_dificultad, tabla_planificada, tabla_real, verificaciones: dict[str, list[str]], veredictos: dict[str, str], devoluciones: int, tokens: tuple[int, int]` y `def resumen(self) -> str`. Ejemplo: `"12 ítems · 12 verificados · 1 corregido por el revisor"`.
  - `class Coordinador`: `__init__(self, perfil: PerfilFacultad, workers: dict[str, Worker], cliente: ClienteLLM)` y `ejecutar(self, conn, trabajo: Trabajo, encargo: Encargo, contexto: ContextoClase, latido: Callable[[], bool]) -> Cierre`. Sigue §3.3:
    1. planifica. El plan es determinista para el mismo contexto, así que al retomar sale igual;
    2. por cada lote **que aún no tenga su `EntregaLote` guardada**, envía la tarea al worker y verifica. Si falla, reintenta el lote con los fallos como `Devolucion` (máximo 2 veces); si sigue fallando, conserva los ítems con sus fallos. La `EntregaLote` se guarda **solo** cuando el lote queda cerrado (aprobado o con los reintentos agotados), junto con `lotes_hechos += 1` en la misma transacción. Así la reanudación sabe exactamente qué lotes saltar;
    3. revisor, con estado `revisando`;
    4. los ítems devueltos vuelven al worker como lote de 1 con su `Devolucion` (máximo 2 rondas); si persisten → `requiere_revision`;
    5. inserta el `recurso` y su evidencia;
    6. guarda cada mensaje con `guardar`, llama a `registrar_avance` en cada transición y a `latido()` antes de cada llamada al modelo. Si `latido()` devuelve `False` (perdió el lease), se detiene sin escribir el recurso.
  - El estado final del recurso es `requiere_revision` si algún ítem quedó devuelto o sin veredicto; si no, `listo`. Los cuestionarios llevan además `evidencia.borrador = True` mientras no se cumpla el criterio de calidad (H8).

- [ ] **Step 1: Escribir las pruebas que fallan** (simulado, con la fixture en la BD):
  - `test_camino_feliz` (criterio 6): cuestionario de 12 → recurso `listo` con 12 ítems. `tabla_real == {"receptivo": 2, "resolutivo": 5, "reflexivo": 4, "critico": 1}`. Los mensajes, en orden, son `Encargo, TareaLote, EntregaLote, … , Veredicto, Cierre`.
  - `test_item_ambiguo_requiere_revision` (criterio 7): el revisor siempre marca dos opciones en `i3` → 2 devoluciones de `i3`, el recurso queda `requiere_revision` y el motivo está en `evidencia.veredictos["i3"]`.
  - `test_reintento_de_lote_por_verificacion`: el primer intento del lote 1 trae "todas las anteriores" → el 2.º intento recibe ese motivo en el prompt y el recurso queda `listo`.
  - `test_retoma_tras_caida` (Review Focus 1): ejecutar con un `latido` que devuelve `False` después del lote 2 → no hay recurso. Al volver a ejecutar el mismo trabajo con otro coordinador, el worker solo recibe la tarea del lote 3 y el recurso tiene 12 ítems con ids únicos.
  - `test_ficha_clase`: recurso con las dos secciones y `veredictos == {"ficha": "ok"}`.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS. **Step 5: Commit** `feat(agentes): coordinador de facultad con devoluciones y paquete de evidencia`.

---

### Task 14: Orquestador y proceso `worker`

> **Ejecución:** Ola 8 · Implementador `general-purpose` **opus** · Revisores: especificación (sonnet; criterios 3, 11 y 14) + código (**opus**; hilos, conexiones por hilo, semáforo compartido H6, prueba de aislamiento) · Desbloquea: T15

**Files:**
- Create: `backend/app/agentes/orquestador.py`, `backend/worker.py`, `backend/tests/test_orquestador.py`

**Interfaces:**
- Consumes: cola (Tarea 4), `enrutar`/`cargar_perfiles` (Tarea 8), `Coordinador` (Tarea 13), `contexto_clase` (Tarea 3).
- Produces:
  - `crear_asignatura(conn, *, dueno: str, silabo: SilaboUTI, catalogo, perfiles) -> UUID`: inserta la asignatura con el agente enrutado. Si ya existe dueño + código, actualiza `silabo` y `version_silabo`.
  - `@dataclass class SolicitudGeneracion: asignatura_id: UUID; ambito: Ambito; herramientas: list[str]; cantidad: int = 12; instrucciones: str = ""`
  - `crear_trabajos(conn, solicitud) -> list[UUID]`: un trabajo por herramienta (§3.3, paso 1). Una herramienta que no esté en `WORKERS` lanza `ValueError`. Por ahora solo se admite el ámbito `clase`; los demás quedan para el P3.
  - `procesar_uno(conn, cliente, perfiles, worker_id: str, lease_s: int) -> bool`: devuelve `False` si no había trabajo. Toma el trabajo, arma el `Encargo` y el contexto, y llama al coordinador con `latido = lambda: renovar_lease(…)`.
    - `ServidorNoDisponible` → `poner_en_espera` (criterio 11).
    - `JsonInvalido` o `ContextoExcedido` → `terminar(…, "error", str(e))`.
    - Cualquier otra excepción → `terminar(…, "error", …)` y log con `trabajo_id`.
  - `worker.py`: `main()` lanza `ajustes().llm_max_concurrencia` hilos. Cada hilo tiene su propia conexión y todos comparten **un** `ClienteVLLM` (H6). El registro de llamadas abre su propia conexión. Cada hilo hace `procesar_uno` en bucle y duerme 2 s cuando no hay trabajo. Se detiene con Ctrl+C.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_enruta_al_crear` (criterio 3): una asignatura de la fixture → `agente == "ingenierias"`. Con la facultad cambiada a "FACULTAD DE ASTRONOMÍA" → `"general"`.
  - `test_un_trabajo_por_herramienta`: `["cuestionario", "ficha_clase"]` → 2 trabajos `en_cola`.
  - `test_servidor_caido_queda_en_espera` (criterio 11): un cliente que lanza `ServidorNoDisponible` → el estado es `en_espera` y `intentos == 1`. Al cambiar al cliente simulado sano y adelantar `disponible_desde`, `procesar_uno` lo termina `listo`.
  - `test_json_invalido_termina_en_error` (Review Focus 2): el estado es `error` y `error` contiene "JSON".
  - `test_aislamiento_dos_asignaturas` (criterio 14):
    - dos asignaturas (Datos y una TIC mínima creada en la prueba) y dos hilos con `procesar_uno` a la vez;
    - el simulado devuelve ítems que copian el sello recibido;
    - en `mensaje`, `recurso` y `llamada_llm` de la asignatura A no aparece el código PF ni ningún contenido de la B, y viceversa.
- [ ] **Step 2:** → FAIL. **Step 3:** Implementar. **Step 4:** → PASS.
- [ ] **Step 5:** Ejecutar todo el conjunto: `pytest -v` → todas las pruebas PASS, salvo las marcadas `servidor`, que se omiten.
- [ ] **Step 6: Commit** `feat: orquestador y proceso worker con hilos y espera ante caídas del servidor`.

---

### Task 15: Prueba de humo con Qwen real

> **Ejecución:** Ola 9 · Puerta del usuario: equipo dentro de la red UTI y autorización para `LLM_REAL=1` (consume GPU compartida de la universidad) · Implementador `general-purpose` **sonnet** · Revisores: especificación (sonnet; criterio 4 y A8 comprobados con datos de `llamada_llm`) + código (sonnet) · El **coordinador** presenta al usuario los tiempos, los tokens y el resumen de evidencia antes de anotarlos en `prueba-calidad-silabo.md`

**Files:**
- Create: `backend/tests/test_humo_servidor.py`

**Interfaces:**
- Consumes: todo. Requiere estar dentro de la red UTI y `LLM_REAL=1`.
- Precondición: `GET {LLM_BASE_URL}/models` responde 200 con `max_model_len == 8192`. Si no responde, la prueba se omite con el mensaje "servidor de IA no alcanzable desde esta red" en vez de fallar.
- Comprobado el 2026-10-26: el servidor es alcanzable desde la máquina de desarrollo, así que la T15 puede correr aquí mismo.

- [ ] **Step 1: Escribir la prueba** `@pytest.mark.servidor` (se omite si `LLM_REAL != "1"`):
  - crear la asignatura de la fixture;
  - `crear_trabajos(["cuestionario"], cantidad=4)` para `M3-S4` y `["ficha_clase"]` para `M2-S1`;
  - ejecutar `procesar_uno` con `ClienteVLLM` hasta vaciar la cola.

  Asserts:
  - los dos recursos existen;
  - en `llamada_llm`, `max(tokens_entrada + tokens_salida) <= 8192` (criterio 4) y todas las filas tienen `asignatura_id` (A8);
  - se imprime `evidencia.resumen()` de cada recurso.
- [ ] **Step 2:** `$env:LLM_REAL="1"; pytest -m servidor -v -s` → PASS.
  - Anotar tiempos y tokens en `docs/prueba-calidad-silabo.md`, en la sección nueva "Humo del núcleo (P1)".
  - Si el revisor con temperatura 0 entra en bucle (H5), anotarlo y proponer el cambio en el spec.
- [ ] **Step 3: Commit** `test: prueba de humo del núcleo contra el servidor de IA de la UTI`.

---

## Cierre: revisión final de la rama

> **Ejecución:** después de la Ola 9 · Revisor final `general-purpose` **opus** con `requesting-code-review` y `verification-before-completion` · Puerta del usuario: decidir si se hace push de `p1/nucleo` y si se abre un PR hacia `main`

- [ ] **Step 1:** El revisor final corre `pytest -v` en `p1/nucleo` → todas las pruebas PASS (las de `servidor` se omiten o pasan si hay red UTI).
- [ ] **Step 2:** Recorre los criterios 3, 4, 5, 6 (parcial), 7, 8, 11 y 14 y los 5 puntos del Review Focus. Para cada uno nombra la prueba que lo demuestra, o lo marca como faltante.
- [ ] **Step 3:** Verifica que ningún archivo de `Silabos/`, `.env` ni `rea/` haya entrado en la historia (`git log --all --stat`).
- [ ] **Step 4:** El coordinador presenta al usuario el informe:
  - criterios cubiertos,
  - hallazgos abiertos,
  - desviaciones del spec que deben pasar a la v1.3 (H1–H6 y lo que salga de la T15).
- [ ] **Step 5:** El coordinador usa `finishing-a-development-branch` **solo** con la decisión del usuario sobre el push o el PR.

## Fuera de este plan (van a P2–P7)

- Lector PDF y menú.
- El resto de los workers, las herramientas sin IA, el módulo de cálculo y el techo del RA.
- API y acceso.
- Chat (`AccionAgente`).
- Exportación y frontend.
- Despliegue.

Los ámbitos `momento` y `asignatura` se habilitan en el P3, cuando existan sus workers.
