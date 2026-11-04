"""Tests de app3/04_errores_entre_agentes: forma del contexto de error, cobertura anotada, vacío frente a fallo, reintentos locales y opciones del coordinador. Sin modelo."""

import json

from harness.data import load
from harness.offline import run_hook
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/04_errores_entre_agentes.py")

P = "mcp__investigacion__"
QUERY = P + "query_source"
LABELS = load("fuentes_investigacion_etiquetas.json")
FAILED = LABELS["failed_sources"][0]
EMPTY = LABELS["empty_sources"][0]
TRANSIENT = LABELS["transient_sources"][0]["source_id"]
TIMEOUT_TEXT = json.dumps({"errorCategory": "transient", "isRetryable": True, "message": "timeout al consultar la fuente", "source_id": FAILED})
EMPTY_TEXT = json.dumps({"source_id": EMPTY, "total": 0, "results": []})
OK_TEXT = json.dumps({"source_id": "SRC-TICKETS", "total": 1, "results": [{"content": "x", "metadata": {}}]})

GOOD_CONTEXT = {
    "failure_type": "transient",
    "attempted": ["query_source SRC-MONITOR (timeout)", "query_source SRC-MONITOR (timeout)"],
    "partial_results": [],
    "alternatives": ["repetir más tarde", "pedir el dato al equipo de red"],
}


def call(cid, name, agent="researcher", input_=None, *, error=False, text="{}"):
    return ToolCall(cid, name, input_ or {}, "r1", agent, True, error, text)


def query(cid, source_id, text, *, error=False):
    return call(cid, QUERY, input_={"source_id": source_id}, error=error, text=text)


def delegation(cid, text):
    # El resultado de la tool Agent es el texto final del subagente.
    return call(cid, "Agent", "principal", {"subagent_type": "researcher", "prompt": "x"}, text=text)


# --- tools por rol y variantes --------------------------------------------------------------

def test_variants():
    assert mod.ANTI_VARIANTS == ["generico", "silenciar", "abortar"]


def test_researcher_only_queries_sources():
    agents = mod.build_agents(None, "modelo")
    assert set(agents) == {"researcher"}
    assert agents["researcher"].tools == [QUERY]
    assert agents["researcher"].background is False and agents["researcher"].model == "modelo"


def test_request_lists_the_failing_the_empty_and_the_healthy_sources():
    for source_id in (FAILED, EMPTY, TRANSIENT, "SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA"):
        assert source_id in mod.REQUEST
    # La petición no revela cuál falla ni cuál está vacía.
    assert "timeout" not in mod.REQUEST.lower() and "vacía" not in mod.REQUEST.lower()


def test_correct_researcher_prompt_asks_for_local_retry_and_structured_error_context():
    prompt = mod.researcher_prompt(None)
    assert str(mod.MAX_LOCAL_RETRIES) in prompt
    for key in ("failure_type", "attempted", "partial_results", "alternatives"):
        assert key in prompt
    assert "vacío" in prompt  # distingue vacío legítimo de fallo


def test_silenciar_is_done_by_the_code_not_by_the_prompt():
    # La variante ya no le pide al subagente que oculte nada: el handler devuelve [] como éxito.
    assert mod.researcher_prompt("silenciar") == mod.researcher_prompt(None)
    assert mod.coordinator_prompt("silenciar") == mod.coordinator_prompt(None)
    assert mod.silences_failures("silenciar") is True
    assert mod.silences_failures(None) is False and mod.silences_failures("generico") is False and mod.silences_failures("abortar") is False


def test_generico_makes_the_researcher_return_a_bare_failed_status_without_context():
    prompt = mod.researcher_prompt("generico")
    assert mod.GENERIC_MESSAGE in prompt and "failed" in prompt
    # Reintenta igual que la correcta: lo único que cambia es lo que devuelve al final.
    assert str(mod.MAX_LOCAL_RETRIES) in prompt and "no reintentes" not in prompt.lower()
    for key in ("error_context", "failure_type", "attempted", "partial_results", "alternatives"):
        assert key not in prompt
    assert prompt != mod.researcher_prompt(None)
    # El coordinador es el mismo: lo que cambia es la información que le llega.
    assert mod.coordinator_prompt("generico") == mod.coordinator_prompt(None)


def test_abortar_changes_the_coordinator_not_the_researcher():
    assert mod.researcher_prompt("abortar") == mod.researcher_prompt(None)
    assert mod.ABORT_MARKER in mod.coordinator_prompt("abortar")
    assert mod.ABORT_MARKER not in mod.coordinator_prompt(None)


def test_correct_coordinator_prompt_sets_goals_not_steps_and_names_no_tools():
    prompt = mod.coordinator_prompt(None).lower()
    assert "cobertura" in prompt and "parcial" in prompt
    assert "paso 1" not in prompt
    for word in ("query_source", "list_sources", "reintent"):
        assert word not in prompt  # el reintento y las tools son del subagente


# --- clasificación de resultados: vacío frente a fallo ---------------------------------------

def test_classify_result_tells_failure_from_empty_from_data():
    assert mod.classify_result(query("c1", FAILED, TIMEOUT_TEXT, error=True)) == "failure"
    assert mod.classify_result(query("c2", EMPTY, EMPTY_TEXT)) == "empty"
    assert mod.classify_result(query("c3", "SRC-TICKETS", OK_TEXT)) == "data"
    # Un error de validación (fuente desconocida) no es un fallo de acceso reintentable.
    invalid = json.dumps({"errorCategory": "validation", "isRetryable": False, "message": "fuente desconocida"})
    assert mod.classify_result(query("c4", "SRC-X", invalid, error=True)) == "invalid"


def test_attempts_and_local_retries_by_source():
    rec = RunRecord(tool_calls=[
        query("c1", FAILED, TIMEOUT_TEXT, error=True), query("c2", FAILED, TIMEOUT_TEXT, error=True), query("c3", FAILED, TIMEOUT_TEXT, error=True),
        query("c4", "SRC-TICKETS", OK_TEXT),
        call("c5", "Agent", "principal", {"subagent_type": "researcher"}),
    ])
    assert {k: len(v) for k, v in mod.attempts_by_source(rec).items()} == {FAILED: 3, "SRC-TICKETS": 1}
    assert mod.local_retries(rec) == {FAILED: 2, "SRC-TICKETS": 0}
    assert mod.local_retries(RunRecord()) == {}


def test_a_retry_is_not_counted_as_a_failure_of_the_run():
    # Sonda B: el reintento local es una llamada más del subagente, no un fallo del coordinador.
    rec = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), query("c2", FAILED, TIMEOUT_TEXT, error=True)])
    assert mod.failed_sources(rec) == [FAILED]
    assert mod.coordinator_errors(rec) == 0


def test_failed_and_empty_sources_come_from_the_tool_results():
    rec = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), query("c2", EMPTY, EMPTY_TEXT), query("c3", "SRC-TICKETS", OK_TEXT)])
    assert mod.failed_sources(rec) == [FAILED] and mod.empty_sources(rec) == [EMPTY]


def test_a_source_recovered_on_retry_is_not_failed():
    rec = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), query("c2", FAILED, OK_TEXT)])
    assert mod.failed_sources(rec) == []


# --- fuente transitoria: recuperación local (5.3-S3) --------------------------------------------

REDES_FAIL = json.dumps({"errorCategory": "transient", "isRetryable": True, "message": "timeout al consultar la fuente", "source_id": TRANSIENT})


def test_recovered_sources_failed_first_and_ended_with_data():
    rec = RunRecord(tool_calls=[query("c1", TRANSIENT, REDES_FAIL, error=True), query("c2", TRANSIENT, OK_TEXT)])
    assert mod.recovered_sources(rec) == [TRANSIENT]
    assert mod.failed_sources(rec) == []  # no termina en fallo
    still = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), query("c2", FAILED, TIMEOUT_TEXT, error=True)])
    assert mod.recovered_sources(still) == []
    assert mod.recovered_sources(RunRecord(tool_calls=[query("c1", "SRC-TICKETS", OK_TEXT)])) == []  # sin fallo no hay recuperación


def test_a_recovery_is_invisible_to_the_coordinator_when_the_report_is_ok_and_no_gap_is_noted():
    rec = RunRecord(
        tool_calls=[query("c1", TRANSIENT, REDES_FAIL, error=True), query("c2", TRANSIENT, OK_TEXT),
                    delegation("d1", json.dumps({"source_id": TRANSIENT, "status": "ok", "findings": []}))],
        final_text="La red tuvo una disponibilidad del 99,2 %.",
    )
    assert mod.recovery_hidden_from_coordinator(rec) == [TRANSIENT]
    leaked = RunRecord(
        tool_calls=rec.tool_calls[:2] + [delegation("d1", json.dumps({"source_id": TRANSIENT, "status": "failed", "findings": []}))],
        final_text="La red tuvo una disponibilidad del 99,2 %.",
    )
    assert mod.recovery_hidden_from_coordinator(leaked) == []  # el coordinador la vio como fallo


def test_requested_sources_include_the_transient_one_and_the_module_builds_the_server_with_it():
    assert TRANSIENT in mod.REQUESTED and mod.SERVER_FLAGS == {"sources": True, "transient": True}

# --- informes de los subagentes: forma del contexto de error ---------------------------------

def failed_report(**changes):
    report = {"source_id": FAILED, "status": "failed", "findings": [], "error_context": dict(GOOD_CONTEXT)}
    report.update(changes)
    return report


def test_error_context_problems_accepts_the_full_shape():
    assert mod.error_context_problems(failed_report()) == []


def test_error_context_problems_names_each_missing_piece():
    for key in ("failure_type", "attempted", "partial_results", "alternatives"):
        context = {k: v for k, v in GOOD_CONTEXT.items() if k != key}
        assert mod.error_context_problems(failed_report(error_context=context)) == [f"falta {key}"]
    assert mod.error_context_problems(failed_report(error_context=dict(GOOD_CONTEXT, attempted=[]))) == ["attempted vacío: no dice qué se intentó"]
    assert mod.error_context_problems(failed_report(error_context=None)) == ["falta error_context"]
    assert mod.error_context_problems({"source_id": FAILED, "status": "ok", "findings": []}) == ["status no es failed"]


def test_parse_reports_reads_json_objects_from_the_agent_results_ignoring_prose():
    text = "Resultados:\n" + json.dumps(failed_report()) + "\nY además " + json.dumps({"source_id": "SRC-TICKETS", "status": "ok", "findings": [{"claim": "x"}]})
    rec = RunRecord(tool_calls=[delegation("d1", text), query("c1", FAILED, TIMEOUT_TEXT, error=True)])
    reports = mod.subagent_reports(rec)
    assert [r["source_id"] for r in reports] == [FAILED, "SRC-TICKETS"]
    assert mod.subagent_reports(RunRecord(tool_calls=[delegation("d1", "sin json {roto")])) == []
    # Un objeto JSON sin source_id (no es un informe) se ignora.
    assert mod.subagent_reports(RunRecord(tool_calls=[delegation("d1", '{"otra": 1}')])) == []


def test_parse_reports_accepts_a_json_list():
    text = json.dumps([failed_report(), {"source_id": EMPTY, "status": "empty", "findings": []}])
    reports = mod.subagent_reports(RunRecord(tool_calls=[delegation("d1", text)]))
    assert [r["source_id"] for r in reports] == [FAILED, EMPTY]


def test_unreported_failures_are_those_that_failed_but_were_reported_without_failure():
    rec = RunRecord(tool_calls=[
        query("c1", FAILED, TIMEOUT_TEXT, error=True),
        delegation("d1", json.dumps({"source_id": FAILED, "status": "ok", "findings": []})),
    ])
    assert mod.unreported_failures(rec) == [FAILED]
    honest = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), delegation("d1", json.dumps(failed_report()))])
    assert mod.unreported_failures(honest) == []
    # Si el subagente no devuelve ningún informe de esa fuente, tampoco se ha dicho que falló.
    assert mod.unreported_failures(RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True)])) == [FAILED]


def test_empty_source_reported_as_failed_is_a_confusion():
    rec = RunRecord(tool_calls=[
        query("c1", EMPTY, EMPTY_TEXT),
        delegation("d1", json.dumps({"source_id": EMPTY, "status": "failed", "findings": [], "error_context": GOOD_CONTEXT})),
    ])
    assert mod.empty_reported_as_failed(rec) == [EMPTY]
    right = RunRecord(tool_calls=[query("c1", EMPTY, EMPTY_TEXT), delegation("d1", json.dumps({"source_id": EMPTY, "status": "empty", "findings": []}))])
    assert mod.empty_reported_as_failed(right) == []


def test_generic_failed_report_lacks_the_error_context():
    generic = {"source_id": FAILED, "status": "failed", "message": mod.GENERIC_MESSAGE, "findings": []}
    assert mod.error_context_problems(generic) == ["falta error_context"]


def test_swallowed_sources_are_labelled_failures_whose_result_did_not_look_like_a_failure():
    # Con el handler que devuelve [] como éxito, la fuente que falla llega como un vacío legítimo.
    swallowed = RunRecord(tool_calls=[query("c1", FAILED, json.dumps({"source_id": FAILED, "total": 0, "results": []}))])
    assert mod.swallowed_sources(swallowed) == [FAILED]
    honest = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True)])
    assert mod.swallowed_sources(honest) == []
    assert mod.swallowed_sources(RunRecord()) == []  # no consultada: no hay nada que tragar
    assert mod.swallowed_sources(RunRecord(tool_calls=[query("c1", EMPTY, EMPTY_TEXT)])) == []  # el vacío legítimo no es un fallo


def test_legit_empty_sources_exclude_the_swallowed_failure():
    # En `silenciar` la fuente que falla llega como vacío: no es un vacío legítimo.
    rec = RunRecord(tool_calls=[query("c1", FAILED, json.dumps({"source_id": FAILED, "total": 0, "results": []})), query("c2", EMPTY, EMPTY_TEXT)])
    assert mod.empty_sources(rec) == [FAILED, EMPTY]
    assert mod.legit_empty_sources(rec) == [EMPTY]


def test_coordinator_delegations_count_only_the_main_agent_calls_to_the_subagent():
    rec = RunRecord(tool_calls=[delegation("d1", "x"), delegation("d2", "y"), query("c1", FAILED, TIMEOUT_TEXT, error=True)])
    assert mod.coordinator_delegations(rec) == 2
    assert mod.coordinator_delegations(RunRecord()) == 0


def test_alternatives_mentioned_looks_for_a_way_to_cover_the_gap():
    assert mod.alternatives_mentioned("Alternativa: pedir el dato al equipo de red.")
    assert mod.alternatives_mentioned("Se puede reintentar más tarde.")
    assert not mod.alternatives_mentioned("La fuente falló.") and not mod.alternatives_mentioned(None)


# --- el resultado final: cobertura anotada ---------------------------------------------------

NAME = next(s["name"] for s in load("fuentes_investigacion.json") if s["source_id"] == FAILED)


def test_gap_noted_needs_the_source_and_a_word_that_says_it_is_missing():
    assert mod.gap_noted(f"No se pudo consultar {FAILED}: timeout. Falta su cobertura.", FAILED, NAME)
    assert mod.gap_noted(f"La {NAME.lower()} no respondió; queda sin cubrir.", FAILED, NAME)
    assert not mod.gap_noted(f"{FAILED} indica que la red va bien.", FAILED, NAME)  # la cita sin decir que falló
    assert not mod.gap_noted("Hubo un timeout en alguna fuente.", FAILED, NAME)  # el fallo sin decir cuál
    assert not mod.gap_noted(None, FAILED, NAME)


def test_gap_noted_treats_negation():
    # Caso que fallaba: «no falló» contenía la palabra de fallo y daba True.
    assert not mod.gap_noted(f"{FAILED} no falló: respondió sin datos.", FAILED, NAME)
    assert not mod.gap_noted(f"No hubo timeout en {FAILED}.", FAILED, NAME)
    assert not mod.gap_noted(f"{FAILED}: sin brecha ni fallos.", FAILED, NAME)
    assert mod.gap_noted(f"{FAILED} no respondió.", FAILED, NAME)  # «no respondió» es la brecha, no su negación
    assert mod.gap_noted(f"{FAILED} no falló la primera vez, pero luego falló y queda sin cubrir.", FAILED, NAME)


def test_partial_delivered_means_figures_of_the_healthy_sources_and_no_abort_marker():
    figure = LABELS["established"]["figure_text"]
    assert mod.partial_delivered(f"Se cerraron {figure} tickets.")
    assert not mod.partial_delivered(mod.ABORT_MARKER)
    assert not mod.partial_delivered(f"{mod.ABORT_MARKER} {figure}")
    assert not mod.partial_delivered("Nada que contar.") and not mod.partial_delivered(None)


def test_partial_delivered_ignores_dates_and_figures_of_sources_not_requested():
    # Caso que fallaba: la fecha 2026-10-18 casaba con la cifra «18».
    assert not mod.partial_delivered("Informe de la fuente con fecha 2026-10-18 y sin cifras.")
    assert not mod.partial_delivered("Corte a 18/10/2026.")
    # Una cifra de una fuente que 04 no pide (SRC-CUADRO, 7,3 %) no cuenta como entrega.
    assert not mod.partial_delivered("Los tickets reabiertos fueron el 7,3 %.")
    assert mod.partial_delivered("El tiempo medio fue de 18 horas (2026-10-02).")
    assert mod.partial_delivered("La satisfacción fue de 4,1 sobre 5.")


def test_partial_delivered_counts_the_transient_source_figure_once_recovered():
    assert mod.partial_delivered("La disponibilidad de la red fue del 99,2 %.")


def test_an_abort_without_the_exact_marker_is_not_a_delivery():
    assert not mod.partial_delivered("La investigación queda abortada porque una fuente falló. Había 1.240 tickets.")
    assert mod.aborted("Investigación abortada.")


def test_aborted_detects_the_marker():
    assert mod.aborted(f"  {mod.ABORT_MARKER}  ") and not mod.aborted("Informe parcial") and not mod.aborted(None)


def test_coverage_summary_lists_covered_empty_and_gap_sources():
    reports = [
        {"source_id": "SRC-TICKETS", "status": "ok", "findings": [{"claim": "x"}]},
        {"source_id": EMPTY, "status": "empty", "findings": []},
        failed_report(),
    ]
    assert mod.coverage_of(reports) == {"covered": ["SRC-TICKETS"], "empty": [EMPTY], "gap": [FAILED]}


# --- opciones --------------------------------------------------------------------------------

def test_gate_denies_the_coordinator_and_is_registered_for_the_server():
    options = mod.build_options(None, budget=0.5, model="m", subagent_model="s")
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.matcher == "mcp__investigacion__.*" and matcher.hooks == [mod.coordinator_gate]
    assert run_hook(mod.coordinator_gate, "PreToolUse", QUERY, {"source_id": "x"}).decision == "deny"
    assert run_hook(mod.coordinator_gate, "PreToolUse", QUERY, {"source_id": "x"}, agent_id="a1").decision is None


def test_options_follow_the_subagent_pattern_with_the_sources_server():
    options = mod.build_options(None, budget=0.5, model="m", subagent_model="s")
    assert options.tools == ["Agent"] and options.permission_mode == "dontAsk"
    assert options.setting_sources == [] and options.max_budget_usd == 0.5
    assert "investigacion" in options.mcp_servers and QUERY in options.allowed_tools and "Agent" in options.allowed_tools
    assert options.env["CLAUDE_CODE_FORK_SUBAGENT"] == "0"
    assert options.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert set(options.agents) == {"researcher"}
