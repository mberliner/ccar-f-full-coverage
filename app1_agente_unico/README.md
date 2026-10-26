# app1 · Agente único

Un agente, sus tools y su bucle: la base sobre la que se apoyan app2 y app3. El dominio es una mesa de ayuda TI con datos sintéticos (`datos/sinteticos/`).

## Ruta de lectura

Cada módulo sigue el ciclo de `README.md` del proyecto: **predecir → ejecutar (correcto y `--anti`) → contrastar → responder la pregunta → anotar los fallos en tu `FALLOS.md` (`estado/<perfil>/`)**.

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_bucle_manual.py`](01_bucle_manual.py) | TS 1.1-K1, K2, K3, S1, S2, S3 · TS 5.1-K4 | 1 |
| [`02_tools_integradas.py`](02_tools_integradas.py) | TS 2.5-K1, K2, K3, K4, S1, S2, S3, S4, S5 | 2 |
| [`03_servidor_mcp.py`](03_servidor_mcp.py) | TS 2.1-K1, K2, K3, K4, S1, S2, S3, S4 | 2 |
| [`04_errores_estructurados.py`](04_errores_estructurados.py) | TS 2.2-K1, K2, K3, K4, S1, S2, S4 | 2 |
| [`05_scoping_y_tool_choice.py`](05_scoping_y_tool_choice.py) | TS 2.3-K1, K4, S4, S5 | 2 |
| [`06_mcp_config.py`](06_mcp_config.py) | TS 2.4-K1, K2, K3, K4, S1, S2, S3, S4, S5 | 2 |
| `07_recorte_de_contexto.py` | TS 5.1-K3, S3 | 3 |

---

## 01 · Bucle manual

```bash
uv run python app1_agente_unico/01_bucle_manual.py                  # correcto
uv run python app1_agente_unico/01_bucle_manual.py --anti texto     # o tope, texto_asistente, sin_historial, arbol_fijo
uv run python app1_agente_unico/01_bucle_manual.py --budget 0.05    # prueba barata (el tope solo baja)
```

El agente atiende el ticket ambiguo «Soy Laura Gómez y necesito que me restablezcáis la contraseña», que no trae `user_id`. Hay dos empleadas con ese nombre, así que necesita encadenar `get_ticket` → `get_user` → `search_kb` y pedir un identificador.

La salida muestra la credencial y las versiones (§11.1), el modelo y el presupuesto con su origen, cada iteración con su `stop_reason` y sus tools, y la causa de la parada.

**Predice antes de ejecutar:**

1. ¿Cuántas iteraciones necesitará la variante correcta? ¿Cuál será su `stop_reason` final?
2. Con `--anti tope` (tope de 2), ¿llegará a pedir el identificador?
3. Con `--anti sin_historial`, ¿qué hará el modelo en la segunda petición?
4. Con `--anti arbol_fijo`, ¿qué devolverá `get_user` y qué respuesta redactará el modelo?

**Qué observar:**

| Variante | Parada | Qué se rompe |
| :--- | :--- | :--- |
| correcta | `end_turn` | — |
| `texto` | la primera vez que el texto dice «terminado», «listo»… | para cuando el modelo comenta, no cuando acaba |
| `tope` | tras 2 iteraciones | corta a mitad del trabajo, sin respuesta final |
| `texto_asistente` | en cuanto hay texto junto a un `tool_use` | el texto «voy a mirar el ticket» no es una respuesta |
| `sin_historial` | red de seguridad (12) | el modelo no ve sus resultados y repite la misma llamada |
| `arbol_fijo` | una llamada al modelo | la secuencia no se adapta: `get_user` falla sin `user_id` y no hay rama para buscar por nombre |

La variabilidad entre ejecuciones es parte de la lección: según la ejecución, el modelo puede no escribir texto junto a sus llamadas, y entonces `texto_asistente` no corta. Las variantes se prueban de forma determinista en `tests/test_app1_01_bucle_manual.py`.

### Pregunta tipo examen

Un agente de soporte construido con la Messages API a veces deja tareas a medias: responde «Perfecto, ya lo tengo» y el bucle termina antes de consultar el sistema de pedidos. El código actual sale del bucle cuando la respuesta contiene un bloque de texto. ¿Qué cambio es el más adecuado?

- A. Añadir al *system prompt* «no escribas texto hasta haber terminado».
- B. Continuar mientras `stop_reason` sea `"tool_use"` y terminar con `"end_turn"`, devolviendo cada `tool_result` al historial.
- C. Buscar frases como «he terminado» o «listo» en el texto para decidir el final.
- D. Fijar un máximo de 5 iteraciones para asegurar que el bucle consulta todas las tools.

<details>
<summary>Respuesta</summary>

**B.** La parada la decide `stop_reason` (TS 1.1-K1, 1.1-S1) y los resultados vuelven al historial con su `tool_use_id` (TS 1.1-K2, 1.1-S2). A intenta arreglar en prosa un error del código de control; C es el anti-patrón de interpretar lenguaje natural y D el de usar un tope como parada principal (TS 1.1-S3). El texto junto a un `tool_use` es comentario, no una señal de fin.
</details>

---

## 02 · Tools integradas

```bash
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda                    # Grep y Glob
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda --anti sin_grep
uv run python app1_agente_unico/02_tools_integradas.py --parte incremental [--anti leer_todo]
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper [--anti solo_nombre]
uv run python app1_agente_unico/02_tools_integradas.py --parte edicion
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper --repeat 3 --budget 0.10   # prueba barata
```

Mismo agente que en `01`, ahora con el Agent SDK y sus tools integradas (`Read`, `Write`, `Edit`, `Grep`, `Glob`). Trabaja sobre una **copia temporal** de `repo_mesa/` (un paquete pequeño de la mesa de ayuda, generado por `datos/generar_sinteticos.py`): `Edit` y `Write` escriben en la copia y los datos sintéticos originales no se tocan nunca. `--anti` solo vale con la parte a la que pertenece.

La salida muestra `[contexto]`, cada llamada con su resultado y, al final de cada petición, `[medida]` (llamadas por tool, número de `Read` y coste) y `[comprobación]` (calculada en código, no leída del texto del modelo).

**Predice antes de ejecutar:**

1. `busqueda`: ¿qué tool usará para localizar el mensaje de error y cuál para listar los tests? ¿Cuántos `Read` hará? Con `--anti sin_grep` no tiene `Grep`: ¿qué hará en su lugar y cuántos `Read` más le costará?
2. `incremental`: ¿por qué archivo empezará y por qué ese? ¿Cuántos `Read` hará la variante correcta frente a `leer_todo`, y cambiará la calidad de la explicación o solo el coste?
3. `wrapper`: `calcular_sla` tiene llamadores que nunca escriben ese nombre. ¿Cuántos de los 4 encontrará cada variante, y qué dirá `solo_nombre` sobre los que le faltan?
4. `edicion`: el ancla `TIMEOUT = 30` aparece dos veces. ¿Qué devolverá el primer `Edit`? ¿Con qué tool se recuperará el agente y qué riesgo corre si reescribe el archivo entero?

**Qué observar:**

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

### Pregunta tipo examen

Un agente de mantenimiento debe encontrar todos los llamadores de `process_refund` antes de cambiar su firma. El módulo `payments/api.py` la reexporta como `issue_refund`, y otros servicios importan `issue_refund` y no el nombre original. ¿Qué enfoque es el más adecuado?

- A. Buscar el texto `process_refund` con `Grep` y dar por llamadores los archivos que devuelva, porque el nombre original identifica todos los usos.
- B. Leer con `Read` cada archivo del directorio de servicios en orden, para que ninguna búsqueda por patrón deje fuera un llamador.
- C. Identificar los nombres con que `payments/api.py` exporta la función y buscar cada uno con `Grep`, juntando los archivos de todas las búsquedas.
- D. Usar `Glob` con el patrón `**/*refund*.py` para dar con los archivos cuyo nombre menciona la función y revisar solo esos.

<details>
<summary>Respuesta</summary>

**C.** Para rastrear una función a través de un módulo *wrapper* se identifican primero todos los nombres exportados y después se busca cada uno (TS 2.5-S5); `Grep` es la tool para el contenido (TS 2.5-K1, 2.5-S1). A pierde los llamadores por alias y parece completa; B es leer todo cuando una búsqueda lo resuelve, contra la exploración incremental (TS 2.5-S4); D confunde `Glob` (rutas, TS 2.5-K2) con una búsqueda de contenido: un llamador no tiene por qué llevar «refund» en su nombre de archivo.
</details>

---

## 03 · Servidor MCP: descripciones de tools

```bash
uv run python app1_agente_unico/03_servidor_mcp.py                          # correcta
uv run python app1_agente_unico/03_servidor_mcp.py --anti minimas           # dos tools solapadas de una línea
uv run python app1_agente_unico/03_servidor_mcp.py --anti palabra_clave     # prompt con una regla por palabra clave
uv run python app1_agente_unico/03_servidor_mcp.py --repeat 3 --budget 0.15 # tasa en 18 peticiones
```

Seis peticiones de mesa de ayuda (dos sobre tickets y cuatro sobre artículos de la base de conocimiento), cada una con su tool esperada. Cada petición es una conversación nueva con `query()` y se registra la **primera** llamada a una tool del servidor `mesa` (`servers/mesa.py`, familia `routing`). La salida da, por petición, la tool esperada y la elegida, y al final la tasa de acierto.

**Predice antes de ejecutar:**

1. Con la variante correcta y sus cuatro tools, ¿qué tasa de acierto esperas? Si alguna petición fallara, ¿qué tendría que tener para confundir al modelo?
2. Con `--anti minimas` solo hay `analyze_content` y `analyze_document`, de una línea cada una. ¿En qué peticiones podrá el modelo guiarse por las palabras de la propia petición, y en cuáles no tendrá ninguna pista?
3. Con `--anti palabra_clave` las descripciones son las buenas y el prompt añade una regla. Cuando las dos cosas apuntan a tools distintas, ¿cuál crees que pesará más? ¿Qué peticiones lo pondrán a prueba?
4. ¿Qué variante esperas más estable entre repeticiones, y por qué?

**Qué observar:**

| Variante | Qué cambia | Acierto observado (Haiku 5.5, 18 peticiones) |
| :--- | :--- | :--- |
| correcta | 4 tools renombradas y divididas, con descripciones de propósito, entrada, ejemplo, casos borde y diferencias | 18/18 |
| `minimas` | 2 tools genéricas con una línea cada una | 15/18: falla `articulo-resumen` siempre |
| `palabra_clave` | las descripciones buenas, pero el prompt dice «si menciona un documento, usa `summarize_article`» | 12/18: las 2 peticiones con «documento» (pasos y verificar) siempre |

Notas:

- **`minimas`:** con un modelo reciente, la caída es moderada. Acierta lo que su vocabulario sugiere (la petición con «documento» va a `analyze_document`) y falla donde la petición no da pista: el resumen de un «artículo». Con un modelo más flojo o más tools solapadas cabe esperar más caída (hipótesis sin comprobar; la variante a repetir sería esta con Haiku 4.5). Lo que se mide aquí es la ambigüedad, no la capacidad: con descripciones reales no hay nada que adivinar.
- **`palabra_clave`:** es la señal más fuerte y estable. La regla del prompt gana a la descripción en las dos peticiones con la palabra, en todas las repeticiones, y deja intacto el resto. La corrección es la configuración correcta: quitar la regla del prompt y confiar en las descripciones.
- **Tool esperada con `minimas`:** como solo hay dos tools, se espera «tickets → `analyze_content`, artículos → `analyze_document`». Es una convención del módulo, no algo que diga la guía.
- Los contratos de cada tool (entrada y salida) y la medida de acierto se prueban sin modelo en `tests/test_app1_servers_mesa.py` y `tests/test_app1_03_servidor_mcp.py`.

### Pregunta tipo examen

Un agente de soporte dispone de dos tools, `analyze_content` y `analyze_document`, descritas como «Analiza contenido.» y «Analiza un documento.». Con frecuencia elige la tool equivocada para peticiones parecidas. ¿Qué cambio es el más adecuado?

- A. Añadir al *system prompt* la regla «si la petición menciona un documento, usa `analyze_document`», para guiar la elección en esos casos.
- B. Fusionar las dos tools en una sola llamada `analyze` que acepte cualquier entrada, para que el modelo no tenga que elegir entre ellas.
- C. Poner un clasificador previo que decida la tool y se la entregue al agente, para que este solo tenga que ejecutarla sin elegir.
- D. Renombrar las tools según su propósito y ampliar sus descripciones con entradas, ejemplos, casos borde y en qué se diferencian de la otra.

<details>
<summary>Respuesta</summary>

**D.** La descripción es el mecanismo con el que el modelo elige (TS 2.1-K1), y las ambiguas o solapadas causan *misrouting* (TS 2.1-K3). La corrección es describir con propósito, entradas y límites (TS 2.1-K2, TS 2.1-S1) y renombrar para quitar el solapamiento (TS 2.1-S2). A es una instrucción por palabra clave que puede anular las descripciones (TS 2.1-K4, TS 2.1-S4): arregla un caso y crea otros. B va al revés de la guía, que divide las tools genéricas en otras de contrato definido (TS 2.1-S3). C añade una pieza para compensar un defecto que se arregla en la descripción; ninguna viñeta de la guía lo propone.
</details>

---

## 04 · Errores estructurados

```bash
uv run python app1_agente_unico/04_errores_estructurados.py                          # correcta
uv run python app1_agente_unico/04_errores_estructurados.py --anti generico          # todos los errores: «Operation failed»
uv run python app1_agente_unico/04_errores_estructurados.py --anti fallo_como_vacio  # el timeout llega como lista vacía
uv run python app1_agente_unico/04_errores_estructurados.py --repeat 5 --budget 0.25
```

Un único mensaje pide cinco tareas al servidor `mesa` (familia `errores`): el histórico de un ticket (**tiempo de espera** la primera vez), el perfil de «1001» (ID mal formado: **validación**), reasignar 12 puestos de licencia (**regla de negocio**: el cupo es 10), exportar el registro de auditoría (**permisos**) y listar los tickets de `EMP-9999` (una **búsqueda sin coincidencias**). El prompt del sistema no dice qué hacer con cada error: lo decide el agente con lo que el error le cuenta.

La salida muestra los reintentos idénticos por tool, cuántos son inútiles, las categorías de error por tool y si el transitorio se recuperó.

**Predice antes de ejecutar:**

1. Con la variante correcta, ¿qué tools se llamarán más de una vez y por qué esas?
2. ¿Cómo explicará el agente el fallo del cupo y el del permiso, y en qué se apoyará para distinguir uno de otro?
3. El perfil se pide con «1001», un ID mal formado. ¿Llegará a producirse el error de validación? ¿De qué depende?
4. Con `--anti generico` todos los errores dicen lo mismo. ¿Reintentará el agente algo que no tiene arreglo? ¿Y dejará de reintentar algo que sí lo tenía?
5. Con `--anti fallo_como_vacio`, ¿qué dirá el agente del histórico del ticket, y habrá un segundo intento?

**Qué observar:**

| Variante | Reintentos | Qué se rompe |
| :--- | :--- | :--- |
| correcta | solo `fetch_ticket_history` (1), que se recupera | — |
| `generico` | `export_audit_log` se repite sin arreglo posible (1 inútil por ejecución) y el transitorio también se reintenta, sin nada que diga que lo es | sin categoría ni `isRetryable`, el agente no distingue lo reintentable de lo que no lo es |
| `fallo_como_vacio` | ninguno: el transitorio no se reintenta | el agente cree que el ticket no tiene histórico (4 de 5) y lo cuenta como un dato |

Notas:

- **Validación:** en las ejecuciones observadas (Haiku 5.5) el modelo corrige «1001» a `EMP-1001` antes de llamar, porque la descripción de la tool dice el formato, y el error de validación no llega a producirse. Su forma se prueba sin modelo (`tests/test_app1_servers_mesa.py`). Es la consecuencia de una buena descripción (TS 2.1-K2), no un defecto del módulo. Con Haiku 4.5 (sonda, 10 ejecuciones) tampoco se vio.
- **`generico` depende del modelo:** con Haiku 4.5 (sonda) no hubo reintentos inútiles, porque no reintentó nada; lo que cambió fue que se rindió ante el *timeout* (lo recuperó 2 de 5 veces con metadatos y 0 de 5 con el error genérico). Muestra pequeña: la señal del módulo es la de Haiku 5.5.
- **`isRetryable` frente a `retriable`:** la guía escribe `retriable: false` para la regla de negocio; el proyecto usa `isRetryable` en todos los errores. Con la regla de negocio, además, el mensaje explica la política para que el agente informe a la persona usuaria (TS 2.2-S2).
- **Vacío válido:** la búsqueda de `EMP-9999` devuelve una lista vacía correcta, que no es un error. Lo que `fallo_como_vacio` rompe es lo contrario: un fallo de acceso disfrazado de lista vacía (TS 2.2-S4).
- Las señales sobre el `RunRecord` (reintentos idénticos, categorías) se prueban sin modelo en `tests/test_app1_04_errores_estructurados.py`. «Dice que no hay histórico» es un detector de texto aproximado; la señal robusta es «transitorio recuperado».

### Pregunta tipo examen

Una tool MCP de reembolsos devuelve «Operation failed» ante cualquier fallo. El agente reintenta tres veces un reembolso rechazado por superar el límite de la política y luego comunica a la persona que hubo un problema técnico. ¿Qué cambio es el más adecuado?

- A. Devolver el error con `isError`, una categoría de regla de negocio, la marca de no reintentable y una explicación legible de la política.
- B. Limitar al agente a un máximo de dos reintentos por tool, para que ningún error se repita más de lo razonable y se acote el gasto.
- C. Añadir al *system prompt* la regla «no reintentes los errores de política y explica la causa», sin cambiar la respuesta de la tool.
- D. Cambiar el mensaje a «Operation failed, please try again later», para que el agente espere un poco antes de volver a intentarlo.

<details>
<summary>Respuesta</summary>

**A.** El fallo se comunica con el flag de error y metadatos estructurados (TS 2.2-K1, TS 2.2-S1): la categoría distingue una regla de negocio de un fallo transitorio (TS 2.2-K2; la guía no da nombre al valor de esa categoría), la marca de no reintentable evita el reintento inútil (TS 2.2-K4; la guía la escribe `retriable: false` en S2 e `isRetryable` en S1) y la explicación de la política permite al agente informar bien (TS 2.2-S2). B pone un tope arbitrario en vez de dar al agente la información, y seguirá reintentando lo que no tiene arreglo; C intenta suplir en prosa lo que debería salir de la tool, y no distingue unos errores de otros; D empeora el problema: invita a reintentar justo lo que no es reintentable. Un mensaje genérico es el anti-patrón (TS 2.2-K3).
</details>

---

## 05 · Scoping y `tool_choice`

```bash
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping                  # 5 tools
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping --anti amplio    # 18 tools
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte tool_choice --repeat 6   # auto, any y forzado
uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping --repeat 5 --budget 0.20
```

Dos partes independientes.

**`scoping` (Agent SDK):** las mismas seis peticiones sobre el servidor `mesa` con la familia `acotado` (5 tools) o `amplio` (18: las mismas 5 más 13 alias casi iguales, como `lookup_ticket` o `get_employee`). Se mide el acierto de la primera llamada (un alias de la tool esperada cuenta como acierto), si la tool elegida cambia entre repeticiones y el coste. La carga diferida de definiciones (*tool search*) se fija en `ENABLE_TOOL_SEARCH=false` por precaución y la salida confirma `cargas diferidas=0`. En las sondas no se activó con ningún valor de la variable, así que no hay prueba de que `false` apague algo: solo de que aquí no interviene (`docs/hallazgos.md`).

**`tool_choice` (Messages API, como `01`):** una misma petición de opinión sobre un ticket («¿crees que este tipo de tickets suelen ser un problema grave?») con `auto`, con `any` y con la tool `extract_ticket_metadata` forzada. En el primer turno va el modo elegido y en los siguientes `auto`, para que el modelo pueda enriquecer y responder. Se imprime con qué empieza cada respuesta.

**Predice antes de ejecutar:**

1. `scoping`: con 18 tools frente a 5, ¿qué esperas que cambie: el acierto, la tool elegida entre repeticiones, el coste? ¿Qué tendrían que tener las peticiones para que el acierto se resintiera?
2. `tool_choice`: con `auto`, ¿cuántas respuestas empezarán por una tool? ¿Y con `any` y con la forzada?
3. ¿Qué tool llamará `any`? ¿Y la forzada?
4. ¿Qué pasaría si `any` o la forzada se enviaran en **todos** los turnos?

**Qué observar (Haiku 5.5):**

| Parte / variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `scoping` 5 tools | acierto 30/30, sin cambios entre repeticiones, ~0,00033 $ por petición | — |
| `scoping` 18 tools (`--anti amplio`) | acierto 30/30, sin cambios, ~0,00045 $ por petición (+36 %) | el acierto no baja, pero cada petición carga 13 definiciones de más |
| `tool_choice` `auto` | 0/6 empiezan por tool: contesta con texto | puede no llamar a ninguna tool |
| `tool_choice` `any` | 6/6 empiezan por tool | garantiza una llamada (cuál, la elige el modelo) |
| `tool_choice` forzado | 6/6 empiezan por `extract_ticket_metadata`, y el turno siguiente (`auto`) enriquece o responde | la tool fijada va primero y el resto sigue en turnos posteriores |

Notas:

- **`scoping`:** la guía dice que 18 tools degradan la fiabilidad de selección; aquí no se vio en el acierto. Con Haiku 5.5 y con Haiku 4.5 (sonda: 18/18 y 18/18) las peticiones son claras y el modelo elige bien. Lo que sí se vio: más coste con 18 tools (+36 % con Haiku 5.5, +58 % con Haiku 4.5) y, con Haiku 4.5, una petición cuya tool cambió entre repeticiones (`get_user` o `get_employee`). Con peticiones más ambiguas o más tools, la degradación de acierto sería previsiblemente más fácil de provocar (hipótesis sin comprobar). En el examen manda la guía.
- **`auto`:** depende de la petición. Con «¿qué te parece?» o «¿es urgente?» Haiku 5.5 sí llamaba a la tool y el contraste no se veía; con una petición de opinión contesta con texto. Ese es el caso que `any` y el forzado resuelven.
- **Un turno, no todos:** el modo forzado o `any` solo va en el primer turno. En todos los turnos, el modelo estaría obligado a llamar a una tool también después de recibir los resultados y no podría dar su respuesta final.
- **En producción (no evaluable):** `any` y la forzada devuelven 400 en Sonnet 5.5 (comprobado) y, según la documentación del repositorio de estudio, en Opus 5.5 y Fable 5.1. Haiku 5.5 y Haiku 4.5 las aceptan. En el examen manda la guía.
- La petición por modo, la secuencia forzado → `auto` y el clasificador de la primera respuesta se prueban sin modelo en `tests/test_app1_05_scoping_y_tool_choice.py`.

### Pregunta tipo examen

Un flujo de soporte necesita extraer los metadatos de cada ticket nuevo antes de enriquecerlo con la base de conocimiento. A veces el asistente responde con texto conversacional y se salta la extracción. ¿Qué configuración es la más adecuada?

- A. Enviar `tool_choice` con el valor `"any"` en todos los turnos, para que el asistente nunca devuelva texto y el flujo siempre avance.
- B. Forzar la extracción con `{"type": "tool", "name": "extract_ticket_metadata"}` en el primer turno y usar `"auto"` en los siguientes.
- C. Añadir al *system prompt* «llama siempre a `extract_ticket_metadata` antes de responder» y mantener `"auto"` en todos los turnos.
- D. Dar al asistente diez tools de enriquecimiento más junto a la de extracción, para que siempre tenga una opción disponible que llamar.

<details>
<summary>Respuesta</summary>

**B.** La selección forzada asegura que una tool concreta se llame primero y los pasos siguientes se procesan en turnos posteriores (TS 2.3-S4, TS 2.3-K4). A fuerza una llamada en cada turno, así que el asistente nunca podría dar su respuesta final, y `"any"` además no fija cuál es la tool (garantiza una llamada, no esa llamada, TS 2.3-S5). C intenta suplir en prosa lo que debe garantizar la configuración: con `"auto"` el modelo puede seguir contestando con texto. D va en contra de TS 2.3-K1: más tools degradan la selección y no aseguran que se llame a la de extracción.
</details>

---

## 06 · Configuración MCP

```bash
uv run python app1_agente_unico/06_mcp_config.py --parte conexion                          # tres servidores y el token
uv run python app1_agente_unico/06_mcp_config.py --parte recursos                          # catálogo como resource
uv run python app1_agente_unico/06_mcp_config.py --parte recursos --anti sin_recursos
uv run python app1_agente_unico/06_mcp_config.py --parte descripcion [--anti descripcion_minima]
uv run python app1_agente_unico/06_mcp_config.py --parte recursos --repeat 4 --budget 0.20
```

El módulo genera, en una copia temporal (el `cwd` del agente), un `.mcp.json` con dos servidores stdio: `catalogo` (`servers/catalogo_stdio.py`) e `inventario`. Los lanza con `uv run --no-sync --project <raíz>` y entrega el token con `"env": {"CATALOGO_TOKEN": "${CCARF_DEMO_TOKEN}"}`: el archivo lleva la **variable**, no el valor, y el módulo pone un valor sintético en el entorno del proceso. El agente se ejecuta con `setting_sources=["project"]` (la excepción al aislamiento: lee el `.mcp.json` del `cwd`, no el del repositorio ni la configuración de usuario).

Tres partes:

- **`conexion`:** además de los dos servidores del `.mcp.json`, el servidor en proceso `mesa`. La petición usa una tool de cada uno. La salida muestra las tools por servidor, si el servidor recibió el token (solo dice sí o no, nunca el valor) y el comando de **ámbito de usuario** (`claude mcp add --scope user …`), que se imprime y no se ejecuta: `~/.claude.json` es personal.
- **`recursos`:** «¿qué artículos hay en el catálogo?» con el catálogo expuesto como *resource* (`kb://catalogo`) frente a `--anti sin_recursos`. Se cuentan las llamadas exploratorias (`search_kb` y `get_article`).
- **`descripcion`:** los artículos están además como archivos en el `cwd`, y el agente tiene `Grep` y `Read` junto a la tool MCP. Se cuentan `Grep` frente a `search_kb`. Con `--anti descripcion_minima` la descripción de `search_kb` es una línea.

**Comunitario frente a propio (TS 2.4-S4), sin código:**

| La integración es… | Servidor | Por qué |
| :--- | :--- | :--- |
| estándar y ya resuelta (Jira, GitHub, Slack) | **comunitario** | se mantiene fuera y se actualiza con su proyecto |
| un flujo de la mesa de ayuda (su catálogo, sus reglas, sus datos) | **propio** | es el único que conoce el dominio y cuyo contrato debe mantener el equipo |

**Predice antes de ejecutar:**

1. `conexion`: ¿verás las tools de los tres servidores a la vez? ¿Qué prefijo llevan?
2. `recursos`: sin avisar de que existen, ¿usará el agente los resources por su cuenta? ¿Cuántas llamadas exploratorias hará sin ellos?
3. `descripcion`: el agente tiene `Grep` y `search_kb` para lo mismo. ¿Qué crees que decidirá cuál usa: la descripción de la tool MCP, saber que los artículos están también como archivos, otra cosa? ¿Cambiará algo con la descripción de una línea?
4. ¿Dónde pondrías un servidor experimental de una sola persona, y dónde uno que debe tener todo el equipo?

**Qué observar (Haiku 5.5):**

| Parte / variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| `conexion` | `mcp=['catalogo','inventario','mesa']`, 9 tools con prefijos `mcp__<servidor>__`, `token_recibido: true`, una llamada ok a cada servidor | todas las tools, a la vez; el token se expande sin escribirse en el archivo |
| `recursos` correcta | 2 llamadas a resources (`ListMcpResourcesTool`, `ReadMcpResourceTool`), 0 exploratorias, ~0,0009 $ | el catálogo da visibilidad de qué hay sin explorar |
| `recursos` `sin_recursos` | 19–31 llamadas exploratorias, 0,0021–0,0033 $ (×2,3–3,7) | el agente adivina con búsquedas y lecturas por ID, incluidos IDs que no existen |
| `descripcion` correcta | `Grep` 0/6, `search_kb` MCP 6/6 | — |
| `descripcion` `descripcion_minima` | `Grep` 0/6, `search_kb` MCP 6/6 | **sin diferencia** con Haiku 5.5 |

Notas:

- **Los resources no los descubre el modelo solo.** Con las tools de resources disponibles pero sin avisar, el agente exploró con búsquedas: la aplicación debe decirle que existen (aquí, una frase en el prompt del sistema). En el SDK se alcanzan con `ListMcpResourcesTool` y `ReadMcpResourceTool`. Es una nota de producto (no evaluable).
- **`descripcion`: la señal que dice la guía no se vio.** Según la guía, una descripción mínima hace que el agente prefiera `Grep`. Con Haiku 5.5 y con Haiku 4.5 (sondas, 6 repeticiones por condición) no cambió la preferencia: sin avisar de que hay archivos, `Grep` salió 0/6 con las dos descripciones, y avisando salió igual de a menudo con una que con otra (4/6 y 5/6 con Haiku 5.5). Lo que movió al agente a `Grep` fue saber que los archivos existían, no la descripción. La viñeta se enseña igualmente (cabecera y pregunta); en el examen manda la guía.
- **`init` puede traer la lista de tools incompleta:** en 2 de unas 8 ejecuciones, los servidores stdio constaban como conectados pero sus tools no estaban aún en `init`; el módulo lo avisa con `[aviso]`. Las llamadas funcionan igualmente.
- **Sin aprobación:** con `setting_sources=["project"]` el SDK conecta los servidores de `.mcp.json` sin pedir aprobación; la CLI interactiva sí puede pedirla.
- El `.mcp.json` generado, el comando de ámbito de usuario, los contadores y la agrupación de tools por servidor se prueban sin modelo en `tests/test_app1_06_mcp_config.py`.

### Pregunta tipo examen

Un agente tiene `Grep` y un servidor MCP propio con una tool `search_kb` que ordena por relevancia y filtra los artículos obsoletos con `superseded_by`. La descripción de la tool es «Busca en la base de conocimiento.» y el agente suele preferir `Grep` sobre los archivos del repositorio. ¿Qué cambio es el más adecuado?

- A. Quitar `Grep` de las tools del agente, para que la única forma de buscar artículos sea la tool del servidor MCP.
- B. Añadir al *system prompt* la regla «usa siempre `search_kb` para buscar artículos» y dejar la descripción como está.
- C. Ampliar la descripción de `search_kb` con sus capacidades y sus salidas: ranking y filtrado de obsoletos con `superseded_by`.
- D. Sustituir el servidor propio por uno comunitario genérico de búsqueda, que ya traerá descripciones más largas.

<details>
<summary>Respuesta</summary>

**C.** Una descripción que detalla capacidades y salidas evita que el agente prefiera una tool integrada sobre una tool MCP más capaz (TS 2.4-S3): lo que decide la elección es lo que el agente ve de cada tool (TS 2.1-K1). A quita una herramienta que el agente sigue necesitando para otras cosas y no arregla la descripción; B es una instrucción en el prompt que compensa una descripción pobre y puede crear asociaciones no deseadas (TS 2.1-K4); D no aplica el criterio de TS 2.4-S4: una búsqueda sobre el catálogo propio de la mesa es un flujo específico del equipo y pide servidor propio.
</details>
