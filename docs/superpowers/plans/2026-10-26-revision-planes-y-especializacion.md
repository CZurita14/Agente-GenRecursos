# Revisión de los planes y estrategia de especialización por facultad y carrera

> **Fecha:** 2026-10-26 · **Revisa:** [hoja de ruta](2026-10-26-analisis-y-hoja-de-ruta-fase1.md) y [plan P1](2026-10-26-p1-nucleo-multiagente.md)
> **Contexto:**
> - Se esperan la **plantilla de herramientas** del área académica y los **sílabos de las demás facultades**. Con ellos se generarán los recursos definitivos.
> - Mientras tanto hay que definir cómo se especializa ("entrena") el sistema para cada facultad y carrera.

## 1. Resumen

1. **La lógica de los planes se sostiene.** Hay una sola falla grave, medida en las pruebas reales: la forma de usar el revisor no cabe ni en el tiempo ni en el contexto (R1). Ya está corregida en el P1.
2. **No hace falta reentrenar el modelo para empezar.** La especialización se construye en 4 niveles:
   - **configuración** por facultad y carrera (Fase 1);
   - **memoria de reglas** aprendida de las ediciones de los docentes (Fase 2);
   - **ejemplares aprobados** (Fase 2, con cautela);
   - **ajuste fino LoRA** por facultad sobre el mismo Qwen3-8B (Fase 3, opcional y con requisitos).
3. **Cada facultad nueva entra por un protocolo de alta** con un conjunto dorado y un criterio de graduación. Hasta graduarse, sus sílabos usan el agente general.

---

## 2. Revisión de la lógica de los planes

| # | Hallazgo | Evidencia | Gravedad | Corrección | Estado |
|---|---|---|---|---|---|
| **R1** | El revisor no puede trabajar de a 3 ítems por llamada ni con un límite de 120 s | Ronda v3: un ítem con razonamiento tardó hasta **125,6 s** y produjo hasta **3 420 tokens**; la mediana fue 33 s y 889 tokens. Tres ítems superan los 8 192 tokens y el límite de tiempo | **Alta** | Revisor de **1 ítem por llamada** y límite de tiempo **por rol**: workers 120 s, revisor 240 s | ✅ Aplicado en P1 (T1, T6, T12) |
| **R2** | El lease de 300 s queda justo frente a una llamada de 240 s | El lease se renueva antes de cada llamada; si la llamada dura más que el lease, otro worker puede tomar el trabajo | Alta | `lease_s = 360` (límite más largo + 120 s) | ✅ Aplicado en P1 (T1) |
| **R3** | El tiempo estimado por cuestionario (2–4 min, spec §5.4) es optimista | 3 lotes × ~1 min + 12 revisiones × ~33 s ≈ **8–10 min** por cuestionario de 12, sin contar devoluciones | Media | Corregir la expectativa en el spec v1.3 y en la pantalla ("suele tardar unos 10 minutos"). Medirlo en la T15 | Pendiente spec v1.3 |
| **R4** | El perfil es solo por **facultad**, pero las carreras de una facultad difieren mucho | FING agrupa Software, Civil, Industrial, Mecatrónica, Electricidad y TI: JASP sirve en Software, no en Civil | Media | El YAML de la facultad lleva **ajustes por carrera** (herencia general → facultad → carrera) | ✅ Aplicado en P1 (T8) |
| **R5** | El recurso no guarda la versión del sílabo con que se generó | Al subir una versión nueva (§2.2) no se sabría qué recursos quedaron desactualizados | Media | Campo `version_silabo` en `recurso` | ✅ Aplicado en P1 (T2) |
| **R6** | El revisor es el mismo modelo que genera, así que sus errores están correlacionados | Rondas 2–3: el revisor dejó pasar errores conceptuales (M2 en §16.1) | Media | Se mantiene la revisión a ciegas y por opción. Se suman reglas de dominio por facultad (M2, P3) y la **aprobación del docente** como última puerta. Se mide la tasa de errores que se escapan en el conjunto dorado (§5) | Diseño (P3) |
| **R7** | Los esquemas de las herramientas están en código; la plantilla académica puede cambiarlos | Pendiente 3b | Media | `version_esquema` en cada recurso (ya existe). Un esquema nuevo es una versión nueva, sin migrar lo ya generado. Los esquemas se aíslan en `herramientas/` para que la llegada de la plantilla toque un solo módulo (H8) | Diseño (P1 T2 + P3 H8) |
| **R8** | El presupuesto de contexto (§5.3) no tiene espacio para reglas aprendidas ni ejemplares | 500 tokens para "perfil + territorio + estilo" | Baja hoy, alta en Fase 2 | Repartir los 500: estilo ≤ 150 · reglas de memoria ≤ 200 · territorio ≤ 150. Un ejemplar (~300) solo cabe recortando la lista de ya generados | Pendiente spec v1.3 |
| **R9** | El spec v1.2 contradice decisiones posteriores | Hallazgos H1–H8 + R1, R3, R8 | Baja | Emitir el **spec v1.3** antes de empezar el P3 | Pendiente |

**Verificaciones que pasaron sin cambios:**
- **Cadena de dependencias de las olas:** ninguna tarea consume una interfaz que se produzca en una ola posterior.
- **Aislamiento entre asignaturas:** las reglas A1–A8 tienen prueba en P1 y la A9 en P4.
- **Datos personales:** el contrato `SilaboUTI` los excluye por construcción y hay una prueba de prompts.
- **Reanudación tras una caída:** el plan es determinista y cada `EntregaLote` se guarda junto con su avance en la misma transacción.
- **Integridad académica:** la cubre el revisor en P1, y P3 (H6) y P5 (C1) la refuerzan.

---

## 3. Qué depende de la documentación pendiente

| Documento esperado | Qué desbloquea | Qué se puede hacer sin él |
|---|---|---|
| **Plantilla de herramientas** (área académica) | Formato final de cada herramienta (P3 H8), renderizado definitivo (P6 E1–E2) | Todo el P1. Las herramientas se generan con el catálogo propuesto, con `version_esquema = 1` |
| **Sílabos de las demás facultades** (≥ 2 por facultad: uno cualitativo y uno cuantitativo; ideal, uno presencial) | Alta de cada facultad (§5), validación del lector con otras plantillas (P2 L7) | FING y el agente general. El lector se prueba con los 2 sílabos actuales |
| **Validación de la tabla verbo → nivel** (área académica) | Techo del RA (P3 H3) | El planificador funciona sin techo; los ítems se limitan por la tabla de especificaciones |

---

## 4. Cómo se especializa el sistema por facultad y carrera

### 4.1 Lo que se especializa y lo que no

| Se especializa | No se especializa |
|---|---|
| **Estilo**: tipos de caso, software, vocabulario, contextos profesionales | **Contenido**: sale solo del sílabo (decisión del 2026-10-20) |
| **Reglas de dominio**: lo que un experto del área marca como error | **Modelo base**: siempre Qwen3-8B-AWQ (decisión del 2026-10-20) |
| **Catálogo de errores típicos** por tema, para los distractores (M1) | **Esquemas y verificación**: comunes a todas las facultades |
| **Herramientas recomendadas** por ámbito | **Reglas de integridad académica** |

Los agentes Opus, Sonnet y Haiku del plan **construyen** el software. No se entrenan ni intervienen en la generación de recursos.

### 4.2 Topología: quién trabaja para quién

```text
                       Orquestador (código, sin IA): enruta por facultad
                                         │
     ┌──────────────────┬────────────────┼────────────────┬──────────────────┐
     ▼                  ▼                ▼                ▼                  ▼
 Agente FING        Agente FACEAN     Agente FCSBH     … (8 facultades)   Agente general
 (coordinador)      (coordinador)     (coordinador)                       (sin catálogo)
  ├─ carrera Software  ├─ Economía      ├─ …
  ├─ carrera Civil     ├─ Marketing
  └─ …                 └─ …
     │  el estilo efectivo = general ⊕ facultad ⊕ carrera (gana lo más específico)
     ▼
 WORKERS COMPARTIDOS por herramienta (cuestionario, ficha, práctica…), sin estado
     │  reciben en cada TareaLote: contexto del sílabo + estilo efectivo + reglas de la facultad
     ▼
 VERIFICADOR (código) + REVISOR (Qwen con razonamiento) con las reglas de dominio de la facultad
     ▼
 DOCENTE: aprueba, edita o descarta ──► sus ediciones alimentan la memoria (Nivel 1)
```

**Personas que acompañan a cada facultad:**

| Persona | Qué aporta | Cuándo |
|---|---|---|
| **Coordinador de carrera** | Valida el perfil de su carrera y aprueba o rechaza las reglas de dominio | En el alta y en cada revisión trimestral |
| **Docentes piloto** (1–2 por facultad) | Revisan el conjunto dorado ítem por ítem | En el alta y al promover cambios de nivel |
| **Área académica** | Plantilla, tabla de Bloom, criterio de calidad institucional | Una vez, y cuando cambie la normativa |

### 4.3 Los cuatro niveles

| Nivel | Qué es | Fase | Datos que necesita | Costo y riesgo | Se activa cuando |
|---|---|---|---|---|---|
| **0 · Configuración** | `agentes/<facultad>.yaml` con ajustes por carrera, glosario, reglas de dominio (M2) y catálogo de errores típicos por tema (M1) | **1** | ≥ 2 sílabos por facultad + 1 sesión con el coordinador de carrera | Bajo; cambia con un commit y una revisión | Siempre. Es la base |
| **1 · Memoria de reglas** (patrón ACE de Hive) | Las ediciones de los docentes se resumen en reglas cortas por facultad y carrera, con contadores *útil / dañina*. Se inyectan ≤ 200 tokens de reglas por llamada | 2 | Registro de ediciones (P4 A4 ya lo guarda) | Medio: una regla mala degrada todo. Por eso las aprueba el coordinador de carrera y se desactivan si empeoran el conjunto dorado | Tras ~50 ediciones de la facultad |
| **2 · Ejemplares aprobados** | 1 ítem aprobado sin cambios de la **misma carrera y herramienta**, mostrado como ejemplo de formato | 2 | Banco de ítems aprobados | Riesgo de que el modelo copie contenido de otra asignatura (choca con "solo el sílabo" y A1). Solo se usa si el conjunto dorado mejora **y** el verificador no detecta contenido ajeno | Experimento controlado; puede no activarse nunca |
| **3 · Ajuste fino LoRA por facultad** | Un adaptador LoRA por facultad sobre **el mismo** Qwen3-8B. vLLM sirve varios adaptadores a la vez (`--enable-lora`) y el agente elige el suyo por petición. No cambia el modelo base | 3 (opcional) | ≥ 300–500 pares aprobados por facultad, conjunto dorado, consentimiento de los docentes | Alto: TI reinicia vLLM con LoRA, hace falta GPU para entrenar (QLoRA de 8B cabe en ~16 GB; Unsloth ya está en la máquina de desarrollo) y gobierno de datos (LOPDP) | Solo si los niveles 0–2 no alcanzan el criterio de graduación de una facultad |

**Recomendación:**
- Fase 1 solo con el **Nivel 0**.
- Construir desde ya el registro de ediciones y el conjunto dorado, que son los insumos de los niveles 1–3.
- El LoRA queda como opción documentada que solo se abre si hay evidencia de que hace falta.

---

## 5. Protocolo de alta de una facultad o carrera

Es la forma repetible de "entrenar" un agente de facultad. Lo ejecuta el mismo equipo de agentes de construcción, con puertas humanas.

| Paso | Qué se hace | Quién (agente de construcción o persona) | Puerta |
|---|---|---|---|
| 1 | Recibir ≥ 2 sílabos de la facultad (uno cualitativo y uno cuantitativo; ideal, uno presencial) | Usuario | Sílabos entregados |
| 2 | Leerlos con el lector (P2). Si la plantilla difiere, ruta de respaldo y alta de la plantilla | Coordinador → implementador (sonnet) | Lectura idéntica al documento (criterio 1) |
| 3 | **Borrador del perfil**: software, tipos de caso y vocabulario **tal como aparecen en los sílabos**, por carrera | Explorador (haiku) extrae + redactor de perfil (sonnet) escribe el YAML | — |
| 4 | Reglas de dominio y catálogo de errores típicos de los temas de esos sílabos | Redactor (sonnet) propone + **revisor académico (opus)** depura | **Coordinador de carrera** valida perfil y reglas |
| 5 | **Conjunto dorado**: 2 clases × herramientas de Fase 1, generadas con el Qwen real | Coordinador corre la generación (como la T15) | — |
| 6 | Revisión humana ítem por ítem con la guía de `prueba-calidad-silabo.md` | **Docentes piloto** | — |
| 7 | **Criterio de graduación**: ≥ 14/16 ítems sólidos en cuestionario y simulacro, fichas sin errores conceptuales, 0 fallas de integridad, prueba de aislamiento aprobada | Revisor final (opus) prepara el informe | **Usuario** decide el alta |
| 8 | Alta: el perfil pasa a activo. Antes de esto, los sílabos de esa facultad usan el agente general y avisan "facultad en preparación" | Coordinador | — |
| 9 | Mejora continua: memoria de reglas (Fase 2) y revisión trimestral con el conjunto dorado como prueba de regresión | Coordinador + coordinador de carrera | Ninguna regla o adaptador entra si empeora el conjunto dorado |

**Productos que deja cada alta:**
- `agentes/<facultad>.yaml` con sus carreras;
- `agentes/glosarios/<facultad>.md`;
- `agentes/reglas/<facultad>.yaml` (dominio y errores típicos);
- `pruebas/dorado/<facultad>/` (ítems con su revisión humana);
- una fila en `progress.md`.

**Orden sugerido:** FING (ya tiene sílabos y pruebas) → la facultad que entregue primero sus sílabos → el resto. FCSBH, FCSH, FCED, FCMA y FJCP aún tienen siglas provisionales en `kb/catalogo.yaml` y deben confirmarse en su alta.

---

## 6. Cambios aplicados hoy

| Documento | Cambio |
|---|---|
| Plan P1 · Global Constraints | Revisor de 1 ítem por llamada; límite de tiempo por rol (120 s workers, 240 s revisor); lease de 360 s |
| Plan P1 · T1 | `llm_timeout_revisor_s = 240`, `lease_s = 360` |
| Plan P1 · T2 | `recurso.version_silabo` |
| Plan P1 · T6 | `completar` acepta un límite de tiempo por llamada |
| Plan P1 · T8 | Ajustes por carrera en el perfil y `estilo_para(carrera)` |
| Plan P1 · T12 | 1 ítem por llamada |
| `progress.md` | Bitácora, decisiones y preguntas abiertas |

## 7. Decisiones que necesito del usuario

| # | Pregunta | Recomendación |
|---|---|---|
| D1 | ¿Ajustes por carrera ya en la Fase 1? | **Sí**: cuesta poco (T8) y evita casos de Software en sílabos de Civil |
| D2 | ¿Abrimos con TI la consulta sobre `--enable-lora` y GPU para un posible Nivel 3? | Preguntar ahora sin comprometerse; la respuesta define si el Nivel 3 es viable |
| D3 | ¿Las ediciones de los docentes pueden usarse para mejorar el sistema (niveles 1–3)? | Sí, con aviso en la pantalla de ingreso y la opción de excluirse (LOPDP). Debe aprobarlo la universidad |
| D4 | ¿Quién valida el perfil de FING? Un coordinador de carrera por carrera, o uno por facultad | Uno por carrera para Software y TI, que ya tienen sílabos |
| D5 | ¿Emitimos el spec v1.3 con H1–H8 y R1–R9 antes del P3? | Sí; no bloquea el P1 |
