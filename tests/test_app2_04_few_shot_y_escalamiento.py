"""Tests de app2/04_few_shot_y_escalamiento: prompt por variante, clasificación de la acción desde las llamadas a tools, puntuación contra etiquetas y proxy de sentimiento. Sin modelo."""

import json

import pytest

from app2_agente_con_control.servers.helpdesk import tool_name
from datos.generar_sinteticos import build_all
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app2_agente_con_control/04_few_shot_y_escalamiento.py")

CASES = json.loads(build_all()["escalamiento_casos.json"])
LABELS = json.loads(build_all()["escalamiento_casos_etiquetas.json"])
EXAMPLES = json.loads(build_all()["escalamiento_ejemplos.json"])


def call(tool: str, /, **tool_input) -> ToolCall:
    return ToolCall(f"id-{tool}", tool_name(tool), tool_input, "r1", "principal", True, False, "{}")


def rec(*calls: ToolCall) -> RunRecord:
    return RunRecord(tool_calls=list(calls))


# --- prompt por variante -----------------------------------------------------------

def test_correct_prompt_has_explicit_criteria_and_the_reasoned_examples():
    prompt = mod.build_system_prompt(None)
    for criterion in mod.CRITERIA_LINES:
        assert criterion in prompt
    for example in EXAMPLES:
        assert example["text"] in prompt
        assert example["reasoning"] in prompt, "el razonamiento es lo que enseña el ejemplo (4.2-S1)"
        assert example["rejected_alternative"] in prompt


def test_sin_ejemplos_keeps_the_same_criteria_and_drops_only_the_examples():
    correct, plain = mod.build_system_prompt(None), mod.build_system_prompt("sin_ejemplos")
    for criterion in mod.CRITERIA_LINES:
        assert criterion in plain
    assert not any(e["text"] in plain for e in EXAMPLES)
    assert plain != correct and correct.startswith(plain.rstrip()), "el prompt corto es el largo sin el bloque de ejemplos"


def test_sentimiento_and_confianza_replace_the_criteria_without_examples():
    sentiment, confidence = mod.build_system_prompt("sentimiento"), mod.build_system_prompt("confianza")
    for prompt in (sentiment, confidence):
        assert not any(e["text"] in prompt for e in EXAMPLES)
        assert not any(c in prompt for c in mod.CRITERIA_LINES)
    assert "sentimiento negativo" in sentiment
    assert "CONFIANZA:" in confidence and "70" in confidence


def test_the_examples_are_not_evaluated_cases():
    prompt = mod.build_system_prompt(None)
    assert not any(c["text"] in prompt for c in CASES), "4.2-K3: si el ejemplo es el caso evaluado, se mide memoria"


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError):
        mod.build_system_prompt("no_existe")


# --- clasificación de la acción ----------------------------------------------------

def test_escalating_with_no_prior_calls_is_immediate():
    turn = mod.classify_turn(rec(call("escalate_to_human", summary="pide una persona")), [])
    assert turn.action == "escalate_now"


def test_escalating_after_searching_is_not_immediate():
    turn = mod.classify_turn(rec(call("search_kb", query="cuenta"), call("escalate_to_human", summary="x")), [])
    assert turn.action == "escalate_after_investigating"


def test_a_call_after_the_escalation_does_not_count_as_prior_investigation():
    turn = mod.classify_turn(rec(call("escalate_to_human", summary="x"), call("search_kb", query="y")), [])
    assert turn.action == "escalate_now"


def test_no_escalation_is_the_default_and_a_lookup_alone_is_not_a_guess():
    candidates = ["EMP-1004", "EMP-1018"]
    turn = mod.classify_turn(rec(call("find_employee_by_name", name="Laura Gómez")), candidates)
    assert turn.action == "no_escalation" and turn.looked_up
    assert mod.classify_turn(rec(), candidates).action == "no_escalation"


def test_picking_one_of_the_candidates_is_guessing_the_identity():
    candidates = ["EMP-1004", "EMP-1018"]
    for follow in (call("verify_employee", user_id="EMP-1004"), call("list_employee_tickets", user_id="EMP-1018")):
        turn = mod.classify_turn(rec(call("find_employee_by_name", name="Laura Gómez"), follow), candidates)
        assert turn.action == "guessed_identity"
    other = mod.classify_turn(rec(call("verify_employee", user_id="EMP-1001")), candidates)
    assert other.action == "no_escalation", "verificar a alguien que no es candidato no es adivinar entre homónimos"


def test_foreign_tool_names_are_ignored():
    turn = mod.classify_turn(rec(ToolCall("x", "Read", {}, "r1", "principal")), [])
    assert turn.action == "no_escalation"


# --- puntuación ---------------------------------------------------------------------

def turn(action, looked_up=False):
    return mod.Turn(action, looked_up, [])


def test_explicit_human_requires_immediate_escalation_without_investigating_first():
    assert mod.is_correct("explicit_human", turn("escalate_now"))
    assert not mod.is_correct("explicit_human", turn("escalate_after_investigating"))
    assert not mod.is_correct("explicit_human", turn("no_escalation"))


def test_frustration_requires_offering_first_and_escalating_only_when_the_client_insists():
    assert mod.is_correct("frustration", turn("no_escalation"), turn("escalate_now"))
    assert not mod.is_correct("frustration", turn("no_escalation"), turn("no_escalation")), "ignora que insiste"
    assert not mod.is_correct("frustration", turn("escalate_now")), "escala a la primera: ignora que se podía resolver"
    assert not mod.is_correct("frustration", turn("no_escalation")), "sin segundo turno no hay prueba de que escale al insistir"


def test_policy_gap_accepts_escalating_with_or_without_looking_things_up():
    assert mod.is_correct("policy_gap", turn("escalate_now"))
    assert mod.is_correct("policy_gap", turn("escalate_after_investigating"))
    assert not mod.is_correct("policy_gap", turn("no_escalation"))


def test_ambiguous_user_requires_not_guessing_and_not_escalating():
    assert mod.is_correct("ambiguous_user", turn("no_escalation", looked_up=True))
    assert not mod.is_correct("ambiguous_user", turn("guessed_identity", looked_up=True))
    assert not mod.is_correct("ambiguous_user", turn("escalate_now"))


def test_rates_by_kind_and_overall():
    rows = [("explicit_human", True), ("explicit_human", False), ("policy_gap", True), ("frustration", False)]
    assert mod.rates_by_kind(rows) == {"explicit_human": (1, 2), "policy_gap": (1, 1), "frustration": (0, 1)}
    assert mod.overall(rows) == (2, 4)
    assert mod.rate_text((3, 4)) == "3/4" and mod.rate_text((0, 0)) == "sin datos"


# --- confianza autodeclarada --------------------------------------------------------

def test_declared_confidence_is_parsed_from_the_line_the_prompt_asks_for():
    assert mod.declared_confidence("CONFIANZA: 85\nTe ayudo con eso.") == 85
    assert mod.declared_confidence("confianza: 40") == 40
    assert mod.declared_confidence("Sin línea de confianza.") is None
    assert mod.declared_confidence(None) is None
    assert mod.declared_confidence("CONFIANZA: 250") is None, "fuera de 0 a 100 no es una confianza"


def test_mean_confidence_splits_hits_and_misses():
    rows = [(True, 90), (True, 80), (False, 85), (False, None)]
    assert mod.mean_confidence(rows) == {"aciertos": 85.0, "fallos": 85.0}
    assert mod.mean_confidence([(True, None)]) == {"aciertos": None, "fallos": None}


# --- proxy de sentimiento (parte determinista, 5.2-K3) ------------------------------

def test_sentiment_proxy_counts_negative_cues():
    assert mod.negative_sentiment("Estoy harto, esto es un desastre") >= 2
    assert mod.negative_sentiment("Pásame con una persona, por favor.") == 0
    assert mod.proxy_action("Estoy harto de la VPN") == "escalate"
    assert mod.proxy_action("¿Podéis comprarla por fuera del catálogo?") == "resolve"


def test_the_proxy_gets_the_evaluation_cases_wrong_in_both_directions():
    """Es la señal sin modelo de 5.2-K3: el tono no mide la complejidad del caso."""
    rows = mod.proxy_rows(CASES, LABELS)
    assert len(rows) == len(CASES)
    hits, total = mod.proxy_score(rows)
    assert hits / total <= 0.5
    kinds_wrong = {kind for kind, _, ok in rows if not ok}
    # Escala las frustraciones sencillas (deberían resolverse) y deja pasar vacíos de política y peticiones de un humano.
    assert "frustration" in kinds_wrong
    assert {"policy_gap", "explicit_human"} & kinds_wrong


def test_proxy_expectation_comes_from_the_label_not_from_the_text():
    # La acción esperada por tipo: escalar en explicit_human y policy_gap; resolver o pedir ID en los otros dos.
    assert mod.proxy_should_escalate("explicit_human") and mod.proxy_should_escalate("policy_gap")
    assert not mod.proxy_should_escalate("frustration") and not mod.proxy_should_escalate("ambiguous_user")


def test_variants_and_parts():
    assert mod.ANTI_VARIANTS == ["sin_ejemplos", "sentimiento", "confianza"]
    assert mod.MODEL_ROLES == ["agent", "enforcement"]
    assert mod.PARTS == ["agente", "proxy"]


def test_confidence_is_read_from_any_text_of_the_turn_not_only_the_final_one():
    # Medido con modelo: el agente escribe «CONFIANZA: N» antes de escalar y el texto final ya no la trae.
    record = RunRecord(texts=["CONFIANZA: 35", "Te paso con una persona."], final_text="Te paso con una persona.")
    assert mod.confidence_of(record) == 35
    assert mod.confidence_of(RunRecord(texts=["Sin línea."], final_text="Sin línea.")) is None
    assert mod.confidence_of(RunRecord()) is None
