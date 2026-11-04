Tanda B de la entrega 3: completar el código antes del pase de textos. Trabaja en la rama `entrega-3b`. Lee primero `docs/diseno-entrega-3.md` (tanda B), `NOTAS.md` (la casilla de la tanda B) y las secciones 04 y 05 de `app3_sistema_multiagente/README.md`.

El texto de la guía está fuera del clon. Las viñetas que necesitas van resumidas aquí, con el número de cada una.

Las reglas de siempre:
- Tests primero.
- Un commit por módulo.
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- `max_budget_usd` en toda ejecución con modelo.
- Los datos solo se cambian desde `datos/generar_sinteticos.py`.
- Si una señal no aparece, no se fabrica: primero el modelo del rol, después Haiku 4.5 y, si tampoco sale, se documenta.

No toques las cabeceras `QUÉ DICE LA GUÍA` y `ANTI-PATRÓN`, las predicciones ni las preguntas tipo examen: esos textos los hace Opus en el pase siguiente, para los tres módulos a la vez. Deja las marcas BORRADOR. En el README solo cambias el «Ejercicio», el «Ejecutar» y las tablas y notas del Paso 3.

**06 · `06_contexto_largo.py` (TS 5.4, 9 viñetas, según el diseño)**
1. Constrúyelo como dice el diseño. Viñetas:
   - K1: degradación en sesiones largas (respuestas inconsistentes, «patrones típicos» en vez de lo descubierto).
   - K2 y S2: *scratchpad* con los hallazgos clave, consultado en las preguntas siguientes.
   - K3 y S1: subagentes para preguntas concretas, mientras el principal coordina.
   - S3: resumen de una fase inyectado en el contexto inicial de la siguiente.
   - K4 y S4: cada agente exporta su estado a un sitio conocido y el coordinador carga un *manifest* al retomar y lo inyecta en los prompts.
   - S5: `/compact`, solo en comentario y README.

**04 · `04_errores_entre_agentes.py`**

2. **TS 5.3-K3 sin variante.** La guía dice que un estado de error genérico («búsqueda no disponible») oculta al coordinador el contexto que necesita. Hoy no hay variante que lo muestre. Añade `--anti generico`: el subagente devuelve `status: failed` con un mensaje genérico y sin `error_context`. Mide qué decide el coordinador (si reintenta, si busca una alternativa, si anota la brecha) frente a la correcta.
3. **`--anti silenciar` lo hace el prompt.** Con un prompt, la brecha llegó igual al resultado final en las 7 ejecuciones (`docs/hallazgos.md`). Haz que el vacío lo produzca el código: en la variante, el *handler* devuelve `[]` como éxito cuando la fuente falla, que es el anti-patrón de la guía (TS 5.3-K4). Vuelve a medir. Si conviene, conserva la versión por prompt como nota del Paso 3, sin variante propia.
4. **Repeticiones.** La correcta y `abortar` se midieron una vez. Es un módulo de ejecución obligatoria y su señal es la de §11.3, así que vuelve a medir con `--repeat 3` todas las variantes.

**05 · `05_procedencia.py`**

5. **TS 5.1-S4 pide dos cosas:** el resumen de hallazgos al principio y encabezados de sección explícitos en los resultados detallados. Hoy solo está el resumen. Añade al informe largo una variante con encabezados, o encabezados más resumen, y mídelo igual.
6. **TS 5.6-K4 y S4: las fechas evitan leer como contradicción lo que es una diferencia temporal.** Los datos ya lo permiten: la encuesta del proveedor corta a 31 de agosto y la auditoría mide otra cosa, porque cuenta las esperas. Las etiquetas, sin embargo, tratan los dos pares como «conflicto». Distingue en las etiquetas y en la medida el conflicto por metodología o periodo (explicado por los metadatos) del desacuerdo sin explicación. Comprueba si el informe final usa la fecha o el método para explicar la diferencia (TS 5.6-S2, contexto metodológico).
7. **Comentario de `build_long_report`** en `datos/generar_sinteticos.py`: dice «el hallazgo clave en el 15.º», pero el código lo inserta en la posición 30 de 60.

Al final:
- Actualiza la casilla de la tanda B en `NOTAS.md`: qué cambió, las cifras nuevas, el coste y la lista de textos desfasados para el pase de Opus.
- No fusiones, no hagas push y no toques el roadmap origen.
