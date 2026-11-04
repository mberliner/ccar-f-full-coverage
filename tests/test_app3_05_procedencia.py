"""Tests de app3/05_procedencia: forma de lo que devuelve cada subagente, comprobador de procedencia, detector de cifras fusionadas y variantes. Sin modelo."""

import json

from harness.data import load
from harness.offline import run_hook
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/05_procedencia.py")

P = "mcp__investigacion__"
QUERY = P + "query_source"
LABELS = load("fuentes_investigacion_etiquetas.json")
CATALOG = {s["source_id"]: s for s in load("fuentes_investigacion.json")}
RESOLUTION, SATISFACTION, REOPENED = LABELS["conflicts"]


def claim(source_id="SRC-TICKETS", text="Tiempo medio de resolución", figure=18, unit="horas", published_at=None):
    return {
        "content": {"claim": text, "figure": figure, "unit": unit},
        "metadata": {"source_id": source_id, "published_at": published_at or CATALOG[source_id]["published_at"]},
    }


def call(cid, name, agent="researcher", input_=None, *, text="{}"):
    return ToolCall(cid, name, input_ or {}, "r1", agent, True, False, text)


def delegation(cid, subagent, prompt="x", result="{}"):
    return call(cid, "Agent", "principal", {"subagent_type": subagent, "prompt": prompt}, text=result)


# --- variantes y opciones --------------------------------------------------------------------

def test_variants_parts_and_texts():
    assert mod.ANTI_VARIANTS == ["sin_procedencia", "promedio"]
    assert mod.PARTES == ["conflictos", "medio"]
    assert mod.TEXTOS == ["sin_resumen", "con_resumen", "con_encabezados", "encabezados_y_resumen"]


def test_each_text_variant_switches_the_summary_and_the_headings_of_the_long_report():
    assert mod.text_flags("sin_resumen") == {"summary_first": False, "headings": False}
    assert mod.text_flags("con_resumen") == {"summary_first": True, "headings": False}
    assert mod.text_flags("con_encabezados") == {"summary_first": False, "headings": True}
    assert mod.text_flags("encabezados_y_resumen") == {"summary_first": True, "headings": True}


def test_each_part_asks_for_the_sources_it_needs_without_revealing_the_conflicts():
    request = mod.request_for("conflictos")
    for source_id in ("SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-PROVEEDOR", "SRC-CUADRO", "SRC-OFICINA"):
        assert source_id in request
    assert "SRC-MONITOR" not in request and "SRC-LARGO" not in request
    for word in ("conflicto", "discrep", "contradic"):
        assert word not in request.lower()
    long_request = mod.request_for("medio")
    assert "SRC-LARGO" in long_request and "SRC-TICKETS" not in long_request


def test_researcher_returns_structured_claims_with_content_apart_from_metadata():
    prompt = mod.researcher_prompt(None)
    for key in ("claim", "figure", "unit", "source_id", "published_at", "content", "metadata"):
        assert key in prompt
    # Contexto metodológico (periodo, método, muestra, población) junto a la cifra, para que llegue a la síntesis.
    assert "context" in prompt and "método" in prompt and "periodo" in prompt


def test_sin_procedencia_asks_the_researcher_for_prose():
    prompt = mod.researcher_prompt("sin_procedencia")
    assert "metadata" not in prompt and "source_id" not in prompt and "JSON" not in prompt
    assert mod.researcher_prompt("promedio") == mod.researcher_prompt(None)


def test_correct_synthesizer_keeps_the_mapping_separates_disputed_and_never_merges():
    prompt = mod.synthesizer_prompt(None).lower()
    for word in ("fuente", "fecha", "establecid", "disputad", "tabla", "prosa"):
        assert word in prompt
    # Contexto metodológico: explica la diferencia si el periodo o el método la explican; si no, la deja como disputada.
    assert "periodo" in prompt and "método" in prompt and "no la explique" in prompt
    assert "promedi" not in prompt and "consolid" not in prompt


def test_promedio_asks_the_synthesizer_for_a_single_consolidated_figure():
    prompt = mod.synthesizer_prompt("promedio").lower()
    assert "promedi" in prompt
    assert mod.synthesizer_prompt("sin_procedencia") == mod.synthesizer_prompt(None)


def test_agents_roles_and_tools():
    agents = mod.build_agents(None, "modelo")
    assert set(agents) == {"researcher", "synthesizer"}
    assert agents["researcher"].tools == [QUERY] and agents["synthesizer"].tools == []
    assert all(a.background is False and a.model == "modelo" for a in agents.values())


def test_coordinator_prompt_sets_goals_and_asks_for_the_full_structured_claims():
    prompt = mod.coordinator_prompt(None).lower()
    assert "procedencia" in prompt and "completas" in prompt
    assert "paso 1" not in prompt and "query_source" not in prompt


def test_options_follow_the_subagent_pattern_and_texto_switches_the_server_summary():
    options = mod.build_options(None, texto="sin_resumen", budget=0.5, model="m", subagent_model="s")
    assert options.tools == ["Agent"] and options.permission_mode == "dontAsk"
    assert options.setting_sources == [] and options.max_budget_usd == 0.5
    assert QUERY in options.allowed_tools and "Agent" in options.allowed_tools
    assert options.env["CLAUDE_CODE_FORK_SUBAGENT"] == "0"
    assert options.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.matcher == "mcp__investigacion__.*" and matcher.hooks == [mod.coordinator_gate]
    assert run_hook(mod.coordinator_gate, "PreToolUse", QUERY, {"source_id": "x"}).decision == "deny"
    assert mod.build_options(None, texto="con_resumen", budget=0.5, model="m", subagent_model="s").mcp_servers.keys() == options.mcp_servers.keys()


# --- lo que devuelve cada subagente ----------------------------------------------------------

def test_claim_problems_accepts_a_well_formed_claim_and_null_figures():
    assert mod.claim_problems(claim()) == []
    assert mod.claim_problems(claim(figure=None, unit=None)) == []  # un hallazgo cualitativo no tiene cifra


def test_claim_problems_names_what_is_missing_or_wrong():
    assert mod.claim_problems({"claim": "x", "source_id": "SRC-TICKETS"}) == ["falta content", "falta metadata"]
    no_source = claim()
    no_source["metadata"]["source_id"] = None
    assert mod.claim_problems(no_source) == ["metadata sin source_id"]
    unknown = claim()
    unknown["metadata"]["source_id"] = "SRC-INVENTADA"
    assert mod.claim_problems(unknown) == ["source_id desconocido: SRC-INVENTADA"]
    assert mod.claim_problems(claim(published_at="2026-01-01")) == ["fecha no coincide con la de SRC-TICKETS"]
    no_date = claim()
    no_date["metadata"]["published_at"] = None
    assert mod.claim_problems(no_date) == ["metadata sin published_at"]
    no_text = claim(text="")
    assert mod.claim_problems(no_text) == ["content sin claim"]
    # El contenido no lleva metadatos mezclados.
    mixed = claim()
    mixed["content"]["source_id"] = "SRC-TICKETS"
    assert mod.claim_problems(mixed) == ["content mezcla metadatos: source_id"]


def test_subagent_claims_reads_objects_lists_and_wrapped_lists_from_researcher_results_only():
    a, b, c = claim(), claim("SRC-AUDITORIA", figure=26), claim("SRC-ENCUESTA", "Satisfacción media", 4.1, "sobre 5")
    rec = RunRecord(tool_calls=[
        delegation("d1", "researcher", result="Hallazgos:\n" + json.dumps([a, b]) + "\nnotas sueltas " + json.dumps({"claims": [c]})),
        delegation("d2", "synthesizer", result=json.dumps(claim("SRC-PROVEEDOR"))),  # del sintetizador: no cuenta
        delegation("d3", "researcher", result='{"otra": 1} y {roto'),
    ])
    found = mod.subagent_claims(rec)
    assert [x["metadata"]["source_id"] for x in found] == ["SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA"]
    assert mod.subagent_claims(RunRecord()) == []


def test_structured_share_is_the_fraction_of_claims_with_no_problems():
    bad = claim()
    bad["metadata"]["published_at"] = None
    rec = RunRecord(tool_calls=[delegation("d1", "researcher", result=json.dumps([claim(), claim("SRC-AUDITORIA", figure=26), bad]))])
    assert mod.structured_share(rec) == (2, 3)
    assert mod.structured_share(RunRecord()) == (0, 0)


def test_sources_passed_to_the_synthesizer_compare_what_the_researcher_found_with_its_prompt():
    claims = json.dumps([claim(), claim("SRC-AUDITORIA", figure=26), claim("SRC-ENCUESTA", "Satisfacción", 4.1, "sobre 5")])
    prompt = "Pregunta... " + json.dumps([claim(), claim("SRC-ENCUESTA", "Satisfacción", 4.1, "sobre 5")])
    rec = RunRecord(tool_calls=[delegation("d1", "researcher", result=claims), delegation("d2", "synthesizer", prompt=prompt)])
    assert mod.sources_passed(rec) == {"found": ["SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-TICKETS"], "passed": ["SRC-ENCUESTA", "SRC-TICKETS"], "missing": ["SRC-AUDITORIA"]}


# --- comprobador de procedencia ---------------------------------------------------------------

GOOD = (
    "| Magnitud | Cifra | Fuente | Fecha |\n"
    "| Tickets cerrados | 1.240 | SRC-TICKETS y SRC-AUDITORIA | 2026-10-02 |\n\n"
    "Tiempo de resolución: SRC-TICKETS (2026-10-02) da 18 horas; SRC-AUDITORIA (2026-10-09) da 26 horas.\n"
    "Satisfacción: la Encuesta interna de satisfacción da 4,1 sobre 5; el Informe del proveedor de soporte externo da 3,6 sobre 5.\n"
)


def test_figures_with_source_requires_the_source_in_the_same_sentence_or_row():
    result = mod.figures_with_source(GOOD)
    assert result == {"1.240": True, "18": True, "26": True, "4,1": True, "3,6": True}
    # La misma información sin fuentes: las cifras están, su procedencia no.
    bare = "Se cerraron 1.240 tickets. El tiempo medio fue de 18 o de 26 horas. La satisfacción fue de 4,1 o de 3,6 sobre 5."
    assert mod.figures_with_source(bare) == {"1.240": False, "18": False, "26": False, "4,1": False, "3,6": False}


def test_figures_with_source_leaves_out_figures_that_are_not_in_the_text():
    assert mod.figures_with_source("SRC-TICKETS: 18 horas.") == {"18": True}
    assert mod.figures_with_source(None) == {}


def test_a_figure_is_not_found_inside_another_number():
    # «18» no está en «2026-10-18» ni en «118», y «4,1» no está en «14,12».
    assert mod.figures_with_source("SRC-TICKETS, 2026-10-18, 118 tickets, 14,12") == {}


def test_provenance_share_counts_figures_with_their_source():
    assert mod.provenance_share(GOOD) == (5, 5)
    assert mod.provenance_share("1.240 tickets, 18 horas y 26 horas (SRC-ENCUESTA).") == (0, 3)  # una fuente que no es la de esas cifras no vale
    assert mod.provenance_share("1.240 tickets, 18 horas y 26 horas (SRC-AUDITORIA).") == (2, 3)  # respalda el total y el 26, no el 18
    assert mod.provenance_share("nada") == (0, 0)


# --- cifras fusionadas ------------------------------------------------------------------------

def test_merged_figures_detects_an_average_of_conflicting_figures():
    assert mod.merged_figures("El tiempo medio de resolución es de 22 horas.") == [("tiempo medio de resolución", "22")]
    assert mod.merged_figures("La satisfacción media consolidada es de 3,85 sobre 5.") == [("satisfacción media", "3,85")]
    assert ("satisfacción media", "3,9") in mod.merged_figures("Satisfacción: 3,9 sobre 5.")
    assert ("satisfacción media", "3.85") in mod.merged_figures("Satisfacción: 3.85 sobre 5.")


def test_merged_figures_does_not_flag_the_original_figures_or_embedded_numbers():
    assert mod.merged_figures(GOOD) == []
    assert mod.merged_figures("Se revisaron 122 tickets el 22/10 y 2026-10-22.") == []
    assert mod.merged_figures(None) == []


# --- conflictos presentados y hallazgo clave ---------------------------------------------------

def test_conflicts_presented_needs_both_figures_and_a_word_that_says_they_differ():
    topics = ["tiempo medio de resolución", "satisfacción media", "tickets reabiertos"]
    only = lambda *on: {t: t in on for t in topics}  # noqa: E731
    text = "El tiempo difiere: SRC-TICKETS da 18 horas y SRC-AUDITORIA 26 horas."
    assert mod.conflicts_presented(text) == only("tiempo medio de resolución")
    assert mod.conflicts_presented(GOOD) == only()  # cifras sí, pero no dice que discrepan
    both = GOOD + "Las dos fuentes de cada magnitud discrepan y no se concilian."
    assert mod.conflicts_presented(both) == only("tiempo medio de resolución", "satisfacción media")
    assert mod.conflicts_presented(None) == only()


def test_uses_table_detects_a_markdown_table():
    assert mod.uses_table(GOOD) and not mod.uses_table("Texto sin tabla. 18 | 26") and not mod.uses_table(None)


def test_key_finding_reported_looks_for_the_figure_in_the_text():
    assert mod.key_finding_reported("El 41 % de las incidencias se debió a un perfil de VPN.")
    assert mod.key_finding_reported("Un 41% de las incidencias.") and mod.key_finding_reported("el 41 por ciento")
    assert not mod.key_finding_reported("Se completó la formación y el 141 % no existe.") and not mod.key_finding_reported(None)


# --- explicación de los conflictos: periodo y método frente a desacuerdo sin explicación (TS 5.6) ----

REPORT = (
    "El tiempo medio de resolución difiere: 18 horas (SRC-TICKETS) frente a 26 horas (SRC-AUDITORIA), porque la auditoría cuenta las esperas y es una muestra de 300 tickets.\n"
    "La satisfacción media: 4,1 sobre 5 (encuesta interna) frente a 3,6 sobre 5 del proveedor, que tiene corte a 31 de agosto.\n"
    "Los tickets reabiertos: 7,3 % (SRC-CUADRO) y 12,4 % (SRC-OFICINA) discrepan y nada en las fuentes lo explica."
)


def test_the_third_pair_has_no_explanation_in_the_labels_and_the_other_two_do():
    explained = {c["topic"]: c["explained_by"] for c in LABELS["conflicts"]}
    assert explained["tickets reabiertos"] == ["sin_explicacion"]
    assert mod.EXPLAINED_TOPICS == ["tiempo medio de resolución", "satisfacción media"]
    assert mod.UNEXPLAINED_TOPICS == ["tickets reabiertos"]


def test_explanation_found_lists_which_kinds_of_context_the_report_gives_for_each_pair():
    found = mod.explanation_found(REPORT)
    assert found["tiempo medio de resolución"] == ["metodo", "muestra"]
    assert found["satisfacción media"] == ["periodo"]
    assert found["tickets reabiertos"] == []  # no se atribuye a ninguna fecha ni método


def test_explanation_found_reads_a_note_that_names_the_topic_but_gives_no_figures():
    note = "Tiempo medio de resolución: 18 y 26 horas.\nNota sobre el tiempo medio de resolución: la auditoría usa otro método y cuenta las esperas."
    assert mod.explanation_found(note)["tiempo medio de resolución"] == ["metodo"]
    # Una explicación de otro par no se cuela: va por líneas.
    assert mod.explanation_found("Satisfacción 4,1 y 3,6.\nResolución 18 y 26: la muestra y las esperas.")["satisfacción media"] == []


def test_explained_by_metadata_is_true_when_the_report_uses_a_label_explanation():
    assert mod.explained_by_metadata(REPORT) == {"tiempo medio de resolución": True, "satisfacción media": True}
    # Cifras y desacuerdo, sin decir por qué: no explica.
    bare = "Resolución: 18 horas y 26 horas difieren. Satisfacción: 4,1 y 3,6 discrepan."
    assert mod.explained_by_metadata(bare) == {"tiempo medio de resolución": False, "satisfacción media": False}
    assert mod.explained_by_metadata(None) == {"tiempo medio de resolución": False, "satisfacción media": False}


def test_unexplained_status_tells_disputed_from_wrongly_attributed_to_date_or_method():
    assert mod.unexplained_status(REPORT) == {"tickets reabiertos": {"attributed": False, "disputed": True}}
    wrong = "Los tickets reabiertos: 7,3 % y 12,4 %; la diferencia se debe al periodo de medición y al método."
    assert mod.unexplained_status(wrong) == {"tickets reabiertos": {"attributed": True, "disputed": False}}
    silent = "Los tickets reabiertos fueron 7,3 % y 12,4 %."
    assert mod.unexplained_status(silent) == {"tickets reabiertos": {"attributed": False, "disputed": False}}
    assert mod.unexplained_status(None) == {"tickets reabiertos": {"attributed": False, "disputed": False}}


def test_merged_figures_covers_the_third_pair_without_flagging_its_originals():
    assert mod.merged_figures("Reabiertos: 9,85 %.") == [("tickets reabiertos", "9,85")]
    assert mod.merged_figures(REPORT) == []
