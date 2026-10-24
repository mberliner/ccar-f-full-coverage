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
- [x] Verificación §11.5 de la capa meta en una sesión nueva (2026-10-24):
  - `/memory` lista `CLAUDE.md` y sus dos `@import`.
  - La skill corre en fork, con argumento y sin él.
  - `datos/sinteticos/` queda protegido: la regla `deny` actúa en `Edit` y el hook en la shell.
  - Regla por ruta: `apps-comentarios.md` no se carga al leer un `.md` y sí al leer un `.py` de `app*/`, con línea `Loaded` y contenido en contexto; `tests.md` se carga al leer un test fuera de `app*/` (glob por tipo de archivo).
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
  - El filtro de shell de `proteger_rutas.py` es heurístico:
    - bloquea cualquier comando que nombre `datos/sinteticos` o un `.env`, salvo `git status|diff|log|show|add` sin nada encadenado (el salto de línea cuenta como separador);
    - no ve un script que escriba por dentro, ni variables o comodines que compongan la ruta. Esa vía la cubre `generar_sinteticos.py --check`.
  - **El hook falla en cerrado:** ante una entrada que no entiende devuelve 2, porque un exit 1 es no bloqueante y la llamada seguiría.
  - **Variantes de `.env`:** protege `.env` y `.env.*`, salvo las plantillas `.env.example` y `.env.sample`, sin distinguir mayúsculas.
  - **Dos barreras para `Edit`/`Write`:** la regla `deny` de `settings.json` rechaza el `Edit` antes que el hook («directory that is denied by your permission settings»), así que el hook queda de respaldo; por shell, el hook es la única barrera y sí se vio bloquear (2026-10-24).
  - **Una instrucción en contexto puede tapar la prueba:** al pedir «edita `datos/sinteticos/tickets.json`», la sesión leyó los estándares y fue directa al generador sin intentar el `Edit`, así que el hook no llegó a ejecutarse. Para probar una barrera hay que forzar el intento. En el examen, la instrucción no garantiza el cumplimiento; solo la puerta programática lo hace.
  - Falso positivo conocido: un commit cuyo mensaje nombra esas rutas, o que llega por heredoc (`<<`), se bloquea. Se escribe el mensaje en un archivo y se usa `git commit -F <archivo>`.
  - En Windows, los scripts de hook necesitan forzar UTF-8 en stdin y stderr, o los motivos con tildes llegan corruptos.
- **`argument-hint` no obliga a pasar el argumento** (Claude Code 2.1.310). La guía lo presenta como el mecanismo para pedir el parámetro; en el producto, el hint solo se muestra en el autocompletado y la skill se lanza igual sin argumento. Por eso `verificar-concepto` comprueba `$ARGUMENTS` y se detiene si llega vacío. En el examen vale la lectura de la guía (registrado en `conceptos-generales.md` §4.6 del repositorio de estudio). Comprobado el 2026-10-24: el fork funciona y a la conversación principal solo llegó el resultado.
- **Varios directorios de configuración (`CLAUDE_CONFIG_DIR`):** todo lo del repositorio funciona igual con cualquiera (`CLAUDE.md`, reglas, skill, comando, hooks, permisos, `settings.local.json`). Cambia lo que vive en el directorio de configuración:
  - **Credencial:** con `apiKeyHelper` en los ajustes de usuario, la clave no está en el entorno. Un módulo lanzado desde esa sesión no la hereda, y el Agent SDK con `setting_sources=[]` previsiblemente tampoco aplica el *helper*; comprobarlo en la primera ejecución con modelo. Si la clave está exportada, el módulo la usa y el coste va a esa cuenta.
  - **Memoria automática, sesiones con nombre e historial:** son propios de cada directorio. `--resume <app>` no encuentra una sesión creada con otro, y `app2/06` reanuda sesiones del directorio del proceso que lo ejecuta.
  - **Plugins, conectores y ajustes gestionados:** dependen de la cuenta. Repetir `/plugin`, `/mcp` y `/hooks` la primera vez que se construya con otro directorio. Unos ajustes gestionados podrían desactivar los hooks del proyecto.
  - **Pendiente:** decidir con qué credencial se ejecutan las apps desde la entrega 1.
- **`/memory` no lista las reglas por ruta:** muestra ubicaciones de `CLAUDE.md` y memoria, aunque no existan. Una regla con `paths` se carga al usar `Read`, `Write` o `Edit` sobre un archivo que coincide, y aparece una línea `Loaded` en el terminal. `/context` muestra lo cargado al arrancar.
- **Viñetas de D3 pendientes para `d3_claude_code/README.md`** (entrega 2): 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5 y las 9 de 3.5. Las otras 27 ya tienen su marcador en `CLAUDE.md`, `docs/` y `.claude/`.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: una variable vacía llega como definida. `credentials.py` las quita.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

- `TS 1.4-K1`: `harness/options.py`, `harness/recorder.py` (al introducir `app2/01`)
- `TS 1.3-S3`: `harness/recorder.py` (`app3/02`)
- `TS 1.2-K1`: `harness/recorder.py` (`app3/01`)

