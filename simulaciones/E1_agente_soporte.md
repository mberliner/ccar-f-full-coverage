<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Revisado por una instancia independiente (3.9, 2026-11-14) y corregido en 3.10 (2026-11-15).
-->
# E1 · Agente de resolución de la mesa de ayuda

> **Escenario:** E1
> **Dominios principales:** D1 · D2 · D5
> **Preguntas:** 9
> **Tiempo orientativo:** 18 minutos

## Contexto

Una tienda en línea monta con el Claude Agent SDK un agente que atiende el chat de la mesa de ayuda. Le llegan devoluciones, cargos duplicados, cambios de dirección y cuentas bloqueadas, muchas veces mezclados en un mismo mensaje y contados a medias. El agente consulta los sistemas internos a través de un servidor MCP propio con cuatro tools: `get_customer` (ficha del cliente), `lookup_order` (pedido), `process_refund` (reembolso) y `escalate_to_human` (pasa el caso a una persona del equipo de segundo nivel). Las conversaciones son largas: un mismo cliente puede abrir varios temas y volver a ellos al cabo de muchos turnos. Cada tool viene de un sistema distinto y devuelve los datos con su propio formato.

## Restricciones compartidas

- R1: el objetivo es resolver al primer contacto al menos el 80 % de los casos, sin quedarse con los que no le corresponden.
- R2: no se reembolsa nada sin un cliente verificado, y ningún reembolso de más de 300 € sale sin aprobación humana; las dos reglas no admiten excepciones.
- R3: quien recibe un caso escalado no ve la conversación con el agente, solo lo que este le manda.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 1.4 | una respuesta |
| 2 | TS 1.4 | multiple-response |
| 3 | TS 1.5 | una respuesta |
| 4 | TS 1.5 | multiple-response |
| 5 | TS 2.1 | una respuesta |
| 6 | TS 2.2 | una respuesta |
| 7 | TS 2.2 | multiple-response |
| 8 | TS 5.1 | una respuesta |
| 9 | TS 5.2 | una respuesta |

## Preguntas

### Pregunta 1 (TS 1.4 · una respuesta)

A mitad de un caso de cargo duplicado, el agente decide escalar. La persona de segundo nivel se queja de que tiene que volver a preguntar al cliente quién es y qué ha pasado, y el cliente repite toda la historia. ¿Qué cambio en la llamada a `escalate_to_human` lo resuelve mejor?

- A. Pasar en la llamada el último mensaje del cliente, que suele resumir lo que necesita.
- B. Pedir al cliente, antes de escalar, que escriba un resumen para el equipo humano.
- C. Pasar un resumen estructurado: cliente, causa raíz, importe y acción recomendada.
- D. Escalar antes, en el primer turno, para que el humano lleve el caso desde el inicio.

<details>
<summary>Respuesta</summary>

**C.** Como el humano no ve la conversación (R3), el escalamiento a mitad de proceso tiene que llevar un traspaso estructurado con los datos del cliente, el análisis de la causa y la acción recomendada (TS 1.4-K3), compilado por el agente (TS 1.4-S3). A deja fuera lo que el agente ya averiguó con las tools. B traslada al cliente el trabajo que el traspaso debe hacer y vuelve a pedirle la historia. D renuncia a resolver casos que sí podría cerrar, en contra de R1, y no cambia lo que recibe el humano.
</details>

### Pregunta 2 (TS 1.4 · multiple-response)

Un cliente escribe en un solo mensaje que le han cobrado dos veces el pedido 4417, que el pedido 4502 llegó con una pieza rota y que quiere cambiar su dirección de envío. El agente atiende solo el primer tema y da la conversación por cerrada. **Selecciona dos** cambios que siguen el patrón de la guía para este tipo de petición. Evalúa cada opción por separado.

- A. Separar la petición en tres asuntos distintos antes de empezar a investigar ninguno.
- B. Pedir al cliente que abra una conversación nueva para cada uno de los tres asuntos.
- C. Resolver el asunto más urgente y anotar los otros dos para un contacto posterior.
- D. Investigar los asuntos en paralelo con contexto común y dar una resolución unificada.

<details>
<summary>Respuesta</summary>

**A y D.** Descomponer la petición con varios asuntos y luego investigarlos en paralelo, con contexto compartido, antes de sintetizar una sola resolución (TS 1.4-S2).

- **A** Correcta: el primer paso del patrón es descomponer la petición en asuntos distintos (TS 1.4-S2).
- **B** Incorrecta: devuelve al cliente la descomposición y multiplica los contactos, en contra de R1.
- **C** Incorrecta: deja dos asuntos sin resolver en el primer contacto, que es justo el fallo observado.
- **D** Correcta: cada asunto se investiga en paralelo con el contexto común y se cierra con una resolución unificada (TS 1.4-S2).
</details>

### Pregunta 3 (TS 1.5 · una respuesta)

`get_customer` devuelve la fecha de alta como un número de ocho cifras con año, mes y día pegados (`20250314`), `lookup_order` devuelve las fechas como texto «mes/día/año» y el estado del pedido como una sola letra (`E`, `D`, `R`). El agente calcula mal si una devolución está dentro de plazo y confunde estados. ¿Qué cambio corrige el problema antes de que el modelo razone sobre esos datos?

- A. Un hook PostToolUse que convierta fechas y estados a un formato común.
- B. Una instrucción en el prompt que explique cómo leer cada formato de fecha.
- C. Ejemplos en el prompt con fechas ya convertidas en cada uno de los formatos.
- D. Un hook sobre las llamadas salientes que rechace las fechas sin normalizar.

<details>
<summary>Respuesta</summary>

**A.** Un hook PostToolUse intercepta el resultado de la tool y lo transforma antes de que el modelo lo procese (TS 1.5-K1), que es el patrón para normalizar formatos heterogéneos de distintas tools MCP (TS 1.5-S1). B y C dejan la conversión al modelo, que es donde está fallando. D actúa sobre las llamadas que salen, no sobre los resultados que vuelven, y rechazar no convierte nada.
</details>

### Pregunta 4 (TS 1.5 · multiple-response)

El prompt del sistema dice que los reembolsos de más de 300 € no se procesan sin aprobación humana (R2). En una muestra de conversaciones, el agente llamó varias veces a `process_refund` con importes de 340 € y 410 €. **Selecciona dos** afirmaciones correctas sobre cómo hacer cumplir R2. Evalúa cada opción por separado.

- A. Repetir la regla al principio y al final del prompt basta para garantizarla.
- B. Un hook que intercepte `process_refund` puede bloquear la llamada que supere 300 €.
- C. Al bloquearla, el hook puede redirigir el caso a escalar con una persona del equipo.
- D. Un hook PostToolUse sobre `process_refund` impide que se ejecute el reembolso.

<details>
<summary>Respuesta</summary>

**B y C.** La regla no admite excepciones, así que se hace cumplir con un hook sobre la llamada saliente que la bloquea y deriva el caso.

- **A** Incorrecta: una instrucción en el prompt da un cumplimiento probabilístico; cuando la regla de negocio exige garantía, se elige un hook (TS 1.5-K3, TS 1.5-S3).
- **B** Correcta: los hooks que interceptan las llamadas salientes hacen cumplir reglas como bloquear reembolsos por encima de un umbral (TS 1.5-K2).
- **C** Correcta: el hook bloquea la acción que viola la política y la redirige a otro flujo, como el escalamiento humano (TS 1.5-S2).
- **D** Incorrecta: PostToolUse actúa sobre el resultado de la tool, cuando el reembolso ya se ha ejecutado (TS 1.5-K1).
</details>

### Pregunta 5 (TS 2.1 · una respuesta)

Las descripciones de las cuatro tools se reescribieron y ya distinguen bien cuándo usar cada una. Aun así, cuando el cliente pregunta «¿dónde está el pedido de mi cuenta?», el agente llama a `get_customer` en lugar de `lookup_order`. El prompt del sistema incluye: «Si el cliente menciona su cuenta, consulta siempre la ficha del cliente». ¿Qué conviene revisar primero?

- A. Las descripciones de las tools, para añadir más ejemplos de preguntas de pedido.
- B. El modelo, porque las descripciones bien escritas deberían bastar por sí solas.
- C. Los nombres de las tools, para que no compartan ninguna palabra con el prompt.
- D. La instrucción del prompt, que asocia la palabra «cuenta» con una tool concreta.

<details>
<summary>Respuesta</summary>

**D.** Una instrucción del prompt sensible a una palabra clave puede crear asociaciones con una tool que nadie pretendía (TS 2.1-K4) y pasar por encima de descripciones bien escritas; por eso se revisa el prompt en busca de esas instrucciones (TS 2.1-S4). A insiste en las descripciones, que el enunciado ya da por buenas. B ignora la causa que está a la vista en el prompt. C no toca la instrucción que provoca la asociación.
</details>

### Pregunta 6 (TS 2.2 · una respuesta)

Para un cliente verificado, `lookup_order` responde a veces con una lista vacía y otras veces agota el tiempo de espera; en los dos casos el agente le dice al cliente que no tiene pedidos. ¿Qué diseño de la respuesta de la tool permite al agente actuar bien en cada caso?

- A. Devolver una lista vacía en los dos casos y dejar que el agente vuelva a consultar.
- B. Marcar el tiempo agotado como error transitorio reintentable y la lista vacía como éxito.
- C. Marcar los dos casos con `isError` y el mismo mensaje genérico de que algo falló.
- D. Tratar la lista vacía como error de validación para que el agente pida otro dato.

<details>
<summary>Respuesta</summary>

**B.** Un fallo de acceso pide una decisión de reintento y un resultado vacío válido es una consulta correcta sin coincidencias; hay que distinguirlos (TS 2.2-S4). El tiempo agotado es un error transitorio (TS 2.2-K2) y se devuelve como reintentable con metadatos estructurados (TS 2.2-S1). A y C los hacen indistinguibles, y un mensaje genérico impide decidir cómo recuperarse (TS 2.2-K3). D convierte una respuesta válida en un error que no existe.
</details>

### Pregunta 7 (TS 2.2 · multiple-response)

Un cliente pide el reembolso de un pedido entregado hace cuatro meses, fuera del plazo de devolución. Hoy `process_refund` devuelve `isError` con el texto «Operation failed», y el agente lo reintenta tres veces y luego le dice al cliente que hay un problema técnico. **Selecciona dos** cambios en la respuesta de error de la tool. Evalúa cada opción por separado.

- A. Mantener el texto y añadir una pausa creciente entre los reintentos del agente.
- B. Marcar el error como no reintentable para que el agente no repita la llamada.
- C. Devolverlo como resultado correcto sin `isError`, con el motivo en un campo aparte.
- D. Incluir una explicación para el cliente del motivo de negocio que impide el reembolso.

<details>
<summary>Respuesta</summary>

**B y D.** Es un error de negocio, no transitorio: se marca como no reintentable y se acompaña de una explicación que el agente pueda trasladar al cliente.

- **A** Incorrecta: reintentar un error de política es inútil; los metadatos de reintento existen para evitar esos intentos (TS 2.2-K4), y el texto genérico sigue sin explicar nada (TS 2.2-K3).
- **B** Correcta: los incumplimientos de reglas de negocio llevan `retriable: false` (TS 2.2-S2), que evita reintentos inútiles (TS 2.2-K4).
- **C** Incorrecta: el fallo se comunica al agente con el patrón `isError` de MCP (TS 2.2-K1); ocultarlo como éxito confunde un reembolso denegado con uno hecho.
- **D** Correcta: la explicación comprensible para el cliente permite que el agente le comunique bien el motivo (TS 2.2-S2).
</details>

### Pregunta 8 (TS 5.1 · una respuesta)

En una conversación larga, el agente resume el historial cada cierto número de turnos para ahorrar contexto. Tras dos resúmenes, el cliente vuelve al cargo duplicado y el agente ya no recuerda el importe exacto (64,90 €), ni la fecha del cargo, ni que el cliente pidió el abono en la tarjeta original. ¿Qué cambio protege esos datos?

- A. Resumir con menos frecuencia para que cada resumen cubra menos turnos.
- B. Pedir que cada resumen sea más detallado y conserve todas las cifras.
- C. Quitar el resumen y pasar a la API solo los últimos turnos de la conversación.
- D. Llevar importes, fechas y peticiones en un bloque de hechos fuera del resumen.

<details>
<summary>Respuesta</summary>

**D.** El resumen progresivo tiende a diluir cifras, fechas y lo que el cliente espera (TS 5.1-K1); la solución es extraer esos hechos a un bloque persistente de «hechos del caso» que se incluye en cada prompt, fuera del historial resumido (TS 5.1-S1). A y B siguen confiando esos datos al resumen, que es donde se pierden. C rompe la coherencia, que depende de pasar el historial completo en cada petición (TS 5.1-K4).
</details>

### Pregunta 9 (TS 5.2 · una respuesta)

Un cliente da su nombre y su ciudad para consultar un pedido, y `get_customer` devuelve tres fichas que coinciden. Una de ellas tiene un pedido reciente que encaja con lo que cuenta el cliente. ¿Qué debe hacer el agente?

- A. Elegir la ficha con el pedido reciente, que es la que mejor encaja con el relato.
- B. Pedir al cliente un identificador más, como el correo o el número de pedido.
- C. Escalar el caso a una persona, porque la identidad del cliente no está clara.
- D. Mostrar al cliente las tres fichas y pedirle que diga cuál es la suya.

<details>
<summary>Respuesta</summary>

**B.** Con varias coincidencias se pide un identificador adicional en lugar de elegir con una heurística (TS 5.2-K4, TS 5.2-S5). A es justo la selección heurística que la guía descarta, y con R2 un error de identidad puede acabar en un reembolso a otro cliente. C escala un caso que el agente puede resolver con una pregunta, en contra de R1. D no pide ningún identificador adicional: deja la elección al cliente sin un dato que la verifique, y R2 exige un cliente verificado.
</details>
