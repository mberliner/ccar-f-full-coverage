"""Tests de app3/09_batches: construcción del lote, emparejado por custom_id, clasificación de resultados, selección y troceo de los fallidos, ventana frente a SLA, estimación de coste y coste con descuento. Sin modelo."""

import itertools
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


def test_a_result_without_data_is_not_counted_as_data_from_another_document():
    # Un truncado o un fallo no trae datos: no son «los datos de otro documento».
    sent = ["DC-01", "DC-12"]
    arrived = [mod.classify_result(succeeded("DC-12", {"doc_type": "delivery_note"}, "max_tokens")), mod.classify_result(errored("DC-01"))]
    paired = mod.pair_results(sent, arrived, by="order")
    assert mod.mismatched(paired, LABELS) == []


def test_the_denominator_of_the_mix_up_count_is_the_documents_with_a_number_in_the_label():
    paired = {doc_id: mod.classify_result(succeeded(doc_id, perfect(doc_id))) for doc_id in LABELS}
    assert mod.numbered(paired, LABELS) == 11  # DC-07 no tiene número en la etiqueta
    assert mod.mismatch_summary(paired, LABELS) == "ninguno (de 11)"
    swapped = {**paired, "DC-01": paired["DC-02"]}
    assert mod.mismatch_summary(swapped, LABELS) == "['DC-01'] (1 de 11)"


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


def test_chunk_custom_ids_are_valid_carry_the_chunk_size_and_map_back_to_the_document():
    ids = mod.chunk_ids("DC-12", 4, 10)
    assert ids == ["DC-12--s10-c1", "DC-12--s10-c2", "DC-12--s10-c3", "DC-12--s10-c4"]
    assert all(CUSTOM_ID.match(i) for i in ids) and {mod.base_id(i) for i in ids} == {"DC-12"}
    assert mod.base_id("DC-01") == "DC-01"
    assert mod.parse_chunk_id("DC-12--s5-c7") == ("DC-12", 5, 7) and mod.parse_chunk_id("DC-12") is None


def trunc(custom_id):
    return mod.classify_result(succeeded(custom_id, {"doc_type": "delivery_note"}, "max_tokens"))


def item_lines(text):
    return [line for line in text.splitlines() if re.match(r"^\d+ x ", line)]


def test_resend_splits_the_truncated_document_and_resends_the_transient_failures_whole():
    items = [
        trunc("DC-12"),
        mod.classify_result(errored("DC-02")),
        mod.classify_result(other("DC-03", "expired")),
        mod.classify_result(errored("DC-04", "invalid_request_error")),
        mod.classify_result(succeeded("DC-01", perfect("DC-01"))),
    ]
    requests = mod.build_resend(items, DOCS, model="m")
    ids = [r["custom_id"] for r in requests]
    # En el orden de los documentos; DC-04 no se reenvía (400) y DC-01 ya estaba bien.
    assert ids == ["DC-02", "DC-03"] + mod.chunk_ids("DC-12", 4, 10)
    assert requests[0]["params"]["messages"][0]["content"].endswith(DOCS["DC-02"])


def test_a_chunk_that_is_truncated_again_re_splits_the_whole_document_in_half():
    requests = mod.build_resend([trunc("DC-12--s10-c3")], DOCS, model="m")
    assert [r["custom_id"] for r in requests] == mod.chunk_ids("DC-12", 8, 5)
    assert all(len(item_lines(r["params"]["messages"][0]["content"])) <= 5 for r in requests)


def test_re_splitting_keeps_halving_down_to_one_line_and_then_gives_up():
    assert [len(mod.build_resend([trunc(f"DC-12--s{size}-c1")], DOCS, model="m")) for size in (10, 5, 2)] == [8, 20, 40]
    assert mod.next_chunk_size(2) == 1 and mod.next_chunk_size(1) is None and mod.next_chunk_size(3) == 1
    # Un trozo de una línea que se trunca ya no se puede partir: no hay petición y queda en la lista de atascados.
    stuck_item = trunc("DC-12--s1-c1")
    assert mod.build_resend([stuck_item], DOCS, model="m") == []
    assert mod.stuck_ids([stuck_item], DOCS) == ["DC-12--s1-c1"]


def test_a_short_truncated_document_is_split_instead_of_being_resent_unchanged():
    requests = mod.build_resend([trunc("DC-03")], DOCS, model="m")  # DC-03 tiene 3 líneas de artículo
    texts = [r["params"]["messages"][0]["content"] for r in requests]
    assert len(texts) == 2 and sorted(len(item_lines(t)) for t in texts) == [1, 2]
    # DC-01 es una tabla, sin líneas «n x»: no hay por dónde partirlo, y reenviarlo igual no arreglaría nada.
    assert mod.build_resend([trunc("DC-01")], DOCS, model="m") == [] and mod.stuck_ids([trunc("DC-01")], DOCS) == ["DC-01"]


def test_two_truncated_chunks_of_the_same_document_produce_one_re_split():
    ids = [r["custom_id"] for r in mod.build_resend([trunc("DC-12--s10-c2"), trunc("DC-12--s10-c3")], DOCS, model="m")]
    assert ids == mod.chunk_ids("DC-12", 8, 5) and len(ids) == len(set(ids))


def test_a_resend_request_for_a_chunk_carries_only_that_chunk():
    requests = mod.build_resend([trunc("DC-12")], DOCS, model="m")
    first, second = (r["params"]["messages"][0]["content"] for r in requests[:2])
    assert "(ref 001)" in first and "(ref 011)" not in first
    assert "(ref 011)" in second and "(ref 001)" not in second


def test_an_invalid_chunk_is_resent_with_only_its_own_text():
    bad = mod.classify_result(succeeded("DC-12--s10-c3", {"doc_type": "factura", "line_items": []}))
    assert bad.status == "invalid"
    requests = mod.build_resend([bad], DOCS, model="m")
    assert [r["custom_id"] for r in requests] == ["DC-12--s10-c3"]
    text = requests[0]["params"]["messages"][0]["content"]
    assert "(ref 021)" in text and "(ref 030)" in text and "(ref 020)" not in text and "(ref 031)" not in text
    assert len(item_lines(text)) == 10 and "ALBARÁN AL-5560" in text  # la cabecera sí: cada trozo la lleva
    for kind in (errored("DC-12--s10-c3"), other("DC-12--s10-c3", "expired")):
        again = mod.build_resend([mod.classify_result(kind)], DOCS, model="m")
        assert len(item_lines(again[0]["params"]["messages"][0]["content"])) == 10


def test_a_truncated_and_an_invalid_chunk_of_the_same_document_give_the_same_resend_in_any_arrival_order():
    items = [trunc("DC-12--s10-c2"), mod.classify_result(succeeded("DC-12--s10-c3", {"doc_type": "factura", "line_items": []})), mod.classify_result(errored("DC-02"))]
    results = {tuple(r["custom_id"] for r in mod.build_resend(list(order), DOCS, model="m")) for order in itertools.permutations(items)}
    assert len(results) == 1
    ids = list(results.pop())
    # El re-troceo del documento cubre el trozo inválido: no se reenvía además por separado.
    assert ids == ["DC-02"] + mod.chunk_ids("DC-12", 8, 5)
    one = mod.build_resend(items, DOCS, model="m")
    lines = [line for r in one if mod.base_id(r["custom_id"]) == "DC-12" for line in item_lines(r["params"]["messages"][0]["content"])]
    assert lines == item_lines(DOCS["DC-12"])  # cada línea del documento, una sola vez


def test_chunk_results_merge_into_one_extraction_that_matches_the_label():
    chunks = mod.chunk_document(DOCS["DC-12"])
    label_lines = LABELS["DC-12"]["line_items"]
    per = mod.CHUNK_LINES
    items = []
    for n, _ in enumerate(chunks):
        data = {**perfect("DC-12"), "line_items": label_lines[n * per:(n + 1) * per]}
        items.append(mod.classify_result(succeeded(f"DC-12--s{per}-c{n + 1}", data)))
    merged = mod.merge_chunks(items)
    assert mod.merge_chunks(list(reversed(items))) == merged  # el orden de llegada no cuenta
    assert list(merged) == ["DC-12"]
    score = ext.score_extraction(merged["DC-12"], LABELS["DC-12"], ext.build_tool("correcta")["input_schema"])
    assert score.lines_ok and score.syntax_ok and not score.wrong


def test_a_failed_chunk_leaves_the_document_unmerged():
    ok = mod.classify_result(succeeded("DC-12--s10-c1", perfect("DC-12")))
    bad = mod.classify_result(errored("DC-12--s10-c2"))
    assert mod.merge_chunks([ok, bad]) == {}


def test_chunks_of_different_sizes_or_with_a_gap_are_not_merged():
    one = mod.classify_result(succeeded("DC-12--s10-c1", perfect("DC-12")))
    other_size = mod.classify_result(succeeded("DC-12--s5-c2", perfect("DC-12")))
    assert mod.merge_chunks([one, other_size]) == {}
    gap = [mod.classify_result(succeeded(f"DC-12--s10-c{n}", perfect("DC-12"))) for n in (1, 3)]
    assert mod.merge_chunks(gap) == {}
    assert mod.unmerged_documents(gap) == ["DC-12"]


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


def sample_extractions(**overrides):
    return {doc_id: {**perfect(doc_id), **overrides.get(doc_id, {})} for doc_id in mod.sample_ids(DOCS)}


def test_preview_passes_when_every_sample_conforms_and_matches_the_labels():
    schema = ext.build_tool("correcta")["input_schema"]
    assert mod.preview_passes(sample_extractions(), LABELS, schema)
    assert not mod.preview_passes({}, LABELS, schema)


def test_preview_fails_when_a_sample_breaks_the_schema():
    schema = ext.build_tool("correcta")["input_schema"]
    bad = sample_extractions(**{"DC-01": {"doc_type": "factura"}})
    assert not mod.preview_passes(bad, LABELS, schema)


def test_preview_fails_below_the_accuracy_threshold_even_when_the_form_is_valid():
    schema = ext.build_tool("correcta")["input_schema"]
    wrong = {doc_id: {"vendor": "Otro S.L.", "issue_date": "2020-01-01", "stated_total": 1.0, "currency": "USD"} for doc_id in mod.sample_ids(DOCS)}
    extractions = sample_extractions(**wrong)
    assert all(not ext.conforms(d, schema) for d in extractions.values())
    assert not mod.preview_passes(extractions, LABELS, schema)
    assert 0 < mod.SAMPLE_MIN_ACCURACY <= 1


def test_accuracy_is_counted_per_field_against_the_labels():
    schema = ext.build_tool("correcta")["input_schema"]
    extractions = sample_extractions(**{"DC-01": {"vendor": "Otro S.L."}})
    accuracy = mod.field_accuracy(extractions, LABELS, schema)
    n = len(extractions)
    assert accuracy["vendor"] == (n - 1, n) and accuracy["doc_type"] == (n, n) and accuracy["line_items"] == (n, n)
    assert set(accuracy) == {"doc_type", "vendor", "document_number", "issue_date", "po_number", "currency", "stated_total", "line_items"}
    assert mod.overall_accuracy(accuracy) == pytest.approx((n * 8 - 1) / (n * 8))
    assert mod.overall_accuracy({}) == 0.0


def test_a_field_invented_where_the_label_has_none_counts_as_wrong():
    schema = ext.build_tool("correcta")["input_schema"]
    accuracy = mod.field_accuracy({"DC-02": {**perfect("DC-02"), "po_number": "PO-0000"}}, LABELS, schema)
    assert accuracy["po_number"] == (0, 1)


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


# --- presupuesto por invocación y muestra, con un cliente simulado -------------------------------------

MODEL = "claude-haiku-5-5"
USAGE = dict(cache_creation_input_tokens=None, cache_read_input_tokens=None)


class FakeClient:
    """Cliente falso: la muestra síncrona devuelve la extracción perfecta (o la que se diga) y los lotes se anotan."""

    def __init__(self, results=(), wrong=False, sample_usage=(1000, 200)):
        self.created, self.results, self.wrong, self.sample_usage = [], list(results), wrong, sample_usage
        self.messages = SimpleNamespace(
            create=self._sync,
            batches=SimpleNamespace(create=self._batch, retrieve=self._retrieve, results=lambda batch_id: iter(self.results)),
        )

    def _sync(self, **request):
        content = request["messages"][0]["content"]
        doc_id = next(i for i, text in DOCS.items() if text in content)
        data = {"doc_type": "factura", "line_items": []} if self.wrong else perfect(doc_id)
        block = SimpleNamespace(type="tool_use", name="extract_metadata", id="tu", input=data)
        usage = SimpleNamespace(input_tokens=self.sample_usage[0], output_tokens=self.sample_usage[1], **USAGE)
        return SimpleNamespace(content=[block], stop_reason="tool_use", usage=usage)

    def _batch(self, requests):
        self.created.append(requests)
        return SimpleNamespace(id="msgbatch_x", processing_status="in_progress")

    def _retrieve(self, batch_id):
        counts = SimpleNamespace(processing=0, succeeded=len(self.results), errored=0, expired=0, canceled=0)
        return SimpleNamespace(id=batch_id, processing_status="ended", request_counts=counts)


def send_args(**kwargs):
    return SimpleNamespace(**{"sin_muestra": False, **kwargs})


def sample_cost(client):
    usage = SimpleNamespace(input_tokens=client.sample_usage[0], output_tokens=client.sample_usage[1], **USAGE)
    return mod.SAMPLE_SIZE * cost_of(MODEL, usage)


def full_estimate():
    return mod.estimate_batch_cost(mod.build_batch_requests(DOCS, model=MODEL), MODEL)


def test_send_does_not_create_the_batch_when_the_estimate_alone_exceeds_the_cap():
    client = FakeClient()
    assert mod.run_send(client, MODEL, full_estimate() / 2, send_args()) == 1
    assert client.created == []


def test_send_counts_the_synchronous_sample_and_the_batch_estimate_together_against_the_cap():
    client = FakeClient()
    budget = full_estimate() + sample_cost(client) / 2  # cabe el lote solo, no la muestra más el lote
    assert mod.run_send(client, MODEL, budget, send_args()) == 1 and client.created == []
    assert mod.run_send(FakeClient(), MODEL, full_estimate() + sample_cost(client) * 2, send_args()) == 0
    # Sin muestra no hay gasto síncrono: el mismo tope sí deja enviar.
    skipped = FakeClient()
    assert mod.run_send(skipped, MODEL, budget, send_args(sin_muestra=True)) == 0 and len(skipped.created) == 1


def test_send_does_not_launch_the_batch_when_the_sample_misses_the_threshold():
    client = FakeClient(wrong=True)
    assert mod.run_send(client, MODEL, 1.0, send_args()) == 1 and client.created == []
    forced = FakeClient(wrong=True)
    assert mod.run_send(forced, MODEL, 1.0, send_args(sin_muestra=True)) == 0 and len(forced.created) == 1


def read_args(**kwargs):
    return SimpleNamespace(**{"batch_id": "msgbatch_x", "esperar": 0, "anti": None, "reenviar": True, **kwargs})


def expensive(custom_id, data, stop="tool_use"):
    entry = succeeded(custom_id, data, stop)
    entry.result.message.usage = SimpleNamespace(input_tokens=20_000_000, output_tokens=2_000_000, **USAGE)
    return entry


def test_resend_is_compared_with_the_cap_of_this_invocation_not_with_what_the_read_batch_cost():
    # El lote leído ya se pagó en otra invocación: su coste (aquí enorme) no cuenta contra el tope del reenvío.
    client = FakeClient(results=[expensive("DC-12", {"doc_type": "delivery_note"}, "max_tokens")])
    estimate = mod.estimate_batch_cost(mod.build_resend([trunc("DC-12")], DOCS, model=MODEL), MODEL)
    assert mod.run_read(client, MODEL, estimate * 2, read_args()) == 0
    assert len(client.created) == 1 and [r["custom_id"] for r in client.created[0]] == mod.chunk_ids("DC-12", 4, 10)


def test_resend_is_not_created_when_its_estimate_exceeds_the_cap():
    client = FakeClient(results=[expensive("DC-12", {"doc_type": "delivery_note"}, "max_tokens")])
    estimate = mod.estimate_batch_cost(mod.build_resend([trunc("DC-12")], DOCS, model=MODEL), MODEL)
    assert mod.run_read(client, MODEL, estimate / 2, read_args()) == 1 and client.created == []


def test_remaining_budget_is_the_cap_minus_what_this_invocation_already_spent():
    assert mod.remaining_budget(0.5, 0.2) == pytest.approx(0.3)
    assert mod.remaining_budget(0.1, 0.4) == 0.0
    assert mod.fits_budget(0.2, 0.2, 0.5) and not mod.fits_budget(0.4, 0.2, 0.5)
