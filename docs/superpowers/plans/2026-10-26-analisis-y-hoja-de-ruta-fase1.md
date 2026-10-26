# Análisis de lo pendiente y hoja de ruta de la Fase 1

> **Fecha:** 2026-10-26 · **Base:** [spec v1.2](../../especificacion-generador-recursos-uti-v1.2.md),
> [mapeo-silabo.md](../../mapeo-silabo.md), [catalogo-herramientas.md](../../catalogo-herramientas.md),
> [prueba-calidad-silabo.md](../../prueba-calidad-silabo.md), [arquitectura-agentica-hive.md](../../arquitectura-agentica-hive.md).

## 1. Estado actual

| Área | Estado | Evidencia |
|---|---|---|
| Especificación funcional y arquitectura | ✅ Completa (v1.2) | `docs/` |
| Modelo de datos del sílabo (`SilaboUTI`) | ✅ Diseñado, ❌ sin código | `mapeo-silabo.md` §3 |
| Catálogo de facultades y carreras | ✅ Código y datos | `kb/catalogo.yaml`, `kb/schema.sql`, `kb/sembrar_catalogo.py` |
| Generación + verificación + revisor (prototipo) | ✅ 3 rondas de prueba con Qwen3-8B real | `pruebas/prueba_calidad_v1..v3.py` |
| Infraestructura local | ⚠️ Solo PostgreSQL en `docker-compose.yml` | Docker Desktop apagado al 2026-10-26 |
| Repositorio git del proyecto | ❌ La carpeta no es un repo propio (queda dentro del repo del perfil de usuario) | `git status` |
| `backend/`, `frontend/`, `agentes/`, `infra/` | ❌ No existen | — |

**En resumen:** el diseño está cerrado y el prototipo demostró que el sílabo alcanza como fuente.
**Todavía no hay una sola línea del producto.** Ninguno de los 14 criterios de aceptación de la Fase 1 (§15) se cumple aún.

## 2. Inventario de lo pendiente por subsistema

| Subsistema | Qué falta | Criterios §15 |
|---|---|---|
| **Núcleo multiagente** | Cola con leases y carriles, mensajes tipados, cliente de IA con presupuesto, constructor de prompts, perfiles de facultad, orquestador, coordinador, planificador, workers, verificador, revisor, proceso `worker` | 3, 4, 5, 6, 7, 8, 11, 14 |
| **Lector y menú** | `pdfplumber` sobre la plantilla institucional, casos del §6 del mapeo, exclusión de datos personales, menú por semana y día, detección de cambios entre versiones | 1, 2, 5 |
| **Herramientas** | Los demás workers (práctica, tarjetas, glosario, guía invertida, repaso, simulacro, caso, guías), las herramientas sin IA (hoja de ruta, autoevaluaciones, lista de verificación), módulo de cálculo, techo del RA, mejoras M1–M3 | 6, 9 |
| **API y acceso** | FastAPI, código por correo, sesiones, dominios, compartir, permisos, límites de intentos, CSRF/CORS, registro de accesos | 12, 12b, 12c |
| **Chat de ajustes** | `AccionAgente`, regenerar un ítem, historial por asignatura y usuario (A5) | 10 |
| **Entrega** | Renderizado HTML autónomo (KaTeX incrustado), PDF y DOCX, pie institucional; frontend React (ingreso, mis asignaturas, menú, revisión, chat) | — |
| **Despliegue** | `docker-compose` con web/api/worker/db/proxy, nginx con HTTPS y HSTS, instalación limpia | 13 |

## 3. Bloqueos externos (spec §16) y cómo no detenerse

| # | Bloqueo | Afecta a | Cómo avanzar sin él |
|---|---|---|---|
| 1 | Sílabos de otras facultades | Agentes de Fase 2, validación del lector | Fase 1 = Ingenierías + agente general. Lector probado con los 2 sílabos actuales |
| 2 | Cuenta SMTP institucional | Inicio de sesión real | Envío por consola en desarrollo (`SMTP_MODO=consola`). El código queda listo para conectar SMTP |
| 2b | Servidor y dominio dentro de la red UTI | Despliegue | Compose y nginx probados en local con un certificado autofirmado |
| 3b | Plantilla del área académica | Formato final (M4) | Esquemas versionados (`version_esquema`). Cambiar el formato no toca la cola ni los mensajes |
| 4 | Concurrencia que admite el servidor de IA | Ajuste de `LLM_MAX_CONCURRENCIA` | Valor por defecto 4. Se mide con la prueba de humo del P1 |
| 5 | Significado del código PF | Nada bloqueante | Se trata como texto opaco |

## 4. Hallazgos del análisis (para corregir en el spec)

| # | Hallazgo | Recomendación |
|---|---|---|
| H1 | §14 dice "SQLite en desarrollo", pero §3.6 exige `FOR UPDATE SKIP LOCKED`, que SQLite no tiene | **PostgreSQL en todos los entornos.** El contenedor `genrecursos-db` ya existe |
| H2 | §11 identifica el `Trabajo` por el código PF, pero la asignatura es única por **dueño + código** (§2.1) | Clave sustituta `asignatura_id` (UUID). El código PF y la versión viajan como datos (A1) |
| H3 | §5.3 recorta primero "fragmentos de conocimiento", pero la base de conocimiento se retiró | Orden de recorte: lista de ya generados → rúbrica → nunca la clase |
| H4 | El revisor con razonamiento necesita más de 3 500 tokens de salida (v3 usó 6 500) | `max_tokens = 8192 − entrada − 300`. Así se respeta el criterio 4 sin un tope fijo |
| H5 | §5.2 fija temperatura 0 para el revisor con razonamiento; Qwen3 recomienda 0,6 en modo razonamiento y v3 usó 0,6 | Mantener 0 (spec) y medirlo en la prueba de humo. Si aparecen bucles, pasar a 0,6 y actualizar el spec |
| H6 | `LLM_MAX_CONCURRENCIA` es "total", pero un semáforo solo limita dentro de un proceso | Fase 1: **un** proceso `worker` con N hilos y un semáforo compartido. Si se escala a varios procesos, usar un semáforo en PostgreSQL |
| H7 | El techo del RA (§6.2.3) necesita una tabla verbo → nivel que el spec no define | Definirla en el P3 con el área académica (taxonomía de Bloom en español) |
| H8 | Calidad: cuestionarios y simulacros siguen en 55–65 % de ítems sólidos (criterio de cierre 14/16) | Publicarlos como **borrador** obligatorio para el docente. Retomar M1–M3 en el P3 |

> **Revisión del 2026-10-26:** los hallazgos R1–R9 (revisor de 1 ítem por llamada, límites de tiempo por rol, ajustes por carrera, tiempos reales de unos 10 min por cuestionario) y la estrategia de especialización por facultad y carrera están en [2026-10-26-revision-planes-y-especializacion.md](2026-10-26-revision-planes-y-especializacion.md).

## 5. Mirada académica: cómo validar que sirve

El criterio técnico (pasar la verificación) no basta para afirmar calidad pedagógica. Propuesta para el piloto en Ingenierías:

1. **Revisión por pares:** dos docentes del área clasifican cada ítem (sólido / corregible / descartable) con la misma guía que la revisión humana de las rondas 1–3. Se reporta el acuerdo entre ellos (kappa de Cohen) y no solo el porcentaje.
2. **Métricas de uso** (sin datos de estudiantes):
   - proporción de ítems editados por el docente,
   - tiempo de generación por herramienta,
   - devoluciones del revisor por ítem.
   Con estas métricas se alimenta la memoria de facultad (Fase 2).
3. **Alineación constructiva:** el paquete de evidencia muestra la tabla de especificaciones planificada frente a la real (RA × nivel). Esa tabla es el argumento ante coordinación académica.
4. **LOPDP:** el aviso de privacidad y el registro de accesos entran en el P4. Las herramientas no tratan datos de estudiantes.

## 6. Hoja de ruta (un plan por subsistema)

```text
 P1 Núcleo multiagente ──┬──► P3 Herramientas ──┐
   (LLM simulado + humo)  │                      ├──► P5 Chat de ajustes ──► P6 Entrega + frontend ──► P7 Despliegue
 P2 Lector y menú ────────┴──► P4 API y acceso ──┘
```

| Plan | Entregable verificable | Depende de | Esfuerzo estimado* | Criterios |
|---|---|---|---|---|
| **P1 Núcleo multiagente** ([plan](2026-10-26-p1-nucleo-multiagente.md)) | `worker` que toma un trabajo, genera un cuestionario y una ficha y deja el recurso con su evidencia; pruebas con IA simulada y humo con Qwen real | — | 2 semanas | 3, 4, 5, 6†, 7, 8, 11, 14 |
| **P2 Lector y menú** | `leer_silabo(pdf) -> SilaboUTI` y `construir_menu()` con los 2 sílabos reales | Contrato `SilaboUTI` del P1 (Tarea 3) | 1,5 semanas (en paralelo con P1) | 1, 2, 5 |
| **P3 Herramientas** | 13 workers más, herramientas sin IA, módulo de cálculo, techo del RA, M1–M3 | P1 | 2 semanas (+ M4 cuando llegue la plantilla) | 6, 9 |
| **P4 API y acceso** | FastAPI con autenticación, asignaturas, compartir, generar, trabajos, recursos | P1, P2 | 1,5 semanas | 12, 12b, 12c |
| **P5 Chat de ajustes** | `/chat` → `AccionAgente` → regenerar ítems | P3, P4 | 1 semana | 10 |
| **P6 Entrega y frontend** | HTML/PDF/DOCX y pantallas React | P4 (P5 para el chat) | 2 semanas | — |
| **P7 Despliegue** | Compose completo, nginx HTTPS, instalación limpia | P6 | 1 semana | 13 |

\* Estimación para una persona a tiempo completo; total ≈ 10–11 semanas.
† El criterio 6 se cierra en el P3 con la tabla de especificaciones completa y el módulo de cálculo.

**Orden recomendado:**

1. El **P1** primero: es lo que convierte el prototipo en producto y fija los contratos que usan los demás.
2. El **P2** puede avanzar en paralelo en cuanto exista el contrato `SilaboUTI`.
3. Los planes P2–P7 se escriben en detalle al terminar el anterior, para que nazcan de interfaces ya probadas y no de supuestos.

---

## 7. Organización de agentes para P2–P7

Todos los bloques siguen el esquema del P1 (ver *Equipo de ejecución* en el [plan P1](2026-10-26-p1-nucleo-multiagente.md)):

- coordinador sin código;
- un implementador nuevo por tarea;
- revisor de especificación y revisor de código;
- devolución al mismo implementador (máx. 2 rondas) y escalamiento al usuario;
- worktree propio cuando la ola es paralela.

Las tareas de esta sección están a **nivel de entregable**. Antes de ejecutar cada bloque, el coordinador escribe su plan detallado con `writing-plans`, con pruebas, interfaces y pasos TDD.

### 7.1 Roles nuevos que aparecen después del P1

| Rol | Quién | Modelo | Skills | Dónde participa | Responsabilidad |
|---|---|---|---|---|---|
| **Revisor de seguridad** | Subagente `general-purpose`, nuevo | opus | `security-review` | P4 (A2, A3, A5), P6 (E1), P7 (D2) | Autenticación, sesiones, autorización por asignatura, inyección, escape en HTML/DOCX/PDF, cabeceras y límites del proxy |
| **Revisor académico** | Subagente `general-purpose`, nuevo | opus | — | P2 (L3), P3 (todas), P5 (C1, C2) | Alineación con RA y rúbrica, niveles de Bloom, calidad de distractores, integridad académica (§9.4), lenguaje para estudiantes universitarios |
| **Verificador de interfaz** | Subagente `general-purpose`, nuevo | sonnet | `run`, Playwright | P6 (E3–E6) | Recorre los flujos en el navegador, toma capturas en móvil y escritorio, revisa la consola y la accesibilidad básica |
| **Implementador de interfaz** | Subagente `general-purpose`, nuevo | opus | `frontend-design`, `test-driven-development` | P6 (E3–E6) | Pantallas React con criterio visual propio. Reutiliza las decisiones de diseño de *Propuesta-SGA* si el usuario lo aprueba |
| **Docentes piloto** | Personas (1–2 de Ingenierías) | — | — | P3 (H7), P5 (C3), P6 (cierre) | Revisión humana ítem por ítem y prueba de uso real |
| **TI de la universidad** | Personas | — | — | P4 (SMTP), P7 (D4) | Cuenta de correo, servidor, dominio, certificado y concurrencia del servidor de IA |

### 7.2 Calendario global de olas (los bloques se solapan)

```text
Semana:      1        2        3        4        5        6        7        8        9       10       11
P1      [T1─T2..T6─T7..T10──T11..T15]
P2               [L1──L2·L3·L4──L5──L6·L7]
P3                          [H1·H2·H3──H4a·H4b·H5──H6──H7]···H8 (cuando llegue la plantilla)
P4                                   [A1──A2──A3──A4·A5]
P5                                                     [C1──C2──C3]
P6                                            [E1·E2]  [E3──E4──E5·E6]
P7                                                                       [D1──D2·D3]──D4 (TI)
```

`·` = en paralelo dentro de la misma ola · `──` = ola siguiente.

---

### 7.3 P2 · Lector y menú

**Base:** spec §7, §8.1, §2.2 · `mapeo-silabo.md` §2–§6 · **Depende de:** T3 del P1 (contrato `SilaboUTI`) · **Criterios:** 1, 2, 5

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **L1** Apertura y segmentación | Comprueba `%PDF`, ≤ 50 MB y capa de texto (si no la tiene, `422`). Separa portada y secciones I–VII. Descarta I y VII **antes** de extraer | sonnet | sonnet | Explorador (haiku): estructura de los 2 PDFs de `Silabos/` **sin copiar datos personales** |
| 2 | **L2** Portada, presentación y mapa de formación | Facultad, carrera, periodo, PF, nivel, horario, competencias, RA con evidencia, problema, PIS, metodologías | sonnet | sonnet | — |
| 2 | **L3** Momentos y tabla de sesiones | Sesiones fechadas, filas partidas entre páginas, actividad asincrónica con horas, entregables (TAREA, PAE, evaluación), LaTeX intacto, `semana_periodo` | **opus** | **opus** | Revisor académico: que los entregables y la política de IA se lean completos (de ellos depende la integridad) |
| 2 | **L4** Rúbricas y bibliografía | Rúbrica por momento y del producto final (indicadores × 5 niveles), bibliografía básica y complementaria | sonnet | sonnet | — |
| 3 | **L5** Ensamblado `leer_silabo(pdf) -> SilaboUTI` | Criterio 1 con los 2 sílabos (4 momentos; 11 y 6 sesiones). El PDF se borra tras la lectura. Prueba de que no se extraen datos personales | sonnet | **opus** (datos personales) | — |
| 4 | **L6** Menú y versiones | `construir_menu()` por semana y día (criterio 2). Una nueva versión del mismo PF marca las clases que cambiaron | sonnet | sonnet | — |
| 4 | **L7** Ruta de respaldo con IA | Solo cuando la plantilla no se reconoce: extracción con esquema `SilaboUTI` y comprobación de fidelidad contra el texto | sonnet | sonnet | — |

**Puertas del usuario:**
- Autorizar que las pruebas lean los PDFs reales en local (nunca se versionan).
- Decidir si se crea una fixture anonimizada versionable.
- Opcional: enviar un sílabo de otra facultad o presencial (pendiente 1) para probar L7.

---

### 7.4 P3 · Herramientas

**Base:** `catalogo-herramientas.md`, spec §6, §8.2, §9.4, §16.1 · **Depende de:** P1 completo · **Criterios:** 6, 9

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **H1** Herramientas sin IA | Hoja de ruta (15), autoevaluación con rúbrica de momento y final (12, 17) y lista de verificación (13). Rúbrica copiada sin cambios (regla 8 de §10.1) | sonnet | sonnet | — |
| 1 | **H2** Módulo de cálculo | Funciones deterministas con semilla para Ingenierías: datasets ficticios, descriptivos, binomial y normal, Bayes, intervalos, t y ANOVA. Cada facultad declara las suyas en su YAML | sonnet | **opus** | Revisor académico: que los resultados correspondan a lo que se enseña en la clase |
| 1 | **H3** Techo del RA | Tabla verbo → nivel (Bloom en español) y su aplicación en el planificador (H7 del análisis) | sonnet | sonnet | Revisor académico. **Puerta: validación del área académica** |
| 2 | **H4a** Workers de texto | Guía de clase invertida, tarjetas, glosario | sonnet | sonnet | Revisor académico |
| 2 | **H4b** Workers con dibujo | Mapa conceptual (la IA da nodos y relaciones, el código dibuja el SVG) y repaso de terminología (el código arma la grilla) | sonnet | sonnet | — |
| 2 | **H5** Práctica guiada | Ejercicios con el software de la sesión y resultados de H2 | **opus** | **opus** | Revisor académico |
| 3 | **H6** Herramientas de momento y asignatura | Repaso integrador, simulacro (reutiliza el cuestionario con tabla de especificaciones), estudio de caso, guía de evidencia (revisor de integridad), guía del producto final. Habilita los ámbitos `momento` y `asignatura` en el orquestador | **opus** | **opus** | Revisor académico (foco en §9.4: ninguna resuelve una evidencia) |
| 4 | **H7** Mejoras M1–M3 y ronda de calidad v4 | Ítems paramétricos, reglas de dominio por facultad, sobregeneración con selección. Ronda nueva según la trazabilidad de §16.1 | **opus** | **opus** | Revisor académico. **Puerta: docentes piloto revisan ítem por ítem** (criterio de cierre 14/16) |
| — | **H8** Plantilla académica (M4) | Adaptar esquemas y prompts a la plantilla institucional (`version_esquema` + 1) | sonnet | sonnet | **Bloqueada hasta recibir la plantilla** (pendiente 3b) |

---

### 7.5 P4 · API y acceso

**Base:** spec §2.1, §12, §14 · **Depende de:** P1, P2 · **Criterios:** 12, 12b, 12c

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **A1** Esqueleto FastAPI | App, `/salud` (servidor de IA alcanzable con `GET /v1/models` y `max_model_len` 8192, agentes cargados), mapa de errores (401/403/404/415/422/429/503), CORS limitado al origen, CSRF | sonnet | sonnet | — |
| 2 | **A2** Inicio de sesión | `/auth/codigo` (respuesta idéntica exista o no la cuenta), `/auth/verificar`, `/auth/salir`, `/auth/yo`. Código de 6 dígitos guardado como hash, 10 min, 5 intentos y `429`. Dominio por igualdad exacta. Cookie `HttpOnly`/`Secure`/`SameSite=Lax` con 8 h de inactividad y 7 días de máximo. `SMTP_MODO=consola` para desarrollo. Módulo aislado para Microsoft más adelante | **opus** | **opus** | **Revisor de seguridad.** Pruebas con `x@indoamerica.edu.ec.otro.com` y `x@mail.uti.edu.ec` |
| 3 | **A3** Asignaturas y permisos | `POST /silabos` (usa P2; `415`/`422`), mis asignaturas, compartir como editor o lector, retirar acceso. Regla A9 en cada ruta | **opus** | **opus** | **Revisor de seguridad** (criterio 12b) |
| 4 | **A4** Generación y recursos | `generar`, `trabajos` (para la consulta periódica), `recursos` GET/PUT con registro de ediciones (alimenta la memoria de facultad de Fase 2), catálogo de herramientas por ámbito | sonnet | sonnet | — |
| 4 | **A5** Registro, límites y privacidad | Registro de accesos sin contenido, límite por correo y por IP, `/admin/consumo`, aviso de privacidad LOPDP | sonnet | sonnet | **Revisor de seguridad** |

**Puertas del usuario:**
- Cuenta SMTP institucional (pendiente 2) para pasar de consola a envío real.
- Lista de `ADMINISTRADORES`.
- Revisar el texto del aviso de privacidad.

---

### 7.6 P5 · Chat de ajustes

**Base:** spec §3.4, §9.2, §3.8 (A5) · **Depende de:** P3, P4 · **Criterio:** 10

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **C1** Interpretación | El agente de facultad convierte el mensaje en `AccionAgente` (temperatura 0, esquema cerrado). El código valida que los IDs existan en la asignatura | **opus** | **opus** | Revisor académico: que `fuera_de_alcance` cubra consultas generales, cambios al sílabo y soluciones de tareas |
| 2 | **C2** Ejecutores | `ajustar_recurso` regenera solo los ítems afectados y los vuelve a verificar y revisar. `generar` crea los mismos trabajos que el menú. Más `aclarar` y `fuera_de_alcance` | **opus** | **opus** | Revisor académico |
| 3 | **C3** Endpoint e historial | `POST /asignaturas/{asig}/chat` e historial por asignatura + usuario (A5). Criterio 10: "Haz más difícil la pregunta 3" | sonnet | sonnet | **Puerta: docentes piloto prueban ~15 frases reales** |

---

### 7.7 P6 · Entrega y frontend

**Base:** spec §8.1, §13, §2.2, §10.3 · **Depende de:** E1–E2 de P3; E3–E6 de P4 (y P5 para el chat)

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **E1** HTML autónomo | Archivo único para Canvas, autocorregible, KaTeX incrustado, sin CDN, todo el texto escapado, pie institucional (§13) | sonnet | sonnet | **Revisor de seguridad** (escape e inyección) |
| 1 | **E2** PDF y DOCX | Mismos contenidos; fórmulas como imagen; pie institucional | sonnet | sonnet | — |
| 2 | **E3** Base del frontend | React + Vite + Tailwind; ingreso con código; mis asignaturas; subida del sílabo | Implementador de interfaz (**opus**) | sonnet | Verificador de interfaz |
| 3 | **E4** Menú y generación | Menú por semana y día con estados; panel de generación; consulta cada 3 s con avance por lotes | Implementador de interfaz (**opus**) | sonnet | Verificador de interfaz |
| 4 | **E5** Revisión y chat | Edición del recurso, estado por ítem ("requiere revisión", "borrador"), resumen del paquete de evidencia, panel de chat | Implementador de interfaz (**opus**) | sonnet | Verificador de interfaz · Revisor académico (cómo se presenta el borrador al docente) |
| 4 | **E6** Compartir y administración | Pantalla para compartir y pantalla de consumo de IA | sonnet | sonnet | Verificador de interfaz |

**Puertas del usuario:**
- Identidad visual (logo y colores Indoamérica) y si se reutiliza el diseño de *Propuesta-SGA*.
- Prueba de uso con 1–2 docentes antes de cerrar el bloque.

---

### 7.8 P7 · Despliegue

**Base:** spec §3.6, §5.1, §14 · **Depende de:** P6 · **Criterio:** 13

| Ola | Tarea | Entregable | Implementador | Revisor de código | Otros |
|---|---|---|---|---|---|
| 1 | **D1** Contenedores | Dockerfiles de `api`, `worker` y `web`; `infra/docker-compose.yml` con los 5 servicios y sus healthchecks; variables de §14 | sonnet | sonnet | — |
| 2 | **D2** Proxy | nginx con HTTPS, HSTS, cabeceras de seguridad, límite de 50 MB y de solicitudes. El servidor de IA nunca queda expuesto | sonnet | sonnet | **Revisor de seguridad** |
| 2 | **D3** Instalación limpia y operación | Criterio 13 en una máquina limpia, respaldo y restauración de PostgreSQL, manual de operación | sonnet | sonnet | — |
| 3 | **D4** Puesta en marcha en la UTI | Despliegue en el servidor de la red universitaria, dominio y certificado; ajuste de `LLM_MAX_CONCURRENCIA` | Coordinador guía al usuario | — | **Puerta: TI** (pendientes 2b y 4). Lo ejecuta TI o el usuario, no un subagente |

---

### 7.9 Cierre de la Fase 1

Al terminar el P7, un **revisor final** (opus, con `requesting-code-review` y `verification-before-completion`):

1. recorre los 14 criterios de §15 con la prueba que demuestra cada uno;
2. corre la prueba de aislamiento (criterio 14) en el entorno desplegado;
3. entrega al usuario el informe con los cambios que deben pasar al **spec v1.3**.
