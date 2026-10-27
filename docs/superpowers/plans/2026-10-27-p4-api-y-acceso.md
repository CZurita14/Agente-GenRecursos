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
- [x] Cierre por defecto de rutas privadas; no reconocer cookies hasta A2. Documentación HTTP desactivada.
- [x] Errores seguros para validación, sílabo ilegible y servidor no disponible. HTTPException conserva los códigos de cada ruta; 404/415/429 se probarán en A2–A3 cuando existan esas operaciones.
- [x] Pruebas con transporte simulado, sin gastar GPU.

Comando desde `backend`: `../.venv/Scripts/python.exe -m pytest tests/test_api.py -q`.
Arranque desde `backend`: `../.venv/Scripts/python.exe -m uvicorn app.api.aplicacion:crear_app --factory --host 127.0.0.1 --port 8001`.

## A2 · Autenticación persistente (siguiente unidad)

Archivos previstos: migración `004_auth.sql`, `app/auth/codigos.py`, `sesiones.py`, `correo.py`, `app/api/auth.py`, `tests/test_auth.py`.

- [ ] Añadir tablas de retos y sesiones con caducidad y hashes; verificar bajo bloqueo de fila para que un código solo se use una vez.
- [ ] Dominio exactamente `uti.edu.ec` o `indoamerica.edu.ec`, normalización y validación del correo antes de crear retos. Probar subdominios y dominios sufijados.
- [ ] Código criptográfico de seis dígitos, HMAC con secreto del servidor, 10 min; máximo cinco intentos y bloqueo temporal 429 persistente. Reenviar no elimina el bloqueo.
- [ ] Sesión aleatoria de alta entropía, hash persistido, 8 h inactividad/7 días absolutos; cookie HttpOnly/Secure/SameSite=Lax; logout revoca en servidor.
- [ ] Rutas `/auth/codigo`, `/auth/verificar`, `/auth/salir`, `/auth/yo`; enviar respuesta de solicitud de código uniforme, validar Origin también antes de abrir sesión.
- [ ] Transporte de correo inyectable; consola solo por configuración explícita de desarrollo. SMTP real depende de B4.
- [ ] Probar expiración, reuso, cinco intentos, concurrencia, logout y cookie falsa antes de habilitar las rutas privadas.

## A3 · Asignaturas y permisos

- [ ] Leer PDF en subproceso con tiempo/memoria y tamaño limitados; eliminar archivo temporal en éxito y error. Usar `leer_silabo` de P2 y no persistir PDF.
- [ ] Implementar `/silabos`, listado, menú, compartir y retirar acceso: UUID y dueño/editor/lector en cada operación. 415 tipo incorrecto; 422 ilegible.
- [ ] Probar dos dueños, un editor y un lector; impedir lectura cruzada y escritura de lectores.

## A4 · Generación y recursos

- [ ] Conectar `crear_trabajos` y catálogo de workers disponibles. Lectores consultan, dueños y editores generan.
- [ ] Listar trabajos/recursos filtrados por asignatura, actualizar recursos con historial de ediciones y control de concurrencia.
- [ ] Probar que UUID de recurso o trabajo de otra asignatura nunca eluda A9.

## A5 · Límites y consumo

- [ ] Límites persistentes por correo/IP, sin confiar en cabeceras proxy salvo proxy configurado.
- [ ] Registro de accesos sin textos de sílabos, prompts ni cuerpos. Consumo agregado solo para administradores configurados.
- [ ] Preparar aviso de privacidad para revisión institucional; no activar recolección para entrenamiento por defecto.

## Puertas y cierre

B4 impide correo real, no pruebas ni desarrollo. B3 mantiene pendiente la plantilla académica de P3. La lista de administradores y el aviso se revisan antes del despliegue. Cada unidad requiere pruebas y revisión de código; no declarar P4 cerrado con solo A1. Conservar apilado de los PR #1 y #2; no fusionarlos automáticamente.
