"""Tests de los servidores stdio de app1 (`catalogo` e `inventario`), llamados en proceso con MCPServer. Sin modelo."""

import asyncio
import json

from app1_agente_unico.servers.catalogo_stdio import build_server, MINIMAL_DESCRIPTION
from app1_agente_unico.servers.inventario_stdio import build_server as build_inventario
from harness.data import load


def call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    text = "".join(block.text for block in result.content if block.type == "text")
    return result, json.loads(text)


def tools_of(server):
    return {t.name: t for t in asyncio.run(server.list_tools())}


def test_tools_exposed():
    assert set(tools_of(build_server())) == {"search_kb", "get_article", "token_status"}


def test_search_kb_ranks_and_hides_superseded_by_default():
    _, data = call(build_server(), "search_kb", {"query": "VPN"})
    ids = [r["article_id"] for r in data["results"]]
    assert "KB-109" in ids and "KB-110" not in ids  # KB-110 está obsoleto
    assert data["excluded_superseded"] == 1


def test_search_kb_can_include_superseded_with_pointer():
    _, data = call(build_server(), "search_kb", {"query": "VPN", "include_superseded": True})
    by_id = {r["article_id"]: r for r in data["results"]}
    assert by_id["KB-110"]["superseded_by"] == "KB-109"


def test_search_kb_results_are_ranked_by_matched_terms():
    _, data = call(build_server(), "search_kb", {"query": "vpn inestable casa"})
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True) and data["results"][0]["article_id"] == "KB-109"


def test_get_article_and_unknown_id():
    _, article = call(build_server(), "get_article", {"article_id": "KB-109"})
    assert article["title"] == "VPN inestable desde casa"
    result, error = call(build_server(), "get_article", {"article_id": "KB-999"})
    assert error["errorCategory"] == "validation" and error["isRetryable"] is False


def test_minimal_description_variant():
    full = tools_of(build_server())["search_kb"].description
    minimal = tools_of(build_server(descripcion="minima"))["search_kb"].description
    assert minimal == MINIMAL_DESCRIPTION and len(minimal) < 60
    assert "superseded_by" in full and "ranking" in full.lower()


def test_token_status_reports_without_revealing(monkeypatch):
    monkeypatch.setenv("CATALOGO_TOKEN", "valor-sintetico-secreto")
    result, data = call(build_server(), "token_status", {})
    assert data == {"token_recibido": True}
    assert "valor-sintetico-secreto" not in json.dumps(data)
    monkeypatch.delenv("CATALOGO_TOKEN")
    assert call(build_server(), "token_status", {})[1] == {"token_recibido": False}


def test_catalog_is_exposed_as_resources():
    server = build_server()
    uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    articles = load("articulos_kb.json")
    assert "kb://catalogo" in uris
    assert {f"kb://articulos/{a['article_id']}" for a in articles} <= uris


def test_catalog_resource_lists_every_article_with_title():
    server = build_server()
    contents = list(asyncio.run(server.read_resource("kb://catalogo")))
    catalog = json.loads(contents[0].content)
    assert {c["article_id"] for c in catalog} == {a["article_id"] for a in load("articulos_kb.json")}
    assert all(c["title"] for c in catalog)


def test_inventory_server_has_one_tool():
    inventario = build_inventario()
    assert set(tools_of(inventario)) == {"stock_equipo"}
    _, data = call(inventario, "stock_equipo", {"tipo": "portatil"})
    assert data["tipo"] == "portatil" and isinstance(data["disponibles"], int)
