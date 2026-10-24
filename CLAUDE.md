# ccar-f-full-coverage

Apps agénticas de demostración para practicar todas las viñetas del examen CCAR-F. El diseño completo vive en el roadmap del repositorio de estudio (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`).

## Contexto heredado

Los `CLAUDE.md` de directorios padre no aplican aquí y contaminarían las pruebas. Se excluyen con `claudeMdExcludes` en `.claude/settings.local.json`, que no se versiona porque el patrón depende de la ubicación de cada persona. Se crea copiando `.claude/settings.local.example.json`: un patrón por cada `CLAUDE.md` padre que aparezca en `/memory`, y en `enabledPlugins` los plugins de la cuenta propia que deban apagarse aquí (o la clave vacía). Comprobar con `/memory` y `/plugin`; si alguno vuelve a aparecer en contexto, se ignora y se corrige el patrón.

## Reglas del proyecto

- Comentarios en español e identificadores en inglés.
- **Perímetro de la guía:** solo los mecanismos que nombra la Exam Guide v1.0. `claude-agent-sdk` queda fijado en `pyproject.toml` y solo se actualiza de forma deliberada.
- **Aislamiento de los agentes de las apps:** `setting_sources=[]`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` y `ENABLE_CLAUDEAI_MCP_SERVERS=false` (lo aplica `harness/options.py`).
- **Regla «una vez»:** cada viñeta tiene un único `# INTRODUCE: TS x.y-Kn/Sn`; después solo `# USA`.
- Datos siempre sintéticos. No se copia texto de la guía oficial ni preguntas reales del examen.
- Coste acotado: `max_budget_usd` en toda ejecución con modelo.
- `CLAUDE.md` solo lleva contexto y reglas estables. El avance de los hitos y el *scratchpad* de sesión van en `NOTAS.md`; las predicciones y respuestas fallidas, en `FALLOS.md`.
