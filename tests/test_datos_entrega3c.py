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


# --- El cambio de prueba de app3/11 y app3/12 (copia de `repo_mesa` con fallos sembrados) -----------------------------


def change() -> dict:
    return json.loads(build_all()["cambio_revision.json"])


def change_labels() -> dict:
    return json.loads(build_all()["cambio_revision_etiquetas.json"])


def final_files() -> dict[str, str]:
    """Estado del repositorio tras los dos commits del cambio."""
    base = {k.removeprefix("repo_mesa/"): v for k, v in build_all().items() if k.startswith("repo_mesa/")}
    return {**base, **change()["commit_1"], **change()["commit_2"]}


def test_change_only_touches_files_of_repo_mesa():
    base = {k.removeprefix("repo_mesa/") for k in build_all() if k.startswith("repo_mesa/")}
    for commit in ("commit_1", "commit_2"):
        assert set(change()[commit]) <= base, "el cambio modifica archivos de repo_mesa, no añade otros"


def test_every_seeded_flaw_has_category_file_and_a_line_that_holds_its_marker():
    labels = change_labels()
    categories = {flaw["category"] for flaw in labels["seeded"]}
    assert categories >= {"bug", "security", "comment", "cross_file"}, "categorías distintas"
    files = final_files()
    first = {**{k.removeprefix("repo_mesa/"): v for k, v in build_all().items() if k.startswith("repo_mesa/")}, **change()["commit_1"]}
    for flaw in labels["seeded"]:
        content = (first if flaw["commit"] == 1 else files)[flaw["file"]]
        assert flaw["marker"] in content.splitlines()[flaw["line"] - 1], flaw["id"]
        assert flaw["commit"] in (1, 2)


def test_the_seeded_flaws_of_one_file_are_far_enough_apart_to_be_told_apart():
    labels = change_labels()
    items = [*labels["seeded"], *labels["correct_changes"], *labels["acceptable_patterns"]]
    by_file: dict[str, list[int]] = {}
    for item in items:
        by_file.setdefault(item["file"], []).append(item["line"])
    for file, lines in by_file.items():
        ordered = sorted(lines)
        assert all(b - a >= 5 for a, b in zip(ordered, ordered[1:])), file


def test_cross_file_flaw_is_in_a_file_whose_callers_are_not_in_the_diff():
    flaw = next(f for f in change_labels()["seeded"] if f["id"] == "D")
    assert flaw["category"] == "cross_file" and flaw["file"] == "core/sla.py" and flaw["commit"] == 1
    outside = [c for c in flaw["callers"] if c not in change()["commit_1"]]
    assert outside, "algunos llamadores (resumen y tests) ni siquiera están en el commit"
    for caller in flaw["callers"]:
        assert "restante_horas" in final_files()[caller]  # siguen esperando la clave vieja
    assert "restante_horas" not in final_files()["core/sla.py"]


def test_cross_file_caller_line_is_not_within_three_lines_of_the_added_code_in_a_changed_file():
    """La pasada por archivo no debe poder ver al llamador en el contexto del diff de ese archivo."""
    flaw = next(f for f in change_labels()["seeded"] if f["id"] == "D")
    avisos = change()["commit_1"]["notificaciones/avisos.py"].splitlines()
    added = max(i for i, line in enumerate(avisos) if "os.system" in line)
    key_line = next(i for i, line in enumerate(avisos) if "restante_horas" in line)
    assert key_line - added > 3
    assert "notificaciones/avisos.py" in flaw["callers"]


def test_there_is_a_correct_change_and_an_acceptable_pattern_that_look_like_flaws():
    labels = change_labels()
    assert labels["correct_changes"] and labels["acceptable_patterns"]
    for item in [*labels["correct_changes"], *labels["acceptable_patterns"]]:
        assert item["marker"] in final_files()[item["file"]].splitlines()[item["line"] - 1], item["id"]
        assert item["why"]


def test_second_commit_fixes_the_swapped_arguments_and_adds_a_new_flaw():
    labels = change_labels()
    bug_1 = next(f for f in labels["seeded"] if f["id"] == "A")
    assert bug_1["commit"] == 1 and bug_1["resolved_in"] == 2
    assert bug_1["marker"] not in final_files()[bug_1["file"]]
    new = [f for f in labels["seeded"] if f["commit"] == 2]
    assert len(new) == 1 and new[0]["category"] == "bug"
    # Lo demás sigue sin resolverse en el estado final.
    for flaw in labels["seeded"]:
        if flaw["id"] != "A":
            assert flaw["marker"] in final_files()[flaw["file"]], flaw["id"]


def test_existing_scenarios_are_the_ones_the_repo_tests_really_cover():
    labels = change_labels()
    assert {s["function"] for s in labels["existing_scenarios"]} >= {"calcular_sla", "debe_escalar"}
    files = final_files()
    text = "\n".join(v for k, v in files.items() if "test" in k)
    for scenario in labels["existing_scenarios"]:
        for value in scenario["args"].values():
            assert str(value) in text


def test_the_change_never_carries_label_text():
    for commit in ("commit_1", "commit_2"):
        for content in change()[commit].values():
            assert "SEMBRADO" not in content.upper() and "FLAW" not in content.upper()


def test_change_is_deterministic_and_every_flaw_has_a_unique_id():
    assert build_all()["cambio_revision.json"] == build_all()["cambio_revision.json"]
    ids = [f["id"] for f in change_labels()["seeded"]]
    assert len(ids) == len(set(ids))


def test_second_cross_file_flaw_needs_both_chunks_of_the_diff_and_neither_shows_it_alone():
    """F: la función devuelve una fracción (0 a 1) y su uso en otro archivo la imprime como porcentaje (4.6-K3)."""
    flaw = next(f for f in change_labels()["seeded"] if f["id"] == "F")
    assert flaw["category"] == "cross_file" and flaw["commit"] == 1 and flaw["file"] == "notificaciones/avisos.py"
    assert flaw["callers"] == ["core/sla.py"] and flaw["keywords"]
    callee = change()["commit_1"]["core/sla.py"]
    use = change()["commit_1"]["notificaciones/avisos.py"]
    assert "de 0 a 1" in callee and "avance_plazo" in callee
    assert "avance_plazo" in use and "% del plazo consumido" in use
    # Ni el nombre ni el texto de ninguno de los dos delatan el desajuste por sí solos.
    assert "porcentaje" not in callee.lower()
    assert "fracción" not in use.lower() and "0 a 1" not in use


def test_every_labeled_item_names_symbols_that_really_appear_in_its_file():
    """Un hallazgo con la línea desplazada sigue contando si cita la función o el símbolo del fallo."""
    labels = change_labels()
    for item in [*labels["seeded"], *labels["correct_changes"], *labels["acceptable_patterns"]]:
        assert item["symbols"], item["id"]
        content = final_files()[item["file"]]
        assert all(symbol in content for symbol in item["symbols"]), item["id"]
