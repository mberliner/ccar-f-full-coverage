"""Tests de la barrera compartida del coordinador de app3 (`coordinator_gate.py`). Sin modelo.

PROPÓSITO: comprobar que el hook deniega las tools del servidor al agente
principal y las deja pasar a los subagentes, y que la medida de intentos cuenta
solo lo que hizo el coordinador.

POR QUÉ EXISTE: `tools=["Agent"]` no oculta las tools MCP al coordinador; si la
barrera falla, las medidas de 01, 02 y 03 mezclan su trabajo con el de los
subagentes sin que nada lo avise.

QUÉ NO HACE: no comprueba que el SDK llame al hook ni que el subagente traiga
`agent_id` en ejecución; eso lo demuestra la sonda con modelo (ver README de app3).
"""

from app3_sistema_multiagente.coordinator_gate import coordinator_attempts, coordinator_gate, coordinator_hooks
from app3_sistema_multiagente.servers.investigacion import tool_name
from harness.offline import run_hook
from harness.recorder import MAIN, RunRecord, ToolCall

SEARCH_TICKETS = tool_name("search_tickets")


def call(name: str, agent: str, n: int = 1) -> ToolCall:
    return ToolCall(f"id{n}", name, {}, "r1", agent, True, False, "x")


def test_gate_denies_the_main_agent():
    denied = run_hook(coordinator_gate, "PreToolUse", SEARCH_TICKETS, {"query": "vpn"})
    assert denied.decision == "deny" and "subagentes" in denied.reason


def test_gate_lets_subagents_through():
    allowed = run_hook(coordinator_gate, "PreToolUse", SEARCH_TICKETS, {"query": "vpn"}, agent_id="agent-1")
    assert allowed.decision is None


def test_hooks_match_only_the_investigation_server():
    hooks = coordinator_hooks()
    assert set(hooks) == {"PreToolUse"}
    (matcher,) = hooks["PreToolUse"]
    assert matcher.matcher == "mcp__investigacion__.*" and matcher.hooks == [coordinator_gate]


def test_attempts_count_only_main_agent_calls_to_server_tools():
    rec = RunRecord(tool_calls=[
        call("Agent", MAIN, 1),  # delegar no es un intento
        call(SEARCH_TICKETS, MAIN, 2),  # el coordinador busca él: intento
        call(SEARCH_TICKETS, "tickets_analyst", 3),  # el subagente, en su rol
        call(tool_name("search_kb"), MAIN, 4),
    ])
    assert coordinator_attempts(rec) == 2
    assert coordinator_attempts(RunRecord()) == 0
