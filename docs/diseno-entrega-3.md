# Diseño de la entrega 3 · D4 y D5 (extracción, calidad, contexto y CI)

Aprobado en plan mode. El avance se registra en `NOTAS.md`; este documento solo cambia si cambia el diseño. No depende de ningún calendario de estudio.

## Contexto

Entregas 1 y 2 e Hito T cerrados (131/240). La entrega 3 (roadmap §10, fila 3) construye `app1/07`, `app2/04` y `app3/04`–`12`: **11 módulos y 109 viñetas**, de 131 a **240/240**. **Hecho cuando:** `test_full_coverage` pasa y se le quita el `xfail`; la señal de §11.3 se observa en `app3/04` (resultado parcial con la brecha anotada) y en `app3/08` (reintento útil frente a inútil); y `app3/11` devuelve JSON válido contra su schema.

**Decisiones que se mantienen:** Haiku 5.5 para agente único y subagentes, Sonnet 5.5 para el coordinador y Haiku 4.5 (`enforcement`) solo si una sonda demuestra que Haiku 5.5 no da la señal. `CCARF_BUDGET_AGENT` (0,25 $) y `CCARF_BUDGET_MULTIAGENT` (1,00 $) como topes de toda la ejecución del script. Plantilla de README de módulo y ciclo de §13 desde el principio. Si una señal no aparece, no se fabrica (§4.3).

**Decisiones nuevas:**

- **Rol `reviewer`** (`CCARF_MODEL_REVIEWER`, por defecto Sonnet 5.5) para `app3/11` y `app3/12`: revisar código pide más que Haiku, y llamarlo «coordinator» confundiría. Usa `CCARF_BUDGET_MULTIAGENT`.
- **La extracción forzada usa el rol `agent`** (Haiku 5.5): Sonnet 5.5 devuelve 400 con `tool_choice` `any` y forzado (§4.3).
- **Entrega por tandas**, cada una en su rama (`entrega-3a`…`3d`), con un commit por módulo y merge a `main` cuando sus tests pasan y tiene su revisión independiente. Así cada tanda se puede estudiar en cuanto se fusiona.

## Orden: cuatro tandas

El orden sale de la verificación del roadmap y de las dependencias, no de un calendario:

| Tanda | Módulos | Viñetas | Contador | Por qué en este orden |
| :---: | :--- | :---: | :---: | :--- |
| A | `app3/07` → `08` → `09` | 27 | 158/240 | `08` es de ejecución obligatoria (§13) y una de las señales de §11.3; `07` define el schema que usan `08`, `09` y `10` |
| B | `app3/04` → `05` → `06` | 32 | 190/240 | `04` es la otra señal de §11.3 y de ejecución obligatoria; los tres amplían el mismo servidor de investigación |
| C | `app3/10` → `11` → `12` | 35 | 225/240 | `10` trabaja sobre las salidas de `07`; `11` y `12` comparten el `git diff` de prueba y la sonda de `claude -p` |
| D | `app2/04` → `app1/07` | 15 | 240/240 | No dependen de nada nuevo; cierran la cobertura |

Si el plazo aprieta, se aplica la regla de escalado de §10: modo ligero sobre lo entregado, sin código nuevo en la semana final.

## Lecturas previas

Las rutas son relativas a la raíz del repositorio de estudio que nombra `CLAUDE.md`. Nada se copia aquí. Un `§` sin nombre de documento se refiere al roadmap.

| Antes de… | Leer |
| :--- | :--- |
| Cualquier módulo | Roadmap §2, §3 (reglas 3, 4 y 7), §4.3 y §13 |
| `QUÉ DICE LA GUÍA` y las preguntas | `docs/resumen-guia-examen-ccar-f.md` §6, la Task Statement del módulo |
| Tanda A y `app3/10` | El mismo resumen, §8: Exercise 3 (extracción estructurada con batch); `docs/conceptos-generales.md` §4.2 (`tool_choice`) y §4.6 |
| Tanda B | El mismo resumen, §8: Exercise 4 (investigación multiagente) |
| `app3/11` y `12` | `docs/conceptos-generales.md` §4.6 (`claude -p` y `--json-schema`) |
| Cada módulo | Roadmap §6–§8, la fila del módulo |
| Cierre | Roadmap §10 (fila 3) y §12 («Mantener la plantilla al día») |

## Piezas compartidas

Se construyen al empezar la tanda que las usa, con tests primero.

1. **Datos** (`datos/generar_sinteticos.py`, con `--check` y test de determinismo). Etiquetas siempre en un archivo aparte, que el agente nunca ve:
   - **Tanda A:** `documentos_compra.json`, documentos de compra de equipos de la mesa (facturas, albaranes y un tipo poco común), con formatos variados (tabla, prosa, líneas sueltas), campos ausentes, un tipo que no encaja en el `enum`, totales que no cuadran (`stated_total` distinto de la suma de líneas) y un documento cuyo dato pedido no está en ninguna parte. `documentos_compra_etiquetas.json` con los valores correctos por campo y tipo.
   - **Tanda B:** en `investigacion.py` o en un JSON nuevo: una fuente que falla por *timeout*, informes con cifras y fechas en conflicto y un texto largo con el hallazgo clave en mitad.
   - **Tanda C:** el `git diff` de prueba se genera en la copia temporal de `repo_mesa` (no en `datos/sinteticos/`), con un fallo sembrado de cada categoría del criterio y un cambio correcto que se parece a un fallo.
   - **Tanda D:** un inventario de 40 campos por equipo para `app1/07` (los casos de escalamiento de `app2/04` ya existen).
2. **`harness/budget.py`:** descuento del 50 % para el coste de una petición en batch, con test.
3. **`harness/config.py`:** rol `reviewer`, con test y su línea en la plantilla de variables de entorno.
4. **`harness/headless.py`** (tanda C, solo si la sonda C1 lo confirma): construye la orden de `claude -p` con el aislamiento de §3 (fuentes de configuración, MCP estricto, `env`), exige un tope de coste y la imprime entera antes de ejecutarla. No esconde nada: la orden es la lección.
5. **Por app:** `app3/CLAUDE.md` (rol `reviewer` y `claude -p`), `app2/CLAUDE.md` si `04` añade algo; secciones de README desde `plantillas/modulo/README.md` con `/nuevo-modulo`.

Cada módulo sigue `/nuevo-modulo`: tests sin modelo primero → módulo con cabecera fija e `INTRODUCE` → ☑ y contador en `CONCEPTOS.md` → sección del README → `uv run pytest -q` en verde.

## Módulos

### Tanda A

#### `app3_sistema_multiagente/07_extraccion_schema.py` · 4.3 K1–4, S1–6 · 4.2 K4, S4–5

- Messages API con `harness/budget.CostGuard`, como `app1/05`. Tool `extract_metadata` con JSON Schema.
- `--parte forzada`: `tool_choice` forzado a `extract_metadata`; `--parte tipo_desconocido`: `any` cuando el documento puede ser de varios tipos y cada tipo tiene su tool.
- Schema correcto: campos opcionales *nullable*, `enum` con `unclear` y `other` más un campo de detalle, y reglas de normalización (fechas, importes) en la descripción.
- `--anti sin_nullable`: los campos opcionales son obligatorios, y el modelo tiene que inventar algo. `--anti enum_cerrado`: sin `unclear`/`other`, el tipo raro se fuerza a una categoría, o el modelo escribe un valor que el `enum` no admite, porque sin modo estricto el esquema de una tool no se impone. El módulo valida la forma de lo que recibe y cuenta los valores fuera del `enum` (corregido tras la sonda A2).
- `--rol-modelo enforcement` (Haiku 4.5), solo para el *few-shot*: con Haiku 5.5 no hay errores de formato que corregir.
- `--parte enriquecimiento` (añadida tras la revisión A5, para 4.3-S3): `extract_metadata` y `lookup_purchase_order`. El primer turno va forzado a `extract_metadata` y después pasa a `auto`, así que el enriquecimiento parte del pedido extraído. `--anti auto_desde_inicio`: el modelo puede consultar el pedido antes de extraerlo.
- Sintaxis frente a semántica: el schema garantiza la forma, no que los valores sean correctos. El módulo lo muestra comparando con las etiquetas.
- *Few-shot* para estructuras documentales variadas (4.2 K4, S4–5): con ejemplos de las tres formas frente a sin ellos.
- Señal: campos inventados frente a `null` y tipo forzado frente a `other`, puntuados contra las etiquetas.
- Tests: schema por variante, puntuación contra etiquetas, construcción de la petición por modo de `tool_choice`.

#### `app3_sistema_multiagente/08_validacion_reintento.py` · 4.4 K1, K2, K4, S1, S2, S4 (ejecución obligatoria)

- 4.4-K3 y S3 (`detected_pattern` para analizar los hallazgos descartados) pasan a `app3/11` tras la revisión A5: en una extracción no hay hallazgos que alguien descarte.

- **Rol `enforcement` (Haiku 4.5)** con su presupuesto, no `agent`: con Haiku 5.5 no hubo fallos de fecha en 36 intentos, así que no había nada que reintentar (sonda A2; `--rol-modelo agent` lo comprueba).
- Sobre la extracción de `07`. Un validador sin modelo calcula `calculated_total` y lo compara con `stated_total`; si no cuadran, marca `conflict_detected` sin reintentar, porque lo incoherente es la fuente (cambiado tras A5: antes se reintentaba una vez).
- Correcta: ante un fallo de validación, reintento con el **error concreto** (campo, valor y regla). Si el dato no está en la fuente, el reintento es inútil y no se hace: el campo se marca con su causa, *no lo trae* (`missing_in_source`) o *remite a otro documento* (`external_reference`, 4.4-S2), distinguidas por una búsqueda en el texto. `stopped_by` guarda el motivo que cerró el bucle.
- `--anti reintento_generico`: el reintento solo dice «inténtalo de nuevo». `--anti insistir`: reintenta hasta el tope también cuando el dato no existe y cuando el total no cuadra.
- Un patrón de fallo (`pattern`) en cada fallo, para agrupar las causas.
- Señal (§11.3): un reintento útil que corrige y uno inútil, con el número de reintentos y su coste.
- Tests: validador, mensaje de error específico, detección del caso sin dato y tope de reintentos.

#### `app3_sistema_multiagente/09_batches.py` · 4.5 K1–4, S1–4

- Message Batches API con las peticiones de `07`, cada una con su `custom_id`.
- `--enviar` crea el lote e imprime su id; `--batch-id <id>` lo retoma y lee resultados. El módulo no guarda nada: el id lo copia la persona.
- Reenvío de los fallidos por `custom_id`, partiendo los documentos demasiado largos (*chunking*). Si un trozo vuelve a truncarse, el documento se parte a la mitad, hasta una línea por trozo; un trozo que falla sin truncarse se reenvía con su propio texto, y la unión no depende del orden de llegada. Una respuesta truncada cuenta como fallida aunque la API la dé por `succeeded`.
- `--anti por_orden`: empareja los resultados por posición en vez de por `custom_id`. Se cuenta sobre los documentos con número en la etiqueta, sin los resultados vacíos.
- Cálculo sin modelo de ventana frente a SLA: qué cabe en batch, qué tiene que ir síncrono y **cada cuánto hay que enviar** (4.5-S2). La condición es `intervalo + ventana × (1 + reenvíos) + margen ≤ SLA`, de modo que con 30 h sale enviar cada 4 h, el ejemplo de la guía. La frecuencia se añadió en A4, al comprobar la viñeta contra la guía.
- Estimación (cota superior) del coste antes de enviar, porque la Batches API no admite un corte a mitad del lote. El tope es por invocación: con `--enviar`, muestra más estimación del lote; con `--reenviar`, solo la estimación del reenvío.
- Muestra previa síncrona de unos pocos documentos, comparada con las etiquetas campo por campo (4.5-S4); por debajo de un umbral visible en el código, no se lanza el lote.
- Comentario: sin tools de varios turnos dentro de una petición de batch.
- Tests: construcción del lote, emparejado por `custom_id`, selección y troceo de los fallidos, cálculo de ventana, coste con descuento.

### Tanda B

Patrón de `app3/01`–`03`: coordinador Sonnet con `tools=["Agent"]` y `coordinator_gate.py`, subagentes Haiku con `AgentDefinition`, y en `env` `FORK_SUBAGENT="0"`, `DISABLE_BACKGROUND_TASKS="1"` y `MAX_SUBAGENT_SPAWN_DEPTH=1`.

#### `app3_sistema_multiagente/04_errores_entre_agentes.py` · 5.3 K1–4, S1–4 · 2.2-S3 (ejecución obligatoria)

- Una de las fuentes del investigador falla por *timeout* en todas las consultas (error estructurado de `app1/04`), y otra solo en la primera, para ver la recuperación local (5.3-S3, añadida en la revisión).
- Correcta: el subagente reintenta en local lo transitorio y, si no se recupera, devuelve al coordinador un contexto estructurado del error (qué falló, qué se intentó, qué falta). El coordinador entrega un resultado parcial con la cobertura anotada.
- `--anti generico` (5.3-K3, añadida tras verificar contra la guía): el subagente reintenta como en la correcta y devuelve `failed` con «búsqueda no disponible» y sin contexto. Solo cambia el mensaje, para no confundir su efecto con la falta de reintento.
- `--anti silenciar`: el *handler* de la tool devuelve vacío como éxito cuando la fuente falla. Lo hace el código, porque por prompt la brecha llegaba igual al resultado final. `--anti abortar`: un fallo tumba toda la investigación.
- Señal (§11.3): resultado parcial con la brecha anotada.
- Tests: forma del contexto de error, anotación de cobertura y diferencia entre vacío y fallo.

#### `app3_sistema_multiagente/05_procedencia.py` · 5.6 K1–4, S1–5 · 5.1 K2, S4–6 · 1.3-S2

- Los subagentes devuelven datos estructurados (afirmación, cifra, contexto; fuente, fecha, sección, fragmento literal y relevancia), con el contenido separado de los metadatos (1.3-S2, 5.1-S5, S6, 5.6-S1).
- El coordinador decide, antes de la síntesis, qué conflictos explica el contexto y cuáles quedan disputados, y pasa esa decisión al sintetizador (5.6-S3).
- El sintetizador conserva el mapeo afirmación–fuente, separa lo establecido de lo disputado, no promedia cifras en conflicto y usa el formato según el tipo de contenido.
- Tres pares de cifras en conflicto: uno se explica por el método y la muestra, otro por el periodo y la población, y el tercero no tiene explicación en los metadatos, como contraste (5.6-K4, S2, S4). El investigador devuelve el contexto metodológico de cada cifra.
- *Lost in the middle* (5.1): el hallazgo clave en mitad de un texto largo, sin tratamiento, con un resumen al principio, con encabezados de sección o con las dos cosas (5.1-S4).
- `--anti sin_procedencia`: los subagentes devuelven prosa larga con su razonamiento y la síntesis pierde las fuentes. `--anti promedio`: las cifras en conflicto se fusionan. `--anti formato_uniforme`: todo en prosa, sin tabla (5.6-S5). `--anti inventar_explicacion`: control positivo de la medida del par sin explicación.
- Tests: estructura de lo que devuelve cada subagente, comprobador de procedencia, detector de cifras fusionadas.

#### `app3_sistema_multiagente/06_contexto_largo.py` · 5.4 K1–4, S1–5

- Una investigación en fases. Correcta: *scratchpad* en el directorio de estado de cada persona, resumen entre fases, subagentes para preguntas concretas y un *manifest* de estado que permite retomar tras una caída simulada.
- `--anti todo_en_contexto`: todo se acumula en un solo hilo. `--simular-caida`: corta tras la fase 1 y la siguiente ejecución retoma desde el *manifest*.
- `Explore` y `/compact` son de Claude Code: van en comentario y en el README, con referencia a la sección D3.
- Tests: escritura y lectura del *manifest*, retomar desde una fase, contenido del resumen entre fases, y *manifest* roto, de otra versión o que no cuadra con el *scratchpad*.

### Tanda C

#### `app3_sistema_multiagente/10_confianza_y_revision.py` · 5.5 K1–4, S1–4

- Casi todo sin modelo, sobre extracciones de `07` con confianza por campo (las que se generan en la ejecución o un conjunto fijo para los tests).
- Calibración contra el conjunto etiquetado: precisión por banda de confianza, por tipo de documento y por campo.
- Muestreo estratificado para revisión humana, frente a un muestreo aleatorio que no ve los tipos raros.
- `--anti confianza_global`: una sola confianza por documento esconde el campo malo.
- Tests: calibración, muestreo estratificado y precisión por tipo y campo.

#### `app3_sistema_multiagente/11_criterios_y_ci.py` · 3.6 K1–3, S1–5 · 4.1 K1–3, S1–3 · 4.2 S2–3 · 4.4 K3, S3

- `claude -p --output-format json --json-schema` sobre un `git diff` de una copia temporal de `repo_mesa`, en una instancia distinta de la que generó el código.
- El `CLAUDE.md` del `cwd` temporal es el contexto de CI; los tests existentes y los hallazgos previos van en contexto.
- Criterios categóricos con severidades y ejemplos de código, desactivando las categorías con falsos positivos; *few-shot* de formato y de patrón aceptable; `detected_pattern` en cada hallazgo y un registro de hallazgos descartados agrupado por patrón, para encontrar los falsos positivos (4.4-K3, S3).
- `--anti conservador`: el prompt solo dice «sé conservador». `--anti sin_ejemplos`: sin *few-shot*.
- Señal: JSON válido contra el schema, fallos sembrados encontrados y el cambio correcto no marcado.
- Tests: schema, generación del diff, puntuación de hallazgos contra lo sembrado, orden de `claude -p` construida.

#### `app3_sistema_multiagente/12_revision_independiente.py` · 4.6 K1–3, S1–3 · 1.6 K2, S2 · 3.6-K4

- Sobre el mismo diff. Correcta: una segunda instancia sin contexto del generador, con pasada por archivo y pasada de integración, y confianza por hallazgo.
- `--anti autorrevision`: la sesión que generó se revisa a sí misma con `resume`.
- Señal: hallazgos de la autorrevisión frente a los de la instancia nueva, y los que solo aparecen en la pasada de integración.
- Tests: reparto de pasadas, fusión de hallazgos y confianza.

### Tanda D

#### `app2_agente_con_control/04_few_shot_y_escalamiento.py` · 4.2 K1–3, S1 · 5.2 K1–4, S1–5

- Los casos de escalamiento y sus etiquetas ya existen en el generador (petición explícita de humano, frustración, *policy gap*, varias coincidencias). Servidor `helpdesk.py` con `escalate_to_human`.
- Correcta: criterios explícitos con *few-shot* razonado.
- `--anti sin_ejemplos`, `--anti sentimiento` (el sentimiento como criterio) y `--anti confianza` (la confianza que el propio modelo declara como criterio).
- Señal: acción por caso frente a la etiqueta.
- Tests: puntuación contra etiquetas y construcción del prompt por variante.

#### `app1_agente_unico/07_recorte_de_contexto.py` · 5.1 K3, S3

- Una tool que devuelve el inventario de 40 campos; correcta: se recorta a los 5 que hacen falta antes de que se acumule. `--anti sin_recorte`.
- Señal: tokens de entrada acumulados por turno, leídos de `usage`.
- Tests: recorte y cuenta de campos.

## Riesgos y sondas (antes de codificar el módulo afectado)

- **A2 · Batches:** disponibilidad con Haiku 5.5, latencia de un lote pequeño, `usage` y coste con el 50 %, y forma del resultado por `custom_id`. Si el lote tarda demasiado para una sesión, el módulo se queda en `--enviar` y `--batch-id`, sin esperar.
- **A2 · Reintento con Haiku 5.5:** comprobar que el reintento con error concreto corrige y que el genérico no; si no hay diferencia, Haiku 4.5; si tampoco, la diferencia se enseña de forma determinista con una respuesta fija del modelo. *Resultado:* con Haiku 5.5 no hubo diferencia y con Haiku 4.5 sí, así que `08` pasó al rol `enforcement`.
- **A3 · `07` con Haiku 5.5:** la señal de *nullable* puede no verse (el modelo pone `null` aunque el campo sea obligatorio). Mismo protocolo. *Resultado:* la señal de *nullable* sí se vio con Haiku 5.5. La del *few-shot* solo se vio con Haiku 4.5, y la de `enum_cerrado` apareció de otra forma: valores fuera del `enum`.
- **B · coordinador y *timeout*:** que el reintento local del subagente no se vea como un fallo en el recorder; y que `DISABLE_BACKGROUND_TASKS` siga bastando en la CLI fijada.
- **C1 · `claude -p`:** en la CLI que se use (instalada o la del SDK fijado), forma de la salida JSON con `--json-schema`, flags de aislamiento (fuentes de configuración, MCP estricto, entorno de §3) y si existe un tope de coste por flag. Sin la sonda no se codifica `11` (roadmap §2). Si no hay tope por flag, el módulo lo acota por otra vía y lo comenta.
- **C · autorrevisión con `resume`:** el coste acumulado de la sesión reanudada (§4.3) entra en el tope de esa rama.

El resultado de cada sonda va a `docs/hallazgos.md`, con `→ roadmap` si le pasaría a otra persona.

## Modelo de cada paso

«Sesión» es el modelo de la sesión de Claude Code que construye. «App» es el modelo con el que se ejecuta el módulo, fijado por `.env` y `harness/config.py`.

| Paso | Sesión | App | Por qué |
| :--- | :--- | :--- | :--- |
| Este diseño y el roadmap en lo que cambie | Opus 5.5 | — | Criterio de diseño |
| Datos, arnés, servidores y sus tests | Sonnet 5.5 | — | Mecánico, lo validan los tests |
| Sondas | Sonnet 5.5 | El del módulo (Haiku 5.5; Haiku 4.5 si falla; Sonnet 5.5 en `reviewer`) | Se ejecutan de verdad |
| Código y tests de cada módulo | Sonnet 5.5 | Tanda A y D: Haiku 5.5 · tanda B: Sonnet 5.5 + Haiku 5.5 · tanda C: Sonnet 5.5 (`reviewer`), Haiku 5.5 en `10` | Siguen el patrón de las entregas anteriores |
| Cabeceras (`QUÉ DICE LA GUÍA` · `ANTI-PATRÓN`), secciones del README, predicciones y preguntas tipo examen | Opus 5.5 | — | Criterio didáctico que ningún test comprueba |
| Revisión independiente de cada tanda | Opus 5.5 en una instancia nueva (`claude -p --model opus` con un prompt de `docs/prompts-entrega-3/`) | — | No revisa quien escribió. Los subagentes con Opus dieron 429 en el Hito T |
| Correcciones | Sonnet 5.5 (código) · Opus 5.5 (texto) | — | Cada uno, lo suyo |
| Roadmap origen | Opus 5.5 | — | Texto agnóstico con criterio |
| Registro (`NOTAS.md`, `CONCEPTOS.md`) | Sonnet 5.5 | — | Mecánico |

**El cambio se pide, no se asume.** La sesión no puede cambiar su propio modelo. Al empezar un paso cuyo modelo no es el actual, se detiene, dice qué paso empieza y qué modelo le toca, y espera a que la persona cambie con `/model`. Si decide seguir con el actual, se anota en `NOTAS.md`.

**Orden dentro de cada tanda:** con Sonnet, los datos, el código, los tests y las sondas de los tres módulos; con Opus, los textos de los tres a la vez; después, la revisión en una instancia nueva. Así hay dos cambios de modelo por tanda.

## Cuándo se actualiza el roadmap origen

Flujo de roadmap §12: lo que aparece al construir se anota en `docs/hallazgos.md` con `→ roadmap` y, al llevarlo, se reduce a `✓ roadmap YYYY-MM-DD §x`. Se lleva en tres momentos:

1. **Al cerrar este diseño:** lo que el diseño cambia del roadmap (rol `reviewer` en §5).
2. **Al fusionar cada tanda:** sus notas `→ roadmap` (§4.3, §6–§8, §11), con su línea en §14. El roadmap nunca va más de una tanda por detrás. Si la sonda C1 confirma `harness/headless.py` y el aislamiento de `claude -p`, entran aquí (§3 regla 3 y §5).
3. **Al cerrar la entrega:** solo lo transversal (§9, §10) y la comprobación de que no queda ningún `→ roadmap`, salvo los que esperan confirmación.

Siempre con Opus 5.5, sin avance de la implementación, sin fechas de calendario ni rutas de una máquina, y con una copia previa, porque el roadmap no está en git.

## Registro y cierre

- `CONCEPTOS.md`: ☑ y contador en el mismo cambio que cada `INTRODUCE`.
- `NOTAS.md`: casilla de la entrega 3, una línea por tanda.
- `docs/hallazgos.md`: sondas y notas `→ roadmap`.
- Al final: quitar el `xfail` de `test_full_coverage`.

## Verificación

1. Tras cada módulo: `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio.
2. Con modelo, con y sin `--anti`, con el coste de cada `[fin]` dentro del tope:
   - `app3/07`: campos ausentes como `null` y no inventados; tipo raro como `other` con detalle.
   - `app3/08`: un reintento útil y uno inútil; `conflict_detected` en los totales que no cuadran.
   - `app3/09`: lote terminado y fallidos reenviados por `custom_id`.
   - `app3/04`: resultado parcial con la brecha anotada.
   - `app3/05`: afirmaciones con su fuente y cifras en conflicto sin fusionar.
   - `app3/06`: retoma desde el *manifest* tras la caída simulada.
   - `app3/11`: JSON válido contra el schema y fallos sembrados encontrados.
   - `app3/12`: hallazgos que la autorrevisión no ve.
   - `app2/04`: acción por caso frente a la etiqueta.
   - `app1/07`: menos tokens acumulados con recorte.
3. `[contexto]` sin la capa meta (§11.6), también en la orden de `claude -p`.
4. `/verificar-concepto` sobre una viñeta de cada tanda; `/practica-guiada` lista los módulos nuevos con su Modo.
5. Tras cada actualización del roadmap: ningún `→ roadmap` de la tanda sin puntero, línea en §14, sin rutas, nombres ni fechas de calendario.
6. Final: 240/240 y `test_full_coverage` en verde sin `xfail`.

Coste orientativo con modelo: unos 6–10 $. La mayor parte va a la tanda B (coordinador Sonnet) y a `app3/11`–`12` (`reviewer` Sonnet); el batch es barato (Haiku al 50 %).
