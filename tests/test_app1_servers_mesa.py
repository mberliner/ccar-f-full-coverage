"""Tests del servidor MCP `mesa` de app1 (familias routing, errores y amplio/acotado). Sin modelo."""

import json

import pytest

from app1_agente_unico.servers.mesa import CANONICAL, RENAMED, SERVER_NAME, ErroresState, build_server, make_tools, tool_name
from harness.data import load
from harness.offline import call_tool


def tools(familia, **kw):
    return {t.name: t for t in make_tools(familia, **kw)}


def run(tool_map, name, args):
    outcome = call_tool(tool_map[name], args)
    return outcome, json.loads(outcome.text)


# --- routing ---------------------------------------------------------------

def test_routing_complete_has_four_split_tools():
    assert set(tools("routing")) == {
        "extract_ticket_facts", "extract_article_steps", "summarize_article", "verify_claim_against_article",
    }


def test_routing_minimal_has_two_overlapping_tools_with_one_line_descriptions():
    minimal = make_tools("routing", variante="minimas")
    assert {t.name for t in minimal} == {"analyze_content", "analyze_document"}
    assert all("\n" not in t.description and len(t.description) < 60 for t in minimal)


def test_complete_descriptions_say_how_they_differ_from_the_similar_tool():
    descriptions = {t.name: t.description for t in make_tools("routing")}
    assert "summarize_article" in descriptions["extract_article_steps"]
    assert "extract_article_steps" in descriptions["summarize_article"]
    assert all(len(d) > 150 for d in descriptions.values())


def test_extract_ticket_facts_contract():
    ticket = load("tickets.json")[0]
    _, data = run(tools("routing"), "extract_ticket_facts", {"ticket_id": ticket["ticket_id"]})
    assert set(data) == {"ticket_id", "user_id", "category", "status", "created_at", "amount_eur", "description"}
    assert data["ticket_id"] == ticket["ticket_id"]


def test_extract_article_steps_and_summary_contract():
    routing = tools("routing")
    _, steps = run(routing, "extract_article_steps", {"article_id": "KB-109"})
    assert steps["article_id"] == "KB-109" and steps["steps"] and all(isinstance(s, str) for s in steps["steps"])
    _, summary = run(routing, "summarize_article", {"article_id": "KB-109"})
    assert set(summary) == {"article_id", "title", "summary"}


def test_verify_claim_supported_and_unsupported():
    routing = tools("routing")
    _, yes = run(routing, "verify_claim_against_article", {"claim": "Hasta 500 EUR lo aprueba soporte", "article_id": "KB-114"})
    _, no = run(routing, "verify_claim_against_article", {"claim": "Los monitores curvos se compran sin aprobación", "article_id": "KB-114"})
    assert yes["supported"] is True and no["supported"] is False


def test_unknown_id_is_structured_validation_error():
    outcome, data = run(tools("routing"), "extract_ticket_facts", {"ticket_id": "TCK-0"})
    assert outcome.is_error and data["errorCategory"] == "validation" and data["isRetryable"] is False


def test_misleading_name_renames_one_tool_keeping_its_description_and_handler():
    original = "verify_claim_against_article"
    new = RENAMED[original]
    normal = {t.name: t for t in make_tools("routing")}
    misleading = tools("routing", variante="nombre_enganoso")
    # Un solo nombre cambia; el resto de tools y su número quedan igual.
    assert set(misleading) == (set(normal) - {original}) | {new}
    assert len(misleading) == len(normal) == 4
    assert new not in normal  # el nombre engañoso no choca con ninguna otra tool
    # Misma descripción (no se toca) y mismo contrato de entrada.
    assert misleading[new].description == normal[original].description
    assert misleading[new].input_schema == normal[original].input_schema
    # El handler sigue verificando afirmaciones, aunque el nombre hable de tickets.
    _, data = run(misleading, new, {"claim": "Hasta 500 EUR lo aprueba soporte", "article_id": "KB-114"})
    assert data["supported"] is True


def test_the_other_routing_variants_keep_their_names():
    assert set(tools("routing")) == {
        "extract_ticket_facts", "extract_article_steps", "summarize_article", "verify_claim_against_article",
    }
    assert set(tools("routing", variante="minimas")) == {"analyze_content", "analyze_document"}


def test_minimal_tools_split_by_kind_so_a_misroute_has_a_consequence():
    # `analyze_content` es para tickets y `analyze_document` para artículos: elegir la otra devuelve un error.
    minimal = tools("routing", variante="minimas")
    ticket_id = load("tickets.json")[0]["ticket_id"]
    assert not run(minimal, "analyze_content", {"content_id": ticket_id})[0].is_error
    assert not run(minimal, "analyze_document", {"document_id": "KB-109"})[0].is_error
    wrong_a, data_a = run(minimal, "analyze_content", {"content_id": "KB-109"})
    wrong_b, data_b = run(minimal, "analyze_document", {"document_id": ticket_id})
    for outcome, data in ((wrong_a, data_a), (wrong_b, data_b)):
        assert outcome.is_error and data["errorCategory"] == "validation" and data["isRetryable"] is False


# --- errores ---------------------------------------------------------------

def test_transient_fails_once_then_answers():
    state = ErroresState()
    errores = tools("errores", state=state)
    first, data = run(errores, "fetch_ticket_history", {"ticket_id": "TCK-4001"})
    assert first.is_error and data == {
        "errorCategory": "transient", "isRetryable": True, "message": data["message"], "tool": "fetch_ticket_history",
    }
    second, ok_data = run(errores, "fetch_ticket_history", {"ticket_id": "TCK-4001"})
    assert not second.is_error and ok_data["events"]
    assert state.calls["fetch_ticket_history"] == 2


def test_validation_error_for_malformed_user_id():
    outcome, data = run(tools("errores", state=ErroresState()), "get_user_profile", {"user_id": "1001"})
    assert outcome.is_error and data["errorCategory"] == "validation" and data["isRetryable"] is False


def test_business_error_is_not_retryable_and_has_user_message():
    outcome, data = run(tools("errores", state=ErroresState()), "reassign_license", {"user_id": "EMP-1001", "license": "editor", "seats": 12})
    assert outcome.is_error and data["errorCategory"] == "business" and data["isRetryable"] is False
    assert "cupo" in data["message"]


def test_permission_error():
    outcome, data = run(tools("errores", state=ErroresState()), "export_audit_log", {"scope": "all"})
    assert outcome.is_error and data["errorCategory"] == "permission" and data["isRetryable"] is False


def test_search_without_matches_is_valid_empty_list_not_error():
    outcome, data = run(tools("errores", state=ErroresState()), "search_tickets_by_user", {"user_id": "EMP-9999"})
    assert not outcome.is_error and data == {"user_id": "EMP-9999", "tickets": []}


def test_generic_mode_hides_the_category():
    errores = tools("errores", state=ErroresState(), estructurado=False)
    outcome, _ = run_text(errores, "export_audit_log", {"scope": "all"})
    assert outcome.is_error and outcome.text == "Operation failed"
    assert call_tool(errores["fetch_ticket_history"], {"ticket_id": "TCK-4001"}).text == "Operation failed"


def test_timeout_as_empty_list_hides_the_failure():
    errores = tools("errores", state=ErroresState(), fallo_como_vacio=True)
    outcome = call_tool(errores["fetch_ticket_history"], {"ticket_id": "TCK-4001"})
    # El timeout se devuelve como una lista vacía válida: indistinguible de «sin eventos».
    assert not outcome.is_error and json.loads(outcome.text)["events"] == []
    # La segunda llamada ya responde con datos: el fallo era transitorio.
    assert json.loads(call_tool(errores["fetch_ticket_history"], {"ticket_id": "TCK-4001"}).text)["events"]


def run_text(tool_map, name, args):
    return call_tool(tool_map[name], args), None


def test_non_numeric_seats_is_a_structured_validation_error_not_an_exception():
    outcome, data = run(tools("errores", state=ErroresState()), "reassign_license", {"user_id": "EMP-1001", "license": "editor", "seats": "doce"})
    assert outcome.is_error and data["errorCategory"] == "validation" and data["isRetryable"] is False
    assert "ValueError" not in outcome.text


def test_invalid_ticket_id_does_not_consume_the_transient_failure():
    errores = tools("errores", state=ErroresState())
    first, data = run(errores, "fetch_ticket_history", {"ticket_id": "TCK-0000"})
    assert first.is_error and data["errorCategory"] == "validation"
    # La primera llamada VÁLIDA es la que sufre el timeout: el ID inválido no la ha gastado.
    valid, valid_data = run(errores, "fetch_ticket_history", {"ticket_id": "TCK-4001"})
    assert valid.is_error and valid_data["errorCategory"] == "transient"


# --- amplio / acotado ------------------------------------------------------

def test_scope_sizes():
    assert len(make_tools("amplio")) == 18
    assert len(make_tools("acotado")) == 5


def test_every_wide_tool_maps_to_a_narrow_canonical_one():
    narrow = {t.name for t in make_tools("acotado")}
    assert {t.name for t in make_tools("amplio")} == set(CANONICAL)
    assert set(CANONICAL.values()) == narrow


def test_search_tickets_by_user_id_returns_exactly_that_users_tickets():
    # Antes, la búsqueda partía «EMP-1002» en «emp» y «1002» y devolvía tickets cuyo texto contenía «emp».
    tickets = load("tickets.json")
    for user_id in ("EMP-1002", "EMP-1010", "EMP-1020"):
        expected = [t["ticket_id"] for t in tickets if t["user_id"] == user_id]
        for family in ("acotado", "amplio"):
            _, data = run(tools(family), "search_tickets" if family == "acotado" else "list_tickets_by_user", {"query": user_id})
            assert data["ticket_ids"] == expected[:8] and data["total"] == len(expected)


def test_search_tickets_by_user_id_without_tickets_is_an_empty_list():
    _, data = run(tools("acotado"), "search_tickets", {"query": "EMP-9999"})
    assert data["ticket_ids"] == [] and data["total"] == 0


def test_search_tickets_by_words_still_works():
    _, data = run(tools("acotado"), "search_tickets", {"query": "wifi salas reuniones"})
    assert data["total"] >= 1


def test_wide_alias_returns_same_data_as_canonical():
    wide, narrow = tools("amplio"), tools("acotado")
    _, a = run(wide, "lookup_ticket", {"ticket_id": "TCK-4001"})
    _, b = run(narrow, "get_ticket", {"ticket_id": "TCK-4001"})
    assert a == b


@pytest.mark.parametrize("familia", ["routing", "errores", "amplio", "acotado"])
def test_every_tool_has_description_and_schema(familia):
    for t in make_tools(familia, state=ErroresState()) if familia == "errores" else make_tools(familia):
        assert t.description and t.input_schema["type"] == "object"


def test_server_config_and_tool_name():
    assert build_server("acotado")["name"] == SERVER_NAME
    assert tool_name("get_ticket") == "mcp__mesa__get_ticket"


def test_unknown_family_fails():
    with pytest.raises(ValueError):
        make_tools("otra")
