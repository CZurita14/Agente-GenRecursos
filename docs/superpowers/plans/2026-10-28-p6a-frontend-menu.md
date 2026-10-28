# P6a · Frontend: menú principal — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir sobre la plantilla UTI el menú aprobado (opción B), conectado a la API del P4. Incluye el ingreso con código, el inicio con «Generar herramientas» y «Perfil docente» (este último en espera), la subida del sílabo y la lista de asignaturas.

**Architecture:** `frontend/` es una copia de la plantilla. Un cliente HTTP mínimo (`src/api/`) habla con la API a través del proxy `/api` de Vite. Un hook de sesión decide si se muestra el ingreso o la aplicación. La navegación es un estado (`vista`) que maneja la `Navbar` de la plantilla. Las vistas viven en `src/vistas/`.

**Tech Stack:** React 18, TypeScript estricto, Vite 8, Tailwind 4, lucide-react y Playwright (de la plantilla).

**Spec:** [diseño del menú](../specs/2026-10-28-frontend-menu-design.md) y spec v1.3 §2.1 (acceso), §8.1 (menú) y §12 (API).

## Global Constraints

- Sin dependencias nuevas.
- Sesión solo en la cookie HttpOnly; nada de tokens ni correos en `localStorage` (la preferencia de tema de la plantilla sí se queda).
- Todas las llamadas usan `credentials: "include"` y la base `/api`.
- Textos de la interfaz en español.
- Se conservan las comprobaciones de la plantilla: `npm run check` (tipos, pruebas y compilación) y `npm run test:browser`.

## Review Focus

1. **Sesión vencida a mitad del uso:** cualquier `401` devuelve al ingreso sin romper la pantalla.
2. **Perfil docente:** no se puede activar (ni con clic ni con teclado) y anuncia «en espera» a los lectores de pantalla.
3. **Errores de la API** (`422` con sílabo ilegible, `429` con `Retry-After`, `503`): mensaje claro, sin detalles internos.
4. **Móvil:** el menú colapsa (Navbar de la plantilla) y las dos tarjetas se apilan.

---

### Task 1: Proyecto `frontend/` desde la plantilla

**Files:** `frontend/**` (copia), `.gitignore`.

- [ ] Copiar la plantilla sin `.git`, `node_modules` ni `dist`. Nombre `genrecursos-frontend` en `package.json`; `npm install`.
- [ ] `BRAND_CONFIG`: `appTitle = "Recursos de estudio"`, `appSubtitle = "Generador de recursos · UTI"`.
- [ ] `vite.config.ts`: proxy `/api` → `http://127.0.0.1:8001` (reescribe el prefijo).
- [ ] Eliminar `src/examples/` y adaptar las pruebas de navegador de la galería (se reescriben en la T5).
- [ ] `.gitignore`: `frontend/node_modules/`, `frontend/dist/`.
- [ ] `npm run check` → verde. Commit `feat(frontend): proyecto desde la plantilla UTI`.

### Task 2: Cliente de la API

**Files:** Create `frontend/src/api/cliente.ts`, `frontend/src/api/tipos.ts`; Test `frontend/tests/api.test.ts`.

**Interfaces:**
- `class ErrorApi extends Error { estado: number; reintentar?: number }`.
- `pedir<T>(ruta, opciones?) => Promise<T>`: usa `/api`, `credentials: "include"`, JSON por defecto. En un error, lanza `ErrorApi` con un mensaje en español según el estado:
  - 401: «Tu sesión terminó»;
  - 403: «No tienes permiso»;
  - 413: «El archivo supera 10 MB»;
  - 415: «Solo se aceptan PDF»;
  - 422: el `detail` de la API si es texto;
  - 429: «Demasiados intentos; espera N s»;
  - 503: «Servicio no disponible».
- Funciones: `pedirCodigo(correo)`, `verificarCodigo(correo, codigo)`, `yo()`, `salir()`, `subirSilabo(archivo: File)` (cuerpo binario, `Content-Type: application/pdf`) y `asignaturas()`.
- Tipos: `Usuario { correo; rol }`, `AsignaturaResumen` (lo que devuelve `GET /asignaturas`) y `SilaboSubido { id; agente; menu; clases_cambiadas }`.

- [ ] Pruebas con `fetch` simulado:
  - base, credenciales y método;
  - el cuerpo binario del PDF;
  - un mensaje por estado;
  - `Retry-After`.
- [ ] Commit `feat(frontend): cliente de la API`.

### Task 3: Sesión e ingreso con código

**Files:** Create `frontend/src/sesion/useSesion.ts`, `frontend/src/vistas/Ingreso.tsx`; Modify `frontend/src/App.tsx`.

- `useSesion()`: `{ usuario, cargando, ingresar(correo, codigo), salir(), refrescar() }`. Al montar llama a `yo()`; un `401` deja `usuario = null`.
- `Ingreso`:
  - paso 1, el correo institucional (aviso: `@uti.edu.ec` o `@indoamerica.edu.ec`);
  - paso 2, el código de 6 dígitos;
  - errores con `Alert`;
  - «Volver a pedir el código».
- `App`: muestra `Ingreso` sin sesión y el menú con sesión. Un `ErrorApi` 401 en cualquier vista lleva al ingreso.
- [ ] Commit `feat(frontend): ingreso con código y sesión`.

### Task 4: Menú e inicio (opción B)

**Files:** Create `frontend/src/vistas/Inicio.tsx`, `frontend/src/vistas/Proximamente.tsx`; Modify `frontend/src/App.tsx`.

- `AppLayout` y `Navbar` con los items `inicio`, `asignaturas` y `recursos`; en `actions`, el correo y el botón «Salir». El tema lo maneja la plantilla.
- `Inicio`: el título «¿Qué quieres hacer hoy?» y dos `Card`.
  - **Generar herramientas:** borde de acento, los pasos 1–3 y el botón «Empezar», que lleva a la vista `generar`.
  - **Perfil docente:** `Badge tone="warning"` «En espera», estilo atenuado, `aria-disabled="true"`, sin botón, con el texto de que se activará con la documentación.
  - En el móvil, las tarjetas se apilan.
- `Proximamente`: para «Mis recursos», con un texto que diga qué llegará.
- [ ] Commit `feat(frontend): menú principal e inicio`.

### Task 5: Subir sílabo y mis asignaturas

**Files:** Create `frontend/src/vistas/Generar.tsx`, `frontend/src/vistas/Asignaturas.tsx`.

- `Generar`:
  - `DropZone` (`accept=".pdf,application/pdf"`, `maxSize = 10 MB`) y el botón «Subir sílabo» con `loading`;
  - al terminar, un `Alert success` con el agente asignado y las semanas y clases del menú devuelto;
  - un enlace a «Mis asignaturas»;
  - cada error de la API con su mensaje.
- `Asignaturas`: una `DataTable` (`caption` «Mis asignaturas») con nombre, código, rol y versión, y un estado vacío que invite a subir el sílabo.
- [ ] Pruebas de navegador (`tests/browser.test.mjs`, API simulada con `page.route`):
  - ingreso en dos pasos;
  - el menú tiene 3 pestañas;
  - el perfil docente está desactivado;
  - «Empezar» lleva a «Generar»;
  - subir un PDF muestra el resumen;
  - un `401` devuelve al ingreso;
  - en el móvil se ve el menú colapsado.
- [ ] `npm run check` y `npm run test:browser` → verde. Commit `feat(frontend): subir sílabo y mis asignaturas`.

### Task 6: Prueba manual con la API real

- [ ] Levantar la API (`ENTORNO=desarrollo`, `SMTP_MODO=consola`, `API_ORIGEN=http://localhost:5173`) y `npm run dev`.
- [ ] En el navegador integrado: ingresar con el código que imprime la consola, subir el PDF de Datos y ver la asignatura. Sin datos personales en capturas ni en el registro.
- [ ] Documentar el arranque en `frontend/README.md` y `progress.md`. Commit `docs: frontend, primera entrega del menú`.
