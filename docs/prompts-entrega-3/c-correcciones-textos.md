Tanda C de la entrega 3: correcciones de textos tras la revisión independiente (Opus 5.5). Trabajas en la rama `entrega-3c`, **después** de las correcciones de código de Sonnet 5.5 (`docs/prompts-entrega-3/c-correcciones-codigo.md`) y con sus cifras. No cambies código ni datos: si un texto exige otro cambio de código, anótalo al final.

Lee primero `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md`, `NOTAS.md` (casilla de la tanda C), `docs/hallazgos.md` (secciones de la tanda C, «antes» y «después» de las correcciones) y `docs/tipos-de-senal.md`. El informe de la revisión independiente numera los hallazgos; los números de abajo son los suyos.

**Regla general:** donde el código haya vuelto a medirse, el README, las cabeceras, `tipos-de-senal.md`, `hallazgos.md` y `NOTAS.md` usan las cifras nuevas y dicen cuáles son anteriores. Ninguna cifra se calcula aquí; si dos documentos no coinciden, no eliges: lo anotas al final. En el examen manda la guía; lo observado va en el Paso 3 rotulado `Producto observado (no evaluable)`.

**`app3/11`**
- (2) «Al revés de lo esperado» en los tests existentes (README, `hallazgos.md`, `NOTAS.md`, `tipos-de-senal.md`) era con mucha probabilidad un artefacto de la medida (se puntuaba el test roto como duplicado). Reescríbelo según la medida nueva: si desaparece, dilo y explica el artefacto; si persiste, dilo con su cifra. Nunca «al revés» sin la medida que lo sostiene.
- (1) Las cifras de la revisión anteriores a la corrección estaban contaminadas (el revisor leía el árbol ya corregido): marca «antes» y «después», y revisa la hipótesis sobre las pérdidas de A en `conservador`.
- (6) README:«nada más cambia» de `--sin-categoria comment` y la nota de la pregunta 1 leen como comportamiento del modelo algo que era la variante: reescríbelo con la variante ya corregida y su medida nueva.
- (7), (8) Avisa de lo que la puntuación por símbolo no distingue (si queda algo) y de que las cifras de `sin_ejemplos` anteriores mezclaban dos puntuaciones; la hipótesis «el ejemplo se parece a B» admite la alternativa de un acierto mal puntuado.
- (16) Presenta las letras A a F antes de «Qué observar». En la multiple-response, la correcta traduce casi literalmente 3.6-S3 y S5 y la C es un distractor débil: reformula las opciones para que se juzguen por el concepto y no por el vocabulario.

**`app3/12`**
- (3) La cita de 1.6-S2 en la cabecera (líneas 17–19 del módulo) corresponde a 1.6-S1, que está introducida en `app3/02`: ahí es `USA`, y 1.6-S2 (partir la revisión en pasadas por archivo más una de integración) es lo que el módulo ejercita. Corrige la cabecera y comprueba que el `INTRODUCE` y los `USA` siguen en regla (`tests/test_una_vez.py`).
- (10) «Esto sí respalda 4.6-K3/S2» fuerza la guía mientras no había una rama de una sola pasada. Con `--anti una_pasada` ya medido, escribe lo que muestre la medida y nada más; el reparto sin tools ni llamadores es en parte consecuencia del diseño, y se dice.
- «Control positivo» estaba mal nombrado en la batería de autorrevisión: que la correcta lo encuentre todo no prueba que la medida pueda registrar una pérdida; esa prueba es la pasada por archivo de la instancia nueva, que pierde F. La regla de tres sobre «25 oportunidades» supone independencia y son 5 ejecuciones sobre el mismo diff. `tests/test_sla.py` ya existía en la base y se modificó (no «se añadió»).
- (15) Calibración con 2 ejecuciones y tabla con 3 (README, sección de `12`) sin explicación; «cada repetición recibe lo que queda» no coincide con el código (`min(lo que queda, budget/repeat)`).

**`app3/10`**
- (4) «34 errores con confianza ≥ 0,85 de 41» mezcla bases: calibración 17 de 19 y producción 17 de 22; di en cuál se calcula cada cifra.
- (5) Con la variante corregida, vuelve a describir qué cambia (solo la confianza por documento) y re-escribe las cifras de los errores y del tipo raro.
- (12), (13) La muestra estratificada sobrerrepresenta el tipo raro (18 de 60 frente al 4 % de la población): explícalo y presenta la tasa ponderada que añadió Sonnet. Los conflictos y los errores son independientes porque el generador los sortea así (hay 0 errores en documentos marcados en producción): rotúlalo como propiedad de los datos y no como lección. 5.5-S3: los umbrales solo se fijan sobre la confianza simulada; la parte con modelo mide la calibración. Dilo en el README.

**Sonda C1 y registro**
- (17) `docs/hallazgos.md`: las marcas de memoria de usuario (`~/.claude/CLAUDE.md`, `~/.claude/rules/`) se probaron con un `CLAUDE_CONFIG_DIR` temporal; con la configuración real solo se miraron skills, MCP y comandos. Declara ese hueco. Las notas `→ roadmap` pasan tal cual salvo «el modelo cita las líneas 3–5 de más»: se generaliza solo como lección («puntuar también por símbolo»), porque la cifra depende de este diff y de esta puntuación.
- (11), (15) Reconcilia en `NOTAS.md` y `hallazgos.md` la contradicción de la casilla de la tanda C y las cifras sueltas (sonda C1, coste de `11`), con lo que dejó Sonnet. Coste total real de la tanda en `NOTAS.md`.

**`docs/tipos-de-senal.md`**
- Aplica la propuesta de Sonnet para las filas medidas de nuevo. Para `app3/12`: las filas de `autorrevision` y `autorrevision_explicita` quedan `Sin señal estable`; `--parte revision` (instancia nueva) solo es `Probabilística con control positivo` si `--anti una_pasada` dio una señal medida frente al reparto por pasadas; si no, `Sin señal estable`. Una fila es `Probabilística con control positivo` solo si hay variante correcta frente al anti-patrón (definición del estándar). `tests/test_tipos_de_senal.py` en verde.

**Didáctica fuera de la tanda (16)**
- La longitud de la correcta en `app3/01` y la posición B en 5 de 6 preguntas de `app2` no se tocan aquí (`app2/04` se reescribe en la tanda D). Anótalo en `NOTAS.md` como pendiente de la tanda D.
- En la pregunta de `10`, D (149 caracteres) es la más larga y acumula el vocabulario de la guía: iguala longitud y registro y mueve la correcta de posición si hace falta (las posiciones de `01`–`09` están en `NOTAS.md`).

**Reglas de siempre**
- Regla «una vez»: ningún `INTRODUCE` se mueve ni se duplica; ☑ y contador en `CONCEPTOS.md` quedan en 225/240.
- Textos agnósticos: rutas relativas, sin nombres, cuentas ni perfiles.
- Sin modelo: no ejecutes nada que llame a la API. `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- Un commit por módulo y uno para registros. En `NOTAS.md`, marca las correcciones de la revisión como hechas y deja pendientes la fusión, `/verificar-concepto` y el roadmap origen (momento 2).

**Informe final:** commits; hallazgos resueltos, parcialmente resueltos o no aplicables, con motivo; discrepancias de cifras que no resolviste; cambios de código que los textos piden y no hiciste.
