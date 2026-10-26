"""Tests de app1/05_scoping_y_tool_choice: batería de scoping, medida de acierto y consistencia, petición por modo de `tool_choice`, secuencia forzado → auto y clasificador de la primera respuesta. Sin modelo."""

import json
from types import SimpleNamespace

import pytest

from app1_agente_unico.servers.mesa import CANONICAL
from harness.data import load
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app1_agente_unico/05_scoping_y_tool_choice.py")


def call(name, response="r1"):
    return ToolCall(f"id-{name}-{response}", name, {}, response, "principal", True, False, "x")


# --- scoping: batería y medida ---------------------------------------------------

def test_battery_has_six_requests_for_the_five_narrow_tools():
    assert len(mod.BATTERY) == 6
    narrow = set(CANONICAL.values())
    assert {r.expected for r in mod.BATTERY} == narrow
    ticket_ids = {t["ticket_id"] for t in load("tickets.json")}
    user_ids = {u["user_id"] for u in load("usuarios.json")}
    article_ids = {a["article_id"] for a in load("articulos_kb.json")}
    for request in mod.BATTERY:
        if request.expected in ("get_ticket", "get_article", "get_user") or "EMP-" in request.prompt:
            words = [w.strip(".,:«»?") for w in request.prompt.split()]
            assert any(w in ticket_ids | user_ids | article_ids for w in words), request.label


def test_an_alias_of_the_expected_tool_counts_as_a_hit():
    # `fetch_ticket_details` es un alias de `get_ticket`: elegirlo no es un error de enrutamiento.
    assert mod.is_correct("fetch_ticket_details", "get_ticket")
    assert mod.is_correct("get_ticket", "get_ticket")
    assert not mod.is_correct("search_tickets", "get_ticket")
    assert not mod.is_correct("find_user", "get_ticket")
    assert not mod.is_correct(None, "get_ticket")
    assert not mod.is_correct("no_existe", "get_ticket")


def test_first_mesa_call_and_accuracy():
    rec = RunRecord(tool_calls=[call("Read"), call("mcp__mesa__lookup_ticket"), call("mcp__mesa__get_user", "r2")])
    assert mod.first_mesa_call(rec) == "lookup_ticket"
    assert mod.first_mesa_call(RunRecord()) is None
    assert mod.accuracy([("lookup_ticket", "get_ticket"), (None, "get_user"), ("get_user", "get_user")]) == (2, 3)
    assert mod.accuracy([]) == (0, 0)
    assert mod.rate_text((5, 6)) == "5/6 (83 %)" and mod.rate_text((0, 0)) == "sin datos"


def test_distinct_choices_shows_inconsistency_across_repeats():
    results = [("ticket", "get_ticket"), ("ticket", "lookup_ticket"), ("ticket", "get_ticket"), ("user", "get_user")]
    choices = mod.distinct_choices(results)
    assert choices == {"ticket": {"get_ticket", "lookup_ticket"}, "user": {"get_user"}}
    assert mod.inconsistent(choices) == ["ticket"]
    assert mod.inconsistent({"a": {"x"}}) == []


def test_scope_options_tool_counts_and_tool_search_off(tmp_path):
    wide = mod.build_scope_options("amplio", budget=0.1, model="m")
    narrow = mod.build_scope_options(None, budget=0.1, model="m")
    assert len(wide.allowed_tools) == 18 and len(narrow.allowed_tools) == 5
    assert wide.tools == [] and wide.setting_sources == [] and wide.max_budget_usd == 0.1
    # La carga diferida de definiciones se apaga: si no, la comparación 18 frente a 5 no sería limpia.
    assert wide.env["ENABLE_TOOL_SEARCH"] == "false" and narrow.env["ENABLE_TOOL_SEARCH"] == "false"
    assert wide.env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"  # el aislamiento sigue


def test_anti_belongs_to_scoping_only():
    assert mod.ANTI_VARIANTS == ["amplio"]
    assert mod.PARTS == ["scoping", "tool_choice"]


# --- tool_choice: petición por modo ----------------------------------------------

def test_choice_for_turn_sets_the_mode_on_the_first_turn_and_auto_after():
    assert mod.choice_for_turn("auto", 0) == {"type": "auto"}
    assert mod.choice_for_turn("any", 0) == {"type": "any"}
    assert mod.choice_for_turn("forzado", 0) == {"type": "tool", "name": "extract_ticket_metadata"}
    # Después, `auto` en todos los modos: con `any` o forzado en cada turno el modelo nunca podría responder.
    for mode in ("any", "forzado"):
        assert mod.choice_for_turn(mode, 1) == {"type": "auto"} and mod.choice_for_turn(mode, 5) == {"type": "auto"}


def test_unknown_mode_fails():
    with pytest.raises(ValueError):
        mod.choice_for_turn("otro", 0)


def test_forced_tool_exists_in_the_tool_list():
    assert mod.FORCED_TOOL in {t["name"] for t in mod.TOOLS}
    assert all(t["input_schema"]["type"] == "object" and t["description"] for t in mod.TOOLS)


# --- clasificador de la primera respuesta ----------------------------------------

def text(value):
    return SimpleNamespace(type="text", text=value)


def tool_use(name, input_, id_="tu1"):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def test_first_block_kind():
    assert mod.first_block_kind([tool_use("search_kb", {})]) == "tool_use"
    assert mod.first_block_kind([text("hola"), tool_use("search_kb", {})]) == "texto"  # empieza por texto aunque luego llame
    assert mod.first_block_kind([text("hola")]) == "texto"
    assert mod.first_block_kind([]) == "vacío"


def test_first_block_kind_skips_thinking():
    thinking = SimpleNamespace(type="thinking", thinking="…")
    assert mod.first_block_kind([thinking, tool_use("search_kb", {})]) == "tool_use"


# --- herramientas locales -----------------------------------------------------------

def test_extract_ticket_metadata_returns_category_and_urgency():
    data = json.loads(mod.execute_tool("extract_ticket_metadata", {"ticket_text": "La VPN se desconecta y no puedo trabajar."}))
    assert data["category"] == "red" and data["urgency"] == "alta"
    calm = json.loads(mod.execute_tool("extract_ticket_metadata", {"ticket_text": "Necesito una licencia del editor."}))
    assert calm["category"] == "licencias" and calm["urgency"] == "normal"


def test_search_kb_and_unknown_tool():
    data = json.loads(mod.execute_tool("search_kb", {"query": "vpn"}))
    assert 1 <= len(data["results"]) <= 3 and all("article_id" in r for r in data["results"])
    assert "error" in json.loads(mod.execute_tool("no_existe", {}))


# --- secuencia forzado → auto ------------------------------------------------------

class FakeCreate:
    """Devuelve respuestas guionizadas y guarda el `tool_choice` y los mensajes de cada llamada."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.choices = []
        self.sent = []

    def __call__(self, messages, tool_choice):
        self.choices.append(tool_choice)
        self.sent.append(list(messages))
        return self.responses.pop(0)


def response(*blocks, stop="tool_use"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop)


def test_forced_then_auto_sequence():
    create = FakeCreate(
        response(tool_use("extract_ticket_metadata", {"ticket_text": "VPN caída"}, "tu1")),
        response(tool_use("search_kb", {"query": "vpn"}, "tu2")),
        response(text("Ticket de red; consulta KB-109."), stop="end_turn"),
    )
    run = mod.run_mode(create, "forzado", "Ticket: VPN caída")
    assert create.choices == [{"type": "tool", "name": "extract_ticket_metadata"}, {"type": "auto"}, {"type": "auto"}]
    assert [t.first_kind for t in run.turns] == ["tool_use", "tool_use", "texto"]
    assert [t.names for t in run.turns] == [["extract_ticket_metadata"], ["search_kb"], []]
    assert run.final_text == "Ticket de red; consulta KB-109."
    # El resultado de la tool vuelve al historial emparejado con su tool_use_id.
    result = create.sent[1][-1]
    assert result["role"] == "user" and result["content"][0]["tool_use_id"] == "tu1"
    assert json.loads(result["content"][0]["content"])["category"] == "red"


def test_auto_can_answer_in_text_without_calling_a_tool():
    create = FakeCreate(response(text("Parece un problema de red."), stop="end_turn"))
    run = mod.run_mode(create, "auto", "¿Qué opinas de este ticket?")
    assert [t.first_kind for t in run.turns] == ["texto"] and run.turns[0].names == []
    assert create.choices == [{"type": "auto"}]


def test_run_mode_stops_at_the_turn_cap():
    endless = [response(tool_use("search_kb", {"query": "vpn"}, f"tu{i}")) for i in range(10)]
    create = FakeCreate(*endless)
    run = mod.run_mode(create, "any", "x", max_turns=3)
    assert len(run.turns) == 3 and run.final_text is None


def test_rate_of_tool_first_responses():
    def run_with(kind):
        return mod.ModeRun("auto", [mod.Turn("auto", kind, [])], [], None)

    runs = [run_with("tool_use"), run_with("texto"), run_with("tool_use")]
    assert mod.starts_with_tool(runs) == (2, 3)
    assert mod.starts_with_tool([]) == (0, 0)
