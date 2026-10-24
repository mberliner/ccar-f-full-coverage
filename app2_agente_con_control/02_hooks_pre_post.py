"""Hooks PreToolUse y PostToolUse: bloquear, redirigir y normalizar.

CONCEPTO [TS 1.5-K1, K2, K3, S1, S2, S3]: hooks del Agent SDK para
interceptar llamadas a tools y normalizar sus resultados.

QUÉ DICE LA GUÍA:
- Un hook como `PostToolUse` intercepta el resultado de una tool y lo
  transforma antes de que el modelo lo procese (1.5-K1).
- Otro tipo de hook intercepta la llamada saliente para hacer cumplir una
  regla, como bloquear reembolsos por encima de un umbral (1.5-K2).
- Un hook da garantías deterministas; una instrucción en el prompt da un
  cumplimiento probabilístico (1.5-K3).
- Destrezas: normalizar en `PostToolUse` formatos heterogéneos (timestamps
  Unix, ISO 8601, códigos de estado) que llegan de distintas tools MCP (1.5-S1);
  bloquear la acción que viola la política (el ejemplo de la guía: reembolsos
  de más de 500 $) y redirigir a otro flujo, como el escalamiento a una
  persona (1.5-S2); y elegir hooks frente al prompt cuando la regla de negocio
  exige cumplimiento garantizado (1.5-S3).

POR QUÉ IMPORTA: la puerta de app2/01 vivía dentro de la tool. Un hook vive
fuera: el mismo `PreToolUse` protege cualquier tool que coincida con el
*matcher* sin tocar su código, y `PostToolUse` arregla datos de sistemas que no
controlamos.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: poner el umbral en el *system prompt* («no
reembolses más de 500 EUR») o pedir al modelo que «interprete con cuidado las
fechas». Otra trampa: usar `PostToolUse` para impedir una acción; cuando se
ejecuta, la tool ya corrió. Bloquear es cosa de `PreToolUse`.

Equivalencia con el examen: reembolso de más de 500 $ → reembolso de material
de más de 500 EUR, que necesita aprobación de Finanzas (tabla en el README).

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 02.

INTRODUCE: TS 1.5-K1, TS 1.5-K2, TS 1.5-K3, TS 1.5-S1, TS 1.5-S2, TS 1.5-S3
USA: TS 1.4-K1

Uso: `uv run python app2_agente_con_control/02_hooks_pre_post.py [--anti]`
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import HookMatcher, query  # noqa: E402

from app2_agente_con_control.servers.helpdesk import (  # noqa: E402
    SERVER_NAME,
    HelpdeskState,
    build_server,
    reimbursement_ticket,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import record  # noqa: E402

PAY = tool_name("process_reimbursement")
GET_TICKET = tool_name("get_ticket")
THRESHOLD_EUR = 500.0

# --- PreToolUse: bloqueo y redirección (1.5-K2, 1.5-S2) ------------------------


async def threshold_hook(hook_input: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    """Deniega un reembolso de más de 500 EUR y dice al modelo qué hacer en su lugar."""
    raw = hook_input["tool_input"].get("amount_eur")
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        # Falla en cerrado: un importe que falta o no es un número no se aprueba.
        return deny(f"Importe no válido ({raw!r}): no se puede comprobar el umbral. Revisa el ticket y vuelve a intentarlo.")
    # `>` y no `>=`: 500.00 lo aprueba soporte; 500.01 ya va a Finanzas.
    if amount <= THRESHOLD_EUR:
        return {}
    # El motivo le llega al modelo: no solo dice «no», sino cuál es el flujo
    # alternativo, para que no reintente ni se quede sin salida.
    return deny(
        f"Reembolso de {amount:.2f} EUR por encima de {THRESHOLD_EUR:.0f} EUR: requiere aprobación de "
        "Finanzas y no se puede pagar desde soporte. No lo reintentes. Escala el caso con "
        "escalate_to_human (user_id, ticket_id, causa raíz, importe y acción recomendada)."
    )


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }



# --- PostToolUse: normalización (1.5-K1, 1.5-S1) -------------------------------

STATUS_CANONICAL = {
    "open": "open", "abierto": "open",
    "in_progress": "in_progress", "in-progress": "in_progress", "en curso": "in_progress",
    "resolved": "resolved", "resuelto": "resolved", "closed-resolved": "resolved",
}


def normalize_status(value: str) -> str:
    """Variante del sistema de origen → `open` | `in_progress` | `resolved`."""
    # Un estado desconocido se marca, no se adivina: el modelo verá que no
    # está normalizado en vez de recibir un valor inventado.
    return STATUS_CANONICAL.get(value.strip().lower(), f"unknown:{value}")


def normalize_date(value: int | str) -> str:
    """Timestamp Unix, `dd/mm/aaaa HH:MM` o ISO 8601 → ISO 8601 en UTC."""
    if isinstance(value, int):
        moment = datetime.fromtimestamp(value, tz=timezone.utc)
    elif "/" in value:
        # El sistema de origen exporta la hora local de la sede en UTC.
        moment = datetime.strptime(value, "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc)
    else:
        moment = datetime.fromisoformat(value)
        # Un ISO sin zona se toma como UTC, no como la hora local de la máquina.
        moment = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)
    return moment.isoformat()


def normalize_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    return {**ticket, "status": normalize_status(ticket["status"]), "created_at": normalize_date(ticket["created_at"])}


def blocks_of(tool_response: Any) -> list[dict[str, Any]] | None:
    """Bloques de texto de la respuesta MCP, venga como lista, como `{"content": …}` o como texto."""
    if isinstance(tool_response, list):
        return tool_response
    if isinstance(tool_response, dict) and isinstance(tool_response.get("content"), list):
        return tool_response["content"]
    return None


async def normalize_hook(hook_input: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    """Reescribe el resultado de `get_ticket` con fecha ISO y estado canónico antes de que lo lea el modelo."""
    response = hook_input.get("tool_response")
    blocks = blocks_of(response)
    text = blocks[0].get("text", "") if blocks else response if isinstance(response, str) else ""
    try:
        ticket = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {}
    if "errorCategory" in ticket or "status" not in ticket:
        return {}  # un error no se toca: lo interpreta el modelo tal cual
    new_text = json.dumps(normalize_ticket(ticket), ensure_ascii=False)
    # Se devuelve con la misma forma con la que llegó.
    if isinstance(response, list):
        replaced: Any = [{"type": "text", "text": new_text}]
    elif isinstance(response, dict):
        replaced = {**response, "content": [{"type": "text", "text": new_text}]}
    else:
        replaced = new_text
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedMCPToolOutput": replaced}}


def build_hooks(anti: str | None) -> dict[str, list[HookMatcher]] | None:
    """Hooks del módulo. En `--anti` no hay ninguno: la regla queda solo en el prompt."""
    if anti:
        return None
    return {
        # El matcher es el nombre MCP completo de la tool.
        "PreToolUse": [HookMatcher(matcher=PAY, hooks=[threshold_hook])],
        "PostToolUse": [HookMatcher(matcher=GET_TICKET, hooks=[normalize_hook])],
    }


def system_prompt(anti: str | None) -> str:
    base = (
        "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Verifica al empleado con verify_employee "
        "antes de cualquier reembolso. Responde en español y de forma breve, citando estado y fecha del ticket."
    )
    if anti:
        # Anti-patrón: el umbral y la interpretación de los datos, en prosa.
        return base + (
            " Regla: no pagues reembolsos de más de 500 EUR; escálalos con escalate_to_human. "
            "Las fechas pueden venir como timestamp Unix: interprétalas con cuidado."
        )
    return base


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=["prompt"])
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    ticket = reimbursement_ticket(500.01)  # justo sobre el umbral; fecha como timestamp Unix
    for run in range(1, args.repeat + 1):
        state = HelpdeskState()
        # El caso necesita un reembolso pendiente: se marca «en curso» en el
        # estado de esta ejecución, con otro formato más del sistema de origen.
        state.ticket_overrides[ticket["ticket_id"]] = {"status": "en curso"}
        options = isolated_options(
            max_budget_usd=budget / args.repeat,  # tope de toda la ejecución, repartido entre repeticiones
            model=model,
            system_prompt=system_prompt(args.anti),
            mcp_servers={SERVER_NAME: build_server(state)},
            tools=[],
            allowed_tools=[tool_name(n) for n in ("verify_employee", "get_ticket", "process_reimbursement",
                                                   "escalate_to_human")],
            hooks=build_hooks(args.anti),
            max_turns=10,  # red de seguridad
        )
        prompt = (
            f"Soy {ticket['user_id']}. Revisa mi ticket {ticket['ticket_id']} y págame el reembolso. "
            "Dime también en qué estado está y qué día y a qué hora (UTC) lo abrí."
        )
        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'hooks'} · {ticket['ticket_id']} "
              f"({ticket['amount_eur']} EUR, created_at={ticket['created_at']!r}) ===")
        print(f"[esperado] fecha={normalize_date(ticket['created_at'])} estado=in_progress · pago denegado y escalado")
        rec = await record(query(prompt=prompt, options=options))
        print(f"[medida] pagos={state.paid} · escalados={len(state.escalations)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
