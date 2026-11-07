"""Tests del servidor MCP `helpdesk` de app2: verificación, puerta del reembolso, handoff y cambios de estado. Sin modelo."""

import json

import pytest

from datos.generar_sinteticos import build_all
from app2_agente_con_control.servers.helpdesk import (
    HelpdeskState,
    SERVER_NAME,
    build_server,
    make_tools,
    reimbursement_ticket,
)
from harness.offline import call_tool


def tools(state=None, **kwargs):
    state = state or HelpdeskState()
    return state, {t.name: t for t in make_tools(state, **kwargs)}


def payload(outcome):
    return json.loads(outcome.text)


def test_verify_employee_marks_session_state():
    state, t = tools()
    ok = call_tool(t["verify_employee"], {"user_id": "EMP-1004"})
    assert not ok.is_error and payload(ok)["verified"] is True
    assert state.verified == {"EMP-1004"}
    bad = call_tool(t["verify_employee"], {"user_id": "EMP-9999"})
    assert bad.is_error and payload(bad)["errorCategory"] == "not_found"
    assert state.verified == {"EMP-1004"}


def test_gate_blocks_reimbursement_until_verified():
    state, t = tools()
    ticket = reimbursement_ticket(120.0)
    args = {"user_id": ticket["user_id"], "ticket_id": ticket["ticket_id"], "amount_eur": 120.0}
    refused = call_tool(t["process_reimbursement"], args)
    assert refused.is_error and payload(refused)["errorCategory"] == "prerequisite"
    assert payload(refused)["isRetryable"] is False and state.paid == []
    call_tool(t["verify_employee"], {"user_id": ticket["user_id"]})
    paid = call_tool(t["process_reimbursement"], args)
    assert not paid.is_error and state.paid == [{**args, "verified": True}]


def test_without_gate_pays_unverified():
    # Variante anti de app2/01: la regla solo está en el prompt.
    state, t = tools(gate=False)
    ticket = reimbursement_ticket(120.0)
    outcome = call_tool(t["process_reimbursement"],
                        {"user_id": ticket["user_id"], "ticket_id": ticket["ticket_id"], "amount_eur": 120.0})
    assert not outcome.is_error and state.paid[0]["verified"] is False


def test_reimbursement_must_match_ticket():
    state, t = tools()
    ticket = reimbursement_ticket(120.0)
    call_tool(t["verify_employee"], {"user_id": ticket["user_id"]})
    wrong = call_tool(t["process_reimbursement"],
                      {"user_id": ticket["user_id"], "ticket_id": ticket["ticket_id"], "amount_eur": 999.0})
    assert wrong.is_error and payload(wrong)["errorCategory"] == "validation"


def test_get_ticket_returns_raw_formats():
    _, t = tools()
    ticket = reimbursement_ticket(500.01)
    raw = payload(call_tool(t["get_ticket"], {"ticket_id": ticket["ticket_id"]}))
    # El servidor no normaliza: eso lo hace el hook PostToolUse de app2/02.
    assert raw["created_at"] == ticket["created_at"] and raw["status"] == ticket["status"]
    missing = call_tool(t["get_ticket"], {"ticket_id": "TCK-0"})
    assert missing.is_error and payload(missing)["errorCategory"] == "not_found"


def test_structured_handoff_requires_all_fields():
    state, t = tools()
    incomplete = call_tool(t["escalate_to_human"], {"user_id": "EMP-1004", "ticket_id": "TCK-1", "root_cause": ""})
    assert incomplete.is_error and set(payload(incomplete)["missing"]) == {"root_cause", "amount_eur", "recommended_action"}
    full = {"user_id": "EMP-1004", "ticket_id": "TCK-1", "root_cause": "importe sobre el umbral",
            "amount_eur": 845.5, "recommended_action": "aprobación de Finanzas"}
    assert not call_tool(t["escalate_to_human"], full).is_error
    assert state.escalations == [full]


def test_free_text_handoff_variant():
    state, t = tools(handoff="free_text")
    outcome = call_tool(t["escalate_to_human"], {"summary": "el empleado quiere su dinero"})
    assert not outcome.is_error and state.escalations == [{"summary": "el empleado quiere su dinero"}]


def test_state_changes_between_phases():
    # app2/06 cambia el estado del servidor sin tocar datos/sinteticos/.
    state, t = tools()
    ticket = reimbursement_ticket(120.0)
    state.ticket_overrides[ticket["ticket_id"]] = {"status": "RESOLVED"}
    assert payload(call_tool(t["get_ticket"], {"ticket_id": ticket["ticket_id"]}))["status"] == "RESOLVED"
    listed = payload(call_tool(t["list_employee_tickets"], {"user_id": ticket["user_id"]}))
    assert ticket["ticket_id"] in {x["ticket_id"] for x in listed["tickets"]}
    state.kb_overrides["KB-108"] = {"obsolete": True}
    hits = payload(call_tool(t["search_kb"], {"query": "sincronización correo"}))["articles"]
    assert next(a for a in hits if a["article_id"] == "KB-108")["obsolete"] is True


def test_server_config():
    config = build_server(HelpdeskState())
    assert config["type"] == "sdk" and config["name"] == SERVER_NAME


@pytest.mark.parametrize("amount", [120.0, 500.0, 500.01])
def test_reimbursement_tickets_exist(amount):
    assert reimbursement_ticket(amount)["amount_eur"] == amount


def test_name_lookup_is_opt_in_so_the_other_modules_keep_their_tools():
    # `app2/04` la activa; el resto de módulos de app2 no debe ver una tool más.
    _, default = tools()
    _, with_lookup = tools(lookup=True)
    assert "find_employee_by_name" not in default
    assert set(with_lookup) - set(default) == {"find_employee_by_name"}


def test_name_lookup_returns_every_homonym_and_never_picks_one():
    # TS 5.2-K4: una búsqueda con varias coincidencias las devuelve todas, para que el agente pida un identificador.
    _, t = tools(lookup=True)
    outcome = call_tool(t["find_employee_by_name"], {"name": "Laura Gómez"})
    data = payload(outcome)
    assert not outcome.is_error
    assert data["match_count"] == 2
    assert {m["user_id"] for m in data["matches"]} == {"EMP-1004", "EMP-1018"}
    assert {m["department"] for m in data["matches"]} == {"Finanzas", "Ventas"}
    assert "user_id" not in data, "el servidor no elige por el agente"


def test_name_lookup_with_a_single_match_and_with_none():
    _, t = tools(lookup=True)
    users = json.loads(build_all()["usuarios.json"])
    unique = next(u for u in users if sum(v["name"] == u["name"] for v in users) == 1)
    one = payload(call_tool(t["find_employee_by_name"], {"name": unique["name"].upper()}))  # sin distinguir mayúsculas
    assert one["match_count"] == 1 and one["matches"][0]["user_id"] == unique["user_id"]
    none = call_tool(t["find_employee_by_name"], {"name": "Nadie Inexistente"})
    assert not none.is_error, "sin coincidencias es un resultado vacío válido, no un fallo (TS 2.2)"
    assert payload(none)["match_count"] == 0


def test_name_lookup_does_not_verify_the_employee():
    state, t = tools(lookup=True)
    call_tool(t["find_employee_by_name"], {"name": "Laura Gómez"})
    assert state.verified == set()
