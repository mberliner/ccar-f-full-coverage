# NOTAS

Scratchpad de sesión y notas de producto no evaluables. Las predicciones y respuestas fallidas van en [FALLOS.md](FALLOS.md).

## Hito 0 (roadmap §10)

- [x] Esqueleto de directorios, `pyproject.toml` con SDK fijado, `NOTAS.md`, `FALLOS.md`
- [x] Aislamiento de las sesiones de construcción (comprobado con `/memory`, `/mcp` y `/plugin`, 2026-10-23)
- [x] `git init` y `uv sync`
- [x] `CONCEPTOS.md` con las 240 filas (solo identificadores y módulo, sin texto de la guía)
- [x] Test «una vez por viñeta» y test de perímetro
- [x] Arnés: `options.py`, `recorder.py`, `offline.py`, `credentials.py`, con sus tests sin modelo (2026-10-23)
- [x] `datos/generar_sinteticos.py`: usuarios, tickets (con etiquetas aparte) y artículos de KB, deterministas y con `--check`; los conjuntos de las entregas 2 y 3 se añaden con su módulo (2026-10-24)
- [ ] Capa meta §4.1: `docs/estandares-*.md`, `.claude/rules/`, skill, comando, permisos y hooks
- [ ] `ANTHROPIC_API_KEY` disponible (necesaria a partir de la entrega 1)

## Sesiones

| App | Nombre de sesión | Estado |
| :--- | :--- | :--- |

## Notas de producto (no evaluables)

- **Plugins sincronizados desde claude.ai:** en `enabledPlugins` se identifican como `<nombre>@synced`; la clave `<nombre>@<marketplace>` no tiene efecto (Claude Code 2.1.310).
- **Subagentes fork activos por defecto** en Claude Code (`CLAUDE_CODE_FORK_SUBAGENT`): candidato a neutralizar con `"0"` en `env` en los módulos de subagentes (roadmap §3, regla 4). El test de perímetro admite el valor apagado.
- **Cobertura 240/240:** `test_full_coverage` está en `xfail(strict=True)`; cuando pase, pytest lo marcará como XPASS fallido y hay que quitar la marca.
- **Conectores de claude.ai:** `ENABLE_CLAUDEAI_MCP_SERVERS=false` en el `env` de `.claude/settings.json` los quita también de la sesión de Claude Code, no solo de los agentes del SDK.
- **Skills sincronizadas de claude.ai** (`docx`, `pdf`, `deep-research`…): no se encontró ajuste para desactivarlas por proyecto; no afectan a las apps (`setting_sources=[]`).
- **`claudeMdExcludes`:** el patrón `**/<ruta>/CLAUDE.md` con barras normales funciona en Windows.
- **`skills=None` no apaga las skills** en `ClaudeAgentOptions` (SDK 0.2.173): las CLI defaults siguen aplicando. Pendiente: en la primera ejecución con modelo, mirar la línea `[contexto]` del recorder; si lista alguna skill, añadir `skills=[]` en `harness/options.py` (regla 4).
- **Una respuesta del modelo puede llegar en varios `AssistantMessage`** con el mismo `message_id`; el recorder agrupa por ese id. Confirmarlo en la primera ejecución de `app3/02`.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: una variable vacía llega como definida. `credentials.py` las quita.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

- `TS 1.4-K1`: `harness/options.py`, `harness/recorder.py` (al introducir `app2/01`)
- `TS 1.3-S3`: `harness/recorder.py` (`app3/02`)
- `TS 1.2-K1`: `harness/recorder.py` (`app3/01`)

