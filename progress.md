# Progreso — Generador de Recursos de Estudio UTI

> **Para qué sirve:** es la memoria del proyecto. Al retomar, **se lee primero este archivo** y solo después, si hace falta, el documento puntual que enlaza.
> No hace falta recorrer el repositorio completo.
>
> **Última actualización:** 2026-10-26 · **Fase:** 1 · **Bloque activo:** P1 (sin empezar)

## Cómo se actualiza

1. **Al cerrar una tarea** (aprobada por los dos revisores e integrada), el coordinador:
   - cambia su estado en el tablero;
   - anota fecha, commit, pruebas y desviaciones en *Bitácora*.
2. **Al tomar una decisión** que cambie el spec o el plan, se registra en *Decisiones* con un enlace al documento modificado.
3. **Al abrirse o resolverse un bloqueo**, se actualiza *Bloqueos*.
4. Las entradas son **breves** (1–3 líneas): qué se hizo, dónde quedó y qué falta. El detalle va en el commit o en `docs/`.
5. Nunca se borra la historia: lo resuelto se marca como resuelto, no se elimina.

Estados: `⬜ pendiente` · `🔄 en curso` · `🔁 devuelta (ronda n)` · `✅ hecha` · `⛔ bloqueada`

---

## Estado en una línea

P1 en ejecución: Olas 0 a 4 cerradas (T1–T9), 105 pruebas pasan en `p1/nucleo`. Lo siguiente es la Ola 5 (T10, workers). El clasificador de permisos bloquea lanzar subagentes nuevos: las revisiones las hace el coordinador. El P2 ya puede arrancar en paralelo.

## Documentos de referencia

| Documento | Contenido |
|---|---|
| [docs/especificacion-generador-recursos-uti-v1.2.md](docs/especificacion-generador-recursos-uti-v1.2.md) | Spec vigente |
| [docs/superpowers/plans/2026-10-26-analisis-y-hoja-de-ruta-fase1.md](docs/superpowers/plans/2026-10-26-analisis-y-hoja-de-ruta-fase1.md) | Análisis de pendientes, hallazgos H1–H8, hoja de ruta P1–P7 y agentes por bloque |
| [docs/superpowers/plans/2026-10-26-p1-nucleo-multiagente.md](docs/superpowers/plans/2026-10-26-p1-nucleo-multiagente.md) | Plan detallado del P1: 15 tareas, olas, agentes y puertas |
| [docs/superpowers/plans/2026-10-26-revision-planes-y-especializacion.md](docs/superpowers/plans/2026-10-26-revision-planes-y-especializacion.md) | Revisión de la lógica (R1–R9), especialización por facultad y carrera (niveles 0–3) y protocolo de alta de facultades |
| [docs/mapeo-silabo.md](docs/mapeo-silabo.md) | Estructura del sílabo y contrato `SilaboUTI` |
| [docs/catalogo-herramientas.md](docs/catalogo-herramientas.md) | 17 herramientas propuestas |
| [docs/prueba-calidad-silabo.md](docs/prueba-calidad-silabo.md) | Rondas de calidad con Qwen3-8B |
| [docs/arquitectura-agentica-hive.md](docs/arquitectura-agentica-hive.md) | Mapa de Hive y patrones que se copian |
| Página visual del plan | https://claude.ai/artifact/DREtxrkEt9TSsoCueev3Hy (privada) |

---

## Tablero

### P1 · Núcleo multiagente

| Tarea | Ola | Estado | Commit | Nota |
|---|---|---|---|---|
| T1 Repositorio y configuración | 0 | ✅ | `c861d08` | Revisión limpia; detalles menores corregidos en la T2 |
| T2 Migraciones | 1 | ✅ | `e61e0b5` (merge) | 1 ronda de corrección (limpieza de la fixture `conn`) |
| T3 Contrato `SilaboUTI` | 1 | ✅ | `1eae46d` (merge) | Fixture transcrita del PDF real sin datos personales. **El P2 ya puede arrancar** |
| T6 Cliente de IA | 1 | ✅ | `c44d84d` (merge) | 1 ronda: errores 4xx de `/tokenize`, registro protegido, `finish_reason`, último JSON |
| T4 Cola con leases | 2 | ✅ | `988a01a` | 1 ronda: fencing por worker (zombis) y conteo de recuperaciones (trabajos venenosos). Desviación aceptada: la cola no se traba tras una caída |
| T5 Mensajes tipados | 3 | ✅ | `f91cf4f` | Incluye: contexto de clase con copias propias (sin compartir la rúbrica entre hilos) |
| T7 Constructor de prompts | 4 | ✅ | `84552af` (merge) | 2 rondas: recorte con búsqueda binaria, sello cotejado, datos delimitados, política de IA y entregables en el prompt (§9.4), pedido del código separado de las indicaciones del docente |
| T8 Perfiles de facultad | 4 | ✅ | `4254625` (merge) | Ajustes por carrera (Software, TI). Revisada por el coordinador (bloqueo de subagentes) |
| T9 Planificador | 4 | ✅ | `c7f7c6b` (merge) | 1 ronda: reparto de focos sin perder contenidos y desacoplado del nivel. Re-revisión por el coordinador |
| T10 Workers | 5 | ⬜ | — | |
| T11 Verificador | 6 | ⬜ | — | |
| T12 Revisor | 6 | ⬜ | — | |
| T13 Coordinador de facultad | 7 | ⬜ | — | |
| T14 Orquestador y worker | 8 | ⬜ | — | |
| T15 Prueba con Qwen real | 9 | ⬜ | — | El servidor es alcanzable desde la PC de desarrollo |
| Revisión final P1 | — | ⬜ | — | |

### P2–P7

| Bloque | Estado | Plan detallado | Nota |
|---|---|---|---|
| P2 Lector y menú | ⬜ | Por escribir | Arranca al cerrar T3 |
| P3 Herramientas | ⬜ | Por escribir | H8 bloqueada por la plantilla académica |
| P4 API y acceso | ⬜ | Por escribir | Envío real de códigos bloqueado por SMTP |
| P5 Chat de ajustes | ⬜ | Por escribir | |
| P6 Entrega y frontend | ⬜ | Por escribir | |
| P7 Despliegue | ⬜ | Por escribir | D4 bloqueada por TI |

### Criterios de aceptación de la Fase 1 (§15)

| # | Criterio (resumen) | Bloque | Estado |
|---|---|---|---|
| 1 | Los 2 sílabos se leen sin IA | P2 | ⬜ |
| 2 | Menú por semana (6 y 4 semanas) | P2 | ⬜ |
| 3 | Enrutamiento por facultad | P1 | ⬜ |
| 4 | Ninguna llamada > 8 192 tokens | P1 | ⬜ |
| 5 | Sin datos personales en prompts | P1, P2 | ⬜ |
| 6 | Cuestionario de 12 con tabla de especificaciones | P1, P3 | ⬜ |
| 7 | Ítem ambiguo → "requiere revisión" | P1 | ⬜ |
| 8 | Herramienta que resuelve una tarea → devuelta | P1 | ⬜ |
| 9 | M2-S1 y M2-S2 producen herramientas distintas | P1, P3 | ⬜ |
| 10 | Chat regenera solo la pregunta pedida | P5 | ⬜ |
| 11 | Caída del servidor → "en espera" y reanuda | P1 | ⬜ |
| 12 / 12b / 12c | Dominios, permisos, bloqueo tras 5 intentos | P4 | ⬜ |
| 13 | Instalación limpia | P7 | ⬜ |
| 14 | Aislamiento entre asignaturas | P1 | ⬜ |

---

## Bloqueos

| # | Bloqueo | Afecta a | Responsable | Estado |
|---|---|---|---|---|
| B1 | Aprobar `git init` y el remoto `CZurita14/Agente-GenRecursos` | P1 T1 | Usuario | ✅ Resuelto 2026-10-26 (sin push) |
| B2 | Docker Desktop apagado (`genrecursos-db`) | P1 T2 | Usuario | ✅ Resuelto 2026-10-26 |
| B3 | Plantilla de herramientas del área académica | P3 H8 | Área académica | Abierto |
| B4 | Cuenta SMTP institucional | P4 A2 | TI | Abierto |
| B5 | Servidor, dominio y certificado en la red UTI | P7 D4 | TI | Abierto |
| B6 | Concurrencia admitida por el servidor de IA | P7 D4 | TI | Abierto |
| B7 | Sílabos de otras facultades | P2 L7, Fase 2 | Usuario | Abierto |
| B8 | (Opcional) activar `--reasoning-parser qwen3` en vLLM | Ninguno; el plan funciona sin él | TI | Abierto |

---

## Decisiones

| Fecha | Decisión | Dónde quedó |
|---|---|---|
| 2026-10-13 a 10-19 | Solo se sube el sílabo; la unidad es la clase; menú por semana y día; agente por facultad + workers compartidos; revisor siempre activo | Spec v1.2 §Decisiones |
| 2026-10-19 | Acceso desde cualquier red con código por correo; solo `@indoamerica.edu.ec` y `@uti.edu.ec` | Spec §2.1 |
| 2026-10-20 | Contenido **solo del sílabo**; la base de conocimiento de carreras se retiró (queda solo el catálogo) | Spec §4.2, `kb/archivo/` |
| 2026-10-20 | No se cambia a un modelo mayor; la calidad se sostiene con el diseño del generador | Spec §Decisiones |
| 2026-10-20 | Cola sobre PostgreSQL con leases; código propio en Python + Pydantic (sin LangGraph) | Spec §3.6 |
| 2026-10-26 | PostgreSQL en todos los entornos; `asignatura_id` UUID; recorte sin base de conocimiento; `max_tokens` dinámico (H1–H4) | Hoja de ruta §4 (pendiente pasarlo al spec v1.3) |
| 2026-10-26 | Ejecución con subagentes: coordinador + implementador + 2 revisores por tarea; olas paralelas en worktrees | Plan P1 *Equipo de ejecución* |
| 2026-10-26 | Motor de razonamiento: **solo** el Qwen3-8B local, usando el SDK `openai` | Plan P1 *Motor de IA* |
| 2026-10-26 | Revisor de 1 ítem por llamada; límite de 120 s para workers y 240 s para el revisor; lease de 360 s; `recurso.version_silabo`; ajustes de estilo por carrera (R1, R2, R4, R5) | Plan P1 (T1, T2, T6, T8, T12) |
| 2026-10-26 | Propuesta de especialización en 4 niveles (configuración → memoria de reglas → ejemplares → LoRA por facultad). Fase 1 solo con el Nivel 0. Protocolo de alta por facultad con conjunto dorado y criterio de graduación | Revisión §4–§5 (D1–D5 por decidir) |

### Preguntas abiertas para el usuario

| # | Pregunta | Recomendación |
|---|---|---|
| D1 | ¿Ajustes de estilo por carrera desde la Fase 1? | Sí (ya incluido en T8) |
| D2 | ¿Consultar a TI sobre `--enable-lora` y GPU (Nivel 3)? | Consultar sin comprometerse |
| D3 | ¿Usar las ediciones de los docentes para mejorar el sistema? | Sí, con aviso y opción de excluirse (LOPDP), aprobado por la universidad |
| D4 | ¿Quién valida el perfil de FING? | Un coordinador por carrera (Software y TI primero) |
| D5 | ¿Emitir el spec v1.3 antes del P3? | Sí |

---

## Bitácora (lo ya hecho)

### 2026-10-26
- Análisis de lo pendiente y hoja de ruta P1–P7 con hallazgos H1–H8.
- Plan detallado del P1: 15 tareas TDD, olas y asignación de agentes y modelos.
- Organización de P2–P7 con el mismo esquema y roles nuevos: revisor de seguridad, revisor académico, implementador y verificador de interfaz, docentes piloto, TI.
- Página visual del plan publicada (artifact privado).
- Servidor de IA verificado desde la PC de desarrollo:
  - `/v1/models` → `max_model_len` 8192;
  - `/tokenize` funciona;
  - con razonamiento activado, el razonamiento llega en `content` entre `<think>` y en inglés.
  - El plan se ajustó en consecuencia (T6, T12, T15).
- Se creó este `progress.md`.
- Revisión final de la lógica de los planes con los tiempos medidos en las rondas v2 y v3:
  - el revisor por ítem tuvo mediana de 33 s y máximo de 125,6 s, con hasta 3 420 tokens;
  - con eso se corrigieron el revisor, los límites de tiempo, el lease y la versión del sílabo en los recursos;
  - se agregaron ajustes por carrera.
- Estrategia de especialización por facultad y carrera (niveles 0–3) y protocolo de alta en 9 pasos.
- Página visual v3:
  - sección "Motor del producto": el Qwen local lo usan el agente coordinador de facultad, los workers y el revisor; el orquestador, el lector, el planificador y el verificador son código;
  - sección de especialización;
  - tarjetas de tareas con las correcciones R1–R5.

### 2026-10-26 · Ejecución del P1
- **Repositorio:**
  - `git init` en la carpeta del proyecto;
  - commit base `5a473ed` en `main`;
  - rama de trabajo `p1/nucleo`;
  - remoto `origin` configurado, **sin push**.
- **Ola 0:** T1 terminada (configuración del backend).
- **Ola 1:** T2, T3 y T6 en paralelo, cada una en su worktree, con doble revisión. T2 y T6 necesitaron 1 ronda de corrección cada una. Integradas en `p1/nucleo` (`1eae46d`), **36 pruebas pasan**.
- **Registro de ejecución** (decisiones, hallazgos menores diferidos): `.superpowers/sdd/2026-10-26-p1-nucleo-multiagente/progress.md`. No se versiona.
- **Incidente de privacidad (T3):** el subagente imprimió en su terminal un fragmento de la sección I del sílabo de Datos (datos del docente).
  - Verificado que no está en ningún archivo ni commit; quedó solo en el registro local temporal de ese subagente.
  - Regla nueva para el P2: extraer el texto saltando las secciones I y VII antes de imprimir nada.

### 2026-10-20
- Tres rondas de prueba de calidad con Qwen3-8B (aprox. 5, 10 y 8 ítems sólidos de 16). Las mejoras M1–M5 quedan en pausa hasta tener la plantilla académica y más sílabos. Detalle en `pruebas/` y `docs/prueba-calidad-silabo.md`.
- Base de conocimiento de carreras construida (PostgreSQL + pgvector, embeddings locales) y **retirada** el mismo día. Quedan el catálogo de 8 facultades y las tablas `facultad`/`carrera`.
- Catálogo de herramientas propuesto (`docs/catalogo-herramientas.md`).
- Arquitectura de implementación decidida (spec §3.6–§3.8): cola, mensajes tipados y reglas de aislamiento A1–A9.

### 2026-10-19
- Spec v1.1 y v1.2.
- Mapa de la arquitectura agéntica de Hive con REA (`docs/arquitectura-agentica-hive.md`).
- Servidor de IA medido: 8 192 tokens, `json_schema` sí, llamadas a herramientas no, ~30 tokens/s.

### 2026-10-13
- Spec v1.0, mapeo de los dos sílabos de Ingenierías (`docs/mapeo-silabo.md`) y análisis de Astra AI.

---

## Siguiente paso

1. Que apruebes la **Ola 0** (B1) y enciendas Docker (B2).
2. Elegir el modo de ejecución. Se recomienda por subagentes.
3. Arranca la T1.
