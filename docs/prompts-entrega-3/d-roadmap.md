Tanda D de la entrega 3: **roadmap origen, momento 2 (la tanda) y momento 3 (cierre de la entrega)**, con Opus 5.5. Trabajas en la rama `main` de este repositorio (la tanda D ya está fusionada, sin `push`) y editas además el roadmap origen: `docs/roadmap-apps-demo-ccar-f.md` del repositorio de estudio (`claude-cert-ccar-f`, hermano de este en el árbol de proyectos). El roadmap **no es un repositorio git: no hagas commit allí**. No cambies código, datos ni tests de este repositorio.

Lee primero `CLAUDE.md`, `docs/estandares-flujo.md` («Registro entre sesiones» y la regla `→ roadmap` / `✓ roadmap`), el roadmap (§4.3, §8 filas de `app2/04` y `app1/07`, §10 fila 3, §12 «Mantener la plantilla al día», §14), `docs/hallazgos.md` (secciones de la tanda D: `app1/07`, y `app2/04` cuarta medida y anteriores), `NOTAS.md` (casilla de la tanda D) y, como modelo de lo mismo hecho antes, la entrada de la tanda C en `NOTAS.md` y las líneas §14 con fecha 2026-11-07 del roadmap.

**Reglas de contenido**
- Español, agnóstico: sin rutas absolutas, nombres de personas, cuentas ni perfiles. Ediciones mínimas con `Edit`. Una lección es de roadmap solo si le pasaría igual a otra persona con otra máquina y otra cuenta; lo que depende de esta implementación o no está comprobado se queda en `docs/hallazgos.md` (criterio de §12).
- Carriles: lo observado es `Producto observado (no evaluable)`; lo que la guía no nombra, `EN PRODUCCIÓN (no evaluable)`; una inferencia propia se rotula así. Los rótulos se escriben exactamente así.
- No copies texto de la guía ni preguntas del examen.

**Qué hay que llevar al roadmap (momento 2)**

1. **§8, filas de `app2/04` y `app1/07`:**
   - `app2/04` (4.2-K1–3, S1 y 5.2-K1–4, S1–5): los cuatro tipos de caso (petición de humano, frustración, vacío de política, «no se puede avanzar» y homónimos), la medida por llamadas a tools y no por el texto, el detector de «pidió un ID» solo en los homónimos, y que **los ejemplos no se notan de forma estable**: con Haiku 5.5, 58/65 frente a 56/65 (homónimos a favor, un único caso; frustración al revés); con Haiku 4.5, 31/39 frente a 33/39, y la frustración de `sin_ejemplos` dio 7/9, 4/9 y 6/9 con el mismo prompt. `sentimiento` (30/65) sí muestra el fallo; `confianza` declarada no separa aciertos de fallos. Nada de esto cambia la respuesta de examen.
   - `app1/07` (5.1-K3, S3): recorte en el handler antes de que el resultado entre en el historial (≈ 16 000 frente a ≈ 54 000 tokens de entrada); es señal de tokens, no de calidad; la comprobación de la respuesta por texto libre tiene límites declarados y la versión de producción es salida estructurada (`EN PRODUCCIÓN (no evaluable)`).
2. **§4.3, lecciones nuevas o ampliaciones** (revisa primero las que ya existen y amplía en vez de duplicar):
   - **Una comprobación sobre texto libre falla en los dos sentidos y sus límites se declaran y se fijan con tests** (`known_limit`): en `app1/07` la prioridad por ID invierte el resultado cuando solo un equipo lleva ID, y exigir la mayúscula pierde aciertos. Versión de producción: salida estructurada con un campo comprobable, casos etiquetados medidos en muchas ejecuciones y, con calibración humana, otro modelo como juez. Ya hay una nota `→ roadmap` sobre «las medidas de texto fallan en los dos sentidos»: amplíala.
   - **Corregir un detector exige tests de falsos positivos y de falsos negativos, no solo del caso que se arregla:** el detector de «pidió un ID» de `app2/04`, ya corregido una vez, introdujo falsos positivos nuevos («¿Cuál es el error?», «¿Me pasas tu número de ticket?») y perdió formas naturales («¿Me das el ID de empleado?»); lo encontró la segunda revisión. Un «?» solo no es una petición ni un posesivo solo es un dato.
   - **Una señal que oscila entre medidas con el mismo prompt no es una señal:** compara medidas repetidas de la variante de control antes de atribuir una diferencia a la técnica; si la oscilación de la propia variante iguala la diferencia, es `Sin señal estable`. Una medida con otro detector o otra comprobación **no es comparable** con las anteriores.
   - **Un caso cortado por el tope de gasto no puntúa y se avisa; la insistencia no se lanza tras un turno cortado o con error.** El SDK comprueba `max_budget_usd` **al cerrar cada turno**, así que el gasto real de un caso y el total pueden pasarse algo del tope (no medido cuánto). Con tope por partes iguales, un caso de dos turnos se corta aunque el total no se agote. Ya hay una nota `→ roadmap` sobre esto en `docs/hallazgos.md`: llévala.
   - **Guardar el texto del agente en las salidas de una medida**, no solo la acción clasificada: sin él no se pueden auditar los aciertos de un detector de texto (la cuarta medida de `app2/04` no pudo comprobar uno a uno los homónimos). Es una mejora de la plantilla, no un hecho de producto.
   - **Los topes de gasto de una ejecución los fija `.env` y mandan sobre la shell:** subirlos exige cambiar `.env`, no exportar una variable. Solo si el roadmap documenta ya el orden de prioridad de la configuración; si no, queda en `docs/hallazgos.md`.
3. **§10, fila 3** (entrega 3, D4 y D5): marca la entrega como cerrada: 240/240, cuatro tandas fusionadas a `main`, cada una con su revisión independiente y sus correcciones. No inventes una fecha distinta de 2026-11-08.
4. **§14:** una línea fechada 2026-11-08 con el estilo de las demás: cierre de la entrega 3 y las lecciones llevadas.
5. **§12 «Mantener la plantilla al día»:** solo si lo aprendido cambia algo del criterio (por ejemplo, que una revisión independiente de un cambio de detector debe pedir tests de falsos positivos); si no, no lo toques.

**En este repositorio**
- `docs/hallazgos.md`: las notas marcadas `→ roadmap` que lleves se reducen a un puntero `✓ roadmap 2026-11-08 §x` (la nota de la comprobación de `app1/07` y la del tope de gasto de `app2/04`, más las que encuentres con `grep`). Las demás se quedan solo allí.
- `NOTAS.md`: marca `[x]` la «Entrega 3 · D4 y D5 (`S-2`)» con la fecha, y deja en la tanda D el momento 2 y el cierre como hechos. No toques `S-1` ni la entrega 4.
- `docs/diseno-entrega-3.md`: no hace falta cambiarlo.

**Verificación y commits**
- Sin modelo: no ejecutes nada que llame a la API. Antes del commit, `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio (los tests de carriles y de comparación de modelos leen `docs/`).
- Un commit en este repositorio (`docs/hallazgos.md` y `NOTAS.md`). El roadmap no se commitea.
- Informe final: qué secciones del roadmap cambiaste (con las líneas aproximadas), qué notas pasaron a puntero, qué te dejaste en `docs/hallazgos.md` y por qué, y cualquier discrepancia entre el roadmap y este repositorio.
