"""Tests de app2/06_sesiones: diff de estados, aviso de cambios concreto, resumen estructurado y decisión reanudar/empezar de nuevo. Sin modelo."""

import json

from app2_agente_con_control.servers.helpdesk import HelpdeskState
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app2_agente_con_control/06_sesiones.py")
USER = mod.EMPLOYEE


def test_snapshot_reflects_overrides():
    state = HelpdeskState()
    before = mod.snapshot(state)
    mod.apply_phase_change(state)
    after = mod.snapshot(state)
    assert before["tickets"][mod.RESOLVED_TICKET] != "RESOLVED"
    assert after["tickets"][mod.RESOLVED_TICKET] == "RESOLVED"
    assert before["kb"][mod.OBSOLETE_ARTICLE] is False and after["kb"][mod.OBSOLETE_ARTICLE] is True


def test_diff_lists_only_what_changed():
    before = {"tickets": {"TCK-1": "OPEN", "TCK-2": "OPEN"}, "kb": {"KB-1": False, "KB-2": False}}
    after = {"tickets": {"TCK-1": "RESOLVED", "TCK-2": "OPEN"}, "kb": {"KB-1": False, "KB-2": True}}
    assert mod.diff_states(before, after) == [
        {"kind": "ticket", "id": "TCK-1", "before": "OPEN", "after": "RESOLVED"},
        {"kind": "kb", "id": "KB-2", "before": "vigente", "after": "obsoleto"},
    ]


def test_change_notice_is_concrete_and_targeted():
    changes = [{"kind": "ticket", "id": "TCK-1", "before": "OPEN", "after": "RESOLVED"},
               {"kind": "kb", "id": "KB-2", "before": "vigente", "after": "obsoleto"}]
    notice = mod.change_notice(changes)
    assert "TCK-1" in notice and "OPEN → RESOLVED" in notice and "KB-2" in notice
    # Pide reconsultar solo lo cambiado, no explorar todo de nuevo (1.7-S4).
    assert "solo" in notice.lower()
    assert mod.change_notice([]) == ""


def call(name, payload):
    return ToolCall(f"id-{name}-{len(json.dumps(payload))}", name, {}, "r1", "principal", True, False, json.dumps(payload))


BASE = RunRecord(tool_calls=[
    call(mod.LIST_TICKETS, {"user_id": USER, "tickets": [{"ticket_id": "TCK-1", "status": "OPEN"},
                                                         {"ticket_id": "TCK-2", "status": "OPEN"}]}),
    call(mod.SEARCH_KB, {"articles": [{"article_id": "KB-2", "title": "x"}]}),
    call(mod.GET_TICKET, {"ticket_id": "TCK-2", "status": "OPEN"}),
    call(mod.SEARCH_KB, {"articles": [{"article_id": "KB-3", "title": "y"}]}),
])


def test_findings_from_base_session():
    assert mod.findings(BASE) == {"tickets": {"TCK-1": "OPEN", "TCK-2": "OPEN"}, "kb": ["KB-2", "KB-3"]}


def test_stale_ratio_counts_results_touching_changed_ids():
    changes = [{"kind": "ticket", "id": "TCK-1", "before": "OPEN", "after": "RESOLVED"}]
    assert mod.stale_ratio(BASE, changes) == 0.25
    changes.append({"kind": "kb", "id": "KB-3", "before": "vigente", "after": "obsoleto"})
    assert mod.stale_ratio(BASE, changes) == 0.5


def test_decide_resume_or_fresh():
    assert mod.decide(0.25) == "reanudar"
    assert mod.decide(0.5) == "nueva"
    assert mod.decide(0.0) == "reanudar"


def test_structured_summary_separates_valid_from_changed():
    changes = [{"kind": "ticket", "id": "TCK-1", "before": "OPEN", "after": "RESOLVED"}]
    summary = mod.structured_summary(mod.findings(BASE), changes)
    valid, changed = summary.split("Cambiado desde entonces")
    assert "TCK-2: OPEN" in valid and "TCK-1" not in valid
    assert "TCK-1: OPEN → RESOLVED" in changed


def test_resume_command_for_cli():
    assert mod.cli_resume_command("app2") == "claude --resume app2"
