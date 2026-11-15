Eres una instancia independiente y no tienes contexto previo. Revisa la tanda B de la entrega 3 de este repositorio. No edites nada: informa de los hallazgos ordenados por gravedad, con archivo y línea en cada uno.

Qué revisar: `git diff main...entrega-3b`. Son `app3_sistema_multiagente/04_errores_entre_agentes.py`, `05_procedencia.py` y `06_contexto_largo.py`, sus secciones en `app3_sistema_multiagente/README.md`, `app3_sistema_multiagente/servers/investigacion.py`, sus tests, `datos/generar_sinteticos.py`, `CONCEPTOS.md`, `docs/glosario.md`, `docs/hallazgos.md`, `docs/diseno-entrega-3.md`, `app3_sistema_multiagente/CLAUDE.md` y `NOTAS.md`.

Las reglas están en `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md` y `.claude/rules/`.

Comprueba lo siguiente:

1. **Guía.** Compara las cabeceras y las respuestas de las preguntas tipo examen con las Task Statements 5.3, 5.6, 5.4, 5.1 (K2, S4–S6), 2.2-S3 y 1.3-S2 de la Exam Guide (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio). Busca:
   - una cita de K/S que no corresponda a su viñeta;
   - texto copiado en vez de parafraseado;
   - mecanismos fuera del perímetro (`tests/perimetro_excluido.yaml`);
   - viñetas asignadas en `CONCEPTOS.md` que el módulo no ejercite de verdad, sobre todo 5.3-K3, 5.6-S3, 5.6-S5, 5.1-S6 y 5.4-K1.
   - En `06`, que `Explore` (TS 3.4) vaya como `USA` y no como viñeta de 5.4.
2. **Hechos frente a inferencias.** Cada cabecera debe separar los hechos de la guía de las inferencias propias. Señala cualquier observación de este repositorio que se presente como si lo dijera la guía, y cualquier adaptación (por ejemplo, 5.4 habla de explorar código y `06` explora fuentes) que no se diga.
3. **Cifras.** Las cabeceras, el README, `docs/hallazgos.md` y `NOTAS.md` tienen que coincidir. Las mediciones de antes y de después de la pasada de completar (variante `generico`, `silenciar` por código, tercer par, encabezados) son distintas: señala dónde se mezclan sin decirlo.
4. **Didáctica.** Revísala contra las reglas 1 a 5 de «Incorporación de quien llega de cero», en roadmap §13 (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`, en el repositorio de estudio):
   - El contexto no adelanta resultados.
   - Las predicciones se plantean por patrón, no por valor.
   - Los términos comunes se enlazan al glosario.
   - En las preguntas tipo examen, las cuatro opciones son plausibles, tienen longitud y registro parecidos, y la correcta no está siempre en la misma posición (mira también las de `07`–`09`).
   - Haz una lectura en frío: alguien que solo haya leído el README raíz y el módulo, ¿podría predecir?
5. **Código.**
   - Que los tests nunca llamen al modelo.
   - `max_budget_usd` en toda ejecución con modelo.
   - El aislamiento de los agentes (`harness/options.py`) y el `env` de subagentes de `app3/01`.
   - Errores de lógica en las medidas: `gap_noted`, `partial_delivered`, el comprobador de procedencia, `merged_figures`, `explanation_found`, `conflicts_presented` y la medida de hechos de `06`. Di cuáles son laxas y si el README lo advierte.
   - En `06`, el *manifest* y la reanudación: qué pasa con un *manifest* corrupto o de otra ejecución.
   - `silence_failures` en `servers/investigacion.py`: que solo actúe en la variante y que no cambie el formato `content`/`metadata` del servidor.
   - Los datos se generan solo desde `datos/generar_sinteticos.py`.
   - Regla «una vez»: un `INTRODUCE` por viñeta y su ☑ en `CONCEPTOS.md` (190/240).
6. **Notas `→ roadmap`** de `docs/hallazgos.md` (sección de la tanda B). ¿Le pasarían también a otra persona, con otra máquina y otra cuenta, o dependen de esta implementación?

Puedes ejecutar `uv run pytest -q`. No ejecutes nada que llame al modelo.
