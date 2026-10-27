"""Barrera del coordinador de app3: las tools del servidor son de los subagentes.

PROPÓSITO: un hook `PreToolUse` que deniega al agente principal las tools del
servidor `investigacion` y deja pasar a los subagentes, y la medida de cuántas
veces lo intentó el coordinador. Lo usan `01_coordinador`, `02_paralelo_y_descomposicion`
y `03_tools_entre_roles`.

POR QUÉ EXISTE: `tools=["Agent"]` solo limita las tools integradas; las del
servidor MCP siguen visibles para el coordinador, y como están pre-aprobadas
para los subagentes, «no busques tú» en su prompt es una petición, no una
barrera. Comprobado en app3/03 (revisión independiente de la entrega 2): sin el
hook, el coordinador las usó cuando se le pidió expresamente. Sin barrera, las
medidas de delegación mezclarían su trabajo con el de los subagentes. Los
módulos numerados no se pueden importar entre sí, así que la pieza vive aquí.

EN PRODUCCIÓN (no evaluable): que el subagente traiga `agent_id` en la entrada
del hook y el agente principal no, y el alcance de `tools`, son comportamiento
del SDK y de la CLI, no algo que diga la guía.

QUÉ NO HACE: no cambia lo que ve el coordinador (sigue viendo las tools) ni el
servidor; solo deniega la llamada y le dice que delegue.
"""

from typing import Any

from claude_agent_sdk import HookMatcher

from app3_sistema_multiagente.servers.investigacion import SERVER_NAME
from harness.recorder import MAIN, RunRecord

SERVER_PREFIX = f"mcp__{SERVER_NAME}__"


async def coordinator_gate(hook_input: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    """Deniega al agente principal las tools del servidor: son de los subagentes."""
    # Un subagente trae `agent_id` en la entrada del hook; el agente principal, no.
    if hook_input.get("agent_id"):
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "El coordinador no usa las tools de investigación: son de los subagentes. "
                "Delega con Agent en el subagente que corresponda."
            ),
        }
    }


def coordinator_hooks() -> dict[str, list[HookMatcher]]:
    # El matcher casa con cualquier tool del servidor `investigacion`.
    return {"PreToolUse": [HookMatcher(matcher=f"{SERVER_PREFIX}.*", hooks=[coordinator_gate])]}


def coordinator_attempts(rec: RunRecord) -> int:
    """Intentos del agente principal de usar tools del servidor (los deniega `coordinator_gate`)."""
    return sum(1 for c in rec.tool_calls if c.agent == MAIN and c.name.startswith(SERVER_PREFIX))
