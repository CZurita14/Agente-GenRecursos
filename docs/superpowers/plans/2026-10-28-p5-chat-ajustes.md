# P5 · Chat de ajustes — diseño para aprobación

**Estado:** propuesta; no hay código P5 implementado.

**Objetivo:** satisfacer el criterio 10: «Haz más difícil la pregunta 3» modifica solo esa pregunta, la verifica y revisa, conserva las demás y exige nueva validación docente.

**Base:** spec v1.3 §3.4, §3.8 A5, §9.2, §9.4 y §12; hoja de ruta P5 C1–C3. Parte de P6d, PR #10; no requiere fusionarlo para trabajar en una rama dependiente.

## Diseño recomendado

### Experiencia del docente

Panel «Ajustar con IA» en la revisión del recurso y acceso al chat dentro de la asignatura. El recurso seleccionado determina a qué se refiere «pregunta 3»; su número se convierte al `item_id` de la revisión seleccionada, nunca a un índice de una versión posterior. Sin selección suficiente, el agente pide aclaración y no inicia una modificación.

El panel muestra el historial propio, el pedido pendiente y un enlace al avance del trabajo. No presenta una modificación como aplicada antes de que termine. No permite enviar mientras existe un borrador manual sin guardar. Los lectores conservan sus descargas pero no tienen acceso al chat ni a los pedidos de otros usuarios.

Ejemplos previstos:

- «Haz más difíciles las preguntas 3 y 7»: modificar solo esos ítems, dentro de los límites académicos vigentes.
- «Cambia el caso a una empresa de Ambato»: conservar la alineación y modificar solo los textos necesarios del recurso seleccionado.
- «Hazme un simulacro del momento 3»: reutilizar el servicio de generación y sus restricciones.
- Solicitudes generales, cambios al sílabo o soluciones de tareas/evidencias: `fuera_de_alcance`, sin trabajo generativo.

### Acciones y confianza

`AccionAgente` será una unión discriminada estricta: `ajustar_recurso`, `generar`, `aclarar`, `fuera_de_alcance`. Cada variante admite únicamente sus campos y tiene límites de tamaño. El intérprete de facultad usa el cliente local existente, temperatura 0, razonamiento desactivado y salida JSON forzada por esquema. Su salida es una propuesta no confiable: solo código autorizado ejecuta acciones.

El servidor valida recurso, revisión, ámbito, herramienta, ítems/secciones, política de IA y permisos. No acepta que el modelo cambie asignatura, usuario, facultad, RA, identificadores o estado de validación. Una petición ambigua pide aclaración; una respuesta inválida del modelo no ejecuta nada. El texto del modelo se muestra escapado, sin HTML ejecutable.

Para dificultad, reutilizar los perfiles y reglas académicas existentes. No resolver por suposición el bloqueo H7 sobre el techo del RA: si un incremento no se puede justificar dentro de lo permitido, solicitar una precisión en lugar de excederlo.

### Ejecución y concurrencia

Usar la cola y leases existentes para interpretación y regeneración; no mantener una petición HTTP ni una transacción de BD abierta durante llamadas al modelo. Distinguir explícitamente los trabajos de chat/ajuste de los de generación, sin hacer pasar un ajuste por una generación completa.

Cada ajuste guarda recurso destino, revisión base, versión del sílabo, usuario solicitante y selección exacta de ítems o rutas editables. Las rutas se validan contra la presentación permitida, no mediante escritura arbitraria de claves proporcionadas por el modelo. Herramientas sin IA no se ajustan: reproducen el sílabo.

Los workers regeneran solo la selección. Se reutilizan verificador y revisor, así como límites de tokens, tiempos, consumo y política de entregables. Para secciones de otras herramientas se valida el esquema completo resultante y las invariantes del contenido conservado. El paquete de revisión debe indicar exactamente qué se revisó: no atribuir al contenido combinado una revisión que no recibió.

Publicación atómica mediante revisión optimista: si sigue siendo la revisión de partida y el usuario conserva permiso, guardar una edición con autor y trazabilidad, aumentar revisión, invalidar la validación y actualizar la evidencia correspondiente. El resto del contenido debe ser idéntico. Si hubo edición concurrente, retirada de permiso, fallo del modelo o pérdida de lease, no sobrescribir el recurso: finalizar con estado claro y conservar el original. Reintentos de un mismo pedido no crean dos ediciones ni dos generaciones.

### Historial y HTTP

Historial aislado por `(asignatura_id, usuario)`; los IDs de pedidos no conceden acceso. Consultar, ejecutar y recuperar resultados vuelve a comprobar permisos. El usuario y la facultad se derivan de la sesión y de la asignatura. No enviar correo ni datos personales del sílabo al modelo; no registrar mensajes, prompts o recursos en logs. `uso_mejora = false`.

Contrato propuesto, compatible con las rutas previstas en el spec:

- `POST /asignaturas/{aid}/chat`: mensaje acotado, recurso/revisión seleccionados si corresponde e identificador de petición para deduplicar. Devuelve 202 y pedido/estado.
- `GET /asignaturas/{aid}/chat`: historial privado paginado, con cursor acotado.
- `GET /asignaturas/{aid}/chat/{pedido}`: estado, respuesta segura y referencias a trabajos o revisión creada; acceso exclusivo del solicitante autorizado.
- `POST /asignaturas/{aid}/recursos/{rid}/items/{item}/regenerar`: usa el mismo ejecutor e invariantes, con revisión y motivo; no duplica la lógica del chat.

Limitar mensajes, contexto enviado, historial recuperado y pedidos pendientes por usuario. El presupuesto incluye el prompt, esquema y respuesta dentro de la ventana de 8192 tokens. Recuperar solamente el contexto de esta asignatura/usuario; el historial no puede alterar las reglas del sistema. Caducidad y eliminación deben seguir la política de privacidad existente; cualquier plazo nuevo requiere una decisión explícita.

## Alternativas

1. **Cola existente — recomendada:** se integra con el avance y los leases, permite recuperación e idempotencia y evita bloquear HTTP durante la regeneración.
2. Interpretar en HTTP y encolar solo el ajuste: menos cambios iniciales, pero expone la respuesta HTTP a latencia y caídas del modelo y exige otro mecanismo para recuperar el pedido.
3. Reemplazar todo el recurso: reutiliza generación más fácilmente, pero incumple el criterio de conservar preguntas no afectadas; descartada.

## Secuencia propuesta después de aprobar

### C1 · Contrato e interpretación

Crear `backend/app/chat/acciones.py`, `interprete.py`, sus pruebas y una migración posterior a `006` para pedidos/historial. Revisar primero el esquema y los estados de cola para ampliar sus tipos sin romper generaciones existentes. Inyectar el cliente del modelo para pruebas simuladas.

Aceptación: las cuatro acciones, esquema estricto, ambigüedad, números de pregunta resueltos contra la revisión correcta, IDs ajenos rechazados, intentos de alterar reglas sin ejecución, prompts sin correo y presupuesto medido.

### C2 · Ejecutores de ajustes

Crear `backend/app/chat/servicio.py` y ejecutor de regeneración; ampliar el despacho de `backend/app/agentes/orquestador.py` y la cola según el esquema elegido. Reutilizar `backend/app/recursos/servicio.py`, workers, verificador y revisor, separando persistencia de llamadas al modelo.

Aceptación: solo cambia la selección; revisión y contenido no afectado idénticos; revisión/verificación del resultado; nueva validación obligatoria; conflicto y revocación no sobrescriben; reintento/lease perdido no duplica; generación desde chat conserva límites y restricciones del menú. Casos de ajuste de ítem y de sección de una herramienta con IA.

### C3 · HTTP e historial

Crear `backend/app/api/chat.py`, registrar rutas en la aplicación e integrar límites/consumo. Pruebas HTTP con sesiones y BD aisladas.

Aceptación: 401/403/404 según contrato, aislamiento entre usuarios/asignaturas, paginación, tamaño/ritmo/pedidos pendientes, deduplicación, fallo del modelo sin detalles privados y sin mutación parcial.

### C4 · Interfaz

Crear panel de chat y tipos/cliente; integrarlo en revisión y navegación de asignatura, con pruebas unitarias y de navegador. Mostrar avance y conflictos con mensajes claros; refrescar el recurso al finalizar sin perder silenciosamente un borrador.

Aceptación: enviar, aclarar, fuera de alcance, seguir progreso, revisar el resultado, conflicto, nueva validación, lector sin chat y aislamiento visual de historial al cambiar de asignatura.

### C5 · Verificación y cierre

Ejecutar pruebas nuevas, regresión backend sin IA real y `npm run check`/navegador. Humo con Qwen local cuando esté disponible; registrar separadamente resultados simulados y reales. La prueba con unos 15 pedidos de docentes piloto sigue siendo una puerta humana y no se declarará satisfecha con pruebas automáticas.

Actualizar `progress.md`, guardar commits y abrir PR dependiente de P6d. No fusionar ramas ni activar producción como parte de este bloque.

## Decisión para aprobar

Aprobar el diseño de chat privado asíncrono, regeneración selectiva con revisión optimista y panel en la revisión del recurso. El cierre académico con docentes piloto, la política institucional y H7 no se sustituyen por decisiones del modelo.
