# app3 · Sistema multiagente

Un coordinador (Sonnet) y subagentes (Haiku) que investigan los tickets y la base de conocimiento de la mesa de ayuda (escenarios E3 y E4 del examen). El servidor MCP en proceso [`servers/investigacion.py`](servers/investigacion.py) devuelve cada resultado con el contenido separado de sus metadatos.

Términos: [glosario común](../docs/glosario.md).

## Ruta de lectura

Cada módulo se hace en 5 pasos: orientarte con su ficha, predecir, ejecutar o no según su **Modo** y contrastar, responder la pregunta y anotar tus fallos en `FALLOS.md`. Si es tu primera vez, lee antes [Empieza aquí](../README.md#empieza-aquí).

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_coordinador.py`](01_coordinador.py) | TS 1.2-K1…K4, S1, S2, S4 · TS 1.3-K1, K2, K3, S1, S4 | 1 |
| [`02_paralelo_y_descomposicion.py`](02_paralelo_y_descomposicion.py) | TS 1.2-S3 · TS 1.3-S3 · TS 1.6-K1, K3, S1, S3 | 1 |
| [`03_tools_entre_roles.py`](03_tools_entre_roles.py) | TS 2.3-K2, K3, S1, S2, S3 | 2 |
| [`04_errores_entre_agentes.py`](04_errores_entre_agentes.py) | TS 5.3-K1…K4, S1…S4 · TS 2.2-S3 | 3 |
| [`05_procedencia.py`](05_procedencia.py) | TS 5.6-K1…K4, S1…S5 · TS 5.1-K2, S4, S5, S6 · TS 1.3-S2 | 3 |
| [`06_contexto_largo.py`](06_contexto_largo.py) | TS 5.4-K1…K4, S1…S5 | 3 |
| [`07_extraccion_schema.py`](07_extraccion_schema.py) | TS 4.2-K4, S4, S5 · TS 4.3-K1…K4, S1…S6 | 3 |
| [`08_validacion_reintento.py`](08_validacion_reintento.py) | TS 4.4-K1, K2, K4, S1, S2, S4 (K3 y S3 en `app3/11`) | 3 |
| [`09_batches.py`](09_batches.py) | TS 4.5-K1…K4, S1…S4 | 3 |
| [`10_confianza_y_revision.py`](10_confianza_y_revision.py) | TS 5.5-K1…K4, S1…S4 | 3 |
| [`11_criterios_y_ci.py`](11_criterios_y_ci.py) | TS 3.6-K1…K3, S1…S5 · TS 4.1-K1…K3, S1…S3 · TS 4.2-S2, S3 · TS 4.4-K3, S3 | 3 |
| [`12_revision_independiente.py`](12_revision_independiente.py) | TS 4.6-K1…K3, S1…S3 · TS 1.6-K2, S2 · TS 3.6-K4 | 3 |

---

## 01 · Coordinador y subagentes

> **Qué vas a hacer:** Ver cómo un coordinador reparte una pregunta entre subagentes y qué cambia cuando su prompt está mal construido.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Los términos comunes (coordinador, subagente, `Task` (guía) / `Agent` (CLI), *hub-and-spoke*, descomposición, hook, permiso) están en el [glosario](../docs/glosario.md). Lo propio de este módulo:

- **El sistema:** un [coordinador](../docs/glosario.md#sistemas-multiagente) recibe una pregunta del usuario sobre la mesa de ayuda. Su única tool integrada es `Task` (guía) / `Agent` (CLI), con la que lanza [subagentes](../docs/glosario.md#sistemas-multiagente). Los subagentes buscan en el servidor MCP en proceso `investigacion`, que lee los tickets y la KB sintéticos. El coordinador va en modo `dontAsk` y pre-aprueba `Agent` y las dos tools de búsqueda, que usan los subagentes.
- **El prompt del coordinador:** fija objetivos y criterios de calidad, no pasos: cubrir todo el alcance de la pregunta, citar cada afirmación con su ID y su fecha, señalar los artículos obsoletos e invocar solo a los subagentes que aporten. También fija el formato de los hallazgos que viajan de un agente a otro.
- **La barrera del coordinador:** `tools=["Agent"]` limita las tools integradas, pero no oculta al coordinador las del servidor MCP. Un [hook](../docs/glosario.md#control-del-agente) `PreToolUse` compartido (`coordinator_gate.py`) le deniega esas tools a él y deja pasar a los subagentes. Así, lo que se mide de los subagentes es solo trabajo suyo.
- **Contenido y metadatos:** cada resultado del servidor separa el texto (`content`) de sus datos de procedencia (`metadata`: ID, fecha, estado o artículo sustituto). Es el formato con el que los hallazgos viajan de un agente a otro.
- **Selección dinámica:** que el coordinador decida, según la pregunta, qué subagentes necesita, en lugar de recorrer siempre todos.
- **Subtema:** cada parte en que se divide un tema amplio. En los datos, «problemas de red» abarca VPN, wifi e impresora.

### Las tools del ejercicio

| Tool | Quién la tiene | Qué recibe | Qué devuelve |
| :--- | :--- | :--- | :--- |
| `Task` (guía) / `Agent` (CLI) | coordinador | el subagente (`subagent_type`) y su prompt | la respuesta final del subagente |
| `search_tickets` | `tickets_analyst` | `query` (palabras clave o una categoría: acceso, hardware, red…) | hasta 8 tickets, con el texto en `content` y el ID, la categoría, el estado y la fecha en `metadata`; además, `total` y `truncated` si hay más coincidencias. Una consulta vacía devuelve un error de validación. |
| `search_kb` | `kb_analyst` | `query` (palabras clave, categoría o ID de artículo) | hasta 8 artículos, con el título y el cuerpo en `content` y el ID, la fecha y el artículo que lo sustituye (si está obsoleto) en `metadata`; también `total` y `truncated` |

Los tres subagentes se definen con `AgentDefinition` (descripción, prompt, tools y modelo):

| Subagente | Tools | Cometido según su prompt |
| :--- | :--- | :--- |
| `tickets_analyst` | solo `search_tickets` | buscar en los tickets lo que le pida el coordinador y devolver cada hallazgo con sus metadatos |
| `kb_analyst` | solo `search_kb` | lo mismo, en la base de conocimiento |
| `synthesizer` | ninguna | redactar un apartado por subtema, con cada cita |

### El ejercicio

Hay dos preguntas: la amplia por defecto («¿Qué problemas de red están teniendo los empleados y qué dice la base de conocimiento de cada uno?») y `--pregunta simple` («¿Qué dice el artículo KB-109?»). Lo que cambia en el código de cada variante `--anti`:

- **`pipeline_completo`:** añade al prompt del coordinador la orden de invocar siempre a los tres subagentes, en orden fijo, sea cual sea la pregunta.
- **`estrecha`:** añade que en esta empresa «problemas de red» quiere decir casi siempre la VPN, y que cada analista reciba una sola consulta concreta.
- **`sin_hallazgos`:** sustituye la regla de pasar los hallazgos por la afirmación de que el sintetizador ya ve lo que han encontrado los analistas, y pide pasarle solo la pregunta.
- **`procedimental`:** sustituye los objetivos por una receta de cuatro pasos: los dos analistas con la consulta «VPN», después el sintetizador, y devolver su respuesta.

La salida imprime la respuesta y varias líneas `[medida]`: los subagentes invocados; las llamadas por agente y los intentos del coordinador que denegó la barrera; si hubo sintetizador, cuántos de los IDs que encontraron los analistas llegaron a su prompt, y cuáles faltan; y qué subtemas aparecen en la respuesta. Esta última línea busca las palabras en el texto final: no comprueba si el subtema se investigó.

**El papel del sintetizador.** Invocarlo no es obligatorio: el coordinador decide, según la pregunta, si lo necesita. Sirve para separar la redacción de la investigación.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Un analista encuentra un ticket relevante. ¿Por dónde tiene que pasar ese hallazgo para llegar al sintetizador? ¿Puede el sintetizador verlo por su cuenta?
2. (guía) Con `--pregunta simple` («¿Qué dice el artículo KB-109?»), ¿qué analistas hacen falta y cuáles sobran?
3. (guía) Con `estrecha` (el prompt dice que «problemas de red» es casi siempre la VPN y que cada analista reciba una sola consulta), ¿qué parte del tema puede quedarse fuera? ¿Puede recuperarla algún subagente?
4. (módulo) Para saber si un subtema se investigó hay dos señales: la línea de subtemas, que busca palabras en la respuesta final, y las consultas delegadas (`[llamada rN]`). ¿De cuál te fías más y por qué?
5. (guía) Con `sin_hallazgos` (el coordinador pasa al sintetizador solo la pregunta), ¿qué puede redactar el sintetizador? ¿Por qué?
6. (módulo) En `sin_hallazgos`, ¿quién esperas que acabe redactando la respuesta final?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/01_coordinador.py                      # pregunta amplia, correcto
uv run python app3_sistema_multiagente/01_coordinador.py --pregunta simple    # selección dinámica
uv run python app3_sistema_multiagente/01_coordinador.py --anti estrecha      # o pipeline_completo, sin_hallazgos, procedimental
```

**Si ejecutas:** la barrera, las tools por subagente y las medidas sobre el registro se prueban sin modelo; ejecutar sirve para ver qué subagentes elige el coordinador y qué les pasa.

### Qué observar

Las líneas `[medida]`: qué subagentes se invocan, cuántos hallazgos llegan al sintetizador y qué subtemas aparecen; y las líneas `[llamada rN · …]`: qué consultas delegó el coordinador y qué tool usó cada subagente.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Por el coordinador: toda la comunicación entre subagentes pasa por él (TS 1.2-K1, 1.2-S4). El sintetizador no lo ve por su cuenta: su contexto está aislado y los hallazgos hay que incluirlos en su prompt (TS 1.2-K2, 1.3-K2, 1.3-S1).
- **P2** Solo `kb_analyst`. El coordinador elige según la pregunta en vez de recorrer siempre todo el pipeline (TS 1.2-K3, 1.2-S1), y aquí redactó él mismo.
- **P3** Todo lo que no es VPN (en la medida, la wifi no apareció). Ningún subagente puede recuperarlo: cada uno solo recibe la consulta que le delegan. Una descomposición demasiado estrecha deja sin cubrir partes de un tema amplio (TS 1.2-K4).
- **P4** De las consultas delegadas. En una repetición, la línea de subtemas dio `wifi: True` porque la respuesta decía que no había buscado la wifi: mira la palabra, no si se investigó.
- **P5** Nada con datos: recibió 0 de 33 hallazgos y dijo que no tenía datos. No hereda lo que encontraron los analistas (TS 1.2-K2, 1.3-S1).
- **P6** El coordinador, que sí tiene los hallazgos.

En la primera ejecución con modelo:

| Variante | Observado |
| :--- | :--- |
| correcta, pregunta amplia | invoca a los dos analistas y redacta él mismo la respuesta (no necesitó el sintetizador); cubre VPN y wifi |
| `--pregunta simple` | solo `kb_analyst` |
| `estrecha` | todo sobre la VPN; la wifi no aparece (`wifi: False`) |
| `sin_hallazgos` | el sintetizador recibe 0 de 33 hallazgos y dice que no tiene datos; el coordinador acaba redactando él |

Las llamadas por agente (`[llamada rN · tickets_analyst]`) muestran que cada subagente solo usó su tool, y que nada pasó de un subagente a otro sin pasar por el coordinador.

Notas:

- **Barrera del coordinador (2026-10-27, Sonnet 5.5 + Haiku 5.5):** como en el módulo 03, `tools=["Agent"]` no oculta al coordinador las tools del servidor, y hasta ahora solo el prompt («No busques tú») le impedía usarlas. Sonda: pidiéndoselo expresamente, sin barrera llamó él mismo a `search_tickets` y obtuvo los 7 tickets; con el hook compartido (`coordinator_gate.py`) recibió el rechazo, delegó en `tickets_analyst` y el subagente buscó con normalidad. Al repetir la medida con la barrera (correcta, `estrecha` y `--pregunta simple`, una ejecución cada una), el coordinador no intentó ninguna tool del servidor (`intentos del coordinador, denegados: 0`): la barrera asegura la medida, no corrige una señal que se hubiera visto.
- **`estrecha` y el detector de subtemas:** en esa repetición las tres consultas fueron solo de VPN (la descomposición estrecha se mantuvo), pero la línea de subtemas dio `wifi: True`, porque la respuesta decía «No he buscado otros problemas de red… como wifi o DNS». El detector busca la palabra, no si se investigó: es aproximado, y la señal fiable está en las consultas delegadas (`[llamada rN]`).

**Para pensar (sin evaluación):** ¿qué cambiaría con `--pregunta simple` en `pipeline_completo`, y qué pierde `procedimental` frente a un prompt con objetivos (TS 1.3-S4)? Esas dos variantes no están en las medidas de este Paso 3, así que no cuentan como predicción.
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un sistema de investigación tiene un coordinador y tres subagentes: búsqueda web, análisis de documentos y síntesis. Los informes finales omiten con frecuencia datos que los subagentes de búsqueda sí encontraron. Los registros muestran que el coordinador invoca al sintetizador con la pregunta original. ¿Cuál es la causa más probable?

- A. El sintetizador necesita un modelo con una ventana de contexto mayor para abarcar todos los hallazgos.
- B. El sintetizador no hereda el contexto del coordinador: los hallazgos había que pasárselos en su prompt.
- C. Los subagentes de búsqueda deberían escribir sus resultados en una memoria compartida con el sintetizador.
- D. Falta `"Task"` en las `allowedTools` del sintetizador, y por eso no puede pedir los hallazgos a los demás.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** El contexto del subagente es aislado y no hereda el historial del coordinador (TS 1.2-K2, 1.3-K2): los hallazgos completos se incluyen en su prompt (TS 1.3-S1), con los metadatos separados del contenido para conservar la atribución. C contradice que no comparten memoria entre invocaciones. D confunde quién necesita `Task`: es el coordinador, para lanzar subagentes (TS 1.3-K1).
</details>

**Pregunta 2 (multiple-response).** Un coordinador de investigación recorre siempre la misma cadena (búsqueda, análisis y síntesis) para cualquier petición, incluidas las consultas puntuales de un solo dato. En un informe sobre un tema amplio, además, los tres subagentes de búsqueda repiten consultas sobre el mismo subtema y otros subtemas quedan sin cubrir, aunque cada subagente ejecutó correctamente lo que se le pidió. **Selecciona dos** cambios que resuelvan los problemas descritos. Evalúa cada opción por separado: no hay nada que indique cuál va con cuál.

- A. El coordinador analiza cada petición y decide qué subagentes invocar según su complejidad, en lugar de recorrer siempre el pipeline completo.
- B. Los subagentes de búsqueda se envían directamente sus resultados entre sí para evitar consultas repetidas y reducir pasos del coordinador.
- C. El coordinador asigna a cada subagente de búsqueda un subtema o un tipo de fuente distinto, para cubrir el tema amplio sin duplicar consultas.
- D. El prompt de cada subagente de búsqueda pide que investigue todo lo relevante del tema, para que ninguna parte quede sin cubrir.

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**A y C.** Cada una corrige un problema distinto, y las otras dos no corrigen ninguno.

- **A** El coordinador es quien analiza qué necesita cada petición y decide qué subagentes invocar según su complejidad; recorrer siempre el pipeline completo es lo que esa habilidad pide evitar (TS 1.2-S1, 1.2-K3).
- **B** Rompe el patrón hub-and-spoke: la comunicación entre subagentes pasa por el coordinador, que da la observabilidad, el tratamiento uniforme de errores y el flujo controlado de información (TS 1.2-S4, 1.2-K1).
- **C** Repartir subtemas o tipos de fuente entre los subagentes evita duplicados y huecos, que es justo el riesgo de una descomposición demasiado estrecha en un tema amplio (TS 1.2-S2, 1.2-K4).
- **D** No reparte el alcance: los tres buscan lo mismo y se duplican, sin garantizar cobertura. Dividir el alcance es trabajo del coordinador (TS 1.2-S2, 1.2-K3).
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 1.3-K3.** Al definir un tipo de subagente con `AgentDefinition`, ¿qué se configura en ella?

- A. Su descripción, su *system prompt* y las tools a las que queda restringido.
- B. El historial del coordinador que recibirá al arrancar, cada vez que se le invoque.
- C. La memoria que compartirá con los demás subagentes entre una invocación y otra.
- D. El orden fijo en que el coordinador tendrá que invocarlo dentro del pipeline.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**A.** La `AgentDefinition` de cada tipo de subagente lleva su descripción, su *system prompt* y sus restricciones de tools (TS 1.3-K3). B y C contradicen que un subagente no hereda el contexto ni comparte memoria entre invocaciones (TS 1.3-K2); D no es de la definición: a quién invocar lo decide el coordinador.
</details>

**C2 · TS 1.3-S4.** ¿Cómo conviene escribir el prompt de un coordinador para que sus subagentes puedan adaptarse a lo que encuentran?

- A. Con una receta numerada de pasos, cada uno con la consulta exacta que hay que lanzar.
- B. Con la lista de tools de cada subagente y el orden en que debe llamar a cada una.
- C. Con los objetivos de la investigación y los criterios de calidad que debe cumplir.
- D. Con un único ejemplo de informe terminado, que los subagentes tienen que imitar.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**C.** El prompt del coordinador fija objetivos de investigación y criterios de calidad, no instrucciones procedimentales paso a paso, para que los subagentes puedan adaptarse (TS 1.3-S4). A y B son procedimiento; D da un formato, no un objetivo.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 02 · Paralelo, refinamiento y descomposición

> **Qué vas a hacer:** Lanzar subagentes en paralelo o en secuencia, refinar una síntesis incompleta y comparar dos formas de descomponer una tarea.
>
> **Necesitas antes:** El [módulo 01](#01--coordinador-y-subagentes): sus tools y la barrera del coordinador.
>
> **Modo:** Ejecución obligatoria en la parte `paralelo` (hay que ejecutarla: su lección es una latencia); las otras tres partes, ligeras.

### Antes de empezar

Los términos comunes (coordinador, subagente, `Task` (guía) / `Agent` (CLI), descomposición, tools integradas) están en el [glosario](../docs/glosario.md). Las dos tools de búsqueda y la barrera del coordinador son las del [módulo 01](#01--coordinador-y-subagentes). Aquí el coordinador solo tiene dos subagentes, `tickets_analyst` y `kb_analyst`, sin sintetizador.

Términos propios:

- **Latencia y aceleración:** la latencia es el tiempo de reloj de una ejecución completa. La aceleración es el tiempo del modo secuencial dividido entre el del paralelo.
- **Respuesta del coordinador:** cada mensaje que emite el modelo. Las llamadas `Agent` se agrupan por la respuesta en la que llegaron (`r1`, `r2`…).
- **Brecha:** un subtema esperado que la síntesis no menciona.
- **Ronda de delegación:** cada respuesta del coordinador que contiene al menos una llamada `Agent`.
- **Código *legacy*:** código heredado, sin tests y con dependencias que no se ven sin leerlo.

### El ejercicio

El módulo tiene cuatro partes independientes que se eligen con `--parte`, cada una con su propio sistema:

- **`paralelo`:** un coordinador con los dos analistas recibe tres peticiones independientes: tickets de licencias, tickets de hardware y artículos de la KB sobre acceso. Hay dos modos, y entre ellos solo cambia la última frase del prompt del coordinador. En el modo paralelo, si las subtareas son independientes, lanza todos los subagentes en la misma respuesta; en el secuencial, lanza uno, espera su resultado y luego el siguiente. Sin `--anti` se ejecutan los dos modos seguidos y se mide el tiempo de reloj de cada uno; con `--anti secuencial`, solo el secuencial.
- **`refinamiento`:** una conversación con `ClaudeSDKClient`. El coordinador recibe «¿Qué problemas de red tienen los empleados?» y la instrucción de hacer una primera pasada rápida, con una sola consulta por analista. Después, un comprobador escrito en código (sin modelo) busca en la síntesis las palabras de cada subtema esperado (VPN, wifi e impresora, `REQUIRED_SUBTOPICS`). Si falta alguno, envía al coordinador un mensaje con solo esos subtemas y le pide volver a delegar. Hace como mucho 2 rondas de refinamiento.
- **`descomposicion`:** dos estrategias. Primero, una **cadena fija** (*prompt chaining*) de tres pasos sobre los tickets de gastos con importe: extraer, aplicar la política (hasta 500 EUR aprueba soporte y, por encima, Finanzas) y redactar el informe. Cada paso es una llamada aparte, sin tools y con una sola respuesta, que recibe solo la salida del anterior. Después, una **descomposición adaptativa**: un coordinador con los dos analistas investiga una pregunta abierta sobre los tickets de septiembre, sin plan fijo, y explica de dónde sale cada subtarea.
- **`legacy`:** sin coordinador. Un solo agente, con las tools integradas de lectura `Glob`, `Grep` y `Read`, trabaja en el directorio de un paquete Python heredado (`datos/sinteticos/legacy_inventario/`) y recibe «Añade tests completos a este paquete legacy. Empieza por el plan». Su prompt le dice cómo organizar ese trabajo; qué le pide es parte de lo que vas a predecir. No puede escribir archivos.

`--anti` tiene una sola variante, `secuencial`, que solo afecta a `--parte paralelo`.

**Cómo se consigue el paralelo.** Ningún código lanza las tres llamadas a la vez: se le pide al coordinador en su prompt, las emite el modelo y el módulo lo comprueba después en el registro, agrupando las llamadas `Agent` por respuesta. El prompt lo pide; el código no lo garantiza.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) En el modo secuencial de `paralelo`, ¿a qué se parece más el tiempo total: a la suma de lo que tarda cada subagente o a lo que tarda el más lento? ¿Por qué?
2. (módulo) ¿Esperas que el modo paralelo acelere lo mismo en dos ejecuciones? ¿De qué depende?
3. (guía) Según la guía, en un bucle de refinamiento, ¿quién evalúa si a la síntesis le faltan temas y hasta cuándo se sigue? ¿Qué cambia que aquí lo detecte un comprobador en código con un tope de 2 rondas?
4. (módulo) El comprobador de `refinamiento` solo busca palabras en la síntesis. ¿Qué clase de síntesis le haría dar por cubierto un subtema que no se investigó?
5. (guía) En `descomposicion`, ¿puede cambiar el número de pasos de la cadena fija según lo que vaya encontrando? ¿Para qué clase de trabajo conviene la cadena y para cuál la descomposición adaptativa?
6. (guía) En la descomposición adaptativa, ¿de dónde deberían salir las subtareas de la segunda ronda?
7. (guía) En `legacy`, ¿qué debería hacer el agente antes de proponer ningún test? ¿Qué hace con el plan si después descubre una dependencia?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte paralelo          # paralelo y secuencial, con latencias
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte paralelo --anti secuencial   # solo el secuencial
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte refinamiento
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte descomposicion
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte legacy
```

**Al ejecutar:** `--parte paralelo` ejecuta los dos modos seguidos y los compara; con `--anti`, solo el secuencial. Las otras tres partes se prueban sin modelo (el comprobador de subtemas, la cadena y las medidas).

### Qué observar

En `paralelo`, cómo se agrupan las llamadas `Agent` por respuesta y la latencia de cada modo; en `refinamiento`, las brechas de cada ronda; en `descomposicion`, de dónde salen las subtareas de la segunda ronda; en `legacy`, qué lee el agente antes del plan y qué dependencias nombra.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** A la suma: con una llamada por respuesta, el coordinador espera cada resultado antes de emitir la siguiente. Para que los subagentes trabajen a la vez, las llamadas van en una misma respuesta (TS 1.3-S3); entonces el total se acerca más al del subagente más lento (inferencia propia). En el registro: en el modo paralelo salieron juntas en `r1`; en el secuencial, una por respuesta (`r1`, `r3`, `r5`).
- **P2** No: ×1,66 en una ejecución y ×1,37 en otra. Depende de lo que tarde cada subagente en esa ejecución, que el módulo no fija.
- **P3** El coordinador: evalúa la síntesis, vuelve a delegar con consultas dirigidas a lo que falta y sintetiza otra vez, hasta que la cobertura baste (TS 1.2-S3). Aquí la detección la hace código, que solo busca palabras (P4), y el tope de 2 rondas es una red de seguridad del módulo: el bucle puede acabar con huecos. En la ejecución de referencia no hubo brechas en la ronda 1 y el bucle no llegó a actuar.
- **P4** Una que nombre el subtema sin haberlo investigado, por ejemplo para decir que no lo buscó. El comprobador mira la palabra, no el trabajo.
- **P5** No: son siempre tres pasos. La cadena fija conviene cuando el trabajo es predecible; la descomposición dinámica, cuando depende de lo que se va descubriendo, como una investigación abierta (TS 1.6-K1, 1.6-S1).
- **P6** De los hallazgos de la primera ronda (TS 1.6-K3): aquí, los tickets del 19 al 22 de septiembre y los bloqueos de cuenta.
- **P7** Mapear la estructura, leer las zonas de mayor impacto y dar un plan priorizado, que se ajusta cuando aparece una dependencia (TS 1.6-S3). Aquí usó `Glob` y `Grep`, leyó los siete archivos y el plan nombró una dependencia que solo se ve leyendo el código.

En la primera ejecución con modelo:

- **paralelo:** 3 llamadas `Agent` en `r1` frente a una por respuesta (`r1`, `r3`, `r5`); 16,8 s frente a 27,9 s (×1,66). El recorder, que agrupa por `message_id`, las puso las tres en la misma respuesta.
- **refinamiento:** el comprobador busca VPN, wifi e impresora en la síntesis y devuelve al coordinador solo las brechas, como mucho 2 rondas. En la primera ejecución no hubo brechas en la ronda 1 y el bucle no llegó a actuar. Repítelo, o cambia `REQUIRED_SUBTOPICS`, para verlo re-delegar.
- **descomposicion:** la cadena fija procesa los reembolsos en tres pasos, y cada uno recibe solo la salida del anterior. La investigación abierta delegó en 2 rondas, y las subtareas de la segunda (tickets del 19 al 22 de septiembre, bloqueos de cuenta) salieron de los hallazgos de la primera.
- **Barrera del coordinador:** `paralelo`, `refinamiento` y la parte adaptativa de `descomposicion` usan el hook compartido del módulo 01 (la cadena fija y `legacy` no tienen coordinador). Con la sonda del módulo 01, el coordinador de este módulo también usó `search_tickets` sin barrera y recibió el rechazo con ella. Al repetir `paralelo` con la barrera (2026-10-27): 0 intentos del coordinador, 3 `Agent` en `r1` frente a uno por respuesta y ×1,37 (23,7 s frente a 32,4 s; la aceleración varía entre ejecuciones).
- **legacy:** primero `Glob` y `Grep` y después `Read` de los siete archivos. El plan menciona la dependencia escondida: `depreciacion.valor_actual` importa `almacen` dentro de la función y lee la caché que llena `asignaciones`.

**Para pensar (sin evaluación):** ¿de qué depende que la aceleración de `paralelo` se acerque o no a ×3 con tres subagentes? Y en `legacy`, ¿bastan `Glob` y `Grep` para conocer todas las dependencias entre módulos, o hace falta leerlos? El módulo no mide ninguna de las dos cosas por separado, así que no cuentan como predicción.
</details>

### Pregunta tipo examen

Un coordinador debe investigar tres temas independientes con tres subagentes. Hoy los invoca uno por turno y cada investigación tarda el triple de lo necesario. ¿Qué cambio es el más adecuado?

- A. Emitir las tres llamadas a Task en una sola respuesta del coordinador.
- B. Fusionar los tres subagentes en uno solo que tenga todas las tools.
- C. Bajar `max_turns` para que el coordinador termine antes cada tema.
- D. Pedir a cada subagente que lance al siguiente cuando haya terminado.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** Los subagentes en paralelo se lanzan con varias llamadas a Task en la misma respuesta (TS 1.3-S3). B pierde la especialización y el reparto del alcance; C no lanza nada en paralelo: un tope de turnos corta el trabajo, no lo acelera (sobre los topes, ver TS 1.1-S3); D rompe el hub-and-spoke, en el que toda la comunicación pasa por el coordinador.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 1.6-K1, S1.** Hay dos trabajos: una revisión que siempre comprueba los mismos tres aspectos en el mismo orden, y una investigación abierta cuyo paso siguiente depende de lo que aparezca. ¿Qué patrón conviene a cada uno?

- A. Descomposición dinámica para los dos, porque se adapta a cualquier tipo de trabajo.
- B. Cadena fija de pasos para los dos, porque así el resultado es siempre más predecible.
- C. Descomposición dinámica para la revisión y cadena fija de pasos para la investigación.
- D. Cadena fija de pasos para la revisión y descomposición dinámica para la investigación.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**D.** Una cadena secuencial fija conviene cuando el trabajo es predecible, y la descomposición dinámica, cuando depende de lo que se va descubriendo (TS 1.6-K1). El patrón se elige según el flujo (TS 1.6-S1). C los cruza; A y B usan uno solo para dos trabajos distintos.
</details>

**C2 · TS 1.6-K3, S3.** Se pide a un agente «añade tests completos a este código *legacy*». ¿Cómo debería empezar?

- A. Escribiendo tests para el primer archivo que encuentre y siguiendo por orden alfabético.
- B. Mapeando la estructura, localizando lo de mayor impacto y dando un plan priorizado que se ajusta.
- C. Pidiendo al usuario la lista exacta de funciones que hay que probar, antes de leer nada.
- D. Generando un plan fijo de diez pasos y siguiéndolo aunque aparezcan dependencias nuevas.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**B.** Para una tarea abierta, primero se mapea la estructura, después se identifican las zonas de mayor impacto y se hace un plan priorizado que se adapta cuando aparecen dependencias (TS 1.6-S3); el plan genera subtareas a partir de lo que encuentra en cada paso (TS 1.6-K3). D es un plan que no se adapta; A no prioriza; C devuelve al usuario un trabajo que el agente puede hacer.
</details>

**C3 · TS 1.2-S3.** La primera síntesis de un coordinador cubre dos de los tres subtemas de la pregunta. ¿Qué hace el coordinador?

- A. Entregarla tal cual y avisar al usuario de que puede volver a preguntar por lo que falta.
- B. Repetir desde cero todas las delegaciones, para que la segunda síntesis salga completa.
- C. Delegar de nuevo con consultas dirigidas a la brecha y sintetizar otra vez hasta cubrirla.
- D. Pedir al sintetizador que complete el subtema que falta con lo que ya sabe del dominio.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**C.** Es el bucle de refinamiento: el coordinador evalúa la síntesis, detecta las brechas, vuelve a delegar con consultas dirigidas y sintetiza otra vez hasta que la cobertura basta (TS 1.2-S3). B repite lo que ya está cubierto; D pide inventar; A entrega algo incompleto.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 03 · Tools entre roles

> **Qué vas a hacer:** Ver qué hace cada subagente según las tools que recibe: las de su rol, todas o una genérica.
>
> **Necesitas antes:** El [módulo 01](#01--coordinador-y-subagentes).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Los términos comunes (coordinador, subagente, *scoping*, tool *cross-role*, error estructurado) están en el [glosario](../docs/glosario.md). Este módulo sigue el patrón del [módulo 01](#01--coordinador-y-subagentes): un coordinador con `tools=["Agent"]` y la misma barrera, y subagentes definidos con `AgentDefinition`.

- **El sistema:** el coordinador tiene dos subagentes, `researcher` (reúne hallazgos) y `synthesizer` (redacta y verifica). El servidor `investigacion` arranca ampliado, con tres tools más. El coordinador pre-aprueba todas las tools del servidor, pero cada subagente solo ve las de su `AgentDefinition`, y eso es lo que cambia en cada variante. El prompt del coordinador no nombra ninguna tool ni dice cuál va a quién: le pide delegar y resolver él las afirmaciones que un subagente le devuelva.
- **La petición:** un informe sobre reembolsos y licencias con el contenido de ocho URLs del catálogo sintético (`documentos.json`). Cuatro son documentos y cuatro no: una página de inicio de sesión, una de seguimiento, una imagen y una de preferencias. Además, verificar cinco afirmaciones (`C-1`…): tres **simples**, que se comprueban con un solo artículo, y dos **complejas**, que necesitan cruzar varios.
- **Tool genérica y tool restringida:** una genérica (`fetch_url`) acepta cualquier entrada de su tipo; una restringida (`load_document`) valida que la entrada corresponde a lo que el rol necesita, y rechaza el resto con un error estructurado.
- **Fuera de rol:** una llamada a una tool que ese rol no tiene en la configuración correcta. La vara de medir es siempre la correcta, también al medir las variantes.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `search_kb` | `query` | igual que en el [módulo 01](#01--coordinador-y-subagentes) |
| `search_tickets` | `query` | igual que en el módulo 01; ningún rol la tiene en la configuración correcta |
| `fetch_url` | `url` | el contenido en bruto de cualquier URL del catálogo. Si la URL no es un documento, devuelve una página genérica sin contenido documental; si no está en el catálogo, un error |
| `load_document` | `url` | el título y el contenido de un documento (`/docs/…`); cualquier otra URL la rechaza con un error de validación no reintentable |
| `verify_fact` | `claim_id` | si la afirmación es simple, `supported` (una heurística de palabras contra su artículo, no una verificación semántica) y el artículo comprobado. Si es compleja, no la verifica: devuelve el estado «enrutar al coordinador» con los artículos implicados |

| Rol | Tools de la configuración correcta |
| :--- | :--- |
| `researcher` | `search_kb` y `load_document` (valida que la URL sea un documento) |
| `synthesizer` | solo `verify_fact` (acotada: verifica afirmaciones simples; las complejas devuelven «enrutar al coordinador») |

### El ejercicio

Lo que cambia en el código de cada variante `--anti` (solo cambian las listas de tools de los subagentes; los prompts son los mismos):

- **`todas`:** el sintetizador recibe las cinco tools del servidor.
- **`fetch_url`:** el investigador recibe `fetch_url` en lugar de `load_document`.
- **`sin_verify`:** el sintetizador no recibe ninguna tool (`tools=[]`).

Antes de las medidas, cada ejecución imprime una línea `[esperado]` con la hipótesis de partida escrita en el código. Es una predicción, no un resultado: contrástala con la tuya y con las medidas.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, cada subagente tiene solo las tools de su rol. ¿Qué no puede hacer el sintetizador, decida lo que decida el modelo? ¿Qué sigue dependiendo del modelo?
2. (guía) Con `todas` (el sintetizador recibe las cinco tools del servidor), ¿qué riesgo hay? ¿Esperas verlo en este ejercicio, donde su prompt trae todo lo que necesita?
3. (guía) Con `fetch_url` (abre cualquier URL) en lugar de `load_document` (comprueba que la URL es un documento), ¿de quién depende que no entren en los hallazgos páginas que no son documentos? ¿Esperas el mismo resultado en todas las repeticiones?
4. (guía) `verify_fact` solo resuelve las afirmaciones simples y devuelve las complejas al coordinador. ¿Por qué no dar al sintetizador las tools de búsqueda, para que resuelva también las complejas?
5. (módulo) Con `sin_verify` (el sintetizador no tiene ninguna tool), ¿esperas más delegaciones o menos que sin `--anti`? ¿Quién verificará las afirmaciones?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/03_tools_entre_roles.py                      # correcta
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti todas         # el sintetizador con todas las tools
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti fetch_url     # tool genérica en el investigador
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti sin_verify    # sin tool cross-role
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --repeat 3 --budget 0.60
```

**Si ejecutas:** las tools por rol y las medidas sobre el registro se prueban sin modelo; ejecutar sirve para ver qué hace cada rol con las tools que recibe.

La salida muestra las llamadas por agente, las llamadas fuera de rol (la vara es la configuración correcta), las URLs que no son documentos abiertas con `fetch_url`, las rechazadas por `load_document`, las delegaciones y las llamadas a `verify_fact`, con cuántas volvieron al coordinador.

### Qué observar

Por variante, las llamadas fuera de rol, las URLs que no son documentos abiertas o rechazadas, las delegaciones y las llamadas a `verify_fact` que vuelven al coordinador.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Ni buscar ni cargar documentos: no tiene esas tools, y eso lo fija la configuración (TS 2.3-S1). Del modelo depende que llame a `verify_fact` y lo que haga el coordinador con lo que le vuelve.
- **P2** Que use mal tools ajenas a su especialidad, como un agente de síntesis que se pone a buscar (TS 2.3-K2). Aquí no hubo señal: recibe todo en su prompt y no las tocó. En el examen manda la guía.
- **P3** Del modelo: la tool genérica ya no rechaza nada. No fue igual: en 2 de 3 repeticiones abrió las cuatro páginas que no son documentos y en la otra, ninguna. Por eso se cambia la tool genérica por una restringida (TS 2.3-S2).
- **P4** Porque cada rol recibe solo lo que necesita: la tool acotada cubre lo frecuente y lo complejo sigue pasando por el coordinador (TS 2.3-K3, 2.3-S3). Con las tools de búsqueda volvería el riesgo de P2. Aquí, 5 llamadas a `verify_fact` y 2 devueltas por complejas.
- **P5** Menos: sin tool con la que verificar, el coordinador casi nunca invoca al sintetizador (1 de 6) y resuelve las afirmaciones él. La hipótesis de partida del módulo era la contraria.

Coordinador Sonnet 5.5, subagentes Haiku 5.5, 3 repeticiones:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | 0 fuera de rol, 2 delegaciones, 5 llamadas a `verify_fact` y 2 devueltas al coordinador por complejas, ~0,05 $ | cada rol hace lo suyo; la tool acotada cubre lo frecuente y lo complejo sube |
| `todas` | **sin señal**: 0 fuera de rol en las 3 ejecuciones, y tampoco con Haiku 4.5 (3 más); el sintetizador solo usó `verify_fact` | la guía dice que tiende a malusarlas; aquí recibe en el prompt todo lo que necesita y no las toca |
| `fetch_url` | en 2 de 3 ejecuciones abrió las 4 páginas que no son documentos; en la 3.ª no abrió ninguna | la tool genérica no impide meter login o seguimiento en los hallazgos |
| `sin_verify` | 0 llamadas a `verify_fact`; el sintetizador se invocó en 1 de 6 ejecuciones (1 delegación en vez de 2 en las otras 5); coste menor (~0,03 $) | sin tool acotada, la verificación se la queda el coordinador, no el sintetizador |

Notas:

- **`todas`:** la señal que describe la guía (un agente de síntesis que se pone a buscar) no apareció. El sintetizador recibe en su prompt todo lo que necesita y solo verifica; las tools extra están ahí, pero no le hacen falta. Es probable que se manifestara si el sintetizador recibiera información incompleta (hipótesis sin comprobar). Lo estable es lo que se mide con la configuración: qué tools tiene cada rol. En el examen manda la guía.
- **`fetch_url`:** «fuera de rol» cuenta aquí todas las llamadas del investigador a `fetch_url`, incluidas las de documentos válidos, porque esa tool no es de su rol; la señal propia es «URLs no documento abiertas». Con la configuración correcta el investigador no llegó a intentar abrir ninguna URL que no fuera un documento, así que `load_document` no tuvo que rechazar nada.
- **`sin_verify`:** la hipótesis de partida era «más delegaciones»; lo observado es lo contrario. Sin una tool con la que verificar, el coordinador casi nunca invoca al sintetizador (1 de 6 ejecuciones): redacta el informe y resuelve las afirmaciones él, con lo que el investigador le devuelve. La verificación pierde la herramienta determinista y pasa a ser un juicio del coordinador, algo que este módulo no mide.
- **Barrera del coordinador (revisión independiente):** `tools=["Agent"]` solo limita las tools integradas; las del servidor MCP seguían visibles para el coordinador, y «no busques tú» en su prompt es una petición. Comprobado: sin barrera y **pidiéndoselo expresamente**, el coordinador llamó él mismo a `verify_fact` y obtuvo el resultado. Ahora un hook `PreToolUse` (`coordinator_gate`) deniega esas tools al agente principal y deja pasar a los subagentes (traen `agent_id`): con él, la misma petición recibió el rechazo del hook y los subagentes siguieron usando las suyas. En 5 ejecuciones normales con la barrera, el coordinador no intentó ninguna (0 intentos), así que no se ha visto que la intente por su cuenta: la barrera garantiza la medida, no corrige una señal observada.
- **`tools=[]` en un subagente significa «ninguna tool»:** forzando la delegación en `sin_verify`, el sintetizador respondió «SIN TOOLS» (2 de 2) y no llamó a ninguna.
- Las tools por rol, las medidas sobre el registro y las opciones del coordinador se prueban sin modelo en `tests/test_app3_03_tools_entre_roles.py`.

**Para pensar (sin evaluación):** con `todas`, ¿sería más probable que el sintetizador se pusiera a buscar si su prompt no trajera todo lo que necesita? Es una hipótesis sin comprobar: el módulo no trae una variante con información incompleta, así que no cuenta como predicción.
</details>

### Pregunta tipo examen

Un agente de síntesis recibe todas las tools del sistema y, aunque su cometido es redactar, empieza a hacer búsquedas que duplican el trabajo del agente investigador. ¿Qué cambio es el más adecuado?

- A. Reforzar su *system prompt* con «no hagas búsquedas, solo redacta» y mantener todas las tools, por si alguna vez las necesita.
- B. Fusionar al investigador y al sintetizador en un único agente con todas las tools, para que nadie duplique el trabajo del otro.
- C. Dejarle solo las tools de su rol, con una de verificación acotada para las comprobaciones simples que necesita a menudo.
- D. Quitarle todas las tools y hacer que cada comprobación, simple o compleja, pase por el coordinador para centralizar el control.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Un agente con tools fuera de su especialización tiende a malusarlas (TS 2.3-K2); la solución es el acceso acotado, con las tools de su rol (TS 2.3-S1) y una tool cross-role muy limitada para las necesidades de alta frecuencia (TS 2.3-K3, TS 2.3-S3); los casos complejos siguen pasando por el coordinador. A pide por prosa lo que la configuración debería garantizar, y el agente conserva las tools que malusa; B deja un agente con todas las tools, lo contrario del acceso acotado (TS 2.3-K3); D elimina la tool acotada, y cada verificación simple pasa a depender del coordinador: es el coste que la tool acotada de TS 2.3-S3 evita.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 2.3-S2.** Un agente de documentación tiene una tool `fetch_url` que abre cualquier dirección, y a veces carga páginas de inicio de sesión como si fueran documentos. ¿Qué cambio encaja?

- A. Añadir al prompt la lista de las direcciones que no debe abrir en ningún caso.
- B. Darle además una tool de búsqueda web, para que compruebe antes cada dirección.
- C. Dejarle `fetch_url` y pedirle que descarte después lo que no parezca un documento.
- D. Sustituirla por una tool acotada, como `load_document`, que valide la dirección.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**D.** Una tool genérica se sustituye por una alternativa restringida que valida su entrada, como `load_document` en lugar de `fetch_url` (TS 2.3-S2). A y C dejan el filtro en manos del modelo; B añade otra tool fuera de su rol.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 04 · Errores entre agentes

> **Qué vas a hacer:** Ver qué le llega al coordinador cuando una de las fuentes de un subagente falla por *timeout*, y qué entrega a partir de ahí.
>
> **Necesitas antes:** El [módulo 01](#01--coordinador-y-subagentes) y el [módulo 03](#03--tools-entre-roles) (mismo patrón de coordinador, barrera y subagente).
>
> **Modo:** Ejecución obligatoria (el resultado parcial con la brecha anotada solo se ve ejecutando).

### Antes de empezar

Los términos comunes (coordinador, subagente, error estructurado, reintentable, brecha) están en el [glosario](../docs/glosario.md).

- **El sistema:** el coordinador tiene un único subagente, `researcher`, con una sola tool, `query_source`. La petición pide un informe de calidad del servicio con seis fuentes sintéticas (`fuentes_investigacion.json`): tres responden con contenido, una responde **vacía** (no tiene nada que decir), una falla con *timeout* en todas las consultas y la sexta, `SRC-REDES`, es transitoria (ver «El ejercicio»). La petición no dice cuál es cuál.
- **Informe del subagente:** por cada fuente, un objeto JSON con `source_id`, `status` (`ok`, `empty` o `failed`) y `findings`. Si falla, también `error_context` con cuatro campos: `failure_type`, `attempted`, `partial_results` y `alternatives`.
- **Reintento local:** el prompt del subagente le deja repetir, con un límite, la consulta que falla con un error reintentable. Lo que haga después depende del modelo.
- **Vacío frente a fallo:** una fuente que responde con `total: 0` es un resultado válido; una que da *timeout* no ha dicho nada. Las medidas del módulo los distinguen leyendo los resultados de la tool, sin modelo.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `query_source` | `source_id` | el informe de la fuente en `content`, con su id, nombre y fecha en `metadata`; `total: 0` si la fuente responde sin contenido; un error transitorio reintentable si hay *timeout*; un error de validación si la fuente no existe |

### El ejercicio

Qué cambia en el código de cada variante `--anti`:

- **`generico`:** el investigador reintenta igual que en la correcta (hasta 2 veces); lo único que cambia es lo que devuelve si la fuente sigue fallando: `status: failed` con el mensaje «búsqueda no disponible» y nada más, sin `error_context`. El coordinador es el mismo que en la correcta.
- **`silenciar`:** lo hace el **código**, no el prompt. El servidor se construye con `silence_failures=True` y el *handler* de `query_source` devuelve `total: 0` y `results: []` como éxito cuando la fuente da *timeout*. El investigador y el coordinador usan los mismos prompts que en la correcta.
- **`abortar`:** el prompt del coordinador añade que, si alguna fuente falla, no entregue nada parcial y responda solo `INVESTIGACIÓN ABORTADA`.

Además, la petición incluye una sexta fuente, `SRC-REDES`, **transitoria**: falla con *timeout* la primera vez que se consulta en una ejecución y responde bien a la siguiente (el estado va por ejecución y solo la ve este módulo).

Cada ejecución imprime una línea `[esperado]` con la hipótesis escrita en el código. Es una predicción, no un resultado.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, un informe `failed` trae `error_context` con sus cuatro campos. ¿Qué puede decidir el coordinador con ellos que no podría con un `failed` a secas?
2. (guía) Una fuente que responde sin resultados llega como `empty`, no como `failed`. ¿Por qué importa esa distinción para el coordinador?
3. (guía) `SRC-REDES` falla solo la primera vez que se consulta. ¿Qué debe hacer el subagente con ese fallo? ¿Qué le llega de él al coordinador?
4. (guía) Con `generico`, al coordinador solo le llega «búsqueda no disponible». ¿Qué información pierde para decidir cómo recuperarse?
5. (módulo) Aquí solo hay una fuente caída y ninguna alternativa que consultar. Con `generico`, ¿esperas que el coordinador haga algo distinto que sin `--anti`?
6. (guía) Con `silenciar`, el *handler* convierte el *timeout* en un resultado vacío antes de que lo vea el subagente. ¿Qué sabe entonces el coordinador de esa fuente? ¿Puede anotar la brecha?
7. (guía) Con `abortar`, el coordinador no entrega nada si una fuente falla. ¿Qué se pierde, sabiendo que las demás fuentes ya habían respondido?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py                    # correcta
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti generico    # fallo sin contexto
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti silenciar   # el handler traga el fallo
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti abortar     # un fallo tumba la investigación
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --repeat 3 --budget 0.60
```

**Si ejecutas:** las medidas y la forma del contexto de error se prueban sin modelo; ejecutar sirve para ver la señal de la guía: un resultado parcial con la brecha anotada y la fuente transitoria recuperada en local. Con `--repeat 3` cada variante cuesta unos 0,06–0,08 $.

### Qué observar

Las consultas por fuente y los reintentos locales, la cobertura según los informes del subagente, si el contexto de error está completo, los fallos que el *handler* tragó, si la brecha aparece anotada en el resultado, las decisiones del coordinador (cuántas veces delega y si menciona alternativas) y si el resultado es parcial o abortado.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Cómo recuperarse: repetir con otra consulta, probar una vía alternativa o seguir con lo parcial y anotar la brecha. Para eso necesita la clase de fallo, qué se consultó, qué se llegó a obtener y qué otras vías quedan (TS 5.3-K1, 5.3-S1).
- **P2** Porque un vacío no es un fallo: una consulta que funcionó y no encontró nada ya es una respuesta, y no hay nada que recuperar ni reintentar (TS 5.3-K2, 5.3-S2).
- **P3** Reintentarlo en local y, si se recupera, no propagarlo (TS 5.3-S3). Al coordinador le llegó un informe `ok`, sin brecha, en 3 de 3.
- **P4** Qué se intentó, qué se obtuvo y qué alternativas hay: justo el contexto que necesitaba (TS 5.3-K3).
- **P5** No hizo nada distinto: una delegación y la brecha anotada, igual que sin `--anti`. Con una sola fuente caída no había decisión que ese contexto pudiera mejorar. En el examen manda la guía.
- **P6** Que respondió vacía: para él el fallo no existe. La brecha solo salió anotada en 1 de 3, y mal diagnosticada. Devolver un vacío como si fuera un éxito es uno de los dos anti-patrones (TS 5.3-K4).
- **P7** Todo el trabajo de las fuentes que sí respondieron: es el anti-patrón opuesto, terminar el flujo entero por un solo fallo (TS 5.3-K4). Lo adecuado es entregar el resultado parcial con la cobertura anotada (TS 5.3-S4).

Coordinador Sonnet 5.5, subagente Haiku 5.5, 3 ejecuciones por variante (`--repeat 3`), ~0,26 $ las cuatro variantes:

| Variante | Señal observada (3 ejecuciones) | Qué dice |
| :--- | :--- | :--- |
| correcta | 1 delegación del coordinador en 3 de 3; informe `failed` con `error_context` completo, brecha de `SRC-MONITOR` anotada y cifras de las fuentes que respondieron, en 3 de 3; **`SRC-REDES` falló una vez y se recuperó con el reintento local en 3 de 3**, sin que el coordinador la viera como fallo (informe `ok`, ninguna brecha anotada) | lo transitorio lo resuelve el subagente y no llega al coordinador; lo que no resuelve llega con su contexto y la cobertura queda dicha |
| `generico` | sin `error_context` en 3 de 3; 2–3 consultas a la fuente que falla, todas del subagente; **1 delegación del coordinador en 3 de 3**; brecha anotada y cifras en 3 de 3 | **sin efecto visible sobre el coordinador**: hizo lo mismo que en la correcta (ver la medición anterior) |
| `silenciar` | fallo tragado por el *handler* en 3 de 3: 1 sola consulta, sin reintentos, la fuente llega como `total: 0`; brecha anotada en **1 de 3** | en esa ejecución el informe dice «falta información sobre la monitorización de red» y, a la vez, «respondió vacía, no es un fallo»: anota un hueco, pero lo diagnostica mal. En las otras dos, la fuente que falló se da por vacía |
| `abortar` | `INVESTIGACIÓN ABORTADA` en 3 de 3, sin cifras ni brecha anotada, con las demás fuentes ya respondidas | un fallo tumba el trabajo de las fuentes que sí respondieron |

Notas:

- **`generico`:** la guía dice que el mensaje genérico esconde al coordinador el contexto que necesita (TS 5.3-K3). Aquí no cambió su decisión. Con una sola fuente caída y ninguna alternativa real que elegir, probablemente no había nada que ese contexto pudiera mejorar; es una hipótesis, no algo medido.
- **Medidas:**
  - «Brecha anotada» (`gap_noted`) pide la fuente y una palabra de falta en la misma frase, y descarta las negaciones pegadas a la palabra de fallo («no falló», «sin brecha»). Una versión anterior de la medida también descartaba «no respondió por timeout» y «sin datos por timeout», que son brechas: se corrigió después de registrar las cifras de arriba y no se recalcularon. Sigue leyendo palabras: no distingue una brecha bien diagnosticada de una mal diagnosticada, como en `silenciar`.
  - El fallo tragado se mide en los resultados de la tool, sin modelo (`swallowed_sources`), y las vacías legítimas se cuentan aparte.
  - «Resultado parcial» pide cifras de las fuentes pedidas que respondieron y no cuenta fechas.
  - «Alternativa o reintento mencionados» es laxa (palabras sueltas): léela junto al texto.
- **Reintento local:** no cuenta como error del coordinador (`coordinator_errors` = 0).
- **Medición anterior** (antes de las correcciones de la revisión; ya no se reproduce con el código actual):
  - `generico` decía además «no reintentes». El coordinador **volvió a delegar en 3 de 3** («Reintentar SRC-MONITOR»), con el mismo *timeout*, y costó algo más (0,026–0,030 $ frente a 0,022–0,024 $). Al añadir el reintento local, la segunda delegación desapareció: la causa era que nadie había reintentado (TS 5.3-S3), no el mensaje genérico.
  - `silenciar` lo hacía el prompt del subagente, no el código. El informe JSON daba la fuente por `ok` sin hallazgos, pero el resultado final anotó la brecha igualmente en las 7 ejecuciones. En una ejecución diagnóstica, el coordinador había pedido en la delegación «si una fuente falla o está vacía, dilo explícitamente». Una explicación posible es que esa instrucción pesara más que la definición del subagente, pero no se comprobó. Por eso la variante actual produce el vacío en el código.
- Las medidas, la forma del contexto de error y las opciones se prueban sin modelo en `tests/test_app3_04_errores_entre_agentes.py`.
</details>

### Pregunta tipo examen

Un coordinador delega búsquedas en dos subagentes. Tras su recuperación local, los dos devuelven lo mismo: `{"status": "failed", "message": "búsqueda no disponible"}`. En un caso la fuente dio *timeout*; en el otro, la consulta estaba mal formada y fallará siempre. El coordinador trata los dos fallos igual y el informe solo dice «faltan datos». ¿Qué cambio le permite decidir bien en cada caso?

- A. Que los subagentes reintenten hasta que la fuente responda, para que el coordinador no reciba nunca un fallo que decidir.
- B. Que los subagentes devuelvan una lista vacía en esos casos, para que el coordinador siga con las demás fuentes sin pararse.
- C. Que cada subagente devuelva el tipo de fallo, la consulta que intentó, lo que llegó a obtener y las alternativas.
- D. Que el coordinador repita las dos delegaciones con el mismo encargo y cancele la investigación si vuelven a fallar.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Un estado genérico esconde al coordinador el contexto que necesita (TS 5.3-K3). Con el tipo de fallo, lo intentado, lo obtenido y las alternativas, puede decidir cómo recuperarse en cada caso (TS 5.3-K1, S1), y el informe puede anotar qué queda sin cubrir en vez de un «faltan datos» (TS 5.3-S4). La recuperación local ya se hizo: al coordinador solo se propaga lo que el subagente no pudo resolver (TS 5.3-S3, TS 2.2-S3).

- **A** sigue sin dar al coordinador el contexto que le falta (TS 5.3-K3), y el subagente ya había hecho su recuperación local.
- **B** convierte dos fallos en vacíos válidos (TS 5.3-K2, K4): el informe dirá que esas fuentes no tenían nada.
- **D** repite a ciegas lo que ya falló y, si vuelve a fallar, tira el trabajo de las demás fuentes (TS 5.3-K4).

**Inferencia propia:** que el *timeout* pueda merecer otro intento o una fuente alternativa y la consulta mal formada no se arregle repitiéndola es la lectura de este módulo, a partir de la diferencia entre errores reintentables y no reintentables (TS 2.2-K4, en `app1/04`). La guía no resuelve este caso concreto.

**Producto observado (no evaluable):** en este módulo, con una sola fuente caída, el mensaje genérico no cambió lo que hizo el coordinador (Paso 3). No cambia la respuesta de examen: la pregunta plantea el caso en que sí hay que elegir.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 5.3-S2.** Un subagente consulta dos fuentes: una responde sin resultados y la otra da *timeout*. ¿Cómo debe informar al coordinador?

- A. Las dos como «sin datos», para que el informe final no se alargue con detalles.
- B. Las dos como fallo, para que el coordinador vuelva a delegar ambas consultas.
- C. Separando el vacío válido del fallo de acceso, para que decida sobre cada una.
- D. Solo la que respondió, y omitir la otra para no detener la investigación.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**C.** El informe de errores distingue un fallo de acceso de un resultado vacío válido, para que el coordinador tome la decisión adecuada en cada caso (TS 5.3-S2, K2). A y B los igualan, en un sentido o en el otro; D esconde el fallo.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 05 · Procedencia entre agentes

> **Qué vas a hacer:** Ver si la fuente y la fecha de cada cifra llegan hasta el informe final cuando dos fuentes discrepan, y si un hallazgo clave se pierde en mitad de un texto largo.
>
> **Necesitas antes:** El [módulo 04](#04--errores-entre-agentes) (mismo servidor de fuentes) y el [módulo 03](#03--tools-entre-roles) (mismo patrón de coordinador y barrera).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar; lo medido está en el Paso 3).

### Antes de empezar

Los términos comunes (coordinador, subagente, procedencia, *lost in the middle*) están en el [glosario](../docs/glosario.md).

- **El sistema:** el coordinador tiene dos subagentes: `researcher` (consulta las fuentes con `query_source`) y `synthesizer` (sin tools, redacta con lo que le pasen en el prompt). Las fuentes son las sintéticas de `fuentes_investigacion.json`.
- **Parte `conflictos` (por defecto):** seis fuentes en tres pares de cifras distintas (**tiempo de resolución**, **satisfacción** y **tickets reabiertos**), cada una con su fecha de publicación y el contexto metodológico que dé la fuente (periodo, método, muestra o población); todas coinciden en el total de tickets cerrados. Los informes van en secciones con encabezado. La petición no dice nada de los pares.
- **Afirmación estructurada:** el investigador devuelve una lista JSON donde cada afirmación separa el contenido (`claim`, `figure`, `unit`, `context`) de los metadatos (`source_id`, `published_at`, `location`, `excerpt` y `relevance`). `context` lleva el periodo, el método, la muestra o la población que dé la fuente; `location`, la sección de la fuente; `excerpt`, la frase literal que respalda la afirmación, y `relevance`, una puntuación de 0 a 1. El código comprueba esa forma y que la fecha, la sección y el fragmento coinciden con la fuente.
- **Decisión del coordinador:** antes de llamar al sintetizador, el coordinador decide para cada magnitud en conflicto si el contexto la explica o queda disputada, y pasa esa decisión en el prompt del sintetizador junto a las afirmaciones.
- **Parte `medio`:** el informe `SRC-LARGO` (unas 1.500 palabras) con una sola frase importante en mitad. `--texto` elige la técnica de 5.1 que aplica el servidor al informe: `con_resumen` antepone una línea con el hallazgo clave (sin quitarlo de su sitio), `con_encabezados` pone un encabezado `##` antes de cada una de seis secciones (el hallazgo queda dentro de «Incidencias y causas», sin abrir sección) y `encabezados_y_resumen` aplica las dos.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `query_source` | `source_id` | igual que en el [módulo 04](#04--errores-entre-agentes): el informe en `content` y su id, nombre y fecha en `metadata` |

### El ejercicio

Qué cambia en el código de cada variante:

- **`sin_procedencia`:** el prompt del investigador le pide prosa verbosa (uno o dos párrafos largos por fuente, con su razonamiento paso a paso), sin listas, sin identificadores de fuente ni fechas, en vez de afirmaciones con metadatos.
- **`promedio`:** el prompt del sintetizador le pide una única cifra consolidada, el promedio, cuando dos fuentes discrepan.
- **`formato_uniforme`:** el prompt del sintetizador pide todo en prosa continua.
- **`inventar_explicacion`:** el sintetizador explica siempre por qué difieren las cifras (periodo, método, muestra o población), aunque el contexto no lo explique; es el control positivo de la medida del par sin explicación.
- **`--parte medio --texto sin_resumen|con_resumen|con_encabezados|encabezados_y_resumen`:** el mismo informe largo, sin tratamiento, con la línea de resumen al principio, con encabezados de sección o con las dos cosas.

El código mide sin modelo cuántas cifras del informe llevan su fuente en la misma frase o fila, si la ubicación y el fragmento llegan al informe, si la decisión del coordinador aparece en el prompt del sintetizador, si algún conflicto aparece fusionado en un promedio, si la tabla lleva las cifras de los pares, cuánto pesa lo que llega al sintetizador, qué contexto usa el informe para explicar cada diferencia, si deja como disputado lo que el contexto no explica y si el resumen del informe largo cita el hallazgo clave.

**Los tres pares de cifras.** Las fuentes traen tres pares de cifras que no coinciden. En dos, los metadatos explican la diferencia: en uno cambian el método y la muestra; en el otro, el periodo y la población. En el tercero, las dos fuentes coinciden en periodo, método y población y aun así dan cifras distintas: nada lo explica. No hace falta abrir el archivo de datos.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, el investigador devuelve cada afirmación con su fuente, su fecha y el fragmento que la respalda. ¿Qué se perdería si en su lugar devolviera un resumen en prosa de lo que encontró?
2. (módulo) Con `sin_procedencia` (prosa larga, sin identificadores de fuente ni fechas), ¿dónde esperas ver el daño: en lo que devuelve el investigador, en el informe final o en ambos?
3. (guía) Con `promedio` (una única cifra consolidada cuando dos fuentes discrepan), ¿qué cifra tendrá el informe que no sale de ninguna fuente? ¿Qué debería hacer el informe en su lugar?
4. (guía) En los dos pares cuya diferencia explican los metadatos, ¿qué debería hacer el informe con las dos cifras? ¿Qué información tiene que viajar con cada cifra para que pueda hacerlo?
5. (guía) En el par que nada explica, ¿qué debería hacer el informe con las dos cifras? ¿Qué error delataría ese par?
6. (guía) El coordinador decide cómo tratar cada par antes de llamar al sintetizador. ¿Qué tiene que haberle llegado del análisis para poder decidir? ¿Qué pasaría si el investigador se quedara con una de las dos cifras?
7. (guía) Con `formato_uniforme` (todo en prosa continua), ¿qué pierde el informe a la hora de presentar las cifras comparables?
8. (módulo) Con `inventar_explicacion` (la orden de explicar siempre por qué difieren las cifras), ¿esperas que el sintetizador invente una causa para el par que nada explica?
9. (guía) En la parte `medio`, el hallazgo clave está en mitad de un informe largo. ¿Qué riesgo corre al resumirlo? ¿Por qué ayudaría anteponer una línea con ese hallazgo?
10. (módulo) El informe de `medio` tiene unas 1.500 palabras. Sin ningún tratamiento, ¿esperas que el resumen pierda el hallazgo clave?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/05_procedencia.py                                        # correcta
uv run python app3_sistema_multiagente/05_procedencia.py --anti sin_procedencia                 # el investigador devuelve prosa
uv run python app3_sistema_multiagente/05_procedencia.py --anti promedio                        # cifras en conflicto fusionadas
uv run python app3_sistema_multiagente/05_procedencia.py --anti formato_uniforme                # todo en prosa, sin tabla
uv run python app3_sistema_multiagente/05_procedencia.py --anti inventar_explicacion            # explica siempre (control positivo)
uv run python app3_sistema_multiagente/05_procedencia.py --anti inventar_explicacion --rol-subagente enforcement  # el mismo control con Haiku 4.5
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio                          # hallazgo en mitad, sin resumen
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio --texto con_resumen      # con la línea de resumen al principio
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio --texto con_encabezados  # con encabezados de sección
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio --texto encabezados_y_resumen
```

**Si ejecutas:** las medidas (comprobador de procedencia, detector de cifras fusionadas, forma de las afirmaciones) se prueban sin modelo; ejecutar sirve para ver qué hace el modelo con ellas. Con `--repeat 3`, una variante de `conflictos` cuesta unos 0,20 $ y una variante de `medio`, unos 0,19 $ (la parte `medio` ya no es barata: ~0,065 $ por ejecución).

### Qué observar

Las afirmaciones estructuradas sin problemas, las fuentes que llegan al sintetizador, las cifras con su fuente en la frase, los conflictos presentados como disputados, las cifras fusionadas, qué contexto (periodo, método, muestra, población) usa el informe para cada par y, en la parte `medio`, si el resumen cita el hallazgo clave.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** La atribución: qué afirmación viene de qué fuente (TS 5.6-K1). Ese emparejamiento es una estructura que el sintetizador tiene que recibir y conservar (TS 5.6-K2, 5.6-S1). Aquí, las 40 afirmaciones llegaron con ubicación y fragmento válidos.
- **P2** En lo que devuelve el investigador: 0 afirmaciones estructuradas. En el informe final casi no se notó, porque la prosa del modelo ya nombraba la fuente y la fecha.
- **P3** El promedio (22 horas; 3,85 sobre 5). Debería anotar las dos cifras, cada una con su fuente, en vez de quedarse con una o fundirlas (TS 5.6-K3). La fusión apareció en 1 de 3.
- **P4** Presentarlas con su contexto, para que la diferencia no parezca una contradicción. Con cada cifra tiene que viajar su fecha, para que una diferencia temporal no se lea como contradicción (TS 5.6-K4, 5.6-S4), y el contexto de su fuente, como el método o la muestra, con la ubicación de donde sale (TS 5.6-S2, 5.1-S5).
- **P5** Dejarlo como disputado, separado de lo bien establecido y respetando cómo lo describe cada fuente (TS 5.6-S2). Delataría un informe que inventa una causa.
- **P6** Los dos valores en conflicto, incluidos y anotados: el análisis no elige, y el coordinador decide cómo reconciliarlos antes de pasarlos a la síntesis (TS 5.6-S3). Si el investigador eligiera, el conflicto desaparecería antes de que nadie pudiera verlo. Su decisión fue acertada en 9 de 9 pares.
- **P7** La tabla: salió en 0 de 3. Cada clase de contenido se presenta a su manera, las cifras en tabla, en vez de pasarlo todo a un formato único (TS 5.6-S5).
- **P8** Con el modelo de la medida no la inventó (0 de 3). Con el otro rol de subagente la inventó en el borrador en 1 de 3, y el coordinador la quitó antes del informe final: el fallo solo se ve midiendo el borrador.
- **P9** Que el modelo se lo salte: en una entrada larga atiende bien el principio y el final y puede perder lo del medio (TS 5.1-K2). La línea antepuesta lo lleva al principio, donde sí atiende: se abre con un resumen de lo importante y el detalle se ordena con encabezados (TS 5.1-S4).
- **P10** No lo perdió: lo citó en 12 de 12, con y sin tratamiento. Con este tamaño no hay señal; en el examen manda la guía.

Coordinador Sonnet 5.5, subagentes Haiku 5.5, 3 ejecuciones por variante; ~1,18 $ en `conflictos` (incluidos 0,13 $ de una prueba que no valió) y 0,78 $ en `medio`:

| Variante | Señal observada (3 ejecuciones) | Qué dice |
| :--- | :--- | :--- |
| correcta | afirmaciones sin problemas (15/15, 13/13 y 12/12), con ubicación y fragmento literal válidos en las 40; las 6 fuentes llegan al sintetizador con su afirmación; **decisión del coordinador acertada en los 3 pares de las 3 ejecuciones (9/9)**; ninguna cifra fusionada; el par que el contexto no explica, disputado en 3 de 3 y atribuido a la fecha o al método en 0 de 3 | la estructura conserva la procedencia y el coordinador decide bien antes de la síntesis |
| correcta: ubicación y fragmento en el informe final | **0 de 6 fuentes en las 3 ejecuciones** (ni el título de la sección ni un tramo del fragmento) | llegan al sintetizador, pero no al informe: los parafrasea en una columna de método o población |
| correcta: tabla con las cifras de los pares | tabla en 3 de 3; los tres pares con sus dos cifras dentro en **2 de 3** (en la otra, la satisfacción queda fuera) | hay tabla, pero no siempre con todas las cifras |
| `formato_uniforme` | **tabla en 0 de 3** | sin la instrucción por tipo, todo sale en prosa |
| `sin_procedencia` (prosa larga) | 0 afirmaciones estructuradas; fuente en la frase en 7/7, 4/7 y 7/7 cifras del informe final; decisiones del coordinador acertadas en 8 de 9 | la pérdida está en lo que devuelve el investigador, **no en el informe final**: la prosa ya nombraba fuente y fecha |
| tamaño: estructurado frente a prosa larga | lo que devuelve el investigador: 8.781, 10.045 y 9.007 caracteres frente a 6.597, 8.601 y 9.134; lo que llega al sintetizador: 3.626, 5.703 y 3.320 frente a 2.594, 2.818 y 3.059 | **al revés de lo esperado**: la salida estructurada pesa más; con estos tamaños, 5.1-S6 no se ve en el volumen |
| `promedio` | fusionó en **1 de 3** (22 horas y 3,85 sobre 5, con las cifras originales también presentes) | señal del anti-patrón, pero no estable |
| `inventar_explicacion` (control positivo), subagentes Haiku 5.5 | par sin explicación atribuido en **0 de 3**, disputado en 3 de 3 | el sintetizador no inventó la explicación |
| `inventar_explicacion`, subagentes Haiku 4.5 (`--rol-subagente enforcement`, 3 + 3 ejecuciones, ~0,60 $) | informe final: atribuido en **0 de 6**, disputado en 6 de 6. Borrador del sintetizador (3 ejecuciones medidas): **inventó la causa en 1 de 3** («criterios distintos para definir qué es un ticket reabierto»), y en otra de las 3 primeras el coordinador dice que quitó «las posibles causas… como una lista de hipótesis» | **el fallo aparece en el borrador y el coordinador lo quita**: medido solo en el informe final, el control no se ve |
| `medio` sin resumen, con resumen, con encabezados y con las dos cosas (3 de cada) | el resumen citó el 41 % en **12 de 12** | **sin señal de *lost in the middle*** |

Notas:

- **Parte `medio`:** el informe (unas 1.500 palabras, ~9.400 caracteres) lleva relleno variado, con porcentajes de distracción del 4 al 18 %. Aun así, el 41 % es la cifra más alta y la única de su tipo, así que puede destacar por saliencia y no por su posición. Que el efecto aparezca con un texto más largo, otro modelo o distracciones más parecidas es una hipótesis sin comprobar; no se forzó.
- **`inventar_explicacion` con Haiku 4.5:** se pide con `--rol-subagente enforcement`, el rol que ya existe para pruebas puntuales con otro modelo, sin tocar `.env`. Un primer intento cambió `CCARF_MODEL_SUBAGENT` en el entorno, que `.env` sobrescribe, y no contó. Con el rol, el coordinador (Sonnet 5.5) revisó el borrador y quitó la explicación inventada antes del informe final. Por eso el módulo mide también el borrador (`[medida] el mismo par en el borrador del sintetizador`). En la ejecución en que la detectó, la medida acertó por una palabra equivocada: tomó «población», que aparece en la descripción de las dos fuentes, y no la causa inventada, que habla de criterios de definición. La medida del par sin explicación sigue siendo laxa: léela junto al texto.
- **Medidas** (léelas junto al texto):
  - `conflicts_presented` pide las dos cifras y una frase con una palabra de desacuerdo, y descarta las negaciones pegadas a ella («no hay discrepancias»). Una frase que nombra un par (tema, fuente o cifra) solo cuenta para ese par; una que no nombra ninguno («las fuentes discrepan») cuenta para todos. Puede dar falsos negativos si el informe usa otras palabras («no comparables»). Las cifras registradas arriba se midieron con la versión anterior, que era global y con una negación más amplia; no se recalcularon.
  - La decisión del coordinador (`coordinator_decisions`) se lee del prompt del sintetizador, donde el coordinador la escribe en el formato que le fija su prompt («explicada por…» o «disputada»). La negación manda: «no explicada» o «no está explicada» cuentan como disputada. Fuera de ese formato la lectura es laxa.
  - `explanation_found` mira qué contexto usa el informe en las líneas que nombran cada par. Ya no toma «la tabla muestra» ni «se espera confirmar» por contexto, ni «el mismo método» por atribución, pero sigue leyendo palabras.
  - `merged_figures` detecta promedios con su unidad («22 horas», «≈4 sobre 5», «10 %»), no cualquier forma de fusionar.
  - `sources_passed` pide que el id de la fuente vaya con su afirmación en el prompt del sintetizador.
- **Medición anterior** (antes de las correcciones de la revisión: sin ubicación, fragmento ni decisión del coordinador, con un relleno repetido en el informe largo y medidas más laxas): la correcta explicó los dos pares explicables y no atribuyó el tercero en ninguna de las 9 ejecuciones de `conflictos`. La medida dio 3 «atribuidos», pero leyendo el texto eran falsos positivos («los mismos 1.240 tickets y el mismo método»). `promedio` fusionó en 1 de 3 (22 horas y 9,85 % de reabiertos). La parte `medio` citó el 41 % en 12 de 12.
- Las medidas, la forma de las afirmaciones y las opciones se prueban sin modelo en `tests/test_app3_05_procedencia.py`.

**Para pensar (sin evaluación):** ¿aparecería el efecto de `medio` con un informe mucho más largo o con distracciones más parecidas al hallazgo? No se ha medido.
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un sistema multiagente prepara informes de mercado. Dos subagentes leen fuentes distintas y devuelven resúmenes en prosa; un sintetizador redacta el informe. En el último, la cuota de un producto aparece como 18 %, que no figura en ninguna fuente: una daba 14 % con datos de enero y otra, 22 % con datos de junio. Además, quien lee no puede saber de dónde sale cada cifra. ¿Qué cambio resuelve las dos cosas?

- A. Pedir al sintetizador que, ante dos cifras distintas, dé la media de las dos y cite ambas fuentes junto a ese número.
- B. Que los subagentes devuelvan cada afirmación con su fuente y la fecha de sus datos, y el informe muestre las dos cifras.
- C. Que los subagentes resuman con más detalle y citen la fuente al final de cada párrafo, para que el sintetizador la deduzca de ahí.
- D. Pedir al sintetizador que marque como contradicción toda cifra que no coincida entre fuentes y que la deje fuera del informe final.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** El 18 % es una fusión de dos cifras que no se contradicen: miden meses distintos. Con la fecha de los datos en la salida estructurada, la diferencia se lee como temporal (TS 5.6-K4, S4), y las dos cifras se presentan con su fuente en vez de fundirse (TS 5.6-K3). El mapeo afirmación–fuente, con el contenido separado de los metadatos, es lo que permite rastrear cada cifra (TS 5.6-S1, K2, TS 1.3-S2).

- **A** es justo lo que produjo el 18 %: citar las dos fuentes no hace que ninguna respalde la media, y las dos cifras eran correctas para su periodo (TS 5.6-K3, K4).
- **C** sigue confiando la atribución a la prosa: es justo donde se pierde al resumir (TS 5.6-K1).
- **D** trata una diferencia temporal como una contradicción y quita del informe dos datos válidos (TS 5.6-K4).
</details>

**Pregunta 2 (multiple-response).** Un subagente de análisis de documentos recibe dos informes financieros de fuentes creíbles que dan cifras distintas para los ingresos de la misma división en el mismo trimestre: 4,2 M€ y 3,9 M€. Ambos cubren el mismo periodo y la misma población, y el informe final debe seguir siendo fiable para quien lo lee. **Selecciona dos** prácticas adecuadas. Evalúa cada opción por separado.

- A. Resumir cada informe en un párrafo breve que no conserva qué fuente respalda cada cifra, para que el sintetizador trabaje con menos texto y sin ruido.
- B. Quedarse con la cifra del informe publicado más recientemente y descartar la otra, porque es la más probable y así el informe final queda coherente y sin dudas.
- C. Incluir las dos cifras con su fuente, anotadas como conflicto, y que el coordinador decida cómo reconciliarlas antes de pasarlas a la síntesis.
- D. Dedicar una sección del informe a los hallazgos establecidos y otra a los disputados, conservando cómo cada fuente caracteriza su cifra y su método.

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**C y D.** Las dos conservan el conflicto con su fuente en vez de esconderlo.

- **A** Un resumen que no conserva qué fuente respalda cada cifra es donde se pierde la atribución (TS 5.6-K1): menos texto no ayuda a quien no puede saber de dónde sale cada cifra.
- **B** Elegir una cifra de forma arbitraria oculta el conflicto; lo correcto es anotarlo con su fuente (TS 5.6-K3). Y la fecha de publicación no decide aquí: sirve para no leer como contradicción una diferencia temporal (TS 5.6-K4), y estos informes cubren el mismo periodo.
- **C** El análisis incluye los valores en conflicto, anotados, y el coordinador decide cómo reconciliarlos antes de la síntesis (TS 5.6-S3, 5.6-K3).
- **D** El informe distingue lo establecido de lo disputado y conserva la caracterización y el método de cada fuente (TS 5.6-S2).
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 5.1-K2, S4.** Un informe largo lleva su hallazgo más importante en mitad del texto, y el resumen que hace el modelo lo omite. ¿Qué cambio es el adecuado?

- A. Abrir el informe con un resumen de lo importante y ordenar el detalle con encabezados claros.
- B. Repetir el informe completo dos veces seguidas en el prompt, para reforzar su contenido.
- C. Pedir al modelo que lea más despacio y que no se salte ninguna parte del documento.
- D. Mover el hallazgo a una nota al pie del final, donde no interrumpa al resto del texto.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**A.** En una entrada larga, el modelo atiende bien el principio y el final y puede saltarse lo que queda en medio (TS 5.1-K2). Ayuda abrir con un resumen de lo importante y ordenar el detalle con encabezados (TS 5.1-S4). B duplica el coste; C es una petición sin mecanismo; D lo esconde.
</details>

**C2 · TS 5.1-S6.** El sintetizador tiene poco margen de contexto, y el investigador le pasa páginas de texto con todo su razonamiento. ¿Qué se cambia?

- A. El sintetizador, para que resuma por su cuenta cada mensaje largo antes de leerlo.
- B. El investigador, para que devuelva lo esencial estructurado: hechos, citas y relevancia.
- C. El coordinador, para que reenvíe ese mismo texto repartido en varios mensajes cortos.
- D. El prompt del investigador, para que explique su razonamiento todavía con más detalle.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**B.** Cuando el agente siguiente tiene poco margen, se cambia el anterior para que le pase lo esencial estructurado (hechos, citas, una puntuación de relevancia) y no texto largo con su razonamiento (TS 5.1-S6). A y C mantienen el mismo volumen; D lo aumenta.
</details>

**C3 · TS 5.1-S5, 5.6-S5.** Un informe de síntesis reúne cifras comparables de varias fuentes y explicaciones narrativas. ¿Cómo se presenta, y qué viaja con cada cifra?

- A. Todo en prosa continua, con las fuentes reunidas en una lista al final del informe.
- B. Todo en una única tabla, incluidas las explicaciones, para que el formato sea uniforme.
- C. Las cifras en tabla y lo demás en prosa, y cada cifra con su fecha, su fuente y su método.
- D. Las cifras redondeadas dentro del texto, sin fuente ni fecha, para no recargar la lectura.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**C.** Cada clase de contenido se presenta a su manera, las cifras en una tabla, en vez de pasarlo todo a un formato único (TS 5.6-S5). Con cada cifra van la fecha, la ubicación en la fuente y el contexto metodológico, que la síntesis necesita para no equivocarse (TS 5.1-S5). A y B fuerzan un solo formato; D pierde la procedencia.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 06 · Contexto largo

> **Qué vas a hacer:** Ver cómo se sostiene una investigación en tres fases sacando el detalle del contexto (scratchpad, subagentes, resumen entre fases) y cómo se retoma tras una caída simulada con un manifest de estado.
>
> **Necesitas antes:** Los módulos [01](#01--coordinador-y-subagentes) y [04](#04--errores-entre-agentes) (coordinador, subagente y barrera sobre el mismo servidor de fuentes).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar; lo medido está en el Paso 3).

### Antes de empezar

Los términos comunes (coordinador, subagente, *scratchpad*, *manifest*) están en el [glosario](../docs/glosario.md).

- **El sistema:** una investigación en tres fases sobre las fuentes sintéticas: 1) los tiempos de resolución y la satisfacción de cuatro fuentes, 2) el informe largo `SRC-LARGO` (~9.400 caracteres), 3) un informe breve con lo descubierto. La petición de cada fase no dice las cifras que se esperan.
- **Scratchpad:** un archivo en tu directorio de estado con dos tools, `save_finding` (la usa el subagente) y `read_scratchpad` (la usa el coordinador).
- **Resumen entre fases:** al terminar una fase, el código guarda su cierre (recortado a 1.200 caracteres) y lo inyecta en el contexto inicial de la fase siguiente.
- **Manifest:** un archivo `manifest.json` en el mismo directorio con las fases hechas, el resumen de cada una, las fuentes cubiertas y el número de hallazgos.
- **`Explore` y `/compact`:** son de Claude Code y no se ejecutan aquí. `Explore` (sección D3) es el subagente de solo lectura que saca la exploración verbosa del hilo principal, como `researcher` en este módulo. `/compact` (TS 5.4-S5) resume una sesión interactiva que se ha llenado de salida de exploración y libera contexto; aquí ese papel lo hace el resumen de cada fase. Puedes probarlo en cualquier sesión larga de Claude Code.

### Las tools del ejercicio

| Tool | Quién la usa | Qué hace |
| :--- | :--- | :--- |
| `query_source` | el subagente `researcher` (en `todo_en_contexto`, el coordinador) | devuelve el informe de una fuente (igual que en el [módulo 04](#04--errores-entre-agentes)) |
| `save_finding` | el subagente | guarda un hallazgo clave (`source_id`, `claim`, `figure`) en el scratchpad |
| `read_scratchpad` | el coordinador | lee los hallazgos guardados, en orden |

### El ejercicio

Qué cambia en el código de cada variante:

- **Correcta:** una conversación por fase. El coordinador delega las consultas al subagente, lee el scratchpad antes de volver a consultar y cierra cada fase con un resumen. La fase siguiente empieza con ese resumen y el estado del manifest.
- **`--anti todo_en_contexto`:** las tres fases en una sola conversación, sin scratchpad, sin resumen y sin subagentes: el coordinador consulta las fuentes él mismo y los informes en bruto se acumulan en su contexto.
- **`--simular-caida`:** la correcta corta tras la fase 1. La siguiente ejecución, sin ese argumento, encuentra el manifest a medias y retoma desde la fase 2. `--desde-cero` ignora un manifest a medias.

Al retomar, el código valida el manifest (versión, claves, tipos) y comprueba que el scratchpad tiene los hallazgos que dice; si no cuadra, avisa y empieza de cero, pero antes aparta el estado anterior a `app3-06.<fecha-hora>.bak` (junto a `app3-06`, en `estado/<perfil>/`) en vez de borrarlo: un manifest de otra versión podría ser trabajo que se quiere conservar. Una ejecución terminada o `--desde-cero` sí sustituyen el estado sin copia. `save_finding` devuelve un error de validación, no una excepción, si `claim` o `source_id` no son texto o `figure` no es un número. Un scratchpad con la última línea cortada por una caída la ignora con un aviso.

El código mide sin modelo cuántos caracteres de resultados de tools llegan al contexto del coordinador, cuántas consultas repite sobre fuentes ya cubiertas, cuántas veces lee el scratchpad, cuántos de los cinco hechos descubiertos recoge el informe final y cuántas expresiones de «patrón típico» contiene.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, las consultas las hacen subagentes y los hallazgos se guardan en el scratchpad. ¿Qué llega al contexto del coordinador de lo que dice cada fuente y qué se queda fuera?
2. (guía) Con `todo_en_contexto` (las tres fases en una sola conversación, con los informes en bruto), ¿qué le puede pasar al informe final si la sesión se alarga mucho?
3. (módulo) Esta investigación es corta: cinco fuentes y unos 11.000 caracteres de resultados. Con `todo_en_contexto`, ¿esperas que el informe final llegue a perder alguno de los cinco hechos?
4. (guía) Tras `--simular-caida`, la ejecución siguiente retoma desde el manifest. ¿Por qué el estado tiene que estar ahí y no en la conversación anterior? ¿Qué hace el coordinador con él para que no se repitan consultas?
5. (guía) Sin `--anti`, cada fase es una conversación nueva que arranca con el resumen de la anterior. ¿Qué perdería la fase 2 si arrancara solo con su petición?
6. (módulo) ¿Cuál de las dos configuraciones, sin `--anti` o `todo_en_contexto`, esperas que cueste más? ¿Por qué?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/06_contexto_largo.py                          # correcta: tres fases
uv run python app3_sistema_multiagente/06_contexto_largo.py --anti todo_en_contexto  # un solo hilo
uv run python app3_sistema_multiagente/06_contexto_largo.py --simular-caida          # corta tras la fase 1
uv run python app3_sistema_multiagente/06_contexto_largo.py                          # y retoma desde el manifest
```

**Si ejecutas:** el manifest, el scratchpad, el resumen entre fases y las medidas se prueban sin modelo; ejecutar sirve para ver el contexto acumulado y la recuperación del estado. El estado queda en `estado/<perfil>/app3-06/` (el perfil sale de `CCARF_PERFIL`), fuera de git y propio de cada persona.

### Qué observar

Los caracteres de resultados de tools en el contexto del coordinador (por fase y en total), las consultas repetidas a fuentes ya cubiertas, las lecturas del scratchpad, los hechos del informe final y las expresiones de patrón típico.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Llega lo que cada subagente devuelve y lo que el coordinador relee del scratchpad; la exploración verbosa se queda en el subagente, fuera del hilo principal (TS 5.4-K3, 5.4-S1), y los hallazgos clave sobreviven fuera del contexto (TS 5.4-K2, 5.4-S2). Como mucho, unos 4.300 caracteres en una fase.
- **P2** Que se degrade: respuestas menos coherentes y «patrones típicos» en lugar de lo concreto que se había descubierto (TS 5.4-K1).
- **P3** No los perdió: 5 de 5 hechos y ningún patrón típico. La acumulación aparece (11.134 caracteres en un solo hilo); la degradación, con este tamaño, no.
- **P4** Porque para recuperarse de una caída cada agente exporta su estado a un sitio conocido, fuera de la conversación (TS 5.4-K4). Al retomar, el coordinador carga el manifest y pasa su contenido a los prompts de los agentes (TS 5.4-S4). Con el manifest y el scratchpad, la reanudación hizo 0 consultas repetidas.
- **P5** Lo descubierto en la fase 1: tendría que volver a consultarlo o trabajar sin ello. Por eso los hallazgos de una fase se resumen antes de lanzar la siguiente y el resumen va en su contexto inicial (TS 5.4-S3), además del estado del manifest.
- **P6** Sin `--anti`, unas 2,5 veces más: son tres conversaciones y subagentes. Lo que compra no es ahorro, sino contexto acotado por fase y poder retomar.

**Medición anterior a las correcciones B4**, con el informe largo de entonces (B4 cambió su relleno; después solo se volvió a medir la caída simulada, abajo). Coordinador Sonnet 5.5, subagente Haiku 5.5, 0,02–0,04 $ por fase (~0,20 $ en total):

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta, completa (1 ejecución) | contexto del coordinador de 4.106, 2.497 y 1.458 caracteres por fase (8.061 en total, nunca juntos); 0 consultas repetidas; el scratchpad se leyó en cada fase; informe final con 5 de 5 hechos; 0,068 $ | el detalle queda fuera del hilo del coordinador y el informe no pierde nada |
| `--simular-caida` y reanudación (1 + 1) | tras la fase 1: 5 hallazgos y manifest con la fase 1; la ejecución siguiente anunció «retomando: fases hechas [1]» con las 4 fuentes cubiertas; en las fases 2 y 3, **0 consultas repetidas**, 1 lectura del scratchpad por fase y contexto de 2.321 y 1.527 caracteres; informe final con 5 de 5 hechos; 0,039 $ + 0,038 $ | el estado se recupera del manifest y del scratchpad, no de la conversación anterior |
| `todo_en_contexto` (2 ejecuciones) | **11.134 caracteres** de resultados de tools en el contexto del coordinador, en un solo hilo, con 5 fuentes consultadas por él; informe final con 5 de 5 hechos y **0** expresiones de patrón típico; 0,025–0,029 $ | la acumulación aparece, **la degradación no** |

Notas:

- **Sin señal de degradación (TS 5.4-K1):** con ~11.000 caracteres (unos pocos miles de tokens) el informe del hilo único no perdió ningún hecho ni recurrió a «patrones típicos». Que aparezca en una sesión mucho más larga es una hipótesis sin comprobar; no se alargó la investigación para forzarla. Lo que sí se midió es la diferencia de contexto: 11.134 caracteres juntos frente a un máximo de 4.106 en una fase de la correcta.
- **Coste:** la correcta cuesta unas 2,5 veces más que el hilo único (0,068 $ frente a 0,025–0,029 $): tres conversaciones y subagentes. Lo que compra no es ahorro, sino contexto acotado por fase y la posibilidad de retomar.
- **Lo que hizo el subagente:** en la fase 1 el coordinador lanzó un subagente por fuente, en paralelo, y cada uno guardó sus hallazgos (5–7 en total, con algún duplicado del total de tickets). La barrera impidió que el coordinador consultara las fuentes por su cuenta (0 intentos denegados).
- **Medida de hechos:** la primera versión rechazaba una cifra seguida de `/5` y marcó 3 de 5 en la reanudación, aunque el informe traía «4,1/5» y «3,6/5». Se corrigió con un test: la reanudación recoge los 5 hechos, como la correcta.
- **Medidas:** «hechos del informe» comprueba que cada cifra aparece, no que vaya con su fuente, y «patrón típico» busca expresiones sueltas. Léelas junto al texto.
- `Explore` y `/compact` no se pueden observar aquí: son de Claude Code.
- Las medidas, el scratchpad, el manifest y las opciones se prueban sin modelo en `tests/test_app3_06_contexto_largo.py`.

**Después de las correcciones B4** (una pasada de `--simular-caida` y su reanudación, 0,07 $; el prompt no cambió, así que no se repitió el resto): el estado se escribió en `estado/default/app3-06/`; tras la fase 1, 6 hallazgos y el manifest con la fase 1; la reanudación anunció «retomando: fases hechas [1]» (el scratchpad cuadraba con el manifest, sin avisos), sin consultas repetidas, con 7 hallazgos al final y **5 de 5 hechos** en el informe. Contexto del coordinador por fase: 4.315, 2.256 y 1.472 caracteres (8.043 en total). Los casos del manifest y del scratchpad (bytes no UTF-8, tipos, claves, versión, manifest ajeno, línea truncada) se prueban solo sin modelo: 14 tests con tipos o valores erróneos, 6 con claves que faltan y el resto para versión, coherencia con el scratchpad y línea cortada.
</details>

### Pregunta tipo examen

Una investigación en tres fases se corta durante la tercera, con las dos primeras ya terminadas. El sistema se diseñó para poder retomar el trabajo tras una caída. ¿Cómo debe retomarse?

- A. Cargar el estado guardado y pasar a la fase pendiente lo que ya está hecho y el resumen de las anteriores.
- B. Reanudar la conversación anterior completa, que conserva el detalle de cada consulta aunque ya sea muy larga.
- C. Empezar de nuevo desde la primera fase con un contexto limpio, por si el estado guardado quedó a medias.
- D. Relanzar solo la tercera fase con la petición original y dejar que vuelva a consultar las fuentes que necesite.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** Para recuperarse de una caída, cada agente exporta su estado a un sitio conocido, y al retomar el coordinador carga el manifest y lo pasa a los prompts (TS 5.4-K4, S4). El resumen de las fases hechas va en el contexto inicial de la siguiente (TS 5.4-S3).

- **B** arrastra un contexto largo, que es lo que favorece la degradación (TS 5.4-K1), en vez de usar el estado que se guardó para esto (TS 5.4-K4).
- **C** tira el trabajo que el estado guardado permite no repetir (TS 5.4-K4, S4).
- **D** no repite las fases hechas, pero la tercera arranca sin lo descubierto: no recibe ni el manifest ni el resumen (TS 5.4-S3, S4).

**Inferencia de este módulo:** comprobar el estado antes de usarlo (versión, claves y coherencia con el scratchpad) evita retomar desde uno roto o ajeno, y tras una caída puede no quedar conversación que reanudar. La guía no dice ninguna de las dos cosas, y la respuesta no depende de ellas.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 5.4-K2, S2.** En una investigación larga, el agente necesita no perder los hallazgos clave cuando el contexto se llene. ¿Qué hace?

- A. Repetir cada hallazgo al principio de cada respuesta, para tenerlo siempre reciente.
- B. Confiar en el historial: lo que se dijo antes sigue disponible durante toda la sesión.
- C. Pedir al usuario que le recuerde los hallazgos cada vez que haga una pregunta nueva.
- D. Anotarlos en un *scratchpad* fuera del contexto y releerlo ante cada pregunta nueva.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**D.** Un *scratchpad* guarda los hallazgos clave fuera del contexto, así que sobreviven a sus límites (TS 5.4-K2); el agente anota en él y lo vuelve a leer cuando llega la pregunta siguiente (TS 5.4-S2). A llena el contexto aún más; B es lo que falla en una sesión larga; C traslada el trabajo al usuario.
</details>

**C2 · TS 5.4-K3, S1.** Explorar un repositorio genera mucha salida, que llena el hilo del agente principal. ¿Cómo se evita?

- A. Delegando la exploración en subagentes, cada uno con una pregunta concreta que responder.
- B. Pidiendo al agente principal que lea los archivos más deprisa y sin comentar ninguno.
- C. Subiendo el tope de turnos, para que la exploración acabe antes de llenar el contexto.
- D. Quitando las tools de lectura al agente principal mientras dure la primera fase.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**A.** La exploración verbosa se delega en subagentes, que la mantienen fuera del hilo principal mientras este conserva la visión de conjunto (TS 5.4-K3), y a cada subagente se le da una pregunta concreta (TS 5.4-S1). B y C no reducen lo que entra en el contexto; D impide explorar.
</details>

**C3 · TS 5.4-S5.** En una sesión de Claude Code, el contexto se ha llenado con la salida de una exploración larga y aún queda trabajo. ¿Qué encaja?

- A. Cerrar la sesión y empezar otra sin llevarse nada de lo que se ha descubierto.
- B. Usar `/compact`, que condensa la conversación y libera contexto para poder seguir.
- C. Usar `/memory`, que borra del contexto los archivos que ya no hacen falta.
- D. Seguir sin hacer nada: el contexto se vacía por sí solo al llegar a su límite.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**B.** En una exploración larga, `/compact` libera contexto cuando se ha llenado de salida de descubrimiento (TS 5.4-S5). A pierde lo descubierto; C no es para eso; D deja que la sesión se degrade.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 07 · Extracción estructurada con schema

> **Qué vas a hacer:** Extraer los metadatos de 12 documentos de compra con una tool de JSON Schema, puntuar lo que sale contra unas etiquetas que el modelo no ve y, en la última parte, enriquecer la extracción consultando el pedido que cita.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Los términos comunes (Messages API, `tool_choice`, *few-shot*, presupuesto) están en el [glosario](../docs/glosario.md). Este módulo no usa el Agent SDK ni subagentes: llama a la Messages API con `harness/budget.py`, como `app1/05`, y por eso necesita una API key.

- **El sistema:** una sola llamada por documento. El modelo recibe el texto del documento y una tool, `extract_metadata`, cuyo `input_schema` es un JSON Schema. Los 12 documentos son facturas, albaranes y otros tipos de una compra de equipos (`documentos_compra.json`), con formatos distintos (tabla, prosa, líneas sueltas), datos que faltan y un fragmento ilegible. Las etiquetas con los valores correctos están en otro archivo, `documentos_compra_etiquetas.json`, que solo lee el código que puntúa.
- **Términos propios:**
  - **Campo *nullable*:** un campo cuyo tipo admite `null` (`["string", "null"]`) y que no está en `required`: es la forma de decir «el documento puede no traerlo».
  - **`enum` abierto:** una lista de valores permitidos con una salida (`other`, más un campo de detalle, y `unclear`) para lo que no encaja.
  - **Tres niveles:** *JSON válido* (se puede parsear), *forma válida* (cumple el esquema: tipos, `required`, `enum`) y *dato correcto* (coincide con la etiqueta). Un nivel no implica el siguiente. El módulo mide los dos últimos por separado (forma, «sintaxis»; fondo, «semántica»).
  - **Modo estricto (`strict: true`):** un campo de la definición de la tool que hace que la API garantice que su entrada cumple el esquema, con los objetos cerrados (`additionalProperties: false`).
  - **Campo inventado:** uno que la etiqueta dice que no está en el documento y para el que el modelo devuelve algo distinto de `null` (incluidos `'null'` como texto, `''` o un valor deducido).

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `extract_metadata` | el documento (en el mensaje) | la extracción: `doc_type`, `doc_type_detail`, proveedor, número, fecha, pedido, moneda, total declarado y líneas |
| `extract_invoice`, `extract_delivery_note`, `extract_other` | el documento | una tool por tipo, con los campos de ese tipo (solo en `--parte tipo_desconocido`) |
| `lookup_purchase_order` | `po_number` (`PO-nnnn`) | proveedor, estado e importe esperado del pedido, leídos de `pedidos_compra.json`, o un error si no existe (solo en `--parte enriquecimiento`) |

Las tools de extracción no hacen nada: lo que importa es lo que el modelo escribe en su entrada, que el módulo compara con la etiqueta. `lookup_purchase_order` sí devuelve datos, y su resultado vuelve al modelo como `tool_result`.

### El ejercicio

Cinco partes (`--parte`) y variantes `--anti` en la primera y en la última:

- **`forzada`:** `tool_choice` forzado a `extract_metadata`. La versión correcta tiene los campos opcionales *nullable*, el `enum` con `other` y `unclear`, y las reglas de formato (fecha ISO, número con punto decimal) en la descripción. `--anti sin_nullable` hace obligatorios todos los campos y quita `null` de los tipos. `--anti enum_cerrado` deja el `enum` solo con `invoice` y `delivery_note`.
- **`estricto`:** el esquema de `enum` cerrado de la parte anterior, sin y con `strict: true`, sobre los mismos 12 documentos. Imprime los tres niveles: forma válida, fuera del `enum` y tipo correcto. El esquema es el mismo en las dos; solo cambia el campo `strict` y que los objetos van cerrados.
- **`tipo_desconocido`:** tres tools, una por tipo de documento, y `tool_choice` `any`. Se compara con `auto` y con forzar siempre la tool de factura.
- **`few_shot`:** el mismo esquema sin las reglas de formato en las descripciones, con y sin tres ejemplos en el *system prompt* (una factura en tabla, otra en prosa y un albarán en líneas sueltas). Admite `--rol-modelo enforcement` (Haiku 4.5). Además de las fechas, imprime los campos con valor en la etiqueta que salen `null` o vacíos (**faltantes**) y los que el modelo inventa donde la etiqueta dice que no están (**inventados**), con y sin ejemplos.
- **`enriquecimiento`:** dos tools, `extract_metadata` y `lookup_purchase_order(po_number)`, cuyo resultado sale de `pedidos_compra.json` (determinista). El primer turno va con `tool_choice` forzado a `extract_metadata`; los siguientes, en `auto`, con la extracción devuelta como `tool_result`. `--anti auto_desde_inicio` usa `auto` desde el primer turno. Se mide el orden de las llamadas, si el modelo consulta un pedido antes de extraer o con un número que no sale del documento, y si el resultado final usa el pedido extraído.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Un documento no menciona ningún número de pedido. Si `po_number` es obligatorio y de tipo `string` (`sin_nullable`), ¿qué opciones le quedan al modelo para ese campo?
2. (guía) Con `po_number` opcional y *nullable*, ¿qué devolverá el modelo para ese mismo documento? ¿Esperas que desaparezcan del todo los valores rellenados?
3. (guía) En `enum_cerrado`, `doc_type` solo admite `invoice` y `delivery_note`, y la llamada va con `tool_choice` forzado: el modelo tiene que escribir algo en ese campo. Llega un certificado de garantía. ¿Qué salida rechazaría un validador del esquema y cuál pasaría sin que nadie lo notara?
4. (guía) En `tipo_desconocido` hay tres tools, una por tipo de documento. ¿Qué garantiza `any` y qué deja sin garantizar `auto`? ¿Qué le pasa a un albarán si se fuerza siempre la tool de factura?
5. (guía) En `few_shot`, las descripciones ya no dicen cómo escribir una fecha: sin regla ni ejemplos, el modelo tiene que adivinar el formato. ¿Qué aportan tres ejemplos de documentos con estructuras distintas?
6. (módulo) ¿Esperas que los ejemplos de `few_shot` se noten con cualquier modelo? ¿De qué depende?
7. (módulo) Algunos campos sí están en el documento, pero el modelo podría dejarlos vacíos. ¿Esperas que los ejemplos cambien cuántos deja vacíos en estos doce documentos?
8. (guía) En `enriquecimiento`, el módulo fuerza `extract_metadata` en el primer turno y deja `auto` en los siguientes. ¿Para qué sirve ese primer turno forzado?
9. (módulo) Con `auto_desde_inicio`, si en tus ejecuciones el modelo extrae siempre primero por su cuenta, ¿basta eso para prescindir del primer turno forzado? ¿Por qué?
10. (guía) En `estricto`, con `strict: true` y el `enum` cerrado (sin `other`), llega el certificado de garantía. ¿Qué tipo le queda al modelo? ¿Lo detectaría un validador del esquema?
11. (guía) Con `strict: true` en producción, ¿dejaría de hacer falta comprobar los datos extraídos contra el documento? ¿Por qué?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada                          # correcta
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada --anti sin_nullable      # todo obligatorio
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada --anti enum_cerrado      # enum sin other ni unclear
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte estricto --repeat 3             # el mismo enum cerrado, sin y con strict
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte tipo_desconocido
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte few_shot --rol-modelo enforcement --repeat 3
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte enriquecimiento --repeat 3                          # extracción forzada y después auto
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte enriquecimiento --anti auto_desde_inicio --repeat 3  # auto desde el primer turno
```

**Si ejecutas:** la construcción del esquema por variante, el validador de forma y la puntuación contra etiquetas se prueban sin modelo; ejecutar sirve para ver qué hace de verdad el modelo con un campo que no puede rellenar. Cada ejecución cuesta menos de 0,05 $ con Haiku 5.5 (`estricto` con `--repeat 3`: unos 0,02 $; `few_shot` y `enriquecimiento` con `--repeat 3`: unos 0,03–0,04 $); con Haiku 4.5 y `--repeat 3`, `few_shot` cuesta unos 0,23 $ y `enriquecimiento`, unos 0,24 $.

### Qué observar

En cada ejecución, `forma válida`, `campos ausentes rellenados`, `tipo correcto`, `fuera del enum` y `valores incorrectos`; en `estricto`, cómo se mueven `forma válida` y `tipo correcto` entre sin y con `strict`; en `tipo_desconocido`, qué tool eligió el modelo para cada documento; en `few_shot`, fechas incorrectas, faltantes e inventados con y sin ejemplos; en `enriquecimiento`, el orden de las tools por documento, las consultas antes de extraer, los números que no salen del documento y si el resultado final usa el pedido extraído.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Inventar algo para cumplir el `required`: el texto `'null'`, una cadena vacía o un valor deducido. Rellenó 21 de 21 campos ausentes (TS 4.3-S4).
- **P2** `null`, casi siempre, pero no siempre: 1 o 2 rellenados de 21. Un campo *nullable* deja de obligar a inventar (TS 4.3-S4), pero el esquema solo elimina los errores de sintaxis, no los de significado (TS 4.3-K3).
- **P3** Rechazaría un valor fuera de la lista, como `other` (pasó en 2 de 12). Pasaría sin aviso un tipo permitido que no es el suyo: el documento ilegible salió como `invoice`. Por eso el `enum` lleva `other` con un campo de detalle, y `unclear` para lo ambiguo (TS 4.3-K4, 4.3-S5).
- **P4** `any` obliga a llamar a alguna tool y deja elegir cuál; `auto` permite contestar con texto (TS 4.3-K2). Con la tool de factura forzada, el albarán se trata como factura (5 de 12 correctos). `any` encaja cuando no se sabe de qué tipo es el documento (TS 4.3-S2).
- **P5** Enseñan dónde está cada dato en cada estructura, y reducen las alucinaciones en la extracción (TS 4.2-K4, 4.2-S4). Las reglas de normalización van en el prompt junto al esquema, porque los documentos no las siguen (TS 4.3-S6).
- **P6** No: solo se notan si el modelo falla sin ellos. Con el modelo por defecto no hubo fechas mal con ni sin ejemplos; con `--rol-modelo enforcement`, 5 o 6 de 12 sin ejemplos y ninguna con ellos.
- **P7** No cambió: 0 campos vacíos con y sin ejemplos. La guía da los ejemplos como remedio para los campos que salen vacíos (TS 4.2-S5); aquí no había vacíos que corregir.
- **P8** Para asegurar que la extracción se hace antes de los pasos que la enriquecen (TS 4.3-S3).
- **P9** No basta: que hoy lo haga no garantiza el orden; el turno forzado lo garantiza por construcción. El fallo que evita no se pudo provocar (sin señal).
- **P10** Uno de los permitidos, aunque no sea el suyo: 0 valores fuera del `enum` y forma válida en 12 de 12, pero el tipo correcto baja de 11 a 9 de 12. Un validador del esquema no lo detecta, porque la forma es válida: el esquema elimina los errores de sintaxis, no los de significado (TS 4.3-K3), y por eso el `enum` lleva `other` (TS 4.3-K4).
- **P11** No: el modo estricto garantiza la forma, es decir, que la salida cumple el esquema, pero no que el dato sea correcto (TS 4.3-K3). Los errores de significado, como el tipo mal elegido de P10, siguen necesitando otra comprobación.

Haiku 5.5 (rol `agent`), 12 documentos, tres repeticiones salvo donde se dice:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `forzada`, correcta | forma válida 12/12, tipo correcto 12/12, campos ausentes rellenados 1/21 en 3 repeticiones y 2/21 en otra ejecución (siempre el total de un presupuesto, deducido de su única línea), líneas correctas 11/12 | con el campo *nullable* el modelo devuelve `null` casi siempre |
| `forzada`, `sin_nullable` | campos ausentes rellenados **21/21**, forma válida **6/12** | con campos obligatorios inventa: `'null'` como texto, `''`, un valor deducido; los que usan `'null'` en un campo numérico ni siquiera cumplen el esquema |
| `forzada`, `enum_cerrado` | tipo correcto 11/12, **2 de 12 con un tipo fuera del `enum`** (`other` en la garantía y el presupuesto), el ilegible forzado a `invoice` | el modelo escribe `other` aunque no esté en el `enum`: un esquema no se impone solo, el validador de forma lo detecta |
| `estricto` (Haiku 5.5, `enum` cerrado, 3 repeticiones, ~0,02 $) | sin `strict`: forma válida **10/12**, 2 fuera del `enum`, tipo correcto **11/12**. Con `strict`: forma válida **12/12**, 0 fuera del `enum`, tipo correcto **9/12**. Idéntico en las tres repeticiones | `strict` garantiza la forma y no el significado: la garantía **empeora** el tipo, porque lo que antes el modelo escribía bien como `other` (garantía y presupuesto) ahora cae en una categoría que no es. Es el motivo del `enum` abierto con `other` y `unclear` (TS 4.3-K4) |
| `tipo_desconocido` | `any`: la tool de su tipo en 12/12 (3 repeticiones); `auto`: igual; **forzada a factura: 5/12**, los otros 7 se tratan como factura | forzar una tool trata como factura todo lo que no lo es; `any` deja elegir |
| `few_shot` con Haiku 5.5 | 0 fechas incorrectas con y sin ejemplos; faltantes 0 en las seis ejecuciones; inventados 0–1 de 21 (un `stated_total` en `DC-11`, o un número en `DC-07` sin ejemplos) | **sin señal**: este modelo ya escribe la fecha en ISO sin que nadie se lo pida y no deja vacío ningún campo con valor |
| `few_shot` con Haiku 4.5 (`--rol-modelo enforcement`, 3 repeticiones, ~0,23 $) | sin ejemplos: **5, 6 y 6 fechas incorrectas** de 12, líneas correctas 10/12; con ejemplos: **0, 0 y 0**, líneas correctas 11/12. Faltantes 0 y inventados 2/21 (`DC-11`: fecha y total) en las seis ejecuciones | los ejemplos de las tres formas arreglan el formato que la descripción no dice; **no** cambian los campos faltantes (ya eran 0) ni los inventados |
| `enriquecimiento`, correcta (Haiku 5.5, 3 repeticiones, ~0,04 $) | extracción primero en 36/36; consulta antes de extraer 0/12 en cada repetición; número ajeno al documento 0; el resultado final usa el pedido extraído en 8, 6 y 7 de 12 (en los demás o no hay pedido que consultar o el modelo no lo consulta) | el primer turno forzado asegura el orden, pero la consulta posterior no siempre se hace |
| `enriquecimiento`, `auto_desde_inicio` (Haiku 5.5, 3 repeticiones) | consulta antes de extraer **0/12** y número ajeno al documento **0**; el resultado final usa el pedido extraído en 7/12, igual que con el primer turno forzado | **sin señal**: con `auto`, el modelo extrae primero por su cuenta. Que lo haga hoy no garantiza el orden |
| `enriquecimiento`, `auto_desde_inicio` (Haiku 4.5, 3 repeticiones) | consulta antes de extraer **0/12** y número ajeno al documento **0**; el resultado final usa el pedido extraído en 9/12, igual que con el primer turno forzado | **sin señal**, igual que en la fila anterior: el control positivo con un modelo más débil tampoco muestra el fallo |

Notas:

- **Forma y fondo:** `DC-06` (el certificado de garantía) sale en las tres repeticiones con una línea inventada (el modelo cuenta la garantía como un artículo), con la forma válida. El esquema lo deja pasar; la etiqueta, no.
- **El `enum` no se impone sin `strict`:** que el modelo devuelva un valor que no está en el `enum` no es un error de la API. El modo estricto (`strict: true`, que la guía nombra) lo evita, y `--parte estricto` lo muestra; el resto de partes usan la tool sin `strict` a propósito, para que el validador de forma tenga algo que detectar.
- **`strict` con campos *nullable*:** la API aceptó el esquema tal cual, con `["string", "null"]` y los opcionales fuera de `required`; solo exige `additionalProperties: false` en cada objeto (comprobado con Haiku 5.5, 3 variantes de esquema, 0,0008 $).
- **El anti de `enriquecimiento` no se nota:** se probó con Haiku 5.5 y con Haiku 4.5 y no hay diferencia entre forzar el primer turno y no hacerlo. Lo que hace el forzado es garantizar el orden por construcción; no se ha podido mostrar el fallo que evita.
- **El identificador de la petición:** en una primera versión de la sonda el prompt llevaba «Documento DC-07:» y el modelo lo copió como `document_number`. El prompt ya no lleva el identificador.
- Detalle y coste de las sondas: `docs/hallazgos.md`. Lo que no depende del modelo (esquemas, validador, puntuación, petición por modo y ejemplos) se prueba en `tests/test_app3_07_extraccion_schema.py`.
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un proceso extrae con una tool de JSON Schema el número de pedido, la fecha y el total de miles de facturas. Todas las respuestas son JSON válido. Sin embargo, una auditoría encuentra números de pedido plausibles que no existen, siempre en facturas que no citan ninguno. En el esquema, el campo es `string` y figura en `required`. ¿Qué cambio ataca la causa?

- A. Añadir al *system prompt* «no inventes datos» y conservar el campo como `string` obligatorio.
- B. Validar el número con una expresión regular `PO-nnnn` y reenviar al modelo las facturas que fallen.
- C. Pasar a `tool_choice` `auto`, para que el modelo pueda contestar en texto cuando le falte el dato.
- D. Hacer el campo opcional y *nullable*, y que su descripción pida `null` si no figura.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** Un campo obligatorio que el documento puede no traer obliga al modelo a fabricar un valor para cumplir el esquema. La forma de decir «puede no estar» es declararlo opcional y *nullable* (TS 4.3-K4, S4). Que todo el JSON sea válido no prueba nada: el esquema elimina los errores de sintaxis, no los de significado (TS 4.3-K3).

- **A** deja el campo obligatorio: el modelo sigue teniendo que escribir algo en él para cumplir el esquema (TS 4.3-S4).
- **B** no detecta el problema: el número inventado tiene el formato correcto y pasa la expresión regular. Además, reintentar no sirve cuando el dato no está en el documento (módulo 08).
- **C** sacrifica la garantía de salida estructurada (TS 4.3-K2) para resolver algo que el esquema resuelve por sí solo.
</details>

**Pregunta 2 (multiple-response).** Un equipo extrae importes y categorías de facturas con una tool de JSON Schema y activa el modo estricto. Tras una semana el equipo ya no tiene fallos al procesar las respuestas, pero en una factura las líneas no suman el total declarado y en otra el IVA aparece en el campo del subtotal. **Selecciona dos** afirmaciones correctas. Evalúa cada opción por separado.

- A. El modo estricto garantiza también que los valores coincidan con el documento, así que los totales erróneos apuntan a un fallo del modelo y no del esquema.
- B. Con el modo estricto desaparecen los errores de sintaxis del esquema: la salida es JSON bien formado que cumple el esquema.
- C. Un total que no suma o un valor en el campo que no le toca son errores de significado: el esquema, estricto o no, no los evita.
- D. Marcar como obligatorios más campos del esquema obliga al modelo a ser más preciso y elimina esos errores de significado.

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**B y C.** La primera dice qué garantiza el modo estricto; la segunda, qué queda fuera de esa garantía.

- **A** Es justo lo que el modo estricto no promete: garantiza la forma, no que el valor sea el del documento (TS 4.3-K3).
- **B** Una tool con esquema estricto elimina los errores de sintaxis: la salida cumple el esquema (TS 4.3-K1, 4.3-K3).
- **C** Líneas que no suman el total y valores en el campo equivocado son los errores semánticos que la guía cita como no evitables con el esquema, estricto o no (TS 4.3-K3).
- **D** Declarar más campos obligatorios no mejora el significado: un campo que el documento puede no traer obliga al modelo a fabricarlo, y la forma de decir «puede no estar» es opcional y *nullable* (TS 4.3-K4, 4.3-S4).
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 4.3-S1.** Se usa una tool cuyo `input_schema` es el esquema de la extracción. ¿De dónde lee el código los datos extraídos?

- A. Del texto que el modelo escribe antes de la llamada, que el código convierte a JSON.
- B. Del `tool_result` que el código devuelve al modelo después de ejecutar la tool.
- C. De la entrada (`input`) del bloque `tool_use` que el modelo devuelve en su respuesta.
- D. Del *system prompt*, donde el modelo deja anotados los valores que ha encontrado.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**C.** Con una tool cuyo `input_schema` es el esquema, la extracción se lee de la entrada del bloque `tool_use` (TS 4.3-K1, 4.3-S1). A vuelve al texto libre, con sus errores de sintaxis; B es lo que el código envía, no lo que recibe; D no existe como mecanismo.
</details>

**C2 · TS 4.3-S2.** Llegan documentos de tipo desconocido y hay un esquema de extracción para cada tipo, cada uno en su tool. ¿Qué `tool_choice` encaja?

- A. `auto`, para que el modelo decida si extrae o si contesta con una explicación.
- B. Forzar siempre la tool de factura, que es el tipo de documento más frecuente.
- C. Ninguno: sin conocer el tipo no se puede usar una tool de extracción.
- D. `any`, que obliga a llamar a alguna tool y deja al modelo elegir cuál.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**D.** `any` encaja cuando hay varios esquemas de extracción y no se sabe de qué tipo es el documento (TS 4.3-S2): garantiza una llamada y deja elegir la tool (TS 4.3-K2). A permite contestar con texto; B trata como factura lo que no lo es.
</details>

**C3 · TS 4.3-S3.** Un flujo debe extraer los metadatos de un documento antes de enriquecerlos con otras tools. ¿Cómo se asegura ese orden?

- A. Forzando la tool de extracción en el primer turno y dejando los demás pasos para después.
- B. Pidiendo en el prompt que extraiga primero, y confiando en que el modelo lo cumpla.
- C. Usando `any` en todos los turnos, para que siempre haya alguna llamada a una tool.
- D. Poniendo la tool de extracción en primer lugar en la lista de tools de la petición.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**A.** Forzar una tool asegura que esa extracción se haga antes de los pasos que la enriquecen (TS 4.3-S3). B es una petición, no una garantía; C no fija cuál se llama; D no impone ningún orden.
</details>

**C4 · TS 4.3-S5, S6.** Los documentos escriben las fechas de muchas formas, y algunos son ambiguos sobre su tipo. ¿Qué diseño es el adecuado?

- A. Dejar que el modelo elija el formato de la fecha y descartar los documentos ambiguos.
- B. Normalizar las fechas a mano después y obligar a elegir siempre un tipo conocido.
- C. Poner las reglas de formato en el prompt, junto al esquema, y añadir el valor `unclear`.
- D. Añadir un campo de texto libre para la fecha y otro campo para describir el tipo.

<details>
<summary>Comprobación C4 · Respuesta</summary>

**C.** Las reglas de normalización van en el prompt, junto al esquema, porque los documentos fuente no las siguen (TS 4.3-S6), y `unclear` recoge los casos ambiguos (TS 4.3-S5). A y D dejan el formato sin fijar; B obliga a inventar un tipo.
</details>

**C5 · TS 4.2-K4, S4, S5.** Una extracción deja vacíos campos que sí están en los documentos cuando estos cambian de formato: tabla, prosa o líneas sueltas. ¿Qué ayuda más?

- A. Marcar todos los campos como obligatorios, para que el modelo no pueda dejarlos vacíos.
- B. Añadir ejemplos *few-shot* de extracciones correctas sobre documentos de formatos distintos.
- C. Repetir la instrucción «no dejes campos vacíos» al principio y al final del prompt.
- D. Reducir el esquema a los campos que aparecen igual en todos los formatos de documento.

<details>
<summary>Comprobación C5 · Respuesta</summary>

**B.** Los ejemplos *few-shot* reducen las alucinaciones en la extracción (TS 4.2-K4): ejemplos de documentos con estructuras distintas enseñan dónde está cada dato (TS 4.2-S4), y ejemplos de extracciones correctas sobre formatos variados corrigen los campos que salen vacíos (TS 4.2-S5). A hace que el modelo invente; C insiste sin enseñar; D renuncia a los datos.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 08 · Validación y reintento con error concreto

> **Qué vas a hacer:** Validar sin modelo las extracciones de 12 documentos y reintentar las que fallan, con el error concreto, con uno genérico o insistiendo cuando el dato no existe.
>
> **Necesitas antes:** El [módulo 07](#07--extracción-estructurada-con-schema), cuya extracción se valida aquí.
>
> **Modo:** Ejecución obligatoria (hay que ejecutarlo: su lección es lo que hace el modelo tras un reintento, y leer el código no lo muestra).

### Antes de empezar

Los términos comunes (Messages API, presupuesto, `tool_choice`) están en el [glosario](../docs/glosario.md). Este módulo reutiliza del [módulo 07](#07--extracción-estructurada-con-schema) la tool `extract_metadata`, los 12 documentos y la puntuación contra etiquetas, y usa la Messages API (necesita una API key).

- **El sistema:** por cada documento, una extracción, una validación con reglas de código (sin modelo) y, si falla, un reintento. Las reglas: el tipo está en el `enum`, la fecha es ISO, todo documento lleva su número, una factura cita su número de pedido (`PO-nnnn`) y el total que declara el documento coincide con la suma de sus líneas. El esquema de la tool no dice cómo se escribe una fecha: esa regla solo la aplica el validador.
- **Qué modelo:** el rol `enforcement` (Haiku 4.5), un modelo anterior al de los demás módulos. El porqué está en el Paso 3. `--rol-modelo agent` ejecuta el módulo con Haiku 5.5.
- **Términos propios:**
  - **Reintento:** enviar de nuevo al modelo su propia llamada fallida, con el error devuelto como resultado de la tool (`is_error`), y pedirle otra extracción.
  - **Error concreto:** el mensaje del reintento nombra el campo, el valor que devolvió y la regla que incumple. Un error **genérico** solo dice «Inténtalo de nuevo».
  - **Patrón de fallo:** la causa de un fallo (`date_format`, `missing_required`, `total_mismatch`…). Se anota en cada fallo, y la salida los agrupa por causa. El `detected_pattern` de la guía, sobre los hallazgos de revisión que se descartan, llega en el módulo 11.
  - **`conflict_detected`:** el total que suma el código a partir de las líneas extraídas no coincide con el declarado. Si las líneas y el total están bien extraídos, lo que no cuadra es el documento.
  - **Dato ausente en la fuente:** que el documento no contiene lo que la regla exige. Tiene dos causas: el dato no aparece (*no lo trae*) o el documento dice dónde está, en otro que no se ha proporcionado (*remite a otro documento*, «Ver adjunto»). El código distingue las dos con una búsqueda en el texto, sin modelo.
  - **Efecto de un reintento** (solo para medir; el bucle no ve las etiquetas): *corregido* si el fallo desaparece y el valor coincide con la etiqueta, *persiste* si el fallo sigue, *falta* si el campo queda vacío aunque la etiqueta tiene un valor, *inventado* si desaparece pero el valor no es el de la etiqueta (o la etiqueta dice que no existe).

### El ejercicio

Lo que cambia en el código de cada variante (el esquema, los documentos y el validador son los mismos):

- **Correcta:** el reintento lleva el error concreto. Si la regla exige un dato que no aparece en el documento, no se reintenta y el campo queda marcado, con su causa: el documento **no lo trae** (`DC-02`, factura sin pedido) o **remite a otro documento** (`DC-07`, «Ver adjunto»). Un total que no cuadra tampoco se reintenta: el documento es incoherente, y se marca `conflict_detected` directamente. Hay un tope de 2 reintentos como red de seguridad. En la salida, `parada` es el motivo que cerró el bucle (el último que se registró).
- **`--anti reintento_generico`:** el mensaje del reintento es «Inténtalo de nuevo.», sin más. Todo lo demás es igual.
- **`--anti insistir`:** se reintenta con el error concreto también cuando el dato no está en el documento o remite a otro, y también el total que no cuadra (pidiendo que se revise); no se marca nada y el tope sube a 4.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) La variante correcta no reintenta cuando el documento no trae el dato que la regla exige, como una factura sin número de pedido. ¿Por qué? ¿En qué clase de fallo sí merece la pena reintentar?
2. (guía) Con `insistir` se le pide al modelo una y otra vez que corrija ese campo. ¿Qué acabará devolviendo? ¿Podría un validador de formato distinguirlo de un número de pedido real?
3. (guía) Una fecha sale como `12/03/2026` y la regla exige ISO. Con `reintento_generico` («Inténtalo de nuevo.»), ¿qué esperas que devuelva el modelo en el reintento? ¿Por qué lo cambia el error concreto?
4. (módulo) ¿Qué variante esperas que gaste más reintentos para arreglar las fechas: la del error concreto o `reintento_generico`?
5. (guía) Dos documentos declaran un total que no es la suma de sus líneas, y el error está en el propio documento. Si se le pide al modelo que lo revise hasta que cuadre, ¿qué puede acabar cambiando? ¿Qué información se pierde entonces?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/08_validacion_reintento.py                            # correcta
uv run python app3_sistema_multiagente/08_validacion_reintento.py --anti reintento_generico  # «inténtalo de nuevo»
uv run python app3_sistema_multiagente/08_validacion_reintento.py --anti insistir            # reintenta aunque no exista el dato ni cuadre el total
uv run python app3_sistema_multiagente/08_validacion_reintento.py --repeat 3                 # cifras más estables
uv run python app3_sistema_multiagente/08_validacion_reintento.py --rol-modelo agent         # con Haiku 5.5 no hay qué reintentar
```

**Si ejecutas:** el validador, los mensajes, la decisión de reintento y el bucle (con un modelo simulado) se prueban sin modelo. Ejecutar es obligatorio porque la lección es lo que el modelo hace con el reintento: corregir, repetir el error o inventar. Cada ejecución cuesta unos 0,05–0,07 $ (tope 0,50 $ de `--budget`; con `--repeat 3`, unos 0,14–0,19 $).

### Qué observar

Por documento, los fallos del primer intento agrupados por patrón, los reintentos, el efecto de cada uno y el motivo que cerró el bucle (`parada`); al final, reintentos útiles, inútiles, inventados y que dejaron vacío, los datos marcados con su causa (no lo trae o remite a otro documento), los conflictos y el coste de los reintentos.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Porque un reintento no crea un dato que la fuente no contiene; sirve para fallos de formato o de estructura (TS 4.4-K2). El bucle distingue el caso antes de reintentar y deja el campo marcado con su causa (TS 4.4-S2).
- **P2** Algo que no sale del documento: reintentar es ineficaz cuando el dato no está en la fuente (TS 4.4-K2), así que lo que devuelva lo habrá fabricado. Aquí fue un pedido inventado en las 3 repeticiones, que el validador no distingue porque tiene el formato correcto: solo lo delata la etiqueta.
- **P3** La misma fecha: con el mensaje genérico no sabe qué falló. Con el error concreto sabe el campo, el valor que falló y la regla, y eso es lo que guía la corrección (TS 4.4-K1, 4.4-S1).
- **P4** `reintento_generico`: 10 u 11 reintentos con solo 1 a 3 útiles, frente a 5 a 7 casi todos útiles con el error concreto.
- **P5** El total declarado: el modelo lo cambió para que cuadrara. Se pierde la discrepancia, que era justo el dato: el conflicto desapareció sin que nadie lo marcara. Lo correcto es extraer el total declarado y el calculado y marcar `conflict_detected` (TS 4.4-K4, 4.4-S4).

Haiku 4.5 (rol `enforcement`), 12 documentos, tres repeticiones:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | **5, 5 y 7 fechas mal** en los primeros intentos y 5, 5 y 7 reintentos de fecha (**útiles 5, 5 y 6**, uno inventado en la tercera); **0 reintentos** de total: 2 conflictos marcados en cada repetición; la factura sin pedido se marca sin reintentar (1 de 1 en cada repetición); `DC-07` («Ver adjunto») se marca como remitido a otro documento en 2 repeticiones (en la tercera el modelo escribió un número de documento y el validador no tuvo qué marcar); coste de los reintentos ~0,014–0,019 $ (total ~0,14 $) | con el error concreto, el reintento corrige lo que el documento sí contiene; lo que no contiene o remite a otro documento se marca; un total incoherente se marca sin gastar un reintento |
| `reintento_generico` | 5–7 fechas mal; **11, 10 y 11 reintentos con solo 1, 1 y 3 útiles** (inútiles 10, 9 y 7); 2 conflictos y 1 documento remitido en cada repetición; coste de los reintentos ~0,028–0,031 $ (total ~0,19 $) | sin saber qué falló, el modelo repite la misma fecha; más del doble de reintentos y de coste para casi el mismo resultado |
| `insistir` | la factura sin pedido pasa por «persiste» y acaba con **un pedido inventado en las 3 repeticiones**; `DC-07` acaba con un **número de documento inventado en las 3**; reintentos «inventaron» **4, 5 y 4**; ningún campo ni conflicto marcado; reintentos 9, 11 y 10 (útiles 5–6, inútiles 2); coste de los reintentos ~0,025–0,030 $ (total ~0,18 $) | el valor falso pasa el validador (tiene el formato `PO-nnnn` o es un número de documento cualquiera): solo la etiqueta lo delata |

Notas:

- **Un reintento empeora un total:** con `insistir`, que sí reintenta los dos totales que no cuadran (`DC-05` y `DC-09`) pidiendo que se revisen, el modelo **cambia el total declarado** para que cuadre con las líneas (*inventado*) en los dos documentos en las tres repeticiones, y el conflicto desaparece sin que nadie lo marque. La correcta ya no lo reintenta: el documento no cuadra y eso se marca (`conflict_detected`, 2 por repetición). En una versión anterior de este módulo, la correcta reintentaba el total una vez con el mensaje «revisa cantidades, precios y total» y se vio el mismo cambio de datos.
- **Dos causas de «dato ausente»:** `DC-02` no trae el pedido en ninguna parte; `DC-07` no trae el número pero dice «Ver adjunto». El validador las distingue con una búsqueda en el texto (sin modelo) y no reintenta ninguna, pero las deja marcadas con causas distintas (`missing_in_source` y `external_reference`).
- **Qué mide cada línea:** el validador de formato no distingue un pedido real de uno inventado con la forma correcta. «Inventaron» sale de comparar con la etiqueta, que el bucle no ve. «Dejaron vacío» (el reintento deja `null` un campo que la etiqueta sí tiene) salió 0 en las nueve ejecuciones.
- **Por qué Haiku 4.5:** en la sonda previa al módulo (A2, `docs/hallazgos.md`), Haiku 5.5 no escribió mal ninguna fecha en 36 primeros intentos. Sin fallos no hay nada que reintentar y la señal no aparece. Es una cifra de la sonda, no de una ejecución del módulo con `--rol-modelo agent`.
- Lo que no depende del modelo se prueba en `tests/test_app3_08_validacion_reintento.py`.

**Para pensar (sin evaluación):** ¿cómo decide el código, sin mirar etiquetas, que un dato no está en el documento? Lo hace con una búsqueda en el texto (ver las notas). Es un detalle de este módulo y no se evalúa: el concepto es que esa distinción se hace antes de reintentar.
</details>

### Pregunta tipo examen

Un proceso extrae datos de facturas y los valida con reglas de código. Cuando una falla, se reenvía al modelo con el mensaje «La extracción no es válida, inténtalo de nuevo», hasta tres veces. Los registros muestran que la mayoría de los reintentos devuelven el mismo error. Además, varias facturas que acaban pasando la validación traen un número de pedido que no figura en el documento. ¿Qué cambio resuelve las dos cosas?

- A. Subir el tope a cinco reintentos y pasar los fallidos a un modelo mayor, que suele corregirse mejor por su cuenta.
- B. Añadir al mensaje de reintento «no inventes datos» y validar además que el número de pedido tenga el formato correcto.
- C. Reenviar el documento, la extracción y el error concreto, y marcar sin reintentar los datos que el documento no contiene.
- D. Quitar el número de pedido del esquema de la tool y pedírselo al modelo en una segunda llamada separada en texto libre.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** El reintento orienta la corrección cuando lleva los errores de validación concretos, junto al documento original y a la extracción que falló (TS 4.4-K1, S1). Eso resuelve los reintentos que repiten el error. Un dato que no está en el documento no se recupera reintentando (TS 4.4-K2, S2): hay que marcarlo como ausente, porque insistir lleva a que el modelo lo invente.

- **A** da más oportunidades de inventar y no le dice a ningún modelo qué falló.
- **B** pide por escrito lo que el flujo tiene que decidir en código. Además, el pedido inventado ya cumple el formato `PO-nnnn` y pasa esa validación.
- **D** renuncia a la salida estructurada para ese campo y deja el dato ausente igual de ausente.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 4.4-K4, S4.** Una extracción con tool y JSON Schema devuelve siempre una salida bien formada, pero en algunas facturas las líneas no suman el total que la factura declara. ¿Qué diseño lo trata bien?

- A. Reintentar hasta que el modelo devuelva un total que coincida con la suma de las líneas.
- B. Activar el modo estricto del esquema, que impide que el total y las líneas discrepen.
- C. Dar por buena la salida, porque cumplir el esquema ya garantiza que el dato es correcto.
- D. Extraer el total declarado y el calculado, y marcar la discrepancia en un campo propio.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**D.** Que los valores no sumen es un error semántico de validación, distinto de los errores de sintaxis del esquema, que el uso de la tool ya elimina (TS 4.4-K4). El flujo extrae el total calculado junto al declarado para señalar la discrepancia, y marca con un booleano los datos de origen incoherentes (TS 4.4-S4). A empuja al modelo a cambiar un dato; B y C confunden la forma con el significado.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 09 · Batches: lotes, ventana y fallidos

> **Qué vas a hacer:** Enviar las extracciones del [módulo 07](#07--extracción-estructurada-con-schema) como un lote, leer sus resultados, reenviar lo que falló y decidir qué trabajos caben en un lote y cuáles no.
>
> **Necesitas antes:** El [módulo 07](#07--extracción-estructurada-con-schema), cuyas peticiones se envían aquí.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar; `--ventanas` no usa modelo y el resto cuesta unos céntimos).

### Antes de empezar

Los términos comunes (Messages API, presupuesto) están en el [glosario](../docs/glosario.md). Este módulo usa la Messages API (necesita una API key) y el esquema, los documentos y la puntuación del [módulo 07](#07--extracción-estructurada-con-schema).

- **El sistema:** una petición de extracción por documento (los 12 de `documentos_compra.json`), enviadas juntas con la Message Batches API. Es una API aparte de la normal: envías el lote, te devuelve un identificador y los resultados se leen más tarde, cuando el lote termina.
- **Términos propios:**
  - **Lote (*batch*):** un conjunto de peticiones que la API procesa de forma asíncrona, con la mitad de precio, en hasta 24 h y sin garantía de cuándo terminan.
  - **`custom_id`:** el identificador que pones a cada petición; es lo que une cada resultado con la petición de la que sale.
  - **Fallido:** una petición del lote cuyo resultado no sirve. Puede ser que el resultado no sea una respuesta (tipos `errored`, `expired` y `canceled`) o que la respuesta no se pueda usar. El módulo clasifica cada resultado y dice por qué no sirve.
  - **Troceo (*chunking*):** partir un documento largo en trozos, cada uno con su cabecera, para que cada respuesta quepa. Cada trozo es una petición con su propio `custom_id`, y sus resultados se unen después en una sola extracción.
  - **Ventana y SLA:** el plazo en el que se necesita el resultado (SLA) frente a las 24 h que puede tardar un lote (ventana).
- **Lo que el módulo no guarda:** nada. El identificador del lote lo copias tú de la salida y lo pasas a `--batch-id`.
- **Sin varios turnos:** cada petición del lote es una sola vuelta. Dentro de un lote no se puede devolver el resultado de una tool y continuar la conversación.

### El ejercicio

Opciones del módulo (cada una es un paso del flujo):

- **`--ventanas`:** sin modelo. Reparte seis trabajos de ejemplo entre tres grupos según su plazo: «cabe en batch», «cabe en batch, sin margen para reenviar fallidos» y «tiene que ir síncrono». Para los que caben, dice además cada cuántas horas hay que enviar un lote.
  - **El criterio:** cuenta todo lo que puede esperar un documento hasta tener su resultado, más un margen de 2 h elegido en este módulo (la guía no habla de margen). La fórmula está en el Paso 3: intenta deducirla antes.
- **`--enviar`:** estima una cota superior del coste, hace una **muestra síncrona** de tres documentos con los mismos parámetros y la compara con las etiquetas (acierto por campo). Si la forma no cumple el esquema o el acierto queda por debajo del umbral (`SAMPLE_MIN_ACCURACY`, 85 %, visible en el código), no se crea el lote. Imprime su identificador. `--sin-muestra` salta la muestra.
- **`--batch-id <id>`:** consulta el estado del lote y, si ha terminado, lee los resultados: orden de llegada, tipo de cada resultado, emparejado por `custom_id` y coste con el descuento. `--esperar <s>` espera hasta ese número de segundos. `--reenviar` crea un lote nuevo solo con los fallidos:
  - un **truncado** se parte en trozos (de 10 líneas la primera vez) y, si un trozo vuelve a truncarse, el documento se re-trocea a la mitad, hasta una línea por trozo; el id de cada trozo lleva su tamaño (`DC-12--s10-c3`);
  - un trozo que falla **sin truncarse** (`invalid`, `errored`, `expired`) se reenvía con su propio texto, no con el documento entero;
  - si el mismo documento tiene un trozo truncado y otro inválido, el re-troceo cubre los dos; el resultado no depende del orden de llegada.
- **`--anti por_orden`** (con `--batch-id`): empareja los resultados por posición en vez de por `custom_id`. El recuento es «X de N», con N los documentos que tienen número en la etiqueta; un resultado sin datos (truncado o fallido) no cuenta como datos de otro documento.
- **El tope `--budget` es por invocación.** Con `--enviar` cubre la muestra síncrona **más** la estimación del lote. Con `--batch-id --reenviar` cubre solo la estimación del reenvío: el lote que se lee ya se pagó en otra invocación y no se resta.

Las peticiones llevan un `max_tokens` corto (600) a propósito, para que el lote tenga algo que reenviar. Qué documento no cabe y cómo llega su resultado se ve en el Paso 3.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Las facturas del turno de noche tienen un plazo de 30 h, contado desde que llega cada una hasta que tiene su resultado, y llegan a lo largo de todo el día. Un lote puede tardar hasta 24 h en procesarse. ¿De qué dos datos sale cada cuánto hay que enviar un lote? ¿Basta con un envío al día?
2. (módulo) Con ese plazo, el módulo reserva además 2 h de margen. ¿Cada cuántas horas hay que enviar un lote para que ninguna factura se pase del plazo?
3. (módulo) Con ese mismo plazo de 30 h, si un documento falla, ¿cabe reenviarlo en un segundo lote, que puede tardar otras 24 h?
4. (guía) Envías 12 peticiones en un lote y emparejas cada resultado con su documento por posición, como hace `por_orden`. ¿Qué da por supuesto ese código sobre el lote? ¿Qué pasa si no se cumple?
5. (módulo) Una respuesta del lote se corta por `max_tokens`. ¿Con qué tipo de resultado crees que llega? ¿Qué tiene que mirar tu código para saber que no sirve?
6. (guía) `--reenviar` crea un lote solo con los fallidos y trocea el documento que no cupo. ¿Qué pasaría si reenviara ese documento tal cual? ¿Qué necesita el código para saber cuáles reenviar?
7. (guía) Antes de crear el lote, el módulo extrae una muestra de tres documentos de forma síncrona. ¿Para qué sirve?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/09_batches.py --ventanas                       # sin modelo
uv run python app3_sistema_multiagente/09_batches.py --enviar                         # muestra síncrona (con su acierto) y lote; copia el id
uv run python app3_sistema_multiagente/09_batches.py --enviar --sin-muestra           # salta la muestra
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --esperar 120    # estado y resultados
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --reenviar       # reenvía los fallidos (troceando)
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --anti por_orden # emparejado por posición
```

**Si ejecutas:** la construcción del lote, el emparejado, la clasificación de resultados, el troceo, la ventana frente a SLA y los costes se prueban sin modelo. Ejecutar sirve para ver el orden real de llegada y las respuestas truncadas, que no se pueden deducir leyendo el código. Todo el flujo (muestra, un lote, su reenvío y las lecturas) costó unos 0,0035 $. El tope `--budget` (0,25 $ por defecto) es **por invocación**: con `--enviar` suma la muestra síncrona y la estimación del lote, y con `--batch-id --reenviar` solo la estimación del reenvío (el lote leído se pagó antes y no se cuenta).

### Qué observar

El acierto por campo de la muestra antes de crear el lote; el orden de llegada frente al de envío; los tipos de resultado (qué cuenta como `ok` y qué como `truncated`); los documentos con datos de otro según el emparejado («X de N»); en el reenvío, los trozos de cada documento y si la unión coincide con la etiqueta; y el coste del lote frente al del mismo trabajo síncrono.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Del plazo y de la ventana de procesamiento de hasta 24 h: la frecuencia de envío se calcula con los dos (TS 4.5-S2). Un envío al día no basta: una factura que llega justo después esperaría casi un día hasta el siguiente envío, y el lote aún podría tardar 24 h más.
- **P2** Cada 4 h, el mismo resultado que da la guía para un plazo de 30 h. El cálculo es una inferencia propia: una factura que llega justo después de un envío espera un intervalo entero hasta el siguiente, y después el lote puede tardar toda la ventana, así que intervalo + 24 h + 2 h de margen ≤ 30 h. El margen es una elección de este módulo; sin él saldrían 6 h.
- **P3** No: un segundo lote añade otras 24 h y se pasa del plazo. Ese trabajo cabe en batch, pero sin margen para reenviar lo que falle. Es una inferencia de este módulo a partir de la ventana de hasta 24 h sin garantía de latencia (TS 4.5-K1); la guía no habla de reenvíos dentro del plazo.
- **P4** Que los resultados llegan en el orden de envío. Si no se cumple, cada documento recibe los datos de otro: por eso cada resultado se empareja con su petición por `custom_id` (TS 4.5-K4). Producto observado (no evaluable): aquí llegaron en otro orden y, emparejados por posición, 11 de 11 documentos recibieron los datos de otro.
- **P5** Como `succeeded`, igual que los buenos. Hay que mirar el `stop_reason`: `max_tokens` indica que la extracción está cortada.
- **P6** Volvería a fallar igual: se reenvían solo los documentos que fallaron, con el cambio que haga falta, que aquí es trocear el que no cupo. Para saber cuáles son, el código los localiza por su `custom_id` (TS 4.5-S3).
- **P7** Para refinar el prompt con una muestra antes de procesar el volumen: sube el acierto a la primera y baja el coste de los reenvíos (TS 4.5-S4). En este módulo la muestra hace además de barrera: si no llega al 85 % de acierto, el lote no se lanza (decisión del módulo). Detecta fallos de prompt y de esquema, no de tamaño.

Haiku 5.5, 12 documentos:

| Paso | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `--ventanas` | 3 trabajos en batch (72 h y los dos sin plazo), 1 en batch **sin margen** (30 h), 2 síncronos (8 h y 0,1 h). Frecuencia: el de 72 h, **cada 46 h** (cada 22 h si se reenvía); el de 30 h, **cada 4 h** y sin reenvío | el plazo tiene que cubrir la espera al siguiente envío además de la ventana; con 30 h sale el ejemplo de la guía, pero no queda tiempo para recuperar un fallo |
| `--enviar` | estimación (cota superior) 0,0023 $; muestra síncrona de 3 documentos (`DC-01`, `DC-02`, `DC-03`) con forma válida y **acierto 100 %** (24 de 24 campos; umbral 85 %), 0,0008 $; lote creado con 12 peticiones | la muestra es lo único que se ve antes de gastar en el lote, y ahora dice también cuántos campos acierta |
| Lectura | el lote estaba terminado al leerlo (unos minutos como mucho, nunca cerca de las 24 h); **llegaron en otro orden** (`DC-05, DC-01, DC-11, DC-03, …`); 11 `ok` y **1 `truncated`** (`DC-12`) aunque la API los daba todos por `succeeded`; coste 0,0017 $ (0,0033 $ síncrono) | el orden no es el de envío y el fallo está en el `stop_reason` |
| `--anti por_orden` | con el emparejado por posición, **11 de 11** documentos con número en la etiqueta reciben los datos de otro (el truncado `DC-12` y `DC-07` no cuentan); por `custom_id`, ninguno (de 11) | el emparejado por posición solo acierta por casualidad |
| Reenvío del truncado | 4 trozos de 10 líneas (`DC-12--s10-c1` … `c4`), **4 de 4 correctos** y las 40 líneas unidas coinciden con la etiqueta; 0,0008 $. En una medición anterior, con el mismo reenvío, **un trozo de 10 líneas volvió a truncarse** (3 de 4) y el documento re-troceado en trozos de 5 líneas dio 8 de 8 | un trozo grande puede truncarse: el documento entero se parte entonces en trozos más pequeños. Esta vez ningún trozo se truncó, así que **el re-troceo en cadena no se vio en vivo** (sí en los tests, hasta una línea por trozo) |

Notas:

- **La fórmula de `--ventanas`:** un documento que llega justo después de un envío espera un intervalo entero hasta el siguiente. Después, el lote puede tardar la ventana completa, y otra más por cada reenvío. Por eso tiene que cumplirse `intervalo + 24 h × (1 + reenvíos) + margen ≤ plazo`. **El margen de 2 h es una elección de este módulo:** la guía da el resultado (enviar cada 4 h para un SLA de 30 h), pero no el cálculo. Sin margen saldrían 6 h.
- **La API no marca la respuesta truncada como error:** devuelve `succeeded` con `stop_reason: max_tokens` y un `tool_use` incompleto (en la sonda, sin `line_items`). Quien solo mire el tipo de resultado da por buena una extracción cortada.
- **El tope de coste de un lote no se puede imponer a mitad:** la Batches API no tiene un corte como `max_budget_usd`. Por eso el módulo estima una cota superior antes de enviar y se niega si la estimación, sumada a lo ya gastado en esa invocación (la muestra), supera el tope. Al reenviar, el lote leído no cuenta: ya se pagó.
- **La muestra no garantiza el lote:** acertó 24 de 24 con tres documentos cortos, pero el único fallo del lote (`DC-12`, el albarán largo) no estaba en ella. La muestra detecta fallos de prompt y de esquema, no de tamaño.
- **Un documento sin número en la etiqueta** (`DC-07`) puede salir con uno inventado; eso no es un cruce de documentos y no cuenta en el emparejado (se mide en el módulo 07).
- Lo que no depende del modelo se prueba en `tests/test_app3_09_batches.py`; el descuento, en `tests/test_budget.py`.

**Para pensar (sin evaluación):** si un trozo reenviado vuelve a truncarse, ¿qué harías con él y con el resto del lote? El módulo lo re-trocea a la mitad; es su algoritmo, no un concepto de la guía, y no se evalúa.
</details>

### Pregunta tipo examen

Un equipo usa Claude para dos trabajos. El primero revisa cada *pull request* antes del merge, y el desarrollador espera el resultado para fusionar. El segundo extrae cada noche los datos de unas 20 000 facturas, que se consultan a la mañana siguiente. En el segundo trabajo fallan cada noche unas decenas de facturas largas por superar el límite de contexto. Para recortar el coste, se plantea pasar los dos trabajos a la Message Batches API. ¿Qué diseño es el adecuado?

- A. La revisión con la API síncrona y las facturas en lote; las fallidas, troceadas y reenviadas por su `custom_id`.
- B. Los dos trabajos en lote con un `custom_id` por petición, y relanzar el lote nocturno completo con las facturas troceadas.
- C. Los dos trabajos con la API síncrona, troceando antes las facturas largas para que ninguna supere el contexto.
- D. La revisión en lote con una tool de varios turnos que avise al autor, y las facturas troceadas con la API síncrona.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** La revisión previa al merge bloquea a una persona, y el lote no garantiza la latencia: va con la API síncrona. La extracción nocturna tolera la espera y se ahorra la mitad (TS 4.5-K1, K2, S1). Las facturas fallidas se reenvían solas, localizadas por su `custom_id` y troceadas (TS 4.5-K4, S3).

- **B** deja a quien quiere fusionar esperando hasta 24 h y paga otra vez las 20 000 facturas por unas decenas.
- **C** renuncia al 50 % en un trabajo que nadie espera.
- **D** invierte el reparto. Además, dentro de una petición del lote no hay tool calling de varios turnos (TS 4.5-K3).
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 4.5-S2.** Los documentos tienen que estar procesados, como mucho, 30 horas después de llegar, y un lote puede tardar hasta 24. ¿Qué decide cada cuánto se envía un lote?

- A. El tamaño del lote: se envía cuando reúne un número fijo de documentos.
- B. El precio: se envía una vez al día, para aprovechar mejor el descuento.
- C. El plazo: la espera hasta el envío y la ventana del lote tienen que caber en él.
- D. La carga de la API: se envía cuando hay menos peticiones en curso.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**C.** La frecuencia de envío se calcula a partir del plazo comprometido y de la ventana de proceso de hasta 24 h; la guía pone el ejemplo de ventanas de 4 h para un plazo de 30 h (TS 4.5-S2). A, B y D eligen la frecuencia por algo que no es el plazo, y con un envío diario un documento puede esperar casi dos días.
</details>

**C2 · TS 4.5-S4.** Antes de enviar 50 000 documentos a la Message Batches API con un prompt nuevo, ¿qué conviene hacer?

- A. Enviarlos todos ya, y reenviar después los que fallen con el prompt corregido.
- B. Afinar el prompt con una muestra, para que el lote acierte más a la primera.
- C. Partirlos en cincuenta lotes iguales, para que cada uno termine mucho antes.
- D. Subir `max_tokens` al máximo, para que ninguna respuesta pueda quedar cortada.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**B.** El prompt se refina sobre una muestra antes de procesar el volumen: sube el acierto a la primera y baja el coste de los reenvíos (TS 4.5-S4). A paga el error en todo el volumen; C y D no mejoran el prompt.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 10 · Confianza y revisión humana

> **Qué vas a hacer:** Medir la exactitud de 292 extracciones con confianza por campo, en conjunto y por tipo de documento y campo; comprobar si la confianza está calibrada, fijar umbrales de revisión por segmento, comparar dos formas de muestrear lo automatizado y decidir qué se revisa cuando la capacidad de revisión es limitada.
>
> **Necesitas antes:** El [módulo 07](#07--extracción-estructurada-con-schema) (el esquema y las etiquetas de la parte con modelo) y el [08](#08--validación-y-reintento-con-error-concreto) (de ahí viene `conflict_detected`).
>
> **Modo:** Ejecución ligera (la parte `poblacion` no usa modelo y sale igual cada vez; la parte con modelo cuesta unos 0,01–0,13 $ y es opcional).

### Antes de empezar

Los términos comunes (confianza por campo, calibración, muestreo estratificado, cola de revisión, etiqueta) están en el [glosario](../docs/glosario.md). La parte `poblacion` trabaja con datos sintéticos que genera `datos/generar_sinteticos.py` (`poblacion_extracciones.json` y sus etiquetas, que el módulo solo usa para puntuar): 292 documentos de compra, 6 campos cada uno, la mitad de cada tipo como conjunto de calibración y la otra mitad como producción. La parte `confianza_modelo` usa los 12 documentos del módulo 07 con la Messages API (necesita una API key).

- **Términos propios:**
  - **`field_confidence`:** el campo del esquema de la tool donde el modelo escribe la confianza de cada valor. En la parte `poblacion` la confianza no la da un modelo: la simula el generador.
  - **Banda de confianza:** un intervalo de confianza declarada («0,95–1,00»). La calibración se mide banda a banda: acierto real frente a confianza media declarada.
  - **Segmento:** un tipo de documento, un campo o la combinación de ambos. La exactitud se calcula por segmento, no solo en conjunto.
  - **Umbral de revisión:** la confianza por encima de la cual una extracción se acepta sin revisión. Se fija con el conjunto de calibración, por segmento.
  - **Estrato:** aquí, la combinación de tipo de documento y campo. La muestra estratificada toma un mínimo de cada uno; la simple sortea sobre toda la población.
  - **Cupo de revisión:** cuántos documentos puede mirar el equipo en el periodo. El módulo compara tres órdenes de la cola con el mismo cupo.

### El ejercicio

La parte `poblacion` calcula, con reglas de código y sin modelo: la exactitud global y por segmento, las bandas de calibración, el estado de cada segmento (`ready`, `below_target` o `insufficient_data` con un objetivo del 98 % y al menos 20 ejemplos), el enrutado de producción, un experimento de muestreo (500 repeticiones de una muestra de 60) y tres órdenes de la cola de revisión.

- **Correcta:** un umbral por tipo y campo, calibrado en el conjunto de calibración.
- **`--anti precision_agregada`:** un único umbral para todos los segmentos, el que cumple el objetivo mirando solo la exactitud global. Todo lo demás es igual.
- **`--anti confianza_global`:** se decide con una sola confianza por documento (la media de las de sus campos) en lugar de una por campo. El umbral sigue siendo por segmento, como en la correcta; solo cambia la confianza.

La parte `confianza_modelo` pide a un modelo que extraiga los 12 documentos con la confianza de cada campo, y compara lo que dice con lo que acierta. Mide si la confianza declarada está calibrada; los umbrales de revisión solo se fijan en la parte `poblacion`, sobre la confianza simulada. `--sin-reglas-de-formato` quita de las descripciones del esquema las reglas de formato (como en el módulo 08) para que un modelo capaz cometa errores que calibrar.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Una extracción acierta el 97 % de los valores en conjunto. ¿Puede haber un tipo de documento que rinda mucho peor sin que esa cifra lo muestre? ¿De qué depende cuánto puede esconder?
2. (guía) Para vigilar lo que se acepta con confianza alta, ¿qué muestra verá más a menudo los errores de un tipo de documento poco frecuente: una aleatoria simple o una estratificada? ¿Por qué?
3. (guía) El modelo declara una confianza de 0,99 en un campo. ¿Qué más hace falta saber para decidir si basta para no revisarlo?
4. (guía) Un segmento (un tipo de documento y un campo) tiene muy pocos ejemplos etiquetados. ¿Debería el sistema dejar de revisar sus extracciones de confianza alta? ¿Por qué?
5. (módulo) Un documento tiene una confianza media alta, pero uno de sus campos es dudoso. ¿Qué decide `confianza_global`, que usa una sola confianza por documento, y qué decidiría una confianza por campo?
6. (guía) Además de las extracciones de confianza baja, ¿qué documentos deben ir a una persona? ¿Por qué hay que priorizar la cola de revisión?
7. (módulo) En la parte `confianza_modelo`, ¿qué tiene que haber en las extracciones para que se pueda medir si la confianza declarada está calibrada?
8. (módulo) Con `--sin-reglas-de-formato`, ¿en qué clase de campo esperas que el modelo esté más seguro de lo que debería?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/10_confianza_y_revision.py                                  # población, correcta (sin modelo)
uv run python app3_sistema_multiagente/10_confianza_y_revision.py --anti precision_agregada        # un umbral para todos
uv run python app3_sistema_multiagente/10_confianza_y_revision.py --anti confianza_global          # una confianza por documento
uv run python app3_sistema_multiagente/10_confianza_y_revision.py --parte confianza_modelo --repeat 3
uv run python app3_sistema_multiagente/10_confianza_y_revision.py --parte confianza_modelo --rol-modelo enforcement --sin-reglas-de-formato --repeat 3
```

**Si ejecutas:** `poblacion` es gratis y sale igual cada vez. La parte con modelo gasta ~0,014 $ con Haiku 5.5 y ~0,13 $ con Haiku 4.5 (3 repeticiones; el tope es `--budget`).

### Qué observar

En `poblacion`: la exactitud global frente a la del peor tipo de documento y del peor formato y campo; las bandas de calibración; qué segmentos no se automatizan y por qué; los errores que quedan entre lo automatizado según la variante; la muestra simple frente a la estratificada; y los errores de extracción y los documentos con conflicto que ve cada orden de la cola. En `confianza_modelo`: la confianza media cuando acierta y cuando falla, los errores con confianza alta y las bandas.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Sí: el global es 97,7 % y el tipo raro acierta el 62,5 %. Una exactitud agregada puede ocultar un rendimiento pobre en tipos de documento o campos concretos (TS 5.5-K1). Inferencia propia: cuanto menos pesa un segmento en el total, más puede esconder la cifra agregada.
- **P2** La estratificada: vio algún error del tipo raro en el 100 % de las muestras, frente al 53,4 % de la aleatoria simple, porque asegura un mínimo por estrato. Mide la tasa de error y deja ver patrones que no se conocían (TS 5.5-K2, 5.5-S1). Inferencia propia, que la guía no recoge: para estimar la tasa hay que ponderar cada estrato por su tamaño.
- **P3** Si esa confianza está calibrada contra un conjunto de validación etiquetado, que es de donde salen los umbrales de revisión (TS 5.5-K3, 5.5-S3). Aquí la mayoría de los errores llegan con confianza de 0,85 o más.
- **P4** No: sin ejemplos no hay evidencia de que acierte. La exactitud se comprueba segmento a segmento antes de dejar de revisar (TS 5.5-K4, 5.5-S2). Aquí esos segmentos quedan como `insufficient_data` y no se automatizan.
- **P5** La media del documento deja pasar el campo dudoso (2 errores más); la confianza por campo lo manda a revisión. La diferencia es pequeña con esta población simulada.
- **P6** Los ambiguos o contradictorios, aunque su confianza sea alta (en el módulo, los marcados `conflict_detected` o ambiguos). Se prioriza porque la capacidad de revisión es limitada (TS 5.5-S4).
- **P7** Errores: si el modelo no falla, no hay nada que calibrar. Con el modelo por defecto hubo 0 errores en 153 valores.
- **P8** En las fechas: casi todos los errores son de formato de fecha y llegan con confianza de 0,85 o más; la banda más alta acierta el 82,9 % y declara el 100 %.

**Parte `poblacion`** (sin modelo; mismos números en cada ejecución):

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | global 97,7 % de 1752 valores; `other`: 62,5 % (72 valores, 27 errores) frente a 99,0 % de las facturas; facturas en prosa, `issue_date`: 86,0 %. Se automatizan 765 valores con **6 errores (0,8 %)** y **0 del tipo raro**: sus 6 campos son `insufficient_data` | el titular esconde el tipo raro; con 6 documentos por conjunto no hay evidencia para automatizarlo |
| `precision_agregada` | automático 805 valores con **17 errores (2,1 %)**; **34 valores del tipo raro aceptados, 11 con error** | un umbral para todos hereda la confianza de los segmentos grandes |
| `confianza_global` | umbral por segmento sobre la confianza del documento; automático **768 valores con 8 errores (1,0 %)** y **0 del tipo raro** | la media del documento deja pasar 2 errores más que la confianza por campo: una diferencia pequeña, en el límite de lo que muestra una sola población simulada |

Una versión anterior de `confianza_global` cambiaba dos cosas, la confianza por documento y un umbral único (0,92), y daba 780 valores con 14 errores (1,8 %), 8 del tipo raro. Al dejar el umbral por segmento, el tipo raro deja de colarse: lo que lo dejaba pasar era el umbral único, no la confianza por documento.

Calibración (conjunto de calibración): la banda 0,95–1,00 acierta el 98,7 % (declara 96,9 %) y la 0,85–0,95, el 97,2 % (declara 92,2 %); hueco ponderado 0,034. **Aun así, la mayoría de los errores llegan con confianza ≥ 0,85:** 17 de los 19 errores del conjunto de calibración y 17 de los 22 de producción (los 41 errores de la población; 27 de ellos están en el tipo raro). Que el hueco sea pequeño en conjunto no quiere decir que la confianza sirva sola.

Muestra de 60 de las 871 extracciones de confianza alta de producción, 500 repeticiones:

| Muestreo | Ve algún error del tipo raro | Patrones de error por muestra (de 8) | Tasa de error estimada (real: 2,0 %) |
| :--- | :--- | :--- | :--- |
| aleatorio simple | 53,4 % de las muestras | 1,0 | 1,8 % (sin ponderada: un estrato puede quedar sin muestra) |
| estratificado (tipo y campo, mínimo 3) | 100 % de las muestras | 3,7 | 10,8 % cruda; **2,0 % ponderada** por el tamaño de cada estrato |

La muestra estratificada ve el tipo raro porque lo sobrerrepresenta: el mínimo de 3 por estrato le da 18 de los 60 valores, cuando el tipo raro es el 4 % de la población. Eso es lo que la hace útil para encontrar patrones de error y lo que la vuelve engañosa para estimar la tasa: la cruda la multiplica por cinco. Para vigilar la tasa de lo aceptado, cada estrato se pondera por su tamaño.

Cola de revisión (25 documentos con algo que revisar, capacidad 6, variante correcta):

| Orden | Errores de extracción vistos (de 16) | Documentos con conflicto o ambiguos vistos (de 11) |
| :--- | :--- | :--- |
| llegada | 4 | 4 |
| confianza (la más baja primero) | 8 | 1 |
| prioridad (conflictos primero) | 0 | 6 |

Con poca capacidad, un orden ve unos y deja los otros. **Esto es una propiedad de los datos, no una lección:** el generador sortea los conflictos y los errores de extracción por separado (en producción no hay ningún error en un documento marcado), así que los dos órdenes no pueden solaparse. Con datos reales, conflicto y error podrían ir juntos. Lo que sí sostiene la guía es que la cola se prioriza (5.5-S4), no qué orden gana.

**Parte `confianza_modelo`** (Messages API, 12 documentos × 3 repeticiones):

| Modelo de la medida | Descripciones | Señal observada |
| :--- | :--- | :--- |
| Haiku 5.5 (rol `agent`, ~0,014 $) | con reglas de formato | **0 errores en 153 valores extraídos**: no hay nada que calibrar. Confianza media 0,95 cuando acierta; el hueco de calibración es 0,046 por declarar menos de lo que acierta. En los campos que deja en `null` la confianza media es 0,64–0,65 |
| Haiku 4.5 (rol `enforcement`, ~0,13 $) | sin reglas de formato | **6, 7 y 7 errores por repetición, casi todos de formato de fecha, con confianza ≥ 0,85 en 5, 7 y 5**; banda 0,97–1,00: **acierta el 82,9 %** y declara el 100 %; hueco de calibración 0,076. En los `null`, confianza media 0,21–0,33. Medida de la segunda ejecución (2026-11-07); la primera dio 6, 7 y 8 errores, con confianza ≥ 0,85 en 5, 7 y 7, y la banda alta acertaba el 85,5 % declarando 99,5 %: la señal se mantiene |

Notas:

- **El modelo está más seguro donde falla:** los errores de fecha de Haiku 4.5 llegan con 0,95–1,0, porque el modelo lee bien la fecha y se equivoca en la forma. La confianza declarada no los distingue de los aciertos. Una medida que dé cero no demuestra que detecte el fallo, por eso `tests/test_app3_10_confianza_y_revision.py` incluye un control positivo sintético (un conjunto mal calibrado da un hueco de ~0,45 y uno calibrado, ~0).
- **La confianza de un campo en `null` habla de la ausencia:** con Haiku 4.5 ronda 0,32 aunque el `null` sea correcto, y mezclarla con los valores extraídos daba un hueco de calibración de 0,137 con Haiku 5.5 que era un artefacto. El módulo la mide aparte.
- **Segmentos pequeños:** con 6 documentos por conjunto, el tipo raro no llega a los 20 ejemplos de confianza alta que se piden. No se puede validar, así que no se automatiza (`insufficient_data` no es lo mismo que `below_target`).
- La población es simulada (la genera `datos/generar_sinteticos.py`): la confianza de sus valores no es la de un modelo real. **Los umbrales por segmento (5.5-S3) solo se fijan sobre esa confianza simulada.** La parte con modelo es la única que mide una confianza declarada de verdad, y lo que mide es su calibración: no fija umbrales con ella.
- Lo que no depende del modelo se prueba en `tests/test_app3_10_confianza_y_revision.py` y `tests/test_datos_entrega3c.py`.
</details>

### Pregunta tipo examen

Un sistema extrae campos de facturas, albaranes y un tipo de documento de compra poco frecuente. Su exactitud global medida es del 97 %, y el equipo propone dejar de revisar todo lo que el modelo marque con confianza alta. ¿Qué debe hacerse antes de reducir la revisión humana?

- A. Elegir un único umbral de confianza con el que la exactitud global de lo aceptado llegue al 99 % y no revisar lo que lo supere.
- B. Pedir al modelo una confianza por documento, la media de las de sus campos, y no revisar los documentos que superen un umbral.
- C. Medir con documentos etiquetados cuánto acierta cada tipo de documento y cada campo, y fijar con ellos un umbral por segmento.
- D. Mantener el 97 % como criterio de aceptación y revisar cada mes una muestra aleatoria simple de lo que se acepta sin revisión.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Una exactitud agregada alta puede esconder un tipo de documento o un campo que rinde mal (TS 5.5-K1), así que antes de automatizar se comprueba la exactitud por tipo y por campo (K4, S2). La confianza por campo solo sirve para enrutar después de calibrarla con un conjunto etiquetado, que fija los umbrales (K3, S3). Después, lo aceptado se sigue vigilando con una muestra aleatoria estratificada (K2, S1).

- **A** elige el umbral mirando la cifra global, que es justo la que puede esconder el segmento malo (K1, K4).
- **B** junta los campos de un documento en una sola cifra, cuando la guía habla de confianza por campo (K3), y no mide nada por tipo ni por campo (K4).
- **D** decide por el titular (K1) y vigila con una muestra simple, cuando la guía pide estratificarla (K2, S1).

**Inferencia propia:** la media de un documento esconde el campo dudoso detrás de los buenos, y una muestra simple apenas toca un tipo poco frecuente. Son las lecturas de este módulo (`confianza_global` y el experimento de muestreo del Paso 3); la guía no las formula así.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 5.5-K2, S1.** Las extracciones de confianza alta ya no se revisan una a una. ¿Cómo se sigue vigilando su calidad?

- A. Con una muestra aleatoria estratificada, que mide la tasa de error y destapa patrones nuevos.
- B. Revisando solo las extracciones cuya confianza baje del umbral que se fijó al principio.
- C. Con una revisión completa una vez al año, cuando se renueve el conjunto de validación.
- D. No hace falta: si la confianza es alta, el error que queda es despreciable por definición.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**A.** Lo que se acepta con confianza alta se sigue vigilando con una muestra aleatoria estratificada: mide la tasa de error de forma continua y deja ver patrones de error que no se conocían (TS 5.5-K2, 5.5-S1). B no mira lo aceptado; C llega tarde; D da por buena la confianza sin comprobarla.
</details>

**C2 · TS 5.5-K3, S3.** El modelo acompaña cada campo extraído con una confianza. ¿Cuándo sirve para decidir qué se revisa?

- A. Siempre: una confianza de 0,9 significa que acierta nueve de cada diez veces.
- B. Nunca: la confianza que declara un modelo no guarda relación con su acierto.
- C. Cuando el modelo la declara con dos decimales y la justifica con un comentario.
- D. Cuando se ha calibrado con un conjunto etiquetado, de donde salen los umbrales.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**D.** La confianza por campo sirve para decidir dónde mirar solo después de calibrarla contra un conjunto de validación etiquetado, que es de donde salen los umbrales de revisión (TS 5.5-K3, 5.5-S3). A la toma sin calibrar; B la descarta del todo, cuando lo que la guía da por poco fiable es usar la confianza autodeclarada como medida de la complejidad de un caso (TS 5.2-K3, en `app2/04`), no la confianza por campo ya calibrada; C confunde formato con fiabilidad.
</details>

**C3 · TS 5.5-K4, S2.** La exactitud global es del 98 % y se propone dejar de revisar las extracciones de confianza alta. ¿Qué se comprueba antes?

- A. Que ese 98 % se mantiene durante un mes seguido, sin necesidad de más detalle.
- B. Que el modelo declara una confianza media superior a la exactitud global medida.
- C. Que la exactitud es consistente por tipo de documento y por campo, no solo en conjunto.
- D. Que los documentos más frecuentes son también los que el modelo extrae mejor.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**C.** Antes de dejar de revisar, se comprueba la exactitud segmento a segmento, por tipo de documento y por campo, y se exige que sea consistente en todos (TS 5.5-K4, 5.5-S2): una cifra agregada alta puede ocultar un segmento que rinde mal (TS 5.5-K1). A y B siguen mirando solo el conjunto; D es justo lo que esconde el problema.
</details>

**C4 · TS 5.5-S4.** La capacidad de revisión humana es limitada. ¿Qué extracciones van a una persona?

- A. Una de cada diez, elegidas al azar entre todas las que han llegado ese mismo día.
- B. Las de confianza baja y las de documentos ambiguos o contradictorios, con la cola priorizada.
- C. Solo las que el propio modelo pide revisar en un comentario al final de su respuesta.
- D. Las de los documentos más largos, porque tienen más campos en los que equivocarse.

<details>
<summary>Comprobación C4 · Respuesta</summary>

**B.** A una persona van las extracciones con confianza baja y las de documentos ambiguos o contradictorios, y la cola se prioriza porque la capacidad de revisión es limitada (TS 5.5-S4). A gasta la revisión al azar; C depende de que el modelo se delate; D usa un criterio que no mide el riesgo.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 11 · Criterios y revisión en CI

> **Qué vas a hacer:** Revisar con `claude -p` un cambio de dos commits sobre una copia temporal de `repo_mesa` que lleva fallos sembrados, un cambio correcto y un patrón aceptable: con criterios categóricos o con «sé conservador», con y sin ejemplos, con y sin los hallazgos de la revisión anterior, y pedir también los tests que faltan.
>
> **Necesitas antes:** Nada. Si vienes del [módulo 08](#08--validación-y-reintento-con-error-concreto), su patrón de fallo agrupa las causas de una extracción que falla; el `detected_pattern` de aquí es otra cosa: agrupa los hallazgos de revisión que se descartan.
>
> **Modo:** Ejecución ligera (`--parte orden` no usa modelo y enseña la orden entera; cada ejecución con modelo cuesta unos 0,02 $).

### Antes de empezar

Los términos comunes (`detected_pattern`, *few-shot*, sesión, JSON Schema) están en el [glosario](../docs/glosario.md). Este módulo no usa la Messages API ni el Agent SDK: lanza la CLI `claude -p` con la orden que construye [`harness/headless.py`](../harness/headless.py) y que imprime entera antes de ejecutarla. Hereda la credencial del entorno (se probó con una API key). El cambio y sus etiquetas (que el revisor nunca ve) los genera `datos/generar_sinteticos.py` (`cambio_revision.json` y `cambio_revision_etiquetas.json`) y se aplica sobre una copia temporal de `repo_mesa` con `git`, así que `datos/sinteticos/` no se toca.

- **El sistema:** una copia temporal de `repo_mesa` con su propio `CLAUDE.md` (el contexto de CI: convenciones y estándares de tests), un commit base y dos commits de cambio. El primero siembra cinco fallos de categorías distintas (`bug`, `security`, `comment` y dos entre archivos) y lleva además un cambio correcto que parece un fallo y un patrón aceptable que parece un problema. El segundo arregla uno y añade otro nuevo.
- **La orden:** `claude -p --output-format json --json-schema …`, con la configuración de usuario y los servidores MCP fuera, solo el `CLAUDE.md` del directorio de trabajo, solo las tools `Read`, `Grep` y `Glob`, un tope de coste y el prompt por la entrada estándar. La sonda C1 (`docs/hallazgos.md`) explica cada flag.
- **Términos propios:**
  - **Hallazgo:** un elemento de la salida estructurada, con archivo, línea, categoría, severidad, problema, arreglo propuesto y `detected_pattern`.
  - **Criterios categóricos:** lista de lo que se informa (`bug`, `comment`, `security`), de lo que no (estilo menor, patrones locales) y de qué es cada severidad con un ejemplo de código.
  - **`detected_pattern` aquí:** un nombre corto en `snake_case` que escribe el propio modelo en cada hallazgo. El registro de descartados agrupa por ese nombre tras igualar mayúsculas y separadores (`normalize_pattern`).
  - **Descartado:** un hallazgo que no coincide con ningún fallo sembrado: un falso positivo, o una marca del cambio correcto o del patrón aceptable.
  - **Segunda revisión:** la revisión del diff completo de la rama tras un commit nuevo. Con hallazgos previos, el prompt los lista y pide informar solo de lo nuevo o de lo no resuelto.
  - **Coincide con un fallo sembrado:** el hallazgo cae en su archivo, a dos líneas o menos, o nombra su función o símbolo con el nombre completo; si la línea es la de otro elemento etiquetado (por ejemplo, el cambio correcto), manda la línea. Un fallo entre archivos también se encuentra en sus llamadores si el hallazgo habla de la clave o de la unidad.

### El ejercicio

`--parte orden` construye el repositorio temporal y muestra la orden y el tamaño del prompt, sin ejecutar nada. `--parte revision` revisa el diff del primer commit; `--parte rerevision`, el diff completo de la rama tras el segundo; `--parte tests` pide los tests que faltan para el primer commit. Cada variante cambia una sola cosa respecto a la correcta:

- **Correcta (`revision`):** criterios categóricos con severidades y un ejemplo de código por severidad, y *few-shot* con el formato de salida y un patrón aceptable que no se informa.
- **`--anti conservador`:** los criterios y las severidades se sustituyen por «Sé conservador: informa solo de los problemas de los que estés muy seguro». El *few-shot* y el schema son los mismos.
- **`--anti sin_ejemplos`:** sin el bloque *few-shot*; los criterios siguen.
- **`--sin-categoria comment`:** la categoría `comment` desaparece de los criterios y del schema. Las definiciones de las demás no se tocan: ninguna se apoya ya en un comentario (en una versión anterior, el ejemplo de `minor` era un comentario y el de `bug` citaba un docstring, así que quitar la categoría cambiaba también esas dos).
- **Correcta (`rerevision`):** la segunda revisión lleva la lista de los hallazgos previos (construida desde las etiquetas) y la orden de informar solo de lo nuevo o de lo no resuelto. **`--anti sin_previos`:** el mismo prompt, sin esa lista.
- **Correcta (`tests`):** el prompt lleva los tests existentes y el `CLAUDE.md` tiene los estándares de tests. **`--anti sin_tests_existentes`:** sin los tests existentes. **`--anti sin_estandares`:** un `CLAUDE.md` sin esa sección. En esta parte la orden va sin tools, para que el modelo no pueda descubrir por su cuenta lo que se le quita del contexto.

Los fallos sembrados se nombran con una letra en la salida y en el Paso 3:

- **A** (`bug`, `tickets/escalado.py`): argumentos intercambiados al llamar a `debe_escalar`. El segundo commit lo arregla.
- **B** (`security`, `notificaciones/avisos.py`): el mensaje y el id llegan sin validar a `os.system`.
- **C** (`comment`, `config.py`): el comentario dice que el máximo es 30 y `NOTIF_TIMEOUT` vale 60.
- **D** (entre archivos): `calcular_sla` devuelve minutos y sus llamadores siguen leyendo horas.
- **E** (`bug`, del segundo commit, `informes/resumen.py`): división por cero con una lista vacía. Solo entra en la segunda revisión.
- **F** (entre archivos): `avance_plazo` devuelve una fracción de 0 a 1 y `texto_progreso` la imprime como porcentaje.

Además, el **cambio correcto** (el comentario que justifica `REINTENTOS`) y el **patrón aceptable** parecen fallos y no lo son.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) `conservador` sustituye los criterios por «sé conservador: informa solo de los problemas de los que estés muy seguro». ¿Qué efecto cabe esperar en la precisión de la revisión frente a unos criterios categóricos explícitos?
2. (guía) El bloque *few-shot* de la revisión muestra el formato de un hallazgo y un patrón aceptable que no se informa. Sin él (`sin_ejemplos`), ¿qué dos cosas cabe esperar que empeoren en la salida?
3. (módulo) Cada variante se mide con 5 ejecuciones sobre el mismo cambio. ¿Esperas que eso baste para distinguir el efecto de `conservador` y de `sin_ejemplos` de la variación entre ejecuciones?
4. (guía) Una categoría de hallazgos genera muchos falsos positivos. ¿Qué coste tiene dejarla activa? ¿Qué se hace con ella mientras se mejora su prompt?
5. (módulo) Con `--sin-categoria comment`, la categoría desaparece del prompt y del schema. ¿Qué puede pasar con el fallo real C, que caía en ella?
6. (guía) Con `sin_previos`, la segunda revisión vuelve a mirar el diff completo de la rama sin la lista de lo ya publicado. ¿Qué verán los desarrolladores en el PR tras el commit nuevo? ¿Por qué?
7. (guía) En `tests`, ¿qué se evita al poner los tests existentes en el contexto? ¿Qué aporta documentar los estándares de tests en el `CLAUDE.md`?
8. (módulo) El nombre del `detected_pattern` lo escribe el propio modelo en cada hallazgo. ¿Qué problema esperas al agrupar los descartados por ese nombre?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/11_criterios_y_ci.py                                       # la orden, sin ejecutar nada
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte revision --repeat 3
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte revision --anti conservador --repeat 3
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte revision --anti sin_ejemplos --repeat 3
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte revision --sin-categoria comment --repeat 3
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte rerevision --repeat 3                    # con los hallazgos previos
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte rerevision --anti sin_previos --repeat 3
uv run python app3_sistema_multiagente/11_criterios_y_ci.py --parte tests --repeat 3                         # y --anti sin_tests_existentes | sin_estandares
```

**Si ejecutas:** la construcción del repositorio, de los prompts, del schema, la puntuación contra lo sembrado y el registro de descartados se prueban sin modelo. Cada ejecución con modelo (rol `reviewer`, Sonnet 5.5) cuesta unos 0,015–0,03 $; el tope es `--budget` y se reparte entre las repeticiones. La salida empieza con la línea `[contexto]` de una ejecución mínima de la misma orden: debe decir 0 servidores MCP y 0 skills.

### Qué observar

En `revision`: qué fallos sembrados encuentra (A a F, el segundo commit añade E), cuáles faltan, cuántos hallazgos no coinciden con ninguno, si marca el cambio correcto o el patrón aceptable, la precisión por categoría y el registro de descartados por `detected_pattern`, con la ubicación de cada uno. En `rerevision`: lo nuevo frente a lo que repite de la primera revisión. En `tests`: los escenarios repetidos y cuáles.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Según la guía, una instrucción general de ese tipo no mejora la precisión como lo hacen los criterios categóricos, que dicen qué se informa y qué se deja (TS 4.1-K1, 4.1-K2, 4.1-S1). Aquí no se vio: `conservador` encontró los cinco fallos y marcó menos. En el examen manda la guía.
- **P2** La consistencia del formato, que los ejemplos fijan en cada hallazgo (TS 4.2-S2), y los falsos positivos, porque los ejemplos enseñan a distinguir un patrón aceptable de un problema real (TS 4.2-S3). En la medida no hubo diferencia.
- **P3** No basta: las variantes difieren en 0 o 1 hallazgos de 25. Lo único que se mueve es la marca del comentario que justifica `REINTENTOS` (3 de 5 sin `--anti`, 0 de 5 con `conservador`).
- **P4** Cuesta confianza: quien lee deja de fiarse también de las categorías que aciertan (TS 4.1-K3). Se apaga por un tiempo mientras se mejora su prompt (TS 4.1-S2).
- **P5** Puede perderse o salir en otra categoría: C faltó en 1 de 5. La marca falsa del comentario desaparece (0 de 5), pero a veces se va también el acierto.
- **P6** Comentarios duplicados: el revisor no sabe qué se publicó ya, y sin la lista repitió B, C y D en 3 de 3. Por eso los hallazgos anteriores van en el contexto, con la orden de informar solo de lo nuevo o de lo no resuelto (TS 3.6-S3). Esta parte se midió antes de las últimas correcciones.
- **P7** Se evita proponer escenarios que la suite ya cubre (TS 3.6-S4). El `CLAUDE.md` es por donde llega el contexto del proyecto en CI, y documentar ahí los estándares mejora los tests y reduce los que aportan poco (TS 3.6-K3, 3.6-S5). En la medida, sin los tests existentes no hubo repetidos (sin diferencia), y sin los estándares salieron más tests (9 a 12 frente a 7 u 8).
- **P8** Que el mismo patrón salga con nombres distintos y el registro lo disperse: el comentario del cambio correcto salió como `misleading_comment`, `dubious_comment`, `comment_does_not_match_code`… El campo sirve para analizar qué patrones se descartan (TS 4.4-K3, 4.4-S3), pero solo agrupa bien si el nombre es estable; `normalize_pattern` solo iguala mayúsculas y separadores.

Sonnet 5.5 (rol `reviewer`), `claude -p` aislado. **Las cifras de referencia son las de después de las correcciones C4** (2026-11-07, 5 ejecuciones por variante, la misma puntuación en toda la batería): cada revisión corre sobre el árbol del commit que revisa, un escenario de test se compara con lo que espera y el símbolo se compara por nombre completo. Las cifras anteriores están más abajo, rotuladas «antes», y **no son comparables**: el revisor del primer commit leía el árbol del segundo, donde A ya estaba arreglado, la puntuación era otra, el prompt de todas las variantes era otro (la línea de `bug` citaba el docstring y el ejemplo de `minor` era otro) y los datos tenían `TIMEOUT` duplicado (ahora `NOTIF_TIMEOUT`).

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | las cinco (A, B, C, D y F) en 5 de 5; 0 falsos positivos; la puntuación da «marca el cambio correcto» en 5 de 5, pero 2 son el renombrado a `NOTIF_TIMEOUT` (un artefacto, ver la nota): **la marca del comentario de `REINTENTOS` sale en 3 de 5**; ~0,019 $ por ejecución | los criterios encuentran todo, pero no evitan la marca del comentario que justifica un valor |
| `conservador` | las cinco en 5 de 5; 0 falsos positivos; **0 marcas del cambio correcto** | al revés de lo que dice la guía (4.1-K2): «sé conservador» no perdió nada y marcó menos. Ver «Lo que no coincide con la guía» |
| `sin_ejemplos` | 24 de 25 (B falta en una ejecución); 0 falsos positivos; marca el cambio correcto en 4 de 5 | **sin diferencia** con la correcta |
| `--sin-categoria comment` | 24 de 25 (C falta en una: el modelo marcó el renombrado como `bug` y no el comentario); 0 falsos positivos; la puntuación da 1 de 5, y esa marca es el renombrado: **la del comentario de `REINTENTOS`, 0 de 5** | quitar la categoría quita la marca del comentario (3 de 5 frente a 0 de 5), y a veces también el fallo C, que esa categoría acertaba |
| `rerevision` correcta (antes, 3 ejecuciones) | hallazgos 0, 1 y 0: **0 repetidos** de la primera revisión; E, el bug nuevo, sale en 1 de 3 | con la lista y la orden, no repite lo ya publicado |
| `rerevision --anti sin_previos` (antes, 3 ejecuciones) | hallazgos 4, 4 y 5: **repite B, C y D en 3 de 3**; E sale en 1 de 3 | sin la lista, publica otra vez lo ya publicado; encontrar lo nuevo no mejora |
| `tests` correcta | 7–8 tests por ejecución; **0 escenarios repetidos** en 5 de 5; 31 de 38 sobre lo que cambió | — |
| `tests --anti sin_tests_existentes` | 8–9 tests; **0 repetidos** en 5 de 5; 25 de 41 sobre lo que cambió (en una ejecución, 0 de 8, sin explicar) | **sin diferencia** en los repetidos: ver la nota |
| `tests --anti sin_estandares` | **9–12 tests** por ejecución; 0 repetidos; 36 de 51 sobre lo que cambió | más tests en 5 de 5, sin solapamiento con la correcta (7–8): una diferencia de cantidad, en el sentido de 3.6-S5 |

La segunda revisión (`rerevision`) **no se volvió a medir** tras las correcciones: sus cifras son de antes. Su árbol, el del estado final, ya era el correcto; la puntuación de entonces era la anterior.

Notas:

- **Los criterios categóricos no resuelven el comentario del cambio correcto:** es la marca más estable. El registro de descartados la agrupa por `detected_pattern`, pero el modelo escribe un nombre distinto casi cada vez (`misleading_comment`, `dubious_comment`, `comment_does_not_match_code`, `comentario_justificacion_dudosa`…): agrupar por ese campo sin normalizarlo lo dispersa. `normalize_pattern` solo iguala mayúsculas y separadores.
- **Lo que la puntuación por símbolo no distingue:** en 4 de las 20 revisiones el modelo avisa de que renombrar a `NOTIF_TIMEOUT` rompería a quien lo importara (nadie lo importa). Como cita la línea del cambio correcto, cuenta como marca del cambio correcto: la puntuación no separa dos quejas distintas sobre la misma línea. Sube «marca el cambio correcto» y no cambia los fallos encontrados. Si cada ejecución marcó una sola cosa (los recuentos lo permiten, pero es una lectura y no una medida directa), la correcta marca el comentario de `REINTENTOS` en 3 de 5 (5 marcas menos las 2 del renombrado) y la variante sin `comment`, en 0 de 5 (su única marca es el renombrado). Esa es la cifra que separa las dos variantes.
- **`--parte tests` y los tests existentes:** con ellos y sin ellos salen 0 escenarios repetidos, y ese 0 **no es una señal ni a favor ni en contra de 3.6-S4**. De los 5 escenarios existentes, solo 2 (`calcular_sla(alta, 3)` y `horas_restantes`) son los que el cambio rompe al pasar las horas a minutos, y quien los reescribe ya no repite el escenario; los otros 3 (`calcular_sla(alta, 9)` con `ValueError` y los dos de `debe_escalar`) no cambian con el commit, y proponerlos otra vez sería un duplicado real. **Limitación de la medida:** la clave de un escenario exige que coincidan todos los números del texto de `expected`, así que un duplicado real escrito con un número de más («lanza ValueError: 9 h de 8 h») deja de contarse. El 0 frente a 0 puede ser en parte un artefacto de la clave y no demuestra que no hubiera duplicados reales. Ningún test cubre ese caso, y las propuestas no se guardaron (el módulo solo imprime los recuentos y los repetidos), así que no se revisaron a mano.

**Lo que no coincide con la guía.** **Producto observado (no evaluable):** dos medidas de este módulo no muestran lo que dice la guía. Ninguna cambia la respuesta de examen, que es siempre la de la guía.

- **`--anti conservador` (4.1-K2): marcó menos, no más.** Con «sé conservador» en lugar de los criterios, el modelo encontró los cinco fallos y no marcó nunca el cambio correcto (0 de 5, frente a 3 de 5 marcas del comentario de `REINTENTOS` con los criterios; la puntuación da 5 de 5 contando el renombrado). Hipótesis **sin comprobar**: la variante sustituye todos los criterios, también el de comentarios, que es el que invita a revisar la justificación de `REINTENTOS`; lo que desaparece sería ese criterio, no la prudencia. Para separarlo haría falta una variante con «sé conservador» y el criterio de comentarios. Con 5 ejecuciones es una pista, no una prueba. En el examen, las instrucciones generales de prudencia no mejoran la precisión como los criterios categóricos.
- **Tests existentes en el contexto (3.6-S4): sin señal.** 0 repetidos con ellos y sin ellos, y la medida no permite leer ese 0 ni a favor ni en contra (ver la nota). En el examen, los tests existentes van en el contexto para no proponer escenarios ya cubiertos.

`--anti sin_ejemplos` tampoco da señal (B falta en 1 de 25): no contradice 4.2-S2 y S3, pero no la demuestra.

**Antes de las correcciones C4** (no comparable: árbol contaminado, otra puntuación, otro prompt en todas las variantes —la línea de `bug` citaba el docstring y el ejemplo de `minor` era otro—, `TIMEOUT` duplicado en los datos y la versión anterior de `--sin-categoria comment`; detalle en `docs/hallazgos.md`):

- **Correcta:** A a D en 7 de 8 (A se pierde en 1) y marca el cambio correcto en 3 de 8; después, con F, 2 de 2.
- **`conservador`:** A se pierde en 2 de 8 y nunca marca el cambio correcto. Con tres ejecuciones parecía que «sé conservador» perdía A, y con cinco más no. El árbol contaminado es una explicación posible de esas pérdidas de A (el revisor podía leer `tickets/escalado.py` ya arreglado), junto a los cambios de prompt y de datos; no se aisló. Tras la corrección, A sale en 5 de 5 con todas las variantes.
- **`sin_ejemplos`:** 10 ejecuciones en tres momentos y **con dos puntuaciones distintas**: 3 con cuatro fallos sembrados (A se pierde en 1), 5 con la puntuación por línea (B no sale en 3 de 5) y 2 con la puntuación por símbolo (las cinco en 2 de 2). No se pueden sumar. Para la pérdida de B había dos lecturas, ninguna comprobada: el ejemplo que se quita (una inyección en la shell) se parece a B, o el modelo encontró B y lo citó con la línea desplazada, y la puntuación por línea lo contó como falso positivo.
- **`--sin-categoria comment`** (con la versión anterior de la variante, que cambiaba también `minor` y `bug`): C en 3 de 3, ahora como `bug`, y marca el cambio correcto en 2 de 3. Lo que parecía comportamiento del modelo («reclasifica en vez de quitar») era en parte la variante, que cambiaba más de una cosa.
- **`tests`:** 1 escenario repetido por ejecución con los tests existentes (siempre `calcular_sla(alta, 3)`) y 0 sin ellos; con y sin los estándares, igual. Ese «al revés de lo esperado» era un artefacto: el escenario se comparaba sin lo que esperaba, y el test que el cambio rompe, actualizado a minutos, contaba como repetido.

Avisos sobre las cifras y la ejecución:

- **El tope de coste** es `--max-budget-usd` de cada `claude -p`: el módulo le pasa a cada repetición lo menor entre lo que queda de `--budget` y `--budget` dividido entre las repeticiones, así que una repetición no puede gastarse el tope de las siguientes. La sonda de contexto del principio cuenta en el mismo tope.
- Lo que no depende del modelo se prueba en `tests/test_app3_11_criterios_y_ci.py`, `tests/test_headless.py` y `tests/test_datos_entrega3c.py`. Coste de las ejecuciones con modelo de este módulo: ~1,0 $ antes de las correcciones y 0,63 $ en la medida después (0,37 $ la revisión y 0,26 $ los tests).
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un equipo ejecuta Claude Code en CI para revisar cada *pull request* y publica los hallazgos como comentarios en línea. La categoría «comentario inexacto» marca a menudo comentarios del código que son correctos, y los desarrolladores han empezado a ignorar también los hallazgos de seguridad. ¿Qué debe hacer el equipo?

- A. Añadir al prompt que informe solo de lo que tenga alta confianza y mantener activas todas las categorías mientras tanto.
- B. Apagar esa categoría por ahora y reescribir su criterio, para que marque solo un comentario que contradiga lo que hace el código.
- C. Pedir una puntuación de confianza por hallazgo y publicar solo los que pasen de un umbral, sin tocar el criterio de ninguna categoría.
- D. Mantener todas las categorías y juntar los hallazgos en un único comentario de resumen al final del PR, para que molesten menos.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** Una categoría con muchos falsos positivos hace desconfiar también de las que aciertan (TS 4.1-K3), así que se desactiva temporalmente mientras se mejora su prompt (4.1-S2). El arreglo es un criterio explícito, que marque un comentario solo cuando lo que dice no coincide con lo que hace el código (4.1-K1, S1). Para seguirla después, un campo `detected_pattern` en cada hallazgo permite analizar qué patrones se descartan (4.4-K3, S3).

- **A** es la instrucción general que la guía descarta: «solo alta confianza» no mejora la precisión frente a criterios categóricos (4.1-K2), y la categoría que resta confianza sigue publicando.
- **C** filtra por la confianza en vez de definir qué se informa y qué no (4.1-S1); el criterio vago sigue igual.
- **D** no reduce los falsos positivos (4.1-K3) y renuncia a los comentarios en línea, que es para lo que sirve la salida estructurada en CI (3.6-S2).

**Producto observado (no evaluable):** en este módulo, quitar solo la categoría `comment` hizo desaparecer la marca del comentario de `REINTENTOS` (3 de 5 con la correcta, 0 de 5 sin la categoría, leyendo una marca por ejecución), y en 1 de 5 se perdió también el fallo C, un comentario que sí contradecía al código (Paso 3). No cambia la respuesta de examen: apagar la categoría es la medida temporal, y por eso mismo pierde lo que la categoría acertaba; el arreglo es el criterio.
</details>

**Pregunta 2 (multiple-response).** Un equipo usa `claude -p --output-format json --json-schema` para revisar los commits de una rama y para pedir los tests que faltan. Tras cada commit nuevo, la revisión vuelve a publicar comentarios que ya estaban, y los tests propuestos repiten escenarios ya cubiertos o aportan poco. **Selecciona dos** cambios que sigan la guía. Evalúa cada opción por separado.

- A. Generar los tests sin mostrar al modelo los que ya existen, para que proponga casos sin dejarse llevar por ellos.
- B. Pasar a cada revisión nueva lo que ya se comentó en las anteriores, para que solo publique lo que falta o sigue abierto.
- C. Revisar cada commit con una instancia nueva y sin nada de las revisiones anteriores, para que mire el diff sin sesgos.
- D. Explicar en el `CLAUDE.md` del repositorio cómo se escriben los tests del proyecto y con qué utilidades de prueba cuenta.

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**B y D.** La primera evita los comentarios duplicados (TS 3.6-S3) y la segunda da a Claude Code en CI el contexto del proyecto (3.6-K3) para que los tests generados sean mejores y aporten más (3.6-S5).

- **A** invierte lo que dice la guía: los tests existentes van en el contexto para no proponer escenarios que la suite ya cubre (3.6-S4).
- **B** da al revisor lo que ya se publicó y le pide solo lo nuevo o lo no resuelto: así no repite comentarios tras un commit nuevo (3.6-S3).
- **C** mezcla dos ideas: la instancia independiente es buena para no heredar el razonamiento de quien generó el código (4.6-K2), pero sin los hallazgos previos la revisión vuelve a publicar lo que ya estaba, que es justo el problema (3.6-S3).
- **D** es el uso de `CLAUDE.md` que la guía asigna al contexto de Claude Code en CI: estándares de tests y *fixtures* disponibles (3.6-K3, S5).

**Producto observado (no evaluable):** en este módulo, con los tests existentes en el contexto y sin ellos salieron 0 escenarios repetidos, pero ese 0 no es una señal ni a favor ni en contra de 3.6-S4: solo 2 de los 5 existentes son los que el cambio rompe, y la clave puede dejar de contar un duplicado real (Paso 3). Sin los estándares en el `CLAUDE.md` salieron más tests (9–12 frente a 7–8). No cambia la respuesta de examen: A sigue siendo incorrecta.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 3.6-K1, S1.** Un job de CI lanza Claude Code y se queda colgado, esperando una entrada que nadie va a dar. ¿Qué falta?

- A. Un tope de presupuesto, para que el job termine cuando se agote el gasto.
- B. La opción `-p` (o `--print`), que lo ejecuta en modo no interactivo.
- C. Un `CLAUDE.md` en la raíz, sin el cual no puede arrancar en un pipeline.
- D. Más tiempo de espera en el job, para que le dé tiempo a responderse solo.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**B.** En un pipeline, Claude Code se lanza en modo no interactivo con `-p` (o `--print`), para que no se quede esperando una entrada (TS 3.6-K1, 3.6-S1). A y D no cambian que espere; C no es un requisito para arrancar.
</details>

**C2 · TS 3.6-K2, S2.** La revisión automática debe publicarse como comentarios en línea del PR. ¿Cómo se obtiene una salida que una máquina pueda leer?

- A. Pidiendo en el prompt que responda en JSON y convirtiendo después el texto recibido.
- B. Con una segunda llamada que pase a JSON la prosa que devolvió la primera revisión.
- C. Leyendo el registro del job y sacando los hallazgos con expresiones regulares.
- D. Con `--output-format json` y `--json-schema`, que imponen la estructura de la salida.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**D.** `--output-format json` junto con `--json-schema` imponen una salida estructurada, que en CI da hallazgos que una máquina puede leer y publicar como comentarios en línea (TS 3.6-K2, 3.6-S2). A, B y C dependen de interpretar texto libre.
</details>

**C3 · TS 3.6-K3, S4, S5.** Los tests que genera Claude Code en CI repiten escenarios ya cubiertos e ignoran las *fixtures* del proyecto. ¿Qué se cambia?

- A. Poner los tests existentes en el contexto y documentar estándares y *fixtures* en `CLAUDE.md`.
- B. Pedir el doble de tests, para que entre todos haya suficientes que no estén repetidos.
- C. Borrar los tests antiguos antes de generar, para que no quede nada que duplicar.
- D. Lanzar la generación dos veces y quedarse con los tests que aparezcan en las dos.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**A.** El contexto del proyecto le llega a Claude Code en CI por `CLAUDE.md` (TS 3.6-K3): documentar ahí los estándares, qué hace valioso un test y qué *fixtures* hay mejora los tests generados (TS 3.6-S5). Y los tests existentes van en el contexto, para no proponer escenarios que la suite ya cubre (TS 3.6-S4). B y D no dan esa información; C destruye la cobertura.
</details>

**C4 · TS 4.1-K1, K2, S1.** Un revisor automático marca demasiados falsos positivos. ¿Qué instrucción mejora más su precisión?

- A. «Sé conservador e informa solo de aquello de lo que estés muy seguro.»
- B. «Revisa el código con mucho cuidado y no te dejes ningún problema.»
- C. Criterios explícitos: qué se informa (bugs, seguridad) y qué no (estilo menor).
- D. «Da una confianza a cada hallazgo y descarta los que no lleguen a 0,8.»

<details>
<summary>Comprobación C4 · Respuesta</summary>

**C.** Un criterio explícito precisa más que una instrucción vaga (TS 4.1-K1), y las instrucciones generales del tipo «sé conservador» no mejoran la precisión como los criterios categóricos (TS 4.1-K2). Los criterios dicen qué se informa y qué se deja, en vez de filtrar por confianza (TS 4.1-S1), que es lo que hace D. A y B son las instrucciones vagas.
</details>

**C5 · TS 4.1-K3, S2.** Hace dos meses, un equipo apagó la categoría de su revisor automático que daba muchos falsos positivos, y desde entonces nadie la ha vuelto a tocar. ¿Qué falta?

- A. Apagar también las demás categorías con algún falso positivo, para no arriesgar más la confianza.
- B. Subir el umbral de confianza de todas las categorías, para compensar la que se apagó.
- C. Mejorar el prompt de esa categoría y reactivarla cuando deje de dar tantos falsos positivos.
- D. Pedir a los desarrolladores que revisen a mano los PR de esos meses, por si se escapó algo.

<details>
<summary>Comprobación C5 · Respuesta</summary>

**C.** Apagar una categoría con muchos falsos positivos es una medida temporal: recupera la confianza mientras se mejora su prompt (TS 4.1-S2). Y la confianza importa porque los falsos positivos de una categoría hacen desconfiar también de las que aciertan (TS 4.1-K3). A pierde los aciertos de categorías útiles; B filtra por confianza en vez de corregir el criterio; D no arregla la categoría.
</details>

**C6 · TS 4.1-S3.** Un revisor clasifica el mismo tipo de fallo como grave en un PR y como menor en otro. ¿Qué cambio da una clasificación consistente?

- A. Pedirle que piense dos veces la severidad antes de asignarla a cada hallazgo.
- B. Definir cada nivel de severidad con un criterio explícito y un ejemplo de código.
- C. Dejar una sola severidad para todos los hallazgos y que una persona decida después.
- D. Asignar la severidad según la confianza que el modelo declare en cada hallazgo.

<details>
<summary>Comprobación C6 · Respuesta</summary>

**B.** La severidad sale consistente cuando cada nivel tiene un criterio explícito y ejemplos de código concretos (TS 4.1-S3). A es una instrucción vaga; C renuncia a clasificar; D confunde la confianza con la severidad.
</details>

**C7 · TS 4.2-S2, S3.** ¿Qué aportan unos ejemplos *few-shot* al prompt de una revisión de código?

- A. Fijan el formato de cada hallazgo y enseñan a separar un patrón aceptable de un problema real.
- B. Sustituyen a los criterios de revisión, que dejan de hacer falta cuando ya hay ejemplos.
- C. Garantizan que el revisor no dará ningún falso positivo en las categorías que cubren.
- D. Limitan la revisión a los casos idénticos a los ejemplos, sin generalizar a otros nuevos.

<details>
<summary>Comprobación C7 · Respuesta</summary>

**A.** Los *few-shot* fijan el formato de cada hallazgo (ubicación, problema, severidad y arreglo propuesto) (TS 4.2-S2) y enseñan a distinguir un patrón aceptable de un problema real, lo que reduce los falsos positivos sin impedir generalizar (TS 4.2-S3). B y C prometen de más; D dice lo contrario de S3.
</details>

**C8 · TS 4.4-K3, S3.** Se quiere saber qué tipo de hallazgos descartan los desarrolladores una y otra vez. ¿Qué lo permite?

- A. Preguntar al modelo, al acabar cada revisión, qué hallazgos cree que se van a descartar.
- B. Un campo `detected_pattern` en cada hallazgo, con la construcción de código que lo provocó.
- C. Guardar solo cuántos hallazgos se descartan cada semana y mirar si la cifra sube o baja.
- D. Pedir a cada desarrollador un informe mensual con los comentarios que no le han servido.

<details>
<summary>Comprobación C8 · Respuesta</summary>

**B.** Un campo `detected_pattern` en cada hallazgo registra qué construcción del código lo provocó y permite analizar de forma sistemática los patrones que los desarrolladores descartan (TS 4.4-K3, 4.4-S3). C cuenta sin decir qué; A y D no dejan un dato que se pueda agrupar.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 12 · Revisión independiente

> **Qué vas a hacer:** Hacer que una sesión de `claude -p` escriba un cambio y revisarlo después de varias maneras: con una instancia nueva en pasadas por archivo y de integración, reanudando la sesión que lo escribió (con y sin la orden explícita de revisar su propio cambio) y con una instancia nueva en una sola pasada larga, con la confianza de cada hallazgo.
>
> **Necesitas antes:** El [módulo 11](#11--criterios-y-revisión-en-ci), cuyo cambio de prueba, schema de hallazgos, letras de los fallos y puntuación reutiliza, y el [10](#10--confianza-y-revisión-humana), cuya calibración aplica a la confianza de cada hallazgo.
>
> **Modo:** Ejecución ligera (`--parte plan` no usa modelo; cada revisión con modelo cuesta entre 0,04 $, en una sola pasada, y unos 0,13 $, en la autorrevisión, más la sesión generadora una vez).

### Antes de empezar

Los términos comunes (autorrevisión, instancia independiente, pasada por archivo y de integración, sesión, reanudar, bifurcar, `claude -p`) están en el [glosario](../docs/glosario.md). Como el módulo 11, lanza `claude -p` con la orden de [`harness/headless.py`](../harness/headless.py): aislada, de solo lectura en la revisión y con tope de coste.

- **El sistema:** una sesión generadora, con `Write`, parte de un repositorio con un solo commit, el estado base, y recibe el mensaje y el contenido exacto de cada archivo del primer commit del módulo 11, con la orden de escribirlos (y ningún otro archivo) y explicar por qué tomó cada decisión. El cambio no queda en el historial de ese repositorio: lo que se revisa es el diff que la sesión deja en el árbol de trabajo, archivos nuevos incluidos. Después, las pasadas: una por archivo (sin tools, con solo el diff de ese archivo), una de integración (con el diff completo, los hallazgos locales y `Read`, `Grep` y `Glob`) y una de verificación que da la confianza de cada hallazgo fusionado.
- **Términos propios:**
  - **Instancia nueva:** la instancia independiente de este módulo, una ejecución de `claude -p` sin sesión previa: solo ve el diff y lo que lea del repositorio.
  - **Autorrevisión aquí:** las mismas pasadas, cada una como `--resume` de la sesión que escribió el cambio. Cada pasada la **bifurca** (`--fork-session`) para que las repeticiones no se contaminen entre sí.
  - **Pasadas encadenadas:** la pasada por archivo va sin tools y con solo el diff de ese archivo; la de integración recibe el diff completo y los hallazgos locales, puede leer el repositorio y no debe repetir lo que ya salió.
  - **Una pasada:** la revisión de todo el diff de una vez, con lectura del repositorio y los mismos criterios, sin pasadas por archivo ni de integración.
  - **Fusión:** dos hallazgos de pasadas distintas se cuentan como uno si caen en el mismo sitio y describen el mismo problema (mismo `detected_pattern` o palabras en común). El mismo problema dicho con otras palabras cuenta dos veces.
  - **Verificación:** una pasada que da, con el diff delante, una confianza de 0 a 1 a cada hallazgo, aparte de la que el hallazgo trae al nacer.
  - **Enrutar:** decidir si un hallazgo se publica o va a una persona. El criterio y su umbral, que es una elección propia, están en el Paso 3.
  - **Coste acumulado:** el `total_cost_usd` de una sesión reanudada incluye el de la sesión de origen; el coste de cada revisión es la diferencia, y el tope de la rama lo lleva `headless.Ledger`.

### El ejercicio

`--parte plan` muestra las pasadas, las tools de cada una y la orden de la autorrevisión (o la de la pasada única, con `--anti una_pasada`), sin ejecutar nada. `--parte revision` genera el cambio y lo revisa. Las ramas usan los mismos criterios y ejemplos; cada una cambia una sola cosa respecto a la correcta:

- **Correcta:** las pasadas son instancias nuevas, sin sesión.
- **`--anti autorrevision`:** cada pasada es un `--resume --fork-session` de la sesión generadora.
- **`--anti autorrevision_explicita`:** igual que la anterior, con una frase delante de cada prompt: «Revisa críticamente tu propio cambio: busca los fallos que hayas podido pasar por alto al escribirlo».
- **`--anti una_pasada`:** una instancia nueva, como la correcta, pero en una única pasada con lectura sobre todo el diff, seguida de la misma verificación.

El cambio lleva los fallos A, B, C, D y F del módulo 11 (E es del segundo commit y no entra aquí). Dos son entre archivos: `D`, `calcular_sla` devuelve minutos y sus llamadores leen horas, y `F`, `avance_plazo` devuelve una fracción de 0 a 1 y `texto_progreso` la imprime como porcentaje. Ninguno de los dos archivos lo delata del todo por sí solo.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) La sesión que escribió un cambio lo revisa en esa misma sesión. ¿Qué conserva que no tiene una instancia nueva? ¿Cómo afecta eso a su revisión?
2. (módulo) Con estos cinco fallos sembrados, ¿esperas que la correcta encuentre más que `autorrevision`? ¿Por qué podría no notarse aquí?
3. (módulo) Con `autorrevision_explicita` se añade la frase «revisa críticamente tu propio cambio». ¿Qué cambia con ella en lo que la sesión sabe?
4. (guía) La revisión se reparte en una pasada por archivo y otra de integración. ¿Qué problema de revisar un cambio grande en una sola pasada evita ese reparto? ¿Para qué clase de fallo existe la pasada de integración?
5. (módulo) El cambio de este módulo es pequeño: 93 líneas en cuatro archivos. Con `una_pasada`, ¿esperas que la revisión pierda los fallos entre archivos D y F?
6. (guía) La pasada de verificación da una confianza a cada hallazgo. ¿Para qué sirve? ¿Qué hace falta para poder fiarse de ella?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/12_revision_independiente.py                                              # el plan de pasadas y la orden, sin modelo
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --repeat 2                  # instancia nueva
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --anti autorrevision --repeat 2
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --anti autorrevision_explicita --repeat 2
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --anti una_pasada --repeat 2
```

**Si ejecutas:** el reparto en pasadas, los prompts, la fusión, el enrutado por confianza, la calibración y el coste de la sesión reanudada se prueban sin modelo. Cada ejecución completa (la sesión generadora, una vez, y cada revisión: cuatro pasadas por archivo, una de integración y una de verificación) cuesta entre 0,15 y 0,25 $ con `--repeat 1`. **El tope por defecto del repositorio (1,00 $) es el de toda la ejecución:** la sesión generadora recibe como mucho 0,30 $ y cada pasada, lo menor entre lo que queda y 0,20 $. No se reparte por repeticiones, así que con `--repeat 5` en la autorrevisión se acerca al tope, y una pasada con poco margen puede quedar sin presupuesto y sin confianza; el módulo lo dice.

### Qué observar

Por repetición: qué fallos sembrados encontró cada pasada, cuáles faltan, falsos positivos, si marcó el cambio correcto, cuántos hallazgos se publican y cuántos van a una persona, la calibración de la verificación y el coste acumulado. Antes, si el diff que escribió la sesión generadora coincide con el cambio que se le dio.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** El razonamiento con el que generó el código. Con él, es menos probable que ponga en duda sus propias decisiones: la sesión que generó el código revisa sus cambios peor que una instancia independiente (TS 4.6-K1, 3.6-K4).
- **P2** No se notó: en la batería anterior a las últimas correcciones, las tres ramas encontraron los cinco fallos, así que la medida está en su techo. La guía dice que una instancia independiente detecta mejor los problemas sutiles (TS 4.6-K2, 4.6-S1); inferencia propia: con fallos que todas las ramas encuentran, no queda margen para verlo. En el examen manda la guía.
- **P3** Nada: tiene el mismo contexto que antes. La frase no cambió lo que encontró.
- **P4** La atención diluida: partir así una revisión grande la evita (TS 4.6-K3, 4.6-S2, 1.6-K2, 1.6-S2). La de integración existe para el flujo de datos entre archivos (D y F); la pasada por archivo ve lo local (A, B y C). Aquí, D salió por archivo en 3 de 5 y F en 1 de 5; la integración completó el resto.
- **P5** No los perdió: 24 de 25 (el que faltó una vez fue C, no D ni F), con la mitad de coste. Con un diff de este tamaño no hay diferencia; la guía habla de revisiones grandes.
- **P6** Para enrutar la revisión de forma calibrada (TS 4.6-S3). Aquí, los hallazgos con confianza de la verificación desde 0,8 se publican, y el resto y los que no la tienen van a una persona; cuenta la de la verificación, no la que el hallazgo trae al nacer. Para fiarse hay que comprobar esa confianza contra hallazgos etiquetados, como la confianza por campo del módulo 10 (inferencia propia: TS 4.6-S3 no lo dice): aquí el hueco de calibración fue de 0,129 a 0,215.

Sonnet 5.5 (rol `reviewer`), `claude -p` aislado. Hay tres mediciones, cada una con su versión del código; **la de referencia es la última**, después de las correcciones C4 (2026-11-07). En ella la sesión generadora escribió exactamente el cambio dado (93 líneas, cuatro archivos) en las dos ramas.

**Después de las correcciones C4** (5 ejecuciones por rama):

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta: instancia nueva | las cinco en 5 de 5, 0 falsos positivos; A, B y C por archivo en 5 de 5; **D por archivo en 3 de 5 y F en 1 de 5**, y la integración completa el resto (D 2 de 5, F 4 de 5); marca el cambio correcto 1 vez. ~0,090 $ por revisión | con la pasada por archivo sin tools, los fallos entre archivos salen sobre todo por integración |
| `--anti una_pasada` | 24 de 25 (C falta en una), 0 falsos positivos; marca el cambio correcto 6 veces en 5 ejecuciones. ~0,042 $ por revisión | **sin diferencia** en lo encontrado: una pasada larga no pierde D ni F con este diff y cuesta unas 2 veces menos |

Calibración de la verificación: con `una_pasada`, los 5 hallazgos de la banda 0,00–0,50 son marcas del cambio correcto (la verificación decía 23 %) y las demás bandas aciertan el 94–100 %; hueco 0,129. Con la instancia nueva, hueco 0,215, por quedarse corta (banda 0,00–0,50 con todos los hallazgos reales). Con más marcas del cambio correcto, la confianza sí separa algo.

**Batería de la autorrevisión** (antes de las correcciones C4, 2026-11-06; 5 ejecuciones por rama, la misma versión del código y de la puntuación en las tres):

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta: instancia nueva | las cinco en 5 de 5, 0 falsos positivos; por archivo A, B y C en 5 de 5, D en 1 de 5 y F en 0 de 5; por integración D 4 de 5 y F 5 de 5. ~0,091 $ por revisión. Su generador añadió un archivo de tests (125 líneas en lugar de 93) | misma pauta de dónde salen D y F, sobre un diff distinto del de las otras dos ramas |
| `--anti autorrevision` | las cinco en 5 de 5, todas por la pasada por archivo; 0 falsos positivos. ~0,127 $ por revisión | **sin diferencia** con la instancia nueva: la sesión bifurcada recuerda lo que escribió y sus pasadas «locales» no son locales |
| `--anti autorrevision_explicita` | las cinco en 5 de 5, todas por archivo; 0 falsos positivos; 1 marca del cambio correcto. ~0,123 $ por revisión | **sin diferencia**: la frase no cambió lo encontrado |

Que la instancia nueva lo encontrara todo **no es un control positivo**: no prueba que la medida pueda registrar una pérdida. Lo que sí lo prueba es la pasada por archivo de la instancia nueva, que pierde F en 5 de 5 y la medida lo registra. Con el techo al 100 % en las tres ramas, falta señal, no muestra: para ver un efecto haría falta un fallo más sutil. Las 25 oportunidades por rama son 5 ejecuciones sobre el mismo diff y no son independientes, así que no dan una cota de la tasa de pérdida.

**Antes, tanda C** (2 a 3 ejecuciones; la sesión generadora conservaba el cambio en su historial, el diff no veía los archivos nuevos y la fusión podía perder un hallazgo distinto):

- La generadora escribió exactamente el cambio dado en 3 de 5 sesiones; en otra añadió archivos de tests.
- Instancia nueva (3 ejecuciones): cada fallo en alguna pasada, 0 falsos positivos; D y F por integración en 2 de 3 y por archivo en 1 de 3. ~0,10 $ por revisión.
- Autorrevisión (2 ejecuciones): A, B, C, D y F por archivo en las 2, ~0,19 $ por revisión. `autorrevision_explicita` no se midió entonces (se midió en la batería).
- Calibración de la verificación (17 hallazgos, todos reales): 0,61, 0,89 y 0,95 de media por banda, hueco 0,20 por quedarse corta. El registro de entonces la da sobre 2 ejecuciones y la tabla de la instancia nueva tiene 3; no dice por qué, y no se ha podido reconstruir.
- En la segunda autorrevisión, la pasada de verificación se quedó sin presupuesto (tope de 0,40 $) y sus hallazgos quedaron sin confianza.

Notas:

- **Lo que no coincide con la guía.** **Producto observado (no evaluable):** ni la autorrevisión encontró menos que la instancia nueva ni la pasada única encontró menos que el reparto. La guía dice que la sesión que generó el código lo revisa peor que una instancia independiente (TS 4.6-K1, K2; 3.6-K4) y que una revisión de varios archivos se parte en pasadas para no diluir la atención (4.6-K3, S2); con este cambio no se vio ninguna de las dos cosas. No cambia la respuesta de examen, que es la de la guía; las dos lecciones quedan como conceptuales.
- **Por qué puede no verse, sin comprobar:** el «razonamiento de generación» de esta sesión es el de copiar un cambio que se le dio, no el de diseñarlo; los fallos sembrados son claros para cualquiera que mire el código; y un diff de 93 líneas cabe entero en la atención de una sola pasada.
- **El reparto de dónde sale cada fallo es en parte del diseño:** la pasada por archivo de la instancia nueva no tiene tools ni ve a los llamadores, así que D y F solo pueden completarse en la de integración. Muestra para qué sirve la pasada de integración, pero no que el reparto encuentre más que una pasada única.
- **La sesión bifurcada no es una pasada local:** como la sesión generadora escribió los cuatro archivos, ve a los llamadores en su historial. Una instancia nueva sin tools es la única pasada local de verdad.
- **El coste de la sesión reanudada es acumulado:** cada revisión bifurcada informa del coste de la generadora más el suyo. El módulo cuenta cada revisión por la diferencia y suma la generadora una vez.
- **La orden «no crees ningún otro archivo»** se añadió tras la medida en que la generadora añadió un archivo de tests. En la última medida copió el cambio exacto, pero no se probó sin la orden: no se sabe si es ella la que lo evita.
- Lo que no depende del modelo se prueba en `tests/test_app3_12_revision_independiente.py` y `tests/test_headless.py`. Coste de las ejecuciones con modelo de este módulo: ~1,3 $ en la tanda C (incluidas las de prueba), 1,90 $ en la batería de la autorrevisión y 0,76 $ en la medida tras las correcciones.

**Para pensar (sin evaluación):** ¿qué pasaría si la pasada de integración y una pasada por archivo se contradijeran? El módulo no lo provoca, así que no cuenta como predicción.
</details>

### Pregunta tipo examen

Un equipo hace que Claude Code genere un cambio de varios archivos y, en la misma sesión, le pide que lo revise. La revisión encuentra poco, y después una persona detecta un fallo en cómo un archivo usa el valor que devuelve otro. ¿Qué debe cambiar el equipo?

- A. Seguir en la misma sesión, con una pasada por archivo y otra de integración, y la orden de cuestionar cada decisión que tomó.
- B. Activar el razonamiento extendido en la sesión que generó el código y pedirle una única revisión más a fondo de todo el cambio.
- C. Revisar con una instancia nueva todos los archivos a la vez en una sola pasada larga, para que tenga el cambio completo delante.
- D. Revisar con una instancia nueva, sin el contexto de la generación, en una pasada por archivo y otra de integración entre archivos.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** La sesión que generó el código conserva su razonamiento y cuestiona menos sus decisiones (TS 4.6-K1, 3.6-K4); una instancia independiente encuentra mejor los problemas sutiles (4.6-K2, S1). Una revisión de varios archivos se encadena en pasadas por archivo y una de integración para el flujo de datos entre archivos, que evita diluir la atención y los hallazgos contradictorios (4.6-K3, S2; 1.6-K2, S2).

- **A** reparte bien las pasadas, pero deja la revisión en la misma sesión: la guía pone las instrucciones de autorrevisión por debajo de una instancia independiente (4.6-K2).
- **B** es el razonamiento extendido de la misma sesión, que la guía tampoco da por mejor que una instancia independiente (4.6-K2), y además en una sola pasada (4.6-K3).
- **C** acierta con la instancia nueva, pero una sola pasada sobre muchos archivos diluye la atención; el fallo entre archivos pide su propia pasada de integración (4.6-K3, S2).

**Producto observado (no evaluable):** en este módulo, ni la autorrevisión encontró menos que la instancia nueva ni la pasada única (la opción C, medida como `--anti una_pasada`) encontró menos que el reparto en pasadas, con un diff de 93 líneas (Paso 3). No cambia la respuesta de examen.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 4.6-K2, S1.** Se quiere detectar problemas sutiles en código que acaba de generar una sesión de Claude. ¿Qué es más eficaz?

- A. Pedir a esa misma sesión que relea su código con más razonamiento extendido.
- B. Pedir a esa misma sesión que se revise «de forma crítica» antes de entregar.
- C. Una segunda instancia que revise el código sin el contexto de quien lo generó.
- D. Lanzar la misma generación dos veces y quedarse con la segunda versión.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**C.** Una instancia independiente, sin el razonamiento previo, detecta mejor los problemas sutiles que pedirle a la misma sesión que se revise o darle más razonamiento extendido (TS 4.6-K2); en la práctica, una segunda instancia revisa sin el contexto del generador (TS 4.6-S1). A y B son las dos alternativas que la guía descarta; D no revisa nada.
</details>

**C2 · TS 4.6-K3, S2, 1.6-K2, S2.** Hay que revisar un cambio grande que toca muchos archivos. ¿Cómo se organiza la revisión?

- A. En una sola pasada sobre todo el cambio, para que el revisor lo vea completo de una vez.
- B. Solo con pasadas por archivo, sin ninguna que mire cómo se relacionan entre ellos.
- C. Empezando por los archivos más cortos y parando en cuanto aparezca el primer problema.
- D. Una pasada por archivo para lo local y otra de integración para el flujo entre archivos.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**D.** Una revisión grande se parte en pasadas: una por archivo para lo local y otra aparte de integración para el flujo de datos entre archivos, lo que evita diluir la atención (TS 4.6-K3, 4.6-S2). Es el ejemplo de cadena fija de prompts para una tarea predecible de varios aspectos (TS 1.6-K2, 1.6-S2). A diluye la atención; B pierde los fallos entre archivos; C deja la revisión a medias.
</details>

**C3 · TS 4.6-S3.** ¿Para qué sirve una pasada de verificación en la que el modelo da su confianza junto a cada hallazgo?

- A. Para enrutar la revisión de forma calibrada: qué se publica y qué pasa por una persona.
- B. Para descartar sin más los hallazgos de las categorías con más falsos positivos.
- C. Para sustituir a la revisión independiente cuando no hay otra instancia disponible.
- D. Para ordenar los hallazgos por archivo antes de publicarlos como comentarios del PR.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**A.** Una pasada de verificación, en la que el modelo informa de su confianza junto a cada hallazgo, permite enrutar la revisión de forma calibrada (TS 4.6-S3). B filtra por categoría, no por confianza; C confunde verificar con revisar de forma independiente; D es solo presentación.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).
