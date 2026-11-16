"""Hooks de prueba (callbacks del Agent SDK) para `hooks-escenarios-codigo.md`.

PROPÓSITO: un callback ejecutable por cada escenario del documento, más una
autocomprobación sin modelo (`python docs/hooks/hooks_escenarios.py`) que los llama con
entradas sintéticas y verifica la salida JSON que devolvería cada uno.

POR QUÉ EXISTE: el documento enseña qué campo es válido en cada evento y qué
decisión toma el hook. Un fragmento sin ejecutar se pudre; este módulo lo prueba.

QUÉ NO HACE: no se carga en el proyecto (`.claude/settings.json` no lo nombra) y solo
llama al modelo con `--demo` (opt-in, gasta tokens). Las herramientas
`mcp__billing__*` y `mcp__crm__*` son inventadas: un servidor MCP en el propio proceso
con datos fijos. La forma exacta del `tool_response` de una herramienta MCP depende de
su servidor: `unwrap_response` admite las formas habituales (dict, texto JSON y lista de
bloques de texto) y `--demo` imprime la que llega de verdad.

Uso:
  uv run python docs/hooks/hooks_escenarios.py                 # autocomprobación, sin modelo
  uv run python docs/hooks/hooks_escenarios.py --demo "<prompt>"   # llamada real con query()
  (con `HOOKS_DEMO_CLI=<ruta del ejecutable claude>` se elige otro lanzador, p. ej. otra cuenta)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import posixpath
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Utilidades comunes
# --------------------------------------------------------------------------

REFUND_TOOL = "mcp__billing__process_refund"
ESCALATE_TOOL = "mcp__billing__escalate_to_human"
REFUND_LIMIT = 500


def pre_output(decision: str, reason: str | None = None, **extra: Any) -> dict[str, Any]:
    """Salida de `PreToolUse`: todo va dentro de `hookSpecificOutput`, con `hookEventName`."""
    out: dict[str, Any] = {"hookEventName": "PreToolUse", "permissionDecision": decision}
    if reason:
        out["permissionDecisionReason"] = reason
    out.update(extra)
    return {"hookSpecificOutput": out}


def unwrap_response(response: Any):
    """Devuelve `(datos, rewrap)` o `(None, None)` si el resultado no es JSON.

    `rewrap` reconstruye el resultado con la MISMA forma que llegó, porque
    `updatedToolOutput` debe respetar la forma de la salida de la herramienta.
    """
    if isinstance(response, dict) and isinstance(response.get("content"), list):
        inner, inner_rewrap = unwrap_response(response["content"])
        if inner is None:
            return None, None
        return inner, lambda d: {**response, "content": inner_rewrap(d)}
    if isinstance(response, dict):
        return response, lambda d: d
    if isinstance(response, str):
        try:
            return json.loads(response), lambda d: json.dumps(d, ensure_ascii=False)
        except ValueError:
            return None, None
    if isinstance(response, list) and len(response) == 1 and isinstance(response[0], dict) and response[0].get("type") == "text":
        try:
            data = json.loads(response[0]["text"])
        except (ValueError, KeyError, TypeError):
            return None, None
        return data, lambda d: [{**response[0], "text": json.dumps(d, ensure_ascii=False)}]
    return None, None


# --------------------------------------------------------------------------
# E1 · Bloquear reembolsos grandes y redirigir a un humano (PreToolUse, examen)
# --------------------------------------------------------------------------


async def block_large_refund(input_data, tool_use_id, context):
    """Deniega un reembolso por encima del límite y dice al modelo a dónde ir."""
    if input_data["tool_name"] != REFUND_TOOL:
        return {}
    raw = input_data["tool_input"].get("amount")
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        amount = math.nan
    # Falla en cerrado: un importe ilegible o NaN no se puede comparar, así que no pasa.
    if not math.isfinite(amount):
        return pre_output("deny", f"No se puede comprobar el importe {raw!r}. Escala el caso con {ESCALATE_TOOL}.")
    if amount > REFUND_LIMIT:
        return pre_output(
            "deny",
            f"Un reembolso de {amount:.2f} supera el límite de {REFUND_LIMIT}. "
            f"No lo reintentes: llama a {ESCALATE_TOOL} con order_id y el motivo.",
        )
    return {}


# --------------------------------------------------------------------------
# E2 · Normalizar datos heterogéneos de herramientas MCP (PostToolUse, examen)
# --------------------------------------------------------------------------

STATUS_NAMES = {0: "pending", 1: "shipped", 2: "delivered", 3: "cancelled"}
MAX_ITEMS = 20
TIME_KEY_SUFFIXES = ("_at", "_ts", "_time", "timestamp")


def to_iso_utc(value: Any) -> str | None:
    """Unix (s o ms) o ISO 8601 -> ISO 8601 UTC con `Z`; `None` si no es una fecha."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() and len(text) >= 9:
            value = int(text)
        else:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)  # sin zona: se asume UTC
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, (int, float)):
        seconds = value / 1000 if abs(value) >= 1e11 else value  # >= 1e11: milisegundos
        try:
            return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (OverflowError, OSError, ValueError):
            return None
    return None


def normalize_data(data: Any) -> tuple[Any, bool]:
    """Aplica en secuencia: truncar listas, fechas a ISO 8601 y códigos de estado a texto."""
    if isinstance(data, list):
        results = [normalize_data(item) for item in data]
        return [r[0] for r in results], any(r[1] for r in results)
    if not isinstance(data, dict):
        return data, False
    out: dict[str, Any] = {}
    changed = False
    for key, value in data.items():
        if isinstance(value, list) and key == "items" and len(value) > MAX_ITEMS:
            out["items_omitted"] = len(value) - MAX_ITEMS
            value, changed = value[:MAX_ITEMS], True
        if key.lower().endswith(TIME_KEY_SUFFIXES):
            iso = to_iso_utc(value)
            if iso is not None:
                out[key], changed = iso, changed or iso != value
                continue
        if key == "status" and isinstance(value, int) and not isinstance(value, bool) and value in STATUS_NAMES:
            out[key], changed = STATUS_NAMES[value], True  # un código desconocido se deja como está
            continue
        out[key], sub_changed = normalize_data(value)
        changed = changed or sub_changed
    return out, changed


async def normalize_mcp_output(input_data, tool_use_id, context):
    """UN solo hook que trunca y normaliza: dos hooks no se encadenan, cada uno vería el original."""
    data, rewrap = unwrap_response(input_data.get("tool_response"))
    if data is None:
        return {}
    new_data, changed = normalize_data(data)
    if not changed:
        return {}  # sin cambios no se reescribe: así no se toca lo que ya estaba bien
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": rewrap(new_data)}}


# --------------------------------------------------------------------------
# P1 · Reescribir argumentos con updatedInput (PreToolUse, producción)
# --------------------------------------------------------------------------

SANDBOX_ROOT = "/tmp/hooks-escenarios-sandbox"


async def redirect_writes_to_sandbox(input_data, tool_use_id, context):
    """Antepone el sandbox a la ruta de `Write`. `updatedInput` reemplaza el input ENTERO."""
    if input_data["tool_name"] != "Write":
        return {}
    new_input = dict(input_data["tool_input"])  # copia: nunca se muta el original
    path = new_input.get("file_path", "")
    if posixpath.normpath(path).startswith(SANDBOX_ROOT + "/"):
        return {}
    target = posixpath.normpath(SANDBOX_ROOT + "/" + path.lstrip("/"))
    if not target.startswith(SANDBOX_ROOT + "/"):  # un `..` no puede sacar la escritura del sandbox
        return pre_output("deny", f"La ruta {path!r} escapa del sandbox.")
    new_input["file_path"] = target
    return pre_output("allow", "Escritura redirigida al sandbox", updatedInput=new_input)


# --------------------------------------------------------------------------
# P2 · allow, ask, defer y precedencia entre hooks (PreToolUse, producción)
# --------------------------------------------------------------------------

PRECEDENCE = ("deny", "defer", "ask", "allow")  # de más a menos restrictiva


async def allow_billing_tools(input_data, tool_use_id, context):
    """Aprobación amplia: un `allow` NO gana a un `deny` de otro hook."""
    if input_data["tool_name"].startswith("mcp__billing__"):
        return pre_output("allow", "Herramientas de billing aprobadas")
    return {}


async def ask_mid_refunds(input_data, tool_use_id, context):
    """Entre 200 y el límite, pide confirmación al usuario."""
    if input_data["tool_name"] != REFUND_TOOL:
        return {}
    try:
        amount = float(input_data["tool_input"].get("amount"))
    except (TypeError, ValueError):
        return {}
    if 200 < amount <= REFUND_LIMIT:
        return pre_output("ask", f"Reembolso de {amount:.2f}: confirma antes de ejecutar.")
    return {}


async def defer_refund_for_approval(input_data, tool_use_id, context):
    """Pausa el turno (`stop_reason: "tool_deferred"`) hasta que un humano apruebe fuera de línea.

    Descarta `updatedInput` y `additionalContext`; en el CLI solo funciona con `-p`.
    """
    if input_data["tool_name"] == REFUND_TOOL:
        return pre_output("defer", "Aprobación pendiente del responsable")
    return {}


def most_restrictive(outputs: list[dict[str, Any]]) -> str | None:
    """Modelo de la regla documentada `deny > defer > ask > allow` (la aplica Claude Code, no tú)."""
    decisions = [o["hookSpecificOutput"]["permissionDecision"] for o in outputs if "hookSpecificOutput" in o]
    return next((d for d in PRECEDENCE if d in decisions), None)


# --------------------------------------------------------------------------
# P3 · additionalContext tras una consulta (PostToolUse, producción)
# --------------------------------------------------------------------------


async def add_account_context(input_data, tool_use_id, context):
    """Añade un hecho junto al resultado, sin reemplazarlo. Redactado como dato, no como orden."""
    data, _ = unwrap_response(input_data.get("tool_response"))
    if not isinstance(data, dict) or "currency" not in data:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"La moneda de esta cuenta es {data['currency']}; los importes del reembolso van en esa moneda.",
        }
    }


# --------------------------------------------------------------------------
# P4 · decision "block" en PostToolUse: feedback, no bloqueo (producción)
# --------------------------------------------------------------------------


async def flag_incomplete_order(input_data, tool_use_id, context):
    """Pide a Claude que verifique. NO oculta el resultado: Claude sigue viendo la salida original."""
    data, _ = unwrap_response(input_data.get("tool_response"))
    if isinstance(data, dict) and "order_id" not in data:
        return {"decision": "block", "reason": "La respuesta de get_order no trae order_id. Verifica el pedido antes de reembolsar."}
    return {}


# --------------------------------------------------------------------------
# P5 · Filtrar por ruta dentro del hook y la vía Bash (PreToolUse, producción)
# --------------------------------------------------------------------------

ENV_IN_COMMAND = re.compile(r"(?:^|[\s/\\'\"=])(\.env(?:\.[\w.-]+)?)(?![\w.-])", re.IGNORECASE)


def is_secret_env(name: str) -> bool:
    name = name.lower()
    return name == ".env" or (name.startswith(".env.") and not name.endswith((".example", ".sample")))


async def guard_protected_paths(input_data, tool_use_id, context):
    """El matcher solo ve el nombre de la herramienta: la ruta se mira aquí, en `tool_input`.

    Registrado con `Write|Edit|Bash`, porque un matcher solo de `Write|Edit` no vería `echo > .env`.
    """
    tool_input = input_data["tool_input"]
    if input_data["tool_name"] == "Bash":
        hit = any(is_secret_env(m.group(1)) for m in ENV_IN_COMMAND.finditer(str(tool_input.get("command", ""))))
    else:
        hit = is_secret_env(posixpath.basename(str(tool_input.get("file_path", "")).replace("\\", "/")))
    return pre_output("deny", "Los archivos .env guardan credenciales y no se modifican.") if hit else {}


# --------------------------------------------------------------------------
# P6 · Guard que falla en cerrado (PreToolUse, producción)
# --------------------------------------------------------------------------


def fail_closed(guard):
    """Envuelve un guard: si lanza error o no devuelve nada, se deniega.

    En `claude-agent-sdk` 0.2.173 `HookMatcher` no tiene `on_failure` (llega en 0.2.177):
    esto da el mismo efecto a mano. Un guard que atrapa su error y devuelve `{}` NO falla:
    deja pasar la llamada, así que el error debe propagarse hasta este envoltorio.
    """

    async def wrapper(input_data, tool_use_id, context):
        try:
            result = await guard(input_data, tool_use_id, context)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del guard debe cerrar
            return pre_output("deny", f"El guard falló ({type(exc).__name__}); se bloquea por seguridad.")
        if result is None:  # un camino sin `return` es un fallo, no un «no opino»
            return pre_output("deny", "El guard no devolvió decisión; se bloquea por seguridad.")
        return result

    return wrapper


async def buggy_refund_guard(input_data, tool_use_id, context):
    """Guard con dos fallos reales: KeyError si falta `amount` y TypeError si llega como texto."""
    if input_data["tool_input"]["amount"] > REFUND_LIMIT:
        return pre_output("deny", "Importe por encima del límite.")
    return {}


strict_refund_guard = fail_closed(buggy_refund_guard)


# --------------------------------------------------------------------------
# P7 · Auditoría asíncrona (PostToolUse, producción)
# --------------------------------------------------------------------------


def make_audit_logger(path: Path):
    """Devuelve un hook que anota cada llamada sin hacer esperar al agente (solo logs y métricas)."""

    def _append(line: str) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    async def audit_tool_use(input_data, tool_use_id, context):
        record = {
            "tool": input_data["tool_name"],
            "tool_use_id": tool_use_id,  # el mismo id correlaciona Pre y Post de una llamada
            "duration_ms": input_data.get("duration_ms"),
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        asyncio.create_task(asyncio.to_thread(_append, json.dumps(record)))
        return {"async_": True, "asyncTimeout": 30000}  # no puede bloquear, reescribir ni añadir contexto

    return audit_tool_use


# --------------------------------------------------------------------------
# Registro: cómo se conectan al agente
# --------------------------------------------------------------------------


def build_options(
    mcp_servers: dict[str, Any],
    *,
    production: bool = False,
    max_budget_usd: float = 0.50,
    model: str | None = None,
    cli_path: str | None = None,
) -> ClaudeAgentOptions:
    """Opciones con los hooks de examen (E1, E2) y, con `production=True`, los de producción."""
    pre = [HookMatcher(matcher=REFUND_TOOL, hooks=[block_large_refund])]
    post = [HookMatcher(matcher="^mcp__", hooks=[normalize_mcp_output])]  # regex: cualquier herramienta MCP
    if production:
        pre += [
            HookMatcher(matcher="Write", hooks=[redirect_writes_to_sandbox]),
            HookMatcher(matcher="Write|Edit|Bash", hooks=[guard_protected_paths]),
            HookMatcher(matcher="^mcp__billing__", hooks=[allow_billing_tools, ask_mid_refunds]),
        ]
        post += [
            HookMatcher(matcher="mcp__crm__get_customer", hooks=[add_account_context]),
            HookMatcher(matcher="mcp__billing__get_order", hooks=[flag_incomplete_order]),
        ]
    return ClaudeAgentOptions(
        mcp_servers=mcp_servers,
        allowed_tools=[REFUND_TOOL, ESCALATE_TOOL, "mcp__billing__get_order", "mcp__crm__get_customer"],
        setting_sources=[],  # aislamiento: no cargar hooks de settings por accidente
        max_budget_usd=max_budget_usd,  # regla del proyecto: tope de gasto en toda ejecución con modelo
        model=model,
        cli_path=cli_path,
        hooks={"PreToolUse": pre, "PostToolUse": post},
    )


# --------------------------------------------------------------------------
# Demo con modelo: servidor MCP de prueba y llamada real a query()
# --------------------------------------------------------------------------


def _text_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Resultado de una herramienta MCP: un bloque de texto con JSON, como lo emite un servidor real."""
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool("process_refund", "Reembolsa un importe de un pedido.", {"order_id": str, "amount": float})
async def process_refund(args: dict[str, Any]) -> dict[str, Any]:
    return _text_result({"order_id": args["order_id"], "refunded": args["amount"], "status": 1, "processed_at": 1760000000})


@tool("escalate_to_human", "Deriva un caso a una persona.", {"order_id": str, "reason": str})
async def escalate_to_human(args: dict[str, Any]) -> dict[str, Any]:
    return _text_result({"ticket": "ESC-001", "order_id": args["order_id"], "status": 0, "created_ts": 1760000000})


@tool("get_order", "Consulta un pedido.", {"order_id": str})
async def get_order(args: dict[str, Any]) -> dict[str, Any]:
    # Formatos mezclados a propósito: Unix, ISO con zona, código de estado y una lista larga.
    return _text_result({
        "order_id": args["order_id"], "created_at": 1760000000, "updated_at": "2025-10-09T08:15:00+02:00",
        "status": 2, "items": [{"sku": f"SKU-{n:03d}", "qty": 1} for n in range(25)],
    })


@tool("get_customer", "Consulta un cliente.", {"customer_id": str})
async def get_customer(args: dict[str, Any]) -> dict[str, Any]:
    return _text_result({"customer_id": args["customer_id"], "currency": "EUR", "tier": "standard"})


def build_demo_servers() -> dict[str, Any]:
    """Dos servidores MCP en el propio proceso: producen los nombres `mcp__billing__*` y `mcp__crm__*`."""
    return {
        "billing": create_sdk_mcp_server("billing", tools=[process_refund, escalate_to_human, get_order]),
        "crm": create_sdk_mcp_server("crm", tools=[get_customer]),
    }


async def trace_pre(input_data, tool_use_id, context):
    """Solo observa: imprime lo que recibe `PreToolUse`. Devuelve `{}`, así que no decide nada."""
    print(f"  [PRE ] {tool_use_id} {input_data['tool_name']} tool_input={json.dumps(input_data['tool_input'])}")
    return {}


async def trace_post(input_data, tool_use_id, context):
    """Solo observa: imprime la forma real de `tool_response`. Devuelve `{}`."""
    print(f"  [POST] {tool_use_id} {input_data['tool_name']} tool_response={json.dumps(input_data.get('tool_response'), ensure_ascii=False)[:300]}")
    return {}


async def run_demo(prompt: str, *, model: str = "haiku", cli_path: str | None = None, max_budget_usd: float = 0.30) -> None:
    """Llama a `query()` con los hooks de examen y de producción y muestra qué ve el modelo."""
    options = build_options(build_demo_servers(), production=True, model=model, cli_path=cli_path, max_budget_usd=max_budget_usd)
    if cli_path:
        # Un lanzador de otra cuenta guarda su `apiKeyHelper` en los settings de usuario: con
        # `setting_sources=[]` no se cargan y la llamada falla con «Not logged in».
        options.setting_sources = ["user"]
    options.hooks["PreToolUse"].append(HookMatcher(hooks=[trace_pre]))  # sin matcher: todas las herramientas
    options.hooks["PostToolUse"].append(HookMatcher(hooks=[trace_post]))
    print(f"PROMPT: {prompt}")
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"  [MODELO pide] {block.name} {json.dumps(block.input)}")
                elif isinstance(block, TextBlock) and block.text.strip():
                    print(f"  [MODELO dice] {block.text.strip()}")
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):  # lo que llegó de vuelta al modelo tras los hooks
                    print(f"  [MODELO ve  ] error={block.is_error} content={json.dumps(block.content, ensure_ascii=False)[:400]}")
        elif isinstance(message, ResultMessage):
            print(f"  [FIN] stop_reason={message.stop_reason} coste=${message.total_cost_usd or 0:.4f} turnos={message.num_turns}")


# --------------------------------------------------------------------------
# Autocomprobación sin modelo
# --------------------------------------------------------------------------


def pre(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    return {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}


def post(tool_name: str, tool_response: Any, tool_input: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"hook_event_name": "PostToolUse", "tool_name": tool_name, "tool_input": tool_input or {}, "tool_response": tool_response, "duration_ms": 7}


def decision_of(output: dict[str, Any]) -> str | None:
    return output.get("hookSpecificOutput", {}).get("permissionDecision")


def run_shell_hook(mode: str, payload: dict[str, Any]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "hooks_escenarios_shell.py"), mode],
        input=json.dumps(payload), capture_output=True, text=True, check=False,
    )


async def self_check() -> None:
    # E1: solo se deniega por encima del límite; un importe ilegible o NaN falla en cerrado.
    out = await block_large_refund(pre(REFUND_TOOL, {"order_id": "A1", "amount": 750}), "t1", None)
    assert decision_of(out) == "deny" and ESCALATE_TOOL in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert await block_large_refund(pre(REFUND_TOOL, {"amount": 500}), "t2", None) == {}
    assert await block_large_refund(pre(REFUND_TOOL, {"amount": 80.5}), "t3", None) == {}
    assert decision_of(await block_large_refund(pre(REFUND_TOOL, {"amount": "mucho"}), "t4", None)) == "deny"
    assert decision_of(await block_large_refund(pre(REFUND_TOOL, {"amount": "nan"}), "t5", None)) == "deny"
    assert await block_large_refund(pre("mcp__crm__get_customer", {"amount": 9999}), "t6", None) == {}
    print("OK E1 reembolso > 500: deny + redirección")

    # E2: tres formas de tool_response, misma normalización; la forma de salida se conserva.
    raw = {"created_at": 1760000000, "updated_at": "2025-10-09T08:15:00+02:00", "status": 2, "name": "Ana"}
    expected = {"created_at": "2025-10-09T08:53:20Z", "updated_at": "2025-10-09T06:15:00Z", "status": "delivered", "name": "Ana"}
    for shape in (raw, json.dumps(raw), [{"type": "text", "text": json.dumps(raw)}], {"content": [{"type": "text", "text": json.dumps(raw)}]}):
        out = await normalize_mcp_output(post("mcp__crm__get_order", shape), "t7", None)
        replaced = out["hookSpecificOutput"]["updatedToolOutput"]
        assert type(replaced) is type(shape), (type(replaced), type(shape))
        data, _ = unwrap_response(replaced)
        assert data == expected, data
    ms = await normalize_mcp_output(post("mcp__x__y", {"sent_at": 1760000000000, "status": 9}), "t8", None)
    assert ms["hookSpecificOutput"]["updatedToolOutput"] == {"sent_at": "2025-10-09T08:53:20Z", "status": 9}  # ms y código desconocido
    big = {"items": list(range(25)), "created_at": 1760000000}
    out = (await normalize_mcp_output(post("mcp__x__y", big), "t9", None))["hookSpecificOutput"]["updatedToolOutput"]
    assert len(out["items"]) == MAX_ITEMS and out["items_omitted"] == 5 and out["created_at"].endswith("Z")  # truncar y normalizar en un hook
    assert await normalize_mcp_output(post("mcp__x__y", {"created_at": "2025-10-09T06:15:00Z", "status": "ok"}), "t10", None) == {}
    assert await normalize_mcp_output(post("mcp__x__y", "texto libre, no JSON"), "t11", None) == {}
    print("OK E2 normalización: updatedToolOutput con la misma forma")

    # P1: reescribe el input entero, no se escapa con `..` y no reescribe dos veces.
    out = await redirect_writes_to_sandbox(pre("Write", {"file_path": "/etc/app.conf", "content": "x"}), "t12", None)
    new = out["hookSpecificOutput"]["updatedInput"]
    assert new == {"file_path": f"{SANDBOX_ROOT}/etc/app.conf", "content": "x"} and decision_of(out) == "allow"
    assert decision_of(await redirect_writes_to_sandbox(pre("Write", {"file_path": "../../etc/passwd"}), "t13", None)) == "deny"
    assert await redirect_writes_to_sandbox(pre("Write", {"file_path": f"{SANDBOX_ROOT}/a.txt"}), "t14", None) == {}
    print("OK P1 updatedInput: input entero, sin escape ni doble reescritura")

    # P2: un allow amplio no gana al deny; ask/defer; precedencia deny > defer > ask > allow.
    call = pre(REFUND_TOOL, {"amount": 900})
    outs = [await h(call, "t15", None) for h in (allow_billing_tools, block_large_refund)]
    assert most_restrictive(outs) == "deny"
    mid = pre(REFUND_TOOL, {"amount": 300})
    outs = [await h(mid, "t16", None) for h in (allow_billing_tools, ask_mid_refunds)]
    assert most_restrictive(outs) == "ask"
    outs.append(await defer_refund_for_approval(mid, "t17", None))
    assert most_restrictive(outs) == "defer" and most_restrictive([{}]) is None
    print("OK P2 permissionDecision: deny > defer > ask > allow")

    # P3 y P4: contexto adicional frente a feedback con decision.
    ctx = await add_account_context(post("mcp__crm__get_customer", {"currency": "EUR"}), "t18", None)
    assert "EUR" in ctx["hookSpecificOutput"]["additionalContext"] and "updatedToolOutput" not in ctx["hookSpecificOutput"]
    flag = await flag_incomplete_order(post("mcp__billing__get_order", {"status": "ok"}), "t19", None)
    assert flag["decision"] == "block" and "hookSpecificOutput" not in flag  # nivel superior, y sin updatedToolOutput
    assert await flag_incomplete_order(post("mcp__billing__get_order", {"order_id": "A1"}), "t20", None) == {}
    print("OK P3/P4 additionalContext y decision block (solo feedback)")

    # P5: ruta dentro del hook y la vía Bash.
    for tool, tool_input, blocked in (
        ("Write", {"file_path": "/app/.env"}, True), ("Edit", {"file_path": "C:\\app\\.ENV.local"}, True),
        ("Write", {"file_path": "/app/.env.example"}, False), ("Write", {"file_path": "/app/.venv/x"}, False),
        ("Bash", {"command": "echo KEY=1 > .env"}, True), ("Bash", {"command": "ls -la"}, False),
    ):
        assert (decision_of(await guard_protected_paths(pre(tool, tool_input), "t21", None)) == "deny") is blocked, (tool, tool_input)
    print("OK P5 filtro por ruta dentro del hook, incluida la vía Bash")

    # P6: el guard con bugs falla en cerrado; sin el envoltorio, el error se propaga.
    for bad in ({}, {"amount": "900"}):
        assert decision_of(await strict_refund_guard(pre(REFUND_TOOL, bad), "t22", None)) == "deny"
    assert await strict_refund_guard(pre(REFUND_TOOL, {"amount": 10}), "t23", None) == {}
    try:
        await buggy_refund_guard(pre(REFUND_TOOL, {}), "t24", None)
        raise AssertionError("debía lanzar KeyError")
    except KeyError:
        pass
    print("OK P6 fail_closed: error o ausencia de decisión = deny")

    # P7: devuelve async de inmediato y el registro se escribe en segundo plano.
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "audit.jsonl"
        out = await make_audit_logger(log)(post("mcp__billing__get_order", {}), "toolu_9", None)
        assert out == {"async_": True, "asyncTimeout": 30000}
        await asyncio.sleep(0.3)
        record = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        assert record["tool"] == "mcp__billing__get_order" and record["tool_use_id"] == "toolu_9"
    print("OK P7 async: registra sin esperar")

    # S1: hook de comando; el código de salida decide, y el 1 NO bloquea.
    rm = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "rm -rf /var/data"}}
    ls = {**rm, "tool_input": {"command": "ls"}}
    proc = run_shell_hook("exit2", rm)
    assert proc.returncode == 2 and "rm -rf" in proc.stderr
    assert run_shell_hook("exit2", ls).returncode == 0
    proc = run_shell_hook("json", rm)
    assert proc.returncode == 0 and json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert run_shell_hook("exit1", rm).returncode == 1  # error NO bloqueante: la llamada pasaría
    assert run_shell_hook("exit2", {}).returncode == 2  # entrada ilegible: falla en cerrado
    failed = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {}, "tool_response": {"stdout": "2 FAILED"}}
    assert run_shell_hook("post-exit2", failed).returncode == 2
    print("OK S1 hooks de comando: exit 2 bloquea, exit 1 no")

    # Registro: las opciones se construyen con los campos que admite la versión fijada del SDK.
    options = build_options({}, production=True)
    assert options.max_budget_usd == 0.50 and options.setting_sources == [] and set(options.hooks) == {"PreToolUse", "PostToolUse"}
    print("OK Registro: ClaudeAgentOptions válido con max_budget_usd")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", metavar="PROMPT", help="llamada real con query() (gasta tokens; tope 0.30 USD)")
    parser.add_argument("--model", default="haiku")
    args = parser.parse_args()
    if args.demo:
        asyncio.run(run_demo(args.demo, model=args.model, cli_path=os.environ.get("HOOKS_DEMO_CLI")))
    else:
        asyncio.run(self_check())
        print("Todos los escenarios pasan (sin llamar al modelo).")
