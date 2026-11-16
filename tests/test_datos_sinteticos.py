"""Tests de `datos/generar_sinteticos.py`: determinismo, sincronía con disco e invariantes de todos los conjuntos (tickets y legado; `repo_mesa/` y `documentos.json`; documentos de compra, fuentes de investigación, población de extracciones y cambio de revisión; escalamiento e inventario), una sección por app. Sin modelo.

PROPÓSITO: comprobar que el generador es determinista, que lo que hay en `datos/sinteticos/` coincide con lo que genera y que los conjuntos cumplen sus invariantes: los de los módulos de app1, app2 y app3 que los usan como entrada y como criterio (p. ej. que la población de `app3/10` esconde un segmento malo tras una exactitud alta, TS 5.5-K1; que los ejemplos *few-shot* de `app2/04` no son sus casos, TS 4.2-K3; que el inventario de `app1/07` tiene 40 campos de los que solo 5 hacen falta, TS 5.1-K3).

POR QUÉ EXISTE: `datos/sinteticos/` solo se cambia ejecutando el generador; este test avisa si alguien lo edita a mano o si el generador y el disco se desincronizan. Y si el generador cambia y un conjunto deja de tener el defecto o el dato que el módulo necesita, la lección se pierde (o se descubre tras gastar una ejecución) sin que nada lo avise.

QUÉ NO HACE: no escribe en `datos/sinteticos/` (salvo en carpetas temporales) ni llama al modelo.
"""

import ast
import importlib
import json
import re
import sys
from collections import defaultdict

import pytest

from datos.generar_sinteticos import REIMBURSEMENT_THRESHOLD_EUR, build_all, check, write


def load(name: str):
    return json.loads(build_all()[name])


def test_generation_is_deterministic():
    assert build_all() == build_all()


def test_committed_files_match_generator():
    # Si falla, alguien editó datos/sinteticos/ a mano o cambió el script sin regenerar.
    assert check() == []


def test_check_detects_manual_edit(tmp_path):
    write(tmp_path)
    assert check(tmp_path) == []
    (tmp_path / "tickets.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "extra.json").write_text("{}\n", encoding="utf-8")
    assert check(tmp_path) == ["difiere tickets.json", "sobra extra.json"]


def test_every_ticket_has_label_and_valid_user():
    tickets = load("tickets.json")
    labels = load("tickets_etiquetas.json")
    user_ids = {u["user_id"] for u in load("usuarios.json")}
    assert {t["ticket_id"] for t in tickets} == set(labels)
    assert all(t["user_id"] in user_ids or labels[t["ticket_id"]]["expected_action"] == "ask_identifier" for t in tickets)


def test_homonyms_exist_in_different_departments():
    lauras = [u for u in load("usuarios.json") if u["name"] == "Laura Gómez"]
    assert len(lauras) == 2 and lauras[0]["department"] != lauras[1]["department"]


def test_reimbursements_cover_the_threshold_boundary():
    amounts = {t["amount_eur"] for t in load("tickets.json") if t["amount_eur"] is not None}
    assert REIMBURSEMENT_THRESHOLD_EUR in amounts
    assert any(a < REIMBURSEMENT_THRESHOLD_EUR for a in amounts)
    assert any(a > REIMBURSEMENT_THRESHOLD_EUR for a in amounts)


def test_statuses_and_dates_come_in_mixed_formats():
    tickets = load("tickets.json")
    assert len({t["status"] for t in tickets}) > 3
    assert {type(t["created_at"]) for t in tickets} == {str, int}


def test_superseded_article_points_to_newer_one():
    articles = {a["article_id"]: a for a in load("articulos_kb.json")}
    old = [a for a in articles.values() if a["superseded_by"]]
    assert len(old) == 1
    assert old[0]["updated_at"] < articles[old[0]["superseded_by"]]["updated_at"]


def test_only_synthetic_email_domain():
    assert all(u["email"].endswith(".test") for u in load("usuarios.json"))


def legacy_files():
    return {name: text for name, text in build_all().items() if name.startswith("legacy_inventario/")}


def test_legacy_package_is_valid_python_without_tests():
    files = legacy_files()
    assert 5 <= len(files) - 1 <= 7  # módulos, sin contar __init__.py
    assert not any("test" in name.split("/")[-1] for name in files)
    for name, text in files.items():
        compile(text, name, "exec")


def test_legacy_hidden_dependency_only_inside_function():
    # depreciacion depende de almacen, pero no en sus imports de cabecera:
    # solo se ve leyendo el cuerpo de valor_actual.
    text = legacy_files()["legacy_inventario/depreciacion.py"]
    header = text.split("def ")[0]
    assert "almacen" not in header
    assert "from . import almacen" in text and "_CACHE_ASIGNADOS" in text


def test_legacy_package_runs(tmp_path):
    import importlib
    import sys
    from datetime import date

    write(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        almacen = importlib.import_module("legacy_inventario.almacen")
        asignaciones = importlib.import_module("legacy_inventario.asignaciones")
        informes = importlib.import_module("legacy_inventario.informes")
        almacen.reset()
        almacen.alta("SN-1", "portatil", 1000.0, "01/01/2020")
        hoy = date(2026, 1, 1)
        assert informes.valor_total(hoy) == 0.0
        # La dependencia escondida cambia el resultado: asignado conserva un 10 %.
        asignaciones.asignar("SN-1", "EMP-1001", "02/01/2020")
        assert informes.valor_total(hoy) == 100.0
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m.startswith("legacy_inventario")]:
            del sys.modules[name]


# --- app1 y app3: `repo_mesa/` y `documentos.json` (antes, entrega 2) ---------------------------------------------


def repo_files() -> dict[str, str]:
    return {name: text for name, text in build_all().items() if name.startswith("repo_mesa/")}


def test_repo_mesa_is_valid_python():
    files = repo_files()
    assert files
    for name, text in files.items():
        ast.parse(text, name)


def test_repo_mesa_has_tests_spread_over_several_directories():
    # Para que `Glob` tenga algo que listar: varios directorios, no uno solo.
    test_dirs = {name.rsplit("/", 1)[0] for name in repo_files() if name.rsplit("/", 1)[-1].startswith("test_")}
    assert len(test_dirs) >= 3


def test_wrapper_reexports_with_alias():
    api = repo_files()["repo_mesa/api.py"]
    assert "calcular_sla as sla_ticket" in api


def test_callers_by_direct_name_and_by_alias():
    # El reto de 2.5-S5: hay llamadores que nunca escriben `calcular_sla`.
    files = repo_files()
    direct = {n for n, t in files.items() if "calcular_sla(" in t and not n.endswith(("core/sla.py", "api.py")) and "/test" not in n and not n.rsplit("/", 1)[-1].startswith("test_")}
    alias_only = {n for n, t in files.items() if "sla_ticket" in t or " as plazo" in t} - direct - {"repo_mesa/api.py"}
    assert direct and len(alias_only) >= 2


def test_sla_error_message_is_unique_to_one_file():
    # Mensaje único para buscar con `Grep`: solo aparece donde se lanza.
    matches = [n for n, t in repo_files().items() if "SLA vencido para" in t]
    assert matches == ["repo_mesa/core/sla.py"]


def test_timeout_anchor_appears_exactly_twice_in_config():
    # Precondición de 2.5-K3: `Edit` falla porque el ancla no es única.
    config = repo_files()["repo_mesa/config.py"]
    assert config.count("TIMEOUT = 30\n") == 2
    first, second = config.split("TIMEOUT = 30\n", 1)[0], config.rsplit("TIMEOUT = 30\n", 1)[0]
    assert first != second  # los dos bloques son distintos


@pytest.fixture
def repo_mesa(tmp_path):
    write(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        yield importlib.import_module("repo_mesa.api"), importlib.import_module("repo_mesa.core.sla")
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m.startswith("repo_mesa")]:
            del sys.modules[name]


def test_alias_is_the_same_function(repo_mesa):
    api, sla = repo_mesa
    assert api.sla_ticket is sla.calcular_sla


def test_sla_within_and_over_limit(repo_mesa):
    _, sla = repo_mesa
    assert sla.calcular_sla("alta", 3)["restante_horas"] == 5
    with pytest.raises(ValueError, match="SLA vencido para"):
        sla.calcular_sla("alta", 9)


def catalog_docs() -> dict:
    return json.loads(build_all()["documentos.json"])


def test_documents_catalog_mixes_documents_and_non_documents():
    urls = catalog_docs()["urls"]
    documents = [u for u in urls if u["is_document"]]
    others = [u for u in urls if not u["is_document"]]
    assert documents and len(others) >= 3
    assert all("/docs/" in u["url"] and u["content"] for u in documents)
    assert all("/docs/" not in u["url"] and u["content"] is None for u in others)
    assert all(u["url"].startswith("https://") and ".test/" in u["url"] for u in urls)


def test_claims_have_simple_and_complex_ones_tied_to_real_articles():
    claims = catalog_docs()["afirmaciones"]
    assert {c["verifiable"] for c in claims} == {"simple", "compleja"}
    article_ids = {a["article_id"] for a in json.loads(build_all()["articulos_kb.json"])}
    for claim in claims:
        assert set(claim["article_ids"]) <= article_ids
    # Una afirmación compleja necesita más de un artículo; una simple, uno.
    assert all(len(c["article_ids"]) == 1 for c in claims if c["verifiable"] == "simple")
    assert all(len(c["article_ids"]) > 1 for c in claims if c["verifiable"] == "compleja")


# --- app3: `documentos_compra*.json`, `pedidos_compra.json` y `fuentes_investigacion*.json` (app3/01 a 07) ---------


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


# --- fuente transitoria (B4, app3/04: TS 5.3-S3) ---------------------------------------------------


def test_one_source_fails_once_with_timeout_and_then_answers_and_is_labelled():
    labels = source_labels()
    (transient,) = labels["transient_sources"]
    entry = next(s for s in sources() if s["source_id"] == transient["source_id"])
    assert entry["availability"] == "timeout_once" and entry["report"]  # falla la primera vez; luego hay informe
    assert transient["figure_text"] in entry["report"]
    # No es la fuente que falla siempre ni la vacía: son tres comportamientos distintos.
    assert transient["source_id"] not in labels["failed_sources"] + labels["empty_sources"]


# --- ubicación y fragmento de cada afirmación; relleno distinto del informe largo (B4, app3/05) --------


def test_each_claim_carries_the_section_and_the_literal_sentence_it_comes_from():
    by_id = {s["source_id"]: s for s in sources()}
    for conflict in source_labels()["conflicts"]:
        for claim in conflict["claims"]:
            report = by_id[claim["source_id"]]["report"]
            assert f"## {claim['location']}\n" in report  # la ubicación es el título de una sección de la fuente
            assert claim["excerpt"] in report and claim["figure_text"] in claim["excerpt"]
            section = report.split(f"## {claim['location']}\n")[1].split("\n\n")[0]
            assert claim["excerpt"] in section  # y el fragmento está en esa sección


def test_long_report_filler_is_distinct_with_distraction_figures_of_the_same_kind_as_the_finding():
    import re

    labels = source_labels()["long_report"]
    report = next(s["report"] for s in sources() if s["source_id"] == labels["source_id"])
    paragraphs = report.split("\n\n")
    assert len(paragraphs) == 61 and len(set(paragraphs)) == 61  # ninguno repetido
    assert "apartado" not in report  # sin marcas de relleno
    filler = [p for p in paragraphs if p != labels["key_finding"]]
    distraction = [p for p in filler if re.search(r"\d+(,\d)? % de las incidencias de red", p)]
    assert len(distraction) >= 30  # la mayoría lleva una cifra del mismo tipo que el hallazgo
    figures = [float(m.replace(",", ".")) for p in distraction for m in re.findall(r"(\d+(?:,\d)?) %", p)]
    assert max(figures) < 41 and len(set(figures)) >= 10  # el hallazgo es la cifra mayor, no la única
    assert all(len(p) > 80 for p in paragraphs)


# --- app3: `poblacion_extracciones*.json` (app3/10) y `cambio_revision*.json` (app3/11 y 12) -----------------------


FIELDS = ["vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"]


def population() -> list[dict]:
    return json.loads(build_all()["poblacion_extracciones.json"])


def extraction_labels() -> dict:
    return json.loads(build_all()["poblacion_extracciones_etiquetas.json"])


def outcomes() -> list[tuple[dict, str, float, bool]]:
    truth = extraction_labels()
    return [(r, f, r["confidences"][f], truth[r["record_id"]]["correct"][f]) for r in population() for f in FIELDS]


def test_every_record_has_a_label_and_the_records_never_carry_it():
    assert {r["record_id"] for r in population()} == set(extraction_labels())
    for record in population():
        assert "correct" not in record and "labels" not in record
        assert set(record["confidences"]) == set(FIELDS)
        assert all(0 <= c <= 1 for c in record["confidences"].values())
        assert 0 <= record["doc_confidence"] <= 1
    for label in extraction_labels().values():
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
    def scalars(value):
        """Los valores sueltos de un argumento, también si es una lista o un diccionario."""
        if isinstance(value, dict):
            return [s for v in value.values() for s in scalars(v)]
        if isinstance(value, list):
            return [s for v in value for s in scalars(v)]
        return [value]

    for scenario in labels["existing_scenarios"]:
        assert scenario["expected"], "cada escenario existente dice lo que espera (la clave de un escenario lo incluye)"
        for value in scenario["args"].values():
            assert all(str(s) in text for s in scalars(value))


def test_commit_1_config_defines_each_name_once_so_the_second_block_does_not_override_the_first():
    """`TIMEOUT` se definía dos veces (30 y 60) y la segunda pisaba la del cliente de la API: el fallo sembrado es solo el comentario."""
    names = [line.split("=")[0].strip() for line in change()["commit_1"]["config.py"].splitlines() if re.match(r"^[A-Z_]+ = ", line)]
    assert len(names) == len(set(names)), names
    assert "NOTIF_TIMEOUT" in names and "TIMEOUT" in names


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


# --- app2 y app1: `escalamiento_*.json` (app2/04) e `inventario_equipos*.json` (app1/07) ----------------------------


KINDS = {"explicit_human", "frustration", "policy_gap", "no_progress", "ambiguous_user"}
ACTIONS = {"escalate_now", "offer_resolution", "escalate_policy_gap", "escalate_no_progress", "ask_identifier"}
# 4.2-S1: de 2 a 4 ejemplos. El de «no se puede avanzar» falta a propósito: es un patrón sin ejemplo (4.2-K3).
EXAMPLE_ACTIONS = ACTIONS - {"escalate_no_progress"}


def cases() -> list[dict]:
    return json.loads(build_all()["escalamiento_casos.json"])


def case_labels() -> dict:
    return json.loads(build_all()["escalamiento_casos_etiquetas.json"])


def examples() -> list[dict]:
    return json.loads(build_all()["escalamiento_ejemplos.json"])


def inventory() -> dict:
    return json.loads(build_all()["inventario_equipos.json"])


def inventory_labels() -> dict:
    return json.loads(build_all()["inventario_equipos_etiquetas.json"])


def test_every_case_has_a_label_and_the_case_never_carries_it():
    assert {c["case_id"] for c in cases()} == set(case_labels())
    for case in cases():
        assert "expected_action" not in case and "kind" not in case
        assert case["text"].strip()
    for label in case_labels().values():
        assert label["kind"] in KINDS and label["expected_action"] in ACTIONS


def test_every_kind_is_covered_and_policy_gap_includes_price_matching():
    labels = case_labels()
    by_kind = {k: [c for c in cases() if labels[c["case_id"]]["kind"] == k] for k in KINDS}
    assert all(len(v) >= 2 for v in by_kind.values())
    # El ejemplo de la guía: igualar el precio de la competencia cuando la política solo contempla el propio sitio.
    assert any("compet" in c["text"].lower() for c in by_kind["policy_gap"])


def test_the_action_follows_the_kind():
    expected = {
        "explicit_human": "escalate_now",
        "frustration": "offer_resolution",
        "policy_gap": "escalate_policy_gap",
        "no_progress": "escalate_no_progress",
        "ambiguous_user": "ask_identifier",
    }
    for label in case_labels().values():
        assert label["expected_action"] == expected[label["kind"]]


def test_frustration_cases_have_a_followup_that_insists_on_a_person():
    """5.2-K2/S3: se ofrece resolver y solo se escala si el cliente reitera su preferencia por un humano."""
    for case in cases():
        label = case_labels()[case["case_id"]]
        if label["kind"] == "frustration":
            assert case["followup"].strip()
            assert label["after_followup"] == "escalate_now"
        else:
            assert "followup" not in case


def test_ambiguous_cases_list_every_matching_employee():
    users = json.loads(build_all()["usuarios.json"])
    for case in cases():
        label = case_labels()[case["case_id"]]
        if label["kind"] != "ambiguous_user":
            continue
        name = label["name"]
        matches = sorted(u["user_id"] for u in users if u["name"] == name)
        assert len(matches) >= 2
        assert label["candidates"] == matches
        assert name in case["text"]


def test_few_shot_examples_are_disjoint_from_the_evaluation_cases():
    """4.2-K3: si un ejemplo es un caso evaluado, la medida premia la memoria y no el juicio."""
    evaluated = {c["text"] for c in cases()}
    all_tickets = {t["body"] if "body" in t else t.get("text", "") for t in json.loads(build_all()["tickets.json"])}
    for example in examples():
        assert example["text"] not in evaluated
        assert example["text"] not in all_tickets
    assert 2 <= len(examples()) <= 4  # 4.2-S1: de 2 a 4 ejemplos


def test_examples_show_the_reasoning_and_cover_four_of_the_five_actions():
    for example in examples():
        assert example["action"] in ACTIONS
        assert len(example["reasoning"].split()) >= 12, "el razonamiento es lo que se enseña (4.2-S1)"
        assert example["rejected_alternative"].strip()
    assert {e["action"] for e in examples()} == EXAMPLE_ACTIONS


def test_inventory_has_forty_fields_per_team_and_five_relevant():
    data = inventory()
    assert len(data["teams"]) >= 6
    relevant = inventory_labels()["relevant_fields"]
    assert len(relevant) == 5
    for team in data["teams"]:
        assert len(team) == 40
        assert set(relevant) <= set(team)


def test_inventory_answer_is_computable_from_the_relevant_fields_alone():
    """Recortar a 5 campos no puede cambiar la respuesta: es la condición de 5.1-S3."""
    labels = inventory_labels()
    teams = inventory()["teams"]
    unassigned = {t["team_id"]: t["laptops_total"] - t["laptops_assigned"] for t in teams}
    best = max(unassigned, key=unassigned.get)
    assert labels["expected"]["team_with_most_unassigned_laptops"] == best
    assert sorted(unassigned.values())[-1] > sorted(unassigned.values())[-2], "sin empate"


def test_inventory_noise_is_bulky():
    """Los 35 campos que sobran pesan de verdad: si fueran cortos, el recorte apenas se notaría en los tokens."""
    relevant = set(inventory_labels()["relevant_fields"])
    team = inventory()["teams"][0]
    noise = len(json.dumps({k: v for k, v in team.items() if k not in relevant}, ensure_ascii=False))
    signal = len(json.dumps({k: v for k, v in team.items() if k in relevant}, ensure_ascii=False))
    assert noise >= 6 * signal


def test_is_deterministic_from_entrega3d():
    for name in ("escalamiento_casos.json", "escalamiento_ejemplos.json", "inventario_equipos.json"):
        assert build_all()[name] == build_all()[name]


def test_no_progress_cases_say_the_user_already_tried_what_the_knowledge_base_offers():
    """5.2-K1, tercer disparador: la imposibilidad de avanzar. El caso lo hace evidente sin tono de enfado."""
    labels = case_labels()
    stuck = [c for c in cases() if labels[c["case_id"]]["kind"] == "no_progress"]
    assert len(stuck) >= 2
    kb_titles = " ".join(a["title"].lower() for a in json.loads(build_all()["articulos_kb.json"]))
    for case in stuck:
        text = case["text"].lower()
        assert any(w in text for w in ("ya ", "seguí", "probé")), "el cliente ya intentó lo que ofrece la base"
        assert "followup" not in case
    assert "sincronización" in kb_titles and "batería" in kb_titles, "los dos casos se apoyan en artículos que existen"


def test_assigned_never_exceeds_total_in_the_noise_fields():
    """Ruido incoherente (más asignados que existentes) despista sin enseñar nada."""
    for team in inventory()["teams"]:
        for kind in ("laptops", "monitors", "phones"):
            if f"{kind}_assigned" in team:
                assert team[f"{kind}_assigned"] <= team[f"{kind}_total"], (team["team_id"], kind)
