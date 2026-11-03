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
| `04_errores_entre_agentes.py` … `06_contexto_largo.py` | D1, D2 y D5 | 3 |
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

## 07 · Extracción estructurada con schema

> **Qué vas a hacer:** Extraer los metadatos de 12 documentos de compra con una tool de JSON Schema y puntuar lo que sale contra unas etiquetas que el modelo no ve.
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

La tool no hace nada: lo que importa es lo que el modelo escribe en su entrada, que el módulo compara con la etiqueta.

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
4. La parte `few_shot` quita de las descripciones la regla de cómo escribir una fecha. ¿Qué tendría que ocurrir sin ejemplos para que los ejemplos se notaran? ¿Esperas lo mismo con dos modelos distintos?

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

En cada ejecución, `forma válida`, `campos ausentes rellenados`, `tipo correcto`, `fuera del enum` y `valores incorrectos`; en `tipo_desconocido`, qué tool eligió el modelo para cada documento.

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
| `enriquecimiento`, `auto_desde_inicio` (Haiku 5.5 y Haiku 4.5, 3 repeticiones cada uno) | consulta antes de extraer **0/12** y número ajeno al documento **0** con los dos modelos; el resultado final usa el pedido extraído en 7/12 (Haiku 5.5) y 9/12 (Haiku 4.5), igual que con el primer turno forzado | **sin señal**: con `auto`, ambos extraen primero porque el prompt lo pide así. Que el modelo lo haga hoy no garantiza el orden |

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

- **El sistema:** por cada documento, una extracción, una validación con reglas de código (sin modelo) y, si falla, un reintento. Las reglas: el tipo está en el `enum`, la fecha es ISO, una factura cita su número de pedido (`PO-nnnn`) y el total que declara el documento coincide con la suma de sus líneas. El esquema de la tool no dice cómo se escribe una fecha: esa regla solo la aplica el validador.
- **Qué modelo:** el rol `enforcement` (Haiku 4.5), un modelo anterior al de los demás módulos. El porqué está en el Paso 3. `--rol-modelo agent` ejecuta el módulo con Haiku 5.5.
- **Términos propios:**
  - **Reintento:** enviar de nuevo al modelo su propia llamada fallida, con el error devuelto como resultado de la tool (`is_error`), y pedirle otra extracción.
  - **Error concreto:** el mensaje del reintento nombra el campo, el valor que devolvió y la regla que incumple. Un error **genérico** solo dice «Inténtalo de nuevo».
  - **Patrón de fallo:** la causa de un fallo (`date_format`, `missing_required`, `total_mismatch`…). Se anota en cada fallo, y la salida los agrupa por causa. El `detected_pattern` de la guía, sobre los hallazgos de revisión que se descartan, llega en el módulo 11.
  - **`conflict_detected`:** el total calculado no coincide con el declarado y, tras un reintento, sigue sin coincidir: el documento mismo no cuadra.
  - **Dato ausente en la fuente:** que el documento no contiene lo que la regla exige (una factura sin número de pedido). El código lo comprueba con una búsqueda en el texto, sin modelo.
  - **Efecto de un reintento** (solo para medir; el bucle no ve las etiquetas): *corregido* si el fallo desaparece y el valor coincide con la etiqueta, *persiste* si el fallo sigue, *inventado* si desaparece pero el valor no es el de la etiqueta (o la etiqueta dice que no existe).

### El ejercicio

Lo que cambia en el código de cada variante (el esquema, los documentos y el validador son los mismos):

- **Correcta:** el reintento lleva el error concreto. Si la regla exige un dato que no aparece en el documento, no se reintenta y el campo queda marcado. Un total que no cuadra se reintenta una vez y, si sigue sin cuadrar, se marca `conflict_detected`. Hay un tope de 2 reintentos como red de seguridad.
- **`--anti reintento_generico`:** el mensaje del reintento es «Inténtalo de nuevo.», sin más. Todo lo demás es igual.
- **`--anti insistir`:** se reintenta con el error concreto también cuando el dato no está en el documento y no se marca nada; el tope sube a 4.

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
uv run python app3_sistema_multiagente/08_validacion_reintento.py --anti insistir            # reintenta aunque no exista el dato
uv run python app3_sistema_multiagente/08_validacion_reintento.py --repeat 3                 # cifras más estables
uv run python app3_sistema_multiagente/08_validacion_reintento.py --rol-modelo agent         # con Haiku 5.5 no hay qué reintentar
```

**Si ejecutas:** el validador, los mensajes, la decisión de reintento y el bucle (con un modelo simulado) se prueban sin modelo. Ejecutar es obligatorio porque la lección es lo que el modelo hace con el reintento: corregir, repetir el error o inventar. Cada ejecución cuesta unos 0,05–0,07 $ (tope 0,50 $ de `--budget`; con `--repeat 3`, unos 0,15–0,18 $).

### Qué observar

Por documento, los fallos del primer intento agrupados por patrón, los reintentos y el efecto de cada uno; al final, reintentos útiles, inútiles e inventados, marcados sin dato, conflictos y el coste de los reintentos.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Haiku 4.5 (rol `enforcement`), 12 documentos, tres repeticiones:

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | **5–6 fechas mal** en los primeros intentos y 5 reintentos de fecha corregidos en cada repetición; la factura sin pedido se **marca sin reintentar** (0 reintentos, 3 de 3); 1 conflicto marcado en 2 repeticiones; coste de los reintentos ~0,014–0,017 $ | con el error concreto, el reintento corrige lo que el documento sí contiene |
| `reintento_generico` | 6 fechas mal; **10, 10 y 9 reintentos con solo 2–3 útiles**; 2 conflictos; coste ~0,025–0,028 $ | sin saber qué falló, el modelo repite la misma fecha; el doble de reintentos y de coste para casi el mismo resultado |
| `insistir` | la factura sin pedido se reintenta 2–3 veces y **acaba con un pedido inventado en las 3 repeticiones**; reintentos «inventaron» 3, 5 y 3; ningún campo marcado | el valor falso pasa el validador (tiene el formato `PO-nnnn`): solo la etiqueta lo delata |

Notas:

- **Un reintento puede empeorar un total:** en la correcta, de los dos documentos con el total mal, el modelo cambió el total declarado para que cuadrara con las líneas (*inventado*) en al menos uno de ellos en las tres repeticiones, y solo en dos de ellas quedó un conflicto marcado. Un total que no cuadra por culpa del documento no se arregla con un reintento: pedírselo invita a falsear el dato. Por eso el conflicto se marca tras un solo reintento y en producción sería mejor no reintentarlo.
- **Qué mide cada línea:** el validador de formato no distingue un pedido real de uno inventado con la forma correcta. «Inventaron» sale de comparar con la etiqueta, que el bucle no ve.
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
  - **Troceo (*chunking*):** partir un documento largo en trozos, cada uno con su cabecera, para que cada respuesta quepa.
  - **Ventana y SLA:** el plazo en el que se necesita el resultado (SLA) frente a las 24 h que puede tardar un lote (ventana).
- **Lo que el módulo no guarda:** nada. El identificador del lote lo copias tú de la salida y lo pasas a `--batch-id`.
- **Sin varios turnos:** cada petición del lote es una sola vuelta. Dentro de un lote no se puede devolver el resultado de una tool y continuar la conversación.

### El ejercicio

Opciones del módulo (cada una es un paso del flujo):

- **`--ventanas`:** sin modelo. Reparte seis trabajos de ejemplo entre tres grupos según su plazo: «cabe en batch», «cabe en batch, sin margen para reenviar fallidos» y «tiene que ir síncrono». Para los que caben, dice además cada cuántas horas hay que enviar un lote.
  - **El criterio:** cuenta todo lo que puede esperar un documento hasta tener su resultado, más un margen de 2 h elegido en este módulo (la guía no habla de margen). La fórmula está en el Paso 3: intenta deducirla antes.
- **`--enviar`:** estima una cota superior del coste, hace una **muestra síncrona** de tres documentos con los mismos parámetros, y solo si cumplen el esquema crea el lote. Imprime su identificador. `--sin-muestra` salta la muestra.
- **`--batch-id <id>`:** consulta el estado del lote y, si ha terminado, lee los resultados: orden de llegada, tipo de cada resultado, emparejado por `custom_id` y coste con el descuento. `--esperar <s>` espera hasta ese número de segundos. `--reenviar` crea un lote nuevo solo con los fallidos (los truncados, partidos en trozos).
- **`--anti por_orden`** (con `--batch-id`): empareja los resultados por posición en vez de por `custom_id`.

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
uv run python app3_sistema_multiagente/09_batches.py --enviar                         # muestra síncrona y lote; copia el id
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --esperar 120    # estado y resultados
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --reenviar       # reenvía los fallidos (troceando)
uv run python app3_sistema_multiagente/09_batches.py --batch-id <id> --anti por_orden # emparejado por posición
```

**Si ejecutas:** la construcción del lote, el emparejado, la clasificación de resultados, el troceo, la ventana frente a SLA y los costes se prueban sin modelo. Ejecutar sirve para ver el orden real de llegada y las respuestas truncadas, que no se pueden deducir leyendo el código. Todo el flujo (muestra, tres lotes y lecturas) costó menos de 0,01 $.

### Qué observar

El orden de llegada frente al de envío, los tipos de resultado (qué cuenta como `ok` y qué como `truncated`), los documentos con datos de otro según el emparejado, y el coste del lote frente al del mismo trabajo síncrono.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Haiku 5.5, 12 documentos:

| Paso | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `--ventanas` | 3 trabajos en batch (72 h y los dos sin plazo), 1 en batch **sin margen** (30 h), 2 síncronos (8 h y 0,1 h). Frecuencia: el de 72 h, **cada 46 h** (cada 22 h si se reenvía); el de 30 h, **cada 4 h** y sin reenvío | el plazo tiene que cubrir la espera al siguiente envío además de la ventana; con 30 h sale el ejemplo de la guía, pero no queda tiempo para recuperar un fallo |
| `--enviar` | estimación (cota superior) 0,0023 $; muestra síncrona de 3 documentos con forma válida (0,0008 $); lote creado con 12 peticiones | la muestra es lo único que se ve antes de gastar en el lote |
| Lectura | el lote estaba terminado al leerlo (unos minutos como mucho, nunca cerca de las 24 h); **llegaron en otro orden** (`DC-12, DC-09, DC-03, DC-06, …`); 11 `ok` y **1 `truncated`** (`DC-12`) aunque la API los daba todos por `succeeded`; coste 0,0017 $ (0,0033 $ síncrono) | el orden no es el de envío y el fallo está en el `stop_reason` |
| `--anti por_orden` | con el emparejado por posición, **9 de 12** documentos reciben los datos de otro; por `custom_id`, ninguno | el emparejado por posición solo acierta por casualidad |
| Reenvío del truncado | 4 trozos de 10 líneas: **3 correctos y 1 truncado otra vez** (`DC-12--c3`); segundo reenvío con trozos de 5 líneas: 8 de 8 correctos y las 40 líneas unidas coinciden con la etiqueta; 0,0008 y 0,0013 $ | un trozo grande también puede truncarse: el documento entero se parte entonces en trozos más pequeños |

Notas:

- **La fórmula de `--ventanas`:** un documento que llega justo después de un envío espera un intervalo entero hasta el siguiente. Después, el lote puede tardar la ventana completa, y otra más por cada reenvío. Por eso tiene que cumplirse `intervalo + 24 h × (1 + reenvíos) + margen ≤ plazo`. **El margen de 2 h es una elección de este módulo:** la guía da el resultado (enviar cada 4 h para un SLA de 30 h), pero no el cálculo. Sin margen saldrían 6 h.
- **La API no marca la respuesta truncada como error:** devuelve `succeeded` con `stop_reason: max_tokens` y un `tool_use` incompleto (en la sonda, sin `line_items`). Quien solo mire el tipo de resultado da por buena una extracción cortada.
- **El tope de coste de un lote no se puede imponer a mitad:** la Batches API no tiene un corte como `max_budget_usd`. Por eso el módulo estima una cota superior antes de enviar y se niega si supera el tope.
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
