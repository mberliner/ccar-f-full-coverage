Tanda A de la entrega 3, paso A6a: correcciones de código tras la revisión independiente (A5). Trabaja en la rama `entrega-3a`. Lee primero `docs/diseno-entrega-3.md` (tanda A), `NOTAS.md` (la casilla de la tanda A) y las secciones 07–09 de `app3_sistema_multiagente/README.md`.

Las reglas de siempre:
- Tests primero.
- Un commit por módulo.
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- `CostGuard` en toda ejecución con modelo.
- Los datos solo se cambian desde `datos/generar_sinteticos.py`.
- Si una señal no aparece, no se fabrica: primero Haiku 5.5, después Haiku 4.5 y, si tampoco sale, se documenta.

No toques las cabeceras `QUÉ DICE LA GUÍA` y `ANTI-PATRÓN`, las predicciones ni las preguntas tipo examen: esos textos los hace Opus en A6b. En el README solo cambias el «Ejercicio», el «Ejecutar» y las tablas y notas del Paso 3, con las cifras nuevas. Al terminar, deja una lista de los textos que hayan quedado desfasados.

**07 · `07_extraccion_schema.py`**
1. **`--parte enriquecimiento` (TS 4.3-S3, ya introducida en 07).**
   - Dos tools: `extract_metadata` y `lookup_purchase_order(po_number)`. El handler de la segunda es determinista y lee los pedidos del generador; si hacen falta pedidos sintéticos, añádelos allí.
   - Variante correcta: el primer turno va con `tool_choice` forzado a `extract_metadata` y los siguientes con `auto`, con el resultado de la extracción devuelto como `tool_result`.
   - `--anti auto_desde_inicio`: `auto` desde el primer turno.
   - Señal: en qué orden llama el modelo a las tools, si consulta un pedido antes de extraerlo o con un número que no sale del documento, y si el resultado final usa el pedido extraído.
   - Mídelo con Haiku 5.5. Si no hay señal, prueba con Haiku 4.5 y, si tampoco, documéntalo.
2. **`--parte few_shot` (TS 4.2-S5).** Imprime también los campos con valor en la etiqueta que salen `null` o vacíos (`Score.missing`) y los inventados (`Score.invented`, TS 4.2-K4), con y sin ejemplos. Vuelve a ejecutarlo con Haiku 5.5 y con Haiku 4.5 (`--rol-modelo enforcement`, `--repeat 3`) y pon al día la fila del Paso 3.

**08 · `08_validacion_reintento.py`**
3. **Totales.** La variante correcta ya no reintenta un `total_mismatch`: marca `conflict_detected` directamente, sin el mensaje «revisa cantidades, precios y total». La guía (TS 4.4-S4) usa ese booleano para marcar una fuente incoherente, no para reintentar. `--anti insistir` sí puede reintentarlo.
4. **Dato que solo está en otro documento (TS 4.4-S2).** `DC-07` («Ver adjunto») es justo el caso de la guía. El validador tiene que distinguir un dato que remite a un documento externo de uno que simplemente falta (`DC-02`): los dos se marcan sin reintentar, cada uno con su causa. Se detecta por una búsqueda en el texto, sin modelo.
5. **`retry_effect`.** Si un fallo `po_format` acaba en `null`, el efecto es «persiste» o «falta», no «inventado».
6. **`stopped_by`.** Tiene que guardar el motivo que paró el bucle, no el primero que se marcó.
7. **Comentarios.** En los comentarios de las líneas ~105 y ~223, «`detected_pattern`» pasa a «patrón de fallo». Las viñetas 4.4-K3 y S3 ya no son de este módulo: se introducen en `app3/11`.
8. Vuelve a ejecutar las tres variantes con `--repeat 3` y pon al día el Paso 3 y la línea «Medido en `app3/08`» de `docs/hallazgos.md`.

**09 · `09_batches.py`**
9. **`build_resend`.** Hoy, un trozo que falla sin estar truncado (`invalid`, `errored`, `expired`) se reenvía con el documento entero bajo el id del trozo, y al unir se duplican líneas. Reenvía solo el texto de ese trozo. La unión tiene que ser determinista aunque el mismo documento tenga un trozo truncado y otro inválido, y no puede depender del orden de llegada. Añade tests para los dos casos.
10. **Re-troceo.** Hoy baja un solo nivel. Si un trozo vuelve a truncarse, se parte a la mitad, hasta un mínimo de una línea.
11. **`mismatched`.** Un resultado sin datos (truncado o fallido) no cuenta como «datos de otro documento». El denominador es el de los documentos que tienen número en la etiqueta: sale «X de 11», no «de 12». Vuelve a medir `--anti por_orden`.
12. **Presupuesto.** El tope es por invocación:
    - Con `--enviar`, la muestra síncrona más la estimación del lote no pueden superar el tope.
    - Con `--batch-id --reenviar`, el lote leído ya se pagó en otra invocación. La estimación del reenvío se compara con lo que queda del tope en esa invocación.
    - Deja dicho en el código y en «Ejecutar» qué cubre el tope.
13. **Muestra previa (TS 4.5-S4).** Además de la forma, la muestra compara las extracciones con las etiquetas e imprime el acierto por campo. Sirve para afinar el prompt antes del lote. Si el acierto queda por debajo de un umbral visible en el código, no se lanza el lote, salvo con `--sin-muestra`.

Al final:
- Actualiza la casilla de la tanda A en `NOTAS.md`: qué cambió, las cifras nuevas, el coste y la lista de textos desfasados para A6b.
- No fusiones, no hagas push y no toques el roadmap origen.
