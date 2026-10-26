"""Servidor MCP stdio `catalogo` (app1/06): la base de conocimiento como servidor externo.

PROPÓSITO: exponer `search_kb` y `get_article` por stdio, y el catálogo de
artículos como *resources* (`kb://catalogo` y `kb://articulos/<ID>`), para que
`.mcp.json` lo lance como un proceso aparte.

POR QUÉ EXISTE: app1/06 enseña la configuración de servidores MCP: alcance del
`.mcp.json`, variables `${VAR}`, descubrimiento de tools de varios servidores y
resources frente a llamadas exploratorias. Hace falta un servidor real, no uno
en proceso, para que esas piezas existan. `CATALOGO_DESCRIPCION=minima` (en el
`env` del `.mcp.json`) sustituye la descripción de `search_kb` por una línea:
es la variante anti-patrón de la parte `descripcion`.

QUÉ NO HACE: no muestra nunca el token (`CATALOGO_TOKEN`): `token_status` solo
dice si llegó. No escribe nada y no autentica de verdad: el token es sintético
y solo sirve para comprobar que `${VAR}` se expandió.

Uso: `python servers/catalogo_stdio.py` (lo lanza `.mcp.json`).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# El proyecto es virtual (sin build-system): al lanzarse por ruta, la raíz no
# está en el path y `harness` no se encontraría.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import CallToolResult, TextContent  # noqa: E402

from harness.data import load  # noqa: E402

SERVER_NAME = "catalogo"
MINIMAL_DESCRIPTION = "Busca en la base de conocimiento."
FULL_DESCRIPTION = (
    "Busca artículos de la base de conocimiento por palabras clave y los devuelve con ranking: cada resultado "
    "lleva `score` (términos coincidentes, el título pesa doble) y sale ordenado de mayor a menor. Por defecto "
    "filtra los artículos obsoletos (los que tienen `superseded_by`) y dice cuántos ha excluido en "
    "`excluded_superseded`; con `include_superseded=true` los incluye y cada uno apunta a su sustituto. "
    "Devuelve hasta 8 resultados con `article_id`, `title`, `category`, `updated_at` y `superseded_by`. "
    "Es la vía para encontrar el artículo vigente sobre un tema; para leer uno ya identificado, get_article."
)
MAX_RESULTS = 8


def words_of(text: str) -> set[str]:
    return {w for w in text.lower().replace("«", " ").replace("»", " ").split() if len(w) >= 3}


def error_result(message: str, **extra: Any) -> CallToolResult:
    data = {"errorCategory": "validation", "isRetryable": False, "message": message, **extra}
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))], is_error=True)


def build_server(descripcion: str | None = None) -> MCPServer:
    # La variante sale del argumento o, al lanzarse como proceso, del entorno.
    variant = descripcion or os.environ.get("CATALOGO_DESCRIPCION", "completa")
    server = MCPServer(SERVER_NAME)
    articles = load("articulos_kb.json")

    def search_kb(query: str, include_superseded: bool = False) -> dict[str, Any]:
        words = words_of(query.replace(":", " ").replace(",", " "))
        scored = []
        for article in articles:
            title = words_of(article["title"].replace(":", " ").replace(",", " "))
            rest = words_of(f"{article['body']} {article['category']}".replace(",", " "))
            score = 2 * len(words & title) + len(words & (rest - title))
            if score:
                scored.append((score, article))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["article_id"]))
        excluded = 0 if include_superseded else sum(1 for _, a in scored if a["superseded_by"])
        if not include_superseded:
            scored = [(s, a) for s, a in scored if not a["superseded_by"]]
        results = [
            {"score": s, **{k: a[k] for k in ("article_id", "title", "category", "updated_at", "superseded_by")}}
            for s, a in scored[:MAX_RESULTS]
        ]
        return {"query": query, "results": results, "excluded_superseded": excluded}

    # `Any` y no `dict | CallToolResult`: MCPServer rechaza CallToolResult dentro de una unión.
    def get_article(article_id: str) -> Any:
        article = next((a for a in articles if a["article_id"] == article_id), None)
        return article if article else error_result(f"artículo no encontrado: {article_id}", input=article_id)

    def token_status() -> dict[str, bool]:
        # Solo informa de si llegó: el valor no sale nunca de este proceso.
        return {"token_recibido": bool(os.environ.get("CATALOGO_TOKEN"))}

    description = MINIMAL_DESCRIPTION if variant == "minima" else FULL_DESCRIPTION
    server.tool(name="search_kb", description=description)(search_kb)
    server.tool(
        name="get_article",
        description="Devuelve un artículo completo de la base de conocimiento dado su ID (formato KB-109), con cuerpo y fecha.",
    )(get_article)
    server.tool(
        name="token_status",
        description="Dice si el servidor recibió CATALOGO_TOKEN en su entorno. Devuelve solo un booleano, nunca el valor.",
    )(token_status)

    # Resources: el catálogo de artículos para que el agente sepa qué hay sin explorar.
    @server.resource("kb://catalogo", name="catalogo", description="Índice de todos los artículos (ID, título, categoría).", mime_type="application/json")
    def catalog() -> str:
        index = [{k: a[k] for k in ("article_id", "title", "category")} for a in articles]
        return json.dumps(index, ensure_ascii=False)

    for article in articles:
        def make_reader(item: dict[str, Any]):
            return lambda: json.dumps(item, ensure_ascii=False)

        server.resource(
            f"kb://articulos/{article['article_id']}", name=article["article_id"], description=article["title"], mime_type="application/json",
        )(make_reader(article))
    return server


if __name__ == "__main__":
    build_server().run("stdio")
