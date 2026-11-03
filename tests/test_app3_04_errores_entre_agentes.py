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
    assert mod.ANTI_VARIANTS == ["silenciar", "abortar"]


def test_researcher_only_queries_sources():
    agents = mod.build_agents(None, "modelo")
    assert set(agents) == {"researcher"}
    assert agents["researcher"].tools == [QUERY]
    assert agents["researcher"].background is False and agents["researcher"].model == "modelo"


def test_request_lists_the_failing_the_empty_and_the_healthy_sources():
    for source_id in (FAILED, EMPTY, "SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA"):
        assert source_id in mod.REQUEST
    # La petición no revela cuál falla ni cuál está vacía.
    assert "timeout" not in mod.REQUEST.lower() and "vacía" not in mod.REQUEST.lower()


def test_correct_researcher_prompt_asks_for_local_retry_and_structured_error_context():
    prompt = mod.researcher_prompt(None)
    assert str(mod.MAX_LOCAL_RETRIES) in prompt
    for key in ("failure_type", "attempted", "partial_results", "alternatives"):
        assert key in prompt
    assert "vacío" in prompt  # distingue vacío legítimo de fallo


def test_silenciar_tells_the_researcher_to_hide_the_failure_as_an_empty_result():
    prompt = mod.researcher_prompt("silenciar")
    assert "error_context" not in prompt and "failed" not in prompt
    assert mod.researcher_prompt(None) != prompt


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


def test_silenced_sources_are_those_that_failed_but_were_reported_without_failure():
    rec = RunRecord(tool_calls=[
        query("c1", FAILED, TIMEOUT_TEXT, error=True),
        delegation("d1", json.dumps({"source_id": FAILED, "status": "ok", "findings": []})),
    ])
    assert mod.silenced_sources(rec) == [FAILED]
    honest = RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True), delegation("d1", json.dumps(failed_report()))])
    assert mod.silenced_sources(honest) == []
    # Si el subagente no devuelve ningún informe de esa fuente, tampoco se ha dicho que falló.
    assert mod.silenced_sources(RunRecord(tool_calls=[query("c1", FAILED, TIMEOUT_TEXT, error=True)])) == [FAILED]


def test_empty_source_reported_as_failed_is_a_confusion():
    rec = RunRecord(tool_calls=[
        query("c1", EMPTY, EMPTY_TEXT),
        delegation("d1", json.dumps({"source_id": EMPTY, "status": "failed", "findings": [], "error_context": GOOD_CONTEXT})),
    ])
    assert mod.empty_reported_as_failed(rec) == [EMPTY]
    right = RunRecord(tool_calls=[query("c1", EMPTY, EMPTY_TEXT), delegation("d1", json.dumps({"source_id": EMPTY, "status": "empty", "findings": []}))])
    assert mod.empty_reported_as_failed(right) == []


# --- el resultado final: cobertura anotada ---------------------------------------------------

NAME = next(s["name"] for s in load("fuentes_investigacion.json") if s["source_id"] == FAILED)


def test_gap_noted_needs_the_source_and_a_word_that_says_it_is_missing():
    assert mod.gap_noted(f"No se pudo consultar {FAILED}: timeout. Falta su cobertura.", FAILED, NAME)
    assert mod.gap_noted(f"La {NAME.lower()} no respondió; queda sin cubrir.", FAILED, NAME)
    assert not mod.gap_noted(f"{FAILED} indica que la red va bien.", FAILED, NAME)  # la cita sin decir que falló
    assert not mod.gap_noted("Hubo un timeout en alguna fuente.", FAILED, NAME)  # el fallo sin decir cuál
    assert not mod.gap_noted(None, FAILED, NAME)


def test_partial_delivered_means_figures_of_the_healthy_sources_and_no_abort_marker():
    figure = LABELS["established"]["figure_text"]
    assert mod.partial_delivered(f"Se cerraron {figure} tickets.")
    assert not mod.partial_delivered(mod.ABORT_MARKER)
    assert not mod.partial_delivered(f"{mod.ABORT_MARKER} {figure}")
    assert not mod.partial_delivered("Nada que contar.") and not mod.partial_delivered(None)


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
