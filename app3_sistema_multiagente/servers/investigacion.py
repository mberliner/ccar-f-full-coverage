"""Servidor MCP en proceso de investigación (app3).

PROPÓSITO: dar a los subagentes de app3 dos fuentes de búsqueda sobre los
datos sintéticos: los tickets de la mesa de ayuda y la base de conocimiento.

POR QUÉ EXISTE: el coordinador reparte el alcance por tipo de fuente (un
analista por tool). Cada resultado separa el contenido de sus metadatos
(`ticket_id`/`article_id`, fecha, `superseded_by`) para que la atribución
sobreviva al pasar de un agente a otro.

QUÉ NO HACE: no resume ni ordena por relevancia semántica (busca palabras y
categoría) y no tiene estado: dos llamadas iguales devuelven lo mismo.

USA: TS 1.3-K2
"""

import json
from typing import Any

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from harness.data import load

SERVER_NAME = "investigacion"
MAX_RESULTS = 8


def tool_name(name: str) -> str:
    return f"mcp__{SERVER_NAME}__{name}"


def ok(data: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def words_of(query: str) -> set[str]:
    return {w for w in query.lower().split() if len(w) >= 3}


def make_tools() -> list[SdkMcpTool[Any]]:
    @tool(
        "search_tickets",
        "Busca en los tickets de la mesa de ayuda por palabras clave o por categoría (acceso, hardware, software, "
        "red, licencias, gastos). Devuelve hasta 8 resultados con el texto del ticket en `content` y su ID, "
        "categoría, estado y fecha en `metadata`. No busca en la base de conocimiento: para eso, search_kb.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    async def search_tickets(args: dict[str, Any]) -> dict[str, Any]:
        words = words_of(args["query"])
        if not words:
            return validation_error(args["query"])
        hits = [
            t for t in load("tickets.json")
            if t["category"] in words or any(w in t["description"].lower() for w in words)
        ]
        results = [
            {
                "content": t["description"],
                "metadata": {k: t[k] for k in ("ticket_id", "category", "status", "created_at")},
            }
            for t in hits[:MAX_RESULTS]
        ]
        return ok({"query": args["query"], "results": results})

    @tool(
        "search_kb",
        "Busca artículos de la base de conocimiento por palabras clave o por categoría. Devuelve hasta 8 con "
        "título y cuerpo en `content`, y su ID, fecha de actualización y, si está obsoleto, el artículo que lo "
        "sustituye en `metadata`. No busca en los tickets: para eso, search_tickets.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    async def search_kb(args: dict[str, Any]) -> dict[str, Any]:
        words = words_of(args["query"])
        if not words:
            return validation_error(args["query"])
        hits = [
            a for a in load("articulos_kb.json")
            if a["category"] in words or a["article_id"].lower() in words
            or any(w in f"{a['title']} {a['body']}".lower() for w in words)
        ]
        results = [
            {
                "content": {"title": a["title"], "body": a["body"]},
                "metadata": {k: a[k] for k in ("article_id", "updated_at", "superseded_by")},
            }
            for a in hits[:MAX_RESULTS]
        ]
        return ok({"query": args["query"], "results": results})

    return [search_tickets, search_kb]


def validation_error(query: str) -> dict[str, Any]:
    # Una consulta vacía es un error de entrada; un resultado vacío no lo es.
    data = {"errorCategory": "validation", "isRetryable": True, "message": "consulta vacía o demasiado corta", "query": query}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def build_server() -> Any:
    return create_sdk_mcp_server(SERVER_NAME, tools=make_tools())
