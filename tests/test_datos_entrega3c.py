"""Tests de los conjuntos de la tanda C de la entrega 3 (`poblacion_extracciones*.json` de `datos/generar_sinteticos.py`). Sin modelo.

PROPÓSITO: la población que usa `app3/10` tiene que esconder de verdad un segmento malo detrás de una exactitud
agregada alta (TS 5.5-K1): si el generador cambia y el segmento desaparece, el módulo deja de enseñar su lección y
ningún otro test lo notaría.
"""

import json
from collections import defaultdict

from datos.generar_sinteticos import build_all

FIELDS = ["vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"]


def population() -> list[dict]:
    return json.loads(build_all()["poblacion_extracciones.json"])


def labels() -> dict:
    return json.loads(build_all()["poblacion_extracciones_etiquetas.json"])


def outcomes() -> list[tuple[dict, str, float, bool]]:
    truth = labels()
    return [(r, f, r["confidences"][f], truth[r["record_id"]]["correct"][f]) for r in population() for f in FIELDS]


def test_every_record_has_a_label_and_the_records_never_carry_it():
    assert {r["record_id"] for r in population()} == set(labels())
    for record in population():
        assert "correct" not in record and "labels" not in record
        assert set(record["confidences"]) == set(FIELDS)
        assert all(0 <= c <= 1 for c in record["confidences"].values())
        assert 0 <= record["doc_confidence"] <= 1
    for label in labels().values():
        assert set(label["correct"]) == set(FIELDS)


def test_is_deterministic():
    assert build_all()["poblacion_extracciones.json"] == build_all()["poblacion_extracciones.json"]


def test_aggregate_accuracy_is_high():
    """El titular que se enseña como engañoso: alrededor del 97 %."""
    rows = outcomes()
    accuracy = sum(correct for *_, correct in rows) / len(rows)
    assert 0.96 <= accuracy <= 0.985


def test_a_bad_segment_hides_behind_the_aggregate():
    by_type = defaultdict(lambda: [0, 0])
    for record, _, _, correct in outcomes():
        by_type[record["doc_type"]][0] += 1
        by_type[record["doc_type"]][1] += correct
    n, ok = by_type["other"]
    assert n >= 60, "el tipo raro debe tener bastantes valores para medirse"
    assert ok / n <= 0.65
    total = sum(n for n, _ in by_type.values())
    assert n / total <= 0.06, "y debe ser raro: poco peso en el agregado"
    for kind in ("invoice", "delivery_note"):
        assert by_type[kind][1] / by_type[kind][0] >= 0.97


def test_a_bad_field_in_one_format_also_exists():
    cells = defaultdict(lambda: [0, 0])
    for record, field, _, correct in outcomes():
        if record["doc_type"] == "invoice":
            cells[(record["doc_format"], field)][0] += 1
            cells[(record["doc_format"], field)][1] += correct
    n, ok = cells[("prosa", "issue_date")]
    assert n >= 40 and 0.7 <= ok / n <= 0.92
    assert cells[("tabla", "issue_date")][1] / cells[("tabla", "issue_date")][0] >= 0.97


def test_the_model_is_overconfident_where_it_is_wrong():
    """Hay errores con confianza alta (si no, la confianza serviría sola) y la mayoría está en el tipo raro."""
    wrong_high = [(r["doc_type"]) for r, _, c, ok in outcomes() if not ok and c >= 0.85]
    assert len(wrong_high) >= 15
    assert wrong_high.count("other") / len(wrong_high) >= 0.5
    wrong_low = [1 for _, _, c, ok in outcomes() if not ok and c < 0.7]
    assert len(wrong_low) >= 5, "y algunos errores sí traen confianza baja"


def test_correct_values_are_mostly_high_confidence():
    right = [c for _, _, c, ok in outcomes() if ok]
    assert sum(c >= 0.85 for c in right) / len(right) >= 0.97


def test_conflicting_and_ambiguous_documents_exist_with_high_confidence():
    records = population()
    flagged = [r for r in records if r["conflict_detected"] or r["ambiguous"]]
    assert sum(r["conflict_detected"] for r in records) >= 8
    assert sum(r["ambiguous"] for r in records) >= 5
    assert sum(r["doc_confidence"] >= 0.9 for r in flagged) >= 8, "su confianza alta no debe librarlos de la revisión"


def test_both_splits_have_every_type_and_enough_rare_documents():
    seen = defaultdict(lambda: defaultdict(int))
    for record in population():
        seen[record["split"]][record["doc_type"]] += 1
    assert set(seen) == {"calibracion", "produccion"}
    for split in seen.values():
        assert split["other"] >= 5 and split["invoice"] >= 80 and split["delivery_note"] >= 30


def test_document_confidence_is_the_mean_of_its_fields():
    for record in population():
        mean = sum(record["confidences"].values()) / len(FIELDS)
        assert abs(record["doc_confidence"] - mean) <= 0.01
