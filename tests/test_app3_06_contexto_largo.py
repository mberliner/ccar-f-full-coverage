"""Tests de app3/06_contexto_largo: scratchpad, manifest de estado, resumen entre fases, retomar tras una caída, medidas y opciones. Sin modelo."""

import json

from harness.data import load
from harness.offline import call_tool, run_hook
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/06_contexto_largo.py")

P = "mcp__investigacion__"
S = "mcp__scratchpad__"
QUERY, SAVE, READ = P + "query_source", S + "save_finding", S + "read_scratchpad"
LABELS = load("fuentes_investigacion_etiquetas.json")
SOURCE_IDS = {s["source_id"] for s in load("fuentes_investigacion.json")}


def call(cid, name, agent="principal", *, text="{}", input_=None):
    return ToolCall(cid, name, input_ or {}, "r1", agent, True, False, text)


# --- fases y variantes ------------------------------------------------------------------------

def test_variants_and_phases():
    assert mod.ANTI_VARIANTS == ["todo_en_contexto"]
    assert [p["id"] for p in mod.PHASES] == [1, 2, 3]
    for phase in mod.PHASES[:2]:
        assert phase["sources"] and set(phase["sources"]) <= SOURCE_IDS
    # La última fase sintetiza lo descubierto: no consulta fuentes.
    assert mod.PHASES[2]["sources"] == []
    # El informe largo (el que más llena el contexto) está en una fase intermedia.
    assert LABELS["long_report"]["source_id"] in mod.PHASES[1]["sources"]


def test_the_requests_do_not_reveal_the_figures():
    for phase in mod.PHASES:
        for fact in mod.EXPECTED_FACTS:
            assert fact["text"] not in phase["task"]


# --- scratchpad -------------------------------------------------------------------------------

def tools_for(directory):
    return {t.name: t for t in mod.make_scratchpad_tools(directory)}


def test_scratchpad_saves_findings_and_reads_them_back_in_order(tmp_path):
    tools = tools_for(tmp_path)
    assert set(tools) == {"save_finding", "read_scratchpad"}
    first = call_tool(tools["save_finding"], {"source_id": "SRC-TICKETS", "claim": "18 horas de media", "figure": 18})
    assert not first.is_error and json.loads(first.text)["saved"] == 1
    second = call_tool(tools["save_finding"], {"source_id": "SRC-AUDITORIA", "claim": "26 horas de media"})
    assert json.loads(second.text)["saved"] == 2
    entries = json.loads(call_tool(tools["read_scratchpad"], {}).text)["findings"]
    assert [e["source_id"] for e in entries] == ["SRC-TICKETS", "SRC-AUDITORIA"]
    assert entries[0]["figure"] == 18 and "figure" not in entries[1]
    # Vive en un archivo conocido: otro proceso (otra ejecución) lo lee sin pasar por el contexto.
    assert mod.read_scratchpad(tmp_path) == entries


def test_scratchpad_is_empty_before_anything_is_saved_and_rejects_a_blank_finding(tmp_path):
    tools = tools_for(tmp_path)
    assert json.loads(call_tool(tools["read_scratchpad"], {}).text) == {"findings": []}
    bad = call_tool(tools["save_finding"], {"source_id": "SRC-TICKETS", "claim": "  "})
    assert bad.is_error and json.loads(bad.text)["errorCategory"] == "validation"
    assert mod.read_scratchpad(tmp_path) == []


def test_each_directory_has_its_own_scratchpad(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    call_tool(tools_for(a)["save_finding"], {"source_id": "SRC-TICKETS", "claim": "x"})
    assert len(mod.read_scratchpad(a)) == 1 and mod.read_scratchpad(b) == []


# --- manifest ---------------------------------------------------------------------------------

def test_new_manifest_has_no_phase_done():
    manifest = mod.new_manifest()
    assert manifest["phases_done"] == [] and manifest["summaries"] == {} and manifest["total_phases"] == 3
    assert mod.next_phase(manifest) == 1 and not mod.is_complete(manifest)


def test_complete_phase_returns_a_new_manifest_with_the_summary_and_the_sources():
    before = mod.new_manifest()
    after = mod.complete_phase(before, 1, "Resumen de la fase 1", ["SRC-TICKETS", "SRC-AUDITORIA"], findings=4)
    assert before["phases_done"] == []  # no muta el original
    assert after["phases_done"] == [1] and after["summaries"] == {"1": "Resumen de la fase 1"}
    assert after["sources_covered"] == ["SRC-AUDITORIA", "SRC-TICKETS"] and after["findings"] == 4
    later = mod.complete_phase(after, 2, "Resumen 2", ["SRC-LARGO", "SRC-TICKETS"], findings=5)
    assert later["phases_done"] == [1, 2] and later["sources_covered"] == ["SRC-AUDITORIA", "SRC-LARGO", "SRC-TICKETS"]
    assert mod.next_phase(later) == 3
    assert mod.is_complete(mod.complete_phase(later, 3, "Fin", [], findings=5)) and mod.next_phase(mod.complete_phase(later, 3, "Fin", [], findings=5)) is None


def test_manifest_survives_a_restart(tmp_path):
    # La caída simulada: lo que escribe un proceso lo retoma otro leyendo el archivo.
    assert mod.read_manifest(tmp_path) is None
    done = mod.complete_phase(mod.new_manifest(), 1, "Resumen 1", ["SRC-TICKETS"], findings=2)
    mod.write_manifest(tmp_path, done)
    restored = mod.read_manifest(tmp_path)
    assert restored == done and mod.next_phase(restored) == 2


def test_a_corrupt_manifest_is_not_trusted(tmp_path):
    (tmp_path / mod.MANIFEST_FILE).write_text("{roto", encoding="utf-8")
    assert mod.read_manifest(tmp_path) is None


# --- resumen entre fases y prompt de cada fase -------------------------------------------------

def test_summarize_cuts_long_text_and_handles_none():
    assert mod.summarize(None) == "" and mod.summarize("  corto  ") == "corto"
    long = "palabra " * 500
    assert len(mod.summarize(long)) <= mod.MAX_SUMMARY_CHARS and mod.summarize(long).endswith("…")


def test_first_phase_prompt_has_the_task_and_no_previous_context():
    prompt = mod.phase_prompt(mod.PHASES[0], None)
    assert mod.PHASES[0]["task"] in prompt
    assert "Resumen de la fase" not in prompt and "manifest" not in prompt.lower()


def test_later_phase_prompt_injects_the_previous_summary_and_the_manifest_state():
    manifest = mod.complete_phase(mod.new_manifest(), 1, "El 18 horas lo da SRC-TICKETS.", ["SRC-TICKETS", "SRC-AUDITORIA"], findings=4)
    prompt = mod.phase_prompt(mod.PHASES[1], manifest)
    assert mod.PHASES[1]["task"] in prompt
    # Resumen de la fase anterior en el contexto inicial (TS 5.4-S3) y estado del manifest (TS 5.4-K4, S4).
    assert "Resumen de la fase 1" in prompt and "El 18 horas lo da SRC-TICKETS." in prompt
    assert "SRC-TICKETS" in prompt and "SRC-AUDITORIA" in prompt and "4 hallazgos" in prompt
    assert "read_scratchpad" in prompt


def test_phase_prompt_lists_every_previous_summary_in_order():
    manifest = mod.complete_phase(mod.complete_phase(mod.new_manifest(), 1, "UNO", [], findings=1), 2, "DOS", [], findings=2)
    prompt = mod.phase_prompt(mod.PHASES[2], manifest)
    assert prompt.index("UNO") < prompt.index("DOS")


def test_all_in_one_prompt_has_every_task_and_no_summaries_or_scratchpad():
    prompt = mod.all_phases_prompt()
    for phase in mod.PHASES:
        assert phase["task"] in prompt
    assert "scratchpad" not in prompt.lower() and "manifest" not in prompt.lower() and "Resumen de la fase" not in prompt


# --- agentes y opciones ------------------------------------------------------------------------

def test_researcher_queries_and_saves_while_the_coordinator_only_reads():
    agents = mod.build_agents("modelo")
    assert set(agents) == {"researcher"} and agents["researcher"].tools == [QUERY, SAVE]
    assert agents["researcher"].background is False and agents["researcher"].model == "modelo"


def test_correct_options_use_subagents_scratchpad_and_the_gate(tmp_path):
    options = mod.build_options(None, scratch_dir=tmp_path, budget=0.3, model="m", subagent_model="s")
    assert options.tools == ["Agent"] and options.permission_mode == "dontAsk"
    assert set(options.allowed_tools) == {"Agent", QUERY, SAVE, READ}
    assert set(options.mcp_servers) == {"investigacion", "scratchpad"} and set(options.agents) == {"researcher"}
    assert options.setting_sources == [] and options.max_budget_usd == 0.3
    assert options.env["CLAUDE_CODE_FORK_SUBAGENT"] == "0" and options.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.matcher == "mcp__investigacion__.*" and matcher.hooks == [mod.coordinator_gate]
    assert run_hook(mod.coordinator_gate, "PreToolUse", QUERY, {"source_id": "x"}).decision == "deny"


def test_todo_en_contexto_has_one_thread_without_subagents_or_scratchpad(tmp_path):
    options = mod.build_options("todo_en_contexto", scratch_dir=tmp_path, budget=0.3, model="m", subagent_model="s")
    assert options.tools == [] and options.allowed_tools == [QUERY]
    assert set(options.mcp_servers) == {"investigacion"} and not options.agents and not options.hooks
    assert "scratchpad" not in mod.coordinator_prompt("todo_en_contexto").lower()


def test_coordinator_prompt_sets_goals_and_asks_for_a_closing_summary():
    prompt = mod.coordinator_prompt(None).lower()
    assert "resumen" in prompt and "read_scratchpad" in prompt and "researcher" in prompt
    assert "paso 1" not in prompt


# --- medidas ------------------------------------------------------------------------------------

def test_main_context_chars_counts_only_what_reaches_the_coordinator():
    rec = RunRecord(tool_calls=[
        call("c1", QUERY, "principal", text="x" * 100),  # `todo_en_contexto`: llega entero al hilo
        call("c2", "Agent", "principal", text="y" * 30),  # con subagente solo llega su resumen
        call("c3", QUERY, "researcher", text="z" * 9000),  # dentro del subagente: no cuenta
    ])
    assert mod.main_context_chars(rec) == 130 and mod.main_context_chars(RunRecord()) == 0


def test_requeried_sources_counts_queries_to_sources_already_covered():
    rec = RunRecord(tool_calls=[
        call("c1", QUERY, "researcher", input_={"source_id": "SRC-TICKETS"}),
        call("c2", QUERY, "researcher", input_={"source_id": "SRC-LARGO"}),
        call("c3", QUERY, "researcher", input_={"source_id": "SRC-TICKETS"}),
    ])
    assert mod.requeried_sources(rec, ["SRC-TICKETS", "SRC-AUDITORIA"]) == ["SRC-TICKETS", "SRC-TICKETS"]
    assert mod.requeried_sources(rec, []) == [] and mod.requeried_sources(RunRecord(), ["SRC-TICKETS"]) == []


def test_scratchpad_reads_counts_calls_to_read_scratchpad():
    rec = RunRecord(tool_calls=[call("c1", READ), call("c2", READ, "researcher"), call("c3", SAVE, "researcher")])
    assert mod.scratchpad_reads(rec) == 2


FULL = "Resolución: 18 horas (SRC-TICKETS) y 26 horas (SRC-AUDITORIA). Satisfacción: 4,1 sobre 5 y 3,6 sobre 5. El 41 % de las incidencias de red fue un perfil de VPN."


def test_facts_found_scores_the_final_text_against_what_was_discovered():
    found, total, missing = mod.facts_found(FULL)
    assert (found, total, missing) == (5, 5, [])
    found, total, missing = mod.facts_found("Resolución: 18 horas. Satisfacción 4,1 sobre 5. Hubo incidencias.")
    assert (found, total) == (2, 5) and missing == ["26", "3,6", "41 %"]
    assert mod.facts_found(None) == (0, 5, ["18", "26", "4,1", "3,6", "41 %"])


def test_facts_are_not_found_inside_other_numbers():
    assert mod.facts_found("2018 tickets, 126 horas y 14,15 de media")[0] == 0


def test_facts_found_accepts_a_score_written_as_a_fraction_but_not_a_date():
    # «4,1/5» es la cifra de satisfacción; «18/10» es una fecha y no cuenta como el 18.
    assert mod.facts_found("Satisfacción 4,1/5 y 3,6/5.")[2] == ["18", "26", "41 %"]
    assert "18" in mod.facts_found("El 18/10 se cerró la fase.")[2]


def test_generic_phrases_flag_typical_patterns_in_place_of_what_was_found():
    assert mod.generic_phrases("Normalmente la red suele fallar; es un patrón típico.") == ["normalmente", "suele", "típico"]
    assert mod.generic_phrases(FULL) == [] and mod.generic_phrases(None) == []
