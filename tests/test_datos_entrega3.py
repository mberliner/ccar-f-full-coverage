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
