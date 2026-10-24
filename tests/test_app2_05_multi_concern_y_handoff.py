"""Tests de app2/05_multi_concern_y_handoff: descomposición, extracción y fusión de case facts, render del bloque y validación del handoff. Sin modelo."""

import json

from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app2_agente_con_control/05_multi_concern_y_handoff.py")


def test_ticket_decomposes_into_three_concerns():
    ticket = mod.multi_concern_ticket()
    assert mod.decompose(ticket["description"]) == ["red", "licencias", "gastos"]


def test_user_facts_keep_numbers_and_dates_per_concern():
    facts = mod.extract_user_facts(
        "El ratón me costó 34,50 EUR y lo compré el 12/09/2026. La licencia caduca el 28/10/2026."
    )
    assert facts["gastos"]["amounts_eur"] == [34.5]
    assert facts["gastos"]["dates"] == ["12/09/2026"]
    assert facts["licencias"]["dates"] == ["28/10/2026"]
    assert "red" not in facts


def call(name, payload, response="r1"):
    return ToolCall(f"id-{name}", name, {}, response, "principal", True, False, json.dumps(payload))


def test_tool_facts_from_results():
    ticket = mod.multi_concern_ticket()
    rec = RunRecord(tool_calls=[
        call(mod.GET_TICKET, ticket),
        call(mod.SEARCH_KB, {"articles": [{"article_id": "KB-110", "title": "VPN: perfil antiguo (obsoleto)",
                                           "superseded_by": "KB-109"}]}),
        ToolCall("x", mod.GET_TICKET, {}, "r1", "principal", True, True, '{"errorCategory": "not_found"}'),
        # Otro ticket consultado después no sustituye al del caso.
        call(mod.GET_TICKET, {**ticket, "ticket_id": "TCK-4001", "status": "RESOLVED"}, response="r2"),
    ])
    facts = mod.extract_tool_facts(rec, ticket["ticket_id"])
    assert facts["caso"]["ticket_id"] == ticket["ticket_id"] and facts["caso"]["user_id"] == ticket["user_id"]
    assert facts["caso"]["status"] == ticket["status"]
    assert facts["red"]["kb"] == ["KB-110 (sustituido por KB-109)"]


def test_merge_keeps_old_and_adds_new():
    old = {"gastos": {"amounts_eur": [34.5], "dates": ["12/09/2026"]}, "caso": {"status": "OPEN"}}
    new = {"gastos": {"amounts_eur": [34.5], "dates": ["30/10/2026"]}, "caso": {"status": "en curso"}}
    merged = mod.merge_facts(old, new)
    assert merged["gastos"] == {"amounts_eur": [34.5], "dates": ["12/09/2026", "30/10/2026"]}
    assert merged["caso"]["status"] == "en curso"  # el escalar más reciente gana
    assert old["gastos"]["dates"] == ["12/09/2026"]  # sin mutar el original


def test_render_block_has_every_fact_and_header():
    block = mod.render_case_facts({"gastos": {"amounts_eur": [34.5]}, "caso": {"ticket_id": "TCK-4053"}})
    assert block.startswith("CASE FACTS")
    assert "34.5" in block and "TCK-4053" in block
    assert block.index("[caso]") < block.index("[gastos]")  # el caso primero, después cada asunto


def test_prompt_puts_case_facts_outside_summary():
    prompt = mod.turn_prompt("resumen en prosa", {"gastos": {"amounts_eur": [34.5]}}, "mensaje nuevo", anti=None)
    assert prompt.index("resumen en prosa") < prompt.index("CASE FACTS") < prompt.index("mensaje nuevo")
    anti = mod.turn_prompt("resumen en prosa", {"gastos": {"amounts_eur": [34.5]}}, "mensaje nuevo", anti="resumen")
    assert "CASE FACTS" not in anti and "34.5" not in anti


def test_handoff_check_against_case_facts():
    facts = {"caso": {"ticket_id": "TCK-4053", "user_id": "EMP-1012"}, "gastos": {"amounts_eur": [34.5]}}
    good = {"user_id": "EMP-1012", "ticket_id": "TCK-4053", "root_cause": "VPN, licencia y reembolso",
            "amount_eur": 34.5, "recommended_action": "pagar 34,50 EUR y renovar la licencia"}
    assert mod.check_handoff(good, facts) == []
    assert mod.check_handoff({**good, "amount_eur": 0}, facts) == ["amount_eur 0 ≠ 34.5"]
    dated = {**facts, "gastos": {"amounts_eur": [34.5], "dates": ["12/09/2026", "30/10/2026"]}}
    with_dates = {**good, "recommended_action": "pagar 34,50 EUR (compra del 12/09/2026) antes del 30/10/2026"}
    assert mod.check_handoff(with_dates, dated) == []
    iso = {**good, "recommended_action": "pagar 34,50 EUR (compra del 2026-09-12) antes del 30/10/2026"}
    assert mod.check_handoff(iso, dated) == []
    vague = {**good, "recommended_action": "pagar 34,50 EUR antes del 30/10"}
    assert mod.check_handoff(vague, dated) == ["falta la fecha 12/09/2026", "falta la fecha 30/10/2026"]
    assert mod.check_handoff({"summary": "quiere su dinero"}, facts) == [
        "sin campo user_id", "sin campo ticket_id", "sin campo root_cause", "sin campo amount_eur",
        "sin campo recommended_action",
    ]
