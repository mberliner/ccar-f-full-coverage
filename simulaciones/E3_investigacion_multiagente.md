<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Pendiente de revisión por una instancia distinta de la que lo escribió (paquete 3.9 del plan de mejoras).
-->
# E3 · Informes de investigación con varios agentes

> **Escenario:** E3
> **Dominios principales:** D1 · D2 · D5
> **Preguntas:** 9
> **Tiempo orientativo:** 18 minutos

## Contexto

El equipo de calidad de la mesa de ayuda quiere informes periódicos sobre temas amplios, como «qué hace que un cliente vuelva a abrir una incidencia». Para ello monta con el Claude Agent SDK un sistema de investigación con un agente coordinador y cuatro subagentes: uno busca en la web, otro analiza documentos internos (actas, encuestas y estudios en PDF), otro sintetiza los hallazgos y el último redacta el informe final. Cada subagente tiene su propia definición, con su descripción, su prompt de sistema y sus tools. El informe final llega a responsables que lo usan para decidir cambios de proceso, así que tiene que cubrir el tema de forma amplia y decir de dónde sale cada dato.

## Restricciones compartidas

- R1: cada afirmación del informe final conserva su fuente (URL o documento, y página o fragmento) desde el subagente que la encontró.
- R2: el fallo de una fuente no detiene el informe; el informe dice qué áreas quedaron sin cubrir y por qué.
- R3: los subagentes no se comunican entre sí; todo intercambio pasa por el coordinador, que lo registra.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 1.2 | una respuesta |
| 2 | TS 1.3 | una respuesta |
| 3 | TS 1.3 | multiple-response |
| 4 | TS 2.3 | una respuesta |
| 5 | TS 2.3 | una respuesta |
| 6 | TS 5.3 | una respuesta |
| 7 | TS 5.3 | multiple-response |
| 8 | TS 5.6 | una respuesta |
| 9 | TS 5.6 | una respuesta |

## Preguntas

### Pregunta 1 (TS 1.2 · una respuesta)

En el informe sobre reaperturas, el subagente de síntesis deja escrito que no encontró nada sobre los clientes que reabren por teléfono, aunque ese canal aparece en varios documentos internos. El coordinador ya ha recibido esa síntesis. ¿Qué debería hacer a continuación para cumplir el objetivo de cobertura amplia?

- A. Pasar la síntesis al redactor y añadir una nota al pie sobre el canal telefónico.
- B. Repetir la búsqueda web completa con el mismo encargo, por si la primera falló.
- C. Volver a encargar búsqueda y análisis sobre ese hueco y sintetizar de nuevo después.
- D. Pedir al sintetizador que complete el hueco con lo que sepa del canal telefónico.

<details>
<summary>Respuesta</summary>

**C.** La guía describe un bucle de refinamiento en el que el coordinador evalúa la síntesis en busca de huecos, vuelve a delegar en los subagentes de búsqueda y análisis con consultas dirigidas y vuelve a invocar la síntesis hasta que la cobertura basta (TS 1.2-S3). A se resigna al hueco aunque hay material disponible. B repite el mismo encargo sin dirigirlo al hueco. D pide al sintetizador que invente contenido sin fuentes, lo que además rompe R1.
</details>

### Pregunta 2 (TS 1.3 · una respuesta)

El subagente de síntesis devuelve un texto genérico sin ninguna de las cifras que los subagentes de búsqueda y de análisis acababan de entregar al coordinador. El prompt con que el coordinador lo invoca solo dice «Sintetiza los hallazgos sobre reaperturas». ¿Cuál es la causa más probable?

- A. El sintetizador no recibe los hallazgos: el coordinador debe incluirlos en su prompt.
- B. El sintetizador necesita más turnos para leer el historial del coordinador por sí mismo.
- C. Los subagentes de búsqueda y análisis deberían escribir directamente al sintetizador.
- D. El prompt de sistema del sintetizador es demasiado corto y le faltan ejemplos de estilo.

<details>
<summary>Respuesta</summary>

**A.** Un subagente no hereda el contexto del agente padre: lo que necesita se le da de forma explícita en el prompt (TS 1.3-K2), y la guía pone como ejemplo pasar los resultados de búsqueda y de análisis completos al subagente de síntesis (TS 1.3-S1). B da por hecho que el subagente puede ver el historial del coordinador, que es justo lo que no ocurre. C rompe R3 y el patrón de hub-and-spoke. D atribuye a un problema de estilo lo que es falta de datos.
</details>

### Pregunta 3 (TS 1.3 · multiple-response)

El equipo quiere que el coordinador lance a la vez el subagente de búsqueda web y el de análisis de documentos, porque sus encargos no dependen uno del otro. **Selecciona dos** afirmaciones correctas sobre cómo conseguirlo. Evalúa cada opción por separado.

- A. Basta con que cada subagente tenga una descripción clara en su definición.
- B. Las herramientas permitidas del coordinador tienen que incluir la tool `Task`.
- C. Conviene lanzar cada subagente en un turno distinto para que no se mezclen.
- D. El coordinador emite varias llamadas a la tool `Task` en una misma respuesta.

<details>
<summary>Respuesta</summary>

**B y D.** Los subagentes se lanzan con la tool `Task`, que tiene que estar entre las herramientas permitidas del coordinador, y el paralelo se obtiene emitiendo varias llamadas en la misma respuesta.

- **A** Incorrecta. La descripción ayuda a elegir el subagente (TS 1.3-K3), pero sin `Task` permitida el coordinador no puede invocarlo, y no dice nada del paralelo.
- **B** Correcta. `allowedTools` debe incluir `"Task"` para que un coordinador invoque subagentes (TS 1.3-K1).
- **C** Incorrecta. Repartir las llamadas en turnos distintos las ejecuta en serie, que es justo lo que la guía contrapone al paralelo (TS 1.3-S3).
- **D** Correcta. Varias llamadas a `Task` en una sola respuesta del coordinador lanzan los subagentes en paralelo (TS 1.3-S3).
</details>

### Pregunta 4 (TS 2.3 · una respuesta)

Para ahorrar configuración, todos los subagentes comparten la misma lista de 16 tools. En los registros se ve que el sintetizador lanza búsquedas web por su cuenta cuando duda de un dato, lo que alarga cada informe y mezcla fuentes no analizadas. Sí es frecuente que necesite comprobar un dato puntual. ¿Qué cambio resuelve mejor el problema?

- A. Añadir al prompt de sistema del sintetizador una prohibición de usar la búsqueda web.
- B. Dejar las 16 tools y forzar con `tool_choice` que el sintetizador no llame a ninguna.
- C. Quitar la búsqueda web a todos los subagentes y dejar que el coordinador la haga solo.
- D. Dar al sintetizador solo sus tools más una de verificación acotada para datos puntuales.

<details>
<summary>Respuesta</summary>

**D.** La guía pide restringir las tools de cada subagente a su papel para evitar el mal uso fuera de su especialidad (TS 2.3-S1, TS 2.3-K2) y dar una tool acotada entre roles para necesidades frecuentes, como una de verificación para el sintetizador, enviando los casos complejos al coordinador (TS 2.3-S3). A deja la tool disponible y confía en una instrucción. B no es un uso de `tool_choice` que describa la guía y le quita al sintetizador lo que sí necesita. C le quita la búsqueda también al subagente que la necesita.
</details>

### Pregunta 5 (TS 2.3 · una respuesta)

El subagente de análisis de documentos debe registrar siempre los metadatos de cada PDF (título, fecha y páginas) antes de usar sus otras tools de extracción. En algunas ejecuciones empieza directamente por la extracción y los metadatos faltan. ¿Qué configuración asegura que la primera llamada sea la de metadatos?

- A. `tool_choice: "auto"` y una frase en el prompt que pida empezar por los metadatos.
- B. Forzar en el primer turno la tool de metadatos y seguir con el resto en turnos siguientes.
- C. `tool_choice: "any"`, que obliga a llamar a una tool en lugar de responder con texto.
- D. Quitar las tools de extracción y pedir los metadatos en el prompt del coordinador.

<details>
<summary>Respuesta</summary>

**B.** Para asegurar que una tool concreta se llama primero, la guía indica la selección forzada (`{"type": "tool", "name": "..."}`) y procesar los pasos siguientes en turnos posteriores (TS 2.3-S4, TS 2.3-K4). A sigue dejando la elección al modelo. C garantiza que se llame alguna tool, pero no cuál (TS 2.3-S5). D deja al subagente sin las tools que su papel necesita.
</details>

### Pregunta 6 (TS 5.3 · una respuesta)

La búsqueda web agota el tiempo de espera con una de las fuentes. El subagente devuelve al coordinador una lista vacía marcada como éxito, y el informe final dice que «no hay estudios externos sobre el tema». Según R2, ¿qué debería haber devuelto el subagente?

- A. Un estado genérico «búsqueda no disponible» para que el coordinador reintente después.
- B. Un error que cancele el informe entero, porque sin esa fuente el resultado no es fiable.
- C. Un error estructurado con el tipo de fallo, la consulta intentada y los resultados parciales.
- D. La misma lista vacía, pero con una nota de texto libre en el resumen para el redactor.

<details>
<summary>Respuesta</summary>

**C.** Un contexto de error estructurado (tipo de fallo, lo que se intentó, resultados parciales y alternativas) permite al coordinador decidir cómo recuperarse (TS 5.3-K1, TS 5.3-S1). Devolver vacío como éxito suprime el error en silencio, y cancelar todo el flujo por un fallo es el otro anti-patrón (TS 5.3-K4): esto descarta D y B. A es un estado genérico que oculta el contexto que el coordinador necesita (TS 5.3-K3).
</details>

### Pregunta 7 (TS 5.3 · multiple-response)

El equipo revisa cómo informan de sus resultados los subagentes de búsqueda y de análisis. **Selecciona dos** prácticas que la guía recomienda. Evalúa cada opción por separado.

- A. Distinguir un fallo de acceso de una consulta que funcionó y no encontró coincidencias.
- B. Propagar al coordinador cada fallo en cuanto ocurre, sin intentar ninguna recuperación.
- C. Recuperar en local los fallos pasajeros y propagar solo los que no se pueden resolver.
- D. Unificar todos los fallos en un único código de error para que el coordinador los trate igual.

<details>
<summary>Respuesta</summary>

**A y C.** El coordinador decide bien si sabe qué tipo de resultado recibe y si solo le llegan los fallos que el subagente no pudo resolver.

- **A** Correcta. Un fallo de acceso pide decidir si se reintenta; un resultado vacío válido es una respuesta (TS 5.3-K2, TS 5.3-S2).
- **B** Incorrecta. La guía pide recuperación local de los fallos pasajeros antes de propagar (TS 5.3-S3).
- **C** Correcta. Se recupera en local lo pasajero y se propaga lo que no se resuelve, con lo intentado y los resultados parciales (TS 5.3-S3).
- **D** Incorrecta. Un estado genérico oculta al coordinador el contexto que necesita para recuperarse (TS 5.3-K3).
</details>

### Pregunta 8 (TS 5.6 · una respuesta)

Dos fuentes creíbles dan cifras distintas del porcentaje de incidencias reabiertas en el sector: una encuesta interna de la mesa de ayuda y un estudio externo. Las dos tienen fecha del mismo trimestre. ¿Cómo debe tratarlas el sistema?

- A. Incluir los dos valores como conflicto anotado, cada uno con su fuente atribuida.
- B. Quedarse con el valor del estudio externo, porque una fuente ajena suele ser más neutral.
- C. Publicar la media de los dos valores, que reparte el error entre ambas fuentes por igual.
- D. Omitir la cifra en el informe, porque dos fuentes que discrepan no permiten afirmar nada.

<details>
<summary>Respuesta</summary>

**A.** Ante estadísticas en conflicto de fuentes creíbles, la guía pide anotar el conflicto con la atribución de cada fuente en lugar de elegir un valor arbitrariamente (TS 5.6-K3), y completar el análisis con los valores en conflicto anotados para que el coordinador decida cómo reconciliarlos antes de la síntesis (TS 5.6-S3). B y C eligen o fabrican un valor y pierden la atribución que pide R1. D pierde información que el informe debería presentar como disputada.
</details>

### Pregunta 9 (TS 5.6 · una respuesta)

En otro informe, el sintetizador marca como contradictorias dos cifras de tiempo medio de resolución: una de un estudio de hace cuatro años y otra de un panel actual. Ninguno de los hallazgos que recibió incluía la fecha de los datos. ¿Qué cambio evita este error?

- A. Pedir al sintetizador que descarte siempre la cifra más antigua cuando haya dos valores.
- B. Pedir al redactor que añada al final del informe una nota general sobre posibles desfases.
- C. Dejar que el sintetizador busque por su cuenta la fecha de cada fuente cuando dude de ella.
- D. Exigir a los subagentes la fecha de publicación o recogida en su salida estructurada.

<details>
<summary>Respuesta</summary>

**D.** Pedir las fechas de publicación o de recogida en las salidas estructuradas evita que una diferencia temporal se interprete como contradicción (TS 5.6-K4, TS 5.6-S4). A descarta datos sin saber si se contradicen. B no corrige la síntesis y no dice qué cifra corresponde a qué momento. C da al sintetizador una búsqueda fuera de su papel, lo que la guía señala como mal uso (ver TS 2.3-K2).
</details>
