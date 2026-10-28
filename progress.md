# Progreso — Generador de Recursos de Estudio UTI

> **Para qué sirve:** es la memoria del proyecto. Al retomar, **se lee primero este archivo** y solo después, si hace falta, el documento puntual que enlaza.
> No hace falta recorrer el repositorio completo.
>
> **Última actualización:** 2026-10-28 · **Fase:** 1 · **Bloque activo:** P5 publicado en PR #11 sobre P6d (#10); aceptación con docentes piloto pendiente. Siguiente: preparar P7.

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

P1–P6 implementados técnicamente, incluido chat privado de ajustes y exportación HTML/PDF/DOCX. P5 se apila sobre P6d (PR #10), sin fusionar. Pruebas finales P5: 783 backend pasan/4 de servidor excluidas; humo optativo del intérprete con Qwen real pasa; 25 unitarias frontend y 28 de navegador, typecheck/build pasan. Falta aceptación con docentes piloto y P7; activación institucional condicionada a SMTP (B4), aviso aprobado (B9) y administradores designados (B10). H7 y plantilla académica siguen pendientes.

## Documentos de referencia

| Documento | Contenido |
|---|---|
| [docs/especificacion-generador-recursos-uti-v1.3.md](docs/especificacion-generador-recursos-uti-v1.3.md) | Spec vigente (v1.3, 2026-10-27): tabla C1–C16 con H1–H8 y contratos de P1/P2/P4; la v1.2 queda como historia |
| [docs/superpowers/plans/2026-10-26-analisis-y-hoja-de-ruta-fase1.md](docs/superpowers/plans/2026-10-26-analisis-y-hoja-de-ruta-fase1.md) | Análisis de pendientes, hallazgos H1–H8, hoja de ruta P1–P7 y agentes por bloque |
| [docs/superpowers/plans/2026-10-26-p1-nucleo-multiagente.md](docs/superpowers/plans/2026-10-26-p1-nucleo-multiagente.md) | Plan detallado del P1: 15 tareas, olas, agentes y puertas |
| [docs/superpowers/plans/2026-10-26-revision-planes-y-especializacion.md](docs/superpowers/plans/2026-10-26-revision-planes-y-especializacion.md) | Revisión de la lógica (R1–R9), especialización por facultad y carrera (niveles 0–3) y protocolo de alta de facultades |
| [docs/mapeo-silabo.md](docs/mapeo-silabo.md) | Estructura del sílabo y contrato `SilaboUTI` |
| [docs/catalogo-herramientas.md](docs/catalogo-herramientas.md) | 17 herramientas propuestas |
| [docs/prueba-calidad-silabo.md](docs/prueba-calidad-silabo.md) | Rondas de calidad con Qwen3-8B |
| [docs/arquitectura-agentica-hive.md](docs/arquitectura-agentica-hive.md) | Mapa de Hive y patrones que se copian |
| Página visual del plan | https://claude.ai/artifact/DREtxrkEt9TSsoCueev3Hy (privada) |
| [Propuesta institucional del proyecto](docs/propuestas/propuesta-desarrollo-materiales-aprendizaje-formato-institucional.docx) | Versión ilustrada de 10 páginas: objetivos, alcance, colmena, 3 mockups conceptuales, gráfico de tiempos, recursos, cronograma e indicadores; conserva el formato de Asana |

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
| T10 Workers | 5 | ✅ | `65afc4c` | Hecha por el coordinador (subagentes bloqueados) |
| T11 Verificador | 6 | ✅ | `a518a1d` | Regex ampliada: "Todas las anteriores" |
| T12 Revisor | 6 | ✅ | `a6c470a` | 1 ítem por llamada, a ciegas, integridad |
| T13 Coordinador de facultad | 7 | ✅ | `e384002` | Correcciones de lease (`c01f9c0`); cada ronda revisa solo los devueltos y la reanudación reutiliza el último veredicto |
| T14 Orquestador y worker | 8 | ✅ | `05af50f` | Pruebas de enrutamiento, caída y aislamiento. Revisado por el coordinador |
| T15 Prueba con Qwen real | 9 | ✅ | ver bitácora 2026-10-27 | Pasa. Cuestionario M3-S4 (4 ítems) → `requiere_revision` con 7 devoluciones; ficha M2-S1 → `listo` |
| Revisión final P1 | — | ✅ | — | Coordinador: sin secretos ni datos personales versionados; logs sin prompts. Push pendiente |

### P2–P7

| Bloque | Estado | Plan detallado | Nota |
|---|---|---|---|
| P2 Lector y menú | ✅ | [plan](docs/superpowers/plans/2026-10-27-p2-lector-y-menu.md) | Rama `p2/lector`, publicada; PR #2 sobre P1 según capturas. Ruta de respaldo con IA (L7) pendiente de B7 |
| P3 Herramientas | 🔄 | [P3a](docs/superpowers/plans/2026-10-27-p3a-herramientas-sin-ia.md) · [P3b](docs/superpowers/plans/2026-10-27-p3b-herramientas-con-ia.md) | **P3b ✅** (rama `p3/con-ia`, `0270b53`…`c7e10dd`): simulacro, repaso integrador, guía de la evidencia, estudio de caso y guía del producto final con IA; §9.4.2 aplicada. **P3a ✅** (rama `p3/sin-ia`, `a90ab9b`, `0f9d82b`): hoja de ruta, autoevaluación con la rúbrica (momento y final) y lista de verificación de la evidencia, sin IA. P3b (herramientas con IA de momento/asignatura, H7) por planificar; formato final bloqueado por B3 |
| P4 API y acceso | ✅ | [plan](docs/superpowers/plans/2026-10-27-p4-api-y-acceso.md) | A1–A5 implementadas; activación institucional pendiente B4/B9/B10 y P7 |
| P5 Chat de ajustes | 🔄 | [plan](docs/superpowers/plans/2026-10-28-p5-chat-ajustes.md) | Implementación y cierre técnico en `codex/p5-chat`; humo del intérprete con Qwen real pasa. [15 casos para docentes piloto](docs/pruebas/p5-piloto.md) pendientes: no equivalen a pruebas automáticas. |
| P6 Entrega y frontend | 🔄 | [P6a](docs/superpowers/plans/2026-10-28-p6a-frontend-menu.md) · [P6b](docs/superpowers/plans/2026-10-28-p6b-mis-recursos.md) · [P6d](docs/superpowers/plans/2026-10-28-p6d-exportacion-pdf-word.md) | Implementados menú, generación, avance, revisión, edición y descargas HTML/PDF/DOCX. P6d publicado en PR #10; QA visual completado. Plantilla institucional y aceptación académica pendientes. |
| P7 Despliegue | 🔄 | [plan](docs/superpowers/plans/2026-10-28-p7-despliegue.md) | D1–D3 implementados y probados en instalación aislada (rama `codex/p7-despliegue`); D4 (entrega a TI) y puesta en marcha bloqueadas por B4/B5/B6/B9/B10 |

### P4 · Registro por tarea

| Tarea | Estado | Commit | Validación |
|---|---|---|---|
| A1 Base HTTP | ✅ | `f85d442` | 275 pasan/1 omitida; salud real HTTP 200 |
| A2 Códigos y sesiones | ✅ | `16690a6` | 314 pasan/1 omitida; dos revisores |
| A3 Asignaturas y permisos | ✅ | `cf4a3b0` | 359 pasan/1 omitida; dos revisores; ambos PDF reales por HTTP |
| A4 Generación y recursos | ✅ | `c6a4fc3` | 443 pasan/1 omitida; dos revisores; generación simulada→HTTP y edición concurrente |
| A5 Límites, consumo y privacidad | ✅ | `49ac905` | 514 pasan/1 omitida; dos revisores; aviso técnico pendiente de aprobación |

### Criterios de aceptación de la Fase 1 (§15)

| # | Criterio (resumen) | Bloque | Estado |
|---|---|---|---|
| 1 | Los 2 sílabos se leen sin IA | P2 | ✅ `test_criterio_1_datos`, `test_criterio_1_tic` (PDF locales) |
| 2 | Menú por semana (6 y 4 semanas) | P2 | ✅ `test_criterio_2_reales` |
| 3 | Enrutamiento por facultad | P1 | ✅ `test_enruta_al_crear` |
| 4 | Ninguna llamada > 8 192 tokens | P1 | ✅ Simulado y real (T15: máx. ≈6 360) |
| 5 | Sin datos personales en prompts | P1, P2 | ✅ `test_sin_datos_personales` + `test_criterio_5_sin_datos_personales` |
| 6 | Cuestionario de 12 con tabla de especificaciones | P1, P3 | 🔄 Simulado: `test_camino_feliz`; calidad real con H8 (P3) |
| 7 | Ítem ambiguo → "requiere revisión" | P1 | ✅ `test_item_ambiguo_requiere_revision` |
| 8 | Herramienta que resuelve una tarea → devuelta | P1 | ✅ `test_devuelto_resuelve_entregable` |
| 9 | M2-S1 y M2-S2 producen herramientas distintas | P1, P3 | 🔄 Contexto y focos distintos (`test_silabo`, `test_planificador`); generación real en P3 |
| 10 | Chat regenera solo la pregunta pedida | P5 | ⬜ |
| 11 | Caída del servidor → "en espera" y reanuda | P1 | ✅ `test_servidor_caido_queda_en_espera`, `test_retoma_tras_caida` |
| 12 / 12b / 12c | Dominios, permisos, bloqueo tras 5 intentos | P4 | 🔄 Implementación probada A2–A5, incluidos límites IP/correo; validación de envío institucional real pendiente B4 |
| 13 | Instalación limpia | P7 | ⬜ |
| 14 | Aislamiento entre asignaturas | P1 | ✅ `test_aislamiento_dos_asignaturas` |

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
| B9 | Aprobar aviso de privacidad, responsable, canales y conservación académica | P4 A5 (activación), P6, P7 | Usuario / institución / DPD | Abierto; borrador técnico en `docs/privacidad-borrador.md` |
| B10 | Designar lista institucional de `ADMINISTRADORES` | Consumo administrativo en despliegue | Usuario / institución | Abierto; lista vacía por defecto |

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
| 2026-10-26 | Especialización en 4 niveles (configuración → memoria de reglas → ejemplares → LoRA por facultad). Fase 1 solo con el Nivel 0. El usuario aprobó D1–D5; las consultas a TI y las designaciones institucionales siguen pendientes de ejecución | Revisión §4–§5 y aprobación del usuario en la conversación |
| 2026-10-27 | A4: historial solo operativo, `uso_mejora=false`; modificaciones reales invalidan la vigencia de la evidencia y quedan `requiere_revision`; guardar contenido idéntico no cambia estado ni revisión | `docs/desarrollo-api.md`, plan P4 A4 |
| 2026-10-27 | A5: cuotas persistentes por ventanas UTC y HMAC, confianza explícita en proxies, bitácora sin URL/cuerpos/identidad en claro. Retención técnica propuesta de 30 días y purga explícita; aviso y administradores reales pendientes de institución | `docs/desarrollo-api.md`, `docs/privacidad-borrador.md`, plan P4 A5 |

### Decisiones D1 a D5 aprobadas por el usuario

| # | Decisión aprobada | Ejecución pendiente o alcance |
|---|---|---|
| D1 | Ajustes de estilo por carrera desde la Fase 1 | Incluidos en T8 |
| D2 | Consultar a TI sobre `--enable-lora` y GPU | Consulta pendiente; no incorpora LoRA al alcance inicial |
| D3 | Usar ediciones docentes para mejorar el sistema | Mantener aviso, exclusión y autorización institucional antes de recolectarlas para ese fin |
| D4 | Un coordinador por carrera valida el perfil de FING, empezando por Software y TI | Personas responsables por designar |
| D5 | Emitir el spec v1.3 antes del P3 | ✅ Emitido el 2026-10-27 |

---

## Bitácora (lo ya hecho)

### 2026-10-28
- **Publicación P7 D1–D3:** commit `8da1e5d` en `origin/codex/p7-despliegue`; PR [#12](https://github.com/CZurita14/Agente-GenRecursos/pull/12) abierto sobre `codex/p5-chat` (#11), sin fusionar ni desplegar.
- **P7 D1–D3 (Codex + revisión e instalación real por Claude):** Compose de despliegue con `db`, `migrar`, `api`, `worker`, `web` y `proxy`; imágenes con bases fijadas por digest, usuario no privilegiado y raíz de solo lectura; migrador con candado; `/salud/vivo` y `/salud/listo` internas; latido del worker; `infra/operar.py` (validar, respaldo, restaurar en base nueva) y `docs/operacion.md`. La instalación aislada real destapó 5 defectos que impedían arrancar o publicar (recursos públicos fuera de la imagen, tmpfs partido por YAML, temporales de nginx, colisión con la IP del proxy, proxy sin puertos por estar solo en redes internas); corregidos con pruebas. Verificación por el proxy HTTPS 24/24, respaldo/restauración idénticos y reinicio estable. **852 backend pasan**. Pendiente D4 y puertas de TI.
- **Preparación P7:** [diseño propuesto](docs/superpowers/plans/2026-10-28-p7-despliegue.md) tras revisar Compose, configuración, salud, autenticación y lector PDF. Docker disponible; no se modificaron contenedores. Propone cinco servicios aislados, migración inicial, HTTPS, salud independiente de Qwen y respaldo/restauración en base nueva. Pendiente de aprobación antes de implementar; puesta en marcha institucional sigue sujeta a TI.
- **Publicación P5:** commit `7f39d2d` en `origin/codex/p5-chat`; PR [#11](https://github.com/CZurita14/Agente-GenRecursos/pull/11) abierto sobre `codex/p6d-exportacion` (#10). Cierre técnico verificado; no se fusionó ni desplegó. La aceptación académica con docentes piloto sigue pendiente.
- **P5 implementado:** cuatro acciones estrictas, chat privado, cola con fencing, generación desde chat y regeneración selectiva; revisión optimista, nueva validación y evidencia con alcance exacto. Corregidos hallazgos de privacidad, selección numérica, concurrencia de borradores y seguimiento de trabajos antiguos. **783 backend pasan/4 deseleccionadas**, **25 unitarias frontend y 28 navegador**, typecheck/build pasan; **humo Qwen real: 1 pasa** (dos pedidos sintéticos). Pendiente piloto humano; preparada matriz de 15 casos. No se migró ni desplegó la base operativa: activar `007_chat.sql` requiere reiniciar API/workers de forma coordinada.
- **Preparación P5:** revisados §3.4/§9.2/A5, cola, orquestador e historial de edición. [Diseño propuesto](docs/superpowers/plans/2026-10-28-p5-chat-ajustes.md): chat privado asíncrono, cuatro acciones estrictas y regeneración selectiva con revisión optimista. Pendiente de aprobación antes de implementar; prueba con docentes piloto y H7 siguen como puertas explícitas.
- **Publicación P6d:** commit `e6dffb8` publicado en `origin/codex/p6d-exportacion`; PR [#10](https://github.com/CZurita14/Agente-GenRecursos/pull/10) abierto sobre `p6/edicion` (#9), sin fusionar. Revisión visual, pruebas de permisos y regresión final completadas.
- **Cierre P6d:** revisadas seis muestras PDF/DOCX (16 páginas; Word local para renderizar DOCX). Corregidos opciones huérfanas, listas numeradas y estilos; fórmulas ajustadas al ancho de celda. Nuevas pruebas de lector, sesión, pertenencia, límites matemáticos y paginación. Resultado final: **663 backend pasan/3 deseleccionadas**, **21 unitarias frontend y 16 navegador**, typecheck/build pasan. Muestras ignoradas en `.superpowers/p6d-qa`; generador reproducible en `backend/tests/revisar_exportacion.py`.
- **P6d implementado** en `codex/p6d-exportacion`: PDF y DOCX en memoria con presentación ordenada, tablas, fórmulas MathText locales y respuestas separadas; API con validación/permisos y descargas frontend. Backend: 654 pasan/3 deseleccionadas (sin IA real); exportación final: 16 pasan. Frontend: 21 unitarias, 15 navegador, typecheck y build pasan. Falta revisión visual de documentos y PR; formato institucional sigue pendiente. Plan actualizado con desviaciones y límites.
- **P6d · PDF/Word:** [diseño y plan](docs/superpowers/plans/2026-10-28-p6d-exportacion-pdf-word.md) preparados tras revisar servicio, ruta HTTP, presentación y §13. Propone renderizadores nativos, fórmulas locales y respuestas al final en documentos estáticos. Pendiente de aprobación de diseño; implementación y pruebas todavía no ejecutadas.
- **Continuación y publicación P6c:** comprobado en el remoto `672635b`; creado PR [#9](https://github.com/CZurita14/Agente-GenRecursos/pull/9) sobre `p6/vistas`. No se fusionaron ramas. Encabezado y próximos pasos actualizados para evitar retomar tareas ya terminadas. Esta continuación no repitió las pruebas de implementación.
- **P6a · Frontend, menú** (rama `p6/menu`): diseño elegido por el usuario en maquetas (opción B: barra superior y dos caminos; «Perfil docente» visible pero en espera hasta la documentación). `frontend/` copiado de la plantilla institucional `andresinose/plantilla-UTI`; cliente de la API con cookie HttpOnly y proxy `/api` de Vite; ingreso con código, inicio, subir sílabo y Mis asignaturas. 17 pruebas unitarias y 7 de navegador (API simulada). Prueba real: ingreso con cuenta de prueba (código en consola), sílabo de Datos subido (201, ingenierias, 6 semanas/11 clases) y visible en Mis asignaturas.
- **P6b · Mis recursos** (rama `p6/recursos`): migración 008 (`validado_por`, `validado_en`; editar anula la validación), `POST …/recursos/{rid}/validar` con revisión y `GET …/exportar?formato=html` (409 sin validar; HTML autónomo, todo escapado, JS fijo de autocorrección, pie §13). Frontend: vista de la asignatura por semana y cierres de momento, catálogo de actividades (no mezcla IA y sin IA; momento restringido por §9.4.2 avisado), avance con sondeo cada 4 s, revisión con alertas del verificador/revisor, validar (confirmación si hay alertas) y descarga. 622 pruebas backend; 10 de navegador. Prueba real: hoja de ruta (sin IA, inmediata) y ficha de clase M2-S1 con Qwen (~45 s, 2/2 lotes) generadas, validadas y descargadas (200, adjunto, pie presente, sin recursos externos). Defecto visto: el renderizador genérico muestra claves crudas («Clase id», «Numero clase») y jsonb reordena las claves → hacen falta vistas por herramienta (ligado a B3).
- **P6 · Vistas por herramienta** (rama `p6/vistas`): `app/exportar/presentacion.py` convierte el contenido de cada herramienta (las 9 que no son cuestionario) en bloques ordenados (texto, lista, tabla, grupo) con títulos legibles; el orden no depende de jsonb y se ocultan las claves internas. La API la entrega como `presentacion` en el detalle del recurso, y la misma presentación arma el HTML para Canvas (rúbricas y calendario como tablas, pasos numerados). Si el contenido no coincide con el esquema (p. ej. editado), un respaldo genérico ordenado alfabéticamente lo muestra sin perder texto. 637 pruebas backend, 11 de navegador. Prueba real: ficha M2-S1 y hoja de ruta se ven en orden, sin claves crudas, y el HTML descargado sigue el mismo orden.
- **P6c · Edición por el docente** (rama `p6/edicion`, [plan](docs/superpowers/plans/2026-10-28-p6c-edicion.md)): la API ya editaba (PUT con revisión, esquema estricto, comprobaciones deterministas, historia, anula la validación); se agregó `ruta`/`rutas` a la presentación para que el mismo diseño sea el formulario: solo es editable el texto libre de las herramientas con IA (no indicador, momento, RA ni nivel). Cuestionario/simulacro: contexto, pregunta, opciones, justificaciones, clave y quitar preguntas (mínimo una). 422 conserva el borrador; 409 recarga; tras editar, las alertas son las de la edición y se avisa que el revisor no vuelve a revisar. Herramientas sin IA y lector: sin «Editar». 647 pruebas backend, 20 unitarias y 15 de navegador. Prueba real: ficha M2-S1 editada (historia revisión 1), «Sin validar», validada y descargada con el texto editado.

### 2026-10-27
- **P3b · Herramientas con IA de momento y asignatura** (rama `p3/con-ia`): contexto de momento/asignatura sobre `ContextoClase` y tabla `DEFINICIONES` (el coordinador ya no tiene la ficha escrita en el código); simulacro, repaso integrador, guía de la evidencia, estudio de caso y guía del producto final; §9.4.2 (TIC M4) bloquea la IA en el momento y en sus clases; requisitos del sílabo antes de encolar. Defecto del P2 corregido: la política de IA de TIC M3 salía vacía (fila partida al pie). Humo real: 3/4 listas, simulacro 3/4 ítems ok, 17 llamadas, 503 s, máx. 5 614 tokens. Revisión final independiente: 0 críticos, 6 importantes (1–5 corregidos con TDD; 6 documentado: los sílabos guardados antes de `0270b53` deben volver a subirse). Suite: 610 pasan/3 omitidas.
- **P3a · Herramientas sin IA** (rama `p3/sin-ia` desde `codex/p4-api-acceso`): generadores puros en `app/herramientas/sin_ia.py` (texto del sílabo + instrucciones fijas) e integración en `ServicioRecursos`: `POST /generar` con ámbito `momento` (`M<n>`) o `asignatura` crea al instante un trabajo `listo` con la instantánea y su recurso, sin cola ni modelo. Catálogo por ámbito; `422` si la herramienta no corresponde al ámbito o falta la rúbrica; no se editan (`422`); `silabo_actualizado` regenera con la instantánea y con el sílabo actual. Con los PDF reales: Datos 6 semanas/4 indicadores finales, TIC 4/5. Suite: 543 pasan/1 omitida. Decisión provisional hasta B3: la lista de verificación usa el descriptor «resolutivo» como referencia del mínimo esperado.
- **Continuación en Codex tras Claude:** contrastadas capturas con ramas; P1/P2 ya tienen upstream y `main` local incluye el merge `9eba803`. Las notas anteriores de «sin push» y «crear PR» quedaron obsoletas. PR #1/#2 abiertos según capturas; estado remoto en vivo no consultado.
- **P4 A1:** rama `codex/p4-api-acceso` desde P2. Fábrica FastAPI con lifespan, `/salud` contra `/v1/models`, modelo y ventana 8192, CORS/Origin exacto, rutas privadas cerradas hasta A2 y errores sin datos recibidos. 19 pruebas HTTP nuevas pasan; no se repitió humo GPU.
- **Validación A1:** suite completa 275 pasan y 1 omitida (58 s); `/salud` real HTTP 200 con agentes `general` e `ingenierias`. Revisión estática independiente sin hallazgos accionables. Autenticación y rutas de negocio aún no implementadas.
- **P4 A2:** migración `004_auth.sql`, códigos HMAC de 6 dígitos/10 min, cinco fallos → bloqueo persistente 15 min, sesiones revocables (8 h inactividad/7 días), rutas auth y cookies seguras. SMTP deshabilitado por defecto; consola solo en desarrollo explícito. Configuración en `docs/desarrollo-api.md`.
- **Revisión A2:** dos revisores independientes detectaron enumeración por rechazo SMTP y bloqueo SQL durante envío; corregidos con respuesta uniforme y reto persistido antes del transporte. Producción exige origen HTTPS. Pruebas adicionales comprueban hashes exactos y contención real de filas, reenvío, revocación y SMTP simulado; sin correos reales ni humo GPU.
- **Cierre A2:** ambos revisores confirmaron las correcciones sin pendientes sustantivos. Suite completa: **314 pasan y 1 omitida** (68 s), 39 pruebas nuevas sobre A1. Solo se migraron esquemas temporales de prueba; la BD de la aplicación requiere aplicar `004_auth.sql` según la guía antes de habilitar ingreso.
- **P4 A3 (`cf4a3b0`):** subida binaria PDF, listado/menú y compartir/revocar por UUID, migración `005_asignatura_acceso.sql`. PDF temporal: 10 MB, recepción 30 s, lectura en subproceso 20 s/512 MB, dos cupos por proceso API. Guía en `docs/desarrollo-api.md`.
- **Revisión A3:** reproducida y corregida carrera de permisos obsoletos tras espera (200→403); bloqueo y lectura del permiso en sentencias separadas. Corregidas primeras subidas concurrentes y cargas lentas/desconectadas; dos revisores confirmaron sin nuevos hallazgos.
- **Cierre A3:** 359 pasan/1 omitida (87 s), 45 pruebas nuevas. Ambos PDF reales vía HTTP: Datos 6 semanas/11 sesiones, TIC 4/6; memoria dura Windows comprobada, POSIX por validar en P7. Sin GPU ni correos reales; solo esquemas temporales. Siguiente A4; actualizar esta memoria al cerrar cada tarea, según solicitud del usuario.
- **P4 A4 (`c6a4fc3`):** catálogo de workers disponibles, generar/consultar trabajos y GET/PUT de recursos por asignatura; perfil elegido preservado en el trabajo. Migración `006_recurso_edicion.sql`: revisión optimista e historial antes/después con autor y sin uso para entrenamiento. Guía HTTP en `docs/desarrollo-api.md`.
- **Revisión A4:** corregida edición de clases sin contenidos explícitos y limitada pregunta a 1000 caracteres antes de comparar duplicados; JSON acotado a 1 MiB/30 s. Dos revisores cerraron sus hallazgos; se explicitó que guardar sin cambios es una operación sin modificación. Evidencia original conservada, pero no atribuida a textos editados.
- **Cierre A4:** 443 pasan/1 omitida (109 s), 84 pruebas nuevas. Polling de ocho estados, aislamiento con ambos cursos poblados, snapshot+perfil tras cambio de sílabo, lectores sin escritura y ediciones concurrentes 200/409. Sin GPU/correos reales; migraciones solo en esquemas temporales. Sigue A5.
- **P4 A5 (`49ac905`):** migración `007_control_acceso.sql`; cuotas IP/correo atómicas, persistentes y seudonimizadas; acceso administrativo por allowlist a consumo agregado. Auditoría mínima sin cuerpos, URLs ni identidades en claro; aviso técnico en `docs/privacidad-borrador.md` y mantenimiento explícito de seguridad vencida.
- **Revisión A5:** corregida imputación de XFF inválido a la cuota del proxy; arranque `python -m app.servidor` sin reinterpretación previa de IP ni access log crudo. Dos revisores cerraron hallazgos. Cierre de sesión no bloqueado por cuota de usuario agotada; se mantienen IP/Origin/sesión.
- **Cierre A5/P4:** 514 pasan/1 omitida (141 s), 71 pruebas nuevas. Cuotas entre instancias y concurrentes, UTC de BD, permisos administrativos, canarios de no-fuga y purga que preserva material académico. Sin GPU/correos reales; migraciones solo en esquemas temporales. B4/B9/B10 abiertos; P7 debe programar/supervisar mantenimiento y configurar proxy/HTTPS.
- **Revisión de A5 y P4 por Claude (2026-10-27):** suite verificada (514/1). A5 sin defectos en cuotas, XFF, seudónimos, auditoría ni mantenimiento; revisados también códigos/sesiones (A2), guarda de permisos (A3) y lector aislado. Hallazgo importante corregido en `383ce1e`: sin pool, cada petición autenticada abría ≥5 conexiones (15 ms de mediana, 30 ms p90; tope de PostgreSQL 100). Pool propio con restablecimiento de `statement_timeout`/`lock_timeout`; 522 pasan/1 omitida. Menores para P7/B9: `/privacidad` exige sesión (el aviso aprobado deberá leerse antes de pedir el correo) y la cuota por IP (600/min) se comparte si los docentes salen por un mismo NAT; ajustar en despliegue.
- **P2 · Lector y menú** (rama `p2/lector`, ejecución en línea con revisión final por un subagente opus):
  - Segmentación por posición en la página: se descartan las secciones I y VII, el índice y el pie «Generado por <usuario>», que también es un dato personal.
  - Las sesiones que empiezan al pie de página no tienen borde inferior: se reconstruye esa fila abierta. Sin esto se perdían 2 de 11 sesiones en Datos y 3 de 6 en TIC.
  - Con los PDF reales: Datos da 4 momentos y 11 sesiones, TIC 4 y 6. La cabecera, los momentos 2 y 3 y la rúbrica final de Datos son idénticos a la fixture transcrita a mano en el P1. El menú da 6 y 4 semanas.
  - Revisión final: 0 críticos, 3 importantes (más 3 menores reclasificados como importantes por privacidad o pérdida silenciosa de datos), todos corregidos con TDD. Quedan 5 menores diferidos en el registro `.superpowers/sdd/2026-10-27-p2-lector-y-menu/`.
  - Privacidad: dos sondeos de exploración imprimieron en la terminal del coordinador un nombre parcial y teléfonos de los docentes. Nada quedó en archivos ni commits. Las pruebas de no-fuga solo cuentan coincidencias.
  - Revisión de seguridad automática: tope de 60 páginas, conteo con salida temprana y cierre del PDF en todo camino de error. Aislar el análisis en un subproceso queda para P4/P7.
- Suite con PostgreSQL real: 183 → 185 pruebas pasan (1 omitida).
- Revisión de T13 por el coordinador: se corrigieron dos costos de tiempo. Las rondas de revisión revisaban de nuevo los 12 ítems (≈33 s cada uno); ahora solo los devueltos. Al reanudar se repetía una revisión ya guardada; ahora se reutiliza el último `Veredicto`. 2 pruebas nuevas.
- T14 revisada sin hallazgos que bloqueen (solo imports de `worker.py`).
- **T15 con Qwen3-8B-AWQ real:** pasa en 964 s. 24 llamadas, 63 196 tokens de entrada y 25 273 de salida. Worker ≈66 s por llamada (máx. 6 359 tokens); revisor ≈25–30 s por llamada (máx. 3 523). Cuestionario M3-S4 de 4 ítems → `requiere_revision`, 4 verificados, 7 devoluciones; ficha M2-S1 → `listo`, sin devoluciones. Los motivos del revisor no se conservaron (el esquema de prueba se borra al terminar). La ejecución de ayer en Codex se había cortado en la ronda 2 y dejó el esquema `prueba_6c0146d0` en la BD.
- **Análisis de las devoluciones del revisor** (3 corridas reales, trazas en `pruebas/resultados/20261027-humo-p1*.json`, detalle en `docs/prueba-calidad-silabo.md` §6). Causa: la evidencia del momento no llegaba como entregable y el worker copiaba su escenario. Cambios: evidencia en `entregables_momento`, regla de otros casos y datos para el worker, criterio de integridad del revisor según §9.4, veredicto de la clave conservado, reintento de las correcciones que fallan la verificación. Cuestionario: de 1/4 a 3/4 ítems `ok` y 4/4 verificados. Suite: 189 pruebas.
- **Escenarios por ítem:** el planificador reparte `escenarios` del perfil de la carrera, descarta los que se parecen al entregable y rota desde un punto fijo por clase. Humo real: cuestionario `listo` con 4/4 `ok`, 12 llamadas y 400 s. Suite: 194 pruebas.
- Revisión final del P1 (coordinador): sin `.env` ni claves versionadas, fixtures sin datos personales, logs solo con ids y tipo de error.
- Commits: `c01f9c0` (lease_version, veredicto completo, cantidad exacta), `e384002` (T13), `05af50f` (T14). Sin push.

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
- **Olas 2–4:** T4, T5, T7, T8 y T9 cerradas; 105 pruebas comprobadas en esa etapa.
- **Olas 5–6:** T10, T11 y T12 cerradas (`65afc4c`, `a518a1d`, `a6c470a`); 138 pruebas. La revisión automática de seguridad del commit no pudo completarse por un fallo de conexión.
- **Continuación en Codex:** T13 y T14 implementadas sin commit; revisores independientes disponibles de nuevo. Suite comprobada: 181 pruebas y 1 omitida. Se añadieron checkpoints de corrección y versión de adquisición del lease; el cierre de revisión sigue pendiente. El usuario interrumpió para priorizar la propuesta institucional.
- **Propuesta institucional:** se elaboró el Word «Desarrollo de materiales para el aprendizaje» a partir de la estructura y formato de la propuesta de Asana. Conserva encabezado, pie y validación institucional; distingue funciones previstas, documentación pendiente y escenario hipotético de tiempos. La referencia permanece sin cambios.
- **Versión ilustrada solicitada por el usuario:** propuesta ajustada a 10 páginas verificadas en Word y PDF de revisión. Incluye 5 imágenes: flujo de la colmena, 3 mockups (menú, generación y revisión) y comparación hipotética de tiempos. Capturas conceptuales identificadas como simulaciones; imágenes editables de origen y PNG en `docs/propuestas/imagenes/` (fuente HTML en `.superpowers/documentos/materiales-aprendizaje/`). Revisadas visualmente las 10 páginas.
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

1. ~~Emitir el spec v1.3~~ ✅ hecho (2026-10-27). Revisar con el usuario la tabla de cambios C1–C16.
2. Validar P5 con docentes piloto usando la matriz de 15 casos y preparar el diseño de P7; la implementación técnica de P5 ya está terminada. Validar con el área académica si «resolutivo» es la referencia correcta del mínimo en la lista de verificación; mantener pendientes H7 (techo del RA) y H8 (plantilla).
3. Resolver puertas institucionales B4/B9/B10 antes de activar P4; preparar despliegue P7 con HTTPS, proxy y mantenimiento supervisado. La calidad final y los formatos académicos siguen condicionados a la plantilla.
4. Mantener los PR apilados: PR #9 (`p6/edicion`) sobre `p6/vistas` (#8); no repetir su creación. Integrar las bases antes de sus ramas dependientes cuando se decida fusionarlas.
5. La propuesta institucional en `docs/propuestas/` permanece disponible para revisión del usuario; no se ha versionado ni modificado en esta continuación.
