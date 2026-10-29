# P6b · Mis recursos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el docente elija una clase o un momento, genere la herramienta, la revise, la valide y descargue un HTML listo para Canvas.

**Architecture:**
- **Backend:** la validación del docente (migración 008 y una ruta) y la exportación HTML (`app/exportar/`), con un renderizador por forma de contenido. Todo texto pasa por `html.escape`.
- **Frontend:** las vistas `Asignatura` (menú por semana), `Actividad` (catálogo y generación), `Progreso` (consulta de trabajos), `Recurso` (revisión, validación y descarga) y `Recursos` (lista).

**Tech Stack:** FastAPI y PostgreSQL (backend); React, TypeScript y la plantilla UTI (frontend). Sin dependencias nuevas.

**Spec:** [diseño P6b](../specs/2026-10-28-frontend-recursos-design.md) y spec v1.3 §8, §9.4, §12 y §13.

## Global Constraints

- La descarga exige la validación; sin ella, `409`.
- Una edición posterior anula la validación.
- El HTML exportado:
  - escapa todo texto;
  - no tiene recursos externos;
  - lleva al pie la asignatura, la clase o el momento con su fecha, los RA, la política de IA y la frase literal «Recurso generado con asistencia de IA y revisado por el docente».
- Lectores: pueden ver y descargar recursos validados; no pueden validar.

## Review Focus

1. **XSS en la exportación:** un ítem con `<script>` o `"onerror=` en su texto debe salir como texto.
2. **Validar y después editar:** la validación se anula y la descarga vuelve a dar `409`.
3. **Consulta de avance:** se detiene al terminar o al salir de la vista, sin dejar intervalos vivos.
4. **Momento restringido:** la vista Actividad muestra el motivo y no ofrece herramientas con IA.

---

### Task 1: Validación del docente (backend)

**Files:**
- Create `backend/app/db/migraciones/008_recurso_validacion.sql`.
- Modify `backend/app/recursos/servicio.py` and `backend/app/api/recursos.py`.
- Test `backend/tests/test_validacion_api.py`.

- Migración: añade a `recurso` las columnas `validado_por text` y `validado_en timestamptz`.
- `POST /asignaturas/{asig}/recursos/{id}/validar` (editor o dueño) con el cuerpo `{revision}`:
  - registra `validado_por` y `validado_en`;
  - si la revisión no coincide, responde `409`;
  - el detalle del recurso expone `validado` (bool), `validado_por` y `validado_en`.
- Un `PUT` que cambia el contenido pone `validado_por` y `validado_en` en `null`.
- [x] Pruebas:
  - `test_validar_y_detalle`;
  - `test_lector_no_valida`;
  - `test_editar_anula_validacion`;
  - `test_validar_revision_vieja_409`;
  - `test_otra_asignatura_404`.
- [x] Commit `feat(recursos): validación del docente`.

### Task 2: Exportación HTML (backend)

**Files:**
- Create `backend/app/exportar/html.py`.
- Modify `backend/app/recursos/servicio.py` and `backend/app/api/recursos.py`.
- Test `backend/tests/test_exportar_html.py`.

- `GET /asignaturas/{asig}/recursos/{id}/exportar?formato=html`:
  - responde `409` si el recurso no está validado y `422` si el formato no es `html`;
  - devuelve `text/html; charset=utf-8` con `Content-Disposition: attachment` y un nombre seguro (`<herramienta>-<ámbito>.html`).
- `exportar_html(recurso, contexto, asignatura) -> str` renderiza:
  - **cuestionario y simulacro:** ítems con sus opciones y una autocorrección en JavaScript en línea que, al elegir, muestra la justificación de esa opción;
  - **secciones** (ficha, repaso, guía, caso, guía final, sin IA): un recorrido genérico de diccionarios y listas, con títulos legibles y en orden;
  - el pie de §13.
- [x] Pruebas:
  - `test_html_cuestionario_autocorregible`: tiene `<script>`, sin `src=`, y las opciones;
  - `test_html_escapa_contenido`: un ítem con `<script>alert(1)</script>` sale como `&lt;script&gt;`;
  - `test_html_pie_y_politica`;
  - `test_html_secciones` (ficha y hoja de ruta);
  - `test_exportar_sin_validar_409`;
  - `test_exportar_validado_200_attachment`;
  - `test_formato_no_soportado_422`.
- [x] Commit `feat(exportar): HTML autónomo para Canvas`.

### Task 3: Cliente y vista Asignatura (frontend)

**Files:**
- Modify `frontend/src/api/{cliente,tipos}.ts`.
- Create `frontend/src/vistas/Asignatura.tsx`.
- Modify `frontend/src/App.tsx` and `frontend/src/vistas/Asignaturas.tsx`.

- Cliente:
  - `menu(aid)`;
  - `catalogo(aid, ambito, id)`;
  - `generar(aid, ambito, herramientas, opciones)`;
  - `trabajos(aid)`;
  - `recursos(aid)`;
  - `recurso(aid, rid)`;
  - `validar(aid, rid, revision)`;
  - `urlExportar(aid, rid)`.
- `Asignatura`:
  - semanas con clases (día, fecha, momento, contenidos y la insignia «N recursos» o «sin generar»);
  - al cierre de cada momento, la tarjeta «Cierra el Momento N»;
  - un botón «Hoja de ruta y guía final» para el ámbito asignatura;
  - un clic en una clase o en un momento abre la vista Actividad.
- `Asignaturas`: un clic en una fila abre `Asignatura`.
- [x] Commit `feat(frontend): vista de la asignatura por semana`.

### Task 4: Actividad, generación y progreso (frontend)

**Files:** Create `frontend/src/vistas/Actividad.tsx`, `frontend/src/vistas/Progreso.tsx`.

- `Actividad`:
  - el catálogo con casillas (recomendadas primero), insignias «con IA» o «sin IA» (sin IA son `hoja_ruta`, `autoevaluacion_*` y `lista_evidencia`) y la política de IA;
  - si `restringido`, un `Alert warning` con el motivo;
  - «Generar» y, al terminar, Progreso.
- `Progreso`:
  - consulta `trabajos(aid)` cada 4 s mientras haya trabajos activos de este pedido;
  - barra por estado (en cola, generando, verificando, revisando, listo, requiere revisión, error);
  - al quedar listos, un enlace a cada recurso;
  - limpia el intervalo al salir.
- [x] Commit `feat(frontend): elegir actividad, generar y seguir el avance`.

### Task 5: Revisar, validar y descargar (frontend) y Mis recursos

**Files:** Create `frontend/src/vistas/Recurso.tsx`, `frontend/src/vistas/Recursos.tsx`.

- `Recurso`:
  - el contenido en lectura (ítems con su clave marcada, o secciones), con las alertas por ítem o sección (`evidencia.verificaciones` y `veredictos`) y la insignia «Borrador» si `evidencia.borrador`;
  - «Validar recurso»: si hay alertas, un `Modal` pide confirmar; con 409, recarga;
  - una vez validado, «Descargar HTML para Canvas» (un enlace con `download`).
- `Recursos` («Mis recursos»): elegir la asignatura y ver la tabla de recursos (herramienta, ámbito, estado, validado y fecha), con apertura de cada uno.
- [x] Pruebas de navegador (API simulada):
  - elegir clase → actividad → generar → progreso → recurso;
  - el momento restringido muestra el aviso;
  - validar con alertas pide confirmación;
  - la descarga aparece solo validado;
  - Mis recursos abre un recurso.
- [x] `npm run check` y `npm run test:browser` → verde. Commit `feat(frontend): revisar, validar y descargar para Canvas`.

### Task 6: Prueba real

- [x] Con la API y el `worker` (servidor de IA), sobre la asignatura de prueba:
  - generar una herramienta sin IA (hoja de ruta) y una con IA (ficha de clase);
  - revisar, validar y descargar;
  - abrir el HTML descargado.
- [x] `progress.md` y commit `docs: P6b mis recursos`.
