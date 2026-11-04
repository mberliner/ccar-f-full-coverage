"""Tests de los conjuntos de la tanda A de la entrega 3 (`documentos_compra*.json` de `datos/generar_sinteticos.py`). Sin modelo."""

import json

from datos.generar_sinteticos import build_all


def docs() -> list[dict]:
    return json.loads(build_all()["documentos_compra.json"])


def labels() -> dict:
    return json.loads(build_all()["documentos_compra_etiquetas.json"])


def test_every_document_has_a_label_and_nothing_else():
    assert {d["doc_id"] for d in docs()} == set(labels())
    assert len(docs()) >= 12


def test_documents_never_carry_label_keys():
    # Las etiquetas van aparte: el texto que ve el agente no puede delatarlas.
    for doc in docs():
        assert set(doc) == {"doc_id", "text"}
        assert "doc_type" not in doc["text"] and "stated_total" not in doc["text"]


def test_formats_vary_table_prose_and_loose_lines():
    texts = [d["text"] for d in docs()]
    assert any("|" in t for t in texts)  # tabla
    assert any(t.count("\n") <= 2 and len(t) > 120 for t in texts)  # prosa en un párrafo
    assert any("x " in t and "|" not in t and t.count("\n") >= 3 for t in texts)  # líneas sueltas


def test_label_shape_and_enum():
    for label in labels().values():
        assert label["doc_type"] in {"invoice", "delivery_note", "other", "unclear"}
        assert set(label["fields"]) == {"vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"}
        assert isinstance(label["line_items"], list)
        assert isinstance(label["total_mismatch"], bool)


def test_there_are_types_that_do_not_fit_the_enum_and_unreadable_ones():
    by_type = {}
    for label in labels().values():
        by_type.setdefault(label["doc_type"], []).append(label)
    assert len(by_type["other"]) >= 2 and all(label["doc_type_detail"] for label in by_type["other"])
    assert len(by_type["unclear"]) >= 1
    assert all(label["doc_type_detail"] is None for t in ("invoice", "delivery_note") for label in by_type[t])


def test_optional_fields_are_absent_in_the_source_not_just_null_in_the_label():
    by_id = {d["doc_id"]: d["text"] for d in docs()}
    absent_po = [i for i, label in labels().items() if label["fields"]["po_number"] is None and label["doc_type"] == "invoice"]
    assert absent_po, "debe haber una factura sin pedido (el dato pedido no está en ninguna parte)"
    for doc_id in absent_po:
        assert "PO-" not in by_id[doc_id]
    # Y los presentes aparecen literalmente en el texto.
    for doc_id, label in labels().items():
        for field in ("document_number", "po_number"):
            value = label["fields"][field]
            if value is not None:
                assert value in by_id[doc_id], (doc_id, field)
    assert any(label["fields"]["issue_date"] is None for label in labels().values() if label["doc_type"] == "delivery_note")


def test_calculated_total_is_the_sum_of_lines_and_mismatch_is_real():
    mismatches = 0
    for label in labels().values():
        items = [i for i in label["line_items"] if i["unit_price"] is not None]
        if not items:
            assert label["calculated_total"] is None and label["total_mismatch"] is False
            continue
        calculated = round(sum(i["quantity"] * i["unit_price"] for i in items), 2)
        assert label["calculated_total"] == calculated
        stated = label["fields"]["stated_total"]
        assert label["total_mismatch"] == (stated is not None and abs(stated - calculated) > 0.01)
        mismatches += label["total_mismatch"]
    assert mismatches >= 2


def test_there_is_one_long_document_with_many_lines():
    all_labels = labels()
    doc_id = max(all_labels, key=lambda i: len(all_labels[i]["line_items"]))
    assert len(all_labels[doc_id]["line_items"]) >= 40
    text = next(d["text"] for d in docs() if d["doc_id"] == doc_id)
    assert text.count("\n") >= 40


def test_documents_use_reserved_domains_and_fictional_vendors():
    import re

    # Si hubiera correos, irían al dominio reservado `.test` (el `@` de «@ $425» es un precio).
    for doc in docs():
        for address in re.findall(r"\S+@\S+\.\w+", doc["text"]):
            assert address.endswith(".test")


# --- pedidos de compra (app3/07, parte enriquecimiento) ------------------------------------------


def test_purchase_orders_cover_every_po_cited_by_a_document_and_are_deterministic():
    files = build_all()
    orders = json.loads(files["pedidos_compra.json"])
    assert files["pedidos_compra.json"] == build_all()["pedidos_compra.json"]
    cited = {label["fields"]["po_number"] for label in json.loads(files["documentos_compra_etiquetas.json"]).values() if label["fields"]["po_number"]}
    assert cited <= {o["po_number"] for o in orders}
    assert all(set(o) >= {"po_number", "vendor", "status", "expected_total"} for o in orders)
    # Un número por pedido, sin repetidos.
    assert len({o["po_number"] for o in orders}) == len(orders)


# --- fuentes de investigación (tanda B: app3/04–06) ------------------------------------------------


def sources() -> list[dict]:
    return json.loads(build_all()["fuentes_investigacion.json"])


def source_labels() -> dict:
    return json.loads(build_all()["fuentes_investigacion_etiquetas.json"])


def test_sources_are_deterministic_and_labels_live_apart():
    files = build_all()
    assert files["fuentes_investigacion.json"] == build_all()["fuentes_investigacion.json"]
    for source in sources():
        # Lo que ve el agente: identidad, estado de acceso y el informe. Nunca las afirmaciones etiquetadas.
        assert set(source) == {"source_id", "name", "published_at", "availability", "report"}
        assert "claims" not in source and "conflicts" not in source


def test_one_source_times_out_and_one_is_validly_empty():
    by_id = {s["source_id"]: s for s in sources()}
    timeouts = [s for s in by_id.values() if s["availability"] == "timeout"]
    assert len(timeouts) == 1 and timeouts[0]["report"] is None  # falla: no hay informe que devolver
    empties = [s for s in by_id.values() if s["availability"] == "ok" and not s["report"]]
    assert len(empties) == 1  # un vacío legítimo: la fuente responde y no tiene nada


def test_conflicting_figures_differ_and_each_has_a_source_and_a_date():
    labels = source_labels()
    assert len(labels["conflicts"]) >= 2
    by_id = {s["source_id"]: s for s in sources()}
    for conflict in labels["conflicts"]:
        figures = {c["figure"] for c in conflict["claims"]}
        assert len(figures) >= 2  # cifras distintas para la misma magnitud
        for claim in conflict["claims"]:
            assert claim["source_id"] in by_id
            assert claim["published_at"] == by_id[claim["source_id"]]["published_at"]
            # La cifra aparece literalmente en el informe de su fuente.
            assert claim["figure_text"] in by_id[claim["source_id"]]["report"]
        # Un promedio de las cifras en conflicto no es ninguna de ellas.
        average = round(sum(c["figure"] for c in conflict["claims"]) / len(conflict["claims"]), 2)
        assert average not in figures


def test_established_claim_agrees_across_sources():
    labels = source_labels()
    established = labels["established"]
    assert len(established["source_ids"]) >= 2 and established["figure_text"]
    by_id = {s["source_id"]: s for s in sources()}
    for source_id in established["source_ids"]:
        assert established["figure_text"] in by_id[source_id]["report"]


def test_long_report_hides_the_key_finding_in_the_middle():
    labels = source_labels()["long_report"]
    report = next(s["report"] for s in sources() if s["source_id"] == labels["source_id"])
    position = report.index(labels["key_finding"]) / len(report)
    assert 0.4 < position < 0.6 and len(report) > 6000
    assert report.count(labels["key_finding"]) == 1
    # La línea de resumen (lo que el módulo pone al principio) repite el hallazgo clave con su cifra.
    assert labels["figure_text"] in labels["key_finding"] and labels["figure_text"] in labels["summary_line"]


# --- explicación de los conflictos y encabezados del informe largo (tanda B, completar) -------------

EXPLANATIONS = {"periodo", "metodo", "muestra", "poblacion", "sin_explicacion"}


def test_there_are_three_conflicts_and_each_one_says_how_the_metadata_explain_it():
    conflicts = source_labels()["conflicts"]
    assert len(conflicts) == 3
    for conflict in conflicts:
        assert conflict["explained_by"] and set(conflict["explained_by"]) <= EXPLANATIONS
    by_topic = {c["topic"]: c["explained_by"] for c in conflicts}
    assert set(by_topic["tiempo medio de resolución"]) == {"metodo", "muestra"}
    assert set(by_topic["satisfacción media"]) == {"periodo", "poblacion"}
    # El contraste: un único par sin explicación, y no mezcla otras.
    assert by_topic["tickets reabiertos"] == ["sin_explicacion"]


def test_each_explanation_is_backed_by_a_phrase_in_the_reports_of_its_pair():
    by_id = {s["source_id"]: s for s in sources()}
    for conflict in source_labels()["conflicts"]:
        reports = " ".join(by_id[c["source_id"]]["report"] for c in conflict["claims"])
        for kind, phrase in conflict.get("evidence", {}).items():
            assert kind in conflict["explained_by"] and phrase in reports
        if conflict["explained_by"] != ["sin_explicacion"]:
            assert set(conflict["evidence"]) == set(conflict["explained_by"])  # cada explicación tiene su frase


def test_the_unexplained_pair_shares_period_method_and_population():
    by_id = {s["source_id"]: s for s in sources()}
    (conflict,) = [c for c in source_labels()["conflicts"] if c["explained_by"] == ["sin_explicacion"]]
    assert "evidence" not in conflict or not conflict["evidence"]
    for claim in conflict["claims"]:
        # Mismo periodo, mismo método y misma población, dicho igual en las dos fuentes.
        assert conflict["shared_context"] in by_id[claim["source_id"]]["report"]
    assert len({c["source_id"] for c in conflict["claims"]}) == 2 and len({c["figure"] for c in conflict["claims"]}) == 2


def test_the_explained_pairs_differ_in_what_the_metadata_say():
    by_id = {s["source_id"]: s for s in sources()}
    resolution = " ".join(by_id[s]["report"] for s in ("SRC-TICKETS", "SRC-AUDITORIA"))
    assert "muestra de 300" in resolution and "esperas" in resolution
    satisfaction = " ".join(by_id[s]["report"] for s in ("SRC-ENCUESTA", "SRC-PROVEEDOR"))
    assert "corte a 31 de agosto" in satisfaction and "95 usuarios" in satisfaction


def test_headed_long_report_adds_headings_without_changing_the_text():
    labels = source_labels()["long_report"]
    plain = next(s["report"] for s in sources() if s["source_id"] == labels["source_id"])
    headed = labels["headed_report"]
    headings = [p for p in headed.split("\n\n") if p.startswith("## ")]
    assert headings == [f"## {h}" for h in labels["section_headings"]] and len(headings) >= 5
    # Quitando los encabezados queda exactamente el informe de siempre.
    assert "\n\n".join(p for p in headed.split("\n\n") if not p.startswith("## ")) == plain
    assert headed.count(labels["key_finding"]) == 1
    # El hallazgo clave sigue en mitad del texto y no abre sección: el encabezado ayuda a ubicarlo, no lo señala.
    position = headed.index(labels["key_finding"]) / len(headed)
    assert 0.4 < position < 0.6
    assert not headed.split(labels["key_finding"])[0].rstrip().split("\n\n")[-1].startswith("## ")
