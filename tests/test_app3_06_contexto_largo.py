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


# --- B4: read_manifest robusto -------------------------------------------------------------------

import pytest  # noqa: E402


def good_manifest(**changes):
    manifest = mod.complete_phase(mod.new_manifest(), 1, "Resumen 1", ["SRC-TICKETS"], findings=2)
    return {**manifest, **changes}


def write_raw(directory, content):
    directory.mkdir(parents=True, exist_ok=True)
    data = content if isinstance(content, bytes) else json.dumps(content).encode("utf-8")
    (directory / mod.MANIFEST_FILE).write_bytes(data)


def test_a_manifest_with_bytes_that_are_not_utf8_gives_none_as_the_docstring_says(tmp_path, capsys):
    # Caso que fallaba: UnicodeDecodeError, porque solo se capturaba JSONDecodeError.
    write_raw(tmp_path, b"\xff\xfe\x00{\x80 no es utf-8")
    assert mod.read_manifest(tmp_path) is None
    assert "manifest" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("field,value", [
    ("phases_done", 1), ("phases_done", "1"), ("phases_done", ["1"]), ("phases_done", [1, 1]), ("phases_done", [9]),
    ("summaries", ["x"]), ("summaries", {"1": 3}), ("sources_covered", "SRC-TICKETS"), ("sources_covered", [1]),
    ("findings", "2"), ("findings", -1), ("findings", True), ("total_phases", "3"), ("total_phases", 2),
])
def test_a_manifest_with_wrong_types_or_values_is_rejected_instead_of_failing_later(tmp_path, field, value):
    # Caso que fallaba: `phases_done` como entero hacía fallar a `next_phase` con TypeError.
    write_raw(tmp_path, good_manifest(**{field: value}))
    assert mod.read_manifest(tmp_path) is None


@pytest.mark.parametrize("key", ["version", "total_phases", "phases_done", "summaries", "sources_covered", "findings"])
def test_a_manifest_missing_a_key_is_rejected_instead_of_raising_keyerror_in_the_prompt(tmp_path, key):
    manifest = good_manifest()
    del manifest[key]
    write_raw(tmp_path, manifest)
    assert mod.read_manifest(tmp_path) is None


def test_a_done_phase_without_its_summary_is_rejected(tmp_path):
    write_raw(tmp_path, good_manifest(summaries={}))  # phases_done=[1] pero sin resumen de la fase 1
    assert mod.read_manifest(tmp_path) is None


def test_a_manifest_of_another_version_is_rejected_with_a_warning(tmp_path, capsys):
    write_raw(tmp_path, good_manifest(version=2))
    assert mod.read_manifest(tmp_path) is None
    assert "versión" in capsys.readouterr().out


def test_a_valid_manifest_is_still_read_and_next_phase_and_prompt_work_with_it(tmp_path):
    write_raw(tmp_path, good_manifest())
    manifest = mod.read_manifest(tmp_path)
    assert manifest == good_manifest() and mod.next_phase(manifest) == 2
    assert "Resumen 1" in mod.phase_prompt(mod.PHASES[1], manifest)


# --- B4: manifest frente a scratchpad al retomar --------------------------------------------------


def save(directory, *claims):
    tools = tools_for(directory)
    for source_id, claim in claims:
        call_tool(tools["save_finding"], {"source_id": source_id, "claim": claim})


def test_scratchpad_problem_checks_that_the_scratchpad_has_the_findings_the_manifest_says(tmp_path):
    manifest = mod.complete_phase(mod.new_manifest(), 1, "R", ["SRC-TICKETS"], findings=2)
    assert "0" in mod.scratchpad_problem(tmp_path, manifest)  # scratchpad vacío: el manifest dice 2
    save(tmp_path, ("SRC-TICKETS", "a"))
    assert mod.scratchpad_problem(tmp_path, manifest)  # uno solo
    save(tmp_path, ("SRC-AUDITORIA", "b"))
    assert mod.scratchpad_problem(tmp_path, manifest) is None  # los dos que dice
    save(tmp_path, ("SRC-ENCUESTA", "c"))  # de más (una fase a medias): no es incoherente
    assert mod.scratchpad_problem(tmp_path, manifest) is None


def test_scratchpad_problem_detects_a_foreign_scratchpad_with_the_same_count_via_the_digest(tmp_path):
    save(tmp_path, ("SRC-TICKETS", "a"), ("SRC-AUDITORIA", "b"))
    digest = mod.scratchpad_digest(tmp_path, 2)
    own = mod.complete_phase(mod.new_manifest(), 1, "R", [], findings=2, digest=digest)
    assert mod.scratchpad_problem(tmp_path, own) is None
    foreign = mod.complete_phase(mod.new_manifest(), 1, "R", [], findings=2, digest="0123456789abcdef")
    assert "no son los" in mod.scratchpad_problem(tmp_path, foreign)
    assert "scratchpad_digest" not in mod.complete_phase(mod.new_manifest(), 1, "R", [], findings=0)  # sin digest: no se comprueba


def test_resuming_with_a_manifest_of_another_run_and_an_empty_scratchpad_starts_from_scratch_with_a_warning(tmp_path, capsys):
    # Caso que fallaba: phases_done=[1] y findings=5 con el scratchpad vacío se retomaba sin avisar.
    mod.write_manifest(tmp_path, mod.complete_phase(mod.new_manifest(), 1, "R", ["SRC-TICKETS"], findings=5))
    manifest = mod.start_state(tmp_path, resume=True)
    out = capsys.readouterr().out
    assert manifest == mod.new_manifest() and "aviso" in out.lower() and "desde cero" in out
    assert mod.read_manifest(tmp_path) == mod.new_manifest()


def test_resuming_with_a_scratchpad_that_matches_keeps_the_manifest(tmp_path, capsys):
    save(tmp_path, ("SRC-TICKETS", "a"), ("SRC-AUDITORIA", "b"))
    saved = mod.complete_phase(mod.new_manifest(), 1, "R", ["SRC-TICKETS"], findings=2, digest=mod.scratchpad_digest(tmp_path, 2))
    mod.write_manifest(tmp_path, saved)
    assert mod.start_state(tmp_path, resume=True) == saved
    assert "aviso" not in capsys.readouterr().out.lower()
    assert len(mod.read_scratchpad(tmp_path)) == 2  # no se borra


# --- B4: scratchpad con una línea truncada --------------------------------------------------------

TRUNCATED = '{"source_id": "SRC-AUDITORIA", "cla'


def scratch_file(directory):
    return directory / mod.SCRATCHPAD_FILE


def test_read_scratchpad_ignores_an_incomplete_last_line_with_a_warning(tmp_path, capsys):
    # Caso que fallaba: JSONDecodeError por una caída a mitad de escritura.
    save(tmp_path, ("SRC-TICKETS", "a"))
    with scratch_file(tmp_path).open("a", encoding="utf-8") as handle:
        handle.write(TRUNCATED)
    entries = mod.read_scratchpad(tmp_path)
    assert [e["source_id"] for e in entries] == ["SRC-TICKETS"]
    assert "aviso" in capsys.readouterr().out.lower()


def test_read_scratchpad_fails_clearly_when_the_corruption_is_in_the_middle(tmp_path):
    scratch_file(tmp_path).write_text('{"source_id": "A", "claim": "x"}\n{roto\n{"source_id": "B", "claim": "y"}\n', encoding="utf-8")
    with pytest.raises(mod.ScratchpadError, match="línea 2"):
        mod.read_scratchpad(tmp_path)


def test_the_read_tool_returns_a_structured_error_instead_of_raising_when_the_scratchpad_is_corrupt(tmp_path):
    scratch_file(tmp_path).write_text('{roto\n{"source_id": "B", "claim": "y"}\n', encoding="utf-8")
    outcome = call_tool(tools_for(tmp_path)["read_scratchpad"], {})
    assert outcome.is_error and "corrupto" in json.loads(outcome.text)["message"]


def test_saving_after_a_truncated_tail_drops_the_fragment_so_the_new_line_is_not_glued_to_it(tmp_path):
    save(tmp_path, ("SRC-TICKETS", "a"))
    with scratch_file(tmp_path).open("a", encoding="utf-8") as handle:
        handle.write(TRUNCATED)
    save(tmp_path, ("SRC-ENCUESTA", "c"))
    assert [e["source_id"] for e in mod.read_scratchpad(tmp_path)] == ["SRC-TICKETS", "SRC-ENCUESTA"]


def test_saving_after_a_complete_line_without_newline_keeps_it(tmp_path):
    scratch_file(tmp_path).write_text('{"source_id": "SRC-TICKETS", "claim": "a"}', encoding="utf-8")  # cayó antes del salto de línea
    save(tmp_path, ("SRC-ENCUESTA", "c"))
    assert [e["source_id"] for e in mod.read_scratchpad(tmp_path)] == ["SRC-TICKETS", "SRC-ENCUESTA"]


# --- B4: el estado vive bajo estado/<perfil>/ ---------------------------------------------------


def test_state_lives_under_the_profile_state_dir_not_the_shared_system_temp(tmp_path):
    import tempfile
    from pathlib import Path

    assert mod.state_directory(profile="ana", root=tmp_path) == tmp_path / "estado" / "ana" / "app3-06"
    assert mod.state_directory(profile="luis", root=tmp_path) != mod.state_directory(profile="ana", root=tmp_path)
    default = mod.state_directory()
    assert Path(tempfile.gettempdir()) not in default.parents and "estado" in default.parts
    assert not hasattr(mod, "STATE_DIR")


# --- B4b: copia de seguridad en vez de borrar, validación en save_finding y versión booleana ------


def test_a_manifest_with_a_boolean_version_is_rejected(tmp_path):
    # Caso que fallaba: `version: true` pasaba la validación porque True == 1.
    write_raw(tmp_path, good_manifest(version=True))
    assert mod.read_manifest(tmp_path) is None


def backups_of(directory):
    return sorted(p for p in directory.parent.iterdir() if p.name.startswith(directory.name + ".") and p.name.endswith(".bak"))


def test_a_discarded_manifest_moves_the_state_to_a_bak_directory_instead_of_deleting_it(tmp_path, capsys):
    # Caso que fallaba: un manifest de una versión futura se descartaba y `rmtree` borraba también el scratchpad.
    state = tmp_path / "app3-06"
    save(state, ("SRC-TICKETS", "a"))
    write_raw(state, good_manifest(version=2))
    manifest = mod.start_state(state, resume=True)
    out = capsys.readouterr().out
    assert manifest == mod.new_manifest()
    (backup,) = backups_of(state)
    assert [json.loads(line)["claim"] for line in (backup / mod.SCRATCHPAD_FILE).read_text(encoding="utf-8").splitlines()] == ["a"]
    assert backup.name in out and ".bak" in out
    assert mod.read_scratchpad(state) == []  # el estado nuevo empieza limpio


def test_a_manifest_that_does_not_match_the_scratchpad_also_leaves_a_backup(tmp_path, capsys):
    state = tmp_path / "app3-06"
    mod.write_manifest(state, mod.complete_phase(mod.new_manifest(), 1, "R", ["SRC-TICKETS"], findings=5))
    mod.start_state(state, resume=True)
    assert len(backups_of(state)) == 1 and ".bak" in capsys.readouterr().out


def test_two_discards_in_the_same_second_do_not_overwrite_each_others_backup(tmp_path):
    state = tmp_path / "app3-06"
    for _ in range(2):
        write_raw(state, good_manifest(version=2))
        mod.start_state(state, resume=True)
    assert len(backups_of(state)) == 2


def test_a_clean_start_or_a_finished_run_leaves_no_backup(tmp_path):
    state = tmp_path / "app3-06"
    mod.start_state(state, resume=True)  # no hay nada que guardar
    done = good_manifest(phases_done=[1, 2, 3], summaries={"1": "a", "2": "b", "3": "c"})
    write_raw(state, done)
    mod.start_state(state, resume=True)  # una ejecución terminada se sustituye por una nueva
    assert backups_of(state) == []


@pytest.mark.parametrize("args", [
    {"source_id": "SRC-TICKETS", "claim": 18},
    {"source_id": "SRC-TICKETS", "claim": None},
    {"claim": "18 horas"},
    {"source_id": 7, "claim": "18 horas"},
    {"source_id": "SRC-TICKETS", "claim": "18 horas", "figure": "dieciocho"},
])
def test_save_finding_returns_a_validation_error_instead_of_raising(tmp_path, args):
    # Casos que fallaban: `claim` numérico daba AttributeError y la falta de `source_id`, KeyError.
    result = call_tool(tools_for(tmp_path)["save_finding"], args)
    assert result.is_error and json.loads(result.text)["errorCategory"] == "validation"
    assert mod.read_scratchpad(tmp_path) == []
