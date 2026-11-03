"""Tests de app3/07_extraccion_schema: schema por variante, validador de forma, puntuación contra etiquetas, petición por modo de `tool_choice`, tools por tipo y few-shot. Sin modelo."""

import json
from types import SimpleNamespace

import pytest

from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/07_extraccion_schema.py")

LABELS = load("documentos_compra_etiquetas.json")
DOCS = {d["doc_id"]: d["text"] for d in load("documentos_compra.json")}


def props(tool):
    return tool["input_schema"]["properties"]


def allows_null(spec):
    kind = spec["type"]
    return "null" in kind if isinstance(kind, list) else False


# --- schema por variante ---------------------------------------------------------------

def test_correct_schema_makes_optional_fields_nullable_and_not_required():
    tool = mod.build_tool("correcta")
    assert tool["name"] == "extract_metadata"
    for field in mod.OPTIONAL_FIELDS:
        assert allows_null(props(tool)[field]), field
        assert field not in tool["input_schema"]["required"]
    assert set(tool["input_schema"]["required"]) == {"doc_type", "line_items"}


def test_correct_schema_enum_has_other_and_unclear_with_a_detail_field():
    tool = mod.build_tool("correcta")
    assert set(props(tool)["doc_type"]["enum"]) == {"invoice", "delivery_note", "other", "unclear"}
    assert allows_null(props(tool)["doc_type_detail"])


def test_correct_schema_puts_normalization_rules_in_the_descriptions():
    text = json.dumps(mod.build_tool("correcta"), ensure_ascii=False)
    assert "YYYY-MM-DD" in text and "punto decimal" in text


def test_normalization_can_be_left_out():
    text = json.dumps(mod.build_tool("correcta", normalization=False), ensure_ascii=False)
    assert "YYYY-MM-DD" not in text and "punto decimal" not in text


def test_sin_nullable_makes_everything_required_and_non_null():
    tool = mod.build_tool("sin_nullable")
    assert set(tool["input_schema"]["required"]) == set(props(tool))
    assert not any(allows_null(spec) for spec in props(tool).values())
    item = props(tool)["line_items"]["items"]
    assert "unit_price" in item["required"] and not allows_null(item["properties"]["unit_price"])


def test_enum_cerrado_drops_other_and_unclear_but_keeps_nullables():
    tool = mod.build_tool("enum_cerrado")
    assert set(props(tool)["doc_type"]["enum"]) == {"invoice", "delivery_note"}
    assert allows_null(props(tool)["po_number"])


def test_unknown_variant_fails():
    with pytest.raises(ValueError):
        mod.build_tool("otra")


# --- validador de forma (sintaxis) -------------------------------------------------------

def test_label_as_extraction_conforms_to_the_correct_schema_for_every_document():
    tool = mod.build_tool("correcta")
    for doc_id, label in LABELS.items():
        data = mod.label_to_extraction(label)
        assert mod.conforms(data, tool["input_schema"]) == [], doc_id


def test_conforms_reports_each_kind_of_violation():
    schema = mod.build_tool("correcta")["input_schema"]
    good = mod.label_to_extraction(LABELS["DC-01"])
    assert mod.conforms({k: v for k, v in good.items() if k != "doc_type"}, schema) == ["falta doc_type"]
    assert any("tipo" in e for e in mod.conforms({**good, "stated_total": "3085,50"}, schema))
    assert any("enum" in e for e in mod.conforms({**good, "doc_type": "factura"}, schema))
    # `null` vale donde el schema lo permite y no donde no.
    assert mod.conforms({**good, "po_number": None}, schema) == []
    assert mod.conforms({**good, "doc_type": None}, schema)
    # Y dentro de las líneas.
    bad_line = {**good, "line_items": [{"description": "x", "quantity": "dos"}]}
    assert any("quantity" in e for e in mod.conforms(bad_line, schema))


def test_syntax_is_not_semantics():
    # Un valor correcto de forma y falso de fondo: el schema lo deja pasar, las etiquetas no.
    schema = mod.build_tool("correcta")["input_schema"]
    wrong = {**mod.label_to_extraction(LABELS["DC-01"]), "vendor": "Proveedor inventado S.A."}
    assert mod.conforms(wrong, schema) == []
    assert "vendor" in mod.score_extraction(wrong, LABELS["DC-01"], schema).wrong


# --- puntuación contra etiquetas --------------------------------------------------------

def score(data, doc_id="DC-02", variant="correcta"):
    return mod.score_extraction(data, LABELS[doc_id], mod.build_tool(variant)["input_schema"])


def test_perfect_extraction_scores_clean():
    for doc_id, label in LABELS.items():
        s = score(mod.label_to_extraction(label), doc_id)
        assert (s.invented, s.wrong, s.missing, s.type_ok, s.in_enum, s.syntax_ok, s.lines_ok) == ([], [], [], True, True, True, True), doc_id
        assert s.absent_total == sum(v is None for v in label["fields"].values())


def test_anything_but_null_in_an_absent_field_counts_as_invented():
    # DC-02 no tiene pedido: 'null' como texto, cadena vacía y un valor deducido son inventos.
    base = mod.label_to_extraction(LABELS["DC-02"])
    for filler in ("null", "", "PO-0000", "N/A"):
        assert score({**base, "po_number": filler}).invented == ["po_number"], filler
    assert score(base).invented == []


def test_missing_and_wrong_values_are_told_apart_with_light_normalization():
    base = mod.label_to_extraction(LABELS["DC-01"])
    assert score({**base, "issue_date": None}, "DC-01").missing == ["issue_date"]
    assert score({**base, "issue_date": "14/09/2026"}, "DC-01").wrong == ["issue_date"]
    assert score({**base, "vendor": "  suministros ibéricos s.l. "}, "DC-01").wrong == []
    assert score({**base, "stated_total": 3085.504}, "DC-01").wrong == []
    assert score({**base, "stated_total": 3085.0}, "DC-01").wrong == ["stated_total"]


def test_type_forced_outside_the_enum_is_detected():
    base = mod.label_to_extraction(LABELS["DC-06"])  # certificado de garantía: other
    closed = score({**base, "doc_type": "other"}, "DC-06", "enum_cerrado")
    assert closed.type_ok and not closed.in_enum  # el modelo se escapó del enum cerrado
    forced = score({**base, "doc_type": "invoice"}, "DC-06", "enum_cerrado")
    assert not forced.type_ok and forced.in_enum  # forzado a una categoría que no es


def test_other_needs_a_detail_that_names_the_kind():
    base = mod.label_to_extraction(LABELS["DC-06"])
    assert score(base, "DC-06").detail_ok is True
    assert score({**base, "doc_type_detail": None}, "DC-06").detail_ok is False
    assert score({**base, "doc_type_detail": "Certificado de garantía extendida"}, "DC-06").detail_ok is True
    assert score(mod.label_to_extraction(LABELS["DC-01"]), "DC-01").detail_ok is None  # no aplica


def test_lines_are_compared_as_quantity_and_price_regardless_of_order_and_wording():
    base = mod.label_to_extraction(LABELS["DC-01"])
    shuffled = {**base, "line_items": list(reversed(base["line_items"]))}
    assert score(shuffled, "DC-01").lines_ok
    other_words = {**base, "line_items": [{**i, "description": "otra cosa"} for i in base["line_items"]]}
    assert score(other_words, "DC-01").lines_ok
    wrong_qty = {**base, "line_items": [{**base["line_items"][0], "quantity": 4}, base["line_items"][1]]}
    assert not score(wrong_qty, "DC-01").lines_ok


def test_summarize_adds_up_the_scores():
    scores = [score(mod.label_to_extraction(LABELS["DC-02"])), score({**mod.label_to_extraction(LABELS["DC-02"]), "po_number": "PO-0000"})]
    summary = mod.summarize(scores)
    assert summary["documentos"] == 2 and summary["inventados"] == 1
    assert summary["ausentes"] == 2 * scores[0].absent_total
    assert summary["tipo_ok"] == 2 and summary["fuera_de_enum"] == 0 and summary["sintaxis_ok"] == 2


# --- petición por modo de tool_choice -----------------------------------------------------

def test_choice_for_each_mode():
    assert mod.choice_for("forzada") == {"type": "tool", "name": "extract_metadata"}
    assert mod.choice_for("any") == {"type": "any"}
    assert mod.choice_for("auto") == {"type": "auto"}
    with pytest.raises(ValueError):
        mod.choice_for("otro")


def test_request_for_the_forced_part_carries_one_tool_and_the_forced_choice():
    request = mod.build_request(DOCS["DC-01"], tools=[mod.build_tool("correcta")], mode="forzada", model="m")
    assert [t["name"] for t in request["tools"]] == ["extract_metadata"]
    assert request["tool_choice"] == {"type": "tool", "name": "extract_metadata"}
    assert request["model"] == "m" and request["max_tokens"] > 0
    assert DOCS["DC-01"] in request["messages"][0]["content"]


def test_request_never_leaks_the_document_id_or_the_labels():
    # Con el id en el prompt el modelo lo copió como número de documento (docs/hallazgos.md).
    request = mod.build_request(DOCS["DC-07"], tools=[mod.build_tool("correcta")], mode="forzada", model="m")
    text = json.dumps(request, ensure_ascii=False)
    assert "DC-07" not in text and "doc_type\": \"unclear" not in text


# --- tools por tipo (tool_choice any) --------------------------------------------------------

def test_one_tool_per_document_type_with_its_own_fields():
    tools = {t["name"]: t for t in mod.build_type_tools()}
    assert set(tools) == {"extract_invoice", "extract_delivery_note", "extract_other"}
    assert "stated_total" in props(tools["extract_invoice"]) and "stated_total" not in props(tools["extract_delivery_note"])
    assert "doc_type_detail" in props(tools["extract_other"])
    for tool in tools.values():
        assert "input_schema" in tool and tool["description"]


def test_any_request_offers_all_the_type_tools_and_no_forced_one():
    request = mod.build_request(DOCS["DC-07"], tools=mod.build_type_tools(), mode="any", model="m")
    assert request["tool_choice"] == {"type": "any"} and len(request["tools"]) == 3


def test_expected_tool_by_label_type():
    assert mod.expected_tool(LABELS["DC-01"]) == "extract_invoice"
    assert mod.expected_tool(LABELS["DC-03"]) == "extract_delivery_note"
    assert mod.expected_tool(LABELS["DC-06"]) == "extract_other"
    assert mod.expected_tool(LABELS["DC-07"]) == "extract_other"


def test_first_tool_use_and_truncation_flags():
    use = SimpleNamespace(type="tool_use", name="extract_metadata", input={"doc_type": "invoice"}, id="t1")
    text = SimpleNamespace(type="text", text="hola")
    response = SimpleNamespace(content=[text, use], stop_reason="tool_use")
    assert mod.first_tool_use(response) == ("extract_metadata", {"doc_type": "invoice"})
    assert mod.first_tool_use(SimpleNamespace(content=[text], stop_reason="end_turn")) is None


# --- few-shot -------------------------------------------------------------------------------

def test_few_shot_examples_cover_the_three_forms_and_are_not_dataset_documents():
    texts = [example[0] for example in mod.FEW_SHOT]
    assert len(texts) == 3
    assert any("|" in t for t in texts)
    assert any(t.count("\n") <= 1 for t in texts)  # prosa
    assert any("x " in t and "|" not in t and t.count("\n") >= 2 for t in texts)  # líneas sueltas
    for text in texts:
        assert text not in DOCS.values()


def test_few_shot_extractions_conform_to_the_schema_and_show_a_null():
    schema = mod.build_tool("correcta")["input_schema"]
    for _, extraction in mod.FEW_SHOT:
        assert mod.conforms(extraction, schema) == []
    assert any(None in extraction.values() for _, extraction in mod.FEW_SHOT)


def test_system_prompt_carries_the_examples_only_when_asked():
    plain = mod.build_request(DOCS["DC-01"], tools=[mod.build_tool("correcta")], mode="forzada", model="m")
    shots = mod.build_request(DOCS["DC-01"], tools=[mod.build_tool("correcta")], mode="forzada", model="m", few_shot=True)
    assert plain["system"] == mod.SYSTEM
    assert shots["system"].startswith(mod.SYSTEM) and all(text in shots["system"] for text, _ in mod.FEW_SHOT)
