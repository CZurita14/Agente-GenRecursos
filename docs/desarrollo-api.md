# API local: configuración y pruebas

Desde `backend`, con el PostgreSQL configurado en `.env`:

```powershell
../.venv/Scripts/python.exe -c "from app.db.conexion import conectar; from app.db.migrar import aplicar_migraciones; c=conectar(); c.autocommit=True; print(aplicar_migraciones(c)); c.close()"
../.venv/Scripts/python.exe -m uvicorn app.api.aplicacion:crear_app --factory --host 127.0.0.1 --port 8001
```

La API no aplica migraciones al iniciar. `004_auth.sql` crea retos y sesiones; el aplicador es idempotente. Las pruebas usan un esquema temporal por prueba, sin modificar las tablas de la aplicación.

## Configuración del ingreso

Definir `AUTH_SECRETO` con al menos 32 caracteres aleatorios en `.env` o en el almacén de secretos del despliegue. Sin ese secreto, `/salud` funciona y las solicitudes de ingreso responden 503. No copiar el valor de prueba ni guardarlo en Git.

El modo predeterminado es `ENTORNO=produccion`, `SMTP_MODO=deshabilitado` y `API_ORIGEN=https://localhost:5173`. Para consola de desarrollo definir explícitamente `ENTORNO=desarrollo` y `SMTP_MODO=consola`. Este modo imprime el correo y código en la terminal local: solo usarlo en desarrollo. En producción exige SMTP y un origen HTTPS exacto, sin ruta ni barra final. El SMTP de esta implementación usa STARTTLS (normalmente puerto 587), validación del certificado y timeout de 10 segundos. No admite conexión SMTP sin TLS ni TLS implícito de puerto 465.

Para SMTP definir `SMTP_HOST`, `SMTP_PORT`, `SMTP_REMITENTE`, `SMTP_USUARIO` y `SMTP_CLAVE`. La cuenta institucional sigue pendiente de TI (B4); las pruebas capturan los mensajes o simulan SMTP y no envían correos reales.

## Contrato de autenticación

- `POST /auth/codigo`, JSON `{"correo":"docente@uti.edu.ec"}`: respuesta uniforme para buzones aceptados o rechazados por SMTP. Solo admite exactamente `uti.edu.ec` e `indoamerica.edu.ec`. Intervalo mínimo de reenvío: 60 segundos.
- `POST /auth/verificar`, JSON con `correo` y `codigo`: código de seis dígitos, 10 minutos, un solo uso. Quinto fallo: 429 y bloqueo de 15 minutos; pedir otro código no borra los intentos ni el bloqueo. Un código expirado no abre sesión.
- `GET /auth/yo`: correo del usuario autenticado y rol `docente`. Los permisos sobre asignaturas y el rol administrativo se incorporan en A3/A5.
- `POST /auth/salir`: elimina la sesión en PostgreSQL y la cookie en el cliente.

Las escrituras exigen `Origin` exactamente igual a `API_ORIGEN`, incluso antes de abrir sesión. Las cookies siempre son `Secure`, `HttpOnly`, `SameSite=Lax`, sin atributo Domain. Para probar el flujo en navegador se necesita servir API y frontend por HTTPS; habilitar HTTP para el origen en desarrollo no desactiva Secure. TestClient usa una URL HTTPS y no necesita certificados.

El servidor invalida sesiones tras 8 horas sin actividad y siempre a los 7 días de creación. No basta una cookie inventada. La BD solo almacena HMAC de códigos y SHA-256 de tokens de sesión; el secreto de HMAC permanece en configuración.

El reto se confirma antes de enviar correo: no hay locks SQL ni conexiones retenidas mientras SMTP responde. Si SMTP acepta un mensaje pero se pierde la confirmación, el código sigue siendo utilizable y se conserva el intervalo de reenvío. Un rechazo del buzón no cambia la respuesta pública. Otros fallos de infraestructura dan 503 sin información interna. Las esperas de lock de emisión y verificación se limitan a 2 segundos.

## Verificación

```powershell
../.venv/Scripts/python.exe -m pytest tests/test_auth.py tests/test_correo_auth.py tests/test_api.py -q
../.venv/Scripts/python.exe -m pytest -q
```

Incluye vencimiento, bloqueo, consumo único, revocación, TLS y no enumeración de buzones. Las pruebas concurrentes retienen una fila y comprueban en `pg_stat_activity` que los competidores esperan un lock antes de liberarla. No activan el humo GPU salvo que se configure `LLM_REAL=1`.

P4 todavía necesita A3 (asignaturas/permisos), A4 (generación/recursos) y A5 (límites por IP, consumo y privacidad). No publicar la API como servicio de producción antes de completar esos controles y el despliegue P7.
