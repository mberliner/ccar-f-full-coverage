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
- **El prompt del coordinador:** fija objetivos y criterios de calidad, no pasos: cubrir todo el alcance de la pregunta, citar cada afirmación con su ID y su fecha, señalar los artículos obsoletos e invocar solo a los subagentes que aporten. También le recuerda que los subagentes no ven su conversación, y le da el formato con el que debe pasar los hallazgos al sintetizador.
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
| `synthesizer` | ninguna | redactar con lo que venga en su prompt, un apartado por subtema y con cada cita; si no recibe hallazgos, decirlo |

### El ejercicio

Hay dos preguntas: la amplia por defecto («¿Qué problemas de red están teniendo los empleados y qué dice la base de conocimiento de cada uno?») y `--pregunta simple` («¿Qué dice el artículo KB-109?»). Lo que cambia en el código de cada variante `--anti`:

- **`pipeline_completo`:** añade al prompt del coordinador la orden de invocar siempre a los tres subagentes, en orden fijo, sea cual sea la pregunta.
- **`estrecha`:** añade que en esta empresa «problemas de red» quiere decir casi siempre la VPN, y que cada analista reciba una sola consulta concreta.
- **`sin_hallazgos`:** sustituye la regla de pasar los hallazgos por la afirmación, falsa, de que el sintetizador ya ve lo que han encontrado los analistas, y pide pasarle solo la pregunta.
- **`procedimental`:** sustituye los objetivos por una receta de cuatro pasos: los dos analistas con la consulta «VPN», después el sintetizador, y devolver su respuesta.

La salida imprime la respuesta y varias líneas `[medida]`: los subagentes invocados; las llamadas por agente y los intentos del coordinador que denegó la barrera; si hubo sintetizador, cuántos de los IDs que encontraron los analistas llegaron a su prompt, y cuáles faltan; y qué subtemas aparecen en la respuesta. Esta última línea busca las palabras en el texto final: no comprueba si el subtema se investigó.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. ¿Por dónde tiene que pasar algo que encuentra un analista para llegar al sintetizador? ¿Qué parte de ese camino fija el código y qué parte depende del prompt del coordinador?
2. Con `--pregunta simple`, ¿qué subagentes hacen falta y cuáles sobran? ¿Qué cambiaría con esa misma pregunta en `pipeline_completo`?
3. Con `estrecha`, ¿qué parte del tema puede quedarse fuera, y por qué no la puede recuperar ningún subagente? Para saber si se investigó, ¿te fías más de la línea de subtemas o de las consultas delegadas?
4. Con `sin_hallazgos`, ¿qué le llega al sintetizador? ¿Quién más podría acabar redactando la respuesta, y en qué líneas de la salida lo verías?

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
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un sistema de investigación tiene un coordinador y tres subagentes: búsqueda web, análisis de documentos y síntesis. Los informes finales omiten con frecuencia datos que los subagentes de búsqueda sí encontraron. Los registros muestran que el coordinador invoca al sintetizador con la pregunta original. ¿Cuál es la causa más probable?

- A. El sintetizador necesita un modelo con una ventana de contexto mayor.
- B. Los subagentes no heredan el contexto del coordinador: el sintetizador nunca recibió los hallazgos, que había que pasarle en el prompt.
- C. Los subagentes de búsqueda deberían escribir sus resultados en una memoria compartida.
- D. Falta `"Task"` en las `allowedTools` del sintetizador.

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

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
- **Respuesta del coordinador:** cada mensaje que emite el modelo. Las llamadas `Agent` se agrupan por la respuesta en la que llegaron (`r1`, `r2`…): varias en la misma respuesta se lanzan a la vez.
- **Brecha:** un subtema esperado que la síntesis no menciona.
- **Ronda de delegación:** cada respuesta del coordinador que contiene al menos una llamada `Agent`.
- **Código *legacy*:** código heredado, sin tests y con dependencias que no se ven sin leerlo.

### El ejercicio

El módulo tiene cuatro partes independientes que se eligen con `--parte`, cada una con su propio sistema:

- **`paralelo`:** un coordinador con los dos analistas recibe tres peticiones independientes: tickets de licencias, tickets de hardware y artículos de la KB sobre acceso. Hay dos modos, y entre ellos solo cambia la última frase del prompt del coordinador. En el modo paralelo, si las subtareas son independientes, lanza todos los subagentes en la misma respuesta; en el secuencial, lanza uno, espera su resultado y luego el siguiente. Sin `--anti` se ejecutan los dos modos seguidos y se mide el tiempo de reloj de cada uno; con `--anti secuencial`, solo el secuencial.
- **`refinamiento`:** una conversación con `ClaudeSDKClient`. El coordinador recibe «¿Qué problemas de red tienen los empleados?» y la instrucción de hacer una primera pasada rápida, con una sola consulta por analista. Después, un comprobador escrito en código (sin modelo) busca en la síntesis las palabras de cada subtema esperado (VPN, wifi e impresora, `REQUIRED_SUBTOPICS`). Si falta alguno, envía al coordinador un mensaje con solo esos subtemas y le pide volver a delegar. Hace como mucho 2 rondas de refinamiento.
- **`descomposicion`:** dos estrategias. Primero, una **cadena fija** (*prompt chaining*) de tres pasos sobre los tickets de gastos con importe: extraer, aplicar la política (hasta 500 EUR aprueba soporte y, por encima, Finanzas) y redactar el informe. Cada paso es una llamada aparte, sin tools y con una sola respuesta, que recibe solo la salida del anterior. Después, una **descomposición adaptativa**: un coordinador con los dos analistas investiga una pregunta abierta sobre los tickets de septiembre, sin plan fijo; se le pide generar subtareas a partir de lo que encuentre y explicar de qué hallazgo salió cada una.
- **`legacy`:** sin coordinador. Un solo agente, con las tools integradas de lectura `Glob`, `Grep` y `Read`, trabaja en el directorio de un paquete Python heredado (`datos/sinteticos/legacy_inventario/`) y recibe «Añade tests completos a este paquete legacy. Empieza por el plan». Su prompt le pide mapear la estructura, leer lo de mayor impacto, entregar un plan priorizado y ajustarlo si descubre una dependencia. No puede escribir archivos.

`--anti` tiene una sola variante, `secuencial`, que solo afecta a `--parte paralelo`.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. En cada modo de `paralelo`, ¿cómo se repartirán las tres llamadas `Agent` entre las respuestas del coordinador? ¿Cuál debería tardar menos y de qué depende que la aceleración se acerque o no a ×3? ¿Esperas la misma cifra en dos ejecuciones?
2. En `refinamiento`, el comprobador solo busca palabras en la síntesis. ¿Qué clase de síntesis le haría dar por cubierto un subtema que no se investigó? ¿Y qué esperas que pase si la primera síntesis ya nombra los tres?
3. En `descomposicion`, ¿puede variar el número de pasos de la cadena fija según lo que encuentre? En la adaptativa, ¿de dónde deberían salir las subtareas de la segunda ronda?
4. En `legacy`, ¿qué hará el agente antes de proponer ningún test, y para qué le sirve cada una de sus tres tools? ¿Basta con `Glob` y `Grep` para conocer todas las dependencias entre módulos, o hace falta leerlos?

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

En la primera ejecución con modelo:

- **paralelo:** 3 llamadas `Agent` en `r1` frente a una por respuesta (`r1`, `r3`, `r5`); 16,8 s frente a 27,9 s (×1,66). El recorder, que agrupa por `message_id`, las puso las tres en la misma respuesta.
- **refinamiento:** el comprobador busca VPN, wifi e impresora en la síntesis y devuelve al coordinador solo las brechas, como mucho 2 rondas. En la primera ejecución no hubo brechas en la ronda 1 y el bucle no llegó a actuar. Repítelo, o cambia `REQUIRED_SUBTOPICS`, para verlo re-delegar.
- **descomposicion:** la cadena fija procesa los reembolsos en tres pasos, y cada uno recibe solo la salida del anterior. La investigación abierta delegó en 2 rondas, y las subtareas de la segunda (tickets del 19 al 22 de septiembre, bloqueos de cuenta) salieron de los hallazgos de la primera.
- **Barrera del coordinador:** `paralelo`, `refinamiento` y la parte adaptativa de `descomposicion` usan el hook compartido del módulo 01 (la cadena fija y `legacy` no tienen coordinador). Con la sonda del módulo 01, el coordinador de este módulo también usó `search_tickets` sin barrera y recibió el rechazo con ella. Al repetir `paralelo` con la barrera (2026-10-27): 0 intentos del coordinador, 3 `Agent` en `r1` frente a uno por respuesta y ×1,37 (23,7 s frente a 32,4 s; la aceleración varía entre ejecuciones).
- **legacy:** primero `Glob` y `Grep` y después `Read` de los siete archivos. El plan menciona la dependencia escondida: `depreciacion.valor_actual` importa `almacen` dentro de la función y lee la caché que llena `asignaciones`.
</details>

### Pregunta tipo examen

Un coordinador debe investigar tres temas independientes con tres subagentes. Hoy los invoca uno por turno y cada investigación tarda el triple de lo necesario. ¿Qué cambio es el más adecuado?

- A. Emitir las tres llamadas a Task en una sola respuesta del coordinador.
- B. Fusionar los tres subagentes en uno con todas las tools.
- C. Bajar `max_turns` para que el coordinador termine antes.
- D. Pedir a cada subagente que lance al siguiente cuando termine.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** Los subagentes en paralelo se lanzan con varias llamadas a Task en la misma respuesta (TS 1.3-S3). B pierde la especialización y el reparto del alcance; C es usar un tope como mecanismo de control (el anti-patrón de TS 1.1-S3); D rompe el hub-and-spoke, en el que toda la comunicación pasa por el coordinador.
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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

Con tus palabras; no hay un número que acertar:

1. Con la configuración correcta, ¿qué parte del reparto entre sintetizador y coordinador está garantizada sea cual sea el modelo, y qué parte depende de que el sintetizador llame a `verify_fact` y de lo que haga el coordinador con lo que le vuelve?
2. Con `--anti todas`, ¿qué podría hacer el sintetizador con las tools que no son suyas? ¿Qué haría más probable o menos probable que las use: que su prompt traiga todo lo que necesita o que le falte algo?
3. Con `--anti fetch_url`, ¿qué rechazaba el código con `load_document` que ahora ya no rechaza? ¿De quién depende entonces que no entren en los hallazgos páginas que no son documentos, y esperas el mismo resultado en todas las repeticiones?
4. Con `--anti sin_verify`, ¿quién puede verificar las afirmaciones y con qué? ¿Esperas más delegaciones o menos que en la correcta? Razónalo antes de leer la línea `[esperado]`.

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
</details>

### Pregunta tipo examen

Un agente de síntesis recibe todas las tools del sistema y, aunque su cometido es redactar, empieza a hacer búsquedas que duplican el trabajo del agente investigador. ¿Qué cambio es el más adecuado?

- A. Reforzar su *system prompt* con «no hagas búsquedas, solo redacta» y mantener todas las tools, por si alguna vez las necesita.
- B. Fusionar al investigador y al sintetizador en un único agente con todas las tools, para que nadie duplique el trabajo del otro.
- C. Dejarle solo las tools de su rol más una de verificación acotada para lo simple, y enviar las comprobaciones complejas al coordinador.
- D. Quitarle todas las tools y hacer que cada comprobación, simple o compleja, pase por el coordinador para centralizar el control.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Un agente con tools fuera de su especialización tiende a malusarlas (TS 2.3-K2); la solución es el acceso acotado, con las tools de su rol (TS 2.3-S1) y una tool cross-role muy limitada para las necesidades de alta frecuencia, con los casos complejos por el coordinador (TS 2.3-K3, TS 2.3-S3). A pide por prosa lo que la configuración debería garantizar, y el agente conserva las tools que malusa; B deja un agente con todas las tools, lo contrario del acceso acotado (TS 2.3-K3); D elimina la tool acotada, y cada verificación simple pasa a depender del coordinador (el anti-patrón de TS 2.3-S3).
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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

Además, la petición incluye una sexta fuente, `SRC-REDES`, **transitoria**: falla con *timeout* la primera vez que se consulta en una ejecución y responde bien a la siguiente (el estado va por ejecución y solo la ve este módulo). Sirve para observar la recuperación local (TS 5.3-S3).

Cada ejecución imprime una línea `[esperado]` con la hipótesis escrita en el código. Es una predicción, no un resultado.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. En la configuración correcta, ¿qué tendría que haber en lo que el subagente le devuelve al coordinador para que este pueda anotar la brecha sin inventarla? ¿Qué distingue ese contenido de un vacío?
2. La fuente con *timeout* falla en todas las consultas y `SRC-REDES`, solo en la primera. ¿Qué esperas que haga el subagente con cada una y qué le llegará al coordinador de cada una? ¿Qué parte de eso decide el código y qué parte el modelo?
3. Con `--anti generico`, el subagente reintenta igual que en la correcta, pero al coordinador solo le llega «búsqueda no disponible»: no sabe qué se intentó ni qué alternativas hay. ¿Esperas que haga algo distinto que en la correcta? ¿Podrá anotar la brecha igualmente?
4. Con `--anti silenciar`, el *handler* convierte el *timeout* en un vacío antes de que lo vea el subagente. ¿Qué sabe entonces el coordinador de esa fuente? ¿Hay algo en lo que recibe que pudiera delatar el fallo?
5. Con `--anti abortar`, ¿qué se pierde respecto a la correcta, y qué parte del trabajo ya estaba hecha cuando se decide abortar?

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
- C. Que cada subagente devuelva tipo de fallo, consulta, lo obtenido y alternativas, y que el informe anote la brecha.
- D. Que el coordinador repita las dos delegaciones con el mismo encargo y cancele la investigación si vuelven a fallar.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** El mensaje genérico esconde justo la diferencia que importa (TS 5.3-K3): un *timeout* puede merecer otro intento o una fuente alternativa, y una consulta mal formada no se arregla repitiéndola. Con el tipo de fallo, lo intentado, lo obtenido y las alternativas, el coordinador decide en cada caso (TS 5.3-K1, S1), y el informe dice qué queda sin cubrir (TS 5.3-S4). La recuperación local ya se hizo y no hay que repetirla (TS 5.3-S3, TS 2.2-S3). En este módulo, con una sola fuente caída, el mensaje genérico no cambió lo que hizo el coordinador (Paso 3): la pregunta plantea el caso en que sí hay que elegir.

- **A** quita el límite al reintento, y la consulta mal formada no va a responder nunca.
- **B** convierte dos fallos en vacíos válidos (TS 5.3-K2, K4): el informe dirá que esas fuentes no tenían nada.
- **D** repite a ciegas lo que ya falló y, si vuelve a fallar, tira el trabajo de las demás fuentes (TS 5.3-K4).
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
- **`formato_uniforme`:** el prompt del sintetizador pide todo en prosa continua, sin la instrucción de tabla para las cifras comparables.
- **`inventar_explicacion`:** el sintetizador explica siempre por qué difieren las cifras (periodo, método, muestra o población), aunque el contexto no lo explique; es el control positivo de la medida del par sin explicación.
- **`--parte medio --texto sin_resumen|con_resumen|con_encabezados|encabezados_y_resumen`:** el mismo informe largo, sin tratamiento, con la línea de resumen al principio, con encabezados de sección o con las dos cosas.

El código mide sin modelo cuántas cifras del informe llevan su fuente en la misma frase o fila, si la ubicación y el fragmento llegan al informe, si la decisión del coordinador aparece en el prompt del sintetizador, si algún conflicto aparece fusionado en un promedio, si la tabla lleva las cifras de los pares, cuánto pesa lo que llega al sintetizador, qué contexto usa el informe para explicar cada diferencia, si deja como disputado lo que el contexto no explica y si el resumen del informe largo cita el hallazgo clave.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. En la configuración correcta, ¿qué parte de la procedencia está garantizada por la estructura de lo que devuelve el investigador y qué parte depende de lo que escriba el sintetizador?
2. Con `--anti sin_procedencia`, ¿qué sabe el sintetizador de cada cifra? ¿Dónde esperas ver el daño: en lo que devuelve el investigador, en el informe final o en ambos? Razónalo antes de ejecutar.
3. Con `--anti promedio`, ¿qué cifras tendrá el informe que no sale en ninguna fuente? ¿Seguirán apareciendo también las cifras originales?
4. Mira el contexto metodológico de cada par en las fuentes (`fuentes_investigacion.json`): ¿qué diferencias explica y cuál no? ¿Qué tendría que hacer un buen informe con cada par, y qué error solo puede delatar un par que nada explica?
5. Con `--anti formato_uniforme` y con `--anti inventar_explicacion`, el sintetizador recibe una orden que va contra la correcta. ¿Qué esperas ver en el informe con cada una? ¿Cuál crees que obedecerá más, y por qué?
6. En la parte `medio`, ¿qué cambia al anteponer una línea de resumen, y qué al poner encabezados de sección? ¿Esperas la misma diferencia con un informe mucho más largo que con uno de unas 1.500 palabras?

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

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
- **Manifest:** un archivo `manifest.json` en el mismo directorio con las fases hechas, el resumen de cada una, las fuentes cubiertas y el número de hallazgos. Es lo que permite retomar: la ejecución siguiente lo carga y lo inyecta en el prompt de la fase que sigue.
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

Con tus palabras; no hay un número que acertar:

1. En la correcta, ¿qué llega al contexto del coordinador de lo que dice cada fuente y qué se queda fuera? ¿Quién decide qué se guarda en el scratchpad, el código o el modelo?
2. Con `--anti todo_en_contexto`, ¿cuánto contexto esperas acumulado frente a lo que ve el coordinador en cada fase de la correcta? ¿Esperas que el informe final pierda alguno de los hechos o que aparezcan «patrones típicos» en su lugar?
3. Tras `--simular-caida`, ¿qué tiene que haber en el manifest y en el scratchpad para que la ejecución siguiente no repita consultas? ¿Qué pasaría si faltara uno de los dos?
4. ¿Cuál de las dos configuraciones esperas que cueste más, y por qué?

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

Una investigación en tres fases se corta durante la tercera. Al terminar cada fase, los agentes habían guardado su estado en un sitio acordado. ¿Cómo debe retomarse?

- A. Leer el estado guardado, comprobar que está completo y pasar a la fase pendiente lo hecho y su resumen.
- B. Reanudar la conversación anterior completa, que conserva el detalle de cada consulta aunque ya sea muy larga.
- C. Empezar de nuevo desde la primera fase con un contexto limpio, por si el estado guardado quedó a medias.
- D. Relanzar solo la tercera fase con la petición original y dejar que vuelva a consultar las fuentes que necesite.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** Para recuperarse de una caída, cada agente exporta su estado a un sitio conocido, y al retomar el coordinador carga el manifest y lo pasa a los prompts (TS 5.4-K4, S4). El resumen de las fases hechas va en el contexto inicial de la siguiente (TS 5.4-S3). Comprobar el estado antes de usarlo evita retomar desde uno roto o ajeno (inferencia de este módulo).

- **B** arrastra un contexto largo, que es lo que favorece la degradación (TS 5.4-K1), y tras una caída puede no haber conversación que reanudar.
- **C** tira el trabajo que se guardó precisamente para no repetirlo. Un estado dudoso se comprueba; no se descarta por defecto.
- **D** no repite las fases hechas, pero la tercera arranca sin lo descubierto: vuelve a consultar fuentes y puede contradecir lo que ya se resumió (TS 5.4-S3, S4).
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
  - **Modo estricto (`strict: true`):** un campo de la definición de la tool que hace que la API garantice que su entrada cumple el esquema, con los objetos cerrados (`additionalProperties: false`). Elimina los errores de sintaxis del esquema; no los de significado (TS 4.3-K1, K3).
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
- **`tipo_desconocido`:** tres tools, una por tipo de documento, y `tool_choice` `any` (el modelo tiene que llamar a una, pero elige cuál). Se compara con `auto` y con forzar siempre la tool de factura.
- **`few_shot`:** el mismo esquema sin las reglas de formato en las descripciones, con y sin tres ejemplos en el *system prompt* (una factura en tabla, otra en prosa y un albarán en líneas sueltas). Admite `--rol-modelo enforcement` (Haiku 4.5). Además de las fechas, imprime los campos con valor en la etiqueta que salen `null` o vacíos (**faltantes**) y los que el modelo inventa donde la etiqueta dice que no están (**inventados**), con y sin ejemplos.
- **`enriquecimiento`:** dos tools, `extract_metadata` y `lookup_purchase_order(po_number)`, cuyo resultado sale de `pedidos_compra.json` (determinista). El primer turno va con `tool_choice` forzado a `extract_metadata`; los siguientes, en `auto`, con la extracción devuelta como `tool_result`. `--anti auto_desde_inicio` usa `auto` desde el primer turno. Se mide el orden de las llamadas, si el modelo consulta un pedido antes de extraer o con un número que no sale del documento, y si el resultado final usa el pedido extraído.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. Un documento no menciona número de pedido. Si `po_number` es obligatorio y de tipo `string`, ¿qué opciones le quedan al modelo? ¿Y si es *nullable* y no obligatorio? En cada caso, ¿qué te garantiza el esquema y qué no?
2. Con el `enum` cerrado (solo `invoice` y `delivery_note`), ¿qué dos salidas distintas podría dar el modelo con un certificado de garantía? ¿Cuál detectaría un validador del esquema y cuál solo se ve comparando con la etiqueta?
3. Con las tres tools por tipo, ¿qué esperas de `any`, de `auto` y de forzar siempre la tool de factura? ¿Qué le pasa a un albarán en cada caso?
4. La parte `few_shot` quita de las descripciones la regla de cómo escribir una fecha. ¿Qué tendría que ocurrir sin ejemplos para que los ejemplos se notaran? ¿Esperas lo mismo con dos modelos distintos? ¿Y con los campos que el documento sí trae pero el modelo podría dejar vacíos?
5. En `enriquecimiento`, el modelo tiene una tool para extraer y otra para consultar el pedido. Con `auto` desde el primer turno, ¿qué podría hacer mal? Si en tus ejecuciones no lo hace nunca, ¿basta eso para prescindir del primer turno forzado?
6. En `estricto`, el `enum` solo admite `invoice` y `delivery_note`. Con `strict: true`, ¿puede salir algún valor fuera del `enum`? ¿Qué pasará con el certificado de garantía? ¿Esperas que «forma válida» y «tipo correcto» suban, bajen o se queden igual con `strict` respecto de sin él? ¿Y qué te dice eso de lo que el modo estricto garantiza y de lo que no?

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

- **A** pide por escrito lo contrario de lo que exige el esquema, y gana el esquema.
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

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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

Con tus palabras; no hay un número que acertar:

1. Una factura no cita número de pedido en ninguna parte. ¿Qué debería hacer el bucle correcto con ella? Si se le pide al modelo una y otra vez que corrija ese campo, ¿qué acabará devolviendo, y podría distinguirlo el validador de un número bueno?
2. Una fecha sale como `12/03/2026` y la regla exige ISO. ¿Qué sabe el modelo en el reintento con el mensaje concreto y qué sabe con «Inténtalo de nuevo»? ¿Qué variante esperas que gaste más en reintentos, y por qué?
3. Dos documentos declaran un total que no es la suma de sus líneas, y el error está en el propio documento, no en la extracción. ¿Qué puede hacer el modelo si le pides que lo revise? ¿Qué sería la salida correcta?
4. Sin mirar etiquetas, ¿cómo decide el código que un dato no está en el documento? ¿Qué parte de esa decisión no puede tomar el modelo por ti?

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

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
- **`--enviar`:** estima una cota superior del coste, hace una **muestra síncrona** de tres documentos con los mismos parámetros y la compara con las etiquetas (acierto por campo, para afinar el prompt antes del lote). Si la forma no cumple el esquema o el acierto queda por debajo del umbral (`SAMPLE_MIN_ACCURACY`, 85 %, visible en el código), no se crea el lote. Imprime su identificador. `--sin-muestra` salta la muestra.
- **`--batch-id <id>`:** consulta el estado del lote y, si ha terminado, lee los resultados: orden de llegada, tipo de cada resultado, emparejado por `custom_id` y coste con el descuento. `--esperar <s>` espera hasta ese número de segundos. `--reenviar` crea un lote nuevo solo con los fallidos:
  - un **truncado** se parte en trozos (de 10 líneas la primera vez) y, si un trozo vuelve a truncarse, el documento se re-trocea a la mitad, hasta una línea por trozo; el id de cada trozo lleva su tamaño (`DC-12--s10-c3`);
  - un trozo que falla **sin truncarse** (`invalid`, `errored`, `expired`) se reenvía con su propio texto, no con el documento entero;
  - si el mismo documento tiene un trozo truncado y otro inválido, el re-troceo cubre los dos; el resultado no depende del orden de llegada.
- **`--anti por_orden`** (con `--batch-id`): empareja los resultados por posición en vez de por `custom_id`. El recuento es «X de N», con N los documentos que tienen número en la etiqueta; un resultado sin datos (truncado o fallido) no cuenta como datos de otro documento.
- **El tope `--budget` es por invocación.** Con `--enviar` cubre la muestra síncrona **más** la estimación del lote. Con `--batch-id --reenviar` cubre solo la estimación del reenvío: el lote que se lee ya se pagó en otra invocación y no se resta.

Las peticiones llevan un `max_tokens` corto (600) a propósito, para que el lote tenga algo que reenviar. Qué documento no cabe y cómo llega su resultado se ve en el Paso 3.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. Las facturas del turno de noche tienen un plazo de 30 h y llegan a lo largo de todo el día. ¿Cada cuántas horas enviarías un lote para cumplirlo, y por qué no basta con comparar 30 h con las 24 h de la ventana? Si un documento falla, ¿queda tiempo para reenviarlo?
2. Envías 12 peticiones en un lote. ¿En qué orden esperas los resultados? ¿Qué le pasa a un código que los empareja con los documentos por posición?
3. Una respuesta se corta por `max_tokens`. ¿Con qué tipo de resultado crees que llega dentro del lote? ¿Qué tiene que mirar tu código para saber que no sirve?
4. Reenvías un documento largo partido en trozos, y uno de ellos vuelve a truncarse. ¿Qué harías y qué no harías con el resto del lote?

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

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
  - **Umbral de revisión:** la confianza por encima de la cual una extracción se acepta sin revisión. Se fija con el conjunto de calibración, por segmento, y es `None` (todo a revisión) si no hay evidencia suficiente.
  - **Estrato:** aquí, la combinación de tipo de documento y campo. La muestra estratificada toma un mínimo de cada uno; la simple sortea sobre toda la población.
  - **Cupo de revisión:** cuántos documentos puede mirar el equipo en el periodo. El módulo compara tres órdenes de la cola con el mismo cupo.

### El ejercicio

La parte `poblacion` calcula, con reglas de código y sin modelo: la exactitud global y por segmento, las bandas de calibración, el estado de cada segmento (`ready`, `below_target` o `insufficient_data` con un objetivo del 98 % y al menos 20 ejemplos), el enrutado de producción, un experimento de muestreo (500 repeticiones de una muestra de 60) y tres órdenes de la cola de revisión. Los documentos con `conflict_detected` o ambiguos van a revisión aunque su confianza sea alta.

- **Correcta:** un umbral por tipo y campo, calibrado en el conjunto de calibración.
- **`--anti precision_agregada`:** un único umbral para todos los segmentos, el que cumple el objetivo mirando solo la exactitud global. Todo lo demás es igual.
- **`--anti confianza_global`:** se decide con una sola confianza por documento (la media de las de sus campos), con un único umbral. Todo lo demás es igual.

La parte `confianza_modelo` pide a un modelo que extraiga los 12 documentos con la confianza de cada campo, y compara lo que dice con lo que acierta. `--sin-reglas-de-formato` quita de las descripciones del esquema las reglas de formato (como en el módulo 08) para que un modelo capaz cometa errores que calibrar.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. Una extracción acierta el 97 % de los valores. ¿Qué tendría que pasar con los demás segmentos para que un tipo de documento rinda mucho peor sin que el titular lo muestre? ¿De qué depende cuánto puede esconder?
2. Para vigilar lo que se acepta con confianza alta, ¿qué muestra esperas que vea más a menudo los errores de un tipo de documento poco frecuente, una aleatoria simple o una estratificada? ¿Qué cambiaría si ese tipo pesara aún menos?
3. Si el modelo declara 0,99 en un campo, ¿qué más necesitas saber para decidir si basta para no revisarlo? ¿Y si el segmento tiene muy pocos ejemplos etiquetados?
4. Un documento tiene una confianza media alta, pero uno de sus campos es dudoso. ¿Qué decide una sola confianza por documento y qué decidiría una por campo?
5. Con poca capacidad de revisión, ¿pesan igual un documento con conflicto y uno con un campo de baja confianza? ¿Qué tipo de problema dejará sin ver cada orden de la cola?
6. En la parte con modelo, ¿qué tiene que haber en las extracciones para que se pueda medir si la confianza declarada está calibrada? ¿Dónde esperas que el modelo esté más seguro de lo que debería?

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

**Parte `poblacion`** (sin modelo; mismos números en cada ejecución):

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | global 97,7 % de 1752 valores; `other`: 62,5 % (72 valores, 27 errores) frente a 99,0 % de las facturas; facturas en prosa, `issue_date`: 86,0 %. Se automatizan 765 valores con **6 errores (0,8 %)** y **0 del tipo raro**: sus 6 campos son `insufficient_data` | el titular esconde el tipo raro; con 6 documentos por conjunto no hay evidencia para automatizarlo |
| `precision_agregada` | automático 805 valores con **17 errores (2,1 %)**; **34 valores del tipo raro aceptados, 11 con error** | un umbral para todos hereda la confianza de los segmentos grandes |
| `confianza_global` | umbral 0,92; automático 780 valores con **14 errores (1,8 %)**; 24 del tipo raro aceptados, 8 con error | la media del documento esconde el campo dudoso |

Calibración (conjunto de calibración): la banda 0,95–1,00 acierta el 98,7 % (declara 96,9 %) y la 0,85–0,95, el 97,2 % (declara 92,2 %); hueco ponderado 0,034. **Aun así hay 34 errores con confianza ≥ 0,85 de 41**, la mayoría en el tipo raro: que el hueco sea pequeño en conjunto no quiere decir que la confianza sirva sola.

Muestra de 60 de las 871 extracciones de confianza alta de producción, 500 repeticiones:

| Muestreo | Ve algún error del tipo raro | Patrones de error por muestra (de 8) |
| :--- | :--- | :--- |
| aleatorio simple | 53,4 % de las muestras | 1,0 |
| estratificado (tipo y campo, mínimo 3) | 100 % de las muestras | 3,7 |

Cola de revisión (25 documentos con algo que revisar, capacidad 6, variante correcta):

| Orden | Errores de extracción vistos (de 16) | Documentos con conflicto o ambiguos vistos (de 11) |
| :--- | :--- | :--- |
| llegada | 4 | 4 |
| confianza (la más baja primero) | 8 | 1 |
| prioridad (conflictos primero) | 0 | 6 |

Los conflictos y los errores de extracción son cosas distintas: con poca capacidad, un orden ve unos y deja los otros. Ninguno gana en todo.

**Parte `confianza_modelo`** (Messages API, 12 documentos × 3 repeticiones):

| Modelo de la medida | Descripciones | Señal observada |
| :--- | :--- | :--- |
| Haiku 5.5 (rol `agent`, ~0,014 $) | con reglas de formato | **0 errores en 153 valores extraídos**: no hay nada que calibrar. Confianza media 0,95 cuando acierta; el hueco de calibración es 0,046 por declarar menos de lo que acierta. En los campos que deja en `null` la confianza media es 0,64–0,65 |
| Haiku 4.5 (rol `enforcement`, ~0,13 $) | sin reglas de formato | **6, 7 y 8 errores por repetición, casi todos de formato de fecha, con confianza ≥ 0,85 en 5, 7 y 7**; banda 0,97–1,00: **acierta el 85,5 %** y declara 99,5 %; banda 0,90–0,97: 90,8 % frente a 95,0 %. En los `null`, confianza media 0,32 y 0 campos que debían tener valor |

Notas:

- **El modelo está más seguro donde falla:** los errores de fecha de Haiku 4.5 llegan con 0,95–1,0, porque el modelo lee bien la fecha y se equivoca en la forma. La confianza declarada no los distingue de los aciertos. Una medida que dé cero no demuestra que detecte el fallo, por eso `tests/test_app3_10_confianza_y_revision.py` incluye un control positivo sintético (un conjunto mal calibrado da un hueco de ~0,45 y uno calibrado, ~0).
- **La confianza de un campo en `null` habla de la ausencia:** con Haiku 4.5 ronda 0,32 aunque el `null` sea correcto, y mezclarla con los valores extraídos daba un hueco de calibración de 0,137 con Haiku 5.5 que era un artefacto. El módulo la mide aparte.
- **Segmentos pequeños:** con 6 documentos por conjunto, el tipo raro no llega a los 20 ejemplos de confianza alta que se piden. No se puede validar, así que no se automatiza (`insufficient_data` no es lo mismo que `below_target`).
- La población es simulada (la genera `datos/generar_sinteticos.py`): la confianza de sus valores no es la de un modelo real. La parte con modelo es la única que mide una confianza declarada de verdad.
- Lo que no depende del modelo se prueba en `tests/test_app3_10_confianza_y_revision.py` y `tests/test_datos_entrega3c.py`.
</details>

### Pregunta tipo examen

Un sistema extrae campos de facturas, albaranes y un tipo de documento de compra poco frecuente. Su exactitud global medida es del 97 %, y el equipo propone dejar de revisar todo lo que el modelo marque con confianza alta. ¿Qué debe hacerse antes de reducir la revisión humana?

- A. Elegir un único umbral de confianza con el que la exactitud global de lo aceptado llegue al 99 % y no revisar lo que lo supere.
- B. Pedir al modelo una confianza por documento, la media de las de sus campos, y no revisar los documentos que superen un umbral.
- C. Mantener el 97 % como criterio de aceptación y revisar cada mes una muestra aleatoria simple de lo que se acepta sin revisión.
- D. Medir la exactitud por tipo de documento y por campo contra datos etiquetados, fijar ahí umbrales por segmento y muestrear lo aceptado por estratos.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** Una exactitud agregada alta puede esconder un tipo de documento o un campo que rinde mal (TS 5.5-K1), así que antes de automatizar se comprueba la exactitud por tipo y por campo (K4, S2). La confianza por campo solo sirve para enrutar después de calibrarla con un conjunto etiquetado, que fija los umbrales (K3, S3), y lo aceptado se sigue vigilando con una muestra aleatoria estratificada (K2, S1).

- **A** elige el umbral mirando la cifra global, que es justo la que puede esconder el segmento malo (K1, K4).
- **B** junta los campos de un documento en una sola cifra: la guía habla de confianza por campo (K3), y la media esconde el campo dudoso detrás de los buenos (inferencia propia).
- **C** decide por el titular y vigila con una muestra simple, que apenas toca un tipo poco frecuente; la guía pide estratificarla (K2, S1).
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

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
  - **Coincide con un fallo sembrado:** el hallazgo cae en su archivo, a dos líneas o menos, o nombra su función o símbolo; un fallo entre archivos también se encuentra en sus llamadores si el hallazgo habla de la clave o de la unidad.

### El ejercicio

`--parte orden` construye el repositorio temporal y muestra la orden y el tamaño del prompt, sin ejecutar nada. `--parte revision` revisa el diff del primer commit; `--parte rerevision`, el diff completo de la rama tras el segundo; `--parte tests` pide los tests que faltan para el primer commit. Cada variante cambia una sola cosa respecto a la correcta:

- **Correcta (`revision`):** criterios categóricos con severidades y un ejemplo de código por severidad, y *few-shot* con el formato de salida y un patrón aceptable que no se informa.
- **`--anti conservador`:** los criterios y las severidades se sustituyen por «Sé conservador: informa solo de los problemas de los que estés muy seguro». El *few-shot* y el schema son los mismos.
- **`--anti sin_ejemplos`:** sin el bloque *few-shot*; los criterios siguen.
- **`--sin-categoria comment`:** la categoría `comment` desaparece de los criterios y del schema, y nada más cambia.
- **Correcta (`rerevision`):** la segunda revisión lleva la lista de los hallazgos previos (construida desde las etiquetas) y la orden de informar solo de lo nuevo o de lo no resuelto. **`--anti sin_previos`:** el mismo prompt, sin esa lista.
- **Correcta (`tests`):** el prompt lleva los tests existentes y el `CLAUDE.md` tiene los estándares de tests. **`--anti sin_tests_existentes`:** sin los tests existentes. **`--anti sin_estandares`:** un `CLAUDE.md` sin esa sección. En esta parte la orden va sin tools, para que el modelo no pueda descubrir por su cuenta lo que se le quita del contexto.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. Dos variantes tocan el prompt de la revisión: una sustituye los criterios por «sé conservador» y otra quita los ejemplos. ¿Dónde podría notarse cada cambio, en lo que el revisor encuentra o en lo que marca de más? ¿Cuántas ejecuciones necesitarías para distinguir un efecto de la variación de una ejecución a otra?
2. Una categoría genera falsos positivos y la quitas del prompt y del schema. ¿Qué puede pasar con el hallazgo que antes caía en esa categoría? ¿Qué te diría cada posibilidad sobre el criterio?
3. Revisas una segunda vez, tras un commit nuevo, el diff completo de la rama. ¿Qué repetirá un revisor que no sabe lo que ya se publicó, y qué cambia si le das la lista?
4. Pides los tests que faltan con y sin los tests existentes en el contexto, y con y sin los estándares de tests en el `CLAUDE.md`. ¿Qué podría cambiar en los escenarios que repiten lo ya cubierto? ¿Qué harías si el resultado no fuera el que esperas?
5. El modelo escribe el `detected_pattern` del mismo falso positivo de varias formas. ¿Qué se pierde al agrupar los descartados, y qué parte de eso arregla el código y qué parte no?

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

Sonnet 5.5 (rol `reviewer`), `claude -p` aislado. Hubo **dos cambios de lo medido** durante la construcción, y las cifras van marcadas: **antes**, cuatro fallos sembrados (A a D) y una puntuación por línea (a dos líneas o menos); **después**, un quinto fallo entre archivos (F) y una puntuación que también reconoce el símbolo, porque el modelo cita las líneas de forma aproximada (con la ventana de líneas, un acierto con la línea desplazada contaba como falso positivo).

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta, antes (8 ejecuciones) | encuentra A a D en 7 de 8 (A, los argumentos intercambiados, se pierde en 1); **marca el cambio correcto** (el comentario de `REINTENTOS`, patrón `misleading_comment`) en 3 de 8; 0 falsos positivos | el criterio de `comment` dice «contradice el código» y aun así el modelo marca un comentario que justifica un valor |
| correcta, después (2 ejecuciones) | A a D y F en 2 de 2; marca el cambio correcto en 2 de 2 | igual que antes; F, el fallo entre archivos, también sale |
| `conservador`, antes (8 ejecuciones) | A se pierde en 2 de 8 (en 2 de las 3 primeras y en ninguna de las 5 siguientes); B, C y D en 8 de 8; ninguna marca del cambio correcto ni falsos positivos | **sin diferencia estable** con la correcta (A se pierde en 1 de 8 con ella): con tres ejecuciones parecía que «sé conservador» perdía A, y con cinco más no. La medida no separa las dos variantes |
| `sin_ejemplos` (10 ejecuciones en tres momentos) | antes (3): A se pierde en 1 de 3 y marca el cambio correcto en 2 de 3. Después, con la puntuación por línea (5): **B (`os.system`) no sale en 3 de 5** y marca el cambio correcto en 5 de 5. Después, con la puntuación por símbolo (2): A a D y F en 2 de 2 y ninguna marca del cambio correcto | **sin señal estable**: la pérdida de B no se repite en las dos últimas. Una lectura posible, sin comprobar: el ejemplo que se quita (una inyección en la shell) se parece al fallo B |
| `--sin-categoria comment`, antes (3 ejecuciones) | C (el comentario que contradice el código) se encuentra en 3 de 3, ahora como `bug`; sigue marcándose el cambio correcto en 2 de 3 | **sin efecto visible** sobre el falso positivo: el modelo reclasificó el hallazgo como `bug` |
| rerevision correcta (antes, 3 ejecuciones) | hallazgos 0, 1 y 0: **0 repetidos** de la primera revisión; E, el bug nuevo, sale en 1 de 3 | con la lista y la orden, no repite lo ya publicado |
| `rerevision --anti sin_previos` (antes, 3 ejecuciones) | hallazgos 4, 4 y 5: **repite B, C y D en 3 de 3**; E sale en 1 de 3 | sin la lista, publica otra vez lo ya publicado; encontrar lo nuevo no mejora |
| `tests` correcta (antes y después, 3 + 3) | **1 escenario repetido por ejecución** (siempre `calcular_sla(alta, 3)`); 6–7 y 7–10 escenarios nuevos | ver la nota |
| `tests --anti sin_tests_existentes` (antes, 3) | **0 repetidos**; 6–11 nuevos | **al revés de lo esperado**: 1 escenario repetido por ejecución con los tests existentes en el contexto y 0 sin ellos |
| `tests --anti sin_estandares` (antes, 3) | 1 repetido por ejecución; 7–9 nuevos | **sin diferencia** con los estándares en el `CLAUDE.md` |

Notas:

- **Los criterios categóricos no resuelven el comentario del cambio correcto:** el falso positivo más estable es el comentario de `REINTENTOS`. El registro de descartados lo agrupa por `detected_pattern`, pero el modelo escribe un nombre distinto casi cada vez (`misleading_comment`, `comentario_sin_respaldo_en_codigo`, `comentario_poco_relacionado`, `comentario_justificacion_dudosa`…): agrupar por ese campo sin normalizarlo lo dispersa. `normalize_pattern` solo iguala mayúsculas y separadores.
- **`--parte tests` y los estándares:** el `CLAUDE.md` de CI con los estándares llega a la sesión (la sonda C1 lo comprueba), pero no cambió nada de lo medido.

**Lo que no coincide con la guía.** **Producto observado (no evaluable):** tres medidas de este módulo no muestran lo que dice la guía. Ninguna cambia la respuesta de examen, que es siempre la de la guía.

- **Tests existentes en el contexto (3.6-S4): al revés de lo esperado.** Con ellos salió 1 escenario repetido por ejecución (siempre `calcular_sla(alta, 3)`) y sin ellos, 0. Hipótesis sin comprobar: ver los tests ancla al modelo en los escenarios que ya existen, y sin verlos propone solo lo que toca el cambio. En el examen, los tests existentes van en el contexto para no proponer escenarios ya cubiertos.
- **`--anti conservador` (4.1-K2): la medida no respalda ni contradice la viñeta.** Con tres ejecuciones parecía perder el fallo A y con cinco más no; con 8 ejecuciones de cada una, no se separa de la correcta. La lección de 4.1-K2 es conceptual y no se apoya en esta medida.
- **`--anti sin_ejemplos` y `--sin-categoria comment`: sin señal estable.** No contradicen la guía (4.2-S2, S3 y 4.1-S2), pero tampoco la demuestran. Desactivar `comment` no quitó el falso positivo, lo reclasificó como `bug`. Inferencia propia: 4.1-S2 es una medida para recuperar la confianza mientras se arregla el criterio, no el arreglo.

Avisos sobre las cifras y la ejecución:

- **Antes y después del fallo F:** las cifras «antes» se midieron con cuatro fallos sembrados (A a D); las «después», con el quinto, F, el segundo fallo entre archivos, que se añadió para el módulo 12.
- **La puntuación por símbolo no recalculó las cifras anteriores:** el modelo cita las líneas de forma aproximada, hasta 3–5 líneas de más, y por eso la puntuación reconoce ahora también el símbolo del fallo. Las cifras «antes» se midieron con la ventana de líneas y no se recalcularon.
- **El tope de coste** es `--max-budget-usd` de cada `claude -p`: el módulo reparte `--budget` entre las repeticiones y le pasa a cada una lo que queda.
- Lo que no depende del modelo se prueba en `tests/test_app3_11_criterios_y_ci.py`, `tests/test_headless.py` y `tests/test_datos_entrega3c.py`. Coste de las ejecuciones con modelo de este módulo: ~1,0 $.
</details>

### Pregunta tipo examen

**Pregunta 1 (una respuesta).** Un equipo ejecuta Claude Code en CI para revisar cada *pull request* y publica los hallazgos como comentarios en línea. La categoría «comentario inexacto» marca a menudo comentarios del código que son correctos, y los desarrolladores han empezado a ignorar también los hallazgos de seguridad. ¿Qué debe hacer el equipo?

- A. Añadir al prompt que informe solo de lo que tenga alta confianza y mantener activas todas las categorías mientras tanto.
- B. Apagar esa categoría por ahora, reescribir su criterio para marcar solo un comentario que contradiga al código y añadir `detected_pattern`.
- C. Pedir una puntuación de confianza por hallazgo y publicar solo los que pasen de un umbral, sin tocar el criterio de ninguna categoría.
- D. Mantener todas las categorías y juntar los hallazgos en un único comentario de resumen al final del PR, para que molesten menos.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** Una categoría con muchos falsos positivos hace desconfiar también de las que aciertan (TS 4.1-K3), así que se desactiva temporalmente mientras se mejora su prompt (4.1-S2). El arreglo es un criterio explícito, que marque un comentario solo cuando lo que dice no coincide con lo que hace el código (4.1-K1, S1), y el campo `detected_pattern` permite analizar qué patrones se descartan (4.4-K3, S3).

- **A** es la instrucción general que la guía descarta: «solo alta confianza» no mejora la precisión frente a criterios categóricos (4.1-K2), y la categoría que resta confianza sigue publicando.
- **C** filtra por la confianza en vez de definir qué se informa y qué no (4.1-S1); el criterio vago sigue igual.
- **D** no reduce los falsos positivos (4.1-K3) y renuncia a los comentarios en línea, que es para lo que sirve la salida estructurada en CI (3.6-S2).

**Producto observado (no evaluable):** en este módulo, quitar la categoría `comment` no hizo desaparecer el falso positivo, que el modelo reclasificó como `bug` (Paso 3). No cambia la respuesta de examen: apagar la categoría es la medida temporal y el arreglo es el criterio.
</details>

**Pregunta 2 (multiple-response).** Un equipo usa `claude -p --output-format json --json-schema` para revisar los commits de una rama y para pedir los tests que faltan. Tras cada commit nuevo, la revisión vuelve a publicar comentarios que ya estaban, y los tests propuestos repiten escenarios ya cubiertos o aportan poco. **Selecciona dos** cambios que sigan la guía. Evalúa cada opción por separado.

- A. Pedir los tests sin darle al modelo los tests existentes, para que no se ancle en lo que ya está escrito.
- B. En la segunda revisión, incluir los hallazgos previos y ordenar que informe solo de lo nuevo o de lo no resuelto.
- C. Quitar `--json-schema` y extraer los hallazgos del texto de la respuesta para publicarlos como comentarios.
- D. Documentar en el `CLAUDE.md` del proyecto los estándares de tests, qué hace valioso un test y las *fixtures* disponibles.

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**B y D.** La primera evita los comentarios duplicados (TS 3.6-S3) y la segunda da a Claude Code en CI el contexto del proyecto (3.6-K3) para que los tests generados sean mejores y aporten más (3.6-S5).

- **A** invierte lo que dice la guía: los tests existentes van en el contexto para no proponer escenarios que la suite ya cubre (3.6-S4).
- **B** es la práctica de la guía para no repetir comentarios al revisar de nuevo tras commits nuevos.
- **C** pierde la salida estructurada que una máquina necesita para publicar comentarios en línea (3.6-K2, S2).
- **D** es el uso de `CLAUDE.md` que la guía asigna al contexto de Claude Code en CI.

**Producto observado (no evaluable):** en este módulo, con los tests existentes en el contexto salió 1 escenario repetido por ejecución y sin ellos 0, al revés de lo esperado (Paso 3). No cambia la respuesta de examen: A sigue siendo incorrecta.
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 12 · Revisión independiente

<!-- BORRADOR (Sonnet 5.5): pendiente del pase de textos de Opus 5.5. -->

> **Qué vas a hacer:** Hacer que una sesión de `claude -p` escriba un cambio y revisarlo después de tres maneras: con una instancia nueva, reanudando la sesión que lo escribió y reanudándola con la orden explícita de revisar su propio cambio, en pasadas por archivo y de integración, con la confianza de cada hallazgo.
>
> **Necesitas antes:** El [módulo 11](#11--criterios-y-revisión-en-ci), cuyo cambio de prueba, schema de hallazgos y puntuación reutiliza, y el [10](#10--confianza-y-revisión-humana), cuya calibración aplica a la confianza de cada hallazgo.
>
> **Modo:** Ejecución ligera (`--parte plan` no usa modelo; cada revisión con modelo cuesta entre 0,10 y 0,20 $).

### Antes de empezar

Los términos comunes están en el [glosario](../docs/glosario.md). Como el módulo 11, lanza `claude -p` con la orden de [`harness/headless.py`](../harness/headless.py): aislada, de solo lectura en la revisión y con tope de coste.

- **El sistema:** una sesión generadora, con `Write`, parte del repositorio en el estado base y recibe el mensaje y el contenido exacto de cada archivo del primer commit del módulo 11, con la orden de escribirlos y explicar por qué tomó cada decisión. El diff que deja en el árbol de trabajo es lo que se revisa. Después, las pasadas: una por archivo (sin tools, con solo el diff de ese archivo), una de integración (con el diff completo, los hallazgos locales y `Read`, `Grep` y `Glob`) y una de verificación que da la confianza de cada hallazgo fusionado.
- **Términos propios:**
  - **Instancia nueva:** una ejecución de `claude -p` sin sesión previa: solo ve el diff y lo que lea del repositorio.
  - **Autorrevisión:** la misma revisión, pero como `--resume` de la sesión que escribió el cambio. Cada pasada la **bifurca** (`--fork-session`) para que las repeticiones no se contaminen entre sí.
  - **Pasada por archivo y de integración:** la primera mira un archivo sin ver el resto; la segunda mira los archivos juntos y busca fallos entre ellos (contratos, unidades, firmas, flujo de datos). Se encadenan: la de integración recibe los hallazgos locales y no debe repetirlos.
  - **Verificación:** una pasada que da, con el diff delante, una confianza de 0 a 1 a cada hallazgo. La que cuenta para enrutar es esta, no la que el hallazgo trae al nacer.
  - **Enrutar:** los hallazgos con confianza desde 0,8 se publican; el resto y los que no tienen confianza van a una persona. El umbral es una elección propia.
  - **Coste acumulado:** el `total_cost_usd` de una sesión reanudada incluye el de la sesión de origen; el coste de cada revisión es la diferencia, y el tope de la rama lo lleva `headless.Ledger`.

### El ejercicio

`--parte plan` muestra las pasadas, las tools de cada una y la orden de la autorrevisión, sin ejecutar nada. `--parte revision` genera el cambio y lo revisa. Las tres ramas usan los mismos prompts; cada una cambia una sola cosa:

- **Correcta:** las pasadas son instancias nuevas, sin sesión.
- **`--anti autorrevision`:** cada pasada es un `--resume --fork-session` de la sesión generadora.
- **`--anti autorrevision_explicita`:** igual que la anterior, con una frase delante de cada prompt: «Revisa críticamente tu propio cambio: busca los fallos que hayas podido pasar por alto al escribirlo».

El cambio lleva dos fallos entre archivos (`D`: `calcular_sla` devuelve minutos y sus llamadores leen horas, y `F`: `avance_plazo` devuelve una fracción de 0 a 1 y `texto_progreso` la imprime como porcentaje). Ninguno de los dos archivos lo delata del todo por sí solo.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. La sesión que escribió un cambio lo revisa en la misma sesión. ¿Qué sabe que no sabe una instancia nueva, y en qué sentido puede jugarle a favor y en contra?
2. ¿Qué fallos esperas que vea una pasada por archivo sin acceso al resto del repositorio, y cuáles solo una pasada de integración?
3. ¿Por qué se pide a la pasada de integración que no repita lo que ya salió por archivo? ¿Qué pasaría si dos pasadas se contradijeran?
4. La verificación da una confianza de 0,6 a un hallazgo. ¿Qué decides con eso y cómo comprobarías que esa confianza vale algo?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/12_revision_independiente.py                                              # el plan de pasadas y la orden, sin modelo
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --repeat 2                  # instancia nueva
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --anti autorrevision --repeat 2
uv run python app3_sistema_multiagente/12_revision_independiente.py --parte revision --anti autorrevision_explicita --repeat 2
```

**Si ejecutas:** el reparto en pasadas, los prompts, la fusión, el enrutado por confianza, la calibración y el coste de la sesión reanudada se prueban sin modelo. Cada ejecución completa (la sesión generadora, una vez, y cada revisión: cuatro pasadas por archivo, una de integración y una de verificación) cuesta entre 0,15 y 0,25 $ con `--repeat 1`. **El tope por defecto del repositorio (1,00 $) se reparte entre la generadora y las repeticiones; con `--repeat 3` en la autorrevisión se acerca a él.** Una pasada puede quedar sin presupuesto y sin confianza, y el módulo lo dice.

### Qué observar

Por repetición: qué fallos sembrados encontró cada pasada, cuáles faltan, falsos positivos, si marcó el cambio correcto, cuántos hallazgos se publican y cuántos van a una persona, la calibración de la verificación y el coste acumulado. Antes, si el diff que escribió la sesión generadora coincide con el cambio que se le dio.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Sonnet 5.5 (rol `reviewer`), `claude -p` aislado. La sesión generadora escribió exactamente el cambio dado en 3 de 5 sesiones; en las otras dos escribió otra cosa (en una añadió archivos de tests) y se puntuó el diff que escribió.

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta: instancia nueva (3 ejecuciones con el fallo F) | cada fallo sembrado sale en alguna pasada, con 0 falsos positivos y sin marcar el cambio correcto. Por archivo: A, B y C en 3 de 3; los entre archivos salen **por la pasada de integración en 2 de 3 ejecuciones y por la de archivo en 1 de 3**, tanto D como F, en ejecuciones distintas. Coste ~0,10 $ por revisión | la pasada de integración da una cobertura distinta a la local: los fallos entre archivos salen en una u otra, y ninguna sola los garantiza |
| `--anti autorrevision` (2 ejecuciones) | **A, B, C, D y F por la pasada por archivo en las 2**, sin falsos positivos ni marcas del cambio correcto. Coste ~0,19 $ por revisión | **sin señal de que se revise peor**: la sesión bifurcada recuerda todo lo que escribió y sus pasadas «locales» no son locales. Costó cerca del doble |
| `--anti autorrevision_explicita` | **sin medir**: no cupo en el tope de coste de la tarea | implementada y probada sin modelo |

Calibración de la verificación (instancia nueva, 2 ejecuciones, 17 hallazgos): todos coinciden con un fallo sembrado, y la verificación les da 0,61 de media en la banda 0,50–0,80, 0,89 en la 0,80–0,95 y 0,95 en la más alta; hueco de calibración 0,20 por quedarse corta. Con todos los hallazgos reales, la confianza no tiene nada que separar. En la segunda autorrevisión, la última pasada de verificación **se quedó sin presupuesto** (tope de 0,40 $) y los hallazgos no tienen confianza.

Notas:

- **Lo medido contradice la expectativa de la guía:** la guía dice que la sesión que generó el código lo revisa peor (TS 4.6-K1, K2; 3.6-K4). Aquí la autorrevisión encontró todo. Dos razones posibles, ninguna comprobada: el «razonamiento de generación» de esta sesión es el de copiar un cambio que se le dio, no el de diseñarlo; y los fallos sembrados son claros para un revisor que mira el código (por ejemplo, una inyección en la shell). La lección de K1 y K2 se queda como conceptual y sin señal estable.
- **La sesión bifurcada no es una pasada local:** como la sesión generadora escribió los cuatro archivos, ve a los llamadores en su historial. Una instancia nueva sin tools es la única pasada local de verdad.
- **El coste de la sesión reanudada es acumulado:** cada revisión bifurcada informa del coste de la generadora más el suyo (0,05 $ + ~0,03 $ por pasada). El módulo cuenta cada revisión por la diferencia y suma la generadora una vez.
- Tamaño de muestra pequeño (2 a 3 ejecuciones): el tope de coste de la tarea no dejó más.
- Lo que no depende del modelo se prueba en `tests/test_app3_12_revision_independiente.py` y `tests/test_headless.py`. Coste de las ejecuciones con modelo de este módulo, incluidas las de prueba: ~1,3 $.
</details>

### Pregunta tipo examen

Un equipo hace que Claude Code genere un cambio de varios archivos y, en la misma sesión, le pide que lo revise. La revisión encuentra poco, pero después una persona detecta un fallo entre dos archivos. ¿Qué debe cambiar el equipo?

- A. Pedir a la misma sesión que se revise con más cuidado, con una instrucción explícita de autorrevisión.
- B. Revisar con una segunda instancia sin el contexto de la generación, con una pasada por archivo para lo local y otra de integración para lo que cruza archivos.
- C. Activar un razonamiento más largo en la sesión que generó el código para que cuestione sus decisiones.
- D. Revisar todos los archivos a la vez en una sola pasada larga, para que no se pierda ningún detalle.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** Una instancia independiente encuentra mejor los problemas sutiles que la autorrevisión o el razonamiento extendido (TS 4.6-K2, S1); quien generó el código conserva su razonamiento y cuestiona menos sus decisiones (4.6-K1, 3.6-K4), y la revisión en varias pasadas, una por archivo y otra de integración, evita la dilución de la atención y los hallazgos contradictorios (4.6-K3, S2; 1.6-K2, S2).

- **A** deja la revisión en la misma sesión, que es lo que la guía desaconseja, también con una instrucción explícita (4.6-K2).
- **C** es el razonamiento extendido de la misma sesión, que la guía no da por mejor que una instancia independiente (4.6-K2).
- **D** diluye la atención en una sola pasada (4.6-K3). **Producto observado (no evaluable):** en este módulo, con Sonnet 5.5, la autorrevisión no encontró menos; no cambia la respuesta de examen.
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).
