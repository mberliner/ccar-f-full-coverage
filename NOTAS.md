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
- [x] `ANTHROPIC_API_KEY` disponible desde `.env` (plantilla en `.env.example`); `credentials.py` la detecta. Clave válida y `apiKeySource=ANTHROPIC_API_KEY` en la línea `[contexto]` de la primera ejecución con modelo (2026-10-24)

**Entregas:**

- [x] Entrega 1 · D1 (`S-4`): diseño aprobado en `docs/diseno-entrega-1.md` (2026-10-24). Construida en la rama `entrega-1` y fusionada a `main` (2026-10-24):
  - [x] Arnés: `config.py`, `cli.py`, `budget.py`, `data.py`; `skills=[]` por defecto en `options.py`; el recorder guarda `session_id` y el texto de cada resultado.
  - [x] 8 módulos con `INTRODUCE` y ☑: 49 viñetas, 76/240. `pytest` en verde y `generar_sinteticos.py --check` limpio.
  - [x] §11.1 observado: credencial, versiones, `[modelo]` y `[presupuesto]` con su origen.
  - [x] Señales con modelo: `app2/02` (500.01 denegado y escalado; fecha y estado normalizados), `app2/05` (sin case facts se pierde la fecha de compra), `app2/06` (sin aviso responde con datos viejos), `app3/01` (`estrecha` pierde la wifi; `simple` solo invoca `kb_analyst`), `app3/02` (3 `Agent` en `r1`, ×1,66 de latencia).
  - [x] **Señal de `app2/01`** (2026-10-24):
    - Con Haiku 5.5, 0 pagos sin verificar en 40 ejecuciones sin puerta, con cuatro mensajes distintos.
    - Con `claude-haiku-4-5` (el modelo más simple disponible para la clave, consultado con `models.list()`): sin puerta, 8 de 10 pagaron sin verificar; con puerta, 9 de 10 lo intentaron y 0 de 10 pagaron.
    - `app2/01` tiene su propio rol, `enforcement` (`CCARF_MODEL_ENFORCEMENT`, por defecto Haiku 4.5), en sus dos variantes; el resto de módulos sigue con Haiku 5.5. El ×10 de coste queda limitado a este módulo (cambio de diseño anotado en `docs/diseno-entrega-1.md`). Presupuesto propio `CCARF_BUDGET_ENFORCEMENT` (0,50 $): con 0,25 $ y `--repeat 10`, la variante con puerta usaba de media el 95 % del tope de cada repetición (máximo 106 %) y la variante anti, el 54 %.
  - [x] Prioridad de `.env` con el `.env` real (diseño, verificación 4; 2026-10-24): con las cinco `CCARF_*` en `.env` y otros valores exportados en la shell, todas las líneas dicen `origen=.env`. Con `CCARF_MODEL_AGENT` falso exportado, `app1/01` (Messages API) y `app2/02` (Agent SDK) se ejecutaron con `claude-haiku-5-5`. `--budget 5` no sube el tope y `--budget 0.05` lo baja.
  - [x] Revisión por una instancia independiente (subagente sin el contexto de la sesión que escribió el código, 2026-10-24): 21 hallazgos, ninguno de gravedad alta, todos aplicados. Los principales: el conteo de pagos ejecutados de `app2/01` sale ahora del estado de la puerta; el hook de umbral falla en cerrado; presupuestos repartidos; y la señal de dependencia escondida, que antes daba falsos positivos.
  - [x] Merge a `main` (2026-10-24).
  - **Criterio de presupuesto** (decidido en la revisión): `CCARF_BUDGET_*` es el tope de **toda la ejecución del script**. Se reparte entre `--repeat`, configuraciones, turnos o ramas; el diseño decía «por ejecución» sin precisarlo.
  - **`resume` y `fork_session` arrastran el coste de la sesión base** (posible, 2026-10-24): un fork sin llamadas costó más que la base. `app2/06` da a cada rama reanudada el coste de la base más su parte. Pendiente: confirmarlo con una base cara.
- [ ] Entrega 2 · D2 y D3 (`S-3`)
- [ ] Entrega 3 · D4 y D5 (`S-2`)
- [ ] `S-1` · repaso sin código nuevo
- [ ] Entrega 4 · opcional, después del examen

## Sesiones

| App | Nombre de sesión | Estado |
| :--- | :--- | :--- |
| app1 | `app1` | módulo 01 hecho (entrega 1) |
| app2 | `app2` | módulos 01, 02, 03, 05 y 06 hechos (entrega 1); práctica de `--resume app2` pendiente (README de app2, módulo 06) |
| app3 | `app3` | módulos 01 y 02 hechos (entrega 1) |

## Notas de producto (no evaluables)

- **Plugins sincronizados desde claude.ai** (`<nombre>@synced`): ✓ roadmap 2026-10-24 §4.3.
- **Subagentes fork activos por defecto** (`CLAUDE_CODE_FORK_SUBAGENT="0"` en los módulos con subagentes): ✓ roadmap 2026-10-24 §3, regla 4.
- **Subagentes en segundo plano aunque `background=False`** (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`): ✓ roadmap 2026-10-24 §3, regla 4. Lo propio de esta implementación: sin la variable, `query()` emitía varios `ResultMessage`; con ella, un solo `[fin]` y resultado «Subagent hand-back».
- **`tools=[]` quita también la tool `Agent`:** ✓ roadmap 2026-10-24 §4.3.
- **`disallowed_tools` con una tool MCP no la quita:** ✓ roadmap 2026-10-24 §4.3 y §7 (`app2/03`).
- **La denegación de un subagente no aparece en `permission_denials`** del padre: ✓ roadmap 2026-10-24 §4.3.
- **Un modelo reciente puede no mostrar la tasa de fallo del prompt** (`app2/01`): ✓ roadmap 2026-10-24 §4.3, §7 y §13. Lo propio de esta implementación: rol `enforcement` y presupuesto `CCARF_BUDGET_ENFORCEMENT` en `harness/config.py`.
- **El corte de `max_budget_usd` lanza `ResultError`:** ✓ roadmap 2026-10-24 §4.3 y §5 (`recorder.py`).
- **Tope por ejecución del script**, repartido entre repeticiones, configuraciones, turnos o ramas: ✓ roadmap 2026-10-24 §3, regla 7.
- **Cobertura 240/240:** `test_full_coverage` está en `xfail(strict=True)`; cuando pase, pytest lo marcará como XPASS fallido y hay que quitar la marca.
- **Conectores de claude.ai** (`ENABLE_CLAUDEAI_MCP_SERVERS=false` también en la sesión de construcción): ✓ roadmap 2026-10-24 §3, regla 3.
- **Skills sincronizadas de claude.ai** (`docx`, `pdf`, `deep-research`…): no se encontró ajuste para desactivarlas por proyecto; no afectan a las apps (`setting_sources=[]`). Origen de las 18 skills de `[contexto]`: ✓ roadmap 2026-10-24 §4.3 (vienen de la CLI; con `CLAUDE_CONFIG_DIR` vacío salen las mismas).
- **`claudeMdExcludes` en Windows:** ✓ roadmap 2026-10-24 §4.3.
- **`skills=None` no apaga las skills** (`skills=[]` por defecto y `setting_sources=None` rechazado): ✓ roadmap 2026-10-24 §3, regla 3, y §5; comprobado que el modelo no ve las skills con `skills=[]`: ✓ roadmap 2026-10-24 §3, regla 3. Lo propio de esta implementación: la primera ejecución con modelo listó 18 skills en `[contexto]`, y la sonda (Haiku 5.5, ~0,004 $) recibió `Skill simplify is not in this session's skills allowlist`.
- **Plugins en la línea `[contexto]` con `setting_sources=[]`** (2026-10-24): ✓ roadmap 2026-10-24 §4.3 (origen `@builtin`, no de la cuenta). Pendiente de comprobar: si aportan hooks o tools a los agentes de las apps; la lista de tools de la sonda (24) solo muestra tools de la CLI. → roadmap (§4.3) cuando se confirme.
- **Una respuesta del modelo puede llegar en varios `AssistantMessage`** con el mismo `message_id`: ✓ roadmap 2026-10-24 §5 (`recorder.py`). Lo propio de esta implementación: `RunRecord.messages_per_response` y `partidas=` en `[fin]`. En `app3/02 --parte paralelo`, `r1` llegó en 3 mensajes con las 3 llamadas `Agent`, y en modo secuencial también en 3 con una sola llamada. Pendiente: por qué son 3 (¿razonamiento o texto en mensajes aparte?); no se ha mirado.
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
  - **`CLAUDE_CONFIG_DIR` para las apps:** en `app2/06` (2026-10-24), `resume` y `fork_session` funcionaron con el directorio de configuración del proceso que ejecuta el módulo, sin fijarlo. Con la clave en `.env` no hace falta login de respaldo. No se amplía `credentials.py`. Se queda aquí: depende del directorio de configuración de cada persona.
- **`/memory` no lista las reglas por ruta:** ✓ roadmap 2026-10-24 §11.5.
- **Viñetas de D3 pendientes para `d3_claude_code/README.md`** (entrega 2): 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5 y las 9 de 3.5. Las otras 27 ya tienen su marcador en `CLAUDE.md`, `docs/` y `.claude/`.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: ✓ roadmap 2026-10-24 §5 (`credentials.py`).
- **Los hooks se lanzan con `uv run`, no con `python`:** ✓ roadmap 2026-10-24 §4.3.
- **La configuración de usuario no se apaga desde el repositorio:** ✓ roadmap 2026-10-24 §3 (regla 3) y §4.3. Pendiente de comprobar: si `--setting-sources project,local` deja fuera también las reglas y el `CLAUDE.md` de usuario. → roadmap (§4.3) cuando se confirme.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

Todas convertidas en la entrega 1 (2026-10-24): `TS 1.4-K1` en `harness/options.py` y `harness/recorder.py`; `TS 1.2-K1` y `TS 1.3-S3` en `harness/recorder.py`.
