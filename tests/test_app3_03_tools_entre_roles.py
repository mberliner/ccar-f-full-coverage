"""Tests de app3/03_tools_entre_roles: tools por rol y variante, llamadas fuera de rol, URLs no documento, delegaciones y opciones del coordinador. Sin modelo."""

import json

from harness.data import load
from harness.offline import run_hook
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/03_tools_entre_roles.py")

P = "mcp__investigacion__"
SEARCH_KB, LOAD, FETCH, VERIFY, SEARCH_T = (P + n for n in ("search_kb", "load_document", "fetch_url", "verify_fact", "search_tickets"))
ALL = [SEARCH_T, SEARCH_KB, FETCH, LOAD, VERIFY]
CATALOG = load("documentos.json")
DOC_URL = next(u["url"] for u in CATALOG["urls"] if u["is_document"])
JUNK_URL = next(u["url"] for u in CATALOG["urls"] if not u["is_document"])


def call(cid, name, agent, input_=None, *, error=False, text="{}"):
    return ToolCall(cid, name, input_ or {}, "r1", agent, True, error, text)


def delegation(cid, subagent):
    return call(cid, "Agent", "principal", {"subagent_type": subagent, "prompt": "x"})


# --- tools por rol y variante ---------------------------------------------------------

def test_correct_roles_are_scoped_with_one_cross_role_tool():
    roles = mod.role_tools(None)
    assert roles["researcher"] == [SEARCH_KB, LOAD]
    assert roles["synthesizer"] == [VERIFY]  # la tool cross-role acotada


def test_todas_gives_the_synthesizer_every_tool():
    roles = mod.role_tools("todas")
    assert set(roles["synthesizer"]) == {SEARCH_T, SEARCH_KB, FETCH, LOAD, VERIFY}
    assert roles["researcher"] == mod.role_tools(None)["researcher"]


def test_fetch_url_swaps_the_validating_tool_for_the_generic_one():
    roles = mod.role_tools("fetch_url")
    assert FETCH in roles["researcher"] and LOAD not in roles["researcher"]
    assert roles["synthesizer"] == [VERIFY]


def test_sin_verify_leaves_the_synthesizer_without_tools():
    roles = mod.role_tools("sin_verify")
    assert roles["synthesizer"] == [] and roles["researcher"] == mod.role_tools(None)["researcher"]


def test_build_agents_applies_the_role_tools_in_the_foreground():
    for anti in (None, "todas", "fetch_url", "sin_verify"):
        agents = mod.build_agents(anti, "modelo")
        assert set(agents) == {"researcher", "synthesizer"}
        for name, agent in agents.items():
            assert agent.tools == mod.role_tools(anti)[name]
            assert agent.background is False and agent.model == "modelo" and agent.description and agent.prompt


def test_variants():
    assert mod.ANTI_VARIANTS == ["todas", "fetch_url", "sin_verify"]


# --- medidas sobre el RunRecord --------------------------------------------------------

def test_out_of_role_counts_calls_a_role_should_not_make():
    rec = RunRecord(tool_calls=[
        delegation("d1", "researcher"), delegation("d2", "synthesizer"),
        call("c1", SEARCH_KB, "researcher"), call("c2", LOAD, "researcher"),
        call("c3", VERIFY, "synthesizer"),
        call("c4", SEARCH_KB, "synthesizer"), call("c5", FETCH, "synthesizer"),  # fuera de rol
    ])
    assert mod.out_of_role(rec) == {"synthesizer": 2}
    assert mod.out_of_role(RunRecord()) == {}


def test_a_coordinator_that_searches_is_out_of_role():
    rec = RunRecord(tool_calls=[delegation("d1", "researcher"), call("c1", SEARCH_KB, "principal")])
    assert mod.out_of_role(rec) == {"principal": 1}


def test_junk_urls_fetched_counts_generic_fetches_of_non_documents():
    rec = RunRecord(tool_calls=[
        call("c1", FETCH, "researcher", {"url": DOC_URL}),
        call("c2", FETCH, "researcher", {"url": JUNK_URL}),
        call("c3", FETCH, "researcher", {"url": JUNK_URL}, error=True),  # un fallo no mete basura en los hallazgos
        call("c4", LOAD, "researcher", {"url": DOC_URL}),
    ])
    assert mod.junk_urls_fetched(rec) == 1


def test_rejected_loads_counts_load_document_validation_errors():
    rejected = json.dumps({"errorCategory": "validation", "isRetryable": False, "message": "la URL no es un documento"})
    rec = RunRecord(tool_calls=[
        call("c1", LOAD, "researcher", {"url": JUNK_URL}, error=True, text=rejected),
        call("c2", LOAD, "researcher", {"url": DOC_URL}),
        call("c3", FETCH, "researcher", {"url": JUNK_URL}, error=True),
    ])
    assert mod.rejected_loads(rec) == 1


def test_delegations_counts_agent_calls_by_type():
    rec = RunRecord(tool_calls=[delegation("d1", "researcher"), delegation("d2", "synthesizer"), delegation("d3", "synthesizer"),
                                call("c1", SEARCH_KB, "researcher")])
    assert mod.delegations(rec) == {"researcher": 1, "synthesizer": 2}
    assert mod.total_delegations(rec) == 3
    assert mod.delegations(RunRecord()) == {}


def test_routed_to_coordinator_counts_complex_claims_sent_back():
    routed = json.dumps({"claim_id": "C-4", "status": "enrutar al coordinador", "article_ids": ["KB-114", "KB-115"]})
    simple = json.dumps({"claim_id": "C-1", "supported": True, "article_ids": ["KB-114"]})
    rec = RunRecord(tool_calls=[call("c1", VERIFY, "synthesizer", text=simple), call("c2", VERIFY, "synthesizer", text=routed)])
    assert mod.routed_to_coordinator(rec) == 1
    assert mod.verify_calls(rec) == 2


# --- petición y opciones -----------------------------------------------------------------

def test_request_lists_every_url_and_claim_of_the_catalog():
    for entry in CATALOG["urls"]:
        assert entry["url"] in mod.REQUEST
    for claim in CATALOG["afirmaciones"]:
        assert claim["claim_id"] in mod.REQUEST and claim["text"] in mod.REQUEST


def test_coordinator_prompt_does_not_name_the_cross_role_tool_or_the_url_rule():
    # El reparto de tools es lo que se mide: el prompt no debe explicarlo.
    prompt = mod.coordinator_prompt().lower()
    for word in ("verify_fact", "load_document", "fetch_url"):
        assert word not in prompt


def test_coordinator_gate_denies_the_main_agent_and_lets_subagents_through():
    # `tools=["Agent"]` solo limita las integradas: las tools MCP siguen visibles para el coordinador.
    # La barrera es este hook, no el prompt. Un subagente trae `agent_id`; el agente principal, no.
    for name in ALL:
        denied = run_hook(mod.coordinator_gate, "PreToolUse", name, {"url": DOC_URL})
        assert denied.decision == "deny" and "subagentes" in denied.reason
        assert run_hook(mod.coordinator_gate, "PreToolUse", name, {"url": DOC_URL}, agent_id="agent-1").decision is None


def test_gate_is_registered_for_the_investigation_tools_only():
    options = mod.build_options(None, budget=0.5, model="m", subagent_model="s")
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.matcher == "mcp__investigacion__.*" and matcher.hooks == [mod.coordinator_gate]
    assert set(options.hooks) == {"PreToolUse"}


def test_coordinator_attempts_are_counted_as_out_of_role():
    # La barrera deniega la llamada, pero el intento queda en el registro y se ve como fuera de rol.
    rec = RunRecord(tool_calls=[call("c1", VERIFY, "principal", {"claim_id": "C-1"}, error=True, text="denegado")])
    assert mod.out_of_role(rec) == {"principal": 1}
    assert mod.coordinator_attempts(rec) == 1
    assert mod.coordinator_attempts(RunRecord()) == 0


def test_options_follow_the_subagent_pattern_with_the_extended_server():
    options = mod.build_options(None, budget=0.5, model="m", subagent_model="s")
    assert options.tools == ["Agent"] and options.permission_mode == "dontAsk"
    assert options.setting_sources == [] and options.max_budget_usd == 0.5
    assert "investigacion" in options.mcp_servers
    assert set(mod.role_tools("todas")["synthesizer"]) <= set(options.allowed_tools) and "Agent" in options.allowed_tools
    assert options.env["CLAUDE_CODE_FORK_SUBAGENT"] == "0"
    assert options.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert set(options.agents) == {"researcher", "synthesizer"}
