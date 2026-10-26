"""Tests de app1/02_tools_integradas: llamadores esperados con ast, comprobadores de rutas y de edición, señales del RunRecord y configuración por parte. Sin modelo."""

import pytest

from harness.data import copy_to_temp
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app1_agente_unico/02_tools_integradas.py")


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    return copy_to_temp("repo_mesa")


def call(cid, name, response="r1", is_error=False):
    return ToolCall(cid, name, {}, response, "principal", True, is_error, "x")


# --- llamadores esperados (ast) ------------------------------------------------

def test_exported_names_follow_the_alias_chain(repo):
    # api.py exporta `sla_ticket`; avisos.py lo reimporta como `plazo`.
    assert mod.exported_names(repo, "calcular_sla") == {"calcular_sla", "sla_ticket", "plazo"}


def test_expected_callers_include_alias_only_files(repo):
    callers = mod.expected_callers(repo)
    assert callers == {
        "tickets/escalado.py", "tests/test_sla.py",  # por el nombre original
        "informes/resumen.py", "notificaciones/avisos.py",  # solo por alias
    }
    # La definición y el reexport no son llamadas.
    assert "core/sla.py" not in callers and "api.py" not in callers


def test_alias_only_callers_are_the_ones_a_name_search_misses(repo):
    assert mod.alias_only_callers(repo) == {"informes/resumen.py", "notificaciones/avisos.py"}


def test_expected_tests_found_by_glob(repo):
    assert mod.expected_tests(repo) == {
        "tests/test_sla.py", "tickets/tests/test_escalado.py", "informes/tests/test_resumen.py",
    }


# --- comprobador de la respuesta -----------------------------------------------

def test_check_paths_found_and_missing():
    expected = {"tickets/escalado.py", "informes/resumen.py"}
    found, missing = mod.check_paths("Lo llaman `tickets/escalado.py` y informes\\resumen.py", expected)
    assert found == expected and missing == set()
    found, missing = mod.check_paths("Solo tickets/escalado.py", expected)
    assert missing == {"informes/resumen.py"}


def test_check_paths_without_answer_misses_everything():
    assert mod.check_paths(None, {"a.py"}) == (set(), {"a.py"})


def test_check_paths_does_not_match_a_longer_name():
    # `escalado.py` no debe contar por aparecer dentro de `pre_escalado.py`.
    assert mod.check_paths("pre_escalado.py", {"escalado.py"}) == (set(), {"escalado.py"})


# --- edición: ancla no única ---------------------------------------------------

def test_anchor_appears_exactly_twice_in_the_original(repo):
    assert mod.anchor_count((repo / "config.py").read_text(encoding="utf-8")) == 2


def test_expected_config_changes_only_the_second_block(repo):
    original = (repo / "config.py").read_text(encoding="utf-8")
    expected = mod.expected_config(original)
    assert expected.count("TIMEOUT = 30") == 1 and expected.count("TIMEOUT = 60") == 1
    assert expected.index("TIMEOUT = 30") < expected.index("TIMEOUT = 60")
    assert expected.index("NOTIF_URL") < expected.index("TIMEOUT = 60")  # el segundo es el de notificaciones


def test_edit_check_accepts_exact_result_and_rejects_the_rest(repo):
    original = (repo / "config.py").read_text(encoding="utf-8")
    assert mod.edit_is_correct(mod.expected_config(original), original)
    assert not mod.edit_is_correct(original, original)  # no cambió nada
    assert not mod.edit_is_correct(original.replace("TIMEOUT = 30", "TIMEOUT = 60"), original)  # cambió los dos
    first_only = original.replace("TIMEOUT = 30", "TIMEOUT = 60", 1)
    assert not mod.edit_is_correct(first_only, original)  # cambió el primero


def test_edit_check_tolerates_a_widened_anchor():
    # El resultado final es lo que cuenta, no cómo se llegó: ampliar el ancla es válido.
    original = "A = 1\nTIMEOUT = 30\nB = 2\nTIMEOUT = 30\nC = 3\n"
    assert mod.edit_is_correct("A = 1\nTIMEOUT = 30\nB = 2\nTIMEOUT = 60\nC = 3\n", original)


# --- señales del RunRecord -----------------------------------------------------

def test_tool_counts():
    rec = RunRecord(tool_calls=[call("1", "Read"), call("2", "Read"), call("3", "Grep")])
    assert mod.tool_counts(rec) == {"Read": 2, "Grep": 1}
    assert mod.tool_counts(RunRecord()) == {}


def test_edit_fallback_detects_failed_edit_then_write():
    failed = call("1", "Edit", "r1", is_error=True)
    rec = RunRecord(tool_calls=[call("0", "Read"), failed, call("2", "Write", "r2")])
    assert mod.edit_fallback(rec) == (True, True)


def test_edit_fallback_write_before_failed_edit_does_not_count():
    rec = RunRecord(tool_calls=[call("1", "Write"), call("2", "Edit", is_error=True)])
    assert mod.edit_fallback(rec) == (True, False)


def test_edit_fallback_with_successful_edit():
    rec = RunRecord(tool_calls=[call("1", "Edit")])
    assert mod.edit_fallback(rec) == (False, False)


def test_widened_anchor_recovery_is_a_second_successful_edit():
    rec = RunRecord(tool_calls=[call("1", "Edit", is_error=True), call("2", "Edit", "r2")])
    assert mod.edit_fallback(rec) == (True, False)
    assert mod.recovered_with_edit(rec) is True
    assert mod.recovered_with_edit(RunRecord(tool_calls=[call("1", "Edit")])) is False


# --- configuración por parte y variante ----------------------------------------

def test_every_anti_belongs_to_one_part():
    assert mod.ANTI_PART == {"sin_grep": "busqueda", "leer_todo": "incremental", "solo_nombre": "wrapper"}
    assert set(mod.ANTI_PART.values()) <= set(mod.PARTS)


def test_tools_per_part_and_variant():
    assert set(mod.tools_for("busqueda", None)) == {"Read", "Grep", "Glob"}
    assert set(mod.tools_for("busqueda", "sin_grep")) == {"Read", "Glob"}
    assert "Grep" in mod.tools_for("incremental", None) and "Grep" in mod.tools_for("incremental", "leer_todo")
    assert set(mod.tools_for("edicion", None)) == {"Read", "Write", "Edit", "Grep"}
    # Las partes de lectura nunca llevan tools que escriben.
    for part in ("busqueda", "incremental", "wrapper"):
        assert not {"Write", "Edit"} & set(mod.tools_for(part, None))


def test_prompts_per_part():
    assert [label for label, _ in mod.prompts_for("busqueda", None)] == ["error", "tests"]
    assert len(mod.prompts_for("incremental", None)) == 1
    anti = mod.prompts_for("incremental", "leer_todo")[0][1]
    assert "todos los archivos" in anti and "todos los archivos" not in mod.prompts_for("incremental", None)[0][1]


def test_wrapper_variants_differ_in_the_method_not_in_the_question():
    right = mod.system_prompt("wrapper", None)
    wrong = mod.system_prompt("wrapper", "solo_nombre")
    assert "reexporta" in right and "reexporta" not in wrong
    assert "solo" in wrong.lower()
    assert mod.prompts_for("wrapper", None) == mod.prompts_for("wrapper", "solo_nombre")


def test_edit_prompt_names_the_notifications_timeout():
    prompt = mod.prompts_for("edicion", None)[0][1]
    assert "segundo" in prompt and "TIMEOUT = 30" in prompt and "60" in prompt


def test_options_are_isolated_with_budget_and_temp_cwd(repo):
    options = mod.build_options("busqueda", None, cwd=repo, budget=0.1, model="m")
    assert options.setting_sources == [] and options.max_budget_usd == 0.1
    assert options.cwd == str(repo) and options.permission_mode == "dontAsk"
    assert set(options.tools) == set(options.allowed_tools) == {"Read", "Grep", "Glob"}
