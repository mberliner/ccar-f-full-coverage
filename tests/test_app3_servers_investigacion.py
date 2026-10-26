"""Tests del servidor MCP `investigacion` de app3: búsqueda en tickets y KB con contenido y metadatos separados. Sin modelo."""

import json

from app3_sistema_multiagente.servers.investigacion import SERVER_NAME, build_server, make_tools
from harness.data import load
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


# --- ampliación de la entrega 2 (app3/03): fetch_url, load_document, verify_fact ---

EXTENDED = {t.name: t for t in make_tools(extended=True)}
CATALOG = load("documentos.json")


def test_default_tools_unchanged():
    # app3/01 y app3/02 siguen viendo solo las dos tools de búsqueda.
    assert {t.name for t in make_tools()} == {"search_tickets", "search_kb"}
    assert set(EXTENDED) == {"search_tickets", "search_kb", "fetch_url", "load_document", "verify_fact"}


def test_fetch_url_opens_any_url_in_the_catalog():
    # Genérica: abre un documento y también una página de login.
    for entry in CATALOG["urls"]:
        outcome = call_tool(EXTENDED["fetch_url"], {"url": entry["url"]})
        assert not outcome.is_error
    login = next(u for u in CATALOG["urls"] if "/login" in u["url"])
    assert json.loads(call_tool(EXTENDED["fetch_url"], {"url": login["url"]}).text)["is_document"] is False


def test_fetch_url_unknown_url_is_structured_error():
    outcome = call_tool(EXTENDED["fetch_url"], {"url": "https://otro.test/x"})
    data = json.loads(outcome.text)
    assert outcome.is_error and data["errorCategory"] == "validation"


def test_load_document_accepts_only_documents():
    document = next(u for u in CATALOG["urls"] if u["is_document"])
    outcome = call_tool(EXTENDED["load_document"], {"url": document["url"]})
    data = json.loads(outcome.text)
    assert not outcome.is_error and data["content"] == document["content"] and data["title"] == document["title"]


def test_load_document_rejects_non_documents_with_validation_error():
    for entry in (u for u in CATALOG["urls"] if not u["is_document"]):
        outcome = call_tool(EXTENDED["load_document"], {"url": entry["url"]})
        data = json.loads(outcome.text)
        assert outcome.is_error and data["errorCategory"] == "validation" and data["isRetryable"] is False


def test_verify_fact_simple_claim_is_checked_against_its_article():
    simple = next(c for c in CATALOG["afirmaciones"] if c["verifiable"] == "simple")
    outcome = call_tool(EXTENDED["verify_fact"], {"claim_id": simple["claim_id"]})
    data = json.loads(outcome.text)
    assert not outcome.is_error and data["supported"] is True and data["article_ids"] == simple["article_ids"]


def test_verify_fact_complex_claim_is_routed_to_coordinator():
    complex_claim = next(c for c in CATALOG["afirmaciones"] if c["verifiable"] == "compleja")
    outcome = call_tool(EXTENDED["verify_fact"], {"claim_id": complex_claim["claim_id"]})
    data = json.loads(outcome.text)
    assert not outcome.is_error and data["status"] == "enrutar al coordinador" and "supported" not in data


def test_verify_fact_unknown_claim():
    outcome = call_tool(EXTENDED["verify_fact"], {"claim_id": "C-99"})
    assert outcome.is_error and json.loads(outcome.text)["errorCategory"] == "validation"
