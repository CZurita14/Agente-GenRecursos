# P7 · Despliegue y operación — diseño para aprobación

**Estado:** propuesta basada en el código actual. No se ha modificado ni desplegado infraestructura.

**Objetivo:** instalar la aplicación desde cero y demostrar operación, respaldo y restauración antes de solicitar la puesta en marcha institucional.

**Base:** spec v1.3 §3.6, §5.1, §14 y criterio 13; hoja de ruta P7 D1–D4. Rama base: P5 (`codex/p5-chat`, PR #11). PostgreSQL y API/Qwen funcionan localmente; Docker está disponible (comprobado sin modificar contenedores).

## Diseño recomendado

### Servicios y aislamiento

Cinco servicios permanentes en un Compose de despliegue separado: `db`, `api`, `worker`, `web` y `proxy`. Un proceso de migración de una sola ejecución precede a API y worker. El Qwen institucional queda externo a Compose y nunca se publica a través del proxy.

- `db`: volumen persistente propio, sin puerto publicado al host. Conservar la base e imagen compatibles con PostgreSQL 18 utilizado en desarrollo; no cambiar versión mayor ni reutilizar automáticamente el volumen local.
- `api` y `worker`: misma imagen Python, distintos comandos; usuario no privilegiado, código de solo lectura y temporales acotados. Incluir perfiles de `agentes/`, catálogo y documentos que la aplicación lee en ejecución; excluir `.env`, sílabos reales, propuestas, bases locales y repositorios auxiliares. La lectura de PDF debe seguir funcionando en su subproceso limitado.
- `web`: compilación reproducible con `npm ci`, sirve únicamente los artefactos de Vite en red privada.
- `proxy`: único punto publicado; HTTPS y redirección desde HTTP. `/api/` elimina ese prefijo y dirige a API; `/` dirige a web. No publicar directamente API, web, worker o BD.

Mantener intacto el Compose raíz de desarrollo. Usar nombre de proyecto y volumen diferentes en las pruebas de instalación. No ejecutar comandos de limpieza global de Docker ni tocar `genrecursos-db`.

### Arranque, configuración y salud

1. Validar configuración y secretos sin imprimirlos. En producción: origen HTTPS exacto, secreto fuerte, SMTP configurado, administradores y revisión del aviso. No habilitar códigos en consola como sustituto de SMTP institucional.
2. Esperar BD saludable y ejecutar migraciones una vez, con exclusión mutua para impedir dos migradores simultáneos. Evitar que workers antiguos continúen activos mientras cambia el esquema.
3. Arrancar API y worker con el mismo código; luego web/proxy. El worker no debe competir ejecutando migraciones simultáneamente con el proceso inicial.
4. Separar salud de proceso, preparación y dependencia IA. `/salud` conserva su diagnóstico actual de Qwen y ventana de 8192 tokens. Una comprobación de preparación interna verifica BD/esquema y carga de perfiles sin exigir que Qwen esté disponible; así siguen operativas consulta, edición y descarga si IA está en espera. No exponer detalles de conexiones ni credenciales en salud.
5. El worker informa latido de su bucle; un proceso vivo que dejó de consumir no se considera saludable indefinidamente. La salud debe tolerar una llamada de revisión legítima y distinguirla de un consumidor detenido, sin reiniciarlo durante el plazo permitido.

La concurrencia de despliegue empieza conservadora y configurable; TI confirma el total admitido por Qwen antes de subirla. Documentar que multiplicar réplicas de workers también multiplica peticiones al modelo: el límite por proceso no equivale a un límite global.

### HTTPS, proxy y límites

Certificado y clave proporcionados por TI y montados solo en el proxy. Para pruebas locales, certificado autofirmado de prueba y origen propio; nunca confundirlo con un certificado institucional válido.

Configurar TLS, HSTS para el host de producción, cabeceras de seguridad y CSP compatible con la aplicación. No aplicar políticas de caché públicas a respuestas autenticadas. El límite de subida será coherente con los **10 MiB actuales**, no con los 50 MB de una versión anterior del plan; API sigue contando bytes y tiempos reales. JSON conserva su límite propio de 1 MiB.

El proxy sobrescribe cabeceras de identidad reenviadas con la IP realmente observada. Uvicorn no interpreta esas cabeceras por su cuenta: el código existente de identidad usa una lista explícita de proxies. Confiar solo en la dirección del proxy dentro de una red dedicada; no aceptar `0.0.0.0/0` ni toda la red institucional. Si TI añade otro balanceador, revisar la cadena antes de habilitarla.

Aplicar cuotas en el borde sin sustituir los límites persistentes por usuario de la API. No registrar URI/query completas, cuerpos, códigos, cookies ni correos en logs del proxy. Conservar diagnóstico operativo por operación saneada/estado, sin rutas con identificadores. No reenviar rutas internas de salud o administración de infraestructura al exterior por comodidad.

### Respaldo, restauración y actualización

Herramientas de operación reproducibles, utilizables desde Windows y Linux, que invoquen Docker con argumentos separados. Contraseñas fuera de argumentos de comandos y logs.

- Respaldo PostgreSQL en formato custom, guardado atómicamente y con comprobación de integridad. Documentar cifrado, acceso restringido y copia externa; el plazo lo define la institución.
- Verificación de restauración en una **base nueva aislada**: jamás restaurar una prueba encima de la base operativa. Comprobar tablas, migraciones y datos sintéticos tras restaurar; borrar únicamente artefactos del proyecto de prueba identificado.
- Manual de actualización: ventana de mantenimiento, detener consumidores anteriores, respaldo, migración, arranque coordinado y comprobación de salud. No prometer rollback de imagen si hubo un cambio incompatible del esquema; documentar recuperación desde un respaldo comprobado.
- Documentar rotación de secretos/certificados, caducidad de sesiones, logs, disco, colas en espera y purga de auditoría. No borrar historial académico sin una política institucional aprobada.

## Alternativas consideradas

1. **Compose separado en servidor institucional — recomendado.** Aprovecha la infraestructura existente y permite probar instalación/restauración de forma aislada.
2. Procesos instalados directamente y servicios del sistema. Menos contenedores, pero introduce más diferencias entre desarrollo e instalación limpia y hace más delicada la recuperación.
3. Kubernetes. No se justifica por el alcance actual; exigiría una plataforma y operación que TI todavía no ha confirmado.

## Secuencia de implementación después de aprobar

### D1 · Imágenes y Compose

Crear `infra/Dockerfile.backend`, `infra/Dockerfile.web`, `infra/compose.yaml`, `.dockerignore` y ejemplo de entorno sin secretos. Añadir comando explícito de migración y verificaciones de configuración/salud; probar PDF, fórmulas y perfiles dentro de la imagen Linux. Verificar dependencias reproducibles y licencias de fuentes incluidas.

Aceptación: construir desde checkout limpio, arrancar en proyecto aislado, migraciones completas y segunda ejecución sin cambios. No puertos internos públicos ni secretos en imagen. Datos de desarrollo intactos.

### D2 · Proxy

Crear configuración nginx de TLS/proxy/web y pruebas con certificados locales desechables. Comprobar rutas, origen y cookie Secure/HttpOnly/SameSite, rechazo de suplantación de IP, límites de carga, caché y cabeceras. Revisar CSP contra la interfaz real y la descarga HTML, sin ejecutar HTML recibido del modelo en el origen de la aplicación.

### D3 · Instalación limpia y recuperación

Crear herramienta y manual de operación (`infra/operar.py`, `docs/operacion.md` o división equivalente), con pruebas de argumentos y de fallo seguro. Ejecutar instalación en volumen de prueba vacío, respaldo y restauración real en otra base de prueba, comparar datos y registrar resultados. La máquina de desarrollo con contenedores nuevos demuestra instalación reproducible, no equivale a probar un servidor institucional distinto.

### D4 · Entrega a TI, sin despliegue automático

Preparar ficha con requisitos, variables, redes, puertos, dominio/certificados, SMTP, administradores, capacidad de IA, respaldo y mantenimiento. Entregar comandos revisables. No enviar mensajes a TI ni desplegar en su servidor sin instrucción expresa y datos de acceso autorizados.

### Verificación y cierre técnico

Pruebas de configuración y operación; regresión backend/frontend cuando se modifique código; integración real de Compose/proxy/BD con datos sintéticos. Comprobar que Qwen caído deja API de consulta utilizable y trabajos en espera, sin exponer el servidor de IA. Actualizar `progress.md`, guardar commits y abrir PR sobre P5 sin fusionar.

## Resultado de la instalación aislada (2026-10-28)

Proyecto `genrecursos-p7-prueba` con volumen, red y puertos propios (18080/18443), certificado autofirmado desechable, datos sintéticos (fixture del sílabo y una sesión de prueba) y Qwen apuntando a una dirección inalcanzable (TEST-NET) a propósito. `genrecursos-db` de desarrollo no se tocó; el proyecto de prueba se eliminó al terminar.

Defectos encontrados al arrancar de verdad y corregidos, cada uno con prueba de regresión en `test_infra_config.py` / `test_operar_infra.py`:

1. `.dockerignore` excluía `frontend/public`: la imagen web quedaba sin favicon ni logo UTI.
2. `tmpfs: [/tmp:size=…,mode=1777]` en estilo de flujo YAML: la coma partía la entrada y Docker rechazaba `web` y `proxy`.
3. nginx con raíz de solo lectura intentaba crear `fastcgi/uwsgi/scgi_temp` en `/var/cache/nginx`: `web` no arrancaba. Todos los temporales van a `/tmp`.
4. `api` o `web` podían tomar la IP fija del proxy al unirse antes a `borde` («Address already in use»). Nuevo `RANGO_DINAMICO` (`ip_range`) que excluye `IP_PROXY`, validado por `operar.py`.
5. El proxy solo estaba en redes internas y Docker **no publicaba sus puertos**: el sitio era inalcanzable. Nueva red `publica`, exclusiva del proxy.

Además, tres pruebas de `test_api.py` usaban un POST sobre `/salud`, que ahora solo es público por GET/HEAD; pasan a una ruta pública por POST.

Verificado (24/24 por el proxy HTTPS, validando el certificado de prueba): redirección 308 con destino fijo; cabeceras HSTS/CSP/X-Frame-Options/nosniff; favicon y logo; `/api/salud` y `/api/salud/listo` no se publican; 401 sin caché; subida de 11 MiB rechazada en el borde (413); sesión, asignaturas y menú; hoja de ruta generada, validada y descargada en HTML, PDF y DOCX desde la imagen Linux; ficha con IA aceptada (202) y en espera mientras consultas y descargas siguen respondiendo. `X-Forwarded-For` falsificado ignorado (14 accesos, un solo seudónimo de IP). Migración repetida sin cambios. Worker sano con la IA caída. Respaldo con manifiesto SHA-256; restauración en base nueva con conteos y hash de contenido idénticos; rechaza restaurar sobre una base existente o la operativa. Reinicio completo conserva datos e IP del proxy. Suite backend: 852 pasan / 4 deseleccionadas (servidor real).

No probado aquí: certificado institucional, SMTP real, Qwen real dentro de Compose, servidor de TI (B4/B5/B6).

## Puertas que este trabajo no puede sustituir

- B3/H8: plantilla académica; H7 y criterio de dificultad acordados con el área académica.
- Piloto P5 con docentes y coordinadores de Software/TI designados.
- B4: SMTP institucional y prueba de recepción real.
- B5/B6: servidor, DNS, certificado, redes y concurrencia confirmados por TI.
- B9/B10: aviso de privacidad, conservación de datos y administradores aprobados.

## Decisión para aprobar

Aprobar la preparación local de este despliegue con Compose aislado, cinco servicios, proxy HTTPS y prueba de restauración en base nueva. La puesta en marcha institucional y la fusión de los PR quedan fuera de esta aprobación.
