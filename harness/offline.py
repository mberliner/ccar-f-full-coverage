"""Pruebas sin modelo de hooks y tools del SDK (roadmap §5 y §11.2).

PROPÓSITO: invocar un hook con los mismos argumentos que le pasa el SDK y leer
su decisión o su salida reemplazada, y ejecutar el handler de una tool del SDK
devolviendo primero si falló y luego su contenido.

POR QUÉ EXISTE: la lógica de un hook (bloquear, redirigir, normalizar) y la de
un error estructurado es determinista y se puede probar con `pytest` sin coste
ni variabilidad. Solo la reacción del modelo necesita una ejecución real.

QUÉ NO HACE: no valida la entrada contra el `input_schema` (el SDK lo hace
antes de llamar al handler) ni evalúa el `matcher` de `HookMatcher`: prueba la
función, no su registro. Es síncrono, pensado para `pytest` sin plugin async.
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import HookCallback, SdkMcpTool


@dataclass
class HookResult:
    decision: str | None  # permissionDecision de PreToolUse, o "block" de PostToolUse
    reason: str | None
    updated_input: dict[str, Any] | None  # entrada reescrita (PreToolUse)
    replaced_output: Any  # salida reemplazada (PostToolUse)
    raw: dict[str, Any]


@dataclass
class ToolOutcome:
    is_error: bool
    content: list[dict[str, Any]]
    text: str  # bloques de texto concatenados, listo para json.loads


def run_hook(
    callback: HookCallback,
    event: str,
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    tool_response: Any = None,
    agent_id: str | None = None,
    cwd: str = ".",
) -> HookResult:
    """Llama al hook como lo haría el SDK en `PreToolUse` o `PostToolUse`."""
    tool_use_id = f"toolu_offline_{uuid.uuid4().hex[:8]}"
    # Mismos campos que PreToolUseHookInput / PostToolUseHookInput.
    hook_input: dict[str, Any] = {
        "session_id": "offline",
        "transcript_path": "",
        "cwd": cwd,
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_use_id": tool_use_id,
    }
    if event == "PostToolUse":
        hook_input["tool_response"] = tool_response
    # Solo aparece cuando la llamada la hace un subagente.
    if agent_id:
        hook_input["agent_id"] = agent_id

    raw = asyncio.run(callback(hook_input, tool_use_id, {"signal": None})) or {}
    specific = raw.get("hookSpecificOutput", {})
    return HookResult(
        decision=specific.get("permissionDecision") or raw.get("decision"),
        reason=specific.get("permissionDecisionReason") or raw.get("reason"),
        updated_input=specific.get("updatedInput"),
        # El SDK acepta las dos claves; updatedMCPToolOutput solo vale para tools MCP.
        replaced_output=specific.get("updatedToolOutput", specific.get("updatedMCPToolOutput")),
        raw=raw,
    )


def call_tool(sdk_tool: SdkMcpTool[Any], args: dict[str, Any]) -> ToolOutcome:
    """Ejecuta el handler de una tool creada con `@tool`."""
    try:
        result = asyncio.run(sdk_tool.handler(args))
    except Exception as exc:  # noqa: BLE001
        # El SDK reporta una excepción del handler como resultado con error:
        # aquí se reproduce para que el test vea lo mismo que el modelo.
        result = {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "is_error": True}
    content = result.get("content", [])
    text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
    return ToolOutcome(is_error=bool(result.get("is_error")), content=content, text=text)
