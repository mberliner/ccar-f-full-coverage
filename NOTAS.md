# NOTAS

Scratchpad de sesión y notas de producto no evaluables. Las predicciones y respuestas fallidas van en [FALLOS.md](FALLOS.md).

Marcas para el roadmap (flujo en `docs/estandares-flujo.md`): `→ roadmap` pendiente de llevar; `✓ roadmap <fecha> §x` ya está allí y manda lo de allí.

## Hitos (roadmap §10)

El roadmap es una plantilla sin seguimiento: el avance vive aquí y el criterio de cada hito es su columna «Hecho cuando».

**Hito 0** (cerrado el 2026-10-24):

- [x] Esqueleto de directorios, `pyproject.toml` con SDK fijado, `NOTAS.md`, `FALLOS.md`
- [x] Aislamiento de las sesiones de construcción (comprobado con `/memory`, `/mcp` y `/plugin`, 2026-10-23)
- [x] `git init` y `uv sync`
- [x] `CONCEPTOS.md` con las 240 filas (solo identificadores y módulo, sin texto de la guía)
- [x] Test «una vez por viñeta» y test de perímetro
- [x] Arnés: `options.py`, `recorder.py`, `offline.py`, `credentials.py`, con sus tests sin modelo (2026-10-23)
- [x] `datos/generar_sinteticos.py`: usuarios, tickets (con etiquetas aparte) y artículos de KB, deterministas y con `--check`; los conjuntos de las entregas 2 y 3 se añaden con su módulo (2026-10-24)
- [x] Capa meta §4.1: `docs/estandares-*.md`, `.claude/rules/`, skill, comando, permisos y hooks; 27 viñetas de D3 con su `INTRODUCE` (2026-10-24)
- [x] Verificación §11.5 de la capa meta en una sesión nueva (2026-10-24):
  - `/memory` lista `CLAUDE.md` y sus dos `@import`.
  - La skill corre en fork, con argumento y sin él.
  - `datos/sinteticos/` queda protegido: la regla `deny` actúa en `Edit` y el hook en la shell.
  - Regla por ruta: `apps-comentarios.md` no se carga al leer un `.md` y sí al leer un `.py` de `app*/`, con línea `Loaded` y contenido en contexto; `tests.md` se carga al leer un test fuera de `app*/` (glob por tipo de archivo).
- [x] `ANTHROPIC_API_KEY` disponible desde `.env` (plantilla en `.env.example`); `credentials.py` la detecta. La validez de la clave y `apiKeySource` se confirman en la primera ejecución con modelo (2026-10-24)

**Entregas:**

- [ ] Entrega 1 · D1 (`S-4`): diseño aprobado en `docs/diseno-entrega-1.md` (2026-10-24)
- [ ] Entrega 2 · D2 y D3 (`S-3`)
- [ ] Entrega 3 · D4 y D5 (`S-2`)
- [ ] `S-1` · repaso sin código nuevo
- [ ] Entrega 4 · opcional, después del examen

## Sesiones

| App | Nombre de sesión | Estado |
| :--- | :--- | :--- |

## Notas de producto (no evaluables)

- **Plugins sincronizados desde claude.ai** (`<nombre>@synced`): ✓ roadmap 2026-10-24 §4.3.
- **Subagentes fork activos por defecto** en Claude Code (`CLAUDE_CODE_FORK_SUBAGENT`): candidato a neutralizar con `"0"` en `env` en los módulos de subagentes (roadmap §3, regla 4). El test de perímetro admite el valor apagado. → roadmap (§3, regla 4) cuando se decida en `app3/01`.
- **Cobertura 240/240:** `test_full_coverage` está en `xfail(strict=True)`; cuando pase, pytest lo marcará como XPASS fallido y hay que quitar la marca.
- **Conectores de claude.ai** (`ENABLE_CLAUDEAI_MCP_SERVERS=false` también en la sesión de construcción): ✓ roadmap 2026-10-24 §3, regla 3.
- **Skills sincronizadas de claude.ai** (`docx`, `pdf`, `deep-research`…): no se encontró ajuste para desactivarlas por proyecto; no afectan a las apps (`setting_sources=[]`).
- **`claudeMdExcludes` en Windows:** ✓ roadmap 2026-10-24 §4.3.
- **`skills=None` no apaga las skills** en `ClaudeAgentOptions` (SDK 0.2.173): las CLI defaults siguen aplicando. Pendiente: en la primera ejecución con modelo, mirar la línea `[contexto]` del recorder; si lista alguna skill, añadir `skills=[]` en `harness/options.py` (regla 4). → roadmap (§3, regla 3) cuando se confirme.
- **Una respuesta del modelo puede llegar en varios `AssistantMessage`** con el mismo `message_id`; el recorder agrupa por ese id. Confirmarlo en la primera ejecución de `app3/02`. → roadmap (§5, `recorder.py`) cuando se confirme.
- **Hooks de la sesión de construcción:**
  - Instantánea de hooks al arrancar, fallo en cerrado, dos barreras (`deny` y hook), falso positivo con `git commit -F` y UTF-8 en Windows: ✓ roadmap 2026-10-24 §4.3.
  - El filtro de shell de `proteger_rutas.py` es heurístico:
    - bloquea cualquier comando que nombre `datos/sinteticos` o un `.env`, salvo `git status|diff|log|show|add` sin nada encadenado (el salto de línea cuenta como separador);
    - no ve un script que escriba por dentro, ni variables o comodines que compongan la ruta. Esa vía la cubre `generar_sinteticos.py --check`.
  - **Variantes de `.env`:** protege `.env` y `.env.*`, salvo las plantillas `.env.example` y `.env.sample`, sin distinguir mayúsculas.
  - La regla `deny` se vio rechazar el `Edit` («directory that is denied by your permission settings») y el hook bloquear por shell (2026-10-24).
  - **Una instrucción en contexto puede tapar la prueba:** ✓ roadmap 2026-10-24 §11.5. Caso visto: al pedir «edita `datos/sinteticos/tickets.json`», la sesión fue directa al generador sin intentar el `Edit`.
- **`argument-hint` no obliga a pasar el argumento** (Claude Code 2.1.310). La guía lo presenta como el mecanismo para pedir el parámetro; en el producto, el hint solo se muestra en el autocompletado y la skill se lanza igual sin argumento. Por eso `verificar-concepto` comprueba `$ARGUMENTS` y se detiene si llega vacío. En el examen vale la lectura de la guía (registrado en `conceptos-generales.md` §4.6 del repositorio de estudio). Comprobado el 2026-10-24: el fork funciona y a la conversación principal solo llegó el resultado.
- **Varios directorios de configuración (`CLAUDE_CONFIG_DIR`)** y decisión de credencial (`apiKeyHelper` solo en la CLI, clave en `.env`): ✓ roadmap 2026-10-24 §4.3. Lo propio de esta implementación:
  - **Credencial:** las apps usan la clave empresarial cargada desde `.env`. Si la clave está exportada, el módulo la usa y el coste va a esa cuenta.
  - `app2/06` reanuda sesiones del directorio de configuración del proceso que lo ejecuta.
  - **`.env` y el hook:** `proteger_rutas.py` impide crear o editar `.env` desde la sesión de construcción; lo crea la persona copiando `.env.example`. `.gitignore` cubre solo `.env` (patrón exacto), no variantes.
  - **Pendiente:** `CLAUDE_CONFIG_DIR` para las apps. En la primera ejecución con modelo, ver qué directorio usa la CLI (sesiones de `app2/06`, login de respaldo) y, si hace falta fijarlo, ampliar `credentials.py` para copiar esa variable desde `.env`. → roadmap (§4.3) cuando se resuelva.
- **`/memory` no lista las reglas por ruta:** ✓ roadmap 2026-10-24 §11.5.
- **Viñetas de D3 pendientes para `d3_claude_code/README.md`** (entrega 2): 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5 y las 9 de 3.5. Las otras 27 ya tienen su marcador en `CLAUDE.md`, `docs/` y `.claude/`.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: ✓ roadmap 2026-10-24 §5 (`credentials.py`).
- **Los hooks se lanzan con `uv run`, no con `python`:** ✓ roadmap 2026-10-24 §4.3.
- **La configuración de usuario no se apaga desde el repositorio:** ✓ roadmap 2026-10-24 §3 (regla 3) y §4.3. Pendiente de comprobar: si `--setting-sources project,local` deja fuera también las reglas y el `CLAUDE.md` de usuario. → roadmap (§4.3) cuando se confirme.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

- `TS 1.4-K1`: `harness/options.py`, `harness/recorder.py` (al introducir `app2/01`)
- `TS 1.3-S3`: `harness/recorder.py` (`app3/02`)
- `TS 1.2-K1`: `harness/recorder.py` (`app3/01`)
