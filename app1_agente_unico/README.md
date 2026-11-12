# app1 · Agente único

Un agente, sus tools y su bucle: la base sobre la que se apoyan app2 y app3. El dominio es una mesa de ayuda TI con datos sintéticos (`datos/sinteticos/`).

Términos: [glosario común](../docs/glosario.md).

## Ruta de lectura

Cada módulo se hace en 5 pasos: orientarte con su ficha, predecir, ejecutar o no según su **Modo** y contrastar, responder la pregunta y anotar tus fallos en `FALLOS.md`. Si es tu primera vez, lee antes [Empieza aquí](../README.md#empieza-aquí).

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_bucle_manual.py`](01_bucle_manual.py) | TS 1.1-K1, K2, K3, S1, S2, S3 · TS 5.1-K4 | 1 |
| [`02_tools_integradas.py`](02_tools_integradas.py) | TS 2.5-K1, K2, K3, K4, S1, S2, S3, S4, S5 | 2 |
| [`03_servidor_mcp.py`](03_servidor_mcp.py) | TS 2.1-K1, K2, K3, K4, S1, S2, S3, S4 | 2 |
| [`04_errores_estructurados.py`](04_errores_estructurados.py) | TS 2.2-K1, K2, K3, K4, S1, S2, S4 | 2 |
| [`05_scoping_y_tool_choice.py`](05_scoping_y_tool_choice.py) | TS 2.3-K1, K4, S4, S5 | 2 |
| [`06_mcp_config.py`](06_mcp_config.py) | TS 2.4-K1, K2, K3, K4, S1, S2, S3, S4, S5 | 2 |
| [`07_recorte_de_contexto.py`](07_recorte_de_contexto.py) | TS 5.1-K3, S3 | 3 |

---

## 01 · Bucle manual

> **Qué vas a hacer:** Ver cómo un bucle escrito a mano decide cuándo seguir pidiendo tools y cuándo parar, y qué rompe cada variante construida mal.
>
> **Necesitas antes:** Nada; es el primer módulo.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md#el-agente-y-su-bucle): Messages API, tool, bucle agéntico, iteración, `stop_reason`, historial. Lo propio de este módulo:

- **El sistema:** un agente de mesa de ayuda TI con datos sintéticos. Recibe un ticket y tiene que redactar una respuesta. El modelo no toca los datos: solo puede pedirle al código que ejecute *tools*.

### Las tres tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `get_ticket` | `ticket_id` (formato `TCK-NNNN`) | El ticket: descripción, categoría, estado, fecha y `user_id` (`null` si quien escribe no está identificado). Si no existe, un error. |
| `get_user` | `user_id` (formato `EMP-NNNN`) o `name` (nombre y apellido) | Todos los empleados que coinciden. Con un nombre puede haber varios. Sin ninguno de los dos datos, o sin coincidencias, un error. |
| `search_kb` | `query` (palabras clave) | Hasta 3 artículos de la base de conocimiento (*KB*, los procedimientos de la mesa de ayuda) con ID, título y texto, y el ID del artículo que lo sustituye si está obsoleto. |

### El ejercicio

El agente atiende el ticket ambiguo «Soy Laura Gómez y necesito que me restablezcáis la contraseña», que no trae `user_id`. Hay dos empleadas con ese nombre, así que lo razonable es leer el ticket, buscar a la persona, consultar la base de conocimiento y pedir un identificador.

La **variante base** (sin `--anti`) es el bucle construido como pide la guía; cuándo sigue y cuándo para es parte de lo que vas a predecir. Además trae cinco variantes construidas mal a propósito (`--anti`), para ver cómo falla cada error. Esto es lo que cambia en el código de cada una:

- **`texto`:** el bucle para la primera vez que el texto de la respuesta contiene «terminado», «listo» o «hecho».
- **`texto_asistente`:** el bucle para en cuanto una respuesta trae un bloque de texto, pida o no una tool.
- **`tope`:** un tope de 2 iteraciones. El bucle se corta tras la segunda vuelta, pase lo que pase, aunque el modelo siga pidiendo tools.
- **`sin_historial`:** en cada petición solo se envía el mensaje inicial, sin los resultados de las tools anteriores.
- **`arbol_fijo`:** un «árbol de decisión» fijo, es decir, una secuencia de pasos que decide el código y no el modelo. No hay bucle: el código llama siempre a `get_ticket`, `get_user` y `search_kb`, en ese orden y con los datos del ticket, y después pide una sola respuesta al modelo.

La salida muestra la credencial detectada y las versiones, el modelo y el presupuesto con su origen, cada iteración con su `stop_reason` y sus tools, y la causa de la parada.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Una respuesta del modelo puede traer texto («voy a mirar el ticket») y, además, la petición de una tool. ¿Debe el bucle parar al ver ese texto? ¿Qué tiene que mirar para decidirlo?
2. (módulo) De `get_ticket`, `get_user` y `search_kb`, ¿cuáles necesitan el resultado de otra y cuáles podrían pedirse a la vez, en una misma iteración?
3. (módulo) En la variante base, ¿esperas el mismo número de iteraciones en todas las ejecuciones? ¿De qué depende?
4. (guía) Sea cual sea el número de iteraciones de la variante base, ¿qué tendrá la última que no tenga ninguna de las anteriores?
5. (guía) Con `tope` (el bucle se corta tras 2 iteraciones), ¿qué trabajo queda sin hacer? ¿Para qué sirve entonces un tope de iteraciones?
6. (guía) Con `sin_historial` (cada petición lleva solo el mensaje inicial), ¿qué pedirá el modelo en cada iteración y por qué?
7. (guía) Con `arbol_fijo` (el código llama siempre a las tres tools, en orden y con los datos del ticket, que no trae `user_id`), ¿qué paso falla? ¿Qué podría hacer el modelo ante ese fallo que la secuencia fija no puede?

### Ejecutar

```bash
uv run python app1_agente_unico/01_bucle_manual.py                  # variante base
uv run python app1_agente_unico/01_bucle_manual.py --anti tope      # o texto, texto_asistente, sin_historial, arbol_fijo
uv run python app1_agente_unico/01_bucle_manual.py --budget 0.05    # prueba barata (el tope solo baja)
```

**Si ejecutas:** las variantes se prueban de forma determinista sin modelo (`tests/test_app1_01_bucle_manual.py`); ejecutar sirve para ver el bucle con tu modelo.

### Qué observar

La causa de la parada de cada variante y, en la base, cuántas iteraciones hubo y qué tools se pidieron en cada una.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** No. El texto que acompaña a un `tool_use` es un comentario, no la respuesta final. El bucle mira `stop_reason`: sigue con `"tool_use"` y para con `"end_turn"` (TS 1.1-K1, 1.1-S1, 1.1-S3). Es lo que rompen `texto` y `texto_asistente`.
- **P2** `get_user` depende de `get_ticket`, porque hasta leer el ticket no se sabe de quién se trata. `search_kb` no depende de ninguna: puede ir con cualquiera de las dos o al final.
- **P3** No: varía entre 2 y 4. Depende de qué llamadas independientes agrupe el modelo en una misma iteración, y eso lo decide él.
- **P4** Trae `end_turn` y ninguna petición de tool (TS 1.1-K1).
- **P5** Si el modelo necesita más de dos iteraciones, el bucle se corta a mitad del trabajo, sin respuesta final. Un tope solo es una red de seguridad contra un bucle sin fin, nunca la parada principal (TS 1.1-S3).
- **P6** Repite la misma primera llamada una y otra vez, hasta la red de seguridad (12): la API no guarda estado y, sin el historial, el modelo no ve sus resultados (TS 5.1-K4, 1.1-K2).
- **P7** Falla `get_user`, que se llama sin `user_id`. El modelo, al ver ese error en el historial, podría buscar por nombre; la secuencia fija no tiene esa rama (TS 1.1-K3).

| Variante | Parada | Qué se rompe |
| :--- | :--- | :--- |
| base | `end_turn` | — |
| `texto` | la primera vez que el texto dice «terminado», «listo»… | para cuando el modelo comenta, no cuando acaba |
| `tope` | tras 2 iteraciones | corta a mitad del trabajo, sin respuesta final |
| `texto_asistente` | en cuanto hay texto junto a un `tool_use` | el texto «voy a mirar el ticket» no es una respuesta |
| `sin_historial` | red de seguridad (12) | el modelo no ve sus resultados y repite la misma llamada |
| `arbol_fijo` | una llamada al modelo | la secuencia no se adapta: `get_user` falla sin `user_id` y no hay rama para buscar por nombre |

**Qué es estable y qué varía en la variante base:**

| Estable | Varía (lo decide el modelo) |
| :--- | :--- |
| La última iteración trae `end_turn` y ninguna tool | El número de iteraciones: entre 2 y 4 |
| Cada `tool_use` recibe su `tool_result` antes de la iteración siguiente | Qué llamadas independientes agrupa en una misma iteración |
| `get_user` no puede ir antes de saber de quién se trata, y `get_ticket` informa de eso | Si `search_kb` va con `get_ticket`, con `get_user` o al final |
| Las iteraciones son como mucho las llamadas más una | |

La variabilidad entre ejecuciones es parte de la lección: según la ejecución, el modelo puede no escribir texto junto a sus llamadas, y entonces `texto_asistente` no corta. Las variantes se prueban de forma determinista en `tests/test_app1_01_bucle_manual.py`.
</details>

### Pregunta tipo examen

Un agente de soporte construido con la Messages API a veces deja tareas a medias: responde «Perfecto, ya lo tengo» y el bucle termina antes de consultar el sistema de pedidos. El código actual sale del bucle cuando la respuesta contiene un bloque de texto. ¿Qué cambio es el más adecuado?

- A. Añadir al *system prompt* «no escribas texto hasta haber terminado», para que solo haya texto en la respuesta final.
- B. Continuar mientras `stop_reason` sea `"tool_use"` y terminar con `"end_turn"`, devolviendo cada `tool_result` al historial.
- C. Buscar en el texto frases como «he terminado» o «listo» y salir del bucle solo cuando aparezca alguna de ellas.
- D. Fijar un máximo de 5 iteraciones, para asegurar que el bucle consulta todas las tools antes de darse por acabado.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** La parada la decide `stop_reason` (TS 1.1-K1, 1.1-S1) y los resultados vuelven al historial con su `tool_use_id` (TS 1.1-K2, 1.1-S2). A intenta arreglar en prosa un error del código de control; C es el anti-patrón de interpretar lenguaje natural y D el de usar un tope como parada principal (TS 1.1-S3). El texto junto a un `tool_use` es comentario, no una señal de fin.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 02 · Tools integradas

> **Qué vas a hacer:** Comparar cómo explora un agente un repositorio pequeño con sus tools integradas (buscar, leer, editar) según cómo se le pida.
>
> **Necesitas antes:** Nada (el Agent SDK trae hecho el bucle de [`01`](#01--bucle-manual)).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): Agent SDK, tool, tools integradas, anti-patrón, `--repeat`, `--budget`. Lo propio de este módulo:

- **El sistema:** el agente ya no atiende tickets: explora un repositorio. Es `repo_mesa/`, un paquete Python pequeño de la mesa de ayuda (generado por `datos/generar_sinteticos.py`), y el agente trabaja sobre una **copia temporal** que se crea de nuevo para cada petición: `Edit` y `Write` escriben en la copia y los datos sintéticos originales no se tocan nunca. Solo tiene tools integradas del Agent SDK, aprobadas sin preguntar (`permission_mode="dontAsk"`).
- **Cuatro partes independientes** (`--parte`), cada una con su petición. `--anti` solo vale con la parte a la que pertenece.
- **Ancla (`old_string`):** el texto que `Edit` busca en el archivo para sustituirlo por `new_string`.
- **Módulo *wrapper* (reexportación):** un módulo que importa una función y la ofrece con otro nombre (`from x import f as g`). Quien importa desde el *wrapper* usa el nombre nuevo y nunca escribe el original. En `repo_mesa/`, `api.py` reexporta `calcular_sla` con otro nombre, y otro módulo la reimporta con un tercero.
- **Punto de entrada:** el archivo por el que empieza un flujo (la función que se llama desde fuera) y desde el que se siguen sus imports.
- **`[comprobación]`:** lo que el módulo calcula en código para contrastar la respuesta. Los llamadores esperados salen de analizar el código con `ast` (siguiendo los alias encadenados y sin contar la definición ni la reexportación), los tests esperados de buscar `test_*.py`, y en `edicion` se compara el archivo final con el esperado.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `Grep` | un patrón (expresión regular) y, si se quiere, una ruta o un filtro de archivos | las líneas o los archivos cuyo **contenido** casa con el patrón |
| `Glob` | un patrón de ruta, como `**/test_*.py` | los archivos cuya **ruta** casa con el patrón |
| `Read` | la ruta de un archivo | su contenido completo, con números de línea |
| `Write` | una ruta y el contenido | escribe el archivo entero: lo crea o lo sustituye |
| `Edit` | una ruta, `old_string` y `new_string` | el archivo con el ancla sustituida; si el ancla no aparece exactamente una vez, un error |

`busqueda`, `incremental` y `wrapper` tienen `Read`, `Grep` y `Glob` (nunca `Write` ni `Edit`); `edicion` tiene `Read`, `Write`, `Edit` y `Grep`.

### El ejercicio

Qué se le pide al agente en cada parte y qué cambia en su variante `--anti`:

- **`busqueda`:** dos peticiones: en qué archivo se lanza el error «SLA vencido para…» y la lista de todos los archivos de tests.
  - **`sin_grep`:** las mismas peticiones, con `Grep` quitado de la lista de tools; le quedan `Read` y `Glob`.
- **`incremental`:** explicar cómo se calcula el SLA de un ticket, citando los archivos que intervienen.
  - **`leer_todo`:** el prompt añade «Antes de responder, lee todos los archivos .py del repositorio».
- **`wrapper`:** encontrar todos los usos de `calcular_sla` y listar los archivos que la llaman. El *system prompt* de la variante correcta dice que, si una función se reexporta con otro nombre, primero se identifican todos los nombres exportados y después se busca cada uno.
  - **`solo_nombre`:** el *system prompt* dice en su lugar que busque solo el nombre original con `Grep` y liste los archivos que lo contienen.
- **`edicion`** (sin `--anti`): `config.py` tiene dos asignaciones `TIMEOUT = 30` y hay que cambiar solo la segunda (la del cliente de notificaciones) a 60. El prompt pide un único `Edit` con `old_string` exactamente `TIMEOUT = 30` y, si no funciona, deja libre cómo resolverlo: no nombra `Read` ni `Write`. La comprobación mira el archivo final, no el camino, y registra qué tools usó el agente para llegar a él.

La salida muestra `[contexto]`, cada llamada con su resultado y, al final de cada petición, `[medida]` (llamadas por tool, número de `Read` y coste) y `[comprobación]` (calculada en código, no leída del texto del modelo).

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) `busqueda` hace dos peticiones: en qué archivo se lanza un mensaje de error y cuáles son todos los archivos de tests. ¿Cuál se resuelve buscando en el contenido de los archivos y cuál en sus rutas? ¿Qué tool corresponde a cada una?
2. (módulo) Con `sin_grep` (las mismas peticiones, solo con `Read` y `Glob`), ¿qué camino le queda al agente para dar con el mensaje de error? ¿Cómo crecería su número de `Read` con el tamaño del repositorio?
3. (guía) `incremental` pide explicar cómo se calcula el SLA en un repositorio que el agente no conoce. ¿Por qué clase de archivo tiene sentido empezar y qué decide qué se lee después?
4. (módulo) Con `leer_todo` (el prompt manda leer antes todos los `.py`), ¿qué esperas que cambie más frente a `incremental` sin `--anti`: la calidad de la explicación, el número de `Read` o el coste?
5. (guía) En `wrapper`, `api.py` reexporta `calcular_sla` con otro nombre, y hay módulos que importan ese nombre nuevo. Con `solo_nombre` (buscar solo el nombre original), ¿qué llamadores no puede encontrar la búsqueda, por construcción? ¿Qué habría que hacer antes de buscar?
6. (módulo) ¿Esperas que la respuesta de `solo_nombre` avise de que le faltan llamadores? ¿Por qué?
7. (guía) En `edicion`, el ancla `TIMEOUT = 30` aparece dos veces en el archivo y solo hay que cambiar la segunda. ¿Qué devuelve un `Edit` con esa ancla? ¿Qué respaldo tiene el agente con `Read` y `Write`?

### Ejecutar

```bash
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda                    # Grep y Glob
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda --anti sin_grep
uv run python app1_agente_unico/02_tools_integradas.py --parte incremental [--anti leer_todo]
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper [--anti solo_nombre]
uv run python app1_agente_unico/02_tools_integradas.py --parte edicion
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper --repeat 3 --budget 0.10   # prueba barata
```

**Si ejecutas:** las funciones de comprobación se prueban sin modelo; ejecutar sirve para ver qué tools elige el agente en cada parte.

### Qué observar

Por parte, qué tools usa el agente y cuántos `Read` hace; en `wrapper`, cuántos de los llamadores esperados encuentra (`[comprobación]`); en `edicion`, si algún `Edit` devolvió error y cómo quedó el archivo.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** El mensaje de error está en el contenido: `Grep` (TS 2.5-K1, 2.5-S1). Los archivos de tests se reconocen por su ruta: `Glob` (TS 2.5-K2, 2.5-S2).
- **P2** Listar con `Glob` y abrir archivos con `Read` hasta dar con el mensaje. El número de `Read` crece con el número de archivos; con `Grep` no.
- **P3** Por un punto de entrada, que se localiza con `Grep`; después se lee solo lo que ese archivo importa y lo que sigue el flujo, en lugar de leer todo por adelantado (TS 2.5-S4).
- **P4** El número de `Read` (uno por cada `.py`) y el coste. La explicación sale parecida.
- **P5** Los que importan la función por su alias: nunca escriben el nombre original. Antes de buscar hay que reunir todos los nombres con que se exporta y buscar cada uno (TS 2.5-S5).
- **P6** No. Devuelve 2 de 4 llamadores y presenta la lista como completa: nada en la búsqueda le dice que existen otros nombres.
- **P7** Un error, porque el ancla no es única («Found 2 matches») (TS 2.5-K3). El respaldo que nombra la guía es leer el archivo con `Read` y guardarlo entero con `Write` (TS 2.5-K4, 2.5-S3), con cuidado de no tocar la primera asignación. Repetir el mismo `Edit` sería un error, porque el fallo no es pasajero (inferencia propia: la guía solo nombra el respaldo).

| Parte / variante | Señal | Qué se rompe |
| :--- | :--- | :--- |
| `busqueda` correcta | `Grep` → `core/sla.py` y `Glob` → los 3 tests, con 0–1 `Read` | — |
| `busqueda` `sin_grep` | `Glob` para listar y después más `Read` hasta dar con el mensaje | leer archivo por archivo para algo que una búsqueda de contenido resuelve |
| `incremental` correcta | `Grep` a un punto de entrada y `Read` solo de lo que este importa | — |
| `incremental` `leer_todo` | un `Read` por cada `.py` y más coste | una explicación parecida, más cara y con el contexto lleno de archivos irrelevantes |
| `wrapper` correcta | `api.py` primero, después una búsqueda por cada nombre: 4 de 4 | — |
| `wrapper` `solo_nombre` | 2 de 4: `informes/resumen.py` y `notificaciones/avisos.py` no salen | un rastreo incompleto que la respuesta presenta como completo |
| `edicion` (sin `--anti`) | `Edit` con `is_error` («Found 2 matches») en cerca de la mitad de las ejecuciones; se recupera con `Edit` de más contexto o con `Read` + `Write`; solo cambia el segundo bloque | la trampa sería repetir el mismo `Edit` o, con `Write`, tocar también el primer `TIMEOUT` |

Notas:

- **`edicion`:** el prompt pide a propósito un único `Edit` con `old_string` exactamente `TIMEOUT = 30`, porque sin esa petición el modelo lee el archivo, ve las dos líneas y amplía el ancla en el primer `Edit`, que nunca falla (Haiku 5.5 y Haiku 4.5, 11 de 11 ejecuciones). Con la petición, el fallo sale en torno a la mitad de las veces (3 de 6); el resto amplía el ancla igualmente.
  - Ampliar el ancla con más contexto también resuelve el fallo. Es válido y el comprobador lo acepta, porque mira el archivo final. La guía nombra `Read` + `Write` como respaldo; ampliar el ancla es una inferencia propia.
  - En las 3 recuperaciones observadas, el modelo usó un segundo `Edit` con más contexto y nunca `Write`. `[comprobación]` indica qué camino tomó.
- **`busqueda`:** la primera pregunta localiza el mensaje de error «SLA vencido para…» y no los llamadores de la función, porque estos son el reto de `wrapper` (TS 2.5-S5).
- **Variabilidad:** con un modelo capaz, `sin_grep` o `leer_todo` pueden salir casi iguales en un repositorio de este tamaño. Lo estable es el comprobador de `wrapper` y el fallo de `Edit`. Usa `--repeat` para ver tasas. Las funciones de comprobación se prueban sin modelo en `tests/test_app1_02_tools_integradas.py`.
</details>

### Pregunta tipo examen

Un agente de mantenimiento debe encontrar todos los llamadores de `process_refund` antes de cambiar su firma. El módulo `payments/api.py` la reexporta como `issue_refund`, y otros servicios importan `issue_refund` y no el nombre original. ¿Qué enfoque es el más adecuado?

- A. Buscar el texto `process_refund` con `Grep` y dar por llamadores los archivos que devuelva, porque el nombre original identifica todos los usos.
- B. Leer con `Read` cada archivo del directorio de servicios en orden, para que ninguna búsqueda por patrón deje fuera un llamador.
- C. Identificar los nombres con que `payments/api.py` exporta la función y buscar cada uno con `Grep`, juntando los archivos de todas las búsquedas.
- D. Usar `Glob` con el patrón `**/*refund*.py` para dar con los archivos cuyo nombre menciona la función y revisar solo esos.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Para rastrear una función a través de un módulo *wrapper* se identifican primero todos los nombres exportados y después se busca cada uno (TS 2.5-S5); `Grep` es la tool para el contenido (TS 2.5-K1, 2.5-S1). A pierde los llamadores por alias y parece completa; B es leer todo cuando una búsqueda lo resuelve, contra la exploración incremental (TS 2.5-S4); D confunde `Glob` (rutas, TS 2.5-K2) con una búsqueda de contenido: un llamador no tiene por qué llevar «refund» en su nombre de archivo.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 2.5-K3, K4, S3.** Un agente tiene que cambiar una de las dos líneas idénticas `RETRIES = 3` de un archivo, y su `Edit` con ese texto como referencia devuelve un error. ¿Qué hace a continuación?

- A. Repetir el mismo `Edit`, porque el error suele ser pasajero y desaparece al segundo intento.
- B. Leer el archivo con `Read` y guardarlo completo con `Write`, con solo esa línea cambiada.
- C. Buscar la línea con `Glob`, que localiza el texto repetido y dice al agente cuál es cada una.
- D. Usar `Grep` para sustituir la segunda aparición, ya que trabaja sobre el contenido del archivo.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**B.** `Edit` hace un cambio localizado que depende de que el texto de referencia aparezca una sola vez (TS 2.5-K3). Cuando se repite y falla, el respaldo es cargar el archivo con `Read` y guardarlo entero con `Write` (TS 2.5-K4, 2.5-S3). A repite una llamada que fallará igual; C confunde `Glob`, que casa rutas; D confunde `Grep`, que busca y no edita.
</details>

**C2 · TS 2.5-S2.** Un agente necesita la lista de todos los archivos de configuración `.yaml` de un repositorio, estén en la carpeta que estén. ¿Qué tool le corresponde?

- A. `Grep` con el patrón `yaml`, que devuelve los archivos cuyo contenido menciona esa palabra.
- B. `Read` sobre cada carpeta del repositorio, para ver uno a uno los archivos que contiene.
- C. `Edit` con una referencia vacía, que enumera los archivos antes de aplicar ningún cambio.
- D. `Glob` con el patrón `**/*.yaml`, que devuelve los archivos cuya ruta casa con el patrón.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**D.** Encontrar archivos por su nombre o su extensión es una búsqueda por ruta, y esa es la tool `Glob` (TS 2.5-K2, 2.5-S2). A busca en el contenido, así que devolvería también archivos que solo mencionan «yaml»; B lee de más; C no es lo que hace `Edit`.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 03 · Servidor MCP: descripciones de tools

> **Qué vas a hacer:** Medir con qué acierto elige el agente entre las tools de un servidor MCP según cómo estén nombradas y descritas.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): tool, MCP, servidor en proceso, *system prompt*, rol de modelo, `--repeat`. Lo propio de este módulo:

- **El sistema:** el agente de la mesa de ayuda atiende seis peticiones, una a una. No tiene tools integradas: solo las del servidor MCP en proceso `mesa` (`servers/mesa.py`, familia `routing`), así que para elegir solo cuenta con el nombre, la descripción y los parámetros de cada tool. Cada petición es una conversación nueva con `query()`, sin historial previo.
- **Qué se mide:** de cada petición se registra la **primera** llamada a una tool de `mesa` y se compara con la tool esperada. La tasa de acierto es cuántas coinciden; una petición sin ninguna llamada cuenta como fallo.
- **Enrutamiento (*routing*):** elegir qué tool atiende una petición. Elegir otra distinta de la adecuada es un *misrouting*.
- **`--rol-modelo`:** elige el rol de modelo del arnés con el que se ejecuta (`agent`, por defecto, o `enforcement`); el modelo concreto de cada rol sale de `.env`.

### Las tools del ejercicio

Variante correcta (también `palabra_clave` y, con un nombre cambiado, `nombre_enganoso`). Cada descripción dice el propósito, el formato de la entrada con un ejemplo, los casos borde y en qué se diferencia de las otras:

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `extract_ticket_facts` | `ticket_id` (`TCK-NNNN`) | usuario, categoría, estado, fecha, importe en EUR y texto original del ticket; un ID desconocido, un error de validación |
| `extract_article_steps` | `article_id` (`KB-NNN`) | el título y los pasos del artículo como lista ordenada |
| `summarize_article` | `article_id` (`KB-NNN`) | el título y una frase de resumen (la primera del artículo) |
| `verify_claim_against_article` | `claim` (la afirmación) y `article_id` | `supported` (verdadero o falso) y los términos coincidentes; compara palabras, no significado |

Variante `minimas`:

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `analyze_content` | `content_id` | descripción «Analiza contenido.»; solo atiende IDs de tickets y con cualquier otro devuelve un error de validación |
| `analyze_document` | `document_id` | descripción «Analiza un documento.»; solo atiende IDs de artículos y con cualquier otro devuelve un error de validación |

Las descripciones de `minimas` no dicen qué tipo de ID atiende cada una.

### El ejercicio

Las seis peticiones y su tool esperada en la variante correcta:

| Petición | Tool esperada |
| :--- | :--- |
| los datos (usuario, estado y fecha) de un ticket | `extract_ticket_facts` |
| la categoría y el importe de otro ticket | `extract_ticket_facts` |
| los pasos que hay que seguir «según el documento KB-109» | `extract_article_steps` |
| un resumen de una frase del «artículo KB-114» | `summarize_article` |
| si una afirmación es cierta «según el documento KB-114» | `verify_claim_against_article` |
| verificar con KB-112 una afirmación | `verify_claim_against_article` |

Qué cambia en el código de cada variante `--anti`:

- **`minimas`:** el servidor solo ofrece las dos tools genéricas de una línea. La tool esperada pasa a ser `analyze_content` para los tickets y `analyze_document` para los artículos.
- **`palabra_clave`:** las cuatro tools buenas, con sus descripciones, y el *system prompt* añade «Si la petición menciona un documento, usa siempre summarize_article».
- **`nombre_enganoso`** (variante propia, sin respaldo en la guía): `verify_claim_against_article` pasa a llamarse `get_ticket_status`, con la misma descripción, los mismos parámetros y el mismo código. La tool esperada para verificar sigue siendo esa, con su nombre nuevo.

La salida da, por petición, la tool esperada y la elegida, y al final la tasa de acierto y las peticiones falladas.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, el agente tiene las cuatro tools de la primera tabla, cada una descrita con su propósito, su entrada con un ejemplo, sus casos borde y sus diferencias con las demás. ¿En qué se apoya el modelo para elegir entre ellas? ¿Qué tendría que tener una petición para confundirlo aun así?
2. (módulo) Con `minimas` solo hay `analyze_content` («Analiza contenido.») y `analyze_document` («Analiza un documento.»). ¿En qué peticiones de la tabla podrá el modelo guiarse por las palabras de la propia petición y en cuáles no tendrá ninguna pista?
3. (guía) Con `palabra_clave`, las descripciones son las buenas y el prompt añade «si la petición menciona un documento, usa siempre `summarize_article`». Cuando la descripción y la regla apuntan a tools distintas, ¿qué puede pasar? ¿Qué peticiones de la tabla lo ponen a prueba?
4. (módulo) Con `palabra_clave`, ¿esperas que la regla desvíe las mismas peticiones en todas las repeticiones o que cambie de una a otra? ¿Por qué?
5. (módulo) Con `nombre_enganoso`, la tool de verificación se llama `get_ticket_status`, pero su descripción sigue diciendo que verifica afirmaciones. ¿Se guiará el modelo por el nombre o por la descripción?

### Ejecutar

```bash
uv run python app1_agente_unico/03_servidor_mcp.py                          # correcta
uv run python app1_agente_unico/03_servidor_mcp.py --anti minimas           # dos tools solapadas de una línea
uv run python app1_agente_unico/03_servidor_mcp.py --anti palabra_clave     # prompt con una regla por palabra clave
uv run python app1_agente_unico/03_servidor_mcp.py --anti nombre_enganoso   # la verificación se llama como una tool de tickets
uv run python app1_agente_unico/03_servidor_mcp.py --anti minimas --rol-modelo enforcement   # Haiku 4.5, ~15× más caro en este módulo
uv run python app1_agente_unico/03_servidor_mcp.py --repeat 3 --budget 0.15 # tasa en 18 peticiones
```

**Si ejecutas:** los contratos de las tools y la medida de acierto se prueban sin modelo; ejecutar sirve para ver la tasa con tu modelo, y `--rol-modelo` permite repetirla con el otro rol.

### Qué observar

La tasa de acierto y las peticiones falladas de cada variante; si repites con `--rol-modelo`, cómo cambian con el otro modelo.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** En la descripción de cada tool, que es el mecanismo principal de selección (TS 2.1-K1); por eso una buena descripción dice propósito, entradas, ejemplos y límites (TS 2.1-K2, 2.1-S1). Para confundirlo, la petición tendría que encajar en dos descripciones a la vez. Con estas cuatro, acierta todas.
- **P2** Tiene pista cuando la petición dice «documento», que coincide con el nombre de `analyze_document`. No la tiene en las de tickets ni en la que pide un «artículo»: ninguna de las dos descripciones dice qué tipo de ID atiende. Es lo que la guía llama descripciones ambiguas o solapadas, que causan *misrouting* (TS 2.1-K3); cuánto falla depende del modelo (ver notas).
- **P3** La regla del prompt puede imponerse a la descripción (TS 2.1-K4, 2.1-S4). La ponen a prueba las dos peticiones que dicen «documento» y no piden un resumen: los pasos de KB-109 y la verificación con KB-114.
- **P4** Las mismas: con el modelo de la medida, la regla desvía en todas las repeticiones las dos peticiones que dicen «documento» y deja intacto el resto, porque es una regla fija sobre una palabra.
- **P5** Por la descripción: acertó todas. Es una variante propia, sin respaldo en la guía, y no dio señal.

Cada variante se mide con el modelo en que su señal se ve (el módulo es un banco de pruebas del mecanismo, no una comparación entre modelos):

| Variante | Qué cambia | Modelo de la medida | Resultado | Qué dice |
| :--- | :--- | :--- | :--- | :--- |
| correcta | 4 tools renombradas y divididas, con descripciones de propósito, entrada, ejemplo, casos borde y diferencias | Haiku 5.5 (`--rol-modelo agent`, por defecto) | 18/18 | con descripciones buenas el agente acierta |
| `minimas` | 2 tools genéricas con una línea cada una | Haiku 4.5 (`--rol-modelo enforcement`) | 14/24 y 14/18 (58–78 %) | la ambigüedad de dos tools genéricas hace fallar la selección; con el otro rol de modelo la señal es inestable (ver notas) |
| `palabra_clave` | las descripciones buenas, pero el prompt dice «si menciona un documento, usa `summarize_article`» | Haiku 5.5 (por defecto) | 12/18: las 2 peticiones con «documento», siempre | la regla del prompt gana a la descripción; con el otro rol de modelo no la obedece y no hay señal (ver notas) |
| `nombre_enganoso` | la tool de verificación se llama `get_ticket_status` (nombre de tickets) con su descripción de siempre | Haiku 5.5 (por defecto) | 30/30 | sin señal: la descripción pesa más que el nombre (ver notas) |

Las cifras de la otra variante de modelo en cada fila, tal como estaban en esta tabla, están en `docs/hallazgos.md` («Comparaciones entre modelos y calibración», no evaluable).

Notas:

- **La señal depende del modelo, y en sentidos opuestos.** `palabra_clave` se ve con Haiku 5.5, que obedece la regla del prompt, y no con Haiku 4.5, que la ignora. `minimas` se ve con Haiku 4.5 y, con Haiku 5.5, es inestable: la primera medida dio 15/18 y las tres siguientes (30 peticiones cada una) dieron 30/30, 30/30 y 29/30. Entre la primera y las otras tres cambió también el servidor (cada tool pasó a atender un solo tipo de ID, ver la última nota), así que la caída inicial no se puede atribuir solo a la variabilidad del modelo. Ningún modelo muestra las dos de forma estable, por eso `--rol-modelo` permite elegir el rol (el nombre del modelo sigue saliendo de `.env`).
- **`minimas`:** con Haiku 5.5 apenas empeora el acierto. Se guía por las palabras de la propia petición («documento» lleva a `analyze_document`). Con Haiku 4.5 fallan sobre todo las peticiones de tickets, que van a `analyze_document`, y el resumen de un «artículo», que va a `analyze_content`. Lo que se mide es la ambigüedad, no la capacidad: con descripciones reales no hay nada que adivinar.
- **`palabra_clave`:** con Haiku 5.5 es la señal más estable. La regla del prompt gana a la descripción en las dos peticiones con la palabra, en todas las repeticiones, y deja intacto el resto. La corrección es la configuración correcta: quitar la regla del prompt y confiar en las descripciones.
- **`nombre_enganoso` (variante propia, sin respaldo en la guía): sin señal.** Con Haiku 5.5 (30/30) y con Haiku 4.5 (24/24) gana la descripción: el modelo no evitó la tool de verificación por llamarse como una de tickets, ni usó `get_ticket_status` donde no tocaba. Con una sonda desechable y solo con Haiku 4.5 se probaron dos casos más duros, renombrar la verificación como `delete_ticket` y cruzar los nombres de `extract_article_steps` y `summarize_article`: 24/24 en ambos. Con estos modelos la descripción pesa más que el nombre, en la línea de TS 2.1-K1 (la descripción es el mecanismo principal de selección). No prueba que el nombre no importe con otros modelos ni con descripciones pobres. La guía no describe este fallo: pide renombrar para quitar solapamientos (TS 2.1-S2), y esta variante hace lo contrario; que un nombre engañoso desvíe al modelo era una hipótesis propia, y aquí no se confirmó.
- **Tool esperada con `minimas`:** como solo hay dos tools, se espera «tickets → `analyze_content`, artículos → `analyze_document`». Es una convención del módulo, no algo que diga la guía. Para que equivocarse tenga consecuencias, cada tool atiende solo ese tipo de ID y la otra devuelve un error de validación; antes las dos hacían lo mismo y un «fallo» de enrutamiento no costaba nada (revisión independiente).
- Los contratos de cada tool (entrada y salida) y la medida de acierto se prueban sin modelo en `tests/test_app1_servers_mesa.py` y `tests/test_app1_03_servidor_mcp.py`.

**Para pensar (sin evaluación):** ¿cambiaría `nombre_enganoso` con otro modelo o con descripciones pobres? Este módulo no lo mide con una señal estable, así que no cuenta como predicción.
</details>

### Pregunta tipo examen

Un agente de soporte dispone de dos tools, `analyze_content` y `analyze_document`, descritas como «Analiza contenido.» y «Analiza un documento.». Con frecuencia elige la tool equivocada para peticiones parecidas. ¿Qué cambio es el más adecuado?

- A. Añadir al *system prompt* la regla «si la petición menciona un documento, usa `analyze_document`», para guiar la elección en esos casos.
- B. Fusionar las dos tools en una sola llamada `analyze` que acepte cualquier entrada, para que el modelo no tenga que elegir entre ellas.
- C. Poner un clasificador previo que decida la tool y se la entregue al agente, para que este solo tenga que ejecutarla sin elegir.
- D. Renombrar las tools según su propósito y ampliar sus descripciones con entradas, ejemplos, casos borde y en qué se diferencian de la otra.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** La descripción es el mecanismo con el que el modelo elige (TS 2.1-K1), y las ambiguas o solapadas causan *misrouting* (TS 2.1-K3). La corrección es describir con propósito, entradas y límites (TS 2.1-K2, TS 2.1-S1) y renombrar para quitar el solapamiento (TS 2.1-S2). A es una instrucción por palabra clave que puede anular las descripciones (TS 2.1-K4, TS 2.1-S4): arregla un caso y crea otros. B va al revés de la guía, que divide las tools genéricas en otras de contrato definido (TS 2.1-S3). C añade una pieza para compensar un defecto que se arregla en la descripción; ninguna viñeta de la guía lo propone.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 04 · Errores estructurados

> **Qué vas a hacer:** Ver qué hace un agente cuando sus tools fallan de cuatro formas distintas, según cómo le llegue cada error.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): error estructurado, tool, MCP, *system prompt*, registro de la ejecución (`RunRecord`), `--repeat`. Lo propio de este módulo:

- **El sistema:** un único mensaje pide al agente cinco tareas del caso de un ticket, y cada tarea usa una tool del servidor `mesa` (familia `errores`). Cuatro de las cinco tools fallan a propósito, cada una de una forma distinta. El agente no tiene tools integradas y el *system prompt* no dice qué hacer con cada error: solo que, si una tool falla, decida qué hacer y explique el resultado de cada tarea. Cada ejecución empieza con el estado del servidor a cero.
- **`is_error`:** la marca del resultado de una tool que dice que la llamada falló. El fallo llega como un resultado más, no como una excepción.
- **`errorCategory`:** el tipo de fallo en los errores de este proyecto: `transient` (pasajero, como un tiempo de espera agotado), `validation` (entrada mal formada o que no existe), `business` (una regla de negocio lo impide) o `permission` (el rol no tiene permiso).
- **`isRetryable`:** campo del error que dice si tiene sentido repetir la misma llamada.
- **Reintento idéntico:** una llamada con exactamente la misma entrada que otra que ya falló. Corregir la entrada (por ejemplo, el formato de un ID) no cuenta como reintento. Un **reintento inútil** es uno idéntico sobre una tool cuyo fallo no se arregla repitiendo, es decir, sobre cualquiera menos la del histórico.
- **Vacío válido:** una consulta que funciona y no encuentra nada, a diferencia de una que no ha podido consultar.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `fetch_ticket_history` | `ticket_id` | los eventos del ticket (creación y estado). La primera llamada válida de cada ejecución falla con un tiempo de espera (`transient`, reintentable); a partir de la segunda, responde |
| `get_user_profile` | `user_id` (su descripción da el formato `EMP-1001`) | el perfil de la persona; un ID mal formado o inexistente, un error `validation` |
| `reassign_license` | `user_id`, `license` y `seats` (puestos) | la reasignación hecha; con más de 10 puestos, un error `business` no reintentable cuyo mensaje explica el cupo y a quién pedir una ampliación |
| `export_audit_log` | `scope` | siempre un error `permission` no reintentable cuyo mensaje dice a quién pedir la exportación |
| `search_tickets_by_user` | `user_id` | la lista de IDs de sus tickets; si no tiene ninguno, una lista vacía, que no es un error |

### El ejercicio

Las cinco tareas del mensaje: el histórico del ticket `TCK-4001`; el perfil de la persona con ID «1001» (sin el prefijo `EMP-`, mal formado a propósito); reasignar 12 puestos de la licencia «editor» a `EMP-1001`; exportar el registro de auditoría completo, y la lista de tickets de `EMP-9999`.

Qué cambia en el código de cada variante `--anti`:

- **`generico`:** las mismas tools con los mismos fallos, pero todo error se devuelve como «Operation failed», con la marca de error y sin categoría, sin `isRetryable` y sin explicación.
- **`fallo_como_vacio`:** los errores siguen estructurados salvo el tiempo de espera del histórico, que se devuelve como un resultado correcto con la lista de eventos vacía.

La salida muestra, por tool, los reintentos idénticos (y cuántos son inútiles) y las categorías de error; si el transitorio llegó a recuperarse; y, sobre el histórico, si se reintentó tras recibirlo vacío (leído del registro) y si el texto final dice que no hay histórico (un detector de texto aproximado).

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Sin `--anti`, cada error llega con su `errorCategory` y su `isRetryable`. De las cuatro tools que fallan, ¿qué llamada tiene sentido repetir con la misma entrada? ¿Qué le dice al agente que no repita las demás?
2. (guía) La reasignación falla por una regla de negocio (el cupo) y la exportación, por falta de permiso. ¿En qué partes del error se apoyará el agente para distinguir un fallo del otro y explicárselo a la persona?
3. (módulo) El perfil se pide con «1001», mal formado, y la descripción de `get_user_profile` da el formato `EMP-1001`. ¿Llegará a producirse el error de validación? ¿De qué depende?
4. (guía) Con `generico`, todo error llega como «Operation failed», sin categoría ni `isRetryable`. ¿Qué deja de poder distinguir el agente? ¿Qué error puede cometer al decidir si reintenta?
5. (guía) Con `fallo_como_vacio`, el tiempo de espera del histórico llega como un resultado correcto con la lista vacía. ¿Qué dirá el agente del histórico del ticket? ¿Habrá un segundo intento?

### Ejecutar

```bash
uv run python app1_agente_unico/04_errores_estructurados.py                          # correcta
uv run python app1_agente_unico/04_errores_estructurados.py --anti generico          # todos los errores: «Operation failed»
uv run python app1_agente_unico/04_errores_estructurados.py --anti fallo_como_vacio  # el timeout llega como lista vacía
uv run python app1_agente_unico/04_errores_estructurados.py --repeat 5 --budget 0.25
```

**Si ejecutas:** la forma de cada error y las señales sobre el registro se prueban sin modelo; ejecutar sirve para ver qué hace el agente con cada error (reintentar, corregir, explicar).

### Qué observar

Por variante, qué tools se repiten con la misma entrada y cuántos de esos reintentos son inútiles, si el transitorio se recupera y qué dice el texto final del histórico.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Solo `fetch_ticket_history`: su error es `transient` y reintentable, y al segundo intento responde. En los demás, la categoría y la marca de no reintentable dicen que repetir no arregla nada (TS 2.2-K2, 2.2-K4, 2.2-S1).
- **P2** En la categoría, que separa la regla de negocio de la falta de permiso, y en el mensaje legible, que explica el cupo o a quién pedir la exportación, para que el agente pueda informar bien (TS 2.2-K2, 2.2-S1; para la regla de negocio, 2.2-S2).
- **P3** No llegó a producirse: el modelo corrige «1001» a `EMP-1001` antes de llamar. Depende de que la descripción de la tool diga el formato.
- **P4** Lo reintentable de lo que no lo es. Puede repetir lo que no tiene arreglo (aquí, `export_audit_log`) o rendirse ante lo pasajero. Un mensaje genérico es el anti-patrón (TS 2.2-K3).
- **P5** Lo da por un dato: «no hay histórico». No hay segundo intento, porque nada le dice que fue un fallo. Un fallo de acceso no debe llegar como un vacío válido (TS 2.2-S4).

| Variante | Reintentos | Qué se rompe |
| :--- | :--- | :--- |
| correcta | solo `fetch_ticket_history` (1), que se recupera | — |
| `generico` | `export_audit_log` se repite sin arreglo posible (1 inútil por ejecución) y el transitorio también se reintenta, sin nada que diga que lo es | sin categoría ni `isRetryable`, el agente no distingue lo reintentable de lo que no lo es |
| `fallo_como_vacio` | ninguno: el transitorio no se reintenta | acepta el histórico vacío sin reintentar (5 de 5, medido sobre el registro) y lo cuenta como un dato; un detector de texto aproximado lo vio en 4 de 5 |

Notas:

- **Validación:** en las ejecuciones observadas (Haiku 5.5) el modelo corrige «1001» a `EMP-1001` antes de llamar, porque la descripción de la tool dice el formato, y el error de validación no llega a producirse. Su forma se prueba sin modelo (`tests/test_app1_servers_mesa.py`). Lo más probable es que sea la consecuencia de una buena descripción (TS 2.1-K2; inferencia propia), no un defecto del módulo. Con Haiku 4.5 (sonda, 10 ejecuciones) tampoco se vio.
- **`generico` depende del modelo:** con Haiku 4.5 (sonda) no hubo reintentos inútiles, porque no reintentó nada; lo que cambió fue que se rindió ante el *timeout* (lo recuperó 2 de 5 veces con metadatos y 0 de 5 con el error genérico). Muestra pequeña: la señal del módulo es la de Haiku 5.5.
- **`isRetryable` frente a `retriable`:** la guía escribe `retriable: false` para la regla de negocio; el proyecto usa `isRetryable` en todos los errores. Con la regla de negocio, además, el mensaje explica la política para que el agente informe a la persona usuaria (TS 2.2-S2).
- **Vacío válido:** la búsqueda de `EMP-9999` devuelve una lista vacía correcta, que no es un error. Lo que `fallo_como_vacio` rompe es lo contrario: un fallo de acceso disfrazado de lista vacía (TS 2.2-S4).
- Las señales sobre el `RunRecord` (reintentos idénticos, categorías) se prueban sin modelo en `tests/test_app1_04_errores_estructurados.py`. «El texto dice que no hay histórico» es un detector aproximado (la revisión independiente encontró frases positivas que lo activaban y se corrigieron); las señales robustas salen del registro: «transitorio recuperado» e «histórico vacío aceptado sin reintento».
</details>

### Pregunta tipo examen

Una tool MCP de reembolsos devuelve «Operation failed» ante cualquier fallo. El agente reintenta tres veces un reembolso rechazado por superar el límite de la política y luego comunica a la persona que hubo un problema técnico. ¿Qué cambio es el más adecuado?

- A. Devolver el error con `isError`, una categoría de regla de negocio, la marca de no reintentable y una explicación legible de la política.
- B. Limitar al agente a un máximo de dos reintentos por tool, para que ningún error se repita más de lo razonable y se acote el gasto.
- C. Añadir al *system prompt* la regla «no reintentes los errores de política y explica la causa», sin cambiar la respuesta de la tool.
- D. Cambiar el mensaje a «Operation failed, please try again later», para que el agente espere un poco antes de volver a intentarlo.

<details>
<summary>Paso 4 · Respuesta</summary>

**A.** El fallo se comunica con el flag de error y metadatos estructurados (TS 2.2-K1, TS 2.2-S1): la categoría distingue una regla de negocio de un fallo transitorio (TS 2.2-K2; la guía no da nombre al valor de esa categoría), la marca de no reintentable evita el reintento inútil (TS 2.2-K4; la guía la escribe `retriable: false` en S2 e `isRetryable` en S1) y la explicación de la política permite al agente informar bien (TS 2.2-S2). B pone un tope arbitrario en vez de dar al agente la información, y seguirá reintentando lo que no tiene arreglo; C intenta suplir en prosa lo que debería salir de la tool, y no distingue unos errores de otros; D empeora el problema: invita a reintentar justo lo que no es reintentable. Un mensaje genérico es el anti-patrón (TS 2.2-K3).
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 05 · Scoping y `tool_choice`

> **Qué vas a hacer:** Comparar cómo elige tools un agente con 5 o con 18 disponibles, y qué garantiza cada modo de `tool_choice` en la primera respuesta.
>
> **Necesitas antes:** El bucle de [`01`](#01--bucle-manual): la parte `tool_choice` usa uno igual.
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): scoping, `tool_choice`, Agent SDK, Messages API, iteración (turno), `stop_reason`, MCP. Lo propio de este módulo:

- **El sistema:** dos partes independientes sobre la mesa de ayuda.
  - **`scoping` (Agent SDK):** seis peticiones al agente, cada una en una conversación nueva, con solo las tools del servidor `mesa` (sin integradas). De cada petición se registra la primera llamada a una tool de `mesa`, si esa elección cambia entre repeticiones y el coste.
  - **`tool_choice` (Messages API, con un bucle propio como el de `01`):** una misma petición con dos tools locales, enviada con tres valores distintos de `tool_choice`. De cada respuesta se imprime si empieza por texto o por una llamada a tool, y cuál.
- **Alias (casi duplicado):** una tool con otro nombre que hace exactamente lo mismo que una de las cinco básicas y repite su descripción con otras palabras, como `lookup_ticket` para `get_ticket` o `get_employee` para `get_user`. En `scoping`, elegir un alias de la tool esperada cuenta como acierto.
- **Carga diferida de definiciones (*tool search*):** un mecanismo que carga las definiciones de las tools bajo demanda en lugar de enviarlas todas. El módulo fija `ENABLE_TOOL_SEARCH=false` por precaución y la salida cuenta las cargas diferidas.
- **Modos de `tool_choice` del ejercicio:** `auto`, `any` y el forzado de una tool concreta (`{"type": "tool", "name": "extract_ticket_metadata"}`). Qué garantiza cada uno es lo que se practica.

### Las tools del ejercicio

`scoping`, familia `acotado` (variante correcta):

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `get_ticket` | `ticket_id` (`TCK-NNNN`) | el ticket completo; un ID desconocido, un error |
| `search_tickets` | `query`: palabras clave, una categoría o un ID de usuario (`EMP-NNNN`) | el total de tickets que coinciden y hasta 8 IDs |
| `search_kb` | `query`: palabras clave o una categoría | el total de artículos que coinciden y hasta 8 IDs |
| `get_article` | `article_id` (`KB-NNN`) | el artículo completo; un ID desconocido, un error |
| `get_user` | `user_id` (`EMP-NNNN`) | la persona usuaria; un ID desconocido, un error |

La familia `amplio` (`--anti amplio`) ofrece esas cinco más 13 alias: `lookup_ticket`, `fetch_ticket_details` y `get_ticket_status` (de `get_ticket`); `find_tickets` y `list_tickets_by_user` (de `search_tickets`); `query_kb`, `kb_lookup` y `find_kb_articles` (de `search_kb`); `read_article` y `get_kb_entry` (de `get_article`); `find_user`, `get_employee` y `lookup_user_profile` (de `get_user`).

`tool_choice`:

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `extract_ticket_metadata` | `ticket_text`, el texto del ticket | la categoría y la urgencia (alta o normal), deducidas por palabras clave |
| `search_kb` | `query`, palabras clave | hasta 3 artículos con su ID y su título |

### El ejercicio

- **`scoping`:** las seis peticiones piden los datos de un ticket, quién es una persona usuaria, leer completo el artículo KB-109, buscar artículos sobre la VPN, buscar tickets sobre la wifi de las salas de reuniones y listar los tickets de una persona. Cada una tiene una de las cinco tools como esperada.
  - **`amplio`:** las mismas peticiones y el mismo *system prompt*, con las 18 tools en lugar de las 5.
- **`tool_choice`** (sin `--anti`; se comparan los tres modos): una petición de opinión sobre el texto de un ticket («¿crees que este tipo de tickets suelen ser un problema grave?»). El código envía el modo elegido solo en el primer turno y `auto` en los siguientes, y el bucle termina según `stop_reason`, como en `01`.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) En `scoping`, `amplio` da al agente 18 tools (las 5 básicas y 13 alias que hacen lo mismo) en lugar de 5. ¿Qué riesgo corre la elección de tool cuando hay muchas y se parecen? ¿Qué tendrían que tener las peticiones para que se notara?
2. (módulo) Las seis peticiones de `scoping` son claras y cada una encaja en una sola tool básica. Con ellas, ¿qué esperas que cambie más entre 5 y 18 tools: el acierto, la tool elegida de una repetición a otra o el coste por petición?
3. (guía) En `tool_choice`, la petición es de opinión y no necesita ninguna tool. De `auto`, `any` y el forzado, ¿qué modo deja al modelo contestar solo con texto? ¿Cuáles obligan a que la primera respuesta empiece por una tool?
4. (guía) Con `any`, ¿quién decide qué tool se llama? ¿Y con el forzado?
5. (módulo) El módulo envía `any` o el forzado solo en el primer turno, y `auto` en los siguientes. ¿Qué pasaría si los enviara en todos los turnos?

### Ejecutar

```bash
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping                  # 5 tools
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping --anti amplio    # 18 tools
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte tool_choice --repeat 6   # auto, any y forzado
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping --repeat 5 --budget 0.20
```

**Si ejecutas:** la petición por modo y el clasificador de la primera respuesta se prueban sin modelo. Ejecutar `tool_choice` sirve para ver con qué empieza la primera respuesta en cada modo, y `scoping`, el acierto, la consistencia y el coste por petición.

### Qué observar

En `scoping`, el acierto, si la elección cambia entre repeticiones y el coste por petición con 5 y con 18 tools. En `tool_choice`, con qué empieza la primera respuesta en cada modo y qué pasa en el turno siguiente.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Con demasiadas tools, la selección se vuelve menos fiable (TS 2.3-K1). Se notaría con peticiones ambiguas, que encajan en varias tools.
- **P2** El coste: cada petición carga 13 definiciones de más. El acierto no bajó con estas peticiones.
- **P3** `auto` deja contestar con texto. `any` y el forzado obligan a empezar por una tool (TS 2.3-K4, 2.3-S5).
- **P4** Con `any`, el modelo: se garantiza una llamada, no cuál. Con el forzado se llama la tool que fija el código (TS 2.3-K4; sus usos, en 2.3-S4 y 2.3-S5).
- **P5** El modelo estaría obligado a llamar a una tool también después de recibir los resultados y no podría dar su respuesta final. Es una inferencia propia a partir de TS 2.3-S4, que solo dice que la tool forzada va primero y lo demás sigue en turnos posteriores.

Haiku 5.5:

| Parte / variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `scoping` 5 tools | acierto 30/30, sin cambios entre repeticiones, ~0,00033 $ por petición | — |
| `scoping` 18 tools (`--anti amplio`) | acierto 30/30, sin cambios, ~0,00045 $ por petición (+36 %) | el acierto no baja, pero cada petición carga 13 definiciones de más |
| `tool_choice` `auto` | 0/6 empiezan por tool: contesta con texto | puede no llamar a ninguna tool |
| `tool_choice` `any` | 6/6 empiezan por tool | garantiza una llamada (cuál, la elige el modelo) |
| `tool_choice` forzado | 6/6 empiezan por `extract_ticket_metadata`, y el turno siguiente (`auto`) enriquece o responde | la tool fijada va primero y el resto sigue en turnos posteriores |

Notas:

- **`scoping`:** la guía dice que 18 tools degradan la fiabilidad de selección; aquí no se vio en el acierto. Con Haiku 5.5 y con Haiku 4.5 (sonda: 18/18 y 18/18) las peticiones son claras y el modelo elige bien. Lo que sí se vio: más coste con 18 tools (+36 % con Haiku 5.5; la cifra con Haiku 4.5 está en `docs/hallazgos.md`) y, con Haiku 4.5, una petición cuya tool cambió entre repeticiones (`get_user` o `get_employee`). Con peticiones más ambiguas o más tools, la degradación de acierto sería previsiblemente más fácil de provocar (hipótesis sin comprobar). En el examen manda la guía.
- ***Tool search*:** `ENABLE_TOOL_SEARCH=false` se fija por precaución y la salida confirma `cargas diferidas=0`. En las sondas no se activó con ningún valor de la variable, así que no hay prueba de que `false` apague algo: solo de que aquí no interviene (`docs/hallazgos.md`).
- **`auto`:** depende de la petición. Con «¿qué te parece?» o «¿es urgente?» Haiku 5.5 sí llamaba a la tool y el contraste no se veía; con una petición de opinión contesta con texto. Ese es el caso que `any` y el forzado resuelven.
- **Un turno, no todos:** el modo forzado o `any` solo va en el primer turno. En todos los turnos, el modelo estaría obligado a llamar a una tool también después de recibir los resultados y no podría dar su respuesta final.
- **Producto observado (no evaluable):** `any` y la forzada devuelven 400 en Sonnet 5.5 (comprobado) y, según la documentación del repositorio de estudio, en Opus 5.5 y Fable 5.1. Haiku 5.5 y Haiku 4.5 las aceptan. En el examen manda la guía.
- La petición por modo, la secuencia forzado → `auto` y el clasificador de la primera respuesta se prueban sin modelo en `tests/test_app1_05_scoping_y_tool_choice.py`.
</details>

### Pregunta tipo examen

Un flujo de soporte necesita extraer los metadatos de cada ticket nuevo antes de enriquecerlo con la base de conocimiento. A veces el asistente responde con texto conversacional y se salta la extracción. ¿Qué configuración es la más adecuada?

- A. Enviar `tool_choice` con el valor `"any"` en todos los turnos, para que el asistente nunca devuelva texto y el flujo siempre avance.
- B. Forzar la extracción con `{"type": "tool", "name": "extract_ticket_metadata"}` en el primer turno y usar `"auto"` en los siguientes.
- C. Añadir al *system prompt* «llama siempre a `extract_ticket_metadata` antes de responder» y mantener `"auto"` en todos los turnos.
- D. Dar al asistente diez tools de enriquecimiento más junto a la de extracción, para que siempre tenga una opción disponible que llamar.

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** La selección forzada asegura que una tool concreta se llame primero y los pasos siguientes se procesan en turnos posteriores (TS 2.3-S4, TS 2.3-K4). A fuerza una llamada en cada turno, así que el asistente nunca podría dar su respuesta final, y `"any"` además no fija cuál es la tool (garantiza una llamada, no esa llamada, TS 2.3-S5). C intenta suplir en prosa lo que debe garantizar la configuración: con `"auto"` el modelo puede seguir contestando con texto. D va en contra de TS 2.3-K1: más tools degradan la selección y no aseguran que se llame a la de extracción.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).

---

## 06 · Configuración MCP

> **Qué vas a hacer:** Conectar el agente a servidores MCP declarados en un `.mcp.json` y ver qué cambian los resources y la descripción de una tool en lo que hace.
>
> **Necesitas antes:** Nada (el servidor `mesa` reutiliza las tools de [`05`](#05--scoping-y-tool_choice)).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): MCP, servidor en proceso / stdio, resource, `.mcp.json`, tools integradas, arnés. Lo propio de este módulo:

- **El sistema:** el agente de la mesa de ayuda se conecta a servidores MCP que son programas aparte. En cada ejecución el módulo crea una copia temporal (el `cwd` del agente) y escribe en ella un `.mcp.json` con dos servidores stdio: `catalogo` (`servers/catalogo_stdio.py`) e `inventario` (`servers/inventario_stdio.py`). Los lanza con `uv run --no-sync --project <raíz>` y entrega el token con `"env": {"CATALOGO_TOKEN": "${CCARF_DEMO_TOKEN}"}`: el archivo lleva la **variable**, no el valor, y el módulo pone un valor sintético en el entorno del proceso. El agente se ejecuta con `setting_sources=["project"]` (la excepción al aislamiento: lee el `.mcp.json` del `cwd`, no el del repositorio ni la configuración de usuario).
- **Ámbito de un servidor MCP:** dónde se declara. El de proyecto es el `.mcp.json` del repositorio, que viaja con git; el de usuario se guarda en `~/.claude.json`, en tu máquina, y vale para todos tus proyectos.
- **Expansión de variables (`${VAR}`):** al conectar el servidor, `${VAR}` se sustituye por el valor de esa variable en el entorno del proceso.
- **`setting_sources`:** qué configuraciones de Claude Code carga el agente. El arnés la deja vacía para aislarlo; `["project"]` carga solo la del ámbito de proyecto del `cwd`.
- **`ListMcpResourcesTool` y `ReadMcpResourceTool`:** las tools del SDK que listan y leen los resources de los servidores conectados.
- **Llamada exploratoria:** en la parte `recursos`, cada llamada a `search_kb` o `get_article` del catálogo, es decir, buscar o leer por ID para averiguar qué hay.

### Las tools del ejercicio

| Servidor | Tool o resource | Qué recibe | Qué devuelve |
| :--- | :--- | :--- | :--- |
| `catalogo` | `search_kb` | `query` y, si se quiere, `include_superseded` | hasta 8 artículos ordenados por relevancia (`score`), sin los obsoletos salvo que se pidan, y cuántos obsoletos excluyó |
| `catalogo` | `get_article` | `article_id` (`KB-NNN`) | el artículo completo; un ID desconocido, un error de validación |
| `catalogo` | `token_status` | nada | solo si el servidor recibió `CATALOGO_TOKEN` (sí o no), nunca su valor |
| `catalogo` | resource `kb://catalogo` | — | el índice de todos los artículos (ID, título y categoría) |
| `catalogo` | resources `kb://articulos/<ID>` | — | cada artículo |
| `inventario` | `stock_equipo` | `tipo` (`portatil`, `monitor`, `movil` o `periferico`) | las unidades disponibles, de una tabla fija; un tipo desconocido, 0 |
| `mesa` (en proceso) | las cinco tools de la familia `acotado` de `05` | | |

La descripción completa de `search_kb` detalla el ranking, el filtro de obsoletos (`superseded_by`) y sus salidas; la mínima es «Busca en la base de conocimiento.».

### El ejercicio

Tres partes, cada una con su petición y sus tools. `--anti` solo vale con la parte a la que pertenece.

- **`conexion`** (sin `--anti`): además de los dos servidores del `.mcp.json`, el servidor en proceso `mesa`. La petición pide expresamente una llamada a una tool de cada servidor: `token_status`, `stock_equipo` con `portatil` y `get_ticket`. La salida muestra las tools por servidor, si el servidor recibió el token (solo dice sí o no, nunca el valor) y el comando de **ámbito de usuario** (`claude mcp add --scope user …`), que se imprime y no se ejecuta: `~/.claude.json` es personal.
- **`recursos`:** «¿qué artículos hay en el catálogo?», pidiendo los IDs y títulos de todos. En la variante correcta el agente tiene las dos tools de resources y el *system prompt* añade una frase que dice que los catálogos están expuestos como resources y con qué tools consultarlos. Se cuentan las llamadas exploratorias (`search_kb` y `get_article`) y las de resources.
  - **`sin_recursos`:** ni las tools de resources ni esa frase; quedan las tools de `catalogo` e `inventario`.
- **`descripcion`:** «¿qué artículo vigente explica cómo arreglar una VPN inestable desde casa?», pidiendo su ID y los pasos. Los artículos están además como archivos `.md` en `articulos/` del `cwd` (con su línea `superseded_by`), y el agente tiene `Grep` y `Read` junto a `search_kb` y `get_article` del catálogo. El *system prompt* no menciona esos archivos. Se cuentan `Grep` frente a `search_kb`.
  - **`descripcion_minima`:** el `.mcp.json` pasa `CATALOGO_DESCRIPCION=minima` al servidor, y la descripción de `search_kb` es una línea.

**Comunitario frente a propio (TS 2.4-S4), sin código:**

| La integración es… | Servidor | Por qué |
| :--- | :--- | :--- |
| estándar y ya resuelta (Jira, GitHub, Slack) | **comunitario** | se mantiene fuera y se actualiza con su proyecto |
| un flujo de la mesa de ayuda (su catálogo, sus reglas, sus datos) | **propio** | es el único que conoce el dominio y cuyo contrato debe mantener el equipo |

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) En `conexion` hay tres servidores configurados: dos en el `.mcp.json` y uno en proceso. ¿Tendrá el agente las tools de los tres a la vez o solo las del que esté usando?
2. (guía) El `.mcp.json` se versiona y lo comparte todo el equipo, y aquí lleva `${CCARF_DEMO_TOKEN}` en lugar del valor del token. ¿Qué problema evita eso? ¿En qué momento se sustituye la variable por su valor?
3. (guía) En `recursos`, el índice de artículos está publicado como resource (`kb://catalogo`). ¿Qué gana el agente con eso frente a averiguar qué artículos hay con `search_kb` y `get_article`?
4. (módulo) Con `sin_recursos` (ni las tools de resources ni la frase del prompt que las anuncia), ¿esperas que el agente necesite unas pocas llamadas exploratorias o decenas para listar todos los artículos?
5. (guía) En `descripcion`, el agente puede buscar el artículo con `Grep` sobre los archivos o con `search_kb`, que además ordena por relevancia y filtra los obsoletos. Con `descripcion_minima` («Busca en la base de conocimiento.»), ¿qué riesgo corre la elección entre las dos? ¿Qué debería contar la descripción para evitarlo?
6. (guía) ¿Dónde declararías un servidor experimental que solo usa una persona, y dónde uno que debe tener todo el equipo?

### Ejecutar

```bash
uv run python app1_agente_unico/06_mcp_config.py --parte conexion                          # tres servidores y el token
uv run python app1_agente_unico/06_mcp_config.py --parte recursos                          # catálogo como resource
uv run python app1_agente_unico/06_mcp_config.py --parte recursos --anti sin_recursos
uv run python app1_agente_unico/06_mcp_config.py --parte descripcion [--anti descripcion_minima]
uv run python app1_agente_unico/06_mcp_config.py --parte recursos --repeat 4 --budget 0.20
```

**Si ejecutas:** el `.mcp.json` generado y los contadores se prueban sin modelo; ejecutar `recursos` sirve para ver cuánto explora el agente en cada variante.

### Qué observar

En `conexion`, las tools por servidor y `token_recibido`. En `recursos`, cuántas llamadas exploratorias y a resources hace cada variante, y su coste. En `descripcion`, cuántas veces usa `Grep` frente a `search_kb`.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Las de los tres a la vez: al conectar, el agente descubre las tools de todos los servidores configurados (TS 2.4-K3). Se distinguen por el prefijo `mcp__<servidor>__`.
- **P2** Que el secreto quede escrito en el repositorio: el archivo guarda el nombre de la variable y nunca su valor. Se expande al lanzar el servidor (TS 2.4-K2, 2.4-S1).
- **P3** Ve qué hay sin tener que explorarlo con llamadas (TS 2.4-K4, 2.4-S5): con el resource bastaron 2 llamadas y ninguna exploratoria.
- **P4** Decenas: entre 19 y 31, con búsquedas y lecturas por ID, incluidos IDs que no existen.
- **P5** Que el agente prefiera la tool integrada, `Grep`, aunque la tool MCP sea más capaz. La descripción debería contar qué sabe hacer y qué devuelve: el ranking y el filtro de obsoletos (TS 2.4-S3). Con el modelo de la medida esa preferencia no se vio (ver notas); en el examen manda la guía.
- **P6** El personal o experimental, en `~/.claude.json`, en el ámbito de usuario. El del equipo, en el `.mcp.json` del proyecto (TS 2.4-K1, 2.4-S2).

Haiku 5.5:

| Parte / variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `conexion` | `mcp=['catalogo','inventario','mesa']`, 9 tools con prefijos `mcp__<servidor>__`, `token_recibido: true`, una llamada ok a cada servidor | todas las tools, a la vez; el token se expande sin escribirse en el archivo |
| `recursos` correcta | 2 llamadas a resources (`ListMcpResourcesTool`, `ReadMcpResourceTool`), 0 exploratorias, ~0,0009 $ | el catálogo da visibilidad de qué hay sin explorar; la mejora sale de las tools de resources **y** de la frase que las anuncia, juntas |
| `recursos` `sin_recursos` | 19–31 llamadas exploratorias, 0,0021–0,0033 $ (×2,3–3,7) | el agente adivina con búsquedas y lecturas por ID, incluidos IDs que no existen |
| `descripcion` correcta | `Grep` 0/6, `search_kb` MCP 6/6 | — |
| `descripcion` `descripcion_minima` | `Grep` 0/6, `search_kb` MCP 6/6 | **sin diferencia** con Haiku 5.5 |

Notas:

- **Los resources no los descubre el modelo solo.** La variante correcta cambia dos cosas a la vez, las tools de resources y la frase que las anuncia. Con las tools solas, sin avisar, el agente exploró con búsquedas: la aplicación debe decirle que existen (aquí, una frase en el prompt del sistema). En el SDK se alcanzan con `ListMcpResourcesTool` y `ReadMcpResourceTool`. Es **Producto observado (no evaluable)**.
- **`descripcion`: la señal que dice la guía no se vio.** Según la guía, una descripción mínima hace que el agente prefiera `Grep`. Con Haiku 5.5 y con Haiku 4.5 (sondas, 6 repeticiones por condición) no cambió la preferencia: sin avisar de que hay archivos, `Grep` salió 0/6 con las dos descripciones, y avisando salió igual de a menudo con una que con otra (4/6 y 5/6 con Haiku 5.5). Lo que movió al agente a `Grep` fue saber que los archivos existían, no la descripción. La viñeta se enseña igualmente (cabecera y pregunta); en el examen manda la guía.
- **`init` puede traer la lista de tools incompleta:** en 2 de unas 8 ejecuciones, los servidores stdio constaban como conectados pero sus tools no estaban aún en `init`; el módulo lo avisa con `[aviso]`. Las llamadas funcionan igualmente.
- **Sin aprobación:** con `setting_sources=["project"]` el SDK conecta los servidores de `.mcp.json` sin pedir aprobación; la CLI interactiva sí puede pedirla.
- El `.mcp.json` generado, el comando de ámbito de usuario, los contadores y la agrupación de tools por servidor se prueban sin modelo en `tests/test_app1_06_mcp_config.py`.
</details>

### Pregunta tipo examen

Un agente tiene `Grep` y un servidor MCP propio con una tool `search_kb` que ordena por relevancia y filtra los artículos obsoletos con `superseded_by`. La descripción de la tool es «Busca en la base de conocimiento.» y el agente suele preferir `Grep` sobre los archivos del repositorio. ¿Qué cambio es el más adecuado?

- A. Quitar `Grep` de las tools del agente, para que la única forma de buscar artículos sea la tool del servidor MCP.
- B. Añadir al *system prompt* la regla «usa siempre `search_kb` para buscar artículos» y dejar la descripción como está.
- C. Ampliar la descripción de `search_kb` con sus capacidades y sus salidas: ranking y filtrado de obsoletos con `superseded_by`.
- D. Sustituir el servidor propio por uno comunitario genérico de búsqueda, que ya traerá descripciones más largas.

<details>
<summary>Paso 4 · Respuesta</summary>

**C.** Una descripción que detalla capacidades y salidas evita que el agente prefiera una tool integrada sobre una tool MCP más capaz (TS 2.4-S3): lo que decide la elección es lo que el agente ve de cada tool (TS 2.1-K1). A quita una herramienta que el agente sigue necesitando para otras cosas y no arregla la descripción; B es una instrucción en el prompt que compensa una descripción pobre y puede crear asociaciones no deseadas (TS 2.1-K4); D no aplica el criterio de TS 2.4-S4: una búsqueda sobre el catálogo propio de la mesa es un flujo específico del equipo y pide servidor propio.
</details>

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS 2.4-K1, S2.** Una desarrolladora quiere probar un servidor MCP experimental sin que le aparezca al resto del equipo. ¿Dónde lo declara?

- A. En el `.mcp.json` del proyecto, en una rama aparte, para retirarlo cuando acabe la prueba.
- B. En el `CLAUDE.md` del proyecto, descrito como un servidor que solo ella debe utilizar.
- C. En su `~/.claude.json`, el ámbito de usuario, que es personal y no viaja con el repositorio.
- D. En el `.claude/settings.json` del proyecto, donde se listan los servidores de cada persona.

<details>
<summary>Comprobación C1 · Respuesta</summary>

**C.** Hay dos sitios para declarar un servidor: `.mcp.json` en el proyecto, para lo que comparte el equipo, y `~/.claude.json` en el usuario, para lo personal o experimental (TS 2.4-K1, 2.4-S2). A lo comparte con quien use esa rama; B y D no son donde se declaran los servidores MCP.
</details>

**C2 · TS 2.4-K2, S1.** El `.mcp.json` del proyecto, que se versiona, necesita un token para uno de sus servidores. ¿Cómo se escribe?

- A. Con una referencia como `${GITHUB_TOKEN}`, que se expande desde el entorno al lanzar el servidor.
- B. Con el valor del token en el archivo, y el archivo añadido a `.gitignore` en cada clon.
- C. Con el token cifrado en el archivo y la clave para descifrarlo guardada en el `CLAUDE.md`.
- D. Con el valor en el *system prompt* del agente, para que él se lo pase al servidor al llamarlo.

<details>
<summary>Comprobación C2 · Respuesta</summary>

**A.** `.mcp.json` admite referencias a variables de entorno que se expanden al lanzar el servidor: el repositorio guarda el nombre de la variable y nunca el secreto (TS 2.4-K2, 2.4-S1). B deja de compartir la configuración; C y D ponen el secreto donde lo lee quien no debe.
</details>

**C3 · TS 2.4-K3.** Un agente tiene configurados tres servidores MCP. ¿Qué tools tiene disponibles al empezar?

- A. Las del primer servidor declarado; las de los otros se activan cuando el agente los pide.
- B. Las de los tres a la vez: al conectar descubre las tools de todos los servidores configurados.
- C. Ninguna hasta que el usuario elige, en cada petición, con qué servidor quiere trabajar.
- D. Las del servidor cuya descripción encaje mejor con la primera petición de la sesión.

<details>
<summary>Comprobación C3 · Respuesta</summary>

**B.** Al conectar, el agente descubre las tools de todos los servidores configurados y puede usarlas todas a la vez (TS 2.4-K3). Ni se activan por turnos ni las elige el usuario.
</details>

**C4 · TS 2.4-K4, S5.** Un agente gasta decenas de llamadas en averiguar qué tablas tiene una base de datos antes de poder consultarla. ¿Qué cambio lo evita?

- A. Añadir más tools de búsqueda al servidor, una por cada tipo de tabla que pueda existir.
- B. Subir el tope de iteraciones, para que le dé tiempo a explorar el esquema completo.
- C. Pedirle en el prompt que explore menos y consulte la tabla que le parezca más probable.
- D. Publicar el esquema como un resource MCP, para que vea qué hay sin llamadas exploratorias.

<details>
<summary>Comprobación C4 · Respuesta</summary>

**D.** Un catálogo de contenido, como el esquema de una base de datos, se publica como *MCP resource*: el agente ve qué hay sin explorarlo con llamadas (TS 2.4-K4, 2.4-S5). A añade más tools que elegir; B paga la exploración en vez de evitarla; C la sustituye por adivinar.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).


---

## 07 · Recorte de contexto

> **Qué vas a hacer:** Preguntar a un agente de inventario por ocho equipos, uno por uno, y comparar los tokens de entrada de cada petición cuando la tool devuelve los 40 campos de cada equipo y cuando devuelve solo los 5 que hacen falta.
>
> **Necesitas antes:** [módulo 01](#01--bucle-manual) (el bucle escrito a mano y el historial que se reenvía completo en cada petición).
>
> **Modo:** Ejecución ligera (puedes hacerlo entero sin ejecutar).

### Antes de empezar

Términos comunes en el [glosario](../docs/glosario.md): tool, historial, `usage`, arnés. Lo propio de este módulo:

- **El sistema:** un agente de inventario de TI de una empresa ficticia, con un bucle escrito a mano sobre la Messages API (como en `01`). Los datos son ocho equipos sintéticos con 40 campos cada uno (`inventario_equipos.json`); solo cinco responden a las preguntas del módulo.
- **Recorte (*trimming*):** quitar de un resultado de tool los campos que no hacen falta antes de que entre en el historial. Aquí lo hace el propio código de la tool.
- **Campo relevante:** el que la tarea usa para responder. Lo fija el código (`KEEP_FIELDS`), no el modelo.
- **Tokens de entrada:** los que el modelo lee en una petición (el *system prompt*, las definiciones de las tools y el historial), que la API informa en el `usage` de la respuesta. El módulo suma también los de caché.
- **Comprobación de la respuesta:** el código da por correcta la primera respuesta si el primer equipo que nombra (por ID o por nombre) es el esperado, y la segunda si contiene el número de solicitudes abiertas de ese equipo. Busca primero por ID y, si no hay ninguno, por nombre escrito con su mayúscula (cuatro equipos se llaman con palabras comunes, y «por seguridad» no es el equipo Seguridad). Es una red de seguridad barata, no un evaluador, y tiene límites que se dejan a propósito (cada uno está fijado en un test):
  - El ID manda sobre los nombres, aunque solo un equipo lo lleve. Con Seguridad (EQ-06) como esperado, «Seguridad tiene 21; le sigue Finanzas TI (EQ-05).» da incorrecta y «Finanzas TI gana; Seguridad (EQ-06) le sigue.» da correcta: lo contrario de «el primero que nombra».
  - No lee el sentido: no distingue «es X, no Y» de «es Y, no X», y «Seguridad revisada: gana Finanzas TI.» cuenta como Seguridad.
  - Sin ningún ID, una frase que empiece por «Datos…» se toma por el equipo Datos (falso positivo o falso negativo según el esperado).
  - Exigir la mayúscula evita «por seguridad», pero pierde aciertos: «el equipo seguridad» y «SEGURIDAD» se dan por incorrectas.

  EN PRODUCCIÓN (no evaluable): no se leería texto libre. Se pediría al modelo el resultado en un campo (una tool de respuesta final con `tool_choice` forzado, o un esquema JSON: `{"team_id": "EQ-06", "unassigned_laptops": 21}`) y se comprobaría `result["team_id"] == expected`. Para respuestas abiertas, casos etiquetados medidos en muchas ejecuciones y, con calibración humana, otro modelo como juez. Es práctica general, no un mecanismo que la guía asigne a este módulo, y no cambia la respuesta de examen.

### Las tools del ejercicio

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `list_teams` | nada | los ocho equipos, con su ID (`EQ-NN`) y su nombre |
| `get_team_inventory` | `team_id` | el registro del equipo: 5 campos en la variante correcta y los 40 en `sin_recorte` |

### El ejercicio

Se hacen dos preguntas en la misma conversación. La primera pide el equipo con más portátiles sin asignar y que consulte los equipos uno por uno; la segunda, cuántas solicitudes abiertas tiene ese equipo, que se responde con lo que ya está en el historial.

- **Correcta:** el código de la tool recorta cada resultado a `team_id`, `team_name`, `laptops_total`, `laptops_assigned` y `open_requests` antes de añadirlo al historial.
- **`sin_recorte`:** la tool devuelve el registro entero, como lo guarda el sistema de origen.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de este ejercicio:

1. (guía) Cada petición lleva el historial completo, y cada consulta de equipo añade un resultado. Petición a petición, ¿qué forma tiene la curva de tokens de entrada? ¿Dónde esperas el máximo de la conversación?
2. (guía) Para reducir ese consumo, ¿en qué momento hay que quitar los campos que sobran: antes de que el resultado entre en el historial, o después, pidiendo al modelo que los ignore? ¿Por qué?
3. (módulo) Cada resultado recortado tiene 8 veces menos campos (5 frente a 40). ¿Esperas que el total de tokens de entrada baje en esa misma proporción, en más o en menos? ¿Qué partes de cada petición no cambian al recortar?
4. (módulo) Con `sin_recorte`, el modelo tiene delante 35 campos que las preguntas no usan. ¿Crees que eso cambia si acierta las dos respuestas?
5. (módulo) De lo que mide el módulo, ¿qué esperas que salga casi igual en cada ejecución y qué puede variar? Piensa en quién decide cuántas peticiones se hacen.

### Ejecutar

```bash
uv run python app1_agente_unico/07_recorte_de_contexto.py                            # correcta (con recorte)
uv run python app1_agente_unico/07_recorte_de_contexto.py --anti sin_recorte         # los 40 campos
uv run python app1_agente_unico/07_recorte_de_contexto.py --repeat 5 --budget 0.10   # varias ejecuciones
```

**Si ejecutas:** el recorte, el bucle con el `usage` de cada petición y la comprobación de la respuesta se prueban sin modelo. Ejecutar sirve para ver la curva de tokens real, que depende de las peticiones que haga el modelo. Con Haiku 5.5 cada ejecución cuesta unos 0,002 $ con recorte y 0,006 $ sin él, muy por debajo del tope.

Modo normal: cambia `KEEP_FIELDS` por cuatro campos y mira qué pregunta deja de poder responderse.

### Qué observar

La línea `[medida]`: cuántas peticiones hubo, los tokens de entrada en total y el máximo de una sola petición, cuántos campos traía cada resultado, y si las dos respuestas siguen siendo correctas.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

**Tus predicciones:**

- **P1** Crece en cada petición, porque los resultados se acumulan en el historial y este se reenvía entero (TS 5.1-K3, 5.1-K4). El máximo llega al final: la petición de la segunda pregunta lleva todo lo acumulado en la primera.
- **P2** Antes de que entre en el historial (TS 5.1-S3). Una instrucción de ignorarlos deja los campos en el contexto: el modelo los sigue leyendo en cada petición y el consumo no baja.
- **P3** En menos: unas 3,4 veces en el total. El *system prompt*, las definiciones de las tools, las preguntas y las respuestas pesan igual en las dos variantes.
- **P4** No: las dos respuestas fueron correctas con y sin recorte. La señal de este módulo es de tokens, no de calidad.
- **P5** Casi igual, el recorte (lo hace el código) y la proporción de tokens entre variantes. Puede variar el número de peticiones, que lo decide el modelo.

Haiku 5.5 (2026-11-07, 5 ejecuciones por variante). En todas hubo 11 peticiones: la lista, una consulta por equipo, la respuesta a la primera pregunta y la respuesta a la segunda.

| Variante | Campos por resultado | Tokens de entrada en total | Máximo en una petición | Respuestas correctas |
| :--- | :--- | :--- | :--- | :--- |
| correcta | 5 | 14 864 – 17 071 | 2 078 – 2 400 | 5/5 y 5/5 |
| `sin_recorte` | 40 | 53 319 – 54 607 | 9 076 – 9 209 | 5/5 y 5/5 |

- **Estable:** el recorte es determinista y la diferencia de tokens es de unas 3,4 veces en el total y de unas 4,2 en el máximo (medias de las cinco ejecuciones), menos que la proporción de campos porque (lectura propia) el *system prompt*, las tools, las preguntas y las respuestas pesan igual en las dos variantes. El máximo llega al final: la petición de la segunda pregunta, que no llama a ninguna tool, lleva todo lo acumulado en la primera.
- **Sin pérdida de acierto, en ninguna de las dos:** con cinco campos ambas respuestas son correctas en 5/5, porque la pregunta solo usa esos campos. Sin recorte también lo son, así que la medida no muestra que los campos sobrantes empeoren la respuesta: la señal del módulo es de tokens, no de calidad. Que recortar un campo necesario la rompa es lo previsible, pero no se ha medido (es la prueba del modo normal).
- **Lo que decide el modelo:** cuántas peticiones hace. Con menos peticiones (varias consultas en una), el total bajaría en las dos variantes; lo que el recorte cambia es cuánto pesa cada resultado en todas las peticiones que vienen detrás.
- **Límite de la comprobación:** cuenta el equipo que se nombra primero, porque la respuesta correcta suele añadir «le siguen…» con otros equipos. Busca por ID antes que por nombre y exige la mayúscula del nombre, así que el ID manda aunque solo un equipo lo lleve y la mayúscula pierde algún acierto; no lee el sentido de la frase. Los cuatro límites están detallados en «Comprobación de la respuesta» (arriba) y fijados en tests. Las correcciones que tuvo están en [`docs/hallazgos.md`](../docs/hallazgos.md), tanda D.

Producto observado (no evaluable): se le pidió una consulta por turno y Haiku 5.5 lo cumplió en las 10 ejecuciones (11 peticiones en todas).

Clasificación por tipo de señal en [`docs/tipos-de-senal.md`](../docs/tipos-de-senal.md): el recorte es determinista y los tokens medidos son probabilísticos con control positivo.
</details>

### Pregunta tipo examen

Un agente de pedidos consulta una tool que devuelve más de 40 campos por pedido, aunque solo 5 hacen falta para responder a los clientes. Tras varias consultas, la conversación consume muchos tokens y se acerca al límite de contexto. ¿Qué cambio es más adecuado?

- A. Indicar en el *system prompt* que el agente ignore los campos que no necesita y que no los mencione en sus respuestas a los clientes.
- B. Resumir el historial completo cada cinco peticiones, sustituyendo los resultados de tools antiguos por una frase corta de lo que contenían.
- C. Cambiar a un modelo con una ventana de contexto mayor, para que quepan los resultados completos de todos los pedidos consultados.
- D. Recortar en el código la salida de la tool a los campos relevantes antes de que el resultado se añada al historial de la conversación.

<details>
<summary>Paso 4 · Respuesta</summary>

**D.** Los resultados de las tools se acumulan en el contexto y consumen tokens de forma desproporcionada a lo que aportan (TS 5.1-K3); la destreza es recortarlos a los campos relevantes antes de que se acumulen (TS 5.1-S3).

- **A** deja los 40 campos en el historial: el modelo los sigue leyendo en cada petición, así que no reduce el consumo (inferencia a partir de 5.1-K3).
- **B** actúa cuando los resultados ya se han acumulado, y resumir arriesga condensar cifras, fechas y estados en frases vagas (TS 5.1-K1).
- **C** no corrige el consumo desproporcionado: solo retrasa el momento de llegar al límite.
- **D** recorta en el punto que pide la guía, antes de que el resultado entre en el contexto.
</details>

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).
