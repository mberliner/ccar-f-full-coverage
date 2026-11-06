"""Tests de app3/10_confianza_y_revision: exactitud por segmento, calibración, umbrales, muestreo estratificado, cola de revisión con cupo y puerta de automatización. Sin modelo."""

import random
from types import SimpleNamespace

import pytest

from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/10_confianza_y_revision.py")
FIELDS = mod.FIELDS


def cell(confidence, correct, *, doc="invoice", field="vendor", record="X-1", split="produccion", doc_conf=None, conflict=False, ambiguous=False, form="tabla"):
    return mod.Cell(record, split, doc, form, field, confidence, doc_conf if doc_conf is not None else confidence, correct, conflict, ambiguous)


POP = load("poblacion_extracciones.json")
LABELS = load("poblacion_extracciones_etiquetas.json")
CELLS = mod.build_cells(POP, LABELS)


# --- datos y celdas --------------------------------------------------------------------------------

def test_build_cells_one_per_record_and_field_and_filters_by_split():
    assert len(CELLS) == len(POP) * len(FIELDS)
    calib = mod.build_cells(POP, LABELS, split="calibracion")
    prod = mod.build_cells(POP, LABELS, split="produccion")
    assert len(calib) + len(prod) == len(CELLS) and calib and prod
    assert {c.split for c in calib} == {"calibracion"}


def test_build_cells_reads_correctness_from_the_labels_not_from_the_records():
    one = POP[0]
    label = {one["record_id"]: {"correct": {f: False for f in FIELDS}}}
    cells = mod.build_cells([one], label)
    assert not any(c.correct for c in cells)


# --- 5.5-K1: la exactitud agregada esconde un segmento --------------------------------------------

def test_accuracy_of_empty_is_none_not_a_crash():
    assert mod.accuracy([]) is None


def test_aggregate_accuracy_is_high_and_hides_the_rare_type():
    assert mod.accuracy(CELLS) >= 0.96
    worst = mod.worst_segments(CELLS, lambda c: c.doc_type, min_n=30)
    assert worst[0][0] == "other"
    assert worst[0][1].accuracy <= 0.65
    assert worst[0][1].n == 72


def test_worst_segments_skips_segments_too_small_to_judge():
    cells = [cell(0.9, False, doc="rare")] + [cell(0.9, True, doc="big") for _ in range(40)]
    assert [k for k, _ in mod.worst_segments(cells, lambda c: c.doc_type, min_n=30)] == ["big"]
    assert [k for k, _ in mod.worst_segments(cells, lambda c: c.doc_type, min_n=1)][0] == "rare"


def test_a_bad_field_in_one_format_is_found_by_a_finer_key():
    worst = mod.worst_segments([c for c in CELLS if c.doc_type == "invoice"], lambda c: (c.doc_format, c.field), min_n=30)
    assert worst[0][0] == ("prosa", "issue_date")


# --- 5.5-K3, S3: calibración por bandas -----------------------------------------------------------------

def test_bands_report_accuracy_and_mean_confidence_per_band():
    cells = [cell(0.9, True), cell(0.92, True), cell(0.95, False), cell(0.5, False), cell(0.6, True)]
    bands = mod.confidence_bands(cells, edges=(0.0, 0.7, 1.01))
    low, high = bands
    assert (low.n, low.accuracy) == (2, 0.5)
    assert (high.n, high.accuracy) == (3, pytest.approx(2 / 3))
    assert high.mean_confidence == pytest.approx(0.9233, abs=1e-3)


def test_empty_band_has_no_accuracy():
    bands = mod.confidence_bands([cell(0.95, True)], edges=(0.0, 0.5, 1.01))
    assert bands[0].n == 0 and bands[0].accuracy is None and bands[0].mean_confidence is None


def test_confidence_one_goes_in_the_last_band():
    assert mod.confidence_bands([cell(1.0, True)], edges=(0.0, 0.5, 1.01))[-1].n == 1


def test_calibration_gap_is_zero_when_confidence_equals_accuracy_and_large_when_overconfident():
    calibrated = [cell(0.8, True)] * 8 + [cell(0.8, False)] * 2
    overconfident = [cell(0.95, True)] * 5 + [cell(0.95, False)] * 5
    assert mod.calibration_gap(mod.confidence_bands(calibrated)) == pytest.approx(0.0, abs=1e-9)
    assert mod.calibration_gap(mod.confidence_bands(overconfident)) == pytest.approx(0.45)


def test_the_population_is_overconfident_in_the_top_band():
    top = mod.confidence_bands(CELLS)[-1]
    assert top.accuracy >= 0.95 and top.mean_confidence >= 0.93
    # Pero entre lo seguro hay errores: un 0 % de error en esa banda no existe.
    assert top.accuracy < 1.0


# --- umbrales -----------------------------------------------------------------------------------------------

def test_pick_threshold_is_the_lowest_confidence_that_reaches_the_target():
    cells = [cell(0.5, False), cell(0.6, False), cell(0.8, True), cell(0.85, True), cell(0.9, True), cell(0.95, True)]
    assert mod.pick_threshold(cells, target=0.99, min_n=2) == 0.8
    assert mod.pick_threshold(cells, target=0.5, min_n=2) == 0.5


def test_pick_threshold_returns_none_when_no_threshold_reaches_the_target():
    cells = [cell(0.9, False), cell(0.95, False), cell(0.99, True)]
    assert mod.pick_threshold(cells, target=0.99, min_n=2) is None


def test_pick_threshold_requires_enough_evidence():
    # Un solo acierto con confianza 0.99 no demuestra nada: n mínimo.
    assert mod.pick_threshold([cell(0.99, True)], target=0.99, min_n=5) is None


def test_thresholds_by_segment_find_none_for_the_rare_type():
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    thresholds = mod.thresholds_by(calibration, lambda c: (c.doc_type, c.field), target=0.98, min_n=20)
    assert thresholds[("invoice", "vendor")] is not None
    assert all(thresholds[("other", f)] is None for f in FIELDS), "con 6 documentos por conjunto no hay evidencia para automatizar"


def test_segment_status_distinguishes_below_target_and_insufficient_data():
    cells = (
        [cell(0.95, True, doc="a") for _ in range(30)]
        + [cell(0.95, True, doc="b") for _ in range(25)] + [cell(0.95, False, doc="b") for _ in range(5)]
        + [cell(0.95, True, doc="c") for _ in range(3)]
    )
    status = mod.segment_status(cells, lambda c: c.doc_type, target=0.98, min_n=20, high=0.85)
    assert status == {"a": "ready", "b": "below_target", "c": "insufficient_data"}


def test_segment_status_only_looks_at_high_confidence_cells():
    # Los errores con confianza baja ya van a revisión: no cuentan contra la automatización.
    cells = [cell(0.95, True) for _ in range(30)] + [cell(0.3, False) for _ in range(30)]
    assert mod.segment_status(cells, lambda c: c.doc_type, target=0.98, min_n=20, high=0.85) == {"invoice": "ready"}


# --- 5.5-S2, K4: validar por segmento antes de automatizar; y --anti precision_agregada ---------------------------

def test_segmented_gate_blocks_the_rare_type_and_aggregate_gate_lets_it_through():
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    key = lambda c: (c.doc_type, c.field)  # noqa: E731
    segmented = mod.automation_plan(calibration, key=key, target=0.98, min_n=20, aggregate=False)
    aggregate = mod.automation_plan(calibration, key=key, target=0.98, min_n=20, aggregate=True)
    assert all(segmented[("other", f)] is None for f in FIELDS)
    assert any(segmented[("invoice", f)] is not None for f in FIELDS)
    # Mirando solo la exactitud global, el tipo raro hereda el umbral de todos.
    assert all(aggregate[("other", f)] is not None for f in FIELDS)


def test_aggregate_plan_has_a_single_threshold_for_every_segment():
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    plan = mod.automation_plan(calibration, key=lambda c: (c.doc_type, c.field), target=0.98, min_n=20, aggregate=True)
    assert len(set(plan.values())) == 1


def test_auto_error_rate_with_segmented_vs_aggregate_gate_on_production():
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    production = mod.build_cells(POP, LABELS, split="produccion")
    key = lambda c: (c.doc_type, c.field)  # noqa: E731
    seg_auto, _ = mod.auto_accept(production, mod.automation_plan(calibration, key=key, target=0.98, min_n=20, aggregate=False), level="campo")
    agg_auto, _ = mod.auto_accept(production, mod.automation_plan(calibration, key=key, target=0.98, min_n=20, aggregate=True), level="campo")
    other_seg = [c for c in seg_auto if c.doc_type == "other"]
    other_agg = [c for c in agg_auto if c.doc_type == "other"]
    assert other_seg == []
    assert len(other_agg) > 0 and mod.error_count(other_agg) >= 3, "automatizar por la exactitud global deja pasar errores del tipo raro"


# --- 5.5-K3 (anti confianza_global): una confianza por documento esconde el campo malo ----------------------------

def test_document_level_confidence_lets_through_a_bad_field_that_field_level_catches():
    # Un documento con un campo dudoso (0.4) y cinco seguros: la media sigue alta.
    cells = [cell(0.4, False, field="issue_date", record="D", doc_conf=0.86)] + [cell(0.97, True, field=f, record="D", doc_conf=0.86) for f in FIELDS[:5] if f != "issue_date"]
    by_field, review_field = mod.auto_accept(cells, {(c.doc_type, c.field): 0.85 for c in cells}, level="campo")
    by_doc, review_doc = mod.auto_accept(cells, 0.85, level="documento")
    assert [c.field for c in review_field] == ["issue_date"]
    assert review_doc == [] and len(by_doc) == len(cells), "el campo malo pasa porque el documento, en conjunto, parece seguro"


def test_field_level_routing_on_the_population_reduces_auto_errors():
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    production = mod.build_cells(POP, LABELS, split="produccion")
    plan = mod.automation_plan(calibration, key=lambda c: (c.doc_type, c.field), target=0.98, min_n=20, aggregate=False)
    field_auto, _ = mod.auto_accept(production, plan, level="campo")
    doc_threshold = mod.pick_threshold(calibration, target=0.98, min_n=20, by="doc_confidence")
    doc_auto, _ = mod.auto_accept(production, doc_threshold, level="documento")
    assert mod.error_count(field_auto) < mod.error_count(doc_auto)


def test_pick_threshold_can_use_the_document_confidence():
    cells = [cell(0.3, True, doc_conf=0.9), cell(0.3, True, doc_conf=0.95)] * 5
    assert mod.pick_threshold(cells, target=0.99, min_n=2, by="doc_confidence") == 0.9


# --- 5.5-S4: conflictos y ambiguos van a revisión aunque la confianza sea alta ------------------------------------

def test_conflict_and_ambiguous_documents_always_go_to_review():
    sure = [cell(0.99, True, record="A"), cell(0.99, True, record="B", conflict=True), cell(0.99, True, record="C", ambiguous=True)]
    auto, review = mod.auto_accept(sure, {(c.doc_type, c.field): 0.5 for c in sure}, level="campo")
    assert [c.record_id for c in auto] == ["A"]
    assert {c.record_id for c in review} == {"B", "C"}


def test_force_review_can_be_switched_off_to_show_what_it_adds():
    sure = [cell(0.99, True, record="B", conflict=True)]
    auto, review = mod.auto_accept(sure, {("invoice", "vendor"): 0.5}, level="campo", force_review=False)
    assert len(auto) == 1 and review == []


def test_none_threshold_sends_everything_of_the_segment_to_review():
    c = cell(0.999, True)
    auto, review = mod.auto_accept([c], {("invoice", "vendor"): None}, level="campo")
    assert auto == [] and review == [c]


def test_a_cell_whose_segment_has_no_threshold_entry_goes_to_review():
    auto, review = mod.auto_accept([cell(0.99, True, doc="nuevo")], {("invoice", "vendor"): 0.5}, level="campo")
    assert auto == [] and len(review) == 1


# --- 5.5-K2, S1: muestreo estratificado frente a aleatorio ------------------------------------------------------------

def auto_pool():
    """Las extracciones de confianza alta en producción: el conjunto del que se muestrea para medir su tasa de error."""
    return [c for c in mod.build_cells(POP, LABELS, split="produccion") if c.confidence >= 0.85]


def test_simple_sample_has_the_requested_size_and_is_reproducible():
    items = list(range(100))
    assert mod.simple_sample(items, 10, random.Random(1)) == mod.simple_sample(items, 10, random.Random(1))
    assert len(set(mod.simple_sample(items, 10, random.Random(1)))) == 10
    assert sorted(mod.simple_sample(items, 500, random.Random(1))) == items  # no pide más de lo que hay


def test_stratified_sample_guarantees_a_minimum_per_stratum():
    items = [("big", i) for i in range(500)] + [("rare", i) for i in range(6)]
    sample = mod.stratified_sample(items, 40, key=lambda x: x[0], min_per_stratum=5, rng=random.Random(2))
    kinds = [k for k, _ in sample]
    assert len(sample) == 40 and kinds.count("rare") >= 5


def test_stratified_sample_takes_the_whole_stratum_when_it_is_smaller_than_the_minimum():
    items = [("big", i) for i in range(100)] + [("rare", 1), ("rare", 2)]
    sample = mod.stratified_sample(items, 20, key=lambda x: x[0], min_per_stratum=5, rng=random.Random(3))
    assert [k for k, _ in sample].count("rare") == 2 and len(sample) == 20


def test_stratified_sample_fills_the_rest_in_proportion_to_stratum_size():
    items = [("a", i) for i in range(300)] + [("b", i) for i in range(100)]
    sample = mod.stratified_sample(items, 40, key=lambda x: x[0], min_per_stratum=2, rng=random.Random(4))
    kinds = [k for k, _ in sample]
    assert kinds.count("a") == 30 and kinds.count("b") == 10


def test_stratified_sample_is_reproducible_and_never_repeats_an_item():
    items = [("a", i) for i in range(50)] + [("b", i) for i in range(50)]
    first = mod.stratified_sample(items, 30, key=lambda x: x[0], min_per_stratum=5, rng=random.Random(9))
    second = mod.stratified_sample(items, 30, key=lambda x: x[0], min_per_stratum=5, rng=random.Random(9))
    assert first == second and len(set(first)) == 30


def test_sampling_experiment_stratified_sees_the_rare_type_errors_that_simple_random_misses():
    pool = auto_pool()
    result = mod.sampling_experiment(pool, n=60, key=lambda c: (c.doc_type, c.field), min_per_stratum=3, trials=300, seed=7)
    assert result["estratificado"]["ve_error_del_tipo_raro"] > result["simple"]["ve_error_del_tipo_raro"]
    assert result["estratificado"]["patrones"] > result["simple"]["patrones"]
    assert 0 <= result["simple"]["ve_error_del_tipo_raro"] <= 1


def test_sampling_experiment_is_deterministic_for_a_seed():
    pool = auto_pool()
    one = mod.sampling_experiment(pool, n=60, key=lambda c: c.doc_type, min_per_stratum=3, trials=50, seed=1)
    two = mod.sampling_experiment(pool, n=60, key=lambda c: c.doc_type, min_per_stratum=3, trials=50, seed=1)
    assert one == two


def test_error_patterns_are_doc_type_and_field_of_the_wrong_cells():
    cells = [cell(0.9, False, doc="other", field="po_number"), cell(0.9, False, doc="other", field="po_number"), cell(0.9, True), cell(0.9, False, doc="invoice", field="issue_date")]
    assert mod.error_patterns(cells) == {("other", "po_number"), ("invoice", "issue_date")}


def test_observed_error_rate_of_a_sample():
    assert mod.error_rate([cell(0.9, True), cell(0.9, False)]) == 0.5
    assert mod.error_rate([]) is None


# --- 5.5-S4: cola priorizada con capacidad limitada -------------------------------------------------------------------------

def item(rid, *, flagged=False, low=0.9, errors=0):
    return mod.ReviewItem(rid, flagged, low, errors)


def test_review_items_group_the_review_cells_by_document():
    cells = [
        cell(0.4, False, record="A", field="issue_date"),
        cell(0.97, True, record="A", field="vendor"),
        cell(0.99, True, record="B", conflict=True),
        cell(0.99, True, record="C"),
    ]
    plan = {("invoice", "vendor"): 0.9, ("invoice", "issue_date"): 0.9}
    items = mod.review_items(cells, plan, level="campo")
    assert {i.record_id for i in items} == {"A", "B"}
    a = next(i for i in items if i.record_id == "A")
    assert a.lowest_confidence == 0.4 and a.errors == 1 and not a.flagged
    assert next(i for i in items if i.record_id == "B").flagged


def test_priority_order_puts_conflicts_first_and_then_the_least_confident():
    items = [item("a", low=0.8), item("b", low=0.5), item("c", flagged=True, low=0.99), item("d", low=0.6)]
    assert [i.record_id for i in mod.order_queue(items, "prioridad")] == ["c", "b", "d", "a"]


def test_arrival_order_keeps_the_original_order():
    items = [item("a"), item("b"), item("c")]
    assert [i.record_id for i in mod.order_queue(items, "llegada")] == ["a", "b", "c"]


def test_order_queue_rejects_an_unknown_order():
    with pytest.raises(ValueError):
        mod.order_queue([], "azar")


def test_capacity_cuts_the_queue_and_reports_what_it_catches():
    queue = [item("a", errors=2), item("b", errors=0), item("c", errors=1), item("d", errors=3)]
    outcome = mod.review_capacity(queue, capacity=2)
    assert outcome.reviewed == 2 and outcome.errors_caught == 2 and outcome.errors_total == 6 and outcome.deferred == 2
    assert mod.review_capacity(queue, capacity=0).reviewed == 0
    assert mod.review_capacity(queue, capacity=99).errors_caught == 6


def test_confidence_order_catches_more_extraction_errors_and_priority_order_catches_every_conflict_first():
    """Con poca capacidad hay que elegir: los conflictos del documento y los errores de extracción son cosas distintas."""
    calibration = mod.build_cells(POP, LABELS, split="calibracion")
    production = mod.build_cells(POP, LABELS, split="produccion")
    plan = mod.automation_plan(calibration, key=lambda c: (c.doc_type, c.field), target=0.98, min_n=20, aggregate=False)
    items = mod.review_items(production, plan, level="campo")
    capacity = max(1, round(len(items) * 0.4))
    arrival = mod.review_capacity(mod.order_queue(items, "llegada"), capacity)
    by_confidence = mod.review_capacity(mod.order_queue(items, "confianza"), capacity)
    by_priority = mod.review_capacity(mod.order_queue(items, "prioridad"), capacity)
    assert by_confidence.errors_caught > arrival.errors_caught
    assert by_priority.flagged_caught == min(capacity, by_priority.flagged_total) > by_confidence.flagged_caught


def test_capacity_outcome_counts_flagged_documents():
    queue = [item("a", flagged=True), item("b"), item("c", flagged=True)]
    outcome = mod.review_capacity(queue, 2)
    assert (outcome.flagged_caught, outcome.flagged_total) == (1, 2)


def test_confidence_order_puts_the_lowest_first_and_ignores_the_flag():
    items = [item("a", flagged=True, low=0.99), item("b", low=0.4), item("c", low=0.8)]
    assert [i.record_id for i in mod.order_queue(items, "confianza")] == ["b", "c", "a"]


def test_flagged_documents_are_reviewed_even_when_every_field_is_confident():
    cells = [cell(0.99, True, record="B", conflict=True, field=f) for f in FIELDS]
    plan = {("invoice", f): 0.5 for f in FIELDS}
    items = mod.review_items(cells, plan, level="campo")
    assert len(items) == 1 and items[0].flagged


# --- 5.5-S3: la confianza que da el modelo ----------------------------------------------------------------------------------

def test_confidence_tool_adds_one_confidence_per_field_and_keeps_the_rest():
    tool = mod.confidence_tool()
    props = tool["input_schema"]["properties"]
    assert set(props["field_confidence"]["properties"]) == set(FIELDS)
    assert "field_confidence" in tool["input_schema"]["required"]
    for sub in props["field_confidence"]["properties"].values():
        assert sub["type"] == "number"
    assert "stated_total" in props  # el esquema de 07 sigue ahí


def test_cells_from_a_model_extraction_compare_with_the_label():
    label = {"doc_type": "invoice", "doc_type_detail": None, "fields": {"vendor": "Acme", "document_number": "F-1", "issue_date": "2026-01-02", "po_number": None, "currency": "EUR", "stated_total": 10.0}, "line_items": []}
    data = {"vendor": "Acme", "document_number": "F-2", "issue_date": "2026-01-02", "po_number": "PO-9999", "currency": "EUR", "stated_total": None,
            "field_confidence": {"vendor": 0.99, "document_number": 0.9, "issue_date": 0.95, "po_number": 0.9, "currency": 0.99, "stated_total": 0.8}}
    cells = {c.field: c for c in mod.cells_from_extraction("DC-01", data, label)}
    assert cells["vendor"].correct and cells["issue_date"].correct and cells["currency"].correct
    assert not cells["document_number"].correct          # valor distinto
    assert not cells["po_number"].correct                # la etiqueta dice que no está y el modelo puso un valor
    assert not cells["stated_total"].correct             # la etiqueta tiene valor y el modelo puso null
    assert cells["document_number"].confidence == 0.9


def test_an_absent_field_left_null_is_correct():
    label = {"doc_type": "invoice", "doc_type_detail": None, "fields": {f: None for f in FIELDS}, "line_items": []}
    data = {**{f: None for f in FIELDS}, "field_confidence": {f: 0.9 for f in FIELDS}}
    assert all(c.correct for c in mod.cells_from_extraction("DC-02", data, label))


def test_missing_or_malformed_confidence_counts_as_none_and_never_crashes():
    label = {"doc_type": "invoice", "doc_type_detail": None, "fields": {f: None for f in FIELDS}, "line_items": []}
    for data in ({}, {"field_confidence": "alta"}, {"field_confidence": {"vendor": "0.9", "currency": 1.7, "po_number": -1}}):
        cells = mod.cells_from_extraction("DC-02", data, label)
        assert len(cells) == len(FIELDS)
    cells = {c.field: c for c in mod.cells_from_extraction("DC-02", {"field_confidence": {"vendor": "0.9", "currency": 1.7, "po_number": -1}}, label)}
    assert cells["vendor"].confidence is None and cells["currency"].confidence is None and cells["po_number"].confidence is None


def test_model_confidence_summary_separates_correct_from_wrong_and_counts_overconfident_errors():
    cells = [cell(0.95, True), cell(0.97, True), cell(0.96, False), cell(0.5, False), cell(None, False)]
    summary = mod.summarize_model_confidence(cells)
    assert summary["n"] == 4 and summary["sin_confianza"] == 1
    assert summary["acierta"] == 2 and summary["falla"] == 2
    assert summary["media_si_acierta"] == pytest.approx(0.96) and summary["media_si_falla"] == pytest.approx(0.73)
    assert summary["errores_con_confianza_alta"] == 1


def test_positive_control_a_miscalibrated_model_is_detected_and_a_calibrated_one_is_not():
    """Control positivo de la medida: lo sintético mal calibrado da un hueco grande; el bien calibrado, ninguno."""
    bad = [cell(0.95, i % 2 == 0) for i in range(100)]
    good = [cell(0.95, i % 20 != 0) for i in range(100)]
    assert mod.calibration_gap(mod.confidence_bands(bad)) > 0.4
    assert mod.calibration_gap(mod.confidence_bands(good)) < 0.02


def test_summary_without_errors_has_no_mean_for_the_wrong_ones():
    summary = mod.summarize_model_confidence([cell(0.9, True)])
    assert summary["media_si_falla"] is None and summary["falla"] == 0


def test_run_confidence_extraction_uses_the_forced_tool_and_the_confidence_schema():
    seen = []

    def fake_create(**request):
        seen.append(request)
        data = {f: None for f in FIELDS} | {"doc_type": "invoice", "line_items": [], "field_confidence": {f: 0.9 for f in FIELDS}}
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="extract_metadata", id="t1", input=data)], usage=SimpleNamespace())

    out = mod.extract_with_confidence(fake_create, {"DC-01": "texto"}, model="m")
    assert seen[0]["tool_choice"] == {"type": "tool", "name": "extract_metadata"}
    assert "field_confidence" in seen[0]["tools"][0]["input_schema"]["properties"]
    assert out["DC-01"]["field_confidence"]["vendor"] == 0.9


def test_cells_remember_whether_the_model_gave_a_value_or_left_null():
    label = {"doc_type": "invoice", "doc_type_detail": None, "fields": {f: None for f in FIELDS} | {"vendor": "Acme"}, "line_items": []}
    data = {"vendor": "Acme", "field_confidence": {f: 0.1 for f in FIELDS} | {"vendor": 0.99}}
    cells = {c.field: c for c in mod.cells_from_extraction("DC-01", data, label)}
    assert cells["vendor"].value_present and not cells["currency"].value_present
    assert cells["currency"].correct, "un null correcto con confianza baja es un acierto: la confianza habla de la ausencia"


def test_confidence_tool_can_drop_the_format_rules_without_touching_the_confidence_field():
    plain = mod.confidence_tool(normalization=False)["input_schema"]["properties"]
    ruled = mod.confidence_tool()["input_schema"]["properties"]
    assert "ISO" not in plain["issue_date"]["description"] and "ISO" in ruled["issue_date"]["description"]
    assert plain["field_confidence"] == ruled["field_confidence"]
