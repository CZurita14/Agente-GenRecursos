# P4 · API y acceso

**Base aprobada:** hoja de ruta §7.5, spec v1.2 §2.1, §12, §14 y decisiones H1–H4.
**Objetivo:** conectar el lector y el núcleo mediante HTTP con acceso por docente.
**Arquitectura:** FastAPI, PostgreSQL para sesiones y permisos, cliente HTTP asíncrono para salud. Las rutas usan UUID de asignatura (H2). Solo Qwen local razona; la API no genera contenido.

## A1 · Base HTTP

Archivos: `backend/app/api/aplicacion.py`, `errores.py`, `backend/tests/test_api.py`, configuración y dependencias.

- [x] Crear fábrica `crear_app`, ejecutable sin arrancar workers ni migrar la BD.
- [x] Cargar perfiles desde la raíz del proyecto durante lifespan y cerrar el pool HTTP al salir.
- [x] `/salud`: consultar `/v1/models`, exigir modelo configurado y ventana de 8192; devolver 503 degradado sin excepciones ni direcciones internas si falla.
- [x] `API_ORIGEN` exacto, CORS con credenciales y rechazo de escrituras sin Origin coincidente (incluye ingreso, evita login CSRF).
- [x] Cierre por defecto de rutas privadas; A2 valida cookies con sesiones persistentes. Documentación HTTP desactivada.
- [x] Errores seguros para validación, sílabo ilegible y servidor no disponible. HTTPException conserva los códigos de cada ruta; 404/415/429 se probarán en A2–A3 cuando existan esas operaciones.
- [x] Pruebas con transporte simulado, sin gastar GPU.

Comando desde `backend`: `../.venv/Scripts/python.exe -m pytest tests/test_api.py -q`.
Arranque desde `backend`: `../.venv/Scripts/python.exe -m uvicorn app.api.aplicacion:crear_app --factory --host 127.0.0.1 --port 8001`.

## A2 · Autenticación persistente

Archivos: migración `004_auth.sql`, `app/auth/servicio.py` (retos y sesiones en un servicio cohesivo), `correo.py`, `app/api/auth.py`, `tests/test_auth.py`, `tests/test_correo_auth.py`. Operación local: [desarrollo-api](../../desarrollo-api.md).

- [x] Añadir tablas de retos y sesiones con caducidad y hashes; verificar bajo bloqueo de fila para que un código solo se use una vez.
- [x] Dominio exactamente `uti.edu.ec` o `indoamerica.edu.ec`, normalización y validación del correo antes de crear retos. Probar subdominios y dominios sufijados.
- [x] Código criptográfico de seis dígitos, HMAC con secreto del servidor, 10 min; máximo cinco intentos y bloqueo temporal 429 persistente. Reenviar no elimina el bloqueo.
- [x] Sesión aleatoria de alta entropía, hash persistido, 8 h inactividad/7 días absolutos; cookie HttpOnly/Secure/SameSite=Lax; logout revoca en servidor.
- [x] Rutas `/auth/codigo`, `/auth/verificar`, `/auth/salir`, `/auth/yo`; enviar respuesta de solicitud de código uniforme, validar Origin también antes de abrir sesión.
- [x] Transporte de correo inyectable; consola solo por configuración explícita de desarrollo. SMTP real depende de B4.
- [x] Probar expiración, reuso, cinco intentos, concurrencia, logout y cookie falsa antes de habilitar las rutas privadas.
- [x] Corregir revisión: no enumerar buzones rechazados por SMTP; entregar fuera del lock, conservar reto ante envío incierto; HTTPS obligatorio en producción y locks de emisión/verificación limitados a 2 s.

## A3 · Asignaturas y permisos

- [x] Leer PDF en subproceso con tiempo/memoria y tamaño limitados; eliminar archivo temporal en éxito y error. Usar `leer_silabo` de P2 y no persistir PDF.
- [x] Implementar `/silabos`, listado, menú, compartir y retirar acceso: UUID y dueño/editor/lector en cada operación. 415 tipo incorrecto; 422 ilegible.
- [x] Probar dos dueños, un editor y un lector; impedir lectura cruzada y escritura de lectores con la guardia `editar=True` que reutilizará A4.
- [x] Forzar retirada/degradación mientras una autorización espera; bloqueo de asignatura y lectura posterior de permiso bajo READ COMMITTED.
- [x] Serializar primeras subidas por dueño+código con advisory lock para comparar contra la versión realmente anterior.
- [x] Acotar recepción del cuerpo a 30 s y lector a 20 s/512 MB; limpiar temporales y liberar cupos también en desconexión. Tamaño 10 MB contado sobre bytes reales; dos cargas simultáneas por proceso API.
- [x] Integración HTTP con ambos PDF reales: Datos 6 semanas/11 sesiones; TIC 4/6. Sin IA ni correos reales.

Archivos: `app/api/asignaturas.py`, `app/asignaturas/servicio.py`, `app/silabo/aislado.py`, migración `005_asignatura_acceso.sql`; pruebas `test_asignaturas_api.py`, `test_asignaturas_concurrencia.py`, `test_pdf_recepcion.py`, `test_lector_aislado.py`.

Decisión de transporte: `POST /silabos` usa cuerpo PDF binario, no multipart, para contar y limitar la recepción antes de cualquier parseo. El cliente no elige dueño, nombre de archivo ni UUID de asignatura. JobObject comprobado en Windows; RLIMIT_AS se validará en el despliegue Linux de P7.

## A4 · Generación y recursos

- [x] Conectar `crear_trabajos` y catálogo de workers disponibles. Lectores consultan, dueños y editores generan.
- [x] Listar trabajos/recursos filtrados por asignatura, actualizar recursos con historial de ediciones y control de concurrencia.
- [x] Probar que UUID de recurso o trabajo de otra asignatura nunca eluda A9.
- [x] Respetar perfil de dificultad elegido, snapshot del trabajo y paginación acotada. No devolver parámetros privados ni errores internos del worker.
- [x] PUT con contenido idéntico es una operación sin cambios: conserva estado, evidencia y revisión. Una modificación real incrementa revisión, conserva evidencia original con `evidencia_vigente=false` y queda `requiere_revision`.
- [x] Historial operativo transaccional con autor, antes/después y `uso_mejora=false`. No se activa memoria ni entrenamiento de Fase 2.
- [x] Validación estricta recursiva contra snapshot: rechazar IDs/RA/contenidos ajenos y campos extra. Preguntas de edición con máximo 1000 caracteres antes de la comparación por pares. Mantener advertencias deterministas sin inventar aprobación IA.
- [x] JSON limitado a 1 MiB/30 s antes del parser, tras comprobar sesión/origen. La subida PDF mantiene sus límites independientes.

Archivos: `app/api/recursos.py`, `cuerpo.py`, `app/recursos/servicio.py`, `validacion.py`, migración `006_recurso_edicion.sql`; extensión aditiva del perfil en `SolicitudGeneracion` y en el despacho del worker. Pruebas principales: `test_generacion_api.py`, `test_edicion_validacion.py`, `test_cuerpo_json.py`.

El catálogo ofrece solo los dos workers disponibles (P1); ámbitos momento/asignatura devuelven catálogo vacío hasta P3. Las ediciones manuales no llaman al modelo, no aprueban exportación y no reescriben los veredictos originales. El chat de regeneración con nueva revisión IA sigue en P5.

## A5 · Límites y consumo

- [ ] Límites persistentes por correo/IP, sin confiar en cabeceras proxy salvo proxy configurado.
- [ ] Registro de accesos sin textos de sílabos, prompts ni cuerpos. Consumo agregado solo para administradores configurados.
- [ ] Preparar aviso de privacidad para revisión institucional; no activar recolección para entrenamiento por defecto.

## Puertas y cierre

B4 impide correo real, no pruebas ni desarrollo. B3 mantiene pendiente la plantilla académica de P3. La lista de administradores y el aviso se revisan antes del despliegue. Cada unidad requiere pruebas y revisión de código; no declarar P4 cerrado con solo A1. Conservar apilado de los PR #1 y #2; no fusionarlos automáticamente.
