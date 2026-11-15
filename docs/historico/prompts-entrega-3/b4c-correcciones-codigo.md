Tanda B de la entrega 3: correcciones de código de la segunda revisión (B4b). Trabaja en la rama `entrega-3b`. Son arreglos localizados en medidas y *handlers*: no hace falta volver a ejecutar con modelo.

Las reglas de siempre:
- Tests primero: cada arreglo va con un test que falla antes con el caso indicado.
- Un commit por módulo.
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- No toques las cabeceras ni las predicciones o preguntas del README. Si un arreglo cambia lo que una medida detecta, actualiza su nota en el Paso 3 del README («Medidas»).

**04 · `04_errores_entre_agentes.py`**

1. **`gap_noted` da falsos negativos con la brecha más natural.** `NEGATED_GAP` (línea ~89) admite de 0 a 2 palabras entre la negación y la palabra de fallo, así que borra «no respondió por timeout» entera, y con ella la palabra de fallo. Casos comprobados:
   - «SRC-MONITOR no respondió por timeout» → hoy False; debe ser True.
   - «SRC-MONITOR quedó sin datos por timeout» → hoy False; debe ser True.
   - «SRC-MONITOR no respondió: timeout» → True (ya bien).
   - «SRC-MONITOR no falló: respondió sin datos» → False (ya bien).

   Limita la negación a «no», «ni» o «sin» seguido directamente del verbo o el sustantivo de fallo («no falló», «sin error», «sin brecha»). Un test por caso. Si el arreglo cambia la medida de alguna ejecución ya registrada, no la recalcules: anota en el README que la medida cambió después.

**05 · `05_procedencia.py`**

2. **`conflicts_presented`:** `NEGATED_DISPUTE` (línea ~109) admite hasta 3 palabras entre «sin/no» y la palabra de desacuerdo, así que «Sin fusionarlas las fuentes difieren» se borra. Restríngelo igual que en el punto 1. Además, la medida es global: una sola mención de desacuerdo vale para los tres pares. Hazla por par (la palabra de desacuerdo en las líneas que nombran el par, como ya hace `explanation_found`), o, si eso no es razonable, deja en la nota del README que es global.
3. **Decisiones del coordinador:** `DECISION_DISPUTED` y `DECISION_EXPLAINED` (líneas ~111-112). «No explicada» y «no está explicada» caen en `DECISION_EXPLAINED`. Trata la negación y añade el test. Si el prompt del coordinador fija el formato, dilo en la nota del README.

**06 · `06_contexto_largo.py`**

4. **`start_state` borra el estado sin confirmar** (línea ~483). Si el *manifest* se descarta (versión distinta, tipos erróneos o no cuadra con el *scratchpad*), `shutil.rmtree` borra también el *scratchpad*. Un *manifest* de una versión futura destruiría trabajo de otra versión. En vez de borrar, mueve el estado a un directorio `*.bak` con marca de tiempo y dilo en el aviso.
5. **`save_finding` puede lanzar excepciones** (líneas ~222-224): con `claim` numérico, `args["claim"].strip()` lanza `AttributeError`; sin `source_id`, `KeyError`. Que devuelva un error de validación estructurado (como los de `app1/04`), no una excepción.
6. **`version: true` pasa la validación**, porque `True == 1`. Exige un entero que no sea booleano.

**Al terminar**

Un informe breve con los commits, qué medidas cambian de comportamiento y si alguna cifra ya registrada quedaría distinta con la medida nueva.
