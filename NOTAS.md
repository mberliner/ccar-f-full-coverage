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
- [x] Capa meta §4.1: `docs/estandares-*.md`, `.claude/rules/`, skill, comando, permisos y hooks; 27 viñetas de D3 con su `INTRODUCE` (2026-10-24)
- [ ] Verificación §11.5 de la capa meta en una sesión nueva (`/memory`, regla por ruta, skill con fork, hook que rechaza `datos/sinteticos/`)
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
- **Hooks de la sesión de construcción:**
  - Claude Code toma una instantánea de los hooks al arrancar: tras cambiarlos, revisar `/hooks` o abrir una sesión nueva.
  - El filtro de shell de `proteger_rutas.py` es heurístico. Bloquea cualquier comando que nombre `datos/sinteticos` o `.env` (salvo un `git` aislado) y no ve un script que escriba por dentro; esa vía la cubre `generar_sinteticos.py --check`.
  - Falso positivo conocido: un commit cuyo mensaje nombra esas rutas, o que llega por heredoc (`<<`), se bloquea. Se escribe el mensaje en un archivo y se usa `git commit -F <archivo>`.
  - En Windows, los scripts de hook necesitan forzar UTF-8 en stdin y stderr, o los motivos con tildes llegan corruptos.
- **Viñetas de D3 pendientes para `d3_claude_code/README.md`** (entrega 2): 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5 y las 9 de 3.5. Las otras 27 ya tienen su marcador en `CLAUDE.md`, `docs/` y `.claude/`.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: una variable vacía llega como definida. `credentials.py` las quita.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

- `TS 1.4-K1`: `harness/options.py`, `harness/recorder.py` (al introducir `app2/01`)
- `TS 1.3-S3`: `harness/recorder.py` (`app3/02`)
- `TS 1.2-K1`: `harness/recorder.py` (`app3/01`)

