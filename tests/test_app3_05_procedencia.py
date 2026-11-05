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
    # Por defecto la ubicación y el fragmento son los de la cifra de esa fuente en el catálogo; si no hay, el primer apartado.
    location, excerpt = "Resumen", "Resumen del tercer trimestre de 2026."
    for conflict in LABELS["conflicts"]:
        for c in conflict["claims"]:
            if c["source_id"] == source_id and c["figure"] == figure:
                location, excerpt = c["location"], c["excerpt"]
    return {
        "content": {"claim": text, "figure": figure, "unit": unit},
        "metadata": {
            "source_id": source_id, "published_at": published_at or CATALOG[source_id]["published_at"],
            "location": location, "excerpt": excerpt, "relevance": 0.9,
        },
    }


def call(cid, name, agent="researcher", input_=None, *, text="{}"):
    return ToolCall(cid, name, input_ or {}, "r1", agent, True, False, text)


def delegation(cid, subagent, prompt="x", result="{}"):
    return call(cid, "Agent", "principal", {"subagent_type": subagent, "prompt": prompt}, text=result)


# --- variantes y opciones --------------------------------------------------------------------

def test_variants_parts_and_texts():
    assert mod.ANTI_VARIANTS == ["sin_procedencia", "promedio", "formato_uniforme", "inventar_explicacion"]
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
    # Ubicación en la fuente, fragmento literal y puntuación de relevancia (TS 5.1-S5, 5.6-S1, 5.1-S6), en los metadatos.
    for key in ("location", "excerpt", "relevance"):
        assert key in prompt
    # Contexto metodológico (periodo, método, muestra, población) junto a la cifra, para que llegue a la síntesis.
    assert "context" in prompt and "método" in prompt and "periodo" in prompt


def test_sin_procedencia_asks_the_researcher_for_verbose_prose_with_its_reasoning_and_no_metadata():
    prompt = mod.researcher_prompt("sin_procedencia")
    assert "metadata" not in prompt and "source_id" not in prompt and "JSON" not in prompt
    assert "razonamiento" in prompt and "prosa" in prompt  # verbosa: con su razonamiento
    for key in ("location", "excerpt", "relevance", "published_at"):
        assert key not in prompt
    for name in ("promedio", "formato_uniforme", "inventar_explicacion"):
        assert mod.researcher_prompt(name) == mod.researcher_prompt(None)


def test_correct_synthesizer_keeps_the_mapping_separates_disputed_and_never_merges():
    prompt = mod.synthesizer_prompt(None).lower()
    for word in ("fuente", "fecha", "establecid", "disputad", "tabla", "prosa"):
        assert word in prompt
    # La reconciliación la decide el coordinador (TS 5.6-S3): el sintetizador la respeta y no explica lo que el contexto no explica.
    assert "coordinador" in prompt and "decisi" in prompt and "periodo" in prompt and "método" in prompt and "no la explique" in prompt
    assert "promedi" not in prompt and "consolid" not in prompt


def test_promedio_asks_the_synthesizer_for_a_single_consolidated_figure():
    prompt = mod.synthesizer_prompt("promedio").lower()
    assert "promedi" in prompt
    assert mod.synthesizer_prompt("sin_procedencia") == mod.synthesizer_prompt(None)


def test_formato_uniforme_asks_for_prose_everywhere_with_no_format_by_content_type():
    prompt = mod.synthesizer_prompt("formato_uniforme").lower()
    assert "prosa" in prompt and "tabla" not in prompt
    assert "tabla" in mod.synthesizer_prompt(None).lower()
    assert mod.researcher_prompt("formato_uniforme") == mod.researcher_prompt(None)


def test_inventar_explicacion_makes_the_synthesizer_always_explain_even_without_context():
    prompt = mod.synthesizer_prompt("inventar_explicacion").lower()
    assert "siempre" in prompt and "aunque" in prompt and "no la explique" not in prompt
    assert "tabla" in prompt  # lo único que cambia es que explica siempre
    assert mod.coordinator_prompt("inventar_explicacion") == mod.coordinator_prompt(None)


def test_agents_roles_and_tools():
    agents = mod.build_agents(None, "modelo")
    assert set(agents) == {"researcher", "synthesizer"}
    assert agents["researcher"].tools == [QUERY] and agents["synthesizer"].tools == []
    assert all(a.background is False and a.model == "modelo" for a in agents.values())


def test_coordinator_prompt_sets_goals_and_asks_for_the_full_structured_claims():
    prompt = mod.coordinator_prompt(None).lower()
    assert "procedencia" in prompt and "completas" in prompt
    assert "paso 1" not in prompt and "query_source" not in prompt
    # El coordinador decide la reconciliación antes de la síntesis (TS 5.6-S3) y no pasa las afirmaciones «tal como llegaron».
    assert "decide" in prompt and "explicad" in prompt and "disputad" in prompt and "tal como llegaron" not in prompt


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
    mixed_detail = claim()
    mixed_detail["content"]["excerpt"] = "x"
    assert mod.claim_problems(mixed_detail) == ["content mezcla metadatos: excerpt"]


def test_claim_problems_checks_location_excerpt_and_relevance():
    no_location = claim()
    no_location["metadata"]["location"] = None
    assert mod.claim_problems(no_location) == ["metadata sin location"]
    wrong_location = claim()
    wrong_location["metadata"]["location"] = "Sección inventada"
    assert mod.claim_problems(wrong_location) == ["location no es una sección de SRC-TICKETS"]
    no_excerpt = claim()
    no_excerpt["metadata"]["excerpt"] = ""
    assert mod.claim_problems(no_excerpt) == ["metadata sin excerpt"]
    invented = claim()
    invented["metadata"]["excerpt"] = "El tiempo fue de 18 horas según todas las fuentes."
    assert mod.claim_problems(invented) == ["excerpt no es literal de SRC-TICKETS"]
    spaced = claim()
    spaced["metadata"]["excerpt"] = "  ".join(spaced["metadata"]["excerpt"].split(" "))
    assert mod.claim_problems(spaced) == []  # los espacios de más no lo vuelven inventado
    for bad in (None, "alta", 1.5, -0.1, True):
        item = claim()
        item["metadata"]["relevance"] = bad
        assert mod.claim_problems(item) == ["relevance no es un número de 0 a 1"], bad


def test_detail_share_counts_claims_with_valid_location_and_literal_excerpt():
    bad_loc = claim("SRC-AUDITORIA", figure=26)
    bad_loc["metadata"]["location"] = "Otra"
    no_excerpt = claim("SRC-ENCUESTA", "x", 4.1, "sobre 5")
    no_excerpt["metadata"]["excerpt"] = "frase inventada"
    rec = RunRecord(tool_calls=[delegation("d1", "researcher", result=json.dumps([claim(), bad_loc, no_excerpt]))])
    assert mod.detail_share(rec) == {"location": 2, "excerpt": 2, "total": 3}
    assert mod.detail_share(RunRecord()) == {"location": 0, "excerpt": 0, "total": 0}


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


def test_sources_passed_needs_the_source_id_together_with_its_claim_not_anywhere_in_the_prompt():
    found = delegation("d1", "researcher", result=json.dumps([claim(), claim("SRC-AUDITORIA", "Tiempo medio con esperas", 26)]))
    # SRC-AUDITORIA sale solo en una lista de fuentes, lejos de su afirmación: no pasó con ella.
    far = "Fuentes consultadas: SRC-AUDITORIA, SRC-TICKETS.\n" + "relleno " * 200 + "\n" + json.dumps([claim(), {"claim": "Tiempo medio con esperas", "figure": 26}])
    rec = RunRecord(tool_calls=[found, delegation("d2", "synthesizer", prompt=far)])
    assert mod.sources_passed(rec)["passed"] == ["SRC-TICKETS"] and mod.sources_passed(rec)["missing"] == ["SRC-AUDITORIA"]
    together = "Afirmaciones: " + json.dumps([claim(), claim("SRC-AUDITORIA", "Tiempo medio con esperas", 26)])
    rec = RunRecord(tool_calls=[found, delegation("d2", "synthesizer", prompt=together)])
    assert mod.sources_passed(rec)["missing"] == []
    # Con la cifra y el id en la misma línea, aunque el texto de la afirmación se haya reescrito, también cuenta.
    rewritten = "SRC-AUDITORIA (2026-10-09): 26 horas\nSRC-TICKETS: 18 horas"
    rec = RunRecord(tool_calls=[found, delegation("d2", "synthesizer", prompt=rewritten)])
    assert mod.sources_passed(rec)["missing"] == []


# --- decisión de reconciliación del coordinador, en el prompt del sintetizador (TS 5.6-S3) -------------

DECISIONS = (
    "Afirmaciones: ...\n"
    "Reconciliación: tiempo medio de resolución (SRC-TICKETS 18 h, SRC-AUDITORIA 26 h): explicado por el método y la muestra.\n"
    "Satisfacción media (SRC-ENCUESTA, SRC-PROVEEDOR): explicada por el periodo y la población.\n"
    "Tickets reabiertos (SRC-CUADRO 7,3 %, SRC-OFICINA 12,4 %): disputado, el contexto no lo explica.\n"
)


def test_coordinator_decisions_reads_each_conflict_decision_from_the_synthesizer_prompt():
    rec = RunRecord(tool_calls=[delegation("d1", "synthesizer", prompt=DECISIONS)])
    assert mod.coordinator_decisions(rec) == {"tiempo medio de resolución": "explicado", "satisfacción media": "explicado", "tickets reabiertos": "disputado"}
    assert mod.decisions_correct(rec) == {"tiempo medio de resolución": True, "satisfacción media": True, "tickets reabiertos": True}


def test_coordinator_decisions_reports_none_when_the_prompt_passes_claims_without_a_decision():
    raw = "Afirmaciones: " + json.dumps([claim(), claim("SRC-AUDITORIA", "x", 26)])
    rec = RunRecord(tool_calls=[delegation("d1", "synthesizer", prompt=raw)])
    assert set(mod.coordinator_decisions(rec).values()) == {None}
    assert set(mod.decisions_correct(rec).values()) == {False}
    assert set(mod.coordinator_decisions(RunRecord()).values()) == {None}


def test_a_wrong_decision_is_counted_as_incorrect_and_not_explained_beats_explained():
    wrong = "Tickets reabiertos (SRC-CUADRO 7,3 %, SRC-OFICINA 12,4 %): explicado por el periodo.\nTiempo medio de resolución (SRC-TICKETS, SRC-AUDITORIA): no queda explicado."
    rec = RunRecord(tool_calls=[delegation("d1", "synthesizer", prompt=wrong)])
    decisions = mod.coordinator_decisions(rec)
    assert decisions["tickets reabiertos"] == "explicado" and decisions["tiempo medio de resolución"] == "disputado"
    assert mod.decisions_correct(rec)["tickets reabiertos"] is False and mod.decisions_correct(rec)["tiempo medio de resolución"] is False


def test_negated_decisions_are_disputed_not_explained():
    # Caso que fallaba (B4b): «no explicada» y «no está explicada» caían en explicado.
    for phrase in ("no explicada", "no está explicada", "no queda explicada", "no es explicable"):
        text = f"Tiempo medio de resolución (SRC-TICKETS, SRC-AUDITORIA): {phrase}.\nSatisfacción media (SRC-ENCUESTA): explicada por el periodo."
        rec = RunRecord(tool_calls=[delegation("d1", "synthesizer", prompt=text)])
        decisions = mod.coordinator_decisions(rec)
        assert decisions["tiempo medio de resolución"] == "disputado", phrase
        assert decisions["satisfacción media"] == "explicado"


def test_sizes_of_what_the_researcher_returns_and_what_reaches_the_synthesizer():
    rec = RunRecord(tool_calls=[
        delegation("d1", "researcher", prompt="pide", result="a" * 100), delegation("d2", "researcher", result="b" * 50),
        delegation("d3", "synthesizer", prompt="c" * 70), delegation("d4", "synthesizer", prompt="d" * 30),
    ])
    assert mod.researcher_output_size(rec) == 150 and mod.synthesizer_input_size(rec) == 100
    assert mod.researcher_output_size(RunRecord()) == 0 and mod.synthesizer_input_size(RunRecord()) == 0


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


def test_merged_figures_detects_rounded_averages_with_their_unit():
    # Casos que no se detectaban: «≈4 sobre 5» (3,85) y «10 %» (9,85).
    assert ("satisfacción media", "4") in mod.merged_figures("La satisfacción conjunta es ≈4 sobre 5.")
    assert ("tickets reabiertos", "10") in mod.merged_figures("Aproximadamente el 10 % de los tickets se reabrió.")
    assert ("satisfacción media", "4") in mod.merged_figures("Satisfacción: 4/5 en conjunto.")
    # Un entero suelto sin la unidad del par no cuenta: «4 de 6 fuentes» no es una media.
    assert mod.merged_figures("4 de 6 fuentes y 10 tickets.") == []
    assert mod.merged_figures("Satisfacción de 4,1 sobre 5 y de 3,6 sobre 5.") == []


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


def test_conflicts_presented_treats_negation():
    # Caso que fallaba: «No hay discrepancias» contenía la palabra y daba True en los tres pares.
    for denial in ("No hay discrepancias entre las fuentes.", "Las fuentes no difieren.", "Sin conflicto alguno.", "Nada que disputar: no hay ninguna contradicción."):
        text = "Resolución 18 y 26 horas; satisfacción 4,1 y 3,6; reabiertos 7,3 y 12,4. " + denial
        assert not any(mod.conflicts_presented(text).values()), denial
    # Una negación de otra cosa no anula el desacuerdo.
    assert mod.conflicts_presented("No hay duda: 18 horas y 26 horas discrepan.")["tiempo medio de resolución"]


def test_conflicts_presented_negation_only_counts_when_it_is_next_to_the_dispute_word():
    # Caso que fallaba (B4b): «Sin fusionarlas las fuentes difieren» se borraba entera, con el desacuerdo.
    figures = "Resolución: SRC-TICKETS 18 horas y SRC-AUDITORIA 26 horas. "
    assert mod.conflicts_presented(figures + "Sin fusionarlas las fuentes difieren.")["tiempo medio de resolución"]
    assert mod.conflicts_presented(figures + "No las promediamos: difieren.")["tiempo medio de resolución"]
    assert not mod.conflicts_presented(figures + "No hay una discrepancia real.")["tiempo medio de resolución"]
    assert not mod.conflicts_presented(figures + "Las fuentes no son contradictorias.")["tiempo medio de resolución"]


def test_conflicts_presented_is_per_pair_when_the_sentence_names_a_pair():
    # Caso que fallaba (B4b): una sola mención de desacuerdo valía para los tres pares.
    text = (
        "Resolución: SRC-TICKETS 18 horas y SRC-AUDITORIA 26 horas, que difieren por el método.\n"
        "Satisfacción: SRC-ENCUESTA 4,1 y SRC-PROVEEDOR 3,6.\n"
    )
    result = mod.conflicts_presented(text)
    assert result["tiempo medio de resolución"] is True
    assert result["satisfacción media"] is False  # sus cifras están, pero ninguna frase dice que difieren


def test_uses_table_detects_a_markdown_table():
    assert mod.uses_table(GOOD) and not mod.uses_table("Texto sin tabla. 18 | 26") and not mod.uses_table(None)


def test_table_covers_pairs_needs_both_figures_of_each_pair_inside_the_table_rows():
    topics = ["tiempo medio de resolución", "satisfacción media", "tickets reabiertos"]
    table = (
        "| Magnitud | SRC-TICKETS | SRC-AUDITORIA |\n|---|---|---|\n| Tiempo | 18 horas | 26 horas |\n"
        "| Satisfacción | 4,1 sobre 5 | 3,6 sobre 5 |\n"
    )
    assert mod.table_covers_pairs(table) == {topics[0]: True, topics[1]: True, topics[2]: False}
    # Una tabla vacía de cifras, con las cifras fuera en prosa: hay tabla, no cubre los pares.
    hollow = "| Magnitud | Fuente |\n|---|---|\n| Tiempo | SRC-TICKETS |\n\nSon 18 y 26 horas; 4,1 y 3,6; 7,3 % y 12,4 %."
    assert mod.uses_table(hollow) and set(mod.table_covers_pairs(hollow).values()) == {False}
    assert set(mod.table_covers_pairs(None).values()) == {False}
    # Solo una de las dos cifras en la tabla: el par no está cubierto.
    assert mod.table_covers_pairs("| a | 18 horas |\n| b | x |")[topics[0]] is False


def test_detail_in_report_checks_the_section_and_a_fragment_of_the_excerpt_per_source():
    resolution = RESOLUTION["claims"][0]
    text = f"En {resolution['source_id']} ({resolution['location']}): «{resolution['excerpt']}»."
    detail = mod.detail_in_report(text)
    assert detail == {resolution["source_id"]: {"location": True, "excerpt": True}}
    only_figure = f"{resolution['source_id']} da 18 horas."
    assert mod.detail_in_report(only_figure) == {resolution["source_id"]: {"location": False, "excerpt": False}}
    # El fragmento sin la cifra no cuenta como respaldo de esa cifra.
    assert mod.detail_in_report("La auditoría de calidad da 26 horas para la resolución.")["SRC-AUDITORIA"]["excerpt"] is False
    assert mod.detail_in_report(None) == {}


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


def test_explanation_found_does_not_take_verbs_or_sameness_for_context():
    # Casos que fallaban: «la tabla muestra» casaba con la muestra y «espera confirmar» con las esperas.
    verbs = "Los tickets reabiertos (7,3 % y 12,4 %): la tabla muestra la diferencia y se espera confirmar la causa."
    assert mod.explanation_found(verbs)["tickets reabiertos"] == []
    assert mod.explanation_found("Reabiertos 7,3 % y 12,4 %: lo que muestra la tabla es que las cifras no coinciden; se espera confirmar.")["tickets reabiertos"] == []
    # El par de control comparte periodo, método y población: decirlo no es atribuirle esa explicación.
    same = "Tickets reabiertos 7,3 % y 12,4 %: mismo periodo, el mismo método y la misma población, y aun así no coinciden."
    assert mod.unexplained_status(same)["tickets reabiertos"]["attributed"] is False
    # Las explicaciones de verdad siguen apareciendo.
    assert mod.explanation_found("Resolución 18 y 26 horas: la auditoría cuenta las esperas y usa una muestra de 300 tickets.")["tiempo medio de resolución"] == ["metodo", "muestra"]
    assert mod.explanation_found("Resolución 18 y 26: la muestra es menor y hay esperas de respuesta.")["tiempo medio de resolución"] == ["metodo", "muestra"]


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
