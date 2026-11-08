Eres una instancia independiente y no tienes contexto previo. Revisa la tanda D de la entrega 3 de este repositorio. No edites nada: informa de los hallazgos ordenados por gravedad, con archivo y línea en cada uno.

Qué revisar: `git diff main...entrega-3d`. Son `app2_agente_con_control/04_few_shot_y_escalamiento.py`, `app1_agente_unico/07_recorte_de_contexto.py`, sus secciones en los README de `app1_agente_unico` y `app2_agente_con_control`, `app2_agente_con_control/servers/helpdesk.py` (`find_employee_by_name`), `harness/recorder.py` (`texts`), `datos/generar_sinteticos.py`, sus tests, `CONCEPTOS.md` (240/240), `docs/glosario.md`, `docs/hallazgos.md` (tanda D), `docs/tipos-de-senal.md`, `docs/credenciales-y-modos.md`, `docs/simulaciones-por-escenario.md`, `harness/narrador.py` y `tests/test_narrador.py`, `tests/test_una_vez.py` y `NOTAS.md`.

Las reglas están en `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md` y `.claude/rules/`.

Comprueba lo siguiente:

1. **Guía.** Compara las cabeceras y las respuestas de las preguntas tipo examen con las Task Statements 4.2 (K1–K3, S1) y 5.2 (K1–K4, S1–S5) en `04`, y 5.1 (K3, S3) en `07`, de la Exam Guide (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio). Busca:
   - una cita de K/S que no corresponda a su viñeta;
   - texto copiado en vez de parafraseado;
   - mecanismos fuera del perímetro (`tests/perimetro_excluido.yaml`);
   - viñetas que el módulo no ejercite de verdad, sobre todo 4.2-K2 (selección de tools ante una petición ambigua) y 4.2-K3 (generalizar a patrones nuevos), 5.2-K1 (la imposibilidad de avanzar como disparador) y 5.1-K3 (cuarenta campos frente a cinco);
   - **respuestas de examen que sigan lo observado en vez de la guía.** Con Haiku 5.5, `sin_ejemplos` sale peor que la correcta en los homónimos (56/65 frente a 63/65); con Haiku 4.5 la señal está repartida por tipos. En el examen manda la guía; lo observado va solo en el Paso 3 y con el rótulo `Producto observado (no evaluable)`.
2. **Hechos frente a inferencias.** Cada cabecera debe separar los hechos de la guía de las inferencias propias. Señala cualquier observación de este repositorio presentada como si la dijera la guía. Candidatos: el proxy de sentimiento (una lista de palabras inventada), que `sentimiento` y `confianza` vayan sin ejemplos y se comparen con `sin_ejemplos`, y que en `07` la lista de campos que se conservan la fije el código.
3. **Cifras.** Cabeceras, README, `docs/hallazgos.md`, `docs/tipos-de-senal.md`, `docs/credenciales-y-modos.md` y `NOTAS.md` tienen que coincidir. `07`: ≈ 16 000 frente a ≈ 54 000 tokens de entrada, 10/10 correctas. `04`, segunda medida (13 casos, vigente): con Haiku 5.5, 63/65, 56/65, 30/65 y 44/65; con Haiku 4.5, 35/39 y 32/39; el proxy, 3/13. La primera medida (11 casos) consta en `docs/hallazgos.md` como anterior y no debe aparecer en ningún README ni cabecera. Señala dónde se mezclan modelos, repeticiones o medidas sin decirlo, o dónde se presenta una cifra que no existe. El coste de la tanda (≈ 2,0 $) es una estimación: dice si está bien presentada.
4. **Didáctica.** Revísala contra las reglas 1 a 5 de «Incorporación de quien llega de cero», en roadmap §13 (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`, en el repositorio de estudio):
   - El contexto no adelanta resultados.
   - Las predicciones se plantean por patrón, no por valor, y no preguntan lo que el contexto ya responde.
   - Los términos comunes se enlazan al glosario.
   - En las preguntas tipo examen, las cuatro opciones son plausibles, tienen longitud y registro parecidos y la correcta no está siempre en la misma posición ni es la más larga (mira también las de `app1/01`–`06` y `app2/01`–`07`: en `app2` la correcta estaba en B en 5 de 6). La multiple-response de `04` declara cuántas elegir, tiene al menos una opción de más y como máximo cuatro, y cada opción se juzga sola.
   - Haz una lectura en frío: alguien que solo haya leído el README raíz y el módulo, ¿podría predecir?
5. **Código.**
   - Que los tests nunca llamen al modelo y que `max_budget_usd` esté en toda ejecución con modelo (en `07`, `CostGuard`); que el tope sea el de toda la ejecución, repartido entre repeticiones y casos.
   - `04`: que la acción se deduzca de las llamadas a tools y no del texto (`classify_turn`, `is_correct`). Para cada tipo de caso, el falso positivo y el falso negativo posibles y si hay test. Que «no escala» incluya pedir un identificador y responder otra cosa, sin distinguirlos, está declarado: dime si el README lo avisa bien. Que la frustración se mida en dos turnos y que el coste de la sesión (acumulado) no se cuente dos veces.
   - `04`: que cada `--anti` cambie una sola cosa respecto de su control (`sentimiento` y `confianza` llevan además criterios y ejemplos fuera, y se comparan con `sin_ejemplos`), y que los ejemplos few-shot no sean ninguno de los casos evaluados.
   - `07`: que el recorte ocurra antes de que el resultado entre en el historial y que `answer_is_correct` (primer equipo nombrado) no dé falsos positivos con respuestas que nombran varios equipos.
   - `helpdesk.py`: que `lookup=True` sea opcional y que los demás módulos de `app2` no vean una tool más; `harness/recorder.py`: que `texts` no cambie nada de lo que ya hacía.
   - El módulo `04` no usa `disallowed_tools` (perímetro): comprueba que las tools que no vienen al caso no queden pre-aprobadas.
   - Los datos se generan solo desde `datos/generar_sinteticos.py`, el generador es determinista y los conjuntos viejos no cambiaron (`tickets.json` y sus IDs).
   - Regla «una vez»: un `INTRODUCE` por viñeta y su ☑ en `CONCEPTOS.md` (240/240); `test_full_coverage` sin `xfail`.
6. **Registros.** `docs/tipos-de-senal.md` y `docs/credenciales-y-modos.md` coinciden con lo que dicen los README; el narrador ya no tiene módulos pendientes y los tests de «pendiente» usan una copia del README (`tests/test_narrador.py`); el estado de preparación de `docs/simulaciones-por-escenario.md` es coherente con 240/240.
7. **Notas `→ roadmap`** de `docs/hallazgos.md` (tanda D). ¿Le pasarían también a otra persona, con otra máquina y otra cuenta, o dependen de esta implementación?

**Pendientes conocidos: no los señales como hallazgos, pero sí di si el registro los describe bien.**
- Las cabeceras y los README de `04` y `07` los escribió Sonnet 5.5 y pasan después por Opus 5.5 (`docs/prompts-entrega-3/d-textos.md`). Si la revisión se hace antes de esa pasada, no señales el estilo, solo lo que contradiga la guía, el código o las cifras.
- La muestra con Haiku 4.5 es de 3 repeticiones (35/39 y 32/39) y la confianza declarada se midió dos veces con n pequeño, con el sentido de la diferencia cambiado entre una y otra: valora si el README las presenta con esa cautela.
- Tras el pase de Opus se hicieron dos cambios de código y se actualizaron los textos **sin pasar por Opus**: el caso de «no se puede avanzar» (criterio 5 sin ejemplo) y la comprobación de que el agente pidió un identificador en los homónimos. Revisa en especial que el detector de palabras (`asks_for_identifier`) tenga tests de falso positivo y de falso negativo, que el README lo describa con su límite y que la explicación de por qué `sin_ejemplos` falla en los homónimos vaya rotulada como inferencia propia.

Puedes ejecutar `uv run pytest -q`. No ejecutes nada que llame al modelo.
