<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Revisado por una instancia independiente (3.9, 2026-11-14) y corregido en 3.10 (2026-11-15).
-->
# E6 · Extracción de datos de los adjuntos de las incidencias

> **Escenario:** E6
> **Dominios principales:** D4 · D5
> **Preguntas:** 9
> **Tiempo orientativo:** 18 minutos

## Contexto

La mesa de ayuda recibe cada día cientos de incidencias de facturación con documentos adjuntos: facturas de proveedores, albaranes y notas de abono, escaneados o en PDF, con formatos muy distintos según el emisor. El equipo de operaciones monta con la API de Claude un extractor que lee cada adjunto y devuelve sus datos (tipo de documento, emisor, fecha, líneas, importes y total) como JSON validado con un esquema. Ese JSON alimenta el sistema contable, que lo concilia sin intervención. Hay tres tools de extracción, una por tipo de documento, y un equipo de revisión de tres personas que no da abasto para mirarlo todo. Además de las incidencias del día, el archivo histórico de adjuntos se reprocesa para completar campos nuevos.

## Restricciones compartidas

- R1: el sistema contable rechaza un JSON que no cumpla el esquema; un dato que el documento no trae no se puede inventar.
- R2: el reprocesado del archivo histórico tiene que estar listo, como mucho, 36 horas después de que entre cada adjunto en el archivo.
- R3: la revisión humana es escasa y se dedica primero a lo que más probablemente esté mal.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 4.3 | una respuesta |
| 2 | TS 4.3 | multiple-response |
| 3 | TS 4.4 | una respuesta |
| 4 | TS 4.4 | una respuesta |
| 5 | TS 4.2 | una respuesta |
| 6 | TS 4.5 | una respuesta |
| 7 | TS 4.5 | multiple-response |
| 8 | TS 5.5 | una respuesta |
| 9 | TS 5.5 | multiple-response |

## Preguntas

### Pregunta 1 (TS 4.3 · una respuesta)

Al extractor le llega un adjunto sin saber si es factura, albarán o nota de abono. Con la configuración actual, a veces responde con un párrafo que describe el documento en lugar de llamar a una de las tres tools, y el sistema contable no recibe nada. ¿Qué ajuste de `tool_choice` lo evita sin decidir de antemano el tipo de documento?

- A. Mantener `tool_choice: "auto"` y pedir en el prompt que use siempre una tool.
- B. Usar `tool_choice: "any"` para que llame a una tool y elija cuál según el adjunto.
- C. Forzar siempre la tool de facturas, que es el tipo de documento más frecuente.
- D. Quitar las tools y pedir que devuelva el JSON como texto dentro de la respuesta.

<details>
<summary>Respuesta</summary>

**B.** Con `"any"` el modelo tiene que llamar a una tool, pero elige cuál, que es lo que pide un documento de tipo desconocido con varios esquemas de extracción (TS 4.3-S2, TS 4.3-K2). A deja `"auto"`, que permite contestar con texto en vez de llamar a la tool, justo el fallo observado. C garantiza una llamada, pero a la tool equivocada para albaranes y notas de abono. D renuncia a la tool use con esquema, que es la vía más fiable para una salida que cumpla el esquema (TS 4.3-K1) y que R1 necesita.
</details>

### Pregunta 2 (TS 4.3 · multiple-response)

En las notas de abono de algunos emisores no aparece la fecha de vencimiento, y el campo es obligatorio en el esquema: el extractor la rellena con fechas verosímiles que no están en el documento. Además, el campo `motivo` es un enum de cinco valores y llegan motivos que no encajan en ninguno. **Selecciona dos** cambios de esquema que resuelven estos problemas. Evalúa cada opción por separado.

- A. Hacer opcional (nullable) la fecha de vencimiento para los documentos que no la traen.
- B. Mantener la fecha obligatoria y pedir en el prompt que no invente ninguna fecha.
- C. Añadir al enum de `motivo` un valor `"other"` con un campo de texto para el detalle.
- D. Quitar el enum de `motivo` y dejarlo como texto libre para admitir cualquier valor.

<details>
<summary>Respuesta</summary>

**A y C.** Campo opcional donde el dato puede faltar y enum extensible con `"other"` más detalle.

- **A** Correcta: un campo opcional (nullable) evita que el modelo fabrique un valor para cumplir un campo obligatorio cuando el documento no lo contiene (TS 4.3-S4), lo que exige R1.
- **B** Incorrecta: mientras el esquema obligue a rellenar la fecha, la presión por cumplirlo sigue ahí; el arreglo está en el diseño del esquema (TS 4.3-K4).
- **C** Correcta: `"other"` con un campo de detalle es el patrón para categorías extensibles (TS 4.3-S5, TS 4.3-K4).
- **D** Incorrecta: el texto libre admite los motivos nuevos, pero pierde la categorización que el sistema contable puede conciliar; el patrón de la guía conserva el enum y lo amplía.
</details>

### Pregunta 3 (TS 4.4 · una respuesta)

En algunas facturas, el número de pedido no aparece en la factura: solo figura en el pedido de compra, que no se adjunta a la incidencia. El validador marca el campo como vacío y el extractor reintenta tres veces, añadiendo el error al prompt, sin éxito. ¿Qué conclusión es la correcta?

- A. Hacen falta más reintentos con el mismo mensaje de error hasta que aparezca el dato.
- B. El mensaje de error del reintento es poco preciso; con uno más concreto se corregiría.
- C. Hay que hacer obligatorio el campo para que el modelo se vea forzado a encontrarlo.
- D. Reintentar no sirve: el dato está en otro documento que no se le ha dado al modelo.

<details>
<summary>Respuesta</summary>

**D.** Los reintentos no funcionan cuando la información no está en el documento fuente, por ejemplo porque solo existe en un documento externo que no se proporcionó; sí funcionan con errores de formato o de estructura (TS 4.4-K2, TS 4.4-S2). A y B insisten en el reintento, que no puede crear un dato ausente. C empuja al modelo a inventar el valor, lo que R1 prohíbe.
</details>

### Pregunta 4 (TS 4.4 · una respuesta)

Todas las extracciones cumplen el esquema, pero contabilidad encuentra facturas en las que la suma de las líneas no coincide con el total extraído: a veces el documento trae un error y a veces el modelo leyó mal una línea. ¿Qué diseño permite detectarlo en el propio flujo de extracción?

- A. Extraer también un total calculado junto al declarado y marcar cuando no coincidan.
- B. Endurecer el esquema JSON con más campos obligatorios para que no haya descuadres.
- C. Cambiar de tool use a texto libre para que el modelo explique cómo sumó las líneas.
- D. Confiar en el esquema estricto, que ya impide que las líneas y el total no cuadren.

<details>
<summary>Respuesta</summary>

**A.** Extraer `calculated_total` junto a `stated_total` (y un booleano como `conflict_detected` si el documento es incoherente) permite señalar las discrepancias y corregirlas (TS 4.4-S4). B y D confunden los dos tipos de error: el esquema estricto elimina los errores de sintaxis, pero no los semánticos, como importes que no suman (TS 4.4-K4). C abandona la salida estructurada que necesita el sistema contable.
</details>

### Pregunta 5 (TS 4.2 · una respuesta)

Las instrucciones del prompt ya explican con detalle dónde suele estar cada dato, pero en los albaranes de los emisores que ponen las cantidades en una tabla al pie, en lugar de en cada línea, el extractor deja vacíos campos obligatorios. ¿Qué cambio en el prompt es el más eficaz?

- A. Repetir las instrucciones en mayúsculas para subrayar que ningún campo quede vacío.
- B. Añadir una lista con todos los emisores conocidos y la posición exacta de sus datos.
- C. Añadir ejemplos de extracción correcta de albaranes con distintas disposiciones.
- D. Partir el albarán en trozos más pequeños y extraer cada uno en una llamada distinta.

<details>
<summary>Respuesta</summary>

**C.** Añadir ejemplos (few-shot) de extracción correcta en documentos con formatos variados es lo que corrige la extracción vacía de campos obligatorios (TS 4.2-S5), y los ejemplos son la técnica más eficaz cuando las instrucciones detalladas solas dan resultados irregulares (TS 4.2-K1). A insiste en instrucciones que ya no bastan. B solo cubre los casos previstos de antemano, mientras que los ejemplos permiten generalizar a disposiciones nuevas (TS 4.2-K3). D no ataca el problema, que es reconocer dónde está el dato.
</details>

### Pregunta 6 (TS 4.5 · una respuesta)

El reprocesado del archivo histórico se pasa a la Message Batches API para ahorrar coste. Cada lote puede tardar hasta 24 horas en procesarse, y se tiene que cumplir R2. ¿Con qué frecuencia hay que enviar lotes?

- A. Una vez al día, con todo lo que entró en el archivo en las 24 horas anteriores.
- B. Una vez por semana, para aprovechar al máximo el descuento por volumen del lote.
- C. Cada 14 horas, con todo lo que entró en el archivo desde el envío anterior.
- D. Cada 10 horas, con todo lo que entró en el archivo desde el envío anterior.

<details>
<summary>Respuesta</summary>

**D.** La frecuencia se calcula a partir del SLA: si el procesamiento puede durar 24 horas y el límite es 36, un adjunto no puede esperar más de 12 horas al siguiente envío. Cada 10 horas, la espera más larga (casi 10) más el lote (24) suman como mucho 34 horas, dentro de R2 (TS 4.5-S2, TS 4.5-K1). A deja que un adjunto espere casi 24 horas, que con otras 24 de lote suma casi 48. B incumple R2 con mucha más holgura. C suma casi 14 más 24, unas 38 horas, por encima de 36.
</details>

### Pregunta 7 (TS 4.5 · multiple-response)

En el primer lote con el archivo completo, un 8 % de las solicitudes falla: unas por documentos demasiado largos para el contexto y otras por un prompt que todavía se equivoca con las notas de abono. **Selecciona dos** prácticas que reducen el coste de volver a procesar. Evalúa cada opción por separado.

- A. Reenviar el lote completo con el prompt corregido para tener un resultado uniforme.
- B. Reenviar solo las solicitudes fallidas, por su `custom_id`, partiendo las demasiado largas.
- C. Pasar el reprocesado a la API síncrona, que permite reintentar al momento cada fallo.
- D. Afinar el prompt con una muestra del archivo antes de enviar el siguiente lote grande.

<details>
<summary>Respuesta</summary>

**B y D.** Reenviar solo lo fallido y afinar el prompt con una muestra antes del volumen.

- **B** Correcta: los fallos se reenvían solos, identificados por `custom_id`, con el ajuste que necesiten, como trocear los documentos que excedieron el contexto (TS 4.5-S3, TS 4.5-K4).
- **D** Correcta: refinar el prompt sobre un conjunto de muestra antes de procesar grandes volúmenes maximiza el acierto a la primera y reduce el coste de reenviar (TS 4.5-S4).
- **A** Incorrecta: vuelve a pagar el 92 % que ya había salido bien.
- **C** Incorrecta: el reprocesado tolera la espera, así que es carga de lote; la API síncrona se reserva a los flujos que bloquean (TS 4.5-K2, TS 4.5-S1) y se pierde el ahorro del lote.
</details>

### Pregunta 8 (TS 5.5 · una respuesta)

Tras un mes, el extractor acierta el 94 % de los campos en el conjunto de validación etiquetado, y dirección propone dejar de revisar las extracciones de alta confianza. ¿Qué hay que comprobar antes de aceptarlo?

- A. Que la precisión se mantenga por tipo de documento y por campo, no solo en conjunto.
- B. Que el 94 % se repita durante un segundo mes con el mismo conjunto de validación.
- C. Que el modelo declare una confianza alta en al menos el 94 % de las extracciones.
- D. Que el sistema contable no haya rechazado ningún JSON por incumplir el esquema.

<details>
<summary>Respuesta</summary>

**A.** Una precisión agregada puede esconder un mal rendimiento en tipos de documento o campos concretos, así que hay que validar la precisión por tipo de documento y por segmento de campo antes de automatizar las extracciones de alta confianza (TS 5.5-K1, TS 5.5-K4, TS 5.5-S2). B repite la misma cifra agregada. C mide lo que el modelo dice de sí mismo, no su acierto. D comprueba el esquema, que no detecta errores semánticos.
</details>

### Pregunta 9 (TS 5.5 · multiple-response)

Aprobada la automatización parcial, el equipo de revisión (R3) tiene que decidir cómo repartir sus horas. **Selecciona dos** prácticas que encajan con R3. Evalúa cada opción por separado.

- A. Revisar a diario las extracciones de los emisores más grandes, que concentran el importe.
- B. Revisar una muestra aleatoria estratificada de las extracciones de alta confianza.
- C. Mandar a revisión las de baja confianza por campo y las de documentos contradictorios.
- D. Revisar todas las extracciones de un solo tipo de documento cada semana, por turnos.

<details>
<summary>Respuesta</summary>

**B y C.** Muestreo estratificado de lo automatizado y prioridad a lo dudoso.

- **B** Correcta: el muestreo aleatorio estratificado de las extracciones de alta confianza mide de forma continua su tasa de error y detecta patrones de error nuevos (TS 5.5-S1, TS 5.5-K2).
- **C** Correcta: las extracciones con baja confianza del modelo o con documentos ambiguos o contradictorios van a revisión humana, que así prioriza su capacidad limitada (TS 5.5-S4); los umbrales se calibran con un conjunto de validación etiquetado (TS 5.5-S3).
- **A** Incorrecta: elige por importe, no por probabilidad de error, y deja sin medir el resto.
- **D** Incorrecta: gasta la revisión entera en un tipo de documento sin atender a la confianza y deja los demás sin vigilancia.
</details>
