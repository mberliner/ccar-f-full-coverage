"""Tests de app3/09_batches: construcción del lote, emparejado por custom_id, clasificación de resultados, selección y troceo de los fallidos, ventana frente a SLA, estimación de coste y coste con descuento. Sin modelo."""

import re
from types import SimpleNamespace

import pytest

from harness.budget import cost_of
from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/09_batches.py")
ext = mod.ext

LABELS = load("documentos_compra_etiquetas.json")
DOCS = {d["doc_id"]: d["text"] for d in load("documentos_compra.json")}
CUSTOM_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")  # lo que admite la API


# --- construcción del lote --------------------------------------------------------------------

def test_batch_has_one_request_per_document_with_a_valid_unique_custom_id():
    requests = mod.build_batch_requests(DOCS, model="m")
    ids = [r["custom_id"] for r in requests]
    assert ids == list(DOCS) and len(set(ids)) == len(ids)
    assert all(CUSTOM_ID.match(i) for i in ids)


def test_each_request_is_a_single_turn_extraction_with_the_forced_tool_and_a_short_max_tokens():
    request = mod.build_batch_requests({"DC-01": DOCS["DC-01"]}, model="m")[0]["params"]
    assert request["tool_choice"] == {"type": "tool", "name": "extract_metadata"}
    assert request["max_tokens"] == mod.BATCH_MAX_TOKENS < 1500
    # Una sola vuelta: el lote no puede devolver un tool_result a mitad de una petición.
    assert len(request["messages"]) == 1 and request["messages"][0]["role"] == "user"
    assert "DC-01" not in str(request["messages"])  # el id viaja en custom_id, no en el prompt


def test_the_long_document_does_not_fit_the_batch_max_tokens_but_the_rest_do():
    # Precondición de la señal: solo el albarán largo supera lo que cabe en BATCH_MAX_TOKENS.
    lines = {doc_id: len(label["line_items"]) for doc_id, label in LABELS.items()}
    assert lines["DC-12"] >= 40 and all(n <= 3 for doc_id, n in lines.items() if doc_id != "DC-12")


# --- clasificación de resultados -------------------------------------------------------------------

def succeeded(custom_id, data, stop="tool_use"):
    block = SimpleNamespace(type="tool_use", name="extract_metadata", id="tu", input=data)
    usage = SimpleNamespace(input_tokens=1000, output_tokens=300, cache_creation_input_tokens=None, cache_read_input_tokens=None)
    message = SimpleNamespace(content=[block], stop_reason=stop, usage=usage)
    return SimpleNamespace(custom_id=custom_id, result=SimpleNamespace(type="succeeded", message=message))


def errored(custom_id, kind="api_error"):
    return SimpleNamespace(custom_id=custom_id, result=SimpleNamespace(type="errored", error=SimpleNamespace(error=SimpleNamespace(type=kind, message="x"))))


def other(custom_id, kind):
    return SimpleNamespace(custom_id=custom_id, result=SimpleNamespace(type=kind))


def perfect(doc_id):
    return ext.label_to_extraction(LABELS[doc_id])


def test_a_good_result_is_ok():
    item = mod.classify_result(succeeded("DC-01", perfect("DC-01")))
    assert item.status == "ok" and item.data["doc_type"] == "invoice" and item.usage.output_tokens == 300


def test_a_truncated_response_is_a_failure_even_though_the_batch_calls_it_succeeded():
    item = mod.classify_result(succeeded("DC-12", {"doc_type": "delivery_note"}, stop="max_tokens"))
    assert item.status == "truncated"


def test_a_response_that_breaks_the_schema_is_a_failure():
    assert mod.classify_result(succeeded("DC-01", {"doc_type": "factura", "line_items": []})).status == "invalid"


def test_errored_expired_and_canceled_results_keep_their_kind():
    assert mod.classify_result(errored("DC-02")).status == "errored"
    assert mod.classify_result(other("DC-03", "expired")).status == "expired"
    assert mod.classify_result(other("DC-04", "canceled")).status == "canceled"
    assert mod.classify_result(errored("DC-02", "invalid_request_error")).error_type == "invalid_request_error"


def test_failed_items_are_selected_by_custom_id():
    items = [mod.classify_result(e) for e in [succeeded("DC-01", perfect("DC-01")), errored("DC-02"), succeeded("DC-12", {"doc_type": "delivery_note"}, "max_tokens")]]
    assert [i.custom_id for i in mod.failed_items(items)] == ["DC-02", "DC-12"]


# --- emparejado por custom_id (y su anti-patrón) --------------------------------------------------------

def test_results_are_paired_by_custom_id_regardless_of_arrival_order():
    sent = ["DC-01", "DC-02", "DC-03"]
    arrived = [mod.classify_result(succeeded(i, perfect(i))) for i in ["DC-03", "DC-01", "DC-02"]]
    paired = mod.pair_results(sent, arrived, by="custom_id")
    assert all(paired[i].custom_id == i for i in sent)


def test_pairing_by_position_mixes_up_documents_when_results_arrive_out_of_order():
    sent = ["DC-01", "DC-02", "DC-03"]
    arrived = [mod.classify_result(succeeded(i, perfect(i))) for i in ["DC-03", "DC-01", "DC-02"]]
    paired = mod.pair_results(sent, arrived, by="order")
    assert mod.mismatched(paired, LABELS) == ["DC-01", "DC-02", "DC-03"]
    assert mod.mismatched(mod.pair_results(sent, arrived, by="custom_id"), LABELS) == []


def test_a_document_without_a_number_in_its_label_is_not_counted_as_mixed_up():
    # DC-07 no tiene número: si el modelo escribe uno es un invento (se mide en 07), no un cruce de documentos.
    paired = {"DC-07": mod.classify_result(succeeded("DC-07", {**perfect("DC-07"), "document_number": "7731"}))}
    assert mod.mismatched(paired, LABELS) == []


def test_unknown_pairing_fails():
    with pytest.raises(ValueError):
        mod.pair_results([], [], by="otro")


# --- troceo y reenvío de los fallidos ---------------------------------------------------------------------

def test_a_short_document_is_not_split():
    assert mod.chunk_document(DOCS["DC-01"]) == [DOCS["DC-01"]]


def test_a_long_document_is_split_keeping_the_header_in_every_chunk_and_every_line_once():
    chunks = mod.chunk_document(DOCS["DC-12"])
    assert len(chunks) == 40 // mod.CHUNK_LINES
    item_lines = lambda t: [line for line in t.splitlines() if re.match(r"^\d+ x ", line)]  # noqa: E731
    assert [line for c in chunks for line in item_lines(c)] == item_lines(DOCS["DC-12"])
    for chunk in chunks:
        assert "ALBARÁN AL-5560" in chunk and "PO-7800" in chunk
        assert len(item_lines(chunk)) <= mod.CHUNK_LINES


def test_chunk_custom_ids_are_valid_and_map_back_to_the_document():
    ids = mod.chunk_ids("DC-12", 4)
    assert ids == ["DC-12--c1", "DC-12--c2", "DC-12--c3", "DC-12--c4"]
    assert all(CUSTOM_ID.match(i) for i in ids) and {mod.base_id(i) for i in ids} == {"DC-12"}
    assert mod.base_id("DC-01") == "DC-01"


def test_resend_splits_the_truncated_document_and_resends_the_transient_failures_whole():
    items = [
        mod.classify_result(succeeded("DC-12", {"doc_type": "delivery_note"}, "max_tokens")),
        mod.classify_result(errored("DC-02")),
        mod.classify_result(other("DC-03", "expired")),
        mod.classify_result(errored("DC-04", "invalid_request_error")),
        mod.classify_result(succeeded("DC-01", perfect("DC-01"))),
    ]
    requests = mod.build_resend(items, DOCS, model="m")
    ids = [r["custom_id"] for r in requests]
    assert ids == ["DC-12--c1", "DC-12--c2", "DC-12--c3", "DC-12--c4", "DC-02", "DC-03"]  # DC-04 no se reenvía, DC-01 ya estaba bien


def test_a_chunk_that_is_truncated_again_re_splits_the_whole_document_into_smaller_chunks():
    # Observado: un trozo de 10 líneas también pudo truncarse. Se re-trocea el documento entero, en trozos de la mitad.
    items = [mod.classify_result(succeeded("DC-12--c3", {"doc_type": "delivery_note"}, "max_tokens"))]
    requests = mod.build_resend(items, DOCS, model="m")
    assert [r["custom_id"] for r in requests] == mod.chunk_ids("DC-12", 40 // mod.RECHUNK_LINES)
    assert mod.RECHUNK_LINES == mod.CHUNK_LINES // 2
    for request in requests:
        text = request["params"]["messages"][0]["content"]
        assert len([line for line in text.splitlines() if re.match(r"^\d+ x ", line)]) <= mod.RECHUNK_LINES


def test_two_truncated_chunks_of_the_same_document_produce_one_re_split():
    items = [mod.classify_result(succeeded(f"DC-12--c{n}", {"doc_type": "delivery_note"}, "max_tokens")) for n in (2, 3)]
    ids = [r["custom_id"] for r in mod.build_resend(items, DOCS, model="m")]
    assert len(ids) == len(set(ids)) == 40 // mod.RECHUNK_LINES


def test_a_resend_request_for_a_chunk_carries_only_that_chunk():
    items = [mod.classify_result(succeeded("DC-12", {"doc_type": "delivery_note"}, "max_tokens"))]
    requests = mod.build_resend(items, DOCS, model="m")
    first, second = (r["params"]["messages"][0]["content"] for r in requests[:2])
    assert "(ref 001)" in first and "(ref 011)" not in first
    assert "(ref 011)" in second and "(ref 001)" not in second


def test_chunk_results_merge_into_one_extraction_that_matches_the_label():
    chunks = mod.chunk_document(DOCS["DC-12"])
    label_lines = LABELS["DC-12"]["line_items"]
    per = mod.CHUNK_LINES
    items = []
    for n, _ in enumerate(chunks):
        data = {**perfect("DC-12"), "line_items": label_lines[n * per:(n + 1) * per]}
        items.append(mod.classify_result(succeeded(f"DC-12--c{n + 1}", data)))
    merged = mod.merge_chunks(items)
    assert list(merged) == ["DC-12"]
    score = ext.score_extraction(merged["DC-12"], LABELS["DC-12"], ext.build_tool("correcta")["input_schema"])
    assert score.lines_ok and score.syntax_ok and not score.wrong


def test_a_failed_chunk_leaves_the_document_unmerged():
    ok = mod.classify_result(succeeded("DC-12--c1", perfect("DC-12")))
    bad = mod.classify_result(errored("DC-12--c2"))
    assert mod.merge_chunks([ok, bad]) == {}


# --- ventana frente a SLA --------------------------------------------------------------------------------

def test_a_job_without_sla_or_with_a_long_one_goes_in_the_batch():
    assert mod.route_workload(None) == "batch"
    assert mod.route_workload(72) == "batch"
    assert mod.route_workload(51) == "batch"  # 51 − 48 − 2 = 1 h de intervalo con un reenvío


def test_a_job_that_only_fits_one_pass_has_no_room_to_resend_failures():
    # La espera hasta el siguiente envío también cuenta: 48 h ya no dejan reenviar.
    assert mod.route_workload(48) == "batch_sin_margen"
    assert mod.route_workload(30) == "batch_sin_margen"


def test_a_job_whose_deadline_leaves_no_submission_interval_is_synchronous():
    assert mod.route_workload(8) == "sync"
    assert mod.route_workload(0.1) == "sync"
    assert mod.route_workload(24) == "sync"  # la ventana entera y nada de intervalo ni margen
    assert mod.route_workload(26) == "sync"


def test_the_window_is_24_hours_and_resubmission_widens_the_needed_margin():
    assert mod.BATCH_WINDOW_HOURS == 24
    assert mod.route_workload(72, resubmissions=2) == "batch_sin_margen"
    assert mod.route_workload(75, resubmissions=2) == "batch"


def test_submission_interval_is_the_deadline_minus_the_window_and_a_margin():
    # El ejemplo de la guía: con un SLA de 30 h y una ventana de 24 h, enviar cada 4 h lo garantiza.
    assert mod.SUBMISSION_MARGIN_HOURS == 2
    assert mod.submission_interval(30) == 4
    assert mod.submission_interval(72) == 46
    assert mod.submission_interval(30, margin_hours=0) == 6


def test_submission_interval_counts_a_window_per_resubmission():
    assert mod.submission_interval(72, resubmissions=1) == 22
    assert mod.submission_interval(48, resubmissions=1) is None
    assert mod.submission_interval(30, resubmissions=1) is None


def test_no_interval_when_the_deadline_does_not_fit_one_window():
    assert mod.submission_interval(8) is None
    assert mod.submission_interval(26) is None  # 26 − 24 − 2 = 0: habría que enviar de forma continua
    assert mod.submission_interval(26.5) == 0.5


def test_split_workloads_groups_the_examples_by_route():
    groups = mod.split_workloads(mod.WORKLOADS)
    assert set(groups) == {"batch", "batch_sin_margen", "sync"}
    assert all(groups[route] for route in groups)
    assert sum(len(v) for v in groups.values()) == len(mod.WORKLOADS)


# --- muestra previa --------------------------------------------------------------------------------------

def test_sample_selection_takes_a_few_short_documents():
    sample = mod.sample_ids(DOCS)
    assert 1 <= len(sample) <= 3 and "DC-12" not in sample


def test_preview_passes_only_when_every_sample_conforms():
    schema = ext.build_tool("correcta")["input_schema"]
    assert mod.preview_passes([perfect("DC-01"), perfect("DC-02")], schema)
    assert not mod.preview_passes([perfect("DC-01"), {"doc_type": "factura", "line_items": []}], schema)
    assert not mod.preview_passes([], schema)


# --- coste ----------------------------------------------------------------------------------------------------

def test_batch_cost_is_half_of_the_synchronous_cost():
    usage = SimpleNamespace(input_tokens=2000, output_tokens=500, cache_creation_input_tokens=None, cache_read_input_tokens=None)
    sync = cost_of("claude-haiku-5-5", usage)
    assert mod.batch_cost("claude-haiku-5-5", [usage, usage]) == pytest.approx(sync)  # 2 × 0,5


def test_estimate_is_a_worst_case_that_grows_with_the_number_of_requests():
    one = mod.estimate_batch_cost(mod.build_batch_requests({"DC-01": DOCS["DC-01"]}, model="claude-haiku-5-5"), "claude-haiku-5-5")
    all_docs = mod.estimate_batch_cost(mod.build_batch_requests(DOCS, model="claude-haiku-5-5"), "claude-haiku-5-5")
    assert 0 < one < all_docs < 0.05
    # Cota superior: toda la salida posible (max_tokens) con el descuento del lote.
    assert one >= mod.BATCH_MAX_TOKENS * 0.50 / 1_000_000 * 0.5
