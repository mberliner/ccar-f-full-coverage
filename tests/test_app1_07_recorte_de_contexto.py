"""Tests de app1/07_recorte_de_contexto: recorte de campos, tools del inventario, bucle con `usage` por petición y comprobación de la respuesta. Sin modelo."""

import json
from types import SimpleNamespace

from datos.generar_sinteticos import build_all
from tests.cargar import load as load_module

mod = load_module("app1_agente_unico/07_recorte_de_contexto.py")

TEAMS = json.loads(build_all()["inventario_equipos.json"])["teams"]
LABELS = json.loads(build_all()["inventario_equipos_etiquetas.json"])


def usage(tokens: int, out: int = 10) -> SimpleNamespace:
    return SimpleNamespace(input_tokens=tokens, output_tokens=out, cache_creation_input_tokens=0, cache_read_input_tokens=0)


def text_response(text: str, tokens: int) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn", usage=usage(tokens))


def tool_response(calls: list[tuple[str, dict]], tokens: int) -> SimpleNamespace:
    blocks = [SimpleNamespace(type="tool_use", id=f"tu_{i}", name=n, input=a) for i, (n, a) in enumerate(calls)]
    return SimpleNamespace(content=blocks, stop_reason="tool_use", usage=usage(tokens))


# --- recorte ---------------------------------------------------------------------

def test_the_kept_fields_are_the_five_the_question_needs():
    assert mod.KEEP_FIELDS == LABELS["relevant_fields"]
    assert len(mod.KEEP_FIELDS) == 5


def test_trim_keeps_only_the_listed_fields_and_never_invents_one():
    trimmed = mod.trim_fields(TEAMS[0], mod.KEEP_FIELDS)
    assert list(trimmed) == mod.KEEP_FIELDS
    assert all(trimmed[k] == TEAMS[0][k] for k in trimmed)
    assert mod.trim_fields({"a": 1}, ["a", "z"]) == {"a": 1}


def test_field_count():
    assert mod.field_count(TEAMS[0]) == 40
    assert mod.field_count(mod.trim_fields(TEAMS[0], mod.KEEP_FIELDS)) == 5


def test_tool_returns_forty_fields_without_trim_and_five_with_it():
    full = json.loads(mod.execute_tool("get_team_inventory", {"team_id": "EQ-01"}, trim=False))
    short = json.loads(mod.execute_tool("get_team_inventory", {"team_id": "EQ-01"}, trim=True))
    assert len(full) == 40 and len(short) == 5
    assert {k: full[k] for k in short} == short, "el recorte no cambia los valores que conserva"


def test_trimmed_result_is_much_smaller_in_characters():
    full = mod.execute_tool("get_team_inventory", {"team_id": "EQ-01"}, trim=False)
    short = mod.execute_tool("get_team_inventory", {"team_id": "EQ-01"}, trim=True)
    assert len(full) >= 6 * len(short)


def test_list_teams_gives_ids_and_names_only():
    teams = json.loads(mod.execute_tool("list_teams", {}, trim=False))["teams"]
    assert [t["team_id"] for t in teams] == [t["team_id"] for t in TEAMS]
    assert all(set(t) == {"team_id", "team_name"} for t in teams)


def test_unknown_team_and_tool_are_errors_not_exceptions():
    assert "error" in json.loads(mod.execute_tool("get_team_inventory", {"team_id": "EQ-99"}, trim=True))
    assert "error" in json.loads(mod.execute_tool("borrar_todo", {}, trim=True))


# --- bucle y medida --------------------------------------------------------------

def scripted(responses):
    sent = []
    it = iter(responses)

    def create(messages):
        sent.append(len(messages))
        return next(it)

    return create, sent


def test_loop_records_input_tokens_per_request_and_keeps_the_full_history():
    create, sent = scripted([
        tool_response([("list_teams", {})], 300),
        tool_response([("get_team_inventory", {"team_id": "EQ-01"}), ("get_team_inventory", {"team_id": "EQ-02"})], 400),
        text_response("EQ-02", 1500),
    ])
    result = mod.run_loop(create, [{"role": "user", "content": "q"}], lambda n, a: mod.execute_tool(n, a, trim=True), echo=False)
    assert [t.input_tokens for t in result.requests] == [300, 400, 1500]
    assert sent == [1, 3, 5], "cada petición lleva el historial completo (5.1-K4)"
    assert result.final_text == "EQ-02" and result.stop == "end_turn"
    assert [t.tool_calls for t in result.requests] == [1, 2, 0]


def test_loop_stops_on_stop_reason_with_a_safety_cap_only_as_net():
    forever = [tool_response([("list_teams", {})], 100 + i) for i in range(50)]
    create, _ = scripted(forever)
    result = mod.run_loop(create, [{"role": "user", "content": "q"}], lambda n, a: "{}", safety_cap=4, echo=False)
    assert result.stop == "red_de_seguridad" and len(result.requests) == 4


def test_tokens_count_cache_fields_too():
    u = SimpleNamespace(input_tokens=100, output_tokens=5, cache_creation_input_tokens=20, cache_read_input_tokens=30)
    assert mod.input_tokens_of(u) == 150
    assert mod.input_tokens_of(usage(77)) == 77


def test_summary_accumulates_and_compares_variants():
    turns = [mod.Request(1, 300, 1), mod.Request(2, 1200, 2), mod.Request(3, 2100, 0)]
    assert mod.total_input(turns) == 3600
    assert mod.peak_input(turns) == 2100
    assert mod.total_input([]) == 0 and mod.peak_input([]) == 0
    assert mod.ratio(3600, 900) == 4.0
    assert mod.ratio(10, 0) is None


# --- respuesta correcta ----------------------------------------------------------

def test_answer_check_accepts_id_or_name_and_rejects_other_teams():
    expected = LABELS["expected"]["team_with_most_unassigned_laptops"]
    team = next(t for t in TEAMS if t["team_id"] == expected)
    assert mod.answer_is_correct(f"El equipo {team['team_name']} tiene más.", expected)
    assert mod.answer_is_correct(f"Es {expected}.", expected)
    other = next(t for t in TEAMS if t["team_id"] != expected)
    assert not mod.answer_is_correct(f"Es {other['team_name']}.", expected)
    assert not mod.answer_is_correct(None, expected)
    assert not mod.answer_is_correct("", expected)


def test_soporte_n1_is_not_mistaken_for_soporte_n2():
    n1 = next(t for t in TEAMS if t["team_name"] == "Soporte N1")
    n2 = next(t for t in TEAMS if t["team_name"] == "Soporte N2")
    assert mod.answer_is_correct("Soporte N2", n2["team_id"])
    assert not mod.answer_is_correct("Soporte N2", n1["team_id"])
    assert not mod.answer_is_correct("Soporte N1", n2["team_id"])


def test_variants_and_questions():
    assert mod.ANTI_VARIANTS == ["sin_recorte"]
    assert len(mod.QUESTIONS) == 2
    assert "uno" in mod.QUESTIONS[0].lower()


def test_follow_up_answer_needs_the_open_requests_of_the_right_team():
    expected = LABELS["expected"]["team_with_most_unassigned_laptops"]
    team = next(t for t in TEAMS if t["team_id"] == expected)
    n = team["open_requests"]
    assert mod.follow_up_is_correct(f"Hay {n} solicitudes abiertas.", expected)
    assert not mod.follow_up_is_correct(f"Hay {n + 1} solicitudes abiertas.", expected)
    assert not mod.follow_up_is_correct(None, expected)


def test_naming_the_same_team_by_id_and_by_name_is_still_one_team():
    # Medido con modelo: «Seguridad (EQ-06)» nombra al equipo dos veces y no es una respuesta ambigua.
    expected = LABELS["expected"]["team_with_most_unassigned_laptops"]
    team = next(t for t in TEAMS if t["team_id"] == expected)
    assert mod.answer_is_correct(f"**{team['team_name']} ({expected})** tiene más.", expected)


def test_the_answer_is_the_first_team_named_so_runners_up_do_not_spoil_it():
    # Medido con modelo: «Seguridad (EQ-06) … Le siguen Finanzas TI y Redes» es correcta; los segundos son contexto.
    expected = LABELS["expected"]["team_with_most_unassigned_laptops"]
    team = next(t for t in TEAMS if t["team_id"] == expected)
    others = [t for t in TEAMS if t["team_id"] != expected][:2]
    assert mod.answer_is_correct(f"{team['team_name']} ({expected}). Le siguen {others[0]['team_name']} y {others[1]['team_name']}.", expected)
    # Si el primero que nombra es otro, la respuesta es otra aunque mencione al esperado después.
    assert not mod.answer_is_correct(f"{others[0]['team_name']}, no {team['team_name']}.", expected)
    assert not mod.answer_is_correct("No lo sé.", expected)
