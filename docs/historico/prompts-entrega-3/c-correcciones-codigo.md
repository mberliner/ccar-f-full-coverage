Tanda C de la entrega 3: correcciones de código tras la revisión independiente (Sonnet 5.5). Trabajas en la rama `entrega-3c`. Solo código, datos del generador, tests y registro de cifras: **no toques cabeceras ni README** (los reescribe Opus 5.5 después, con tus cifras). Si algo exige decidir un texto, anótalo al final.

Lee primero `CLAUDE.md`, `docs/estandares-codigo.md`, `app3_sistema_multiagente/CLAUDE.md`, `docs/hallazgos.md` (sonda C1, tanda C y batería de autorrevisión) y los módulos `app3/10`, `11`, `12` y `harness/headless.py`.

Los números entre paréntesis son los del informe de la revisión independiente. Tests primero (un test que falle antes de corregir, con su falso positivo y su falso negativo), un commit por grupo, `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit. Los datos solo se cambian en `datos/generar_sinteticos.py`.

**Grupo 1 · `app3/11`: la medida estaba contaminada**
- (1) `build_review_repo` termina en `commit_2` y `run_revision` revisa el diff de `commit_1` con el árbol en `commit_2`: el revisor lee el código ya corregido. Haz que cada revisión corra sobre un árbol en el commit que revisa (copia o `checkout` desacoplado, sin tocar la copia de otra rama). Test: en la revisión del primer commit, `tickets/escalado.py` y `informes/resumen.py` tienen el fallo sembrado, no el arreglo.
- (2) `scenario_key` ignora `expected`: actualizar un test roto cuenta como duplicado. Incluye `expected` en la clave. Añade a `existing_scenarios` el escenario de `informes/tests/test_resumen.py` que el cambio también rompe. Test del caso «test con `expected` en minutos».
- (7) La coincidencia por símbolo es laxa en el mismo archivo: un hallazgo sobre el señuelo `REINTENTOS` que nombra `TIMEOUT` puntúa como acierto de C. Corrígelo y cubre el caso con un test («señuelo que nombra el símbolo de un fallo del mismo archivo»). Además, `TIMEOUT` se define dos veces en los datos (30 y 60) y la segunda pisa la del cliente: decide en el generador si es un fallo real y se etiqueta, o se quita la duplicación. Documenta la decisión en `NOTAS.md`.
- (6) `--sin-categoria comment` no solo quita la categoría: la severidad `minor` sigue definida como «un comentario engaña» (con ejemplo) y el criterio de `bug` menciona el docstring. La variante debe cambiar una sola cosa.
- (8) Los resultados de `sin_ejemplos` mezclan dos puntuaciones (ventana de líneas y símbolo). No se arregla con código: se vuelve a medir en el grupo 5.

**Grupo 2 · `harness/headless.py`**
- (9) `probe_context` ejecuta `claude -p` sin imprimir la orden y su coste no entra en ningún `Ledger`; `run()` acepta cualquier `cmd` sin comprobar `--max-budget-usd`. Imprime la orden entera antes de ejecutar, mete su coste en el `Ledger` (`11` puede pasar de `--budget`) y haz que `run()` rechace una orden sin tope. Tests de cada caso.

**Grupo 3 · `app3/10`**
- (5) `--anti confianza_global` cambia dos cosas (confianza por documento y un único umbral global). Que cambie una: `doc_confidence` con un umbral por segmento. Reajusta el test.
- (12) `stratified_sample` devuelve más de `n` cuando los mínimos suman más que `n` (10 estratos, mínimo 3, n=12 devuelve 30): rechaza o recorta, con test. Estimación de la tasa de error **ponderada** por el tamaño de cada estrato (la otra mitad de 5.5-S1): añádela como función sin modelo, con test, y que `10` la muestre junto a la tasa de la muestra.

**Grupo 4 · `app3/12`**
- (14) `generated_diff` y `matches_target` usan `git diff base` y no ven los archivos nuevos sin seguimiento: inclúyelos (p. ej. `git add -N`), con test. El `.git` de la copia conserva en el reflog el mensaje del commit 2, al alcance de `Grep`: límpialo o impide que el revisor lo lea. `MERGE_WINDOW` puede fusionar dos hallazgos distintos del mismo archivo y categoría: test del falso negativo y, si no se corrige, que el módulo lo avise.
- **Variante nueva `--anti una_pasada`** (cambia una sola cosa respecto a la correcta): una única pasada larga sobre todo el diff, sin pasada por archivo ni de integración. Es el contraste que le falta a 4.6-K3/S2 (la revisión indica que no hay rama contra la que comparar el reparto por pasadas). Tests sin modelo de la orden construida.

**Grupo 5 · Medir de nuevo (tope total de la tarea: 4 $; si va a pasar, para y avisa antes)**
Todo con el código ya corregido y **la puntuación fija durante la batería** (si la cambias a mitad, repites la batería). `--budget` no sube el tope por encima del de `.env`: comprueba el aviso del arnés antes de cada tanda y sube `CCARF_BUDGET_MULTIAGENT` en el entorno si hace falta, sin tocar `.env` salvo que te lo digas.
1. `app3/11 --parte revision`: correcta, `--anti conservador`, `--anti sin_ejemplos` y `--sin-categoria comment`, `--repeat 5` cada una (cifras x/5, con la puntuación por símbolo).
2. `app3/11 --parte tests`: correcta, `--anti sin_tests_existentes` y `--anti sin_estandares`, `--repeat 5` cada una, ahora puntuando `expected`.
3. `app3/10`: la parte con modelo y `--anti confianza_global`, con el umbral por segmento.
4. `app3/12 --parte revision --anti una_pasada --repeat 5`, y la instancia nueva con `--repeat 5` sobre el mismo diff (el generador no debe añadir archivos que no estén en el cambio dado; si ocurre, dilo).
Informa por variante: ejecuciones, fallos sembrados encontrados, falsos positivos, coste, y qué señales cambian respecto a «antes». Puede que «al revés de lo esperado» en los tests desaparezca, y que A deje de perderse: es el resultado, no se fuerza.

**Registro**
- `docs/hallazgos.md`: las mediciones anteriores bajo «antes de las correcciones C4» y las nuevas bajo «después», con la cifra de cada una. Cifras de coste reconciliadas: la sonda C1 (~0,4 $ en `hallazgos.md` y ~0,3 $ en `NOTAS.md`) y el coste de `11` (~1,0 $ en README y ~1,1 $ en `hallazgos.md` y `NOTAS.md`): elige el correcto sumando las ejecuciones registradas y anota cuál era.
- `NOTAS.md`: corrige la contradicción de la casilla de la tanda C (línea de la batería de autorrevisión «medida» frente a «autorrevision_explicita quedó sin medir» y el tope de ≈ 2,9 $), con el coste real total de la tanda.
- No actualices `docs/tipos-de-senal.md`: propón las filas que corresponden con los datos nuevos, y Opus las aplica.

**No hagas (decisión tomada)**
- Rehacer la sesión generadora de `12` para que diseñe en vez de copiar: queda como limitación documentada.
- Tocar el README, las cabeceras, el glosario o el estándar.

**Informe final:** commits; por grupo, qué cambió y qué test lo prueba; tabla de cifras «antes» y «después» por variante con ejecuciones y coste; qué señal desapareció, apareció o se mantuvo; y los textos que tu cambio deja desfasados (lista exacta para Opus).
