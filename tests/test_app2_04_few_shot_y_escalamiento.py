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

def turn(action, looked_up=False, asked_id=False):
    return mod.Turn(action, looked_up, [], asked_id)


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


def test_ambiguous_user_requires_not_guessing_not_escalating_and_asking_for_an_identifier():
    assert mod.is_correct("ambiguous_user", turn("no_escalation", looked_up=True, asked_id=True))
    assert not mod.is_correct("ambiguous_user", turn("no_escalation", looked_up=True)), "no adivinó, pero tampoco pidió el ID"
    assert not mod.is_correct("ambiguous_user", turn("guessed_identity", looked_up=True, asked_id=True))
    assert not mod.is_correct("ambiguous_user", turn("escalate_now", asked_id=True))


def test_no_progress_is_a_trigger_to_escalate_with_or_without_one_more_lookup():
    assert mod.is_correct("no_progress", turn("escalate_now"))
    assert mod.is_correct("no_progress", turn("escalate_after_investigating"))
    assert not mod.is_correct("no_progress", turn("no_escalation")), "seguir proponiendo pasos cuando no hay avance"


# --- ¿pidió un identificador? (5.2-K4, S5) ---------------------------------------------

def test_asking_for_an_identifier_is_recognised_in_its_usual_forms():
    for text in (
        "Hay dos empleadas con ese nombre. ¿Me indicas tu ID de empleado (EMP-NNNN)?",
        "Encontré dos Laura Gómez, de Finanzas y de Ventas. ¿De cuál eres?",
        "Necesito que me facilites tu correo corporativo para identificarte.",
        "Dime tu departamento y sigo con tu solicitud.",
    ):
        assert mod.asks_for_identifier(text), text


def test_answering_something_else_is_not_asking_for_an_identifier():
    for text in (
        "He restablecido tu contraseña. Ya puedes entrar en el portal.",
        "El portal de nóminas está en la intranet.",
        "Te paso con una persona del equipo.",
        "",
        None,
    ):
        assert not mod.asks_for_identifier(text), text


def test_mentioning_an_identifier_word_without_asking_is_not_asking():
    # Límite conocido: la frase nombra el departamento pero no pide nada.
    assert not mod.asks_for_identifier("Tu departamento ya tiene acceso al portal.")


def test_classify_turn_reads_the_request_from_every_text_of_the_turn():
    record = RunRecord(
        tool_calls=[call("find_employee_by_name", name="Laura Gómez")],
        texts=["Busco a Laura Gómez.", "Hay dos. ¿Cuál es tu ID de empleado?"],
        final_text="Hay dos. ¿Cuál es tu ID de empleado?",
    )
    turn_ = mod.classify_turn(record, ["EMP-1004", "EMP-1018"])
    assert turn_.action == "no_escalation" and turn_.looked_up and turn_.asked_id
    assert not mod.classify_turn(rec(), []).asked_id


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
    assert mod.proxy_should_escalate("no_progress")
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


def test_the_criteria_name_the_third_trigger_and_the_examples_do_not_cover_it():
    """El criterio 5 (5.2-K1, no se puede avanzar) es un patrón sin ejemplo: no se atribuye a los ejemplos."""
    assert any("base de conocimiento" in line and "avanz" in line for line in mod.CRITERIA_LINES)
    assert len(mod.CRITERIA_LINES) == 5
    assert {e["action"] for e in EXAMPLES} == {"escalate_now", "offer_resolution", "escalate_policy_gap", "ask_identifier"}


# --- detector de «pidió un identificador»: límites de la revisión independiente --------

def test_asking_to_choose_between_the_departments_is_asking_to_disambiguate():
    for text in (
        "¿Eres la de Finanzas o la de Ventas?",
        "Hay dos Laura Gómez, una en Finanzas y otra en Ventas. ¿Cuál eres?",
        "Confírmame quién eres con tu ID.",
        "¿Me confirmas tu número EMP-NNNN?",
        "¿Me das tu correo corporativo?",
    ):
        assert mod.asks_for_identifier(text), text


def test_a_word_of_the_data_without_asking_for_it_is_not_asking():
    for text in (
        "Te he enviado las instrucciones por correo. ¿Algo más?",
        "He visto que eres de Finanzas, ¿te reviso el reembolso del departamento?",
        "¿Puedo ayudarte con algo más sobre el portal?",
        "Tu departamento ya tiene acceso al portal.",
    ):
        assert not mod.asks_for_identifier(text), text


def test_known_limit_it_cannot_tell_a_request_written_without_any_cue():
    # Límite declarado: una frase que pide el dato de otra forma, con verbo pero sin ningún dato de la lista, no se ve.
    assert not mod.asks_for_identifier("Para seguir necesito saber a cuál corresponde la solicitud.")


# --- segunda revisión: falsos positivos del «?» y formas naturales que se perdían -----------

def test_a_question_that_is_not_about_the_person_is_not_asking_for_an_identifier():
    # Eran True con la versión anterior: «cuál es …» seguido de cualquier cosa, «tu número …» de cualquier cosa y el «?» solo.
    for text in (
        "¿Cuál es el error que ves?",
        "¿Cuál es el problema exacto?",
        "¿Me pasas tu número de ticket?",
        "Comprueba tu número de serie. ¿Se resolvió?",
        "¿Me das el número de pedido?",
        "Te he enviado las instrucciones a tu correo. ¿Algo más?",
        "Revisa tu correo y prueba el artículo. ¿Te sirve?",
    ):
        assert not mod.asks_for_identifier(text), text


def test_the_natural_ways_to_ask_for_the_employee_id_are_recognised():
    # Eran False con la versión anterior (se perdió «id de empleado» al exigir el posesivo) o en las dos.
    for text in (
        "¿Me das el ID de empleado?",
        "¿Podrías darme el ID de empleado?",
        "Necesito el número de empleado para seguir, ¿me lo das?",
        "Para continuar necesito el ID de empleado (EMP-NNNN).",
        "Por favor, pásame tu ID EMP-NNNN.",
        "¿Cuál es tu ID de empleado?",
        "¿Cuál de ellas eres?",
    ):
        assert mod.asks_for_identifier(text), text


def test_a_possessive_with_a_question_mark_needs_a_request_for_that_data():
    # El posesivo y el «?» juntos no bastan: hay que pedir el dato, no mencionarlo.
    assert not mod.asks_for_identifier("Tu departamento ya tiene acceso al portal. ¿Algo más?")
    assert mod.asks_for_identifier("¿Cuál es tu departamento?")
    assert mod.asks_for_identifier("¿Me das tu correo corporativo?")


# --- turnos cortados o con error: no se lanza la insistencia ni puntúan -------------------

def test_a_turn_with_a_run_error_does_not_score_but_a_budget_cut_is_not_an_error():
    errored = mod.classify_turn(RunRecord(is_error=True), [])
    assert errored.error and not errored.cut
    # El tope de gasto marca is_error en el SDK: eso es un corte, no un error de la ejecución.
    cut = mod.classify_turn(RunRecord(is_error=True, budget_exceeded=True), [])
    assert cut.cut and not cut.error
    assert not mod.scorable(errored, None)
    assert not mod.scorable(turn("no_escalation"), errored)
    assert mod.error_note(2) and "2" in mod.error_note(2) and mod.error_note(0) is None


def test_the_insistence_is_only_sent_after_a_first_turn_that_ended_normally():
    case_ = {"case_id": "X", "text": "t", "followup": "f"}
    assert mod.should_insist(case_, mod.Turn("no_escalation", False, [], False))
    assert not mod.should_insist(case_, mod.Turn("no_escalation", False, [], False, cut=True))
    assert not mod.should_insist(case_, mod.Turn("no_escalation", False, [], False, error=True))
    assert not mod.should_insist(case_, mod.Turn("escalate_now", False, [], False))
    assert not mod.should_insist({"case_id": "X", "text": "t"}, mod.Turn("no_escalation", False, [], False))


def test_not_logged_in_is_also_read_from_the_final_text():
    assert mod.not_logged_in(RunRecord(final_text="Not logged in · Please run /login"))


# --- turnos cortados por el tope de gasto -------------------------------------------

def test_a_turn_cut_by_the_budget_is_flagged_and_does_not_score():
    cut = mod.classify_turn(RunRecord(budget_exceeded=True), [])
    assert cut.cut
    assert not mod.classify_turn(RunRecord(), []).cut
    assert mod.scorable(turn("no_escalation"), None)
    assert not mod.scorable(mod.Turn("no_escalation", False, [], False, cut=True), None)
    assert not mod.scorable(turn("no_escalation"), mod.Turn("escalate_now", False, [], False, cut=True))


def test_case_cap_gives_each_case_up_to_three_shares_without_exceeding_what_is_left():
    # El tope se pasa a cada caso, pero el SDK solo lo comprueba al cerrar un turno: el gasto real puede pasar algo de él.
    # Un caso de dos turnos (la frustración) cuesta más que la parte igual: con partes iguales el tope lo cortaba.
    assert mod.case_cap(0.50, 0.0, 39) == pytest.approx(3 * 0.50 / 39)
    assert mod.case_cap(0.50, 0.20, 10) == pytest.approx(3 * 0.03)
    # Nunca más de lo que queda del tope de toda la ejecución: el total sigue acotado.
    assert mod.case_cap(0.50, 0.45, 1) == pytest.approx(0.05)
    assert mod.case_cap(0.50, 0.45, 2) == pytest.approx(0.05)
    assert mod.case_cap(0.50, 0.50, 5) == 0 and mod.case_cap(0.50, 0.60, 5) == 0
    assert mod.case_cap(0.50, 0.10, 0) == 0


def test_partial_measure_is_announced():
    assert mod.partial_note(65, 65) is None
    note = mod.partial_note(40, 65)
    assert "40" in note and "65" in note and "parcial" in note
    assert "2" in mod.cut_note(2) and mod.cut_note(0) is None


def test_a_run_without_a_session_is_detected_instead_of_being_measured_as_no_escalation():
    # Sin sesión de Claude Code ni API key el agente responde «Not logged in»: no es un resultado del caso.
    assert mod.not_logged_in(RunRecord(texts=["Not logged in · Please run /login"]))
    assert not mod.not_logged_in(RunRecord(texts=["Te paso con una persona."]))
    assert not mod.not_logged_in(RunRecord())
