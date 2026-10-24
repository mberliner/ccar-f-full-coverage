"""Servidor MCP en proceso de la mesa de ayuda (app2).

PROPÓSITO: dar al agente de app2 las tools de la mesa de ayuda sobre los datos
sintéticos: verificar a un empleado, leer y listar tickets, buscar en la base
de conocimiento, procesar un reembolso y escalar a una persona.

POR QUÉ EXISTE: los módulos 01, 02, 03, 05 y 06 enseñan control del agente
sobre las mismas tools. Equivalencias con el vocabulario del examen en
`app2_agente_con_control/README.md`: `verify_employee` ≈ `get_customer`,
`process_reimbursement` ≈ `process_refund`.

QUÉ NO HACE: no normaliza fechas ni estados (los devuelve tal como vienen del
sistema de origen; lo hace el hook de app2/02), no aplica el umbral de 500 EUR
(lo aplica el hook) y no guarda nada entre ejecuciones: el estado de sesión
vive en `HelpdeskState`, uno por ejecución.

USA: TS 1.4-K1, TS 1.4-S1
"""

import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from harness.data import load

SERVER_NAME = "helpdesk"


def tool_name(name: str) -> str:
    """Nombre con el que el agente ve la tool: `mcp__<servidor>__<tool>`."""
    return f"mcp__{SERVER_NAME}__{name}"


HANDOFF_FIELDS = ["user_id", "ticket_id", "root_cause", "amount_eur", "recommended_action"]


@dataclass
class HelpdeskState:
    """Estado de una ejecución. Los overrides simulan cambios entre fases (app2/06)."""

    verified: set[str] = field(default_factory=set)
    paid: list[dict[str, Any]] = field(default_factory=list)
    escalations: list[dict[str, Any]] = field(default_factory=list)
    ticket_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    kb_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


def ok(data: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def error(category: str, message: str, *, retryable: bool = False, **extra: Any) -> dict[str, Any]:
    # Error como resultado con metadatos estructurados (regla mcp-servers.md),
    # nunca como excepción: el modelo debe poder razonar sobre la causa.
    data = {"errorCategory": category, "isRetryable": retryable, "message": message, **extra}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def find_ticket(state: HelpdeskState, ticket_id: str) -> dict[str, Any] | None:
    ticket = next((t for t in load("tickets.json") if t["ticket_id"] == ticket_id), None)
    return {**ticket, **state.ticket_overrides.get(ticket_id, {})} if ticket else None


def reimbursement_ticket(amount: float) -> dict[str, Any]:
    """El ticket de reembolso de ese importe (los datos cubren 120, 500, 500.01…)."""
    return next(t for t in load("tickets.json") if t["amount_eur"] == amount)


def make_tools(state: HelpdeskState, *, gate: bool = True, handoff: str = "structured") -> list[SdkMcpTool[Any]]:
    """Tools del servidor. `gate=False` quita la puerta programática (anti de app2/01);
    `handoff="free_text"` cambia el escalamiento a texto libre (anti de app2/05)."""

    @tool(
        "verify_employee",
        "Verifica la identidad de un empleado por su ID exacto (EMP-NNNN) y la deja verificada en esta "
        "sesión. Es el paso previo obligatorio a cualquier operación económica. No busca por nombre.",
        {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]},
    )
    async def verify_employee(args: dict[str, Any]) -> dict[str, Any]:
        user = next((u for u in load("usuarios.json") if u["user_id"] == args["user_id"]), None)
        if user is None:
            return error("not_found", f"no existe el empleado {args['user_id']}")
        state.verified.add(user["user_id"])
        return ok({"verified": True, "user_id": user["user_id"], "name": user["name"], "department": user["department"]})

    @tool(
        "get_ticket",
        "Devuelve un ticket por su ID (TCK-NNNN) tal como lo guarda el sistema de origen: estado y fecha "
        "pueden venir en formatos distintos. Para ver todos los tickets de un empleado, usa list_employee_tickets.",
        {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]},
    )
    async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
        ticket = find_ticket(state, args["ticket_id"])
        return ok(ticket) if ticket else error("not_found", f"no existe el ticket {args['ticket_id']}")

    @tool(
        "list_employee_tickets",
        "Lista los tickets de un empleado por su ID (EMP-NNNN), con ID, categoría, estado y descripción. "
        "Para el detalle de un ticket concreto, usa get_ticket.",
        {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]},
    )
    async def list_employee_tickets(args: dict[str, Any]) -> dict[str, Any]:
        ids = [t["ticket_id"] for t in load("tickets.json") if t["user_id"] == args["user_id"]]
        tickets = [find_ticket(state, tid) for tid in ids]
        keep = ("ticket_id", "category", "status", "description", "amount_eur")
        return ok({"user_id": args["user_id"], "tickets": [{k: t[k] for k in keep} for t in tickets]})

    @tool(
        "search_kb",
        "Busca artículos de la base de conocimiento por palabras clave. Devuelve hasta 3 con ID, título, "
        "resumen, fecha de actualización y, si está obsoleto, `superseded_by` u `obsolete`.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    async def search_kb(args: dict[str, Any]) -> dict[str, Any]:
        words = {w for w in args["query"].lower().split() if len(w) > 3}
        articles = [{**a, **state.kb_overrides.get(a["article_id"], {})} for a in load("articulos_kb.json")]

        def score(article: dict[str, Any]) -> int:
            haystack = f"{article['title']} {article['body']}".lower()
            return sum(word in haystack for word in words)

        ranked = sorted((a for a in articles if score(a)), key=score, reverse=True)[:3]
        return ok({"articles": [{k: v for k, v in a.items() if k != "category"} for a in ranked]})

    @tool(
        "process_reimbursement",
        "Paga el reembolso de un ticket de gastos al empleado. Requiere que verify_employee haya verificado "
        "antes a ese empleado en esta sesión, y que el importe coincida con el del ticket.",
        {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "ticket_id": {"type": "string"},
                "amount_eur": {"type": "number"},
            },
            "required": ["user_id", "ticket_id", "amount_eur"],
        },
    )
    async def process_reimbursement(args: dict[str, Any]) -> dict[str, Any]:
        verified = args["user_id"] in state.verified
        # Puerta programática (prerrequisito): sin verificación previa, la
        # operación no se ejecuta, diga lo que diga el prompt.
        if gate and not verified:
            return error("prerequisite", "empleado no verificado: llama antes a verify_employee", user_id=args["user_id"])
        ticket = find_ticket(state, args["ticket_id"])
        if ticket is None or ticket["user_id"] != args["user_id"] or ticket["amount_eur"] != args["amount_eur"]:
            return error("validation", "el ticket no existe, no es de ese empleado o el importe no coincide")
        state.paid.append({**args, "verified": verified})
        return ok({"paid": True, **args})

    if handoff == "free_text":

        @tool(
            "escalate_to_human",
            "Pasa el caso a una persona del equipo de soporte con un resumen en texto libre.",
            {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
        )
        async def escalate_to_human(args: dict[str, Any]) -> dict[str, Any]:
            state.escalations.append(dict(args))
            return ok({"escalated": True})

    else:

        @tool(
            "escalate_to_human",
            "Pasa el caso a una persona del equipo de soporte, que no ve esta conversación. Todos los campos "
            "son obligatorios: ID del empleado, ticket, causa raíz, importe en EUR (0 si no hay) y acción recomendada.",
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "ticket_id": {"type": "string"},
                    "root_cause": {"type": "string"},
                    "amount_eur": {"type": "number"},
                    "recommended_action": {"type": "string"},
                },
                "required": HANDOFF_FIELDS,
            },
        )
        async def escalate_to_human(args: dict[str, Any]) -> dict[str, Any]:
            # El SDK valida el schema antes del handler, pero un campo vacío
            # pasaría: la persona que recibe el caso no tendría el dato.
            missing = [f for f in HANDOFF_FIELDS if args.get(f) in (None, "")]
            if missing:
                return error("validation", "handoff incompleto", missing=missing)
            state.escalations.append(dict(args))
            return ok({"escalated": True, "ticket_id": args["ticket_id"]})

    return [verify_employee, get_ticket, list_employee_tickets, search_kb, process_reimbursement, escalate_to_human]


def build_server(state: HelpdeskState, **kwargs: Any) -> Any:
    """Configuración `McpSdkServerConfig` para `ClaudeAgentOptions(mcp_servers={SERVER_NAME: …})`."""
    return create_sdk_mcp_server(SERVER_NAME, tools=make_tools(state, **kwargs))
