# Razonador entrenado · Guía para el área académica y para TI

**Estado:** implementado y probado solo con la prueba de humo (2 sílabos). **Está apagado** y no cambia nada de lo que hoy hace la aplicación hasta que alguien lo encienda a propósito. Los criterios de aprobación de la sección 5 son una **propuesta, pendiente de que el usuario los confirme** antes de la corrida real.

---

## 1. Qué decide el modelo y qué sigue haciendo Qwen

Al preparar una ficha, un cuestionario u otra herramienta, la aplicación primero arma un **plan**: de qué tratará cada pregunta (el «foco») y con qué situación concreta (el «caso»). Después Qwen redacta cada pregunta siguiendo ese plan.

El modelo entrenado, llamado **razonador**, solo interviene en el plan, y solo en dos decisiones:

| Decisión | Hoy | Con el razonador |
|---|---|---|
| **Temas** | Los focos se reparten de forma fija, sin saber cuáles se parecen entre sí. | Agrupa los focos por tema y reparte las preguntas recorriendo un foco de cada tema antes de repetir. Un cuestionario cubre más temas distintos. |
| **Casos** | Se descartan los casos que comparten palabras con el entregable del momento. | Además descarta los que **significan lo mismo** aunque usen otras palabras. Nunca acepta un caso que el filtro de palabras ya había descartado. |

**Qwen sigue redactando todo**: el enunciado, las opciones, la respuesta correcta y las explicaciones. Qwen no participa en el entrenamiento ni en la evaluación del razonador.

**Por qué no corrige claves de respuesta equivocadas.** El razonador cambia *lo que Qwen recibe*, no *lo que Qwen sabe*. Si Qwen marca una opción incorrecta como correcta, el razonador no lo detecta ni lo arregla. Ese problema requiere otro trabajo (ítems con cálculo automático y verificación de las claves) y sigue pendiente; la revisión docente sigue siendo necesaria. Una mejora en las preguntas finales solo se podrá afirmar al comparar, con Qwen real y revisión docente, las mismas clases con y sin razonador (sección 8).

Si el razonador falla o no está encendido, la generación es exactamente la de siempre.

---

## 2. Cuántos sílabos hacen falta

El modelo se entrena con el 70 % de los sílabos y se evalúa con el 30 % restante. La separación se hace **por sílabo** (nunca por fragmento), para que la evaluación no vea nada parecido a lo que estudió.

| Uso | Sílabos | Para qué sirve |
|---|---|---|
| Prueba de humo | 2 | Solo comprueba que el programa corre. **No mide calidad.** |
| **Mínimo para entrenar** | **4 por facultad, en al menos 5 facultades (20)** | Deja 3 para entrenar y 1 para evaluar en cada facultad. |
| Recomendado | 4 por facultad en las 8 facultades (32) | Cubre todo el catálogo. |
| Separación 70/30 exacta | 10 por facultad en las 8 (80) | Solo si la universidad los entrega. |

Con menos sílabos el programa se niega a entrenar (salvo con la opción de humo). Hoy hay 2 PDF, ambos de Ingenierías.

Los sílabos reales contienen datos personales de los docentes: se guardan en `Silabos/` en el equipo de trabajo, **no se versionan**, y ningún informe ni mensaje de consola reproduce su texto, solo cifras.

---

## 3. Cómo etiquetar

Dos archivos CSV en `datos_cd/` (carpeta fuera del repositorio). Los llenan docentes; el equipo técnico solo los lee. Se pueden abrir y guardar con Excel en formato CSV UTF-8.

### 3.1 `pares.csv`: ¿este caso se parece al entregable?

**Este archivo todavía no se puede generar con ninguna herramienta.** El equipo técnico debe prepararlo a mano (o con un programa que aún no existe) a partir de los casos de cada carrera y de los entregables de los sílabos; la ficha de etiquetado se entrega a los docentes ya con esas columnas llenas. Hasta entonces la evaluación real no puede correr (ver sección 8).

Cada fila es un par: un **caso** (la situación que se propondría en una pregunta) y una **evidencia** (el texto de un entregable del sílabo). El docente responde una sola cosa: ¿el caso es **lo mismo o casi lo mismo** que la evidencia, de modo que la pregunta le regalaría la respuesta al estudiante?

| Columna | Qué poner |
|---|---|
| `caso` | Texto del caso. Lo escribe el equipo técnico al preparar el archivo. |
| `evidencia` | Texto del entregable. Lo escribe el equipo técnico al preparar el archivo. |
| `codigo_pf` | Código del proyecto formativo de donde sale la evidencia. Lo escribe el equipo técnico. |
| `docente` | Un código o iniciales acordadas (por ejemplo `D1`, `D2`). **No escribir nombres ni correos.** |
| `parecido` | `sí` si se parecen; `no` si son situaciones distintas. También se aceptan `1`/`0`, `si`/`no`. |

Reglas:

- Se necesitan **500 pares**, con **al menos 40 % de «sí»** (para que el grupo de evaluación tenga unos 60 casos parecidos).
- **Dos docentes** etiquetan por separado **al menos 100 pares en común**: con ellos se mide si los docentes coinciden entre sí (kappa).
- Si dos docentes responden distinto al mismo par, ese par no cuenta para el umbral ni para las métricas (se informa cuántos fueron).
- Una celda vacía o con otra respuesta no se cuenta como «no»: se descarta y se cuenta aparte.

### 3.2 `temas.csv`: ¿este grupo de fragmentos tiene sentido como tema?

El programa agrupa los fragmentos del grupo de evaluación en unos 8 temas y escribe una lista (`temas-para-revisar`). El docente lee cada grupo y responde si todos sus fragmentos tratan de un mismo asunto reconocible.

| Columna | Qué poner |
|---|---|
| `huella_temas` | Identificador de esa agrupación. Ya viene escrito: no tocar. |
| `grupo` | Número del grupo. Ya viene escrito. |
| `docente` | Código del docente, como en `pares.csv`. |
| `tiene_sentido` | `sí` o `no`. |

**Importante:** hasta evaluar no se sabe si gana el modelo ajustado o el modelo base. Por eso los docentes deben juzgar los temas de **ambos candidatos** (se ejecuta `temas-para-revisar` sobre cada uno). Si faltan los de quien gana, esa medida queda vacía y el modelo **no se aprueba**.

---

## 4. Cómo se entrena y se evalúa (para el equipo técnico)

Se usa el entorno de entrenamiento `.venv-ciencia` (con PyTorch, solo CPU) y el modelo base ya descargado en la caché local. La consola puede ser Windows: no hace falta configurar nada especial.

```text
cd backend
# 1. Candidato ajustado y candidato base (sin ajuste), con los sílabos reales
HF_HUB_OFFLINE=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.entrenar --silabos ../Silabos --salida ../modelos/v1
HF_HUB_OFFLINE=1 ../.venv-ciencia/Scripts/python.exe -m ciencia_datos.entrenar --silabos ../Silabos --salida ../modelos/base --sin-ajuste
# 2. Listas de temas para los docentes: una por candidato, con el mismo --k (8 por omisión)
... -m ciencia_datos.evaluar temas-para-revisar --modelo ../modelos/v1 --silabos ../Silabos --salida ../datos_cd/temas-revision-v1.csv
... -m ciencia_datos.evaluar temas-para-revisar --modelo ../modelos/base --silabos ../Silabos --salida ../datos_cd/temas-revision-base.csv
# 3. Con pares.csv y temas.csv completos, una sola evaluación
... -m ciencia_datos.evaluar --modelo ../modelos/v1 --base-modelo ../modelos/base --silabos ../Silabos
```

El valor de `--k` debe ser **el mismo** en `temas-para-revisar` y en `evaluar` (si se cambia en uno, se indica igual en el otro): la huella de los temas depende de él, y las filas de `temas.csv` solo valen para la agrupación con la que se juzgaron. Los sílabos pueden estar en subcarpetas de `Silabos/`; se conserva una versión por código de proyecto formativo.

Los informes de la prueba de humo (`pruebas/ciencia_datos/*-humo.json`) no se versionan: están en `.gitignore`.

La evaluación se hace **una sola vez por versión**: deja un candado en la carpeta del modelo y una segunda corrida se rechaza. Si todo aprueba, marca el modelo como aprobado y fija su umbral; si no, queda sin aprobar y no se puede cargar en producción.

Nota: el modelo ajustado compite contra el base y puede perder. Con 20 a 32 sílabos hay pocos miles de fragmentos, que pueden no alcanzar para que el ajuste supere al modelo base. Si pierde, se usa el base.

---

## 5. Criterios de aprobación (PROPUESTOS, pendientes de confirmación del usuario)

El modelo se aprueba solo si **cumple todos**. Una medida que falte nunca cuenta como cumplida.

| Medida | Criterio propuesto |
|---|---|
| Umbral de parecido | Se elige solo con el 70 % de entrenamiento: el de mayor precisión con exhaustividad de al menos 0,90. |
| Casos en el 30 % de evaluación | Exhaustividad de al menos 0,85 (de cada 100 casos que los docentes dicen parecidos, el modelo descarta 85 o más). |
| Mejor que el filtro actual | Prueba de McNemar con p < 0,05 **y** más aciertos propios que el filtro de palabras actual (no basta con ser distinto: debe ser mejor). |
| Temas, separación | Silueta mayor que el percentil 95 de agrupar al azar. |
| Temas, estabilidad | ARI entre semillas de al menos 0,80 (la agrupación no cambia al repetirla). |
| Temas, juicio docente | Al menos 80 % de los grupos «tienen sentido». |
| Acuerdo entre docentes | Kappa de Cohen de al menos 0,60, con al menos 100 pares comunes. |
| Muestra de evaluación | Al menos 60 casos parecidos en el 30 % de evaluación. |
| Ajuste fino | Se conserva solo si supera al modelo base en F1 de evaluación; si no, se usa el base. |
| Generalización | Se repite dejando fuera cada facultad, y se informa la peor. |

---

## 6. Cómo leer el informe

Los informes quedan en `pruebas/ciencia_datos/` y **solo contienen cifras y huellas, nunca textos** de sílabos. Se leen así:

- **`aprobado`**: `true` solo si cumplió todos los criterios de la sección 5. Con `humo: true` es siempre `false`.
- **`criterios`**: una línea por criterio, `true` o `false`. El que dice `false` es el motivo del rechazo.
- **`medidas`**: las cifras detrás de cada criterio (exhaustividad, valor p de McNemar, silueta frente al azar, ARI, kappa, conteos).
- **`problemas`**: avisos de datos que impiden decidir (sílabo de prueba ausente, etiquetas fuera de grupo, falta de un archivo).
- **`modelo_elegido`** y **`nota_modelo`**: si ganó el ajustado o el base.
- Un valor `null` significa «no se pudo calcular» y **nunca** cumple un criterio.

### Resultado de la prueba de humo (2 sílabos)

Con los 2 PDF de Ingenierías (1 para entrenamiento, 1 para evaluación, 27 fragmentos) el entrenamiento y la evaluación corrieron de principio a fin: se generó el modelo, se exportó y el informe se escribió con `humo: true` y `aprobado: false`. **Este resultado no es una evaluación de calidad**: demuestra que el programa funciona, no que el modelo sea bueno. Con un solo sílabo de evaluación no hay etiquetas docentes ni conclusiones posibles.

---

## 7. Cómo encenderlo y apagarlo

| Acción | Cómo |
|---|---|
| **Apagado (por omisión)** | `RAZONADOR_RUTA` vacía o ausente. La generación es idéntica a la de siempre. |
| **Encender** | Solo TI y solo con un modelo **aprobado**: copiar la carpeta del modelo al volumen `modelos` (montado de solo lectura en el contenedor `worker`), poner en el archivo de entorno `RAZONADOR_RUTA=/modelos/<versión>` y recrear el `worker`. Ver [entrega a TI](entrega-ti.md) y [operación](operacion.md). |
| **Apagar de nuevo** | Dejar `RAZONADOR_RUTA=` vacía y recrear el `worker`. |

Garantías:

- Solo el `worker` recibe `RAZONADOR_RUTA`; la API y los demás servicios no la ven.
- En producción el `worker` **no arranca** con un modelo ausente, dañado, de humo o sin aprobar, y registra la causa en su bitácora. Nunca sigue en silencio sin el razonador.
- Un trabajo que se reanuda tras una caída conserva el plan que ya había decidido, aunque entretanto se haya instalado otro modelo.
- La imagen de producción no incluye PyTorch: solo `numpy`, `scikit-learn`, `onnxruntime` y `tokenizers`.

---

## 8. Lo que falta y lo que no se sabe

Corrida real (depende de personas, no de código):

1. El área académica entrega al menos 20 sílabos según la sección 2.
2. El usuario confirma los criterios de la sección 5.
3. Docentes etiquetan los 500 pares y los temas de ambos candidatos. La lista de pares (caso, evidencia) todavía debe prepararla el equipo técnico a partir de los casos de cada carrera y los entregables de los sílabos; no hay una herramienta que la genere.
4. Se entrena, se evalúa **una sola vez** y se presenta el informe al usuario.
5. Solo si aprueba y el usuario lo decide, TI instala el modelo y define `RAZONADOR_RUTA`.
6. Se compara con y sin razonador en las mismas clases, con Qwen real y revisión docente. Una regresión logística multinivel se añadirá cuando existan esas 240 preguntas revisadas.

Límites conocidos: con 20 a 32 sílabos el ajuste fino puede no superar al modelo base; el razonador no corrige claves incorrectas; y cambia lo que Qwen recibe, no lo que Qwen sabe.
