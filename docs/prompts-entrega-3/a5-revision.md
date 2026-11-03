Eres una instancia independiente y no tienes contexto previo. Revisa la tanda A de la entrega 3 de este repositorio. No edites nada: informa de los hallazgos ordenados por gravedad, con archivo y línea en cada uno.

Qué revisar: `git diff main...entrega-3a`. Son `app3_sistema_multiagente/07_extraccion_schema.py`, `08_validacion_reintento.py` y `09_batches.py`, sus secciones en `app3_sistema_multiagente/README.md`, sus tests, `datos/generar_sinteticos.py`, `harness/budget.py`, `harness/config.py`, `CONCEPTOS.md`, `docs/hallazgos.md`, `docs/diseno-entrega-3.md` y `NOTAS.md`.

Las reglas están en `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md` y `.claude/rules/`.

Comprueba lo siguiente:

1. **Guía.** Compara las cabeceras y las respuestas de las preguntas tipo examen con las Task Statements 4.2 a 4.5 de la Exam Guide (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio). Busca una cita de K/S que no corresponda a su viñeta, texto copiado en vez de parafraseado, mecanismos fuera del perímetro (`tests/perimetro_excluido.yaml`) y viñetas asignadas en `CONCEPTOS.md` que el módulo no ejercite de verdad, sobre todo 4.3-S3, 4.4-K3/S3 y 4.5-S2.
2. **Hechos frente a inferencias.** Cada cabecera debe separar los hechos de la guía de las inferencias propias y de las notas `EN PRODUCCIÓN (no evaluable)`. Señala cualquier observación de este repositorio que se presente como si lo dijera la guía.
3. **Cifras.** Las cabeceras, el README, `docs/hallazgos.md` y `NOTAS.md` tienen que coincidir. Las sondas A2 y las ejecuciones del módulo son medidas distintas: señala dónde se mezclan sin decirlo.
4. **Didáctica.** Revísala contra las reglas 1 a 5 de «Incorporación de quien llega de cero», en roadmap §13 (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`, en el repositorio de estudio):
   - El contexto no adelanta resultados.
   - Las predicciones se plantean por patrón, no por valor.
   - Los términos comunes se enlazan al glosario.
   - En las preguntas tipo examen, las cuatro opciones son plausibles, tienen longitud y registro parecidos, y la correcta no está siempre en la misma posición.
   - Haz una lectura en frío: alguien que solo haya leído el README raíz y el módulo, ¿podría predecir?
5. **Código.**
   - Que los tests nunca llamen al modelo.
   - `max_budget_usd` o `CostGuard` en toda ejecución con modelo.
   - Errores de lógica en `conforms`, en la puntuación contra etiquetas, en el bucle de reintento, en `classify_result`, en el troceo y en `submission_interval` y `route_workload`.
   - Los datos se generan solo desde `datos/generar_sinteticos.py`.
   - Regla «una vez»: un `INTRODUCE` por viñeta y su ☑ en `CONCEPTOS.md`.
6. **Notas `→ roadmap`** de `docs/hallazgos.md` (sección «Entrega 3 · tanda A»). ¿Le pasarían también a otra persona, con otra máquina y otra cuenta, o dependen de esta implementación?

Puedes ejecutar `uv run pytest -q` y `uv run python app3_sistema_multiagente/09_batches.py --ventanas`, que no usa modelo. No ejecutes nada que llame al modelo.
