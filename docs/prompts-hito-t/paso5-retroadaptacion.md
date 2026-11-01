Trabajas en la raíz de este repositorio. Lee `CLAUDE.md`, `docs/estandares-*.md`, `docs/glosario.md` y la regla 5 y las reglas 1–4 de «Incorporación de quien llega de cero» (§13 del roadmap en `claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md` (repositorio de estudio)). No hagas commit.

TANDA: <app1/02–06 | app2/01–07 | app3/01–03> (una por ejecución).

Para cada módulo de la tanda, en su `app*/README.md`:
- Añade, al abrir la sección, «Antes de empezar» con el contexto propio del módulo: qué hace su sistema, qué hace cada tool que usa, qué cambia en cada variante `--anti`. Los términos transversales se enlazan a `docs/glosario.md`, no se repiten; amplía solo con términos propios.
- Reescribe «Predice» para pedir patrones, rangos o invariantes, no valores que el modelo pueda variar.
- El contexto explica qué hace el código, nunca qué pasa al ejecutarlo.
RESTRICCIONES: no cambies ninguna cifra medida, tabla de resultados ni lógica; no toques código ni tests; mantén «Pregunta tipo examen». Si una predicción depende de un valor que no puedes reformular sin tocar lo medido, déjala y lístala al final.
Termina con `uv run pytest -q` en verde y `git diff --stat`. Informa de lo que dejaste sin tocar.
