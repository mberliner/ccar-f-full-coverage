# Hooks `PreToolUse` y `PostToolUse`: escenarios con código

> Complemento de [`hooks-pre-post-tooluse.md`](hooks-pre-post-tooluse.md) (la ayuda rápida; cada escenario enlaza a su sección y esa ayuda enlaza aquí). Tema: TS 1.5 de CCAR-F.
> Fecha: `2026-11-15`. Código ejecutado contra `claude-agent-sdk` 0.2.173 (la versión que fija el proyecto) y verificado contra la documentación oficial el `2026-11-15`.
> **Son hooks de prueba, no hooks reales:** viven junto a este documento y nada los carga (ni `.claude/settings.json` ni `.claude/hooks/`). Las herramientas `mcp__billing__*` y `mcp__crm__*` son inventadas.

## Archivos y cómo probarlos

| Archivo | Qué es |
|---|---|
| [`hooks_escenarios.py`](hooks_escenarios.py) | Un callback del Agent SDK por escenario, `build_options()` que los registra, un servidor MCP de prueba, una autocomprobación sin modelo y una demo con `query()` (`--demo`) |
| [`hooks_escenarios_shell.py`](hooks_escenarios_shell.py) | Hook de comando (shell) para S1, con cuatro modos |
| [`hooks_escenarios_settings.json`](hooks_escenarios_settings.json) | Cómo se registraría S1 en `settings.json`; no se carga solo |

```bash
uv run python docs/referencia/hooks/hooks_escenarios.py     # sin modelo: llama a cada hook con entradas sintéticas
uv run python docs/referencia/hooks/hooks_escenarios.py --demo "<prompt>"   # con modelo: ver «Cómo se conecta»
```

## Qué escenario cubre cada caso de la ayuda

| Escenario | Evento | Carril | Caso de la ayuda rápida |
|---|---|---|---|
| [E1](#e1-bloquear-reembolsos-grandes-y-redirigir-a-un-humano) Reembolso de más de 500 $ | `PreToolUse` | Examen (TS 1.5) | [§1 llamada saliente y hook frente a prompt](hooks-pre-post-tooluse.md#1-lo-que-evalúa-el-examen) |
| [E2](#e2-normalizar-datos-heterogéneos-de-herramientas-mcp) Timestamps y estados MCP | `PostToolUse` | Examen (TS 1.5) | [§1 normalizar resultados](hooks-pre-post-tooluse.md#1-lo-que-evalúa-el-examen) y [§5 combinar reescrituras](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida) |
| [P1](#p1-reescribir-argumentos-con-updatedinput) `updatedInput` | `PreToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§2 reescribir](hooks-pre-post-tooluse.md#2-tabla-maestra) |
| [P2](#p2-allow-ask-defer-y-precedencia-entre-hooks) `allow`, `ask`, `defer` | `PreToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§3 `permissionDecision`](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse) |
| [P3](#p3-additionalcontext-tras-una-consulta) `additionalContext` | `PostToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§2 añadir contexto](hooks-pre-post-tooluse.md#2-tabla-maestra) |
| [P4](#p4-decision-block-en-posttooluse-es-feedback-no-bloqueo) `decision: "block"` | `PostToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§2 bloquear](hooks-pre-post-tooluse.md#2-tabla-maestra) y [§6 trampas](hooks-pre-post-tooluse.md#6-trampas) |
| [P5](#p5-filtrar-por-ruta-dentro-del-hook-y-la-vía-bash) Filtrar por ruta | `PreToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§4 matchers](hooks-pre-post-tooluse.md#4-matchers-y-registro) y [§6 trampas](hooks-pre-post-tooluse.md#6-trampas) |
| [P6](#p6-un-guard-que-falla-en-cerrado) Guard en cerrado | `PreToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§2 si el callback falla](hooks-pre-post-tooluse.md#2-tabla-maestra) y [§6 trampas](hooks-pre-post-tooluse.md#6-trampas) |
| [P7](#p7-auditoría-asíncrona) Auditoría `async` | `PostToolUse` | `EN PRODUCCIÓN (no evaluable)` | [§5 async](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida) |
| [S1](#s1-hooks-de-comando-el-código-de-salida-decide) Hook de comando | ambos | `EN PRODUCCIÓN (no evaluable)` | [§5 exit codes](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida) |

Antes de los escenarios, la [anatomía de una llamada](#anatomía-de-una-llamada-qué-recibe-y-qué-devuelve-un-hook) muestra el JSON que recibe y devuelve cada hook, y [«Cómo se conecta»](#cómo-se-conecta-de-las-opciones-a-una-llamada-con-query) una llamada real con `query()`. E1 y E2 son los dos casos que nombra la guía. Los demás son campos y comportamientos del SDK: sirven para implementar, y ninguno decide la respuesta de una pregunta tipo examen.

El registro común está en `build_options()`: aplica `setting_sources=[]` y `max_budget_usd` (regla del proyecto en toda ejecución con modelo).

---

## Anatomía de una llamada: qué recibe y qué devuelve un hook

**Carril:** `EN PRODUCCIÓN (no evaluable)`: es el formato concreto del SDK. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra), [§3](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse), [§4](hooks-pre-post-tooluse.md#4-matchers-y-registro), [§5](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida).

Un callback del SDK es `async def cb(input_data, tool_use_id, context)`. `input_data` es el JSON del evento; `tool_use_id` es el mismo id que lleva dentro y es lo que correlaciona el `PreToolUse` y el `PostToolUse` de **una misma llamada**. Un hook de comando recibe ese mismo JSON por stdin.

### 1. `PreToolUse`: lo que recibe

*Ayuda rápida:* [§2 input](hooks-pre-post-tooluse.md#2-tabla-maestra) y [§4 nombres de herramienta MCP y matchers](hooks-pre-post-tooluse.md#4-matchers-y-registro).

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/u/.claude/projects/p/abc123.jsonl",
  "cwd": "/home/u/proyecto",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "mcp__billing__process_refund",
  "tool_input": { "order_id": "A-1042", "amount": 750 },
  "tool_use_id": "toolu_01REF",
  "mcp_server": { "name": "billing", "source": "sdk" }
}
```

- `tool_name`, `tool_input` y `tool_use_id` son los tres campos propios del evento; el resto son campos comunes a todos los hooks.
- `mcp_server` solo aparece en herramientas MCP.
- En `Write`, `Edit` y `Read`, `tool_input.file_path` llega siempre **absoluto** (con barras invertidas en Windows: normalizar antes de comparar).
- Los campos de `tool_input` dependen de la herramienta (`command` en `Bash`, `file_path` y `content` en `Write`, los argumentos que defina el servidor en una MCP).

### 2. `PreToolUse`: lo que devuelve

*Ayuda rápida:* [§2 bloquear y reescribir](hooks-pre-post-tooluse.md#2-tabla-maestra), [§3 `permissionDecision` y precedencia](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse) y [§6 trampas](hooks-pre-post-tooluse.md#6-trampas).

| Decisión | JSON devuelto | Escenario |
|---|---|---|
| No opinar (la llamada sigue su flujo normal) | `{}` | todos |
| Bloquear y explicar al modelo | ver abajo | [E1](#e1-bloquear-reembolsos-grandes-y-redirigir-a-un-humano) |
| Aprobar y reescribir el input | `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {…el input entero…}}}` | [P1](#p1-reescribir-argumentos-con-updatedinput) |
| Pedir confirmación o pausar | igual con `"ask"` o `"defer"` | [P2](#p2-allow-ask-defer-y-precedencia-entre-hooks) |

Salida real de `block_large_refund` para la entrada de arriba:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Un reembolso de 750.00 supera el límite de 500. No lo reintentes: llama a mcp__billing__escalate_to_human con order_id y el motivo."
  }
}
```

Con `"amount": 120` la misma función devuelve `{}`. El `permissionDecisionReason` de un `deny` es lo que lee el modelo.

### 3. `PostToolUse`: lo que recibe

*Ayuda rápida:* [§2 input de `PostToolUse`](hooks-pre-post-tooluse.md#2-tabla-maestra) y [§7 `PostToolUseFailure`](hooks-pre-post-tooluse.md#7-mecanismos-hermanos).

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/u/.claude/projects/p/abc123.jsonl",
  "cwd": "/home/u/proyecto",
  "permission_mode": "default",
  "hook_event_name": "PostToolUse",
  "tool_name": "mcp__crm__get_order",
  "tool_input": { "order_id": "A-1042" },
  "tool_response": [
    { "type": "text", "text": "{\"order_id\": \"A-1042\", \"created_at\": 1760000000, \"status\": 2}" }
  ],
  "tool_use_id": "toolu_01ORD",
  "duration_ms": 84,
  "mcp_server": { "name": "crm", "source": "sdk" }
}
```

- Además de `tool_input`, trae `tool_response` (lo que devolvió la herramienta) y `duration_ms` (sin contar permisos ni hooks de `PreToolUse`).
- **La forma de `tool_response` depende de la herramienta.** Aquí es una lista de bloques de texto con un JSON dentro. `Producto observado (no evaluable)`: es la forma que emite un servidor MCP del SDK ([traza real](#cómo-se-conecta-de-las-opciones-a-una-llamada-con-query)); otros servidores no están verificados.
- Solo se dispara si la herramienta terminó con éxito: si falla, el evento es `PostToolUseFailure`.

### 4. `PostToolUse`: lo que devuelve

*Ayuda rápida:* [§2 reescribir, añadir contexto y bloquear](hooks-pre-post-tooluse.md#2-tabla-maestra) y [§6 trampas](hooks-pre-post-tooluse.md#6-trampas).

Salida real de `normalize_mcp_output` para la entrada de arriba (`created_at` pasa de Unix a ISO 8601 y `status` de código a texto, con la misma forma que llegó):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "updatedToolOutput": [
      {
        "type": "text",
        "text": "{\"order_id\": \"A-1042\", \"created_at\": \"2025-10-09T08:53:20Z\", \"status\": \"delivered\"}"
      }
    ]
  }
}
```

| Intención | JSON devuelto | Escenario |
|---|---|---|
| No tocar el resultado | `{}` | [E2](#e2-normalizar-datos-heterogéneos-de-herramientas-mcp) |
| Sustituir lo que ve el modelo | `hookSpecificOutput.updatedToolOutput` (misma forma que la salida original) | [E2](#e2-normalizar-datos-heterogéneos-de-herramientas-mcp) |
| Añadir un dato junto al resultado | `hookSpecificOutput.additionalContext` | [P3](#p3-additionalcontext-tras-una-consulta) |
| Dar feedback a Claude (no oculta nada) | `{"decision": "block", "reason": "…"}` en el nivel superior | [P4](#p4-decision-block-en-posttooluse-es-feedback-no-bloqueo) |

### 5. Una llamada de principio a fin

*Ayuda rápida:* [§2 cuándo dispara cada evento](hooks-pre-post-tooluse.md#2-tabla-maestra), [§3 precedencia entre hooks](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse) y [§5 varios hooks en paralelo y `async`](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida).

| Paso | Evento | `tool_use_id` | Qué pasa |
|---|---|---|---|
| 1 | El modelo pide `process_refund` con `amount: 120` | `toolu_01REF` | — |
| 2 | `PreToolUse` | `toolu_01REF` | `block_large_refund` devuelve `{}`: sigue el flujo normal de permisos |
| 3 | La herramienta se ejecuta | — | Devuelve su resultado |
| 4 | `PostToolUse` | `toolu_01REF` | `normalize_mcp_output` normaliza fechas y estado antes de que el modelo lo vea |

Con `amount: 750` el paso 2 devuelve el `deny` de arriba, la herramienta **no** se ejecuta y no hay `PostToolUse`. El mismo `tool_use_id` en los pasos 2 y 4 es lo que permite, por ejemplo, medir el tiempo entre ambos o unir las dos entradas de un registro de auditoría ([P7](#p7-auditoría-asíncrona)).

---

## Cómo se conecta: de las opciones a una llamada con `query()`

**Carril:** `EN PRODUCCIÓN (no evaluable)` la conexión; `Producto observado (no evaluable)` la traza. **Ayuda rápida:** [§4 registro en el SDK](hooks-pre-post-tooluse.md#4-matchers-y-registro). **Código:** `build_options`, `build_demo_servers`, `run_demo`.

```python
options = build_options(build_demo_servers(), production=True, model="haiku", max_budget_usd=0.30)
# dentro de build_options: setting_sources=[], max_budget_usd y los hooks
#   "PreToolUse":  [HookMatcher(matcher="mcp__billing__process_refund", hooks=[block_large_refund]), ...]
#   "PostToolUse": [HookMatcher(matcher="^mcp__", hooks=[normalize_mcp_output]), ...]
async for message in query(prompt="Reembolsa 750 al pedido A-1042", options=options):
    ...  # AssistantMessage (ToolUseBlock, TextBlock), UserMessage (ToolResultBlock) y ResultMessage
```

```bash
# Gasta tokens (tope de 0.30 USD). Con otra cuenta, HOOKS_DEMO_CLI apunta a su lanzador.
uv run python docs/referencia/hooks/hooks_escenarios.py --demo "Consulta el pedido A-1042 y reembolsa 750 si está entregado."
```

- **Sin servidor externo:** `create_sdk_mcp_server` y `@tool` montan `billing` y `crm` dentro del propio proceso. Así los nombres son `mcp__billing__*` y `mcp__crm__*` y los hooks se prueban sin infraestructura.
- **Trazas:** `run_demo` añade dos hooks sin matcher que solo imprimen lo que reciben y devuelven `{}`, y muestra lo que **vuelve al modelo** (`ToolResultBlock`).
- **Otra cuenta:** si el lanzador guarda su `apiKeyHelper` en los settings de usuario, `setting_sources=[]` hace fallar la llamada con «Not logged in». La demo habilita solo la fuente `user` cuando se le pasa un lanzador.

**Traza real** (Claude Code 2.1.325, `claude-agent-sdk` 0.2.173, Haiku; unos 0.004 USD por ejecución):

| Paso | Qué ocurrió |
|---|---|
| 1 | `PreToolUse` de `get_order`: ningún hook decide, la llamada sigue. La herramienta devuelve `[{"type": "text", "text": "{\"created_at\": 1760000000, \"status\": 2, …25 items…}"}]` |
| 2 | `PostToolUse`: `normalize_mcp_output` reescribe. El modelo ve `created_at` en ISO 8601, `"status": "delivered"`, 20 `items` y `items_omitted: 5` |
| 3 | `PreToolUse` de `process_refund` con `amount: 750`: `block_large_refund` deniega. **No hay `PostToolUse` de esa llamada** |
| 4 | El modelo recibe un resultado con `is_error=True` y el texto `PreToolUse:mcp__billing__process_refund hook error: Un reembolso de 750.00 supera el límite de 500. No lo reintentes: llama a mcp__billing__escalate_to_human …` |
| 5 | El modelo carga la herramienta de escalado (`ToolSearch`) y llama a `escalate_to_human` con un motivo que menciona el bloqueo |
| 6 | `PostToolUse` de `escalate_to_human`: el modelo ve `"status": "pending"` y `created_ts` en ISO 8601 |

**Qué enseña la traza**
- **Forma de `tool_response` confirmada** para un servidor MCP del SDK: una lista de bloques de texto con el JSON dentro. Es la forma que supone E2, y `updatedToolOutput` con esa misma forma llegó al modelo. Otros servidores MCP no están verificados.
- **El `deny` llega como error de herramienta**, con el prefijo `PreToolUse:<herramienta> hook error:` y el motivo detrás. El `permissionDecisionReason` es, por tanto, un texto escrito para el modelo.
- **La redirección ocurrió, pero por el motivo.** Tras el `deny` el modelo se dispuso a escalar en las dos ejecuciones (la primera la completó con el ticket `ESC-001`; la segunda la corté antes del final). Es lo que E1 describe como guía y no como garantía.
- **La traza reúne dos ejecuciones con prompts distintos** (el reembolso solo, y la consulta seguida del reembolso); los pasos 1 y 2 se vieron en ambas.
- **Un matcher `^mcp__` es amplio.** También normalizó `escalate_to_human`, que no era el objetivo. Para acotarlo hay que nombrar las herramientas o filtrar dentro del hook.
- **Sin matcher significa todas las herramientas, también las internas.** Los hooks de traza se dispararon incluso con `ToolSearch`.

---

## Verificación con modelo: resultados observados

**Carril:** `Producto observado (no evaluable)`. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra), [§3](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse), [§4](hooks-pre-post-tooluse.md#4-matchers-y-registro), [§5](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida), [§6](hooks-pre-post-tooluse.md#6-trampas).

Cada afirmación de la ayuda rápida que se podía ejecutar se probó con modelo en un directorio temporal, midiendo efectos reales (archivos creados, contador de llamadas a la herramienta) y no lo que el modelo contaba. Condiciones: Claude Code 2.1.325, `claude-agent-sdk` 0.2.173, Haiku, **una ejecución por caso**. Los hooks de comando se probaron con `claude -p` y `settings.json`; los callbacks, con `query()`.

| Afirmación | Resultado |
|---|---|
| `allow` con `updatedInput` reemplaza el input antes de ejecutar ([P1](#p1-reescribir-argumentos-con-updatedinput)) | **Confirmado.** El `Write` pedido a `…/out/hello.txt` se creó bajo el sandbox y el original no existe. El modelo vio la ruta real en el resultado, buscó el archivo en la ruta pedida, no lo halló y dijo que no pudo crearlo: reescribir en silencio desorienta al modelo |
| `allow` y `ask` a la vez: gana `ask` ([P2](#p2-allow-ask-defer-y-precedencia-entre-hooks)) | **Confirmado.** La herramienta no se ejecutó aunque estaba preaprobada en `allowed_tools`; sin nadie que conteste, el modelo recibió el `reason` como error |
| `allow` amplio frente a `deny`: gana `deny` | **Confirmado** (traza de «Cómo se conecta») |
| `defer` termina con `stop_reason: "tool_deferred"` | **Confirmado** con un callback del SDK y con un hook de comando en `-p`; la herramienta no se ejecutó. El descarte de `updatedInput` y de `additionalContext` con `defer` no se probó |
| `additionalContext` llega al modelo ([P3](#p3-additionalcontext-tras-una-consulta)) | **Confirmado.** El modelo dio un código que solo estaba en el contexto añadido; el resultado de la herramienta no cambió |
| `decision: "block"` en `PostToolUse` no oculta nada ([P4](#p4-decision-block-en-posttooluse-es-feedback-no-bloqueo)) | **Confirmado.** El resultado de la herramienta llegó intacto (`{"status": 1}`) y el `reason` llegó aparte, como mensaje de hook |
| Un *timeout* de callback del SDK bloquea `PreToolUse` | **Confirmado.** «PreToolUse hook did not respond before its timeout… The tool call was not executed»; el modelo reintentó una vez |
| Un *timeout* de un hook de comando no bloquea | **Confirmado.** La herramienta se ejecutó |
| Un callback que lanza error deja pasar la llamada; `fail_closed` la bloquea ([P6](#p6-un-guard-que-falla-en-cerrado)) | **Confirmado.** Sin cierre, la herramienta se ejecutó (1 llamada); con `fail_closed`, 0 llamadas y el modelo recibió el motivo |
| `onFailure: "block"` en un hook de comando | **Confirmado** con un script ausente (127) y con `exit 1`: bloquea. Sin la opción, la llamada se ejecuta |
| `exit 2` bloquea, un JSON `deny` con `exit 0` bloquea, `exit 1` no ([S1](#s1-hooks-de-comando-el-código-de-salida-decide)) | **Confirmado** con `rm -rf ./victim`: con `exit 2` y con JSON el directorio siguió existiendo; con `exit 1` desapareció |
| En `PostToolUse`, `exit 2` solo muestra el *stderr* a Claude | **Confirmado.** El comando ya había corrido y su salida llegó; el modelo recibió el *stderr* citado como error de bloqueo del hook |
| El `allow` de un hook no salta una regla `deny` de `settings.json` | **Confirmado.** La regla ganó y el comando no se ejecutó |
| Matchers: solo letras es literal; con otros caracteres es regex sin anclar | **Confirmado** contra `Read`: dispararon `Read`, `^Read$` y `ead.*`; no dispararon `ead` (literal exacto) ni `^ead$` |
| `Write\|Edit` no ve un `Bash` ([P5](#p5-filtrar-por-ruta-dentro-del-hook-y-la-vía-bash)) | **Confirmado.** `echo KEY=1 > .env` creó el archivo; con `Write\|Edit\|Bash` quedó bloqueado |
| Los hooks de `settings.json` se cargan según `setting_sources` | **Confirmado.** Dispararon con `project` en las fuentes y no sin ella |
| Los hooks pueden no ejecutarse al terminar por `max_turns` | **Confirmado** con `max_turns=1`: ni la herramienta ni sus hooks llegaron a ejecutarse (`error_max_turns`) |
| Un hook `async` registra sin esperar ([P7](#p7-auditoría-asíncrona)) | **Confirmado.** El registro se escribió con el `tool_use_id` y la ejecución terminó sin error |

**Trampa nueva: el código de salida de un script que no existe.** `python3 /ruta/que/no/existe.py` sale con **`2`**, que es un código bloqueante: sin `onFailure` el hook bloquea sin querer. Un script de shell ausente sale con `127` y no bloquea. Una prueba con Python no distingue, por tanto, si `onFailure` funciona.

**Cómo se ve un bloqueo desde el modelo.** Con `exit 2`, el modelo recibe `PreToolUse:Bash hook error: [comando]: <stderr>`. Con un JSON `deny` recibe el mismo prefijo seguido del `permissionDecisionReason`.

**Sin probar:** el descarte de `updatedInput`/`additionalContext` con `defer`, el `ask` frente a `defer`, `on_failure` (no existe en el SDK 0.2.173) y todo lo propio de TypeScript.

---

## E1. Bloquear reembolsos grandes y redirigir a un humano

**Carril:** examen (TS 1.5). **Ayuda rápida:** [§1](hooks-pre-post-tooluse.md#1-lo-que-evalúa-el-examen), [§3](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse). **Código:** `block_large_refund`.

**Situación.** Un agente de soporte puede llamar a `mcp__billing__process_refund`. La regla de negocio dice que por encima de 500 el reembolso lo decide una persona.

```python
async def block_large_refund(input_data, tool_use_id, context):
    ...
    if amount > REFUND_LIMIT:
        return pre_output("deny",
            f"Un reembolso de {amount:.2f} supera el límite de {REFUND_LIMIT}. "
            f"No lo reintentes: llama a {ESCALATE_TOOL} con order_id y el motivo.")
    return {}

HookMatcher(matcher="mcp__billing__process_refund", hooks=[block_large_refund])
```

| Entrada (`tool_input`) | Salida del hook | Resultado |
|---|---|---|
| `{"order_id": "A1", "amount": 750}` | `deny` + motivo con la herramienta de escalado | No se ejecuta; el modelo lee el motivo |
| `{"amount": 500}` | `{}` | Se ejecuta (el límite es «más de 500») |
| `{"amount": "mucho"}` o `"nan"` | `deny` | Falla en cerrado: un importe que no se puede comparar no pasa |

**Por qué un hook y no una instrucción.** Escribir «nunca reembolses más de 500» en el *prompt* funciona casi siempre, y «casi siempre» no es una garantía: un importe formulado de otra forma, una conversación larga o una inyección pueden saltárselo. El hook se ejecuta fuera del razonamiento del modelo y la regla se cumple al 100 %.

**Matiz de la redirección.** El `deny` garantiza que el reembolso **no se ejecuta**. Que el modelo después llame a la herramienta de escalado depende de que siga el motivo, que es una guía y no una garantía. Si la derivación también debe ser segura, la herramienta de escalado ha de ser la única vía para ese caso, y no solo una sugerencia del mensaje.

---

## E2. Normalizar datos heterogéneos de herramientas MCP

**Carril:** examen (TS 1.5). **Ayuda rápida:** [§1](hooks-pre-post-tooluse.md#1-lo-que-evalúa-el-examen), [§5](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida). **Código:** `normalize_mcp_output`.

**Situación.** Tres servidores MCP devuelven la misma información con formatos distintos: fechas como Unix en segundos, Unix en milisegundos o ISO 8601 con zona, y el estado como código numérico. El hook las deja en un único formato antes de que el modelo las lea.

```python
HookMatcher(matcher="^mcp__", hooks=[normalize_mcp_output])   # regex: cualquier herramienta MCP

# dentro: unwrap_response -> normalize_data -> updatedToolOutput con la misma forma
return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                               "updatedToolOutput": rewrap(new_data)}}
```

| `tool_response` recibido | Lo que ve el modelo |
|---|---|
| `{"created_at": 1760000000, "status": 2}` | `{"created_at": "2025-10-09T08:53:20Z", "status": "delivered"}` |
| `{"updated_at": "2025-10-09T08:15:00+02:00"}` | `{"updated_at": "2025-10-09T06:15:00Z"}` |
| `{"sent_at": 1760000000000, "status": 9}` | `sent_at` en ISO 8601; el código 9, desconocido, se deja como está |
| `{"created_at": "2025-10-09T06:15:00Z", "status": "ok"}` | `{}`: sin cambios no se reescribe |

- **Un solo hook para varias reescrituras.** `normalize_data` trunca `items` a 20 (con `items_omitted`), pasa las fechas a ISO 8601 y traduce los estados, todo en secuencia. Dos hooks no se encadenan: cada uno vería el resultado original y no está documentado cuál prevalece. `Producto observado (no evaluable)`: en una prueba con Claude Code 2.1.325 (dos hooks de comando sobre `Bash`, retardos cruzados), ambos recibieron el original y el modelo vio solo la reescritura del que terminó último.
- **La misma forma de salida.** `unwrap_response` admite un dict, un texto JSON y una lista de bloques de texto, y `rewrap` devuelve el resultado con la forma que llegó. `Producto observado (no evaluable)`: un servidor MCP del SDK emite justo esa lista de bloques de texto ([traza real](#cómo-se-conecta-de-las-opciones-a-una-llamada-con-query)); con otro servidor conviene registrar primero un hook que solo imprima `tool_response`.
- **Lo que no hace.** `updatedToolOutput` solo cambia lo que ve el modelo; la herramienta ya corrió y la telemetría guarda la salida original. En herramientas MCP no se valida la forma; en las nativas, un valor que no encaja se ignora.

---

## P1. Reescribir argumentos con `updatedInput`

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra). **Código:** `redirect_writes_to_sandbox`.

```python
new_input = dict(input_data["tool_input"])            # copia: no se muta el original
new_input["file_path"] = posixpath.normpath(SANDBOX_ROOT + "/" + path.lstrip("/"))
return pre_output("allow", "Escritura redirigida al sandbox", updatedInput=new_input)
```

| Entrada (`Write`) | Salida |
|---|---|
| `/etc/app.conf` | `allow` + `updatedInput` con `/tmp/hooks-escenarios-sandbox/etc/app.conf` y el `content` intacto |
| `../../etc/passwd` | `deny`: el `..` escaparía del sandbox |
| una ruta ya dentro del sandbox | `{}`: no se reescribe dos veces |

`updatedInput` reemplaza el input **entero**: por eso se copia el dict y se cambia solo `file_path`. Va dentro de `hookSpecificOutput`; fuera de ahí, o junto a `defer`, no se aplica. Reescribir en silencio corrige un descuido, pero también tapa un intento que un `deny` haría visible.

---

## P2. `allow`, `ask`, `defer` y precedencia entre hooks

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§3](hooks-pre-post-tooluse.md#3-permissiondecision-solo-pretooluse). **Código:** `allow_billing_tools`, `ask_mid_refunds`, `defer_refund_for_approval`, `most_restrictive`.

```python
HookMatcher(matcher="^mcp__billing__", hooks=[allow_billing_tools, ask_mid_refunds])
# junto a block_large_refund (E1): los tres corren en paralelo sobre la misma llamada
```

| Reembolso | Decisiones de los hooks | Gana |
|---|---|---|
| 900 | `allow` (aprobación amplia) y `deny` (E1) | `deny` |
| 300 | `allow` y `ask` (entre 200 y 500) | `ask` |
| 300 | `allow`, `ask` y `defer` (aprobación fuera de línea) | `defer` |

- **Precedencia:** `deny` > `defer` > `ask` > `allow`. Un `allow` amplio nunca anula el `deny` de otro hook, y los hooks no esperan unos a otros. `most_restrictive` solo modela la regla para probarla; quien la aplica es Claude Code.
- **`allow` tampoco salta las reglas `deny`/`ask` de `settings.json`.**
- **`defer`** termina el turno con `stop_reason: "tool_deferred"` para reanudar después; en el CLI solo funciona con `-p`, y descarta `updatedInput` y `additionalContext`.

---

## P3. `additionalContext` tras una consulta

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra). **Código:** `add_account_context`.

```python
HookMatcher(matcher="mcp__crm__get_customer", hooks=[add_account_context])
# resultado {"currency": "EUR", ...} -> additionalContext junto al resultado, que sigue intacto
```

Añade «La moneda de esta cuenta es EUR…» sin reemplazar la salida. Va redactado como un dato (no como una orden) porque una frase con forma de instrucción del sistema puede activar las defensas contra inyección de *prompt* y Claude la mostraría al usuario en lugar de usarla. Si varios hooks devuelven `additionalContext`, Claude recibe todos.

---

## P4. `decision: "block"` en `PostToolUse` es feedback, no bloqueo

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra), [§6](hooks-pre-post-tooluse.md#6-trampas). **Código:** `flag_incomplete_order`.

```python
return {"decision": "block",                 # nivel superior, no dentro de hookSpecificOutput
        "reason": "La respuesta de get_order no trae order_id. Verifica el pedido antes de reembolsar."}
```

La herramienta ya corrió y **Claude sigue viendo la salida original**: el `reason` solo se añade a su lado. Es la trampa de usar `block` para ocultar un resultado; para sustituirlo, `updatedToolOutput` (E2). La autocomprobación verifica que la respuesta no lleva `hookSpecificOutput`.

---

## P5. Filtrar por ruta dentro del hook y la vía `Bash`

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§4](hooks-pre-post-tooluse.md#4-matchers-y-registro), [§6](hooks-pre-post-tooluse.md#6-trampas). **Código:** `guard_protected_paths`.

```python
HookMatcher(matcher="Write|Edit|Bash", hooks=[guard_protected_paths])
```

| Llamada | Resultado |
|---|---|
| `Write` a `/app/.env`, `Edit` a `C:\app\.ENV.local` | `deny` |
| `Write` a `/app/.env.example` o `/app/.venv/x` | `{}` (plantilla y otro directorio) |
| `Bash`: `echo KEY=1 > .env` | `deny` |

El matcher solo ve el **nombre** de la herramienta, así que la ruta se comprueba dentro del hook, en `tool_input`. Con `Write|Edit` a secas, `echo > .env` pasaría por `Bash`: por eso el matcher incluye `Bash`. El filtro de shell es una heurística: no detecta un script que escriba por dentro ni rutas compuestas con variables.

---

## P6. Un guard que falla en cerrado

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§2](hooks-pre-post-tooluse.md#2-tabla-maestra), [§6](hooks-pre-post-tooluse.md#6-trampas). **Código:** `fail_closed`, `buggy_refund_guard`, `strict_refund_guard`.

```python
strict_refund_guard = fail_closed(buggy_refund_guard)   # error o ausencia de decisión -> deny
```

| Entrada | `buggy_refund_guard` a pelo | Con `fail_closed` |
|---|---|---|
| `{}` (falta `amount`) | `KeyError`: la llamada seguiría su flujo normal | `deny` |
| `{"amount": "900"}` | `TypeError`: ídem | `deny` |
| `{"amount": 10}` | `{}` | `{}` |

- **Por defecto un fallo no bloquea:** si un callback lanza error, la acción sigue y solo llega un aviso. Un `PreToolUse` que se rompe deja pasar la llamada.
- **Con el SDK de la versión fijada (0.2.173) hay que cerrarlo a mano**, como aquí. `HookMatcher(..., on_failure="block")` (`onFailure` en TypeScript) existe desde Python SDK 0.2.177 y TypeScript SDK 0.3.317.
- **Un guard que atrapa su propio error y devuelve `{}` no falla:** la llamada pasa. El error debe llegar hasta quien cierra.
- **Un camino sin `return` también cuenta como fallo.**

---

## P7. Auditoría asíncrona

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§5](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida). **Código:** `make_audit_logger`.

```python
asyncio.create_task(asyncio.to_thread(_append, json.dumps(record)))
return {"async_": True, "asyncTimeout": 30000}      # el agente no espera
```

Anota herramienta, `tool_use_id` (el mismo que tuvo el `PreToolUse`), duración y hora. Como el agente ya siguió adelante, un hook asíncrono **no puede bloquear, reescribir ni añadir contexto**: solo sirve para logs y métricas. En Python la clave es `async_`, porque `async` es palabra reservada.

---

## S1. Hooks de comando: el código de salida decide

**Carril:** `EN PRODUCCIÓN (no evaluable)`. **Ayuda rápida:** [§5](hooks-pre-post-tooluse.md#5-varios-hooks-async-y-códigos-de-salida). **Código:** `hooks_escenarios_shell.py`; registro en `hooks_escenarios_settings.json`.

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash",
  "hooks": [{"type": "command", "command": "python docs/referencia/hooks/hooks_escenarios_shell.py exit2", "onFailure": "block"}]}]}}
```

Con la entrada `rm -rf /var/data` en `PreToolUse`:

| Modo | Salida del script | Efecto |
|---|---|---|
| `exit2` | `exit 2` y el motivo en *stderr* | **Bloquea** la llamada |
| `json` | `exit 0` y `permissionDecision: "deny"` en JSON | Bloquea; con `exit 0` decide el JSON |
| `exit1` | `exit 1` y el motivo en *stderr* | **No bloquea**: error no bloqueante, la llamada se ejecuta |
| entrada ilegible | `exit 2` | Falla en cerrado (con `exit 1` la llamada pasaría) |

En `PostToolUse`, el modo `post-exit2` con `exit 2` solo muestra el *stderr* a Claude: la herramienta ya corrió.

- **La trampa es el `exit 1`**: es el código «de error» habitual en Unix y aquí no impone nada. Para hacer cumplir una política, `exit 2`.
- **Un JSON junto a `exit 2` no puede anular el bloqueo.**
- **`onFailure: "block"`** en un hook de comando cierra también el caso de que el script no arranque (una ruta mal escrita) o agote su tiempo; requiere Claude Code 2.1.295 o posterior. Sin él, un hook de comando que agota el tiempo en `PreToolUse` **no** bloquea; un callback del SDK que lo agota, sí.
- La autocomprobación solo ejercita el script. La carga desde `settings.json` con el CLI real se verificó aparte ([resultados](#verificación-con-modelo-resultados-observados)); para repetirlo, copia el registro a `.claude/settings.local.json` de un proyecto de prueba.
