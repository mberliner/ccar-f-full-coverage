"""Tests del servidor MCP `investigacion` de app3: búsqueda en tickets y KB con contenido y metadatos separados. Sin modelo."""

import json

from app3_sistema_multiagente.servers.investigacion import SERVER_NAME, build_server, make_tools
from harness.offline import call_tool

TOOLS = {t.name: t for t in make_tools()}


def search(tool, query):
    outcome = call_tool(TOOLS[tool], {"query": query})
    return outcome, json.loads(outcome.text)


def test_tickets_separate_content_from_metadata():
    outcome, data = search("search_tickets", "VPN")
    assert not outcome.is_error and data["results"]
    for result in data["results"]:
        assert set(result) == {"content", "metadata"}
        assert set(result["metadata"]) == {"ticket_id", "category", "status", "created_at"}
        assert "VPN" in result["content"]


def test_broad_query_by_category_covers_vpn_and_wifi():
    _, data = search("search_tickets", "red")
    texts = " ".join(r["content"] for r in data["results"]).lower()
    assert "vpn" in texts and "wifi" in texts


def test_narrow_query_misses_wifi():
    _, data = search("search_tickets", "VPN")
    assert "wifi" not in " ".join(r["content"] for r in data["results"]).lower()


def test_kb_metadata_includes_date_and_supersession():
    _, data = search("search_kb", "VPN")
    by_id = {r["metadata"]["article_id"]: r for r in data["results"]}
    assert by_id["KB-110"]["metadata"]["superseded_by"] == "KB-109"
    assert all(set(r["metadata"]) == {"article_id", "updated_at", "superseded_by"} for r in data["results"])
    assert all(set(r["content"]) == {"title", "body"} for r in data["results"])


def test_empty_result_is_valid_not_error():
    outcome, data = search("search_kb", "inexistente-xyz")
    assert not outcome.is_error and data == {"query": "inexistente-xyz", "total": 0, "truncated": False, "results": []}


def test_truncation_is_reported():
    _, data = search("search_tickets", "red")
    assert data["total"] > len(data["results"]) == 8 and data["truncated"] is True


def test_blank_query_is_structured_error():
    outcome = call_tool(TOOLS["search_tickets"], {"query": "  "})
    assert outcome.is_error and json.loads(outcome.text)["errorCategory"] == "validation"


def test_server_config():
    assert build_server()["name"] == SERVER_NAME
