"""Tests de app3/08_validacion_reintento: validador sin modelo, mensaje de error específico, detección del dato ausente en la fuente, tope de reintentos y el bucle con un modelo simulado. Sin modelo."""

from types import SimpleNamespace

import pytest

from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/08_validacion_reintento.py")
ext = mod.ext  # el módulo 07, cargado desde su archivo

LABELS = load("documentos_compra_etiquetas.json")
DOCS = {d["doc_id"]: d["text"] for d in load("documentos_compra.json")}


def perfect(doc_id):
    return ext.label_to_extraction(LABELS[doc_id])


# --- validador -------------------------------------------------------------------------

def test_a_perfect_extraction_has_no_failures_except_the_known_source_problems():
    # Los fallos que quedan son los de la fuente: factura sin pedido y totales que no cuadran.
    expected = {"DC-02": {"missing_required"}, "DC-05": {"total_mismatch"}, "DC-09": {"total_mismatch"}}
    for doc_id in LABELS:
        patterns = {f.pattern for f in mod.validate(perfect(doc_id)).failures}
        assert patterns == expected.get(doc_id, set()), doc_id


def test_each_failure_carries_a_detected_pattern_field_value_and_rule():
    data = {**perfect("DC-01"), "issue_date": "14/09/2026", "doc_type": "factura"}
    by_pattern = {f.pattern: f for f in mod.validate(data).failures}
    assert set(by_pattern) == {"date_format", "enum_value"}
    date = by_pattern["date_format"]
    assert (date.field, date.value) == ("issue_date", "14/09/2026") and "ISO" in date.rule
    assert by_pattern["enum_value"].field == "doc_type"


def test_total_check_computes_the_total_and_flags_a_conflict():
    ok = mod.validate(perfect("DC-01"))
    assert ok.calculated_total == 3085.5 and ok.conflict_detected is False
    bad = mod.validate(perfect("DC-05"))  # líneas 1200,00 y total declarado 1250,00
    assert bad.calculated_total == 1200.0 and bad.conflict_detected is True
    assert [f.pattern for f in bad.failures] == ["total_mismatch"]


def test_total_check_is_skipped_without_prices_or_without_a_stated_total():
    assert mod.validate(perfect("DC-03")).calculated_total is None  # albarán sin precios
    quote = mod.validate(perfect("DC-11"))  # presupuesto con precio y sin total declarado
    assert quote.calculated_total == 1380.0 and quote.conflict_detected is False


def test_total_tolerance_is_one_cent():
    data = {**perfect("DC-01"), "stated_total": 3085.505}
    assert mod.validate(data).failures == []
    assert mod.validate({**perfect("DC-01"), "stated_total": 3085.52}).conflict_detected


def test_invoice_without_po_fails_but_a_delivery_note_without_po_does_not():
    assert any(f.pattern == "missing_required" and f.field == "po_number" for f in mod.validate({**perfect("DC-01"), "po_number": None}).failures)
    assert not any(f.field == "po_number" for f in mod.validate({**perfect("DC-03"), "po_number": None}).failures)


def test_an_impossible_date_is_a_format_failure_too():
    assert [f.pattern for f in mod.validate({**perfect("DC-01"), "issue_date": "2026-13-45"}).failures] == ["date_format"]


# --- ¿está el dato en la fuente? ------------------------------------------------------------

def test_source_has_distinguishes_a_missing_value_from_one_the_model_overlooked():
    assert not mod.source_has("po_number", DOCS["DC-02"])  # la factura en prosa no cita pedido
    assert mod.source_has("po_number", DOCS["DC-01"])
    assert mod.source_has("issue_date", DOCS["DC-01"]) and mod.source_has("issue_date", DOCS["DC-02"]) and mod.source_has("issue_date", DOCS["DC-08"])
    assert not mod.source_has("issue_date", DOCS["DC-04"])  # albarán sin fecha
    assert mod.source_has("doc_type", "lo que sea")  # sin comprobación específica: se supone que sí


# --- mensajes de error ------------------------------------------------------------------------

def test_concrete_message_names_field_value_and_rule():
    failures = mod.validate({**perfect("DC-01"), "issue_date": "14/09/2026"}).failures
    text = mod.concrete_message(failures)
    assert "issue_date" in text and "14/09/2026" in text and "ISO" in text


def test_concrete_message_for_a_total_gives_both_figures():
    text = mod.concrete_message(mod.validate(perfect("DC-05")).failures)
    assert "1200.00" in text and "1250.00" in text


def test_generic_message_says_nothing_about_the_error():
    assert mod.generic_message() == "Inténtalo de nuevo."


def test_message_by_mode():
    failures = mod.validate({**perfect("DC-01"), "issue_date": "14/09/2026"}).failures
    assert mod.message_for("reintento_generico", failures) == mod.generic_message()
    assert mod.message_for(None, failures) == mod.concrete_message(failures)
    assert mod.message_for("insistir", failures) == mod.concrete_message(failures)


# --- decisión de reintento y topes ------------------------------------------------------------

def failures_of(data):
    return mod.validate(data).failures


def test_a_fixable_failure_is_retried():
    plan = mod.plan_retry(failures_of({**perfect("DC-01"), "issue_date": "14/09/2026"}), DOCS["DC-01"], 0, None)
    assert [f.field for f in plan.retry] == ["issue_date"] and plan.stop == []


def test_missing_in_source_is_not_retried_and_is_marked():
    plan = mod.plan_retry(failures_of(perfect("DC-02")), DOCS["DC-02"], 0, None)
    assert plan.retry == [] and [(f.field, reason) for f, reason in plan.stop] == [("po_number", "missing_in_source")]


def test_insistir_retries_even_when_the_data_does_not_exist():
    plan = mod.plan_retry(failures_of(perfect("DC-02")), DOCS["DC-02"], 0, "insistir")
    assert [f.field for f in plan.retry] == ["po_number"] and plan.stop == []


def test_total_conflict_gets_one_retry_and_then_is_flagged():
    first = mod.plan_retry(failures_of(perfect("DC-05")), DOCS["DC-05"], 0, None)
    assert [f.pattern for f in first.retry] == ["total_mismatch"]
    second = mod.plan_retry(failures_of(perfect("DC-05")), DOCS["DC-05"], 1, None)
    assert second.retry == [] and [reason for _, reason in second.stop] == ["conflict_detected"]


def test_retry_cap_is_a_safety_net_and_insistir_has_its_own():
    failing = failures_of({**perfect("DC-01"), "issue_date": "14/09/2026"})
    capped = mod.plan_retry(failing, DOCS["DC-01"], mod.MAX_RETRIES, None)
    assert capped.retry == [] and [reason for _, reason in capped.stop] == ["retry_cap"]
    assert mod.plan_retry(failing, DOCS["DC-01"], mod.MAX_RETRIES, "insistir").retry  # insistir llega más lejos
    assert mod.plan_retry(failing, DOCS["DC-01"], mod.MAX_INSISTIR, "insistir").retry == []
    assert mod.MAX_INSISTIR > mod.MAX_RETRIES


def test_failures_are_grouped_by_detected_pattern():
    failures = failures_of({**perfect("DC-01"), "issue_date": "14/09/2026", "doc_type": "x"}) + failures_of(perfect("DC-05"))
    assert mod.group_by_pattern(failures) == {"date_format": 1, "enum_value": 1, "total_mismatch": 1}


# --- conversación del reintento -------------------------------------------------------------------

def test_retry_messages_replay_the_attempt_and_return_the_error_as_tool_result():
    history = [("tu_1", {"issue_date": "14/09/2026"}, "issue_date mal"), ("tu_2", {"issue_date": "14-09-2026"}, "otra vez")]
    messages = mod.retry_messages("DOCUMENTO", history)
    assert messages[0]["role"] == "user" and "DOCUMENTO" in messages[0]["content"]
    assert [m["role"] for m in messages[1:]] == ["assistant", "user", "assistant", "user"]
    use = messages[1]["content"][0]
    assert (use["type"], use["id"], use["input"]) == ("tool_use", "tu_1", {"issue_date": "14/09/2026"})
    result = messages[2]["content"][0]
    assert (result["type"], result["tool_use_id"], result["is_error"], result["content"]) == ("tool_result", "tu_1", True, "issue_date mal")


# --- el bucle, con un modelo simulado -----------------------------------------------------------------

class FakeModel:
    """Devuelve extracciones en el orden dado y recuerda los mensajes de cada llamada."""

    def __init__(self, *extractions):
        self.extractions = list(extractions)
        self.calls = []

    def __call__(self, **request):
        self.calls.append(request)
        data = self.extractions.pop(0)
        block = SimpleNamespace(type="tool_use", name="extract_metadata", id=f"tu_{len(self.calls)}", input=data)
        return SimpleNamespace(content=[block], stop_reason="tool_use", usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


def run(model, doc_id, mode=None):
    tool = ext.build_tool("correcta", normalization=False)
    return mod.process_document(model, DOCS[doc_id], LABELS[doc_id], mode, tool=tool, model_name="m")


def test_a_valid_first_attempt_needs_no_retry():
    model = FakeModel(perfect("DC-01"))
    outcome = run(model, "DC-01")
    assert outcome.retries == 0 and outcome.stopped_by == "valido" and len(model.calls) == 1


def test_useful_retry_corrects_a_format_error_with_the_concrete_message():
    model = FakeModel({**perfect("DC-01"), "issue_date": "14/09/2026"}, perfect("DC-01"))
    outcome = run(model, "DC-01")
    assert outcome.retries == 1 and outcome.stopped_by == "valido"
    assert [e.verdict for e in outcome.effects] == ["corregido"]
    sent = model.calls[1]["messages"][-1]["content"][0]
    assert sent["is_error"] and "14/09/2026" in sent["content"]  # el error concreto viajó
    assert model.calls[1]["tool_choice"] == {"type": "tool", "name": "extract_metadata"}


def test_generic_retry_that_repeats_the_error_is_useless_until_the_cap():
    bad = {**perfect("DC-01"), "issue_date": "14/09/2026"}
    model = FakeModel(bad, bad, bad)
    outcome = run(model, "DC-01", "reintento_generico")
    assert outcome.retries == mod.MAX_RETRIES and outcome.stopped_by == "retry_cap"
    assert {e.verdict for e in outcome.effects} == {"persiste"}
    assert model.calls[1]["messages"][-1]["content"][0]["content"] == "Inténtalo de nuevo."


def test_missing_in_source_stops_without_retrying_and_marks_the_field():
    model = FakeModel(perfect("DC-02"))
    outcome = run(model, "DC-02")
    assert outcome.retries == 0 and len(model.calls) == 1
    assert outcome.marked_missing == ["po_number"] and outcome.stopped_by == "missing_in_source"


def test_insistir_keeps_retrying_and_the_invented_value_passes_validation_but_not_the_label():
    invented = {**perfect("DC-02"), "po_number": "PO-0000"}
    model = FakeModel(perfect("DC-02"), invented, invented, invented)
    outcome = run(model, "DC-02", "insistir")
    assert outcome.retries >= 1 and outcome.effects[0].verdict == "inventado"
    assert outcome.marked_missing == []  # nadie lo marcó: ahora hay un dato falso donde faltaba uno


def test_total_conflict_is_retried_once_and_then_flagged():
    model = FakeModel(perfect("DC-05"), perfect("DC-05"))
    outcome = run(model, "DC-05")
    assert outcome.retries == 1 and outcome.conflict_detected and outcome.stopped_by == "conflict_detected"
    assert [e.verdict for e in outcome.effects] == ["persiste"]


def test_changing_the_numbers_to_make_a_conflict_disappear_is_an_invention():
    adjusted = {**perfect("DC-05"), "stated_total": 1200.0}
    model = FakeModel(perfect("DC-05"), adjusted)
    outcome = run(model, "DC-05")
    assert outcome.effects[0].verdict == "inventado" and not outcome.conflict_detected


def test_summary_counts_useful_useless_and_invented_retries():
    outcomes = [
        run(FakeModel({**perfect("DC-01"), "issue_date": "14/09/2026"}, perfect("DC-01")), "DC-01"),
        run(FakeModel(perfect("DC-05"), perfect("DC-05")), "DC-05"),
        run(FakeModel(perfect("DC-02")), "DC-02"),
    ]
    summary = mod.summarize_outcomes(outcomes)
    assert summary == {"documentos": 3, "reintentos": 2, "utiles": 1, "inutiles": 1, "inventaron": 0, "marcados": 1, "conflictos": 1}
