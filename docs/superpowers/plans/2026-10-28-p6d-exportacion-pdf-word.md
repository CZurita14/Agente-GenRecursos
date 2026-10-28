# P6d · Exportación PDF y Word — diseño propuesto y plan

**Estado:** implementación, revisión visual y regresión final completadas. Commit `e6dffb8`, publicado en [PR #10](https://github.com/CZurita14/Agente-GenRecursos/pull/10) sobre `p6/edicion`; sin fusionar.

**Objetivo:** descargar recursos validados como PDF para impresión y DOCX editable, además del HTML existente (§13 del spec v1.3).

**Arquitectura:** mantener la ruta de exportación, los permisos y la comprobación de validación en `ServicioRecursos`. Cada renderizador recibe una copia del recurso y su contexto histórico y devuelve bytes en memoria. Reutilizar `presentar()` para texto, listas, tablas y grupos; los cuestionarios requieren una representación estática propia.

**Tecnologías propuestas:** `python-docx` para DOCX y ReportLab para PDF; renderizador local de fórmulas con sintaxis restringida, sin ejecutar LaTeX externo ni obtener recursos de red. Verificar soporte y licencias de fuentes antes de incorporarlas. Registrar límites compatibles de las nuevas dependencias tras probarlas en el entorno del proyecto.

## Diseño para revisión

1. Conservar `GET /asignaturas/{aid}/recursos/{rid}/exportar?formato=html`; añadir `pdf` y `docx`. Formato desconocido: 422. Recurso sin validar: 409 para los tres formatos. Autorización y pertenencia antes de renderizar.
2. Añadir enlaces «Descargar PDF» y «Descargar Word» junto al HTML, únicamente después de validar. Mientras haya borrador abierto, pedir guardar o cancelar antes de descargar para evitar confundirlo con la versión persistida.
3. Encabezado con nombre de herramienta, asignatura y ámbito. Conservar el orden y los títulos de la presentación actual. Al final: asignatura, clase/ámbito, fecha, RA, política de IA y la leyenda exigida por §13. Usar el contexto histórico del recurso, no reconstruirlo con una versión posterior del sílabo.
4. Cuestionarios/simulacros: preguntas y opciones sin marcar la respuesta en el cuerpo; sección final «Respuestas y justificaciones» para conservar la utilidad de autoestudio del HTML. Esta sección queda identificada y comienza en página nueva. No incluir ids internos, evidencia del coordinador ni razonamientos internos del modelo.
5. PDF A4 con márgenes, fuente Unicode incorporada, salto de línea y paginación. Tablas con cabecera repetida y celdas ajustables. DOCX con estilos de título, texto y tablas editables. No prometer formato institucional definitivo: sigue pendiente B3/H8.
6. Fórmulas: reconocer delimitadores explícitos, convertir la notación admitida a imágenes locales e incorporarlas en ambos formatos (§9). Texto alternativo con la expresión original en DOCX. Si una fórmula no puede representarse, informar un error controlado de exportación; no sustituirla silenciosamente por una fórmula incorrecta. Comprobar fracciones, raíces, índices, potencias y letras griegas con ejemplos de los recursos. La cobertura del dialecto matemático debe quedar documentada.
7. No usar HTML del recurso como instrucciones de renderizado ni resolver URLs, enlaces de archivos, imágenes o campos de Word recibidos del modelo. Los textos se insertan como datos; escapar el marcado que interprete la biblioteca PDF. Limitar longitud y dimensiones de las fórmulas antes de procesarlas. Generar en memoria y no conservar documentos con contenido académico en disco en producción.

## Alternativas consideradas

- **Recomendada: renderizadores nativos PDF/DOCX.** Menos dependencias de servicios externos y conserva la edición real de tablas y párrafos en Word. Requiere comprobar paginación y mantener dos adaptadores pequeños.
- HTML → navegador para PDF y DOCX nativo. Reutiliza CSS, pero añade Chromium en producción y exige bloquear red y acceso a archivos del convertidor.
- DOCX → LibreOffice → PDF. Acerca la apariencia entre documentos, pero requiere una aplicación externa y aislamiento de sus conversiones concurrentes.

## Tareas y verificación

### T1 · Contratos de documento y fórmulas

Archivos: crear `backend/app/exportar/documento.py`, `backend/app/exportar/formulas.py`, `backend/tests/test_exportar_documento.py` y `backend/tests/test_exportar_formulas.py`; modificar `backend/pyproject.toml`.

- [ ] Escribir pruebas de orden, metadatos históricos y separación de respuestas; deben fallar antes de implementar.
- [ ] Extraer una estructura común de documento sin modificar el contenido persistido ni las rutas editables.
- [ ] Probar fórmulas válidas, inválidas y sobredimensionadas, incluidos caracteres Unicode y texto con apariencia de HTML/URL.
- [ ] Implementar el renderizado local de fórmulas y errores controlados sin publicar expresiones en logs.

### T2 · Renderizadores PDF y DOCX

Archivos: crear `backend/app/exportar/pdf.py`, `backend/app/exportar/docx.py` y `backend/tests/test_exportar_documentos.py`.

- [ ] Escribir pruebas que abran los bytes con lectores independientes: PDF con `pdfplumber`, DOCX con ZIP/XML y `python-docx`.
- [ ] Cubrir cuestionario, ficha de clase, herramienta sin IA con tablas, grupos anidados, caracteres españoles, Unicode, textos extensos y varias páginas.
- [ ] Implementar título, bloques y pie comunes; incluir imágenes de fórmulas sin enlaces externos.
- [ ] Verificar que las tablas de Word siguen siendo tablas y que las respuestas están separadas de las preguntas.
- [ ] Inspeccionar visualmente PDF y DOCX renderizado: sin recortes, cabeceras huérfanas ni superposiciones. Conservar muestras sintéticas de prueba fuera de los recursos del usuario.

### T3 · Servicio y HTTP

Archivos: modificar `backend/app/recursos/servicio.py`, `backend/app/api/recursos.py`, `backend/tests/test_exportar_html.py`; crear `backend/tests/test_exportar_formatos_api.py`.

- [ ] Parametrizar pruebas para HTML/PDF/DOCX: validado 200; sin validar 409; sin sesión 401; usuario ajeno y recurso de otra asignatura rechazados según el contrato vigente.
- [ ] Cambiar la prueba que hoy rechaza PDF por un formato realmente no soportado, por ejemplo `qti`.
- [ ] Mantener HTML por defecto y su contrato existente; seleccionar renderizador mediante lista cerrada.
- [ ] Enviar MIME correcto, extensión segura, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` y política de caché privada/no-store coherente con el middleware.
- [ ] Probar que editar invalida las tres exportaciones y que volver a validar exporta el texto actualizado.
- [ ] Mantener una instantánea coherente del recurso y su contexto durante la descarga; evitar abrir procesos externos dentro de una transacción.

### T4 · Descargas en frontend

Archivos: modificar `frontend/src/api/cliente.ts`, `frontend/src/vistas/Recurso.tsx`, `frontend/tests/api.test.ts` y `frontend/tests/browser.test.mjs`.

- [ ] Probar URL por formato y compatibilidad del valor por defecto `html`.
- [ ] Añadir formatos tipados y tres enlaces accesibles; conservar el enlace HTML para Canvas.
- [ ] Probar que no aparecen descargas sin validar, que un lector autorizado descarga recursos validados y que no se ofrece descarga de un borrador sin guardar.

### T5 · Cierre

- [ ] Ejecutar pruebas nuevas y regresión de exportación/edición/permisos, seguidas de la suite backend cuando el entorno de BD esté disponible.
- [ ] Ejecutar `npm run check` y `npm run test:browser` en `frontend`.
- [ ] Revisar autorización, inyección de marcado, límites de fórmulas y ausencia de dependencias externas en los documentos.
- [ ] Registrar pruebas ejecutadas y limitaciones reales en `progress.md`; no reutilizar cifras históricas como resultados nuevos.
- [ ] Crear rama dependiente de P6c para implementación y PR sobre `p6/edicion`, sin fusionar la cadena existente.

## Decisión pendiente

El usuario aprobó el diseño. Se implementaron renderizadores y proyección compartida en `documento.py` (en lugar de módulos separados), integración HTTP y enlaces frontend. Las fórmulas admiten el dialecto MathText, no LaTeX completo; las expresiones no soportadas producen 422. Se incorporan fuentes DejaVu distribuidas con Matplotlib para PDF.

Verificación inicial: backend sin servidor IA real, 654 pruebas pasan y 3 deseleccionadas; exportación: 16 pasan. Cierre posterior: cobertura del lector, 401, 409 y pertenencia a otra asignatura añadida; 19 pruebas de exportación pasan antes de incorporar límites de fórmulas y regresión de paginación. Frontend: typecheck, build, 21 unitarias y 16 de navegador pasan (incluido lector y borrador sin guardar).

QA visual: `python -m tests.revisar_exportacion ../.superpowers/p6d-qa` desde backend genera tres ejemplos de cada formato, sin IA ni BD. Se revisaron 16 páginas renderizadas: cuestionario con fórmulas, ficha con grupos y listas, y hoja de ruta con tablas largas. Para DOCX se utilizó Word local en modo oculto y solo lectura: el renderizador de la habilidad no dispone de LibreOffice en este equipo. Corregidos opciones huérfanas en PDF, numeración continuada entre listas en DOCX y estilos de párrafo. Muestras locales ignoradas por Git; no se incluyen en producción.

Resultado final: **663 pruebas backend pasan, 3 deseleccionadas** (`pytest -q -m "not servidor"`); **21 unitarias frontend, 16 de navegador**, typecheck y build pasan. No se ha integrado plantilla institucional ni ampliado MathText a LaTeX completo.

### Aceptación final

- [x] T1: proyección de contenido y fórmulas locales acotadas, sin ejecutar LaTeX ni obtener recursos externos.
- [x] T2: PDF y DOCX con texto, grupos, listas y tablas; revisión visual de seis muestras (16 páginas), con correcciones verificadas.
- [x] T3: formatos HTTP, adjuntos y caché; autorización, validación, invalidación tras editar, sesión y pertenencia comprobadas.
- [x] T4: enlaces tipados, HTML por defecto, descarga del lector y bloqueo durante edición, con pruebas de navegador.
- [x] T5: regresión completa y resultados registrados; rama dependiente preparada para PR.

Las casillas anteriores a este resumen corresponden al desglose de diseño original, no a trabajo pendiente adicional. Los renderizadores y fórmulas se consolidaron en `documento.py`; las pruebas, en `test_exportar_documentos.py`. El único uso de Word instalado fue QA local: no es dependencia de producción.
