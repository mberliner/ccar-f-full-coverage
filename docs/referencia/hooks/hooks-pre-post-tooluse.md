# Hooks `PreToolUse` y `PostToolUse`: ayuda rápida

> Documento portable junto con su complemento [`hooks-escenarios-codigo.md`](hooks-escenarios-codigo.md) (escenarios con código y hooks de prueba): se copian juntos y los únicos enlaces son entre ambos. Tema: TS 1.5 de CCAR-F («Apply Agent SDK hooks for tool call interception and data normalization»).
> Fecha: `2026-11-15`. Verificado contra la Exam Guide v1.0 y la documentación oficial el `2026-11-15`, salvo lo marcado como **[sin verificar]**. Los comportamientos que se podían ejecutar se probaron además con modelo: [resultados](hooks-escenarios-codigo.md#verificación-con-modelo-resultados-observados).

## 1. Lo que evalúa el examen

- **`PostToolUse` intercepta el resultado** antes de que el modelo lo procese. Caso de la guía: normalizar formatos heterogéneos que devuelven distintas tools MCP (timestamps Unix frente a ISO 8601, códigos de estado numéricos). Código: [E2](hooks-escenarios-codigo.md#e2-normalizar-datos-heterogéneos-de-herramientas-mcp).
- **Un hook intercepta la llamada saliente** para aplicar una regla de negocio. Caso de la guía: bloquear un reembolso de más de 500 $ y **redirigir** a un flujo alternativo (escalado a un humano). Código: [E1](hooks-escenarios-codigo.md#e1-bloquear-reembolsos-grandes-y-redirigir-a-un-humano).
- **Hook frente a prompt:** el hook da una garantía determinista; la instrucción en el prompt da un cumplimiento probabilístico. Si la regla debe cumplirse siempre, va en un hook. Contraste con código en [E1](hooks-escenarios-codigo.md#e1-bloquear-reembolsos-grandes-y-redirigir-a-un-humano).
- **Regla de oro:** `Pre` = ¿dejo pasar la llamada? · `Post` = ¿qué ve el modelo?

Todo lo que sigue es **`EN PRODUCCIÓN (no evaluable)`**: los campos y el comportamiento concretos del SDK. Sirve para implementar, y nunca decide la respuesta de una pregunta tipo examen. Cada fila, regla y trampa enlaza al escenario con código que la ejecuta ([índice completo](hooks-escenarios-codigo.md#qué-escenario-cubre-cada-caso-de-la-ayuda)).

## 2. Tabla maestra

| | **PreToolUse** | **PostToolUse** |
|---|---|---|
| Cuándo dispara | Antes de ejecutar la herramienta | Cuando la herramienta termina con éxito, antes de que el modelo vea el resultado |
| Input ([JSON completo](hooks-escenarios-codigo.md#anatomía-de-una-llamada-qué-recibe-y-qué-devuelve-un-hook)) | `tool_name`, `tool_input`, `tool_use_id` | Lo mismo, más `tool_response` (el resultado) y `duration_ms` |
| Bloquear | `hookSpecificOutput.permissionDecision: "deny"` ([E1](hooks-escenarios-codigo.md#e1-bloquear-reembolsos-grandes-y-redirigir-a-un-humano)) | **No puede**: la herramienta ya corrió. El `decision: "block"` de nivel superior solo añade `reason` junto al resultado, y **Claude sigue viendo la salida original** ([P4](hooks-escenarios-codigo.md#p4-decision-block-en-posttooluse-es-feedback-no-bloqueo)) |
| Reescribir | `updatedInput`: reemplaza el input **entero** ([P1](hooks-escenarios-codigo.md#p1-reescribir-argumentos-con-updatedinput)) | `updatedToolOutput`: reemplaza la salida (nativas y MCP). Debe tener la forma de la salida de la herramienta ([E2](hooks-escenarios-codigo.md#e2-normalizar-datos-heterogéneos-de-herramientas-mcp)) |
| Añadir contexto | `additionalContext` (ignorado con `defer`) | `additionalContext` ([P3](hooks-escenarios-codigo.md#p3-additionalcontext-tras-una-consulta)) |
| Si el callback falla | La llamada sigue el flujo normal de permisos; con `onFailure: "block"`, se bloquea ([P6](hooks-escenarios-codigo.md#p6-un-guard-que-falla-en-cerrado)) | Se conserva el resultado; con `onFailure: "block"`, Claude recibe el fallo como feedback |
| Timeout | Callback del SDK: **bloquea** la llamada. Hook de comando: **no** bloquea (sigue el flujo de permisos), salvo `onFailure: "block"` | Se conserva el resultado y el turno continúa |
| Exit `2` (hook de shell) | Bloquea la llamada ([S1](hooks-escenarios-codigo.md#s1-hooks-de-comando-el-código-de-salida-decide)) | Solo muestra el *stderr* a Claude |

- Todos los campos de decisión van dentro de `hookSpecificOutput`, con `hookEventName`. La excepción es el `decision`/`reason` de `PostToolUse`, que va en el nivel superior.
- `updatedMCPToolOutput` es el campo antiguo y solo sirve para MCP; `updatedToolOutput` lo sustituye.
- `updatedToolOutput` solo cambia lo que ve Claude: no deshace los efectos ya producidos, y la telemetría registra la salida original. En herramientas nativas, un valor que no encaja con su esquema se ignora; en MCP no se valida.
- `PostToolUseFailure` no puede reescribir: la salida de una llamada fallida llega a Claude tal cual.
- `return {}` = no opinar. Un callback que no devuelve nada cuenta como **fallo**.

## 3. `permissionDecision` (solo `PreToolUse`)

| Valor | Efecto |
|---|---|
| `allow` | Salta la confirmación, con `updatedInput` incluido. **Las reglas `deny`/`ask` de settings se evalúan igual.** |
| `deny` | Bloquea; `permissionDecisionReason` se lo explica a Claude |
| `ask` | Pide confirmación al usuario; el `reason` se muestra en esa confirmación |
| `defer` | Termina el turno con `stop_reason: "tool_deferred"` para reanudar después (en el CLI, solo en modo `-p`). **Descarta `updatedInput` y `additionalContext`** |

- **Precedencia entre hooks:** `deny` > `defer` > `ask` > `allow` (gana la más restrictiva). Código: [P2](hooks-escenarios-codigo.md#p2-allow-ask-defer-y-precedencia-entre-hooks).
- **Sin `permissionDecision`:** el `updatedInput` se aplica igual y sigue la evaluación normal de permisos.

## 4. Matchers y registro

- **Literal o regex:** si el matcher solo tiene letras, dígitos, `_`, `-`, espacio, `,` o `|`, es un nombre exacto o una lista (`"Write|Edit"`). Con cualquier otro carácter es una regex JS **sin anclar**: `Edit.*` también captura `NotebookEdit`, y `^Edit$` fija la coincidencia exacta.
- `"*"`, `""` o sin matcher: todas las herramientas. Las MCP se llaman `mcp__<servidor>__<acción>` (con `"^mcp__"` se capturan todas).
- Solo filtran por **nombre**. Para filtrar por ruta u otro argumento, mirar `tool_input` dentro del hook ([P5](hooks-escenarios-codigo.md#p5-filtrar-por-ruta-dentro-del-hook-y-la-vía-bash)).
- **Agent SDK:** `hooks={"PreToolUse": [HookMatcher(matcher=..., hooks=[cb])]}` (Python) o `{ PreToolUse: [{ matcher, hooks: [cb] }] }` (TypeScript). El callback recibe `(input_data, tool_use_id, context)`, y `tool_use_id` correlaciona el `Pre` y el `Post` de una misma llamada. Llamada completa con `query()` y su traza real: [Cómo se conecta](hooks-escenarios-codigo.md#cómo-se-conecta-de-las-opciones-a-una-llamada-con-query).
- **Opciones de `HookMatcher`:** `timeout` en segundos (600 s por defecto en la mayoría de eventos) y `onFailure: "block"` (`on_failure` en Python).
- **Settings** (`.claude/settings.json`): `{"hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "..."}]}]}}` (ejemplo funcional en [S1](hooks-escenarios-codigo.md#s1-hooks-de-comando-el-código-de-salida-decide)). El SDK los carga con las opciones por defecto, salvo que `settingSources`/`setting_sources` excluya esa fuente.

## 5. Varios hooks, async y códigos de salida

- **Varios hooks en el mismo evento:** corren **en paralelo** y terminan en orden no determinista. Cada uno ve el input o el resultado **original**: no se encadenan. Los `additionalContext` de todos llegan a Claude.
- **Combinar reescrituras** (p. ej. truncar y normalizar timestamps): un **único** hook que haga ambas en secuencia ([E2](hooks-escenarios-codigo.md#e2-normalizar-datos-heterogéneos-de-herramientas-mcp)). Qué pasa si dos hooks reescriben lo mismo no está documentado. `Producto observado (no evaluable)` (Claude Code 2.1.325, dos hooks de comando sobre `Bash`, retardos cruzados): ambos recibieron el resultado original y el modelo vio solo la reescritura del que **terminó último**, sin importar el orden de registro; no se componen.
- **Async:** `{"async": true}` (`async_` en Python), con un `asyncTimeout` opcional. El agente no espera, así que el hook no puede bloquear, modificar ni añadir contexto: solo vale para logs y métricas ([P7](hooks-escenarios-codigo.md#p7-auditoría-asíncrona)).
- **Exit codes (hooks de shell):** `0` aplica el JSON que imprima el hook · `2` bloquea en los eventos que admiten bloqueo, y un JSON no puede anularlo · **cualquier otro código, incluido el `1`, es un error no bloqueante**. Para imponer una regla, `exit 2` ([S1](hooks-escenarios-codigo.md#s1-hooks-de-comando-el-código-de-salida-decide)).

## 6. Trampas

- `permissionDecision` en `PostToolUse`: no tiene efecto.
- Usar `decision: "block"` en `Post` creyendo que oculta el resultado: Claude lo sigue viendo. Para ocultarlo o sustituirlo, `updatedToolOutput` ([P4](hooks-escenarios-codigo.md#p4-decision-block-en-posttooluse-es-feedback-no-bloqueo), [E2](hooks-escenarios-codigo.md#e2-normalizar-datos-heterogéneos-de-herramientas-mcp)).
- `updatedInput` o `updatedToolOutput` parciales: `updatedInput` reemplaza el objeto entero, y una salida que no encaja con el esquema se ignora ([P1](hooks-escenarios-codigo.md#p1-reescribir-argumentos-con-updatedinput)).
- `updatedInput` fuera de `hookSpecificOutput` o junto a `defer`: no se aplica ([P2](hooks-escenarios-codigo.md#p2-allow-ask-defer-y-precedencia-entre-hooks)).
- Pensar que `allow` se salta una regla `deny` de settings, o que gana a un `deny` de otro hook ([P2](hooks-escenarios-codigo.md#p2-allow-ask-defer-y-precedencia-entre-hooks)).
- Un *guard* que atrapa su propio error y devuelve `{}`: no cuenta como fallo, y la llamada pasa ([P6](hooks-escenarios-codigo.md#p6-un-guard-que-falla-en-cerrado)).
- Un matcher `Write|Edit` no intercepta una escritura hecha con `Bash` ([P5](hooks-escenarios-codigo.md#p5-filtrar-por-ruta-dentro-del-hook-y-la-vía-bash)).
- `exit 1` en un hook de comando no bloquea: hay que usar `exit 2` ([S1](hooks-escenarios-codigo.md#s1-hooks-de-comando-el-código-de-salida-decide)).
- Suponer encadenamiento por orden de registro o alfabético: no existe.
- Los hooks pueden no ejecutarse si la sesión termina por `max_turns`.

## 7. Mecanismos hermanos

| Necesidad | Mecanismo |
|---|---|
| Regla que debe cumplirse al 100 % | **Hook**, no prompt |
| Reaccionar al fallo de una herramienta | `PostToolUseFailure` |
| Una vez por lote de llamadas, antes de la siguiente llamada al modelo | `PostToolBatch` (solo TypeScript; `exit 2` detiene el bucle) |
| Decisión de permisos personalizada | `PermissionRequest` o el callback `canUseTool` |
| Reglas declarativas de permitir, preguntar o denegar | Reglas y modos de permisos (`settings.json`) |
| Verificación al terminar | Hook `Stop` |
| Orientación blanda por tipo de archivo | `.claude/rules/` (guía, **no** garantía) |

## Fuentes

- Escenarios con código y hooks de prueba ejecutables: [`hooks-escenarios-codigo.md`](hooks-escenarios-codigo.md).
- Exam Guide v1.0, Task Statement 1.5 (y 1.4 sobre *enforcement* programático frente a prompt).
- Agent SDK, hooks: <https://code.claude.com/docs/en/agent-sdk/hooks>
- Referencia de hooks de Claude Code (decision control, exit codes, matchers, `PostToolUse`): <https://code.claude.com/docs/en/hooks>
- Complementaria, no oficial: <https://agentpatterns.ai/tool-engineering/posttooluse-output-replacement/>
