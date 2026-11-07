"""Tests de app3/11_criterios_y_ci: repositorio temporal con el cambio, diff, prompts por variante (una sola diferencia), schema, puntuación contra lo sembrado, registro de descartados, segunda revisión y generación de tests. Sin modelo."""

import json
import shutil
import subprocess
from pathlib import Path

import jsonschema
import pytest

from harness.data import DATA_DIR, load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/11_criterios_y_ci.py")

pytestmark_git = pytest.mark.skipif(shutil.which("git") is None, reason="necesita git")
LABELS = load("cambio_revision_etiquetas.json")
CHANGE = load("cambio_revision.json")


@pytest.fixture(scope="module")
def repo():
    return mod.build_review_repo()


def finding(file="notificaciones/avisos.py", line=20, category="security", severity="critical", pattern="shell_injection", **extra):
    return {"file": file, "line": line, "category": category, "severity": severity, "problem": "p", "suggested_fix": "f", "detected_pattern": pattern, **extra}


# --- repositorio temporal y diff (3.6) ---------------------------------------------------------------------------------

@pytestmark_git
def test_repo_is_a_temporary_copy_and_never_touches_the_data_folder(repo):
    assert DATA_DIR not in repo.path.parents and repo.path != DATA_DIR / "repo_mesa"
    assert (repo.path / "core" / "sla.py").is_file()
    assert "restante_horas" in (DATA_DIR / "repo_mesa" / "core" / "sla.py").read_text(encoding="utf-8")


@pytestmark_git
def test_ci_claude_md_is_in_the_cwd_and_committed_in_the_base_so_it_is_not_in_the_diff(repo):
    assert (repo.path / "CLAUDE.md").read_text(encoding="utf-8") == mod.ci_claude_md(standards=True)
    assert "CLAUDE.md" not in mod.diff_of(repo, repo.base, repo.commit_1)
    assert "CLAUDE.md" not in mod.diff_of(repo, repo.base, repo.commit_2)


@pytestmark_git
def test_first_diff_contains_the_four_seeded_flaws_and_the_two_decoys(repo):
    diff = mod.diff_of(repo, repo.base, repo.commit_1)
    for marker in ('debe_escalar(t["horas"], t["prioridad"])', "os.system(", "NOTIF_TIMEOUT = 60", '"restante_minutos"', "REINTENTOS = 5", "except ValueError as exc:", "% del plazo consumido"):
        assert marker in diff, marker
    assert "len(restantes)" not in diff, "el segundo commit aún no existe"


@pytestmark_git
def test_cross_file_callers_are_not_visible_in_the_first_diff(repo):
    diff = mod.diff_of(repo, repo.base, repo.commit_1)
    assert "restante_horas" not in diff.replace("-    return {\"limite_horas\": limite, \"restante_horas\": limite - horas_abiertas}", ""), "ningún llamador a la vista"
    assert "informes/resumen.py" not in diff


@pytestmark_git
def test_pr_diff_after_the_second_commit_has_the_fix_the_new_bug_and_the_old_flaws(repo):
    diff = mod.diff_of(repo, repo.base, repo.commit_2)
    assert 'debe_escalar(t["prioridad"], t["horas"])' in diff and 'debe_escalar(t["horas"], t["prioridad"])' not in diff
    assert "/ len(restantes)" in diff and "os.system(" in diff and "NOTIF_TIMEOUT = 60" in diff


@pytestmark_git
def test_diff_line_numbers_agree_with_the_labels(repo):
    """El número de línea de cada fallo sembrado es el del archivo en el estado final de ese commit."""
    for flaw in LABELS["seeded"]:
        commit = repo.commit_1 if flaw["commit"] == 1 else repo.commit_2
        text = subprocess.run(["git", "show", f"{commit}:{flaw['file']}"], cwd=repo.path, capture_output=True, text=True, encoding="utf-8", check=True).stdout
        assert flaw["marker"] in text.splitlines()[flaw["line"] - 1], flaw["id"]


@pytestmark_git
def test_each_repo_is_a_new_directory(repo):
    other = mod.build_review_repo()
    assert other.path != repo.path


# --- el CLAUDE.md de CI (3.6-K3, S5) -------------------------------------------------------------------------------------

def test_ci_claude_md_holds_conventions_and_test_standards_and_no_review_task():
    text = mod.ci_claude_md(standards=True)
    assert "ValueError" in text, "el patrón local de excepciones está en el contexto del proyecto"
    assert "fixture" in text.lower() and "parametrize" in text
    assert "informa" not in text.lower(), "la tarea y los criterios van en el prompt, no aquí"


def test_ci_claude_md_without_standards_only_drops_the_standards_section():
    with_standards, without = mod.ci_claude_md(standards=True), mod.ci_claude_md(standards=False)
    assert without != with_standards and with_standards.startswith(without.rstrip("\n")[:80])
    assert "parametrize" not in without and "fixture" not in without.lower() and "ValueError" in without


# --- el prompt y sus variantes: cada una cambia una sola cosa (4.1, 4.2) ------------------------------------------------------------

DIFF = "diff --git a/x b/x\n+código\n"


def test_correct_prompt_has_criteria_severities_examples_and_the_diff():
    prompt = mod.build_review_prompt(DIFF, message="mensaje del commit")
    assert mod.CRITERIA in prompt and mod.FEW_SHOT in prompt and DIFF in prompt and "mensaje del commit" in prompt


def test_criteria_name_what_to_report_and_what_not_and_give_a_code_example_per_severity():
    text = mod.CRITERIA
    for category in ("bug", "security", "comment"):
        assert category in text
    assert "estilo" in text.lower() and "patrones locales" in text.lower()
    for severity in ("critical", "major", "minor"):
        assert severity in text
    assert text.count("```") >= 6, "un ejemplo de código por severidad (4.1-S3)"


def test_comment_criterion_is_explicit_not_vague():
    """4.1-K1: «marca un comentario solo si lo que dice contradice el código», no «comprueba que los comentarios son correctos»."""
    assert "contradice" in mod.CRITERIA and "comprueba que los comentarios" not in mod.CRITERIA


def test_anti_conservador_replaces_only_the_criteria_with_a_conservative_instruction():
    correct = mod.build_review_prompt(DIFF, message="m")
    anti = mod.build_review_prompt(DIFF, message="m", anti="conservador")
    assert correct.replace(mod.CRITERIA, mod.CONSERVATIVE) == anti
    assert "conservador" in mod.CONSERVATIVE.lower() and "bug" not in mod.CONSERVATIVE


def test_anti_sin_ejemplos_removes_only_the_few_shot_block():
    correct = mod.build_review_prompt(DIFF, message="m")
    anti = mod.build_review_prompt(DIFF, message="m", anti="sin_ejemplos")
    assert correct.replace(mod.FEW_SHOT, "") == anti


def test_few_shot_shows_the_output_format_and_an_acceptable_pattern_apart_from_a_real_problem():
    text = mod.FEW_SHOT
    for field in ("file", "line", "category", "severity", "problem", "suggested_fix", "detected_pattern"):
        assert f'"{field}"' in text
    assert "NO informes" in text or "no informes" in text.lower()
    assert "exec" not in text and "debe_escalar" not in text, "los ejemplos no son el código del cambio"


def test_few_shot_examples_validate_against_the_review_schema():
    for example in mod.FEW_SHOT_FINDINGS:
        jsonschema.validate({"findings": [example]}, mod.review_schema())


def test_disabled_category_leaves_the_prompt_and_the_schema_without_it_and_nothing_else_changes():
    base = mod.build_review_prompt(DIFF, message="m")
    off = mod.build_review_prompt(DIFF, message="m", disabled=("comment",))
    assert base != off and "- comment:" in base and "- comment:" not in off
    enum = mod.review_schema(disabled=("comment",))["properties"]["findings"]["items"]["properties"]["category"]["enum"]
    assert "comment" not in enum and {"bug", "security"} <= set(enum)
    assert "comment" in mod.review_schema()["properties"]["findings"]["items"]["properties"]["category"]["enum"]


def test_comment_category_leaves_no_trace_outside_its_own_line():
    """4.1-S2 cambia una sola cosa: sin `comment`, ni la severidad `minor` ni el criterio de `bug` siguen hablando de comentarios o docstrings."""
    base = mod.build_review_prompt(DIFF, message="m")
    off = mod.build_review_prompt(DIFF, message="m", disabled=("comment",))
    assert "comentario" in base and "comentario" not in off.lower()
    assert "docstring" not in mod.criteria_line("bug") and "docstring" not in mod.CRITERIA.split("Severidades")[1]
    # Control: quitar otra categoría no toca la de `comment`.
    assert mod.criteria_line("comment") in mod.build_review_prompt(DIFF, message="m", disabled=("security",))


def test_disabling_a_category_removes_only_its_line():
    base = mod.build_review_prompt(DIFF, message="m")
    off = mod.build_review_prompt(DIFF, message="m", disabled=("comment",))
    assert base.replace(mod.criteria_line("comment") + "\n", "") == off


def test_unknown_variant_or_category_is_rejected():
    with pytest.raises(ValueError):
        mod.build_review_prompt(DIFF, message="m", anti="otra")
    with pytest.raises(ValueError):
        mod.build_review_prompt(DIFF, message="m", disabled=("no_existe",))


def test_schema_requires_every_field_including_detected_pattern_and_validates_good_and_bad_output():
    schema = mod.review_schema()
    item = schema["properties"]["findings"]["items"]
    assert set(item["required"]) == {"file", "line", "category", "severity", "problem", "suggested_fix", "detected_pattern"}
    jsonschema.validate({"findings": [finding()]}, schema)
    bad = finding()
    del bad["detected_pattern"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"findings": [bad]}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"findings": [finding(severity="enorme")]}, schema)


# --- puntuación contra lo sembrado (4.1, señal) -----------------------------------------------------------------------------------

def score(findings, scope=1):
    return mod.score_findings(findings, LABELS, scope=scope)


def test_a_finding_on_the_seeded_line_finds_it_and_nothing_is_a_false_positive():
    result = score([finding()])
    assert result.found == {"B"} and result.false_positives == [] and result.missed == {"A", "C", "D", "F"}


def test_line_window_accepts_a_small_offset_and_rejects_a_far_one():
    near = score([finding(line=21)])
    far = score([finding(line=40)])
    assert near.found == {"B"} and far.found == set() and len(far.false_positives) == 1


def test_a_finding_in_the_wrong_file_is_a_false_positive_even_on_the_same_line():
    assert score([finding(file="config.py", line=20)]).found == set()


def test_cross_file_finding_counts_in_the_flawed_file_or_in_any_caller():
    in_sla = score([finding(file="core/sla.py", line=12, category="bug")])
    in_caller = score([finding(file="informes/resumen.py", line=1, category="bug", problem="usa restante_horas, que ya no existe")])
    assert in_sla.found == {"D"} and in_caller.found == {"D"}
    assert score([finding(file="tickets/escalado.py", line=1)]).found == set()
    # Un hallazgo cualquiera sobre un llamador que no habla de la clave o la unidad no es el fallo entre archivos.
    assert score([finding(file="informes/resumen.py", line=1, category="bug")]).found == set()


def test_two_findings_on_the_same_flaw_count_once_and_the_extra_is_a_duplicate_not_a_false_positive():
    result = score([finding(), finding(line=21, pattern="otra")])
    assert result.found == {"B"} and result.duplicates == 1 and result.false_positives == []


def test_flagging_the_correct_change_or_the_acceptable_pattern_is_recorded_apart():
    result = score([finding(file="config.py", line=6, category="bug", severity="minor", pattern="magic_number"),
                    finding(file="notificaciones/avisos.py", line=13, category="bug", severity="minor", pattern="exception_control_flow")])
    assert [f["detected_pattern"] for f in result.flagged_ok] == ["magic_number", "exception_control_flow"]
    assert result.found == set() and result.false_positives == []


def test_scope_two_removes_the_resolved_flaw_and_adds_the_new_one():
    result = score([finding(file="informes/resumen.py", line=13, category="bug", severity="major", pattern="zero_division", problem="división por cero")], scope=2)
    assert result.found == {"E"} and result.missed == {"B", "C", "D", "F"}
    assert score([finding(file="tickets/escalado.py", line=18, category="bug")], scope=2).false_positives, "A ya no está en el estado final"


def test_precision_and_recall_with_no_findings_do_not_divide_by_zero():
    result = score([])
    assert mod.precision(result) is None and mod.recall(result) == 0.0


def test_precision_counts_true_findings_over_all_findings():
    result = score([finding(), finding(file="x.py", line=1), finding(file="y.py", line=1)])
    assert mod.precision(result) == pytest.approx(1 / 3) and mod.recall(result) == pytest.approx(0.2)


def test_precision_by_category_shows_the_category_that_misleads_the_rest():
    findings = [finding(), finding(file="a.py", line=1, category="comment", severity="minor", pattern="x"), finding(file="b.py", line=1, category="comment", severity="minor", pattern="y")]
    by = mod.precision_by_category(score(findings))
    assert by["security"] == 1.0 and by["comment"] == 0.0


def test_negative_control_a_clean_review_flags_nothing_and_a_noisy_one_is_caught():
    """Control positivo de la medida: una revisión que marca todo lo marcable da recall completo y falsos positivos; una vacía no encuentra nada."""
    everything = [finding(file=s["file"], line=s["line"], category="bug") for s in LABELS["seeded"] if s["commit"] == 1] + [finding(file="x.py", line=1) for _ in range(4)]
    result = score(everything)
    assert mod.recall(result) == 1.0 and len(result.false_positives) == 4
    assert mod.recall(score([])) == 0.0


# --- 4.4-K3, S3: registro de descartados agrupado por detected_pattern ---------------------------------------------------------------------

def test_discard_log_groups_false_positives_and_flagged_ok_by_detected_pattern():
    findings = [
        finding(),  # acierto: no se descarta
        finding(file="a.py", line=1, category="comment", severity="minor", pattern="Nombre_Corto"),
        finding(file="b.py", line=1, category="comment", severity="minor", pattern="nombre corto"),
        finding(file="config.py", line=6, category="bug", severity="minor", pattern="magic_number"),
        finding(file="c.py", line=1, pattern=""),
    ]
    log = mod.discard_log(score(findings))
    assert log == {"nombre_corto": 2, "magic_number": 1, "sin_patron": 1}
    assert list(log) == ["nombre_corto", "magic_number", "sin_patron"], "de más a menos frecuente"


def test_discard_log_is_empty_when_everything_found_matches():
    assert mod.discard_log(score([finding()])) == {}


def test_normalize_pattern_handles_case_spaces_and_punctuation():
    assert mod.normalize_pattern("  Shell Injection! ") == "shell_injection"
    assert mod.normalize_pattern(None) == "sin_patron"


# --- 3.6-S3: segunda revisión con los hallazgos previos --------------------------------------------------------------------------------------

def test_prior_findings_are_the_first_review_rendered_with_ids_and_validate_against_the_schema():
    prior = mod.prior_findings(LABELS)
    assert [p["id"] for p in prior] == ["P1", "P2", "P3", "P4", "P5"]
    assert {p["category"] for p in prior} == {"bug", "security", "comment"} | {"bug"}
    assert prior[0]["file"] == "tickets/escalado.py"


def test_rereview_prompt_with_previous_adds_only_the_list_and_the_instruction():
    prior = mod.prior_findings(LABELS)
    with_prior = mod.build_rereview_prompt(DIFF, message="m", prior=prior)
    without = mod.build_rereview_prompt(DIFF, message="m", prior=None)
    assert with_prior.replace(mod.prior_block(prior), "") == without
    assert "P1" in with_prior and "nuevo" in with_prior.lower() and "P1" not in without
    assert mod.REREVIEW_TASK in without, "ambas ramas saben que es una segunda revisión de la rama"


def test_rereview_classification_separates_new_repeated_and_resolved_reports():
    prior = mod.prior_findings(LABELS)
    findings = [
        finding(file="informes/resumen.py", line=13, category="bug", severity="major", pattern="zero_division"),  # nuevo (E)
        finding(),  # repetido (B ya publicado)
        finding(file="config.py", line=12, category="comment", severity="minor", pattern="comment"),  # repetido (C)
        finding(file="tickets/escalado.py", line=18, category="bug", pattern="swapped"),  # A, ya resuelto
        finding(file="z.py", line=1),
    ]
    c = mod.classify_rereview(findings, LABELS, prior)
    assert c["nuevos"] == {"E"} and c["repetidos"] == {"B", "C"} and c["resueltos_repetidos"] == 1 and c["otros"] == 1


def test_rereview_with_nothing_reported_has_zero_everything():
    c = mod.classify_rereview([], LABELS, mod.prior_findings(LABELS))
    assert c == {"nuevos": set(), "repetidos": set(), "resueltos_repetidos": 0, "otros": 0, "total": 0}


# --- 3.6-S4, S5: generación de tests --------------------------------------------------------------------------------------------------------------

def test_scenario_key_ignores_case_order_and_numeric_form():
    a = mod.scenario_key("Calcular_SLA", {"prioridad": "Alta", "horas_abiertas": 3})
    b = mod.scenario_key("calcular_sla", {"horas_abiertas": 3.0, "prioridad": "alta"})
    assert a == b
    assert a != mod.scenario_key("calcular_sla", {"prioridad": "alta", "horas_abiertas": 9})


def test_tests_schema_and_scoring_count_duplicates_of_existing_scenarios():
    proposed = {"tests": [
        {"function": "calcular_sla", "args": {"prioridad": "alta", "horas_abiertas": 9}, "expected": "ValueError"},
        {"function": "calcular_sla", "args": {"prioridad": "critica", "horas_abiertas": 1}, "expected": "restante_minutos 0"},
        {"function": "debe_escalar_lote", "args": {"tickets": []}, "expected": "[]"},
    ]}
    jsonschema.validate(proposed, mod.tests_schema())
    result = mod.score_tests(proposed["tests"], LABELS)
    assert result.total == 3 and result.duplicates == 1 and result.new == 2
    assert result.on_changed_code == 2, "los dos que no repiten tocan lo que cambió"
    assert result.duplicated == [("calcular_sla", {"prioridad": "alta", "horas_abiertas": 9})]


def test_score_tests_tolerates_malformed_entries():
    result = mod.score_tests([{"function": "calcular_sla"}, {"function": 3, "args": []}, "x"], LABELS)
    assert result.total == 3 and result.duplicates == 0


def test_existing_tests_text_lists_every_test_file_of_the_repo(repo):
    text = mod.existing_tests_text(repo.path)
    for name in ("test_dentro_de_plazo", "test_vencido", "test_escala_cuando_vence", "test_horas_restantes"):
        assert name in text


def test_tests_prompt_includes_existing_tests_only_in_the_correct_variant():
    with_tests = mod.build_tests_prompt(DIFF, existing="def test_vencido(): ...")
    without = mod.build_tests_prompt(DIFF, existing=None)
    assert "def test_vencido" in with_tests and "def test_vencido" not in without
    assert DIFF in with_tests and DIFF in without


def test_tests_variants_are_one_difference_each():
    assert mod.tests_arm(None) == {"existing": True, "standards": True}
    assert mod.tests_arm("sin_tests_existentes") == {"existing": False, "standards": True}
    assert mod.tests_arm("sin_estandares") == {"existing": True, "standards": False}
    with pytest.raises(ValueError):
        mod.tests_arm("otra")


# --- la orden de claude -p ------------------------------------------------------------------------------------------------------------------------

@pytestmark_git
def test_review_command_is_isolated_read_only_with_budget_and_schema(repo):
    cmd = mod.review_command(repo.path, model="claude-sonnet-5-5", budget=0.2, schema=mod.review_schema())
    assert "--max-budget-usd" in cmd and cmd[cmd.index("--setting-sources") + 1] == "project"
    assert cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob"
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == mod.review_schema()
    assert "--resume" not in cmd


@pytestmark_git
def test_tests_command_has_no_tools_so_the_model_cannot_find_the_existing_tests_by_itself(repo):
    cmd = mod.review_command(repo.path, model="m", budget=0.2, schema=mod.tests_schema(), tools=())
    assert cmd[cmd.index("--tools") + 1] == ""


def test_a_finding_with_the_line_off_still_counts_if_it_names_the_flawed_function():
    """El modelo cita las líneas de forma aproximada: lo que identifica el fallo es su archivo y su símbolo."""
    far = finding(file="notificaciones/avisos.py", line=40, category="security", problem="enviar_aviso concatena el mensaje en la shell")
    assert score([far]).found == {"B"} and score([far]).false_positives == []
    assert score([finding(file="notificaciones/avisos.py", line=40, problem="otra cosa sin relación")]).found == set()


def test_the_symbol_only_counts_in_the_same_file_as_the_flaw():
    assert score([finding(file="config.py", line=40, problem="enviar_aviso concatena el mensaje")]).found == set()


def test_a_symbol_match_on_the_decoy_is_recorded_as_flagged_ok_not_as_a_false_positive():
    result = score([finding(file="config.py", line=40, category="comment", severity="minor", pattern="x", problem="REINTENTOS no está justificado")])
    assert len(result.flagged_ok) == 1 and result.false_positives == []
