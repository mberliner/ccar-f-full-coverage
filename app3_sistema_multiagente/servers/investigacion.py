"""Servidor MCP en proceso de investigación (app3).

PROPÓSITO: dar a los subagentes de app3 dos fuentes de búsqueda sobre los
datos sintéticos: los tickets de la mesa de ayuda y la base de conocimiento.

POR QUÉ EXISTE: el coordinador reparte el alcance por tipo de fuente (un
analista por tool). Cada resultado separa el contenido de sus metadatos
(`ticket_id`/`article_id`, fecha, `superseded_by`) para que la atribución
sobreviva al pasar de un agente a otro.

`extended=True` (app3/03) añade `fetch_url` (genérica), `load_document` (solo
documentos) y `verify_fact` (solo afirmaciones simples); por defecto el servidor
sigue con las dos tools de búsqueda que usan app3/01 y app3/02.

QUÉ NO HACE: no resume ni ordena por relevancia semántica (busca palabras y
categoría) y no tiene estado: dos llamadas iguales devuelven lo mismo.

USA: TS 1.3-K2, TS 2.2-K1, TS 2.2-S1
"""

import json
import re
from typing import Any

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from harness.data import load

SERVER_NAME = "investigacion"
MAX_RESULTS = 8
# Subtemas de «problemas de red» en los datos (categoría red). Los usan los
# módulos para medir cobertura; vive aquí porque describe los datos del servidor.
NETWORK_SUBTOPICS = {"vpn": ["vpn"], "wifi": ["wifi", "wi-fi"], "impresora": ["impresora"]}


def tool_name(name: str) -> str:
    return f"mcp__{SERVER_NAME}__{name}"


def ok(data: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


def words_of(query: str) -> set[str]:
    return {w for w in query.lower().split() if len(w) >= 3}


def make_tools(*, extended: bool = False) -> list[SdkMcpTool[Any]]:
    @tool(
        "search_tickets",
        "Busca en los tickets de la mesa de ayuda por palabras clave o por categoría (acceso, hardware, software, "
        "red, licencias, gastos). Devuelve hasta 8 resultados con el texto del ticket en `content` y su ID, "
        "categoría, estado y fecha en `metadata`, más `total` y `truncated` si hay más coincidencias. "
        "No busca en la base de conocimiento: para eso, search_kb.",
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
        # `total` y `truncated`: el analista sabe que hay más de lo que ve y
        # puede afinar la búsqueda, en vez de dar por completo un listado parcial.
        return ok({"query": args["query"], "total": len(hits), "truncated": len(hits) > MAX_RESULTS, "results": results})

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
        return ok({"query": args["query"], "total": len(hits), "truncated": len(hits) > MAX_RESULTS, "results": results})

    if not extended:
        return [search_tickets, search_kb]
    return [search_tickets, search_kb, *make_extended_tools()]


def find_url(url: str) -> dict | None:
    return next((u for u in load("documentos.json")["urls"] if u["url"] == url), None)


def make_extended_tools() -> list[SdkMcpTool[Any]]:
    """Tools de app3/03: una genérica (`fetch_url`) frente a dos acotadas (`load_document`, `verify_fact`)."""

    @tool(
        "fetch_url",
        "Abre cualquier URL del catálogo y devuelve su contenido en bruto. Entrada: `url`. Sirve para documentos y "
        "también para páginas que no lo son (login, seguimiento, imágenes).",
        {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    )
    async def fetch_url(args: dict[str, Any]) -> dict[str, Any]:
        entry = find_url(args["url"])
        if entry is None:
            return structured_error("URL fuera del catálogo", url=args["url"])
        # Un recurso que no es documento devuelve una página genérica, no texto útil.
        content = entry["content"] or "Página web sin contenido documental (inicio de sesión, seguimiento o imagen)."
        return ok({"url": entry["url"], "is_document": entry["is_document"], "content": content})

    @tool(
        "load_document",
        "Carga un DOCUMENTO de la documentación (URL con ruta /docs/…) y devuelve su título y su contenido. "
        "Entrada: `url`. Rechaza con un error de validación cualquier URL que no sea un documento (login, "
        "seguimiento, imágenes): para esas no hay contenido que citar. No verifica afirmaciones: para eso, verify_fact.",
        {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    )
    async def load_document(args: dict[str, Any]) -> dict[str, Any]:
        entry = find_url(args["url"])
        if entry is None or not entry["is_document"]:
            return structured_error("la URL no es un documento de /docs/", url=args["url"])
        return ok({"url": entry["url"], "title": entry["title"], "content": entry["content"]})

    @tool(
        "verify_fact",
        "Verifica una afirmación SIMPLE contra su artículo de la base de conocimiento. Entrada: `claim_id` (C-1…). "
        "Devuelve `supported` y los `article_ids` comprobados. Las afirmaciones complejas, que necesitan cruzar "
        "varios artículos, no se verifican aquí: devuelve el estado «enrutar al coordinador». No busca ni carga "
        "documentos (search_kb y load_document).",
        {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]},
    )
    async def verify_fact(args: dict[str, Any]) -> dict[str, Any]:
        claim = next((c for c in load("documentos.json")["afirmaciones"] if c["claim_id"] == args["claim_id"]), None)
        if claim is None:
            return structured_error("afirmación desconocida", claim_id=args["claim_id"])
        if claim["verifiable"] != "simple":
            return ok({"claim_id": claim["claim_id"], "status": "enrutar al coordinador", "article_ids": claim["article_ids"]})
        article = next(a for a in load("articulos_kb.json") if a["article_id"] == claim["article_ids"][0])
        text = set(re.findall(r"\w+", f"{article['title']} {article['body']}".lower()))
        claim_words = [w for w in re.findall(r"\w+", claim["text"].lower()) if len(w) >= 4]
        # Heurística de palabras (como en app1): suficiente para la demo, no es verificación semántica.
        supported = bool(claim_words) and sum(w in text for w in claim_words) / len(claim_words) >= 0.6
        return ok({"claim_id": claim["claim_id"], "supported": supported, "article_ids": claim["article_ids"]})

    return [fetch_url, load_document, verify_fact]


def structured_error(message: str, **extra: Any) -> dict[str, Any]:
    data = {"errorCategory": "validation", "isRetryable": False, "message": message, **extra}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def validation_error(query: str) -> dict[str, Any]:
    # Una consulta vacía es un error de entrada; un resultado vacío no lo es.
    data = {"errorCategory": "validation", "isRetryable": True, "message": "consulta vacía o demasiado corta", "query": query}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "is_error": True}


def build_server(*, extended: bool = False) -> Any:
    return create_sdk_mcp_server(SERVER_NAME, tools=make_tools(extended=extended))
