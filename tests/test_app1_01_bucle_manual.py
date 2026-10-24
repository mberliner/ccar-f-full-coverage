"""Tests de app1/01_bucle_manual: parada por stop_reason, tool_use_id, historial completo y variantes anti con respuestas falsas. Sin modelo."""

import json
from types import SimpleNamespace

import pytest

from tests.cargar import load

mod = load("app1_agente_unico/01_bucle_manual.py")


# --- Respuestas falsas con la forma de `anthropic.types.Message` -------------


def text(value):
    return SimpleNamespace(type="text", text=value)


def use(block_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def response(stop_reason, *blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


# Guion: el modelo encadena tres tools y responde. Cada paso lleva una trampa
# para una variante anti distinta.
SCRIPT = [
    response("tool_use", text("Voy a mirar el ticket."), use("tu_1", "get_ticket", {"ticket_id": "TCK-1"})),
    response("tool_use", text("Ticket leído; no he terminado, falta la persona."),
             use("tu_2", "get_user", {"name": "Laura Gómez"})),
    response("tool_use", use("tu_3", "search_kb", {"query": "contraseña"})),
    response("end_turn", text("Hay dos personas con ese nombre: necesito el ID de empleado.")),
]
QUESTION = [{"role": "user", "content": "Atiende el ticket TCK-1"}]


class FakeModel:
    """Elige la respuesta según cuántos `tool_result` ve en lo que recibe."""

    def __init__(self):
        self.sent = []

    def __call__(self, messages):
        self.sent.append(list(messages))
        seen = sum(1 for m in messages if m["role"] == "user" and isinstance(m["content"], list))
        return SCRIPT[min(seen, len(SCRIPT) - 1)]


def executor(name, tool_input):
    return json.dumps({"tool": name, "input": tool_input})


def run(anti=None, **kwargs):
    model = FakeModel()
    result = mod.run_loop(model, QUESTION, executor, anti=anti, echo=False, **kwargs)
    return result, model


def test_correct_loop_ends_on_end_turn():
    result, model = run()
    assert result.stop == "end_turn" and result.iterations == 4
    assert [c.name for c in result.tool_calls] == ["get_ticket", "get_user", "search_kb"]
    assert "ID de empleado" in result.final_text


def test_tool_results_pair_with_tool_use_id():
    result, _ = run()
    user_turns = [m for m in result.history if m["role"] == "user" and isinstance(m["content"], list)]
    assert [m["content"][0]["tool_use_id"] for m in user_turns] == ["tu_1", "tu_2", "tu_3"]
    assert all(m["content"][0]["type"] == "tool_result" for m in user_turns)


def test_full_history_sent_each_iteration():
    _, model = run()
    # Pregunta + (asistente, resultados) por cada iteración anterior.
    assert [len(sent) for sent in model.sent] == [1, 3, 5, 7]
    assert model.sent[-1][0] == QUESTION[0]


def test_text_with_tool_use_does_not_stop_correct_loop():
    # El texto «no he terminado» y el texto junto al tool_use no deciden nada.
    result, _ = run()
    assert result.stop == "end_turn"


@pytest.mark.parametrize(
    ("anti", "stop", "executed"),
    [
        ("texto", "texto", 1),  # «terminado» en el texto del paso 2
        ("texto_asistente", "texto_asistente", 0),  # texto junto al primer tool_use
        ("tope", "tope", 2),  # tope de 2 iteraciones como parada principal
    ],
)
def test_anti_variants_stop_too_early(anti, stop, executed):
    result, _ = run(anti)
    assert result.stop == stop
    assert len(result.tool_calls) == executed
    assert result.final_text is None or "ID de empleado" not in result.final_text


def test_anti_without_history_repeats_until_safety_net():
    result, model = run("sin_historial", safety_cap=5)
    assert result.stop == "red_de_seguridad"
    # Siempre recibe solo la pregunta: no ve sus resultados y repite la misma llamada.
    assert all(len(sent) == 1 for sent in model.sent)
    assert {c.name for c in result.tool_calls} == {"get_ticket"}


def test_fixed_tree_ignores_results():
    calls = []

    def spy(name, tool_input):
        calls.append(name)
        return mod.execute_tool(name, tool_input)

    def final_answer(messages):
        return response("end_turn", text("respuesta"))

    ticket = mod.ambiguous_ticket()
    result = mod.run_fixed_tree(final_answer, ticket["ticket_id"], spy, echo=False)
    # Misma secuencia aunque get_user falle por no tener user_id.
    assert calls == ["get_ticket", "get_user", "search_kb"]
    assert result.tool_calls[1].is_error and result.stop == "arbol_fijo"


# --- Tools locales sobre los datos sintéticos --------------------------------


def test_get_user_by_name_returns_both_homonyms():
    payload = json.loads(mod.execute_tool("get_user", {"name": "Laura Gómez"}))
    assert len(payload["matches"]) == 2
    assert {m["department"] for m in payload["matches"]} == {"Finanzas", "Ventas"}


def test_get_ticket_and_unknown_tool():
    ticket = mod.ambiguous_ticket()
    assert ticket["user_id"] is None and "Laura Gómez" in ticket["description"]
    payload = json.loads(mod.execute_tool("get_ticket", {"ticket_id": ticket["ticket_id"]}))
    assert payload["ticket_id"] == ticket["ticket_id"]
    assert "error" in json.loads(mod.execute_tool("get_ticket", {"ticket_id": "TCK-0"}))
    assert "error" in json.loads(mod.execute_tool("borrar_todo", {}))
    assert "argumentos no válidos" in json.loads(mod.execute_tool("get_ticket", {"id": "TCK-1"}))["error"]


def test_search_kb_finds_password_article():
    payload = json.loads(mod.execute_tool("search_kb", {"query": "restablecer contraseña"}))
    assert payload["articles"][0]["title"] == "Restablecer la contraseña corporativa"


def test_tool_definitions_match_executor():
    assert {t["name"] for t in mod.TOOLS} == set(mod.HANDLERS)
