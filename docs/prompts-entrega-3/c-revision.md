Eres una instancia independiente y no tienes contexto previo. Revisa la tanda C de la entrega 3 de este repositorio. No edites nada: informa de los hallazgos ordenados por gravedad, con archivo y línea en cada uno.

Qué revisar: `git diff main...entrega-3c`. Son `app3_sistema_multiagente/10_confianza_y_revision.py`, `11_criterios_y_ci.py` y `12_revision_independiente.py`, sus secciones en `app3_sistema_multiagente/README.md`, `harness/headless.py`, `datos/generar_sinteticos.py`, sus tests, `CONCEPTOS.md`, `docs/glosario.md`, `docs/hallazgos.md` (sonda C1 y tanda C), `docs/tipos-de-senal.md`, `docs/diseno-entrega-3.md`, `app3_sistema_multiagente/CLAUDE.md` y `NOTAS.md`.

Las reglas están en `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md` y `.claude/rules/`.

Comprueba lo siguiente:

1. **Guía.** Compara las cabeceras y las respuestas de las preguntas tipo examen con las Task Statements 5.5 (`10`); 3.6, 4.1, 4.2-S2/S3 y 4.4-K3/S3 (`11`); 4.6, 1.6-K2/S2 y 3.6-K4 (`12`) de la Exam Guide (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio). Busca:
   - una cita de K/S que no corresponda a su viñeta;
   - texto copiado en vez de parafraseado;
   - mecanismos fuera del perímetro (`tests/perimetro_excluido.yaml`);
   - viñetas asignadas en `CONCEPTOS.md` que el módulo no ejercite de verdad, sobre todo 5.5-S3 y S4, 3.6-S3, S4 y S5, 4.1-S2, 4.4-S3, 4.6-K3 y 1.6-S2;
   - **respuestas de examen que sigan lo observado en vez de la guía.** Tres medidas contradicen o no respaldan la guía: la autorrevisión no encontró menos que la instancia nueva (4.6-K1/K2, 3.6-K4), los tests existentes en contexto no redujeron los duplicados (3.6-S4) y `conservador` no mostró señal estable (4.1-K2). En el examen manda la guía; lo observado va solo en el Paso 3 y con el rótulo `Producto observado (no evaluable)`.
2. **Hechos frente a inferencias.** Cada cabecera debe separar los hechos de la guía de las inferencias propias. Señala cualquier observación de este repositorio presentada como si la dijera la guía, y las adaptaciones que no se digan (por ejemplo, en `12` la sesión generadora copia un cambio dado en vez de diseñarlo).
3. **Cifras.** Cabeceras, README, `docs/hallazgos.md` y `NOTAS.md` tienen que coincidir. Las cifras de `11` están en «antes» y «después» del fallo F; la puntuación por símbolo no recalculó las anteriores; en `12` hay hallazgos sin confianza por falta de presupuesto; `autorrevision_explicita` no se midió. Señala dónde se mezclan sin decirlo o dónde se presenta una cifra que no existe.
4. **Didáctica.** Revísala contra las reglas 1 a 5 de «Incorporación de quien llega de cero», en roadmap §13 (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`, en el repositorio de estudio):
   - El contexto no adelanta resultados.
   - Las predicciones se plantean por patrón, no por valor.
   - Los términos comunes se enlazan al glosario.
   - En las preguntas tipo examen, las cuatro opciones son plausibles, tienen longitud y registro parecidos y la correcta no está siempre en la misma posición (mira también las de `01`–`09`). La multiple-response de `11` declara cuántas elegir, tiene al menos una opción de más y como máximo cuatro, y cada opción se juzga sola.
   - Haz una lectura en frío: alguien que solo haya leído el README raíz y el módulo, ¿podría predecir?
5. **Código.**
   - Que los tests nunca llamen al modelo.
   - `max_budget_usd` en toda ejecución con modelo, y en `claude -p` el tope por `--max-budget-usd`; que `harness/headless.py` imprima la orden entera antes de ejecutarla y no admita una ejecución sin tope.
   - El aislamiento de `claude -p` (fuentes de configuración, MCP estricto, `env`): que cargue el `CLAUDE.md` del `cwd` temporal y no la capa meta del repositorio. Si la sonda C1 dejó algo sin probar (el nivel de usuario), que el registro lo diga.
   - En `12`, que el coste de la sesión reanudada (acumulado) entre en el tope de su rama.
   - Errores de lógica en las medidas: calibración y muestreo estratificado (`10`), cola con cupo y `conflict_detected` a revisión, puntuación de hallazgos por línea y por símbolo (`11` y `12`), duplicados de escenarios y fusión de hallazgos entre pasadas. Para cada una: test con su falso positivo y su falso negativo, y si hay control positivo. Di cuáles son laxas y si el README lo advierte.
   - Cada `--anti` cambia una sola cosa respecto a la correcta.
   - Los datos se generan solo desde `datos/generar_sinteticos.py` y el generador es determinista.
   - Regla «una vez»: un `INTRODUCE` por viñeta y su ☑ en `CONCEPTOS.md` (225/240).
6. **Tipos de señal.** Las filas de `docs/tipos-de-senal.md` para `10`–`12` coinciden con lo que el README dice que se observó.
7. **Notas `→ roadmap`** de `docs/hallazgos.md` (sonda C1 y tanda C). ¿Le pasarían también a otra persona, con otra máquina y otra cuenta, o dependen de esta implementación?

Puedes ejecutar `uv run pytest -q`. No ejecutes nada que llame al modelo.
