"""Tests de `harness/recorder.py` sobre un flujo construido con los tipos reales del SDK. Sin modelo."""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from harness.recorder import MAIN, record

MODEL = "modelo-sintetico"


def assistant(blocks, message_id, parent=None):
    return AssistantMessage(content=blocks, model=MODEL, message_id=message_id, parent_tool_use_id=parent)


def results(*pairs, parent=None):
    return UserMessage(
        content=[ToolResultBlock(tool_use_id=i, content="...", is_error=err) for i, err in pairs],
        parent_tool_use_id=parent,
    )


def result_message(subtype="success", denials=None):
    return ResultMessage(
        subtype=subtype, duration_ms=1, duration_api_ms=1, is_error=subtype != "success", num_turns=3,
        session_id="s", total_cost_usd=0.0123, result="hecho", permission_denials=denials,
    )


async def stream(messages):
    for message in messages:
        yield message


def run(messages):
    return asyncio.run(record(stream(messages), echo=False))


def test_full_run():
    messages = [
        SystemMessage("init", {"tools": ["Read", "Agent"], "mcp_servers": [], "skills": [], "plugins": [],
                               "apiKeySource": "ANTHROPIC_API_KEY", "model": MODEL}),
        # Una respuesta partida en dos mensajes con el mismo id: dos llamadas en paralelo.
        assistant([TextBlock("miro dos tickets"), ToolUseBlock("t1", "get_ticket", {"id": 1})], "m1"),
        assistant([ToolUseBlock("t2", "get_ticket", {"id": 2})], "m1"),
        results(("t1", False), ("t2", True)),
        # Carga de tool search: no cuenta como llamada del modelo.
        assistant([ToolUseBlock("ts", "ToolSearch", {"query": "refund"})], "m2"),
        results(("ts", False)),
        # Subagente lanzado con Agent; su llamada se atribuye a su tipo.
        assistant([ToolUseBlock("a1", "Agent", {"subagent_type": "investigador", "prompt": "x"})], "m3"),
        assistant([ToolUseBlock("t3", "Read", {"file_path": "kb.md"})], "m4", parent="a1"),
        results(("t3", False), parent="a1"),
        results(("a1", False)),
        # Llamada denegada: recibe tool_result, pero no se ejecutó.
        assistant([ToolUseBlock("t4", "issue_refund", {"amount": 900})], "m5"),
        results(("t4", True)),
        result_message(denials=[{"tool_name": "issue_refund", "tool_use_id": "t4", "tool_input": {}}]),
    ]
    rec = run(messages)

    assert rec.init["apiKeySource"] == "ANTHROPIC_API_KEY"
    assert [c.id for c in rec.tool_calls] == ["t1", "t2", "a1", "t3", "t4"]
    assert rec.tool_search_loads == 1
    assert {resp: [c.id for c in calls] for resp, calls in rec.parallel_groups().items()} == {"r1": ["t1", "t2"]}
    agents = rec.by_agent()
    assert [c.id for c in agents["investigador"]] == ["t3"]
    assert all(c.agent == MAIN for c in agents[MAIN])
    calls = {c.id: c for c in rec.tool_calls}
    assert calls["t2"].executed and calls["t2"].is_error
    assert not calls["t4"].executed
    assert (rec.final_text, rec.num_turns, rec.cost_usd, len(rec.denials)) == ("hecho", 3, 0.0123, 1)
    assert not rec.budget_exceeded


def test_budget_cut_is_recorded_not_raised(capsys):
    rec = asyncio.run(record(stream([result_message("error_max_budget_usd")]), echo=True))
    assert rec.budget_exceeded and rec.is_error
    assert "presupuesto agotado" in capsys.readouterr().out


def test_echo_prints_one_line_per_event(capsys):
    run_messages = [assistant([ToolUseBlock("t1", "Read", {"file_path": "a"})], "m1"), results(("t1", False))]
    asyncio.run(record(stream(run_messages), echo=True))
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("[llamada r1 · principal] Read")
    assert lines[1].startswith("[resultado r1 · principal] Read ok")


def test_result_text_is_kept_for_downstream_extraction():
    blocks = [{"type": "text", "text": '{"ticket_id": "TCK-1"}'}]
    messages = [
        assistant([ToolUseBlock("t1", "get_ticket", {}), ToolUseBlock("t2", "Read", {})], "m1"),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content=blocks, is_error=False),
                             ToolResultBlock(tool_use_id="t2", content="texto plano", is_error=False)]),
    ]
    calls = {c.id: c for c in run(messages).tool_calls}
    assert calls["t1"].result_text == '{"ticket_id": "TCK-1"}'
    assert calls["t2"].result_text == "texto plano"


def test_budget_cut_followed_by_result_error_returns_the_record():
    # El SDK emite el ResultMessage del corte y después lanza ResultError: la
    # ejecución tiene que terminar con su registro, no tirar el script entero.
    from claude_agent_sdk import ResultError

    async def cut_then_raise():
        yield result_message("error_max_budget_usd")
        raise ResultError("Reached maximum budget", {"subtype": "error_max_budget_usd"}, exit_code=1)

    rec = asyncio.run(record(cut_then_raise(), echo=False))
    assert rec.budget_exceeded and rec.is_error


def test_result_error_without_result_message_still_raises():
    import pytest
    from claude_agent_sdk import ResultError

    async def raise_only():
        raise ResultError("fallo", {"subtype": "error_during_execution"}, exit_code=1)
        yield  # pragma: no cover

    with pytest.raises(ResultError):
        asyncio.run(record(raise_only(), echo=False))


def test_messages_per_response_distinguishes_split_from_single_message(capsys):
    # r1 llega partida en tres mensajes (uno por llamada); r2 llega entera.
    messages = [
        assistant([ToolUseBlock("a", "Agent", {"subagent_type": "x"})], "m1"),
        assistant([ToolUseBlock("b", "Agent", {"subagent_type": "y"})], "m1"),
        assistant([ToolUseBlock("c", "Agent", {"subagent_type": "z"})], "m1"),
        assistant([TextBlock("hecho"), ToolUseBlock("d", "Read", {"file_path": "a"})], "m2"),
        result_message(),
    ]
    rec = asyncio.run(record(stream(messages), echo=True))
    assert rec.messages_per_response == {"r1": 3, "r2": 1}
    out = capsys.readouterr().out
    assert "mensajes=4 respuestas=2 partidas=r1:3" in out


def test_no_split_responses_omits_partidas(capsys):
    asyncio.run(record(stream([assistant([ToolUseBlock("a", "Read", {"file_path": "a"})], "m1"), result_message()]), echo=True))
    out = capsys.readouterr().out
    assert "mensajes=1 respuestas=1" in out and "partidas" not in out
