"""Servidor MCP en proceso de la mesa de ayuda (app1): familias de tools.

PROPÓSITO: ofrecer, sobre los datos sintéticos, las familias de tools que cada
módulo de app1 monta según lo que enseña. `make_tools(familia, ...)` devuelve
solo la familia pedida:
  - `routing` (app1/03): tools divididas con descripciones completas, o
    `variante="minimas"` con dos tools solapadas de una línea.
  - `errores` (app1/04): cinco tools que fallan de cuatro formas distintas más
    una búsqueda sin coincidencias; `estructurado=False` y `fallo_como_vacio`
    producen las variantes anti-patrón.
  - `amplio` / `acotado` (app1/05): 18 tools (varias casi iguales) frente a 5.

POR QUÉ EXISTE: el servidor es el mismo y cambia la configuración, así que la
diferencia que mide cada módulo (acierto de enrutamiento, reintentos, tools por
agente) sale de las descripciones y de los errores, no de datos distintos.

QUÉ NO HACE: no tiene estado salvo `ErroresState` (cuenta las llamadas para
que el transitorio falle solo la primera vez) y no escribe nada: los datos se
leen de `datos/sinteticos/`. No lleva marcadores `INTRODUCE` (los llevan los
módulos). Los errores usan `errorCategory`/`isRetryable` (ver TS 2.2-K1); su
marcador `USA` se añade con el módulo que lo introduce.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from harness.data import load

SERVER_NAME = "mesa"
LICENSE_QUOTA = 10  # cupo de puestos por licencia (regla de negocio de `errores`)
USER_ID_PATTERN = re.compile(r"^EMP-\d{4}$")

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def tool_name(name: str) -> str:
    return f"mcp__{SERVER_NAME}__{name}"


def ok(data: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def error(category: str, message: str, *, retryable: bool = False, **extra: Any) -> dict[str, Any]:
    # Error como resultado con metadatos estructurados (regla mcp-servers.md).
    data = {"errorCategory": category, "isRetryable": retryable, "message": message, **extra}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def generic_error() -> dict[str, Any]:
    # Anti-patrón: el mismo texto para cualquier fallo, sin categoría ni pista de reintento.
    return {"content": [{"type": "text", "text": "Operation failed"}], "is_error": True}


@dataclass
class ErroresState:
    """Cuenta las llamadas por tool, para que el transitorio falle solo la primera vez."""

    calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))


def words_of(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def find_ticket(ticket_id: str) -> dict | None:
    return next((t for t in load("tickets.json") if t["ticket_id"] == ticket_id), None)


def find_article(article_id: str) -> dict | None:
    return next((a for a in load("articulos_kb.json") if a["article_id"] == article_id), None)


def not_found(kind: str, value: str) -> dict[str, Any]:
    return error("validation", f"{kind} no encontrado: {value}", retryable=False, input=value)


def make(name: str, description: str, properties: dict[str, str], handler: Handler) -> SdkMcpTool[Any]:
    """Crea una tool con entrada de campos de texto, todos obligatorios."""
    schema = {
        "type": "object",
        "properties": {key: {"type": "string", "description": text} for key, text in properties.items()},
        "required": list(properties),
    }
    return tool(name, description, schema)(handler)


# --- routing (app1/03) ------------------------------------------------------

def routing_tools(variante: str | None) -> list[SdkMcpTool[Any]]:
    if variante == "minimas":
        async def analyze(args: dict[str, Any]) -> dict[str, Any]:
            value = args.get("content_id") or args.get("document_id") or ""
            record = find_ticket(value) or find_article(value)
            return ok(record) if record else not_found("contenido", value)

        # Descripciones de una línea y solapadas: el modelo no tiene con qué elegir.
        return [
            make("analyze_content", "Analiza contenido.", {"content_id": "ID del contenido"}, analyze),
            make("analyze_document", "Analiza un documento.", {"document_id": "ID del documento"}, analyze),
        ]

    async def extract_ticket_facts(args: dict[str, Any]) -> dict[str, Any]:
        ticket = find_ticket(args["ticket_id"])
        if ticket is None:
            return not_found("ticket", args["ticket_id"])
        keys = ("ticket_id", "user_id", "category", "status", "created_at", "amount_eur", "description")
        return ok({k: ticket[k] for k in keys})

    async def extract_article_steps(args: dict[str, Any]) -> dict[str, Any]:
        article = find_article(args["article_id"])
        if article is None:
            return not_found("artículo", args["article_id"])
        steps = [s.strip().rstrip(".") for s in re.split(r"(?<=[.;])\s+", article["body"]) if s.strip()]
        return ok({"article_id": article["article_id"], "title": article["title"], "steps": steps})

    async def summarize_article(args: dict[str, Any]) -> dict[str, Any]:
        article = find_article(args["article_id"])
        if article is None:
            return not_found("artículo", args["article_id"])
        first = re.split(r"(?<=[.;])\s+", article["body"])[0]
        return ok({"article_id": article["article_id"], "title": article["title"], "summary": first})

    async def verify_claim(args: dict[str, Any]) -> dict[str, Any]:
        article = find_article(args["article_id"])
        if article is None:
            return not_found("artículo", args["article_id"])
        text = set(words_of(f"{article['title']} {article['body']}"))
        claim_words = [w for w in words_of(args["claim"]) if len(w) >= 4]
        hits = [w for w in claim_words if w in text]
        # Heurística de palabras: basta para una demo sin modelo; no es verificación semántica.
        supported = bool(claim_words) and len(hits) / len(claim_words) >= 0.6
        return ok({"article_id": article["article_id"], "claim": args["claim"], "supported": supported, "matched_terms": hits})

    return [
        make(
            "extract_ticket_facts",
            "Extrae los hechos estructurados de UN ticket de la mesa de ayuda a partir de su ID (formato TCK-4001): "
            "usuario, categoría, estado, fecha e importe en EUR, más el texto original. Úsala cuando la petición "
            "nombre un ticket concreto y pida sus datos; no sirve para artículos de la base de conocimiento "
            "(para eso, extract_article_steps o summarize_article). Un ID desconocido devuelve un error de validación.",
            {"ticket_id": "ID del ticket, p. ej. TCK-4001"},
            extract_ticket_facts,
        ),
        make(
            "extract_article_steps",
            "Devuelve los PASOS de un artículo de la base de conocimiento como lista ordenada, a partir de su ID "
            "(formato KB-109). Úsala cuando la petición pida qué hay que hacer, el procedimiento o los pasos. "
            "A diferencia de summarize_article, que da una sola frase de resumen, esta separa cada acción; "
            "a diferencia de extract_ticket_facts, trabaja con artículos y no con tickets.",
            {"article_id": "ID del artículo, p. ej. KB-109"},
            extract_article_steps,
        ),
        make(
            "summarize_article",
            "Devuelve un RESUMEN de una frase de un artículo de la base de conocimiento (título y primera frase), "
            "a partir de su ID (formato KB-109). Úsala cuando la petición pida de qué trata un artículo, no el "
            "procedimiento completo: para los pasos, extract_article_steps. Casos borde: un ID inexistente "
            "devuelve un error de validación; un artículo obsoleto se resume igual.",
            {"article_id": "ID del artículo, p. ej. KB-109"},
            summarize_article,
        ),
        make(
            "verify_claim_against_article",
            "Comprueba si UNA afirmación se sostiene según un artículo concreto de la base de conocimiento. "
            "Entrada: la afirmación en texto y el ID del artículo (KB-114). Devuelve `supported` (true o false) y "
            "los términos coincidentes. Úsala solo para verificar; no resume ni extrae pasos (summarize_article y "
            "extract_article_steps) y no sirve para tickets.",
            {"claim": "afirmación que hay que comprobar", "article_id": "ID del artículo, p. ej. KB-114"},
            verify_claim,
        ),
    ]


# --- errores (app1/04) ------------------------------------------------------

def errores_tools(state: ErroresState, estructurado: bool, fallo_como_vacio: bool) -> list[SdkMcpTool[Any]]:
    def fail(category: str, message: str, *, retryable: bool = False, **extra: Any) -> dict[str, Any]:
        return error(category, message, retryable=retryable, **extra) if estructurado else generic_error()

    async def fetch_ticket_history(args: dict[str, Any]) -> dict[str, Any]:
        state.calls["fetch_ticket_history"] += 1
        ticket = find_ticket(args["ticket_id"])
        if ticket is None:
            return fail("validation", f"ticket no encontrado: {args['ticket_id']}")
        if state.calls["fetch_ticket_history"] == 1:
            # Transitorio: falla la primera vez y responde a partir de la segunda.
            if fallo_como_vacio:
                # Anti-patrón: el fallo de acceso se disfraza de resultado vacío válido.
                return ok({"ticket_id": ticket["ticket_id"], "events": []})
            return fail("transient", "tiempo de espera agotado al consultar el histórico", retryable=True, tool="fetch_ticket_history")
        events = [{"event": "created", "at": ticket["created_at"]}, {"event": "status", "value": ticket["status"]}]
        return ok({"ticket_id": ticket["ticket_id"], "events": events})

    async def get_user_profile(args: dict[str, Any]) -> dict[str, Any]:
        state.calls["get_user_profile"] += 1
        if not USER_ID_PATTERN.match(args["user_id"]):
            return fail("validation", "ID de usuario mal formado; el formato es EMP-1001", input=args["user_id"])
        user = next((u for u in load("usuarios.json") if u["user_id"] == args["user_id"]), None)
        return ok(user) if user else fail("validation", f"usuario no encontrado: {args['user_id']}", input=args["user_id"])

    async def reassign_license(args: dict[str, Any]) -> dict[str, Any]:
        state.calls["reassign_license"] += 1
        if int(args.get("seats", 1)) > LICENSE_QUOTA:
            # Regla de negocio: no es reintentable. La guía (2.2-S2) lo escribe `retriable: false`;
            # aquí el campo se llama `isRetryable`, como en el resto del proyecto.
            return fail(
                "business", f"No se puede reasignar: supera el cupo de {LICENSE_QUOTA} puestos por licencia. "
                "Solicita una ampliación de cupo a Finanzas.",
            )
        return ok({"user_id": args["user_id"], "license": args["license"], "reassigned": True})

    async def export_audit_log(args: dict[str, Any]) -> dict[str, Any]:
        state.calls["export_audit_log"] += 1
        return fail("permission", "Tu rol no tiene permiso para exportar el registro de auditoría")

    async def search_tickets_by_user(args: dict[str, Any]) -> dict[str, Any]:
        state.calls["search_tickets_by_user"] += 1
        tickets = [t["ticket_id"] for t in load("tickets.json") if t["user_id"] == args["user_id"]]
        # Sin coincidencias no es un error: es una lista vacía válida.
        return ok({"user_id": args["user_id"], "tickets": tickets})

    return [
        make("fetch_ticket_history", "Devuelve el histórico de eventos de un ticket (creación y cambios de estado) dado su ID TCK-4001.",
             {"ticket_id": "ID del ticket"}, fetch_ticket_history),
        make("get_user_profile", "Devuelve el perfil de una persona usuaria (nombre, departamento, correo) dado su ID EMP-1001.",
             {"user_id": "ID del usuario, formato EMP-1001"}, get_user_profile),
        make("reassign_license", "Reasigna una licencia de software a una persona usuaria. Entrada: user_id, license y seats (puestos).",
             {"user_id": "ID del usuario", "license": "nombre de la licencia", "seats": "número de puestos"}, reassign_license),
        make("export_audit_log", "Exporta el registro de auditoría de la mesa de ayuda. Entrada: scope (all o un ticket).",
             {"scope": "all o un ID de ticket"}, export_audit_log),
        make("search_tickets_by_user", "Lista los IDs de los tickets de una persona usuaria. Una lista vacía significa que no tiene tickets.",
             {"user_id": "ID del usuario"}, search_tickets_by_user),
    ]


# --- amplio / acotado (app1/05) ---------------------------------------------

# Cada alias de `amplio` apunta a una de las 5 tools de `acotado`: la batería
# cuenta un acierto si la tool llamada tiene la canónica esperada.
CANONICAL = {
    "get_ticket": "get_ticket", "lookup_ticket": "get_ticket", "fetch_ticket_details": "get_ticket", "get_ticket_status": "get_ticket",
    "search_tickets": "search_tickets", "find_tickets": "search_tickets", "list_tickets_by_user": "search_tickets",
    "search_kb": "search_kb", "query_kb": "search_kb", "kb_lookup": "search_kb", "find_kb_articles": "search_kb",
    "get_article": "get_article", "read_article": "get_article", "get_kb_entry": "get_article",
    "get_user": "get_user", "find_user": "get_user", "get_employee": "get_user", "lookup_user_profile": "get_user",
}
CANONICAL_SPECS = {
    "get_ticket": ("Devuelve un ticket completo dado su ID (TCK-4001).", {"ticket_id": "ID del ticket"}),
    "search_tickets": ("Busca tickets por palabras clave, categoría o ID de usuario (EMP-1001).", {"query": "palabras de búsqueda"}),
    "search_kb": ("Busca artículos de la base de conocimiento por palabras clave o categoría.", {"query": "palabras de búsqueda"}),
    "get_article": ("Devuelve un artículo de la base de conocimiento dado su ID (KB-109).", {"article_id": "ID del artículo"}),
    "get_user": ("Devuelve una persona usuaria dada su ID (EMP-1001).", {"user_id": "ID del usuario"}),
}


def scope_handlers() -> dict[str, Handler]:
    async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
        ticket = find_ticket(args["ticket_id"])
        return ok(ticket) if ticket else not_found("ticket", args["ticket_id"])

    async def search_tickets(args: dict[str, Any]) -> dict[str, Any]:
        words = {w for w in words_of(args["query"]) if len(w) >= 3}
        hits = [
            t["ticket_id"] for t in load("tickets.json")
            if t["category"] in words or (t["user_id"] or "").lower() in words
            or any(w in t["description"].lower() for w in words)
        ]
        return ok({"query": args["query"], "total": len(hits), "ticket_ids": hits[:8]})

    async def search_kb(args: dict[str, Any]) -> dict[str, Any]:
        words = {w for w in words_of(args["query"]) if len(w) >= 3}
        hits = [
            a["article_id"] for a in load("articulos_kb.json")
            if a["category"] in words or any(w in f"{a['title']} {a['body']}".lower() for w in words)
        ]
        return ok({"query": args["query"], "total": len(hits), "article_ids": hits[:8]})

    async def get_article(args: dict[str, Any]) -> dict[str, Any]:
        article = find_article(args["article_id"])
        return ok(article) if article else not_found("artículo", args["article_id"])

    async def get_user(args: dict[str, Any]) -> dict[str, Any]:
        user = next((u for u in load("usuarios.json") if u["user_id"] == args["user_id"]), None)
        return ok(user) if user else not_found("usuario", args["user_id"])

    return {"get_ticket": get_ticket, "search_tickets": search_tickets, "search_kb": search_kb, "get_article": get_article, "get_user": get_user}


def scope_tools(wide: bool) -> list[SdkMcpTool[Any]]:
    handlers = scope_handlers()
    names = list(CANONICAL) if wide else list(CANONICAL_SPECS)
    tools_ = []
    for name in names:
        canonical = CANONICAL[name]
        description, properties = CANONICAL_SPECS[canonical]
        # Los alias repiten la descripción canónica con otras palabras: se solapan a propósito.
        text = description if name == canonical else f"{description[:-1]} (equivale a {name.replace('_', ' ')})."
        tools_.append(make(name, text, properties, handlers[canonical]))
    return tools_


def make_tools(
    familia: str,
    *,
    variante: str | None = None,
    state: ErroresState | None = None,
    estructurado: bool = True,
    fallo_como_vacio: bool = False,
) -> list[SdkMcpTool[Any]]:
    if familia == "routing":
        return routing_tools(variante)
    if familia == "errores":
        return errores_tools(state or ErroresState(), estructurado, fallo_como_vacio)
    if familia in ("amplio", "acotado"):
        return scope_tools(wide=familia == "amplio")
    raise ValueError(f"familia desconocida: {familia}")


def build_server(familia: str, **kwargs: Any) -> Any:
    return create_sdk_mcp_server(SERVER_NAME, tools=make_tools(familia, **kwargs))
