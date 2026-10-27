"""Tests de app3/01_coordinador: definición de subagentes, prompt del sintetizador con hallazgos y metadatos, y medidas sobre un RunRecord sintético. Sin modelo."""

import json

import pytest

from app3_sistema_multiagente.coordinator_gate import coordinator_gate
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app3_sistema_multiagente/01_coordinador.py")
ST, SK = mod.SEARCH_TICKETS, mod.SEARCH_KB


def test_each_subagent_has_only_its_tools():
    agents = mod.build_agents("haiku")
    assert agents["tickets_analyst"].tools == [ST]
    assert agents["kb_analyst"].tools == [SK]
    assert agents["synthesizer"].tools == []
    assert all(a.model == "haiku" and a.background is False for a in agents.values())
    # La descripción es lo que el coordinador usa para elegir.
    assert all(a.description for a in agents.values())


def test_coordinator_options():
    options = mod.build_options(anti=None, budget=1.0, model="sonnet", subagent_model="haiku")
    assert "Agent" in options.allowed_tools and options.tools == ["Agent"]
    assert {ST, SK} <= set(options.allowed_tools)
    assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert options.env["CLAUDE_CODE_FORK_SUBAGENT"] == "0"
    assert options.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert options.setting_sources == [] and options.max_budget_usd == 1.0
    # La barrera es el hook, no `tools=["Agent"]` ni el prompt: las tools MCP siguen visibles para el coordinador.
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.hooks == [coordinator_gate]


@pytest.mark.parametrize("anti", [None, *mod.ANTI_VARIANTS])
def test_each_variant_has_its_own_prompt(anti):
    prompt = mod.coordinator_prompt(anti)
    assert prompt and ("Objetivo" in prompt) == (anti not in {"procedimental"})


def test_synthesizer_prompt_includes_every_finding_with_metadata():
    findings = [
        {"source": "tickets_analyst", "content": "La VPN se cae", "metadata": {"ticket_id": "TCK-4015", "created_at": "2026-09-10"}},
        {"source": "kb_analyst", "content": "Perfil TCP", "metadata": {"article_id": "KB-109", "updated_at": "2026-05-01"}},
    ]
    prompt = mod.synthesizer_prompt("¿Qué pasa con la red?", findings)
    assert prompt.index("¿Qué pasa con la red?") < prompt.index("HALLAZGOS")
    for finding in findings:
        assert finding["content"] in prompt
        for value in finding["metadata"].values():
            assert value in prompt


def agent_call(cid, subagent, prompt, response):
    return ToolCall(cid, "Agent", {"subagent_type": subagent, "prompt": prompt}, response, "principal", True, False, "ok")


def sub_call(cid, name, agent, payload, response):
    return ToolCall(cid, name, {"query": "x"}, response, agent, True, False, json.dumps(payload))


def run_record(synth_prompt):
    return RunRecord(tool_calls=[
        agent_call("a1", "tickets_analyst", "busca", "r1"),
        agent_call("a2", "kb_analyst", "busca", "r1"),
        sub_call("t1", ST, "tickets_analyst", {"results": [{"metadata": {"ticket_id": "TCK-4015"}},
                                                           {"metadata": {"ticket_id": "TCK-4021"}}]}, "r2"),
        sub_call("t2", SK, "kb_analyst", {"results": [{"metadata": {"article_id": "KB-111"}}]}, "r3"),
        agent_call("a3", "synthesizer", synth_prompt, "r4"),
    ])


def test_invoked_agents_in_order():
    assert mod.invoked_agents(run_record("")) == ["tickets_analyst", "kb_analyst", "synthesizer"]


def test_findings_coverage_in_synthesizer_prompt():
    full = mod.findings_coverage(run_record("TCK-4015, TCK-4021 y KB-111"))
    assert full == {"found": ["KB-111", "TCK-4015", "TCK-4021"], "passed": ["KB-111", "TCK-4015", "TCK-4021"], "missing": []}
    empty = mod.findings_coverage(run_record("responde a la pregunta"))
    assert empty["missing"] == ["KB-111", "TCK-4015", "TCK-4021"]


def test_subtopic_coverage_detects_missing_wifi():
    assert mod.subtopics_covered("VPN, wifi de las salas e impresora de planta") == {"vpn": True, "wifi": True, "impresora": True}
    assert mod.subtopics_covered("Solo la VPN falla") == {"vpn": True, "wifi": False, "impresora": False}
