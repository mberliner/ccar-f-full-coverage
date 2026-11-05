Tanda B de la entrega 3: correcciones de código tras la revisión independiente (B4). Trabaja en la rama `entrega-3b`. Lee primero `NOTAS.md` (la casilla de la tanda B), `docs/hallazgos.md` (sección de la tanda B) y las secciones 04, 05 y 06 de `app3_sistema_multiagente/README.md`.

El texto de la guía está fuera del clon. Las viñetas que necesitas van resumidas aquí, con el número de cada una.

Las reglas de siempre:
- Tests primero.
- Un commit por módulo.
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- `max_budget_usd` en toda ejecución con modelo, con el presupuesto `multiagent` (1 $ por ejecución). Si el total de esta tarea va a pasar de 2 $, para y avisa antes de seguir.
- Los datos solo se cambian desde `datos/generar_sinteticos.py`.
- Si una señal no aparece, no se fabrica: primero el modelo del rol, después Haiku 4.5 y, si tampoco sale, se documenta.

No toques las cabeceras `QUÉ DICE LA GUÍA`, `POR QUÉ IMPORTA` y `ANTI-PATRÓN` de `04`–`06`, ni las predicciones, las preguntas tipo examen o las explicaciones del README: los reescribe Opus en el pase siguiente, con tus cifras. En el README solo cambias el «Ejercicio», el «Ejecutar» y las tablas y notas del Paso 3. En `docs/hallazgos.md` y `NOTAS.md`, anota las mediciones nuevas como **después de las correcciones B4**, separadas de las anteriores, sin borrar estas.

**04 · `04_errores_entre_agentes.py`**

1. **`generico` cambia dos cosas a la vez.** Hoy su prompt dice «no reintentes», así que no se puede saber si el coordinador vuelve a delegar por el mensaje genérico (5.3-K3: un estado genérico como «búsqueda no disponible» oculta el contexto al coordinador) o porque nadie reintentó (5.3-S3: el subagente recupera en local los fallos transitorios). Haz que `generico` reintente igual que la correcta (hasta `MAX_LOCAL_RETRIES`) y que solo cambie lo que devuelve al final: `status: failed` con el mensaje genérico, sin `error_context`. Vuelve a medir `generico` con `--repeat 3`.
2. **5.3-S3: hoy no se ve ninguna recuperación local**, porque la fuente con *timeout* falla siempre. Añade una fuente transitoria: falla con *timeout* la primera vez que se consulta en una ejecución y responde bien a la siguiente. El estado del fallo va por ejecución, no global, y con un test sin modelo. Mide si en la correcta el subagente la recupera sin que el coordinador lo vea como fallo. Esta fuente solo afecta a los datos de `04`; comprueba que `05` y `06` no la reciben.
3. **Medidas laxas** (comprobadas por la revisión con un script). Corrígelas y añade un test con el caso que hoy falla:
   - `gap_noted` da True con «SRC-MONITOR no falló: respondió sin datos». Que trate la negación.
   - `silenced_sources` usa `failed_sources`, así que en `silenciar` siempre devuelve `[]`. Decide si se quita o se renombra; lo que mide el anti-patrón es `swallowed_sources`.
   - `print_measures` rotula `empty_sources` como «vacías legítimas», pero en `silenciar` incluye la fuente tragada. Sepáralas en la salida.
   - `partial_delivered`: una fecha como 2026-10-18 cuenta como cifra; basta una cifra cualquiera, incluidas las de fuentes que `04` no pide; y un aborto sin la marca exacta cuenta como entrega. Que exija cifras de las fuentes pedidas que respondieron y que no cuente fechas.
4. Tras los cambios, vuelve a medir con `--repeat 3` la correcta, `silenciar` y `abortar`, porque cambian los datos.
5. Corta la línea larga de `servers/investigacion.py:16`.

**05 · `05_procedencia.py`**

6. **5.1-S5 y 5.6-S1: falta la ubicación en la fuente y el fragmento.** La guía pide a los subagentes metadatos con la ubicación en la fuente (5.1-S5) y mapeos afirmación–fuente con el fragmento relevante (5.6-S1). Hoy el investigador devuelve `{claim, figure, unit, context}` y `{source_id, published_at}`. Añade a los metadatos la ubicación (la sección o el apartado de la fuente; los datos tendrán que traerla) y un `excerpt` con el fragmento literal que respalda la afirmación. Mide si llegan al informe final.
7. **5.6-S3: quien decide la reconciliación es el coordinador, antes de la síntesis.** La guía dice que el análisis termina con los valores en conflicto incluidos y anotados, y que el coordinador decide cómo reconciliarlos antes de pasarlos al sintetizador. Hoy el coordinador los pasa «tal como llegaron». Haz que el coordinador decida, para cada conflicto, si lo explica el contexto (periodo, método, muestra, población) o queda disputado, y que esa decisión vaya en el prompt del sintetizador junto a las afirmaciones. Mide si la decisión aparece en el prompt del sintetizador (lo capturas como ya haces con `sources_passed`).
8. **5.6-S5: el formato por tipo no tiene contraste.** El prompt del sintetizador ya pide tabla, y `uses_table` solo cuenta dos líneas que empiezan por `|`. Añade `--anti formato_uniforme` (todo en prosa, sin instrucción de formato por tipo) y haz que la medida compruebe que la tabla contiene las cifras de los pares, no solo que haya una tabla.
9. **5.1-S6: falta el contraste entre salida estructurada y verbosa** cuando el agente de después tiene poco contexto. La guía dice que se cambian los agentes de antes para que devuelvan datos estructurados (hechos clave, citas, *relevance scores*) en vez de contenido verboso y cadenas de razonamiento. Añade una puntuación de relevancia a la salida estructurada del investigador. Haz que `sin_procedencia` sea de verdad verbosa (prosa con su razonamiento, sin metadatos), y mide el tamaño de lo que llega al sintetizador en las dos variantes.
10. **Falta un control positivo para la explicación inventada.** El «0 de 9» del par sin explicación no demuestra que la medida detecte el fallo. Añade `--anti inventar_explicacion`: el sintetizador explica siempre las diferencias, aunque el contexto no las explique. Mide si `unexplained_status` lo detecta.
11. **Medidas laxas.** Corrígelas y añade un test con el caso que hoy falla:
    - `conflicts_presented` da True en los tres pares con «No hay discrepancias». Que trate la negación.
    - `explanation_found`: la regex de muestra casa con el verbo («la tabla muestra») y la de espera con «espera confirmar». Con los dos, el par de control sale «atribuido».
    - `merged_figures` no detecta «≈4 sobre 5» ni «10 %».
    - `sources_passed` da por pasada una fuente si su id aparece en cualquier parte del prompt. Que exija que vaya con su afirmación.
12. **El informe largo destaca el hallazgo por saliencia, no por posición.** Hoy son 60 párrafos de relleno casi iguales, con «(apartado N)», y una sola frase distinta con cifra. Así no se puede medir *lost in the middle*. Cambia el relleno en `datos/generar_sinteticos.py`: párrafos distintos, con cifras de distracción del mismo tipo que el hallazgo. Vuelve a medir las variantes de `medio`. Si sigue sin señal, se documenta.
13. Vuelve a medir con `--repeat 3` la correcta, `sin_procedencia` y `promedio`, porque cambian los datos y los prompts.
14. Corrige el comentario de `datos/generar_sinteticos.py` que cuenta las fuentes («tres que concuerdan, seis que discrepan, una timeout, una vacía y un largo» suma 12, y son 9, o las que haya tras los cambios).

**06 · `06_contexto_largo.py`**

15. **`read_manifest` no es robusto** (la revisión lo comprobó con un script). Tests primero, uno por caso:
    - Bytes no UTF-8: hoy lanza `UnicodeDecodeError`, porque solo se captura `JSONDecodeError`. Debe devolver `None`, como dice el docstring.
    - Tipos: `phases_done` como entero hace fallar a `next_phase` con `TypeError`. Valida los tipos.
    - Claves: si faltan `sources_covered` o `summaries`, `phase_prompt` lanza `KeyError`. Valídalas.
    - `version` no se comprueba. Un *manifest* de otra versión se rechaza con un aviso.
16. **Ninguna comprobación entre *manifest* y *scratchpad*.** Un *manifest* de otra ejecución (`phases_done=[1]`, `findings=5`) con el *scratchpad* vacío o ajeno se retoma sin avisar, y el prompt manda leer hallazgos que no existen. Comprueba al retomar que el *scratchpad* tiene los hallazgos que dice el *manifest*. Si no cuadra, avisa y empieza de cero.
17. **Una caída a mitad de escritura** deja una línea truncada en `scratchpad.jsonl`, y `read_scratchpad` lanza `JSONDecodeError`. Pasa dentro del *handler* de la tool y, en `run_phased`, después de haber pagado la fase. Que `read_scratchpad` ignore una última línea incompleta con un aviso y falle de forma clara si la corrupción está en medio.
18. **`STATE_DIR` es fijo** bajo el temporal del sistema. En una máquina con `/tmp` compartido lo compartirían varias personas. Hazlo por usuario o llévalo bajo `estado/<perfil>/`, como el resto del estado personal.
19. Con estos cambios no hace falta volver a medir con modelo. Si cambias algo que afecte al prompt, mide una vez `--simular-caida` y su reanudación.

**Al terminar**

- `CONCEPTOS.md` sigue en 190/240: no se introduce ninguna viñeta nueva.
- Un informe con:
  - los commits;
  - una tabla de cifras de antes y de después de estas correcciones (04: decisiones del coordinador en `generico`, recuperación de la fuente transitoria, brecha anotada y entrega parcial; 05: procedencia, ubicación y fragmento, decisión del coordinador, tabla con las cifras, tamaño estructurado frente a verboso, control positivo, *lost in the middle*; 06: casos del *manifest*);
  - el coste total;
  - lo que no salió o salió distinto de lo esperado.
