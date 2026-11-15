"""Resultados de tools MCP y decisiones de hooks, con la forma que usan los módulos.

PROPÓSITO: `ok` y `error` envuelven datos como resultado de tool (el error con `errorCategory` e
`isRetryable`); `deny` es la decisión de un hook PreToolUse que deniega con su motivo.

POR QUÉ EXISTE: las copias de `mesa.py`, `helpdesk.py`, `investigacion.py` y de los hooks de app2 eran
idénticas y podían derivar por separado.

QUÉ NO HACE: no decide cuándo fallar ni qué categoría usar, y no incluye el error genérico sin
metadatos (`mesa.generic_error`), que es un anti-patrón deliberado de un módulo.
"""

import json
from typing import Any


def ok(data: Any) -> dict[str, Any]:
    """Resultado correcto: los datos como texto JSON, conservando los acentos."""
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def error(category: str, message: str, *, retryable: bool = False, **extra: Any) -> dict[str, Any]:
    """Error como resultado con metadatos estructurados (regla mcp-servers.md)."""
    data = {"errorCategory": category, "isRetryable": retryable, "message": message, **extra}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def deny(reason: str) -> dict[str, Any]:
    """Decisión de un hook PreToolUse que deniega la llamada y explica por qué."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
