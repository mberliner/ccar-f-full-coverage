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
| `06_contexto_largo.py` | D5 | 3 |
| [`07_extraccion_schema.py`](07_extraccion_schema.py) | TS 4.2-K4, S4, S5 · TS 4.3-K1…K4, S1…S6 | 3 |
| [`08_validacion_reintento.py`](08_validacion_reintento.py) | TS 4.4-K1…K4, S1…S4 | 3 |
| [`09_batches.py`](09_batches.py) | TS 4.5-K1…K4, S1…S4 | 3 |
| `10_confianza_y_revision.py` … `12_revision_independiente.py` | D3, D4 y D5 | 3 |

---

## 01 · Coordinador y subagentes

> **Qué vas a hacer:** Ver cómo un coordinador reparte una pregunta entre subagentes y qué cambia cuando su prompt está mal construido.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Los términos comunes (coordinador, subagente, `Agent`/`Task`, *hub-and-spoke*, descomposición, hook, permiso) están en el [glosario](../docs/glosario.md). Lo propio de este módulo:

- **El sistema:** un [coordinador](../docs/glosario.md#sistemas-multiagente) recibe una pregunta del usuario sobre la mesa de ayuda. Su única tool integrada es `Agent`, con la que lanza [subagentes](../docs/glosario.md#sistemas-multiagente). Los subagentes buscan en el servidor MCP en proceso `investigacion`, que lee los tickets y la KB sintéticos. El coordinador va en modo `dontAsk` y pre-aprueba `Agent` y las dos tools de búsqueda, que usan los subagentes.
- **El prompt del coordinador:** fija objetivos y criterios de calidad, no pasos: cubrir todo el alcance de la pregunta, citar cada afirmación con su ID y su fecha, señalar los artículos obsoletos e invocar solo a los subagentes que aporten. También le recuerda que los subagentes no ven su conversación, y le da el formato con el que debe pasar los hallazgos al sintetizador.
- **La barrera del coordinador:** `tools=["Agent"]` limita las tools integradas, pero no oculta al coordinador las del servidor MCP. Un [hook](../docs/glosario.md#control-del-agente) `PreToolUse` compartido (`coordinator_gate.py`) le deniega esas tools a él y deja pasar a los subagentes. Así, lo que se mide de los subagentes es solo trabajo suyo.
- **Contenido y metadatos:** cada resultado del servidor separa el texto (`content`) de sus datos de procedencia (`metadata`: ID, fecha, estado o artículo sustituto). Es el formato con el que los hallazgos viajan de un agente a otro.
- **Selección dinámica:** que el coordinador decida, según la pregunta, qué subagentes necesita, en lugar de recorrer siempre todos.
- **Subtema:** cada parte en que se divide un tema amplio. En los datos, «problemas de red» abarca VPN, wifi e impresora.

### Las tools del ejercicio

| Tool | Quién la tiene | Qué recibe | Qué devuelve |
| :--- | :--- | :--- | :--- |
| `Agent` | coordinador | el subagente (`subagent_type`) y su prompt | la respuesta final del subagente |
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

Un sistema de investigación tiene un coordinador y tres subagentes: búsqueda web, análisis de documentos y síntesis. Los informes finales omiten con frecuencia datos que los subagentes de búsqueda sí encontraron. Los registros muestran que el coordinador invoca al sintetizador con la pregunta original. ¿Cuál es la causa más probable?

- A. El sintetizador necesita un modelo con una ventana de contexto mayor.
- B. Los subagentes no heredan el contexto del coordinador: el sintetizador nunca recibió los hallazgos, que había que pasarle en el prompt.
- C. Los subagentes de búsqueda deberían escribir sus resultados en una memoria compartida.
- D. Falta `"Task"` en las `allowedTools` del sintetizador.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** El contexto del subagente es aislado y no hereda el historial del coordinador (TS 1.2-K2, 1.3-K2): los hallazgos completos se incluyen en su prompt (TS 1.3-S1), con los metadatos separados del contenido para conservar la atribución. C contradice que no comparten memoria entre invocaciones. D confunde quién necesita `Task`: es el coordinador, para lanzar subagentes (TS 1.3-K1).
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

Los términos comunes (coordinador, subagente, `Agent`/`Task`, descomposición, tools integradas) están en el [glosario](../docs/glosario.md). Las dos tools de búsqueda y la barrera del coordinador son las del [módulo 01](#01--coordinador-y-subagentes). Aquí el coordinador solo tiene dos subagentes, `tickets_analyst` y `kb_analyst`, sin sintetizador.

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

<!-- BORRADOR (Sonnet 5.5): pendiente del pase de textos de Opus 5.5 (cabecera del módulo, predicciones y pregunta). -->

> **Qué vas a hacer:** Ver qué le llega al coordinador cuando una de las fuentes de un subagente falla por *timeout*, y qué entrega a partir de ahí.
>
> **Necesitas antes:** El [módulo 01](#01--coordinador-y-subagentes) y el [módulo 03](#03--tools-entre-roles) (mismo patrón de coordinador, barrera y subagente).
>
> **Modo:** Ejecución obligatoria (el resultado parcial con la brecha anotada solo se ve ejecutando).

### Antes de empezar

Los términos comunes (coordinador, subagente, error estructurado, reintentable) están en el [glosario](../docs/glosario.md).

- **El sistema:** el coordinador tiene un único subagente, `researcher`, con una sola tool, `query_source`. La petición pide un informe de calidad del servicio con cinco fuentes sintéticas (`fuentes_investigacion.json`): tres responden con contenido, una responde **vacía** (no tiene nada que decir) y una falla siempre con un *timeout*. La petición no dice cuál es cuál.
- **Informe del subagente:** por cada fuente, un objeto JSON con `source_id`, `status` (`ok`, `empty` o `failed`) y `findings`. Si falla, también `error_context` con cuatro campos: `failure_type`, `attempted`, `partial_results` y `alternatives`.
- **Reintento local:** el subagente repite la consulta que falla con un error reintentable (hasta 2 veces). La fuente no tiene estado: falla siempre, así que el reintento no la recupera y lo que se observa es qué hace el agente después.
- **Vacío frente a fallo:** una fuente que responde con `total: 0` es un resultado válido; una que da *timeout* no ha dicho nada. Las medidas del módulo los distinguen leyendo los resultados de la tool, sin modelo.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `query_source` | `source_id` | el informe de la fuente en `content`, con su id, nombre y fecha en `metadata`; `total: 0` si la fuente responde sin contenido; un error transitorio reintentable si hay *timeout*; un error de validación si la fuente no existe |

### El ejercicio

Qué cambia en el código de cada variante `--anti`:

- **`generico`:** el prompt del investigador le pide que, si una fuente falla, devuelva `status: failed` con el mensaje «búsqueda no disponible» y nada más: sin `error_context` y sin reintentar. El coordinador es el mismo que en la correcta.
- **`silenciar`:** lo hace el **código**, no el prompt. El servidor se construye con `silence_failures=True` y el *handler* de `query_source` devuelve `total: 0` y `results: []` como éxito cuando la fuente da *timeout*. El investigador y el coordinador usan los mismos prompts que en la correcta.
- **`abortar`:** el prompt del coordinador añade que, si alguna fuente falla, no entregue nada parcial y responda solo `INVESTIGACIÓN ABORTADA`.

Cada ejecución imprime una línea `[esperado]` con la hipótesis escrita en el código. Es una predicción, no un resultado.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. En la configuración correcta, ¿qué tendría que haber en lo que el subagente le devuelve al coordinador para que este pueda anotar la brecha sin inventarla? ¿Qué distingue ese contenido de un vacío?
2. ¿Cuántas veces esperas que se consulte la fuente que falla, y cuántas las demás? ¿Qué parte de eso decide el código y qué parte el modelo?
3. Con `--anti silenciar`, ¿qué sabe el coordinador de la fuente que falló, y por qué ya no puede distinguirla de la vacía? ¿Qué más puede llegarle por otro camino?
4. Con `--anti abortar`, ¿qué se pierde respecto a la correcta, y qué parte del trabajo ya estaba hecha cuando se decide abortar?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py                    # correcta
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti generico    # fallo sin contexto
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti silenciar   # el handler traga el fallo
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --anti abortar     # un fallo tumba la investigación
uv run python app3_sistema_multiagente/04_errores_entre_agentes.py --repeat 3 --budget 0.60
```

**Si ejecutas:** las medidas y la forma del contexto de error se prueban sin modelo; ejecutar sirve para ver la señal de la guía: un resultado parcial con la brecha anotada.

### Qué observar

Las consultas por fuente y los reintentos locales, la cobertura según los informes del subagente, si el contexto de error está completo, los fallos que el *handler* tragó, si la brecha aparece anotada en el resultado, las decisiones del coordinador (cuántas veces delega y si menciona alternativas) y si el resultado es parcial o abortado.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Coordinador Sonnet 5.5, subagente Haiku 5.5, 3 ejecuciones por variante (`--repeat 3`), 0,01–0,03 $ por ejecución y ~0,25 $ en total:

| Variante | Señal observada (3 ejecuciones) | Qué dice |
| :--- | :--- | :--- |
| correcta | 2–3 consultas a la fuente que falla (1–2 reintentos locales) y 1 a cada una de las demás; 1 delegación del coordinador en las 3; informe `failed` con `error_context` completo en 2 de 3 (en la otra el subagente no devolvió JSON y la medida no ve informe); brecha anotada y cifras de las fuentes sanas en 3 de 3 | el fallo llega con su contexto y la cobertura queda dicha |
| `generico` | `failed` sin `error_context` en 3 de 3; **el coordinador volvió a delegar en 3 de 3** («Reintentar SRC-MONITOR»), con el mismo *timeout*, y en 1 intentó consultar él mismo (la barrera lo denegó); brecha anotada y cifras sanas en 3 de 3; coste de 0,026–0,030 $ frente a 0,022–0,024 $ | sin contexto el coordinador reintenta a ciegas: repite lo que el subagente ya había intentado. El resultado final sigue anotando la brecha: las alternativas que da las pone él, no salen de lo intentado |
| `silenciar` | el *handler* tragó el fallo en 3 de 3 (la fuente llegó como `total: 0`, 1 sola consulta, sin reintentos); **la brecha no se anotó en ninguna**: las dos fuentes vacías se describen como «respondieron sin contenido» o «no dieron error» | el coordinador no puede distinguir un fallo de un vacío legítimo: un hecho falso («no dio error») entra en el informe |
| `abortar` | `INVESTIGACIÓN ABORTADA`, sin cifras, en 3 de 3, con tres fuentes respondidas y el fallo bien informado | un fallo tumba el trabajo de las fuentes que sí respondieron |

Notas:

- **`silenciar` por prompt (versión anterior, sin variante propia):** cuando era el prompt del investigador el que pedía ocultar el fallo, el informe JSON del subagente daba la fuente por `ok` con `findings` vacío, pero **el resultado final anotó la brecha igualmente en las 7 ejecuciones**. En una ejecución diagnóstica se vio el motivo probable: el coordinador, al escribir el prompt de la delegación, le pidió al subagente «si una fuente falla o está vacía, dilo explícitamente», y el subagente lo cumplió en prosa fuera del JSON. La instrucción de la delegación manda sobre la definición del subagente, así que un prompt no basta para que el vacío oculte el fallo. Con el vacío producido por el código (la variante actual), el fallo no se puede contar porque el subagente no lo ve: la señal aparece donde el prompt no la daba.
- **Decisión del coordinador en `generico`:** `coordinator_delegations` cuenta las delegaciones del coordinador; con la correcta es 1 en las 3 ejecuciones y con `generico`, 2 en las 3. La medida «alternativa o reintento mencionados» es laxa (palabras sueltas) y dio verdadera también en `silenciar`, donde el coordinador sugiere reconsultar las fuentes vacías por prudencia; la comprobación fiable de la brecha es «brecha anotada» (la fuente y una palabra de falta en la misma frase).
- **Reintento local:** en la ejecución correcta el subagente hizo 2 reintentos (3 consultas); los reintentos locales no cuentan como errores del coordinador (`coordinator_errors` = 0).
- Las medidas, la forma del contexto de error y las opciones se prueban sin modelo en `tests/test_app3_04_errores_entre_agentes.py`.
</details>

### Pregunta tipo examen

Un subagente de búsqueda agota sus reintentos con una fuente que da *timeout*, mientras que otras tres fuentes han respondido bien. ¿Qué debe ocurrir a partir de ahí?

- A. El subagente devuelve un resultado vacío para esa fuente, para que el coordinador continúe sin interrumpir el flujo.
- B. El subagente devuelve el tipo de fallo, qué intentó, lo parcial y alternativas, y el coordinador entrega lo obtenido anotando la brecha.
- C. El subagente propaga la excepción para que el coordinador cancele toda la investigación y la relance cuando la fuente se recupere.
- D. El subagente reintenta sin límite hasta que la fuente responda, para no entregar nunca un informe sin esa fuente.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** Tras recuperar en local lo transitorio, el subagente no oculta el fallo: devuelve el contexto estructurado (tipo, intento, resultados parciales y alternativas) y el coordinador, que gestiona los errores, entrega un resultado parcial con la cobertura anotada (TS 5.3, TS 2.2-S3). A confunde un fallo de acceso con un resultado vacío válido; C tira el trabajo de las fuentes que sí respondieron; D no acota el reintento y bloquea la entrega.
</details>

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 05 · Procedencia entre agentes

<!-- BORRADOR (Sonnet 5.5): pendiente del pase de textos de Opus 5.5 (cabecera del módulo, predicciones y pregunta). -->

> **Qué vas a hacer:** Ver si la fuente y la fecha de cada cifra llegan hasta el informe final cuando dos fuentes discrepan, y si un hallazgo clave se pierde en mitad de un texto largo.
>
> **Necesitas antes:** El [módulo 04](#04--errores-entre-agentes) (mismo servidor de fuentes) y el [módulo 03](#03--tools-entre-roles) (mismo patrón de coordinador y barrera).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar; lo medido está en el Paso 3).

### Antes de empezar

Los términos comunes (coordinador, subagente, procedencia) están en el [glosario](../docs/glosario.md).

- **El sistema:** el coordinador tiene dos subagentes: `researcher` (consulta las fuentes con `query_source`) y `synthesizer` (sin tools, redacta con lo que le pasen en el prompt). Las fuentes son las sintéticas de `fuentes_investigacion.json`.
- **Parte `conflictos` (por defecto):** cuatro fuentes. Todas coinciden en el total de tickets cerrados, pero dan cifras distintas para el tiempo medio de resolución y para la satisfacción, cada una con su fecha de publicación. La petición no lo dice.
- **Afirmación estructurada:** el investigador devuelve una lista JSON donde cada afirmación separa el contenido (`claim`, `figure`, `unit`) de los metadatos (`source_id`, `published_at`). El código comprueba esa forma y que la fecha coincide con la de la fuente.
- **Parte `medio`:** el informe `SRC-LARGO` (unas 1.500 palabras) con una sola frase importante en mitad. `--texto con_resumen` hace que el servidor anteponga al informe una línea con ese hallazgo, sin quitarlo de su sitio.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `query_source` | `source_id` | igual que en el [módulo 04](#04--errores-entre-agentes): el informe en `content` y su id, nombre y fecha en `metadata` |

### El ejercicio

Qué cambia en el código de cada variante:

- **`sin_procedencia`:** el prompt del investigador le pide un párrafo en prosa por fuente, en vez de afirmaciones con metadatos.
- **`promedio`:** el prompt del sintetizador le pide una única cifra consolidada, el promedio, cuando dos fuentes discrepan.
- **`--parte medio --texto sin_resumen|con_resumen`:** el mismo informe largo, sin o con la línea de resumen al principio.

El código mide sin modelo cuántas cifras del informe llevan su fuente en la misma frase o fila, si algún conflicto aparece fusionado en un promedio y si el resumen del informe largo cita el hallazgo clave.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

1. En la configuración correcta, ¿qué parte de la procedencia está garantizada por la estructura de lo que devuelve el investigador y qué parte depende de lo que escriba el sintetizador?
2. Con `--anti sin_procedencia`, ¿qué sabe el sintetizador de cada cifra? ¿Dónde esperas ver el daño: en lo que devuelve el investigador, en el informe final o en ambos? Razónalo antes de ejecutar.
3. Con `--anti promedio`, ¿qué cifras tendrá el informe que no sale en ninguna fuente? ¿Seguirán apareciendo también las cifras originales?
4. En la parte `medio`, ¿qué cambia al anteponer una línea de resumen? ¿Esperas la misma diferencia con un informe mucho más largo que con uno de unas 1.500 palabras?

### Ejecutar

```bash
uv run python app3_sistema_multiagente/05_procedencia.py                                        # correcta
uv run python app3_sistema_multiagente/05_procedencia.py --anti sin_procedencia                 # el investigador devuelve prosa
uv run python app3_sistema_multiagente/05_procedencia.py --anti promedio                        # cifras en conflicto fusionadas
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio                          # hallazgo en mitad, sin resumen
uv run python app3_sistema_multiagente/05_procedencia.py --parte medio --texto con_resumen      # con la línea de resumen al principio
```

**Si ejecutas:** las medidas (comprobador de procedencia, detector de cifras fusionadas, forma de las afirmaciones) se prueban sin modelo; ejecutar sirve para ver qué hace el modelo con ellas.

### Qué observar

Las afirmaciones estructuradas sin problemas, las fuentes que llegan al sintetizador, las cifras con su fuente en la frase, los conflictos presentados como disputados, las cifras fusionadas y, en la parte `medio`, si el resumen cita el hallazgo clave.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Coordinador Sonnet 5.5, subagentes Haiku 5.5, ~0,04–0,06 $ por ejecución:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta (1 ejecución) | 10 de 10 afirmaciones sin problemas, las 4 fuentes llegan al sintetizador, 5 de 5 cifras con su fuente en la frase, los 2 conflictos como disputados, ningún promedio y las cifras en tabla | la estructura conserva la procedencia y el informe separa lo establecido de lo disputado |
| `promedio` (1 ejecución) | **fusionó los dos conflictos**: 22 horas y 3,85 sobre 5, que ninguna fuente dice; ningún conflicto presentado como disputado, aunque las cifras originales siguieron apareciendo con su fuente | señal clara del anti-patrón |
| `sin_procedencia` (4 ejecuciones) | **0 afirmaciones estructuradas** en las 4; pero el informe final llevó la fuente en la frase en 5 de 5 cifras en 3 ejecuciones y en 4 de 5 en la otra | la señal aparece en lo que devuelve el investigador, **no en el informe final** (ver notas) |
| `medio` sin resumen (3) y con resumen (3) | el resumen citó el 41 % en **6 de 6** | **sin señal**: el informe de ~9.400 caracteres no basta para que se pierda |

Notas:

- **`sin_procedencia`:** con Haiku 5.5 la prosa del investigador ya traía el nombre de cada fuente y su fecha, y el sintetizador la reprodujo. La estructura se pierde, pero la procedencia no se perdió en el informe final (salvo una cifra en una ejecución). No se fuerza: se documenta.
- **`promedio`:** el informe también lista las cifras originales con su fuente, así que `figures_with_source` no baja. La señal está en `merged_figures` y en `conflicts_presented`.
- **Parte `medio`:** la señal de *lost in the middle* no apareció con ~1.500 palabras y Haiku 5.5. Que aparezca con un texto mucho más largo es una hipótesis sin comprobar; no se alargó el informe para forzarla.
- `conflicts_presented` es una comprobación laxa: pide las dos cifras y una palabra de desacuerdo en cualquier parte del texto.
- Las medidas, la forma de las afirmaciones y las opciones se prueban sin modelo en `tests/test_app3_05_procedencia.py`.
</details>

### Pregunta tipo examen

Dos fuentes dan cifras distintas para el mismo dato, cada una con su fecha. El informe final debe ser claro para quien lo lea y poder rastrearse hasta sus fuentes. ¿Qué diseño es el más adecuado?

- A. Cada subagente resume en prosa lo que encuentra, y el sintetizador deduce por el contexto de qué fuente viene cada cifra.
- B. El sintetizador calcula el promedio de las dos cifras para dar una sola, y cita las dos fuentes al lado de ese número.
- C. El sintetizador conserva solo la cifra de la fuente más reciente y omite la otra, para que el informe no confunda.
- D. Cada subagente devuelve afirmaciones con fuente y fecha aparte del contenido, y el sintetizador muestra ambas cifras como disputadas.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** La procedencia se conserva si el subagente devuelve datos estructurados con el contenido separado de los metadatos y el sintetizador mantiene el mapeo afirmación–fuente (TS 1.3-S2, TS 5.6); las cifras en conflicto se presentan las dos, con su fuente y su fecha, y lo disputado se separa de lo establecido (TS 5.6). A pierde la fuente en el primer salto; B crea una cifra que ninguna fuente respalda; C descarta una fuente sin decirlo.
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
  - **Forma frente a fondo:** que el JSON cumpla el esquema (forma, «sintaxis») no quiere decir que sus valores sean los de la etiqueta (fondo, «semántica»). El módulo mide las dos cosas por separado.
  - **Campo inventado:** uno que la etiqueta dice que no está en el documento y para el que el modelo devuelve algo distinto de `null` (incluidos `'null'` como texto, `''` o un valor deducido).

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `extract_metadata` | el documento (en el mensaje) | la extracción: `doc_type`, `doc_type_detail`, proveedor, número, fecha, pedido, moneda, total declarado y líneas |
| `extract_invoice`, `extract_delivery_note`, `extract_other` | el documento | una tool por tipo, con los campos de ese tipo (solo en `--parte tipo_desconocido`) |
| `lookup_purchase_order` | `po_number` (`PO-nnnn`) | proveedor, estado e importe esperado del pedido, leídos de `pedidos_compra.json`, o un error si no existe (solo en `--parte enriquecimiento`) |

Las tools de extracción no hacen nada: lo que importa es lo que el modelo escribe en su entrada, que el módulo compara con la etiqueta. `lookup_purchase_order` sí devuelve datos, y su resultado vuelve al modelo como `tool_result`.

### El ejercicio

Cuatro partes (`--parte`) y variantes `--anti` en la primera y en la última:

- **`forzada`:** `tool_choice` forzado a `extract_metadata`. La versión correcta tiene los campos opcionales *nullable*, el `enum` con `other` y `unclear`, y las reglas de formato (fecha ISO, número con punto decimal) en la descripción. `--anti sin_nullable` hace obligatorios todos los campos y quita `null` de los tipos. `--anti enum_cerrado` deja el `enum` solo con `invoice` y `delivery_note`.
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

### Ejecutar

```bash
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada                          # correcta
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada --anti sin_nullable      # todo obligatorio
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada --anti enum_cerrado      # enum sin other ni unclear
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte tipo_desconocido
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte few_shot --rol-modelo enforcement --repeat 3
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte enriquecimiento --repeat 3                          # extracción forzada y después auto
uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte enriquecimiento --anti auto_desde_inicio --repeat 3  # auto desde el primer turno
```

**Si ejecutas:** la construcción del esquema por variante, el validador de forma y la puntuación contra etiquetas se prueban sin modelo; ejecutar sirve para ver qué hace de verdad el modelo con un campo que no puede rellenar. Cada ejecución cuesta menos de 0,05 $ con Haiku 5.5 (`few_shot` y `enriquecimiento` con `--repeat 3`: unos 0,03–0,04 $); con Haiku 4.5 y `--repeat 3`, `few_shot` cuesta unos 0,23 $ y `enriquecimiento`, unos 0,24 $.

### Qué observar

En cada ejecución, `forma válida`, `campos ausentes rellenados`, `tipo correcto`, `fuera del enum` y `valores incorrectos`; en `tipo_desconocido`, qué tool eligió el modelo para cada documento; en `few_shot`, fechas incorrectas, faltantes e inventados con y sin ejemplos; en `enriquecimiento`, el orden de las tools por documento, las consultas antes de extraer, los números que no salen del documento y si el resultado final usa el pedido extraído.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Haiku 5.5 (rol `agent`), 12 documentos, tres repeticiones salvo donde se dice:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `forzada`, correcta | forma válida 12/12, tipo correcto 12/12, campos ausentes rellenados 1/21 en 3 repeticiones y 2/21 en otra ejecución (siempre el total de un presupuesto, deducido de su única línea), líneas correctas 11/12 | con el campo *nullable* el modelo devuelve `null` casi siempre |
| `forzada`, `sin_nullable` | campos ausentes rellenados **21/21**, forma válida **6/12** | con campos obligatorios inventa: `'null'` como texto, `''`, un valor deducido; los que usan `'null'` en un campo numérico ni siquiera cumplen el esquema |
| `forzada`, `enum_cerrado` | tipo correcto 11/12, **2 de 12 con un tipo fuera del `enum`** (`other` en la garantía y el presupuesto), el ilegible forzado a `invoice` | el modelo escribe `other` aunque no esté en el `enum`: un esquema no se impone solo, el validador de forma lo detecta |
| `tipo_desconocido` | `any`: la tool de su tipo en 12/12 (3 repeticiones); `auto`: igual; **forzada a factura: 5/12**, los otros 7 se tratan como factura | forzar una tool trata como factura todo lo que no lo es; `any` deja elegir |
| `few_shot` con Haiku 5.5 | 0 fechas incorrectas con y sin ejemplos; faltantes 0 en las seis ejecuciones; inventados 0–1 de 21 (un `stated_total` en `DC-11`, o un número en `DC-07` sin ejemplos) | **sin señal**: este modelo ya escribe la fecha en ISO sin que nadie se lo pida y no deja vacío ningún campo con valor |
| `few_shot` con Haiku 4.5 (`--rol-modelo enforcement`, 3 repeticiones, ~0,23 $) | sin ejemplos: **5, 6 y 6 fechas incorrectas** de 12, líneas correctas 10/12; con ejemplos: **0, 0 y 0**, líneas correctas 11/12. Faltantes 0 y inventados 2/21 (`DC-11`: fecha y total) en las seis ejecuciones | los ejemplos de las tres formas arreglan el formato que la descripción no dice; **no** cambian los campos faltantes (ya eran 0) ni los inventados |
| `enriquecimiento`, correcta (Haiku 5.5, 3 repeticiones, ~0,04 $) | extracción primero en 36/36; consulta antes de extraer 0/12 en cada repetición; número ajeno al documento 0; el resultado final usa el pedido extraído en 8, 6 y 7 de 12 (en los demás o no hay pedido que consultar o el modelo no lo consulta) | el primer turno forzado asegura el orden, pero la consulta posterior no siempre se hace |
| `enriquecimiento`, `auto_desde_inicio` (Haiku 5.5 y Haiku 4.5, 3 repeticiones cada uno) | consulta antes de extraer **0/12** y número ajeno al documento **0** con los dos modelos; el resultado final usa el pedido extraído en 7/12 (Haiku 5.5) y 9/12 (Haiku 4.5), igual que con el primer turno forzado | **sin señal**: con `auto`, ambos modelos extraen primero por su cuenta. Que lo hagan hoy no garantiza el orden |

Notas:

- **Forma y fondo:** `DC-06` (el certificado de garantía) sale en las tres repeticiones con una línea inventada (el modelo cuenta la garantía como un artículo), con la forma válida. El esquema lo deja pasar; la etiqueta, no.
- **El `enum` no se impone:** que el modelo devuelva un valor que no está en el `enum` no es un error de la API. El modo estricto lo evitaría, pero la guía no lo nombra y el repositorio no lo usa.
- **El anti de `enriquecimiento` no se nota:** se probó con Haiku 5.5 y con Haiku 4.5 y no hay diferencia entre forzar el primer turno y no hacerlo. Lo que hace el forzado es garantizar el orden por construcción; no se ha podido mostrar el fallo que evita.
- **El identificador de la petición:** en una primera versión de la sonda el prompt llevaba «Documento DC-07:» y el modelo lo copió como `document_number`. El prompt ya no lleva el identificador.
- Detalle y coste de las sondas: `docs/hallazgos.md`. Lo que no depende del modelo (esquemas, validador, puntuación, petición por modo y ejemplos) se prueba en `tests/test_app3_07_extraccion_schema.py`.
</details>

### Pregunta tipo examen

Un proceso extrae con una tool de JSON Schema el número de pedido, la fecha y el total de miles de facturas. Todas las respuestas son JSON válido. Sin embargo, una auditoría encuentra números de pedido plausibles que no existen, siempre en facturas que no citan ninguno. En el esquema, el campo es `string` y figura en `required`. ¿Qué cambio ataca la causa?

- A. Añadir al *system prompt* «no inventes datos» y conservar el campo como `string` obligatorio.
- B. Validar el número con una expresión regular `PO-nnnn` y reenviar al modelo las facturas que fallen.
- C. Pasar a `tool_choice` `auto`, para que el modelo pueda contestar en texto cuando le falte el dato.
- D. Hacer el campo opcional y *nullable*, y decir en su descripción que quede en `null` si no figura.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** Un campo obligatorio que el documento puede no traer obliga al modelo a fabricar un valor para cumplir el esquema. La forma de decir «puede no estar» es declararlo opcional y *nullable* (TS 4.3-K4, S4). Que todo el JSON sea válido no prueba nada: el esquema elimina los errores de sintaxis, no los de significado (TS 4.3-K3).

- **A** pide por escrito lo contrario de lo que exige el esquema, y gana el esquema.
- **B** no detecta el problema: el número inventado tiene el formato correcto y pasa la expresión regular. Además, reintentar no sirve cuando el dato no está en el documento (módulo 08).
- **C** sacrifica la garantía de salida estructurada (TS 4.3-K2) para resolver algo que el esquema resuelve por sí solo.
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
