"""Tests de app3/12_revision_independiente: reparto de pasadas, prompts de cada rama (una diferencia), fusión de hallazgos, confianza y coste de la sesión reanudada; y, de la revisión independiente de `app3/12`, archivos nuevos en el diff generado, repositorio generador sin el futuro, fusión de hallazgos distintos y variante `una_pasada`. Sin modelo.

PROPÓSITO: comprobar el reparto de pasadas, los prompts de cada rama (con una diferencia), la fusión de hallazgos, la confianza y el coste de la sesión reanudada; y los casos borde que encontró la revisión independiente: archivos nuevos en el diff generado, repositorio generador sin el futuro, fusión de hallazgos distintos y variante `una_pasada`.

POR QUÉ EXISTE: el módulo compara una revisión independiente con la del propio generador; el reparto y el coste de la rama reanudada deben ser correctos para que la comparación valga, y los casos borde (un diff sin los archivos nuevos, un generador que dejaba ver el cambio) quedan fijados aquí.

QUÉ NO HACE: no lanza `claude -p` ni llama al modelo.
"""

import subprocess

import jsonschema
import pytest

from harness import headless
from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/12_revision_independiente.py")
m11 = mod.m11
LABELS = load("cambio_revision_etiquetas.json")
CHANGE = load("cambio_revision.json")

TWO_FILES = (
    "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"
    "diff --git a/dir/b.py b/dir/b.py\n--- a/dir/b.py\n+++ b/dir/b.py\n@@ -1 +1 @@\n-p\n+q\n"
)


def f(file="a.py", line=1, category="bug", confidence=0.9, **extra):
    return {"file": file, "line": line, "category": category, "severity": "major", "problem": "p", "suggested_fix": "x", "detected_pattern": "pat", "confidence": confidence, **extra}


# --- el reparto en pasadas (4.6-K3, S2 · 1.6-K2, S2) ------------------------------------------------------------------------------------

def test_split_diff_gives_one_chunk_per_file():
    chunks = mod.split_diff(TWO_FILES)
    assert list(chunks) == ["a.py", "dir/b.py"]
    assert "+y" in chunks["a.py"] and "+q" not in chunks["a.py"]
    assert chunks["dir/b.py"].startswith("diff --git a/dir/b.py")


def test_split_diff_of_an_empty_diff_is_empty():
    assert mod.split_diff("") == {}


def test_plan_has_one_local_pass_per_file_and_one_integration_pass_after_them():
    plan = mod.plan_passes(TWO_FILES)
    assert [p.kind for p in plan] == ["file", "file", "integration"]
    assert [p.name for p in plan[:2]] == ["a.py", "dir/b.py"]
    assert plan[-1].name == "integración"


def test_local_passes_have_no_tools_and_the_integration_pass_can_read_the_repository():
    plan = mod.plan_passes(TWO_FILES)
    assert all(p.tools == () for p in plan if p.kind == "file")
    assert plan[-1].tools == headless.READ_ONLY_TOOLS


def test_file_pass_prompt_has_only_its_file_and_says_nothing_else_is_visible():
    chunks = mod.split_diff(TWO_FILES)
    prompt = mod.file_pass_prompt(chunks["a.py"], message="m")
    assert "+y" in prompt and "+q" not in prompt
    assert "solo este archivo" in prompt.lower()


def test_integration_prompt_has_the_whole_diff_the_local_findings_and_forbids_repeating_them():
    local = [f("a.py", 1), f("dir/b.py", 1)]
    prompt = mod.integration_prompt(TWO_FILES, local, message="m")
    assert "+y" in prompt and "+q" in prompt
    assert "a.py:1" in prompt and "dir/b.py:1" in prompt
    assert "no repitas" in prompt.lower() and "entre archivos" in prompt.lower()


def test_integration_prompt_without_local_findings_says_there_were_none():
    assert "ninguno" in mod.integration_prompt(TWO_FILES, [], message="m").lower()


def test_local_pass_cannot_see_the_cross_file_failure_in_its_context():
    """El fallo sembrado entre archivos: el diff de `core/sla.py` no trae a ningún llamador."""
    d = next(x for x in LABELS["seeded"] if x["id"] == "D")
    assert '"restante_minutos"' in CHANGE["commit_1"]["core/sla.py"] and "core/sla.py" not in d["callers"]
    assert "restante_horas" not in CHANGE["commit_1"]["core/sla.py"]


# --- esquemas ----------------------------------------------------------------------------------------------------------------------------

def test_findings_schema_adds_a_confidence_between_zero_and_one_to_each_finding_and_requires_it():
    item = mod.findings_schema()["properties"]["findings"]["items"]
    assert item["properties"]["confidence"] == {"type": "number", "minimum": 0, "maximum": 1}
    assert "confidence" in item["required"] and "detected_pattern" in item["required"]
    jsonschema.validate({"findings": [f()]}, mod.findings_schema())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"findings": [f(confidence=1.5)]}, mod.findings_schema())


def test_verification_schema_returns_a_confidence_per_finding_id():
    jsonschema.validate({"verdicts": [{"id": 0, "confidence": 0.7, "reason": "r"}]}, mod.verification_schema())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"verdicts": [{"id": 0, "confidence": 2, "reason": "r"}]}, mod.verification_schema())


def test_verification_prompt_numbers_the_findings_and_includes_the_diff():
    prompt = mod.verification_prompt(TWO_FILES, [f("a.py", 3), f("dir/b.py", 5)])
    assert "0 " in prompt and "1 " in prompt and "a.py:3" in prompt and "+q" in prompt


# --- fusión (evita los hallazgos contradictorios o repetidos) ----------------------------------------------------------------------------------

def test_merge_keeps_every_local_finding_and_the_integration_ones_marked_by_source():
    merged = mod.merge_findings({"a.py": [f("a.py", 1)], "dir/b.py": [f("dir/b.py", 4)]}, [f("a.py", 30, category="bug")])
    assert [(m["file"], m["source"]) for m in merged] == [("a.py", "file"), ("dir/b.py", "file"), ("a.py", "integration")]


def test_merge_drops_an_integration_finding_that_repeats_a_local_one():
    merged = mod.merge_findings({"a.py": [f("a.py", 10, confidence=0.6)]}, [f("a.py", 11, confidence=0.9)])
    assert len(merged) == 1 and merged[0]["source"] == "file"
    assert merged[0]["confidence"] == 0.9, "se conserva la confianza más alta de las dos"


def test_merge_does_not_join_findings_of_different_category_or_far_lines():
    merged = mod.merge_findings({"a.py": [f("a.py", 10)]}, [f("a.py", 10, category="security"), f("a.py", 40)])
    assert len(merged) == 3


def test_merge_of_nothing_is_empty():
    assert mod.merge_findings({}, []) == []


# --- las tres ramas: una diferencia cada una (4.6-K1, K2 · 3.6-K4) ----------------------------------------------------------------------------

def test_arms_share_the_same_prompts_and_only_the_explicit_one_adds_a_paragraph():
    base = mod.file_pass_prompt(mod.split_diff(TWO_FILES)["a.py"], message="m")
    explicit = mod.with_arm_note(base, "autorrevision_explicita")
    assert mod.with_arm_note(base, None) == base and mod.with_arm_note(base, "autorrevision") == base
    assert explicit.replace(mod.SELF_REVIEW_NOTE, "") == base
    assert "tu propio cambio" in mod.SELF_REVIEW_NOTE.lower()


def test_unknown_arm_is_rejected():
    with pytest.raises(ValueError):
        mod.with_arm_note("p", "otra")


def test_arm_session_independent_has_no_resume_and_self_review_forks_the_generator_session():
    assert mod.session_args(None, "S1") == {"resume": None, "fork": False}
    assert mod.session_args("autorrevision", "S1") == {"resume": "S1", "fork": True}
    assert mod.session_args("autorrevision_explicita", "S1") == {"resume": "S1", "fork": True}


# --- la sesión generadora y su coste ---------------------------------------------------------------------------------------------------------

def test_generator_prompt_gives_the_specification_and_the_exact_contents_and_asks_for_the_reasons():
    prompt = mod.generator_prompt(CHANGE)
    assert CHANGE["message_1"] in prompt
    for name, content in CHANGE["commit_1"].items():
        assert name in prompt and content in prompt
    assert "por qué" in prompt.lower() and "Write" in prompt


def test_generator_prompt_does_not_leak_labels():
    assert "SEMBRADO" not in mod.generator_prompt(CHANGE).upper() and "os.system" in mod.generator_prompt(CHANGE)


def test_generator_tools_can_write_but_the_review_tools_cannot():
    assert {"Write", "Edit"} <= set(mod.GENERATOR_TOOLS) and not ({"Write", "Edit"} & set(headless.READ_ONLY_TOOLS))


def test_each_fork_costs_its_own_part_only_and_the_branch_total_counts_the_generator_once():
    """Sonda C1: `total_cost_usd` de una sesión reanudada es acumulado. El tope de la rama lo lleva el Ledger."""
    ledger = headless.Ledger(limit_usd=1.0)
    generator = headless.HeadlessResult("ok", session_id="S", cost_usd=0.10)
    ledger.add(generator)
    reviews = [headless.HeadlessResult("ok", session_id=f"F{i}", cost_usd=0.10 + own) for i, own in enumerate((0.02, 0.03, 0.01))]
    owns = [ledger.add(r, resumed_from=generator) for r in reviews]
    assert owns == pytest.approx([0.02, 0.03, 0.01])
    assert ledger.spent == pytest.approx(0.16)


# --- confianza por hallazgo y su calibración (4.6-S3, reutiliza app3/10) ------------------------------------------------------------------------

def test_finding_cells_mark_a_finding_correct_when_it_matches_a_seeded_flaw():
    findings = [f("notificaciones/avisos.py", 20, category="security", confidence=0.95), f("x.py", 1, confidence=0.9)]
    cells = mod.finding_cells(findings, LABELS, scope=1)
    assert [(c.confidence, c.correct) for c in cells] == [(0.95, True), (0.9, False)]
    assert mod.m10.confidence_bands(cells, edges=(0.0, 0.5, 0.8, 1.01))[-1].accuracy == 0.5


def test_finding_cells_tolerate_a_missing_or_invalid_confidence():
    cells = mod.finding_cells([f("x.py", 1, confidence=None), {"file": "x.py", "line": 1}], LABELS, scope=1)
    assert all(c.confidence is None for c in cells)


def test_route_sends_low_confidence_findings_to_a_human_and_the_rest_to_publication():
    publish, human = mod.route_by_confidence([f(confidence=0.95), f(confidence=0.4), f(confidence=None)], threshold=0.8)
    assert [p["confidence"] for p in publish] == [0.95] and len(human) == 2


def test_overconfident_verification_is_visible_in_the_calibration_gap():
    """Control positivo: confianza 0,95 sobre hallazgos que no coinciden con nada sembrado da un hueco grande."""
    cells = mod.finding_cells([f("x.py", i, confidence=0.95) for i in range(1, 11)], LABELS, scope=1)
    assert mod.m10.calibration_gap(mod.m10.confidence_bands(cells)) > 0.9


# --- hallazgos por pasada y señal de K3 ---------------------------------------------------------------------------------------------------------

def test_found_by_pass_attributes_each_seeded_flaw_to_the_pass_that_reported_it():
    merged = [f("notificaciones/avisos.py", 20, category="security", source="file"), f("core/sla.py", 12, source="integration")]
    by = mod.found_by_pass(merged, LABELS, scope=1)
    assert by == {"file": {"B"}, "integration": {"D"}}
    # El fallo entre archivos F solo está a la vista con los dos trozos: lo que cita su uso en `avisos.py` cuenta si lo dice la integración.
    f_use = next(x for x in LABELS["seeded"] if x["id"] == "F")
    cross = [f(f_use["file"], f_use["line"], source="integration", problem="avance_plazo devuelve una fracción de 0 a 1 y aquí se imprime como porcentaje")]
    assert mod.found_by_pass(cross, LABELS, scope=1) == {"file": set(), "integration": {"F"}}


def test_a_flaw_reported_by_both_passes_counts_for_the_local_one():
    merged = mod.merge_findings({"core/sla.py": [f("core/sla.py", 12)]}, [f("core/sla.py", 12)])
    assert mod.found_by_pass(merged, LABELS, scope=1) == {"file": {"D"}, "integration": set()}


# --- repositorio y orden -------------------------------------------------------------------------------------------------------------------------

@pytest.mark.needs_git
def test_generator_repo_starts_at_the_base_without_the_change():
    repo = mod.build_generator_repo()
    assert "restante_horas" in (repo.path / "core" / "sla.py").read_text(encoding="utf-8")
    assert not mod.generated_diff(repo).strip()


@pytest.mark.needs_git
def test_generated_diff_matches_the_target_when_the_files_are_written_as_given():
    repo = mod.build_generator_repo()
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))
    assert mod.matches_target(repo, CHANGE)
    assert repo.target_diff == mod.generated_diff(repo)
    (repo.path / "config.py").write_text("distinto\n", encoding="utf-8")
    assert not mod.matches_target(repo, CHANGE)


@pytest.mark.needs_git
def test_pass_command_is_isolated_with_budget_schema_and_the_forked_session():
    repo = mod.build_generator_repo()
    cmd = mod.pass_command(repo.path, model="claude-sonnet-5-5", budget=0.2, schema=mod.findings_schema(), tools=(), session={"resume": "S1", "fork": True})
    assert cmd[cmd.index("--resume") + 1] == "S1" and "--fork-session" in cmd
    assert "--max-budget-usd" in cmd and cmd[cmd.index("--setting-sources") + 1] == "project"
    assert cmd[cmd.index("--tools") + 1] == ""


def test_apply_verdicts_replaces_the_confidence_and_keeps_the_declared_one():
    findings = [f(confidence=0.99), f(confidence=0.5)]
    out = mod.apply_verdicts(findings, [{"id": 0, "confidence": 0.3, "reason": "r"}])
    assert [o["confidence"] for o in out] == [0.3, None] and [o["declared_confidence"] for o in out] == [0.99, 0.5]
    assert mod.apply_verdicts(findings, [{"x": 1}, "mal"])[0]["confidence"] is None


@pytest.mark.needs_git
def test_mismatch_files_names_the_files_that_differ_from_the_given_content_and_any_extra_file():
    repo = mod.build_generator_repo()
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))
    assert mod.mismatch_files(repo, CHANGE) == []
    (repo.path / "config.py").write_text("distinto", encoding="utf-8")
    (repo.path / "extra.py").write_text("x = 1", encoding="utf-8")
    assert mod.mismatch_files(repo, CHANGE) == ["config.py", "extra.py"]

def write_given(repo):
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))


# --- (14) los archivos nuevos sin seguimiento cuentan en el diff ----------------------------------------------------------------

@pytest.mark.needs_git
def test_a_new_file_written_by_the_generator_shows_up_in_the_generated_diff():
    """Falso negativo de antes: `git diff base` no veía un archivo nuevo sin seguimiento y `matches_target` daba True."""
    repo = mod.build_generator_repo()
    write_given(repo)
    (repo.path / "tests" / "test_nuevo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    diff = mod.generated_diff(repo)
    assert "tests/test_nuevo.py" in diff and "+def test_x" in diff
    assert not mod.matches_target(repo, CHANGE), "el generador añadió un archivo que no estaba en el cambio dado"
    assert mod.mismatch_files(repo, CHANGE) == ["tests/test_nuevo.py"]


@pytest.mark.needs_git
def test_control_the_exact_change_still_matches_and_a_new_file_is_split_into_its_own_pass():
    repo = mod.build_generator_repo()
    write_given(repo)
    assert mod.matches_target(repo, CHANGE) and mod.mismatch_files(repo, CHANGE) == []
    (repo.path / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert "extra.py" in mod.split_diff(mod.generated_diff(repo)), "la pasada por archivo también revisa el archivo nuevo"


@pytest.mark.needs_git
def test_generated_diff_can_be_called_twice_with_the_same_result():
    repo = mod.build_generator_repo()
    write_given(repo)
    (repo.path / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert mod.generated_diff(repo) == mod.generated_diff(repo)


# --- (14) el repositorio del generador no guarda el futuro ----------------------------------------------------------------------

def git_out(path, *args):
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, encoding="utf-8", check=True).stdout


@pytest.mark.needs_git
def test_generator_repo_history_has_only_the_base_commit_and_its_reflog_shows_nothing_else():
    repo = mod.build_generator_repo()
    assert git_out(repo.path, "rev-list", "--all", "--count").strip() == "1"
    assert len(git_out(repo.path, "reflog").strip().splitlines()) == 1
    assert git_out(repo.path, "rev-parse", "HEAD").strip() == repo.base


@pytest.mark.needs_git
def test_no_file_under_dot_git_contains_the_messages_of_the_change():
    """El revisor tiene `Grep`: el mensaje del commit 2 no debe estar en el reflog ni en ningún otro archivo de `.git`."""
    repo = mod.build_generator_repo()
    for path in (repo.path / ".git").rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert CHANGE["message_2"].encode() not in data and CHANGE["message_1"].encode() not in data, path


@pytest.mark.needs_git
def test_the_target_diff_is_computed_apart_and_is_the_one_of_the_first_commit():
    repo = mod.build_generator_repo()
    full = m11.build_review_repo()
    assert repo.target_diff == m11.diff_of(full, full.base, full.commit_1)
    assert "debe_escalar_lote" in repo.target_diff


@pytest.mark.needs_git
def test_build_review_repo_can_stop_at_the_base():
    repo = m11.build_review_repo(commits=0)
    assert repo.commit_1 == "" and repo.commit_2 == ""
    assert git_out(repo.path, "rev-list", "--all", "--count").strip() == "1"
    assert m11.build_review_repo(commits=1).commit_2 == ""


def test_generator_prompt_forbids_extra_files():
    assert "ningún otro archivo" in mod.generator_prompt(CHANGE)


# --- (14) MERGE_WINDOW: dos hallazgos distintos del mismo archivo y categoría no se fusionan --------------------------------------

def test_two_different_findings_on_nearby_lines_of_the_same_file_and_category_are_both_kept():
    """Falso negativo de antes: el segundo hallazgo, de otro problema, se descartaba por estar a una línea del primero."""
    local = f("a.py", 10, problem="la división por cero con una lista vacía", detected_pattern="zero_division")
    other = f("a.py", 11, problem="el orden de los argumentos está intercambiado en la llamada", detected_pattern="arguments_swapped")
    merged = mod.merge_findings({"a.py": [local]}, [other])
    assert len(merged) == 2 and merged[1]["source"] == "integration"


def test_the_same_problem_in_other_words_is_still_merged_when_the_pattern_or_the_words_match():
    local = f("a.py", 10, problem="división por cero con lista vacía", detected_pattern="zero_division", confidence=0.5)
    by_pattern = f("a.py", 11, problem="algo distinto escrito de otra forma", detected_pattern="Zero Division", confidence=0.9)
    by_words = f("a.py", 12, problem="división por cero cuando la lista vacía llega aquí", detected_pattern="otro_nombre", confidence=0.7)
    merged = mod.merge_findings({"a.py": [local]}, [by_pattern, by_words])
    assert len(merged) == 1 and merged[0]["confidence"] == 0.9


def test_an_empty_pattern_never_counts_as_the_same_pattern():
    a = f("a.py", 10, problem="uno", detected_pattern="")
    b = f("a.py", 11, problem="dos", detected_pattern="")
    assert len(mod.merge_findings({"a.py": [a]}, [b])) == 2


# --- variante `una_pasada` (4.6-K3, S2): una sola cosa cambia, el reparto en pasadas -------------------------------------------------
# (TWO_FILES es el de arriba: el mismo texto estaba repetido en el archivo fusionado.)

def test_una_pasada_is_an_anti_variant_and_the_default_plan_is_unchanged():
    assert "una_pasada" in mod.ANTI_VARIANTS
    assert [p.kind for p in mod.plan_passes(TWO_FILES)] == ["file", "file", "integration"]
    assert [p.kind for p in mod.plan_passes(TWO_FILES, "autorrevision")] == ["file", "file", "integration"]


def test_una_pasada_has_one_pass_over_the_whole_diff_with_read_tools_and_no_file_or_integration_pass():
    plan = mod.plan_passes(TWO_FILES, "una_pasada")
    assert len(plan) == 1 and plan[0].kind == "single" and plan[0].chunk == TWO_FILES
    assert plan[0].tools == headless.READ_ONLY_TOOLS


def test_single_pass_prompt_has_the_whole_diff_the_same_criteria_and_nothing_about_other_passes():
    prompt = mod.single_pass_prompt(TWO_FILES, message="m")
    assert "+y" in prompt and "+q" in prompt and m11.CRITERIA in prompt and m11.FEW_SHOT in prompt
    assert "solo este archivo" not in prompt.lower() and "pasada de integración" not in prompt.lower()
    assert "confianza" in prompt.lower()


def test_una_pasada_uses_a_new_instance_not_the_generator_session():
    assert mod.session_args("una_pasada", "S1") == {"resume": None, "fork": False}
    assert mod.session_args(None, "S1") == {"resume": None, "fork": False}
    assert mod.session_args("autorrevision", "S1") == {"resume": "S1", "fork": True}
    assert mod.with_arm_note("p", "una_pasada") == "p"


@pytest.mark.needs_git
def test_una_pasada_command_is_isolated_read_only_with_budget_schema_and_no_resume():
    repo = mod.build_generator_repo()
    plan = mod.plan_passes(TWO_FILES, "una_pasada")
    cmd = mod.pass_command(repo.path, model="claude-sonnet-5-5", budget=0.2, schema=mod.findings_schema(), tools=plan[0].tools, session=mod.session_args("una_pasada", "S1"))
    assert "--resume" not in cmd and "--fork-session" not in cmd
    assert cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob" and "--max-budget-usd" in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert "confidence" in cmd[cmd.index("--json-schema") + 1]


def test_found_by_pass_of_a_single_pass_attributes_everything_to_it():
    merged = [f("notificaciones/avisos.py", 20, category="security", source="single"), f("core/sla.py", 12, source="single")]
    assert mod.found_by_pass(merged, LABELS, scope=1) == {"single": {"B", "D"}}


def test_found_by_pass_of_a_single_pass_without_findings_is_still_the_single_pass():
    # Antes se deducía la variante de los hallazgos: con la lista vacía caía en «por archivo / integración».
    assert mod.found_by_pass([], LABELS, scope=1, single=True) == {"single": set()}
    assert mod.found_by_pass([], LABELS, scope=1) == {"file": set(), "integration": set()}


def test_the_default_still_splits_found_by_pass_into_file_and_integration():
    merged = [f("notificaciones/avisos.py", 20, category="security", source="file"), f("core/sla.py", 12, source="integration")]
    assert mod.found_by_pass(merged, LABELS, scope=1) == {"file": {"B"}, "integration": {"D"}}


class Args:
    def __init__(self, anti=None, repeat=1):
        self.anti, self.repeat = anti, repeat


def fake_headless(monkeypatch, calls, findings):
    """Un `headless.run` falso: el generador escribe el cambio dado y cada pasada devuelve `findings` o la verificación."""

    def fake_run(cmd, prompt, *, cwd, schema, **kwargs):
        if schema is None:
            for name, content in CHANGE["commit_1"].items():
                (cwd / name).write_bytes(content.encode("utf-8"))
            calls.append(("generador", cmd))
            return headless.HeadlessResult("ok", session_id="GEN", cost_usd=0.01)
        if "verdicts" in schema["properties"]:
            calls.append(("verificacion", cmd))
            return headless.HeadlessResult("ok", structured={"verdicts": [{"id": i, "confidence": 0.9, "reason": "r"} for i in range(len(findings))]}, session_id="V", cost_usd=0.01)
        calls.append(("pasada", cmd))
        return headless.HeadlessResult("ok", structured={"findings": findings}, session_id="P", cost_usd=0.01)

    monkeypatch.setattr(mod.headless, "run", fake_run)


@pytest.mark.needs_git
def test_run_revision_una_pasada_makes_one_review_pass_and_then_the_verification(monkeypatch):
    calls = []
    finding = f("notificaciones/avisos.py", 20, category="security", confidence=0.9)
    fake_headless(monkeypatch, calls, [finding])
    mod.run_revision(Args("una_pasada"), "m", 5.0)
    kinds = [k for k, _ in calls]
    assert kinds == ["generador", "pasada", "verificacion"], kinds
    review = calls[1][1]
    assert "--resume" not in review and review[review.index("--tools") + 1] == "Read,Grep,Glob"


@pytest.mark.needs_git
def test_run_revision_default_still_makes_one_pass_per_file_plus_integration(monkeypatch):
    """Control del otro lado: sin `una_pasada` el reparto es el de siempre (4 archivos y la integración)."""
    calls = []
    fake_headless(monkeypatch, calls, [])
    mod.run_revision(Args(None), "m", 5.0)
    kinds = [k for k, _ in calls]
    assert kinds == ["generador", *(["pasada"] * (len(CHANGE["commit_1"]) + 1))], kinds
