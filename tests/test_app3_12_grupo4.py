"""Tests de app3/12 tras la revisión independiente (tanda C4, grupo 4): archivos nuevos en el diff generado, repositorio generador sin el futuro, fusión de hallazgos distintos y la variante `una_pasada`. Sin modelo."""

import shutil
import subprocess

import pytest

from harness import headless
from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/12_revision_independiente.py")
m11 = mod.m11
LABELS = load("cambio_revision_etiquetas.json")
CHANGE = load("cambio_revision.json")
pytestmark_git = pytest.mark.skipif(shutil.which("git") is None, reason="necesita git")


def f(file="a.py", line=1, category="bug", confidence=0.9, **extra):
    return {"file": file, "line": line, "category": category, "severity": "major", "problem": "p", "suggested_fix": "x", "detected_pattern": "pat", "confidence": confidence, **extra}


def write_given(repo):
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))


# --- (14) los archivos nuevos sin seguimiento cuentan en el diff ----------------------------------------------------------------

@pytestmark_git
def test_a_new_file_written_by_the_generator_shows_up_in_the_generated_diff():
    """Falso negativo de antes: `git diff base` no veía un archivo nuevo sin seguimiento y `matches_target` daba True."""
    repo = mod.build_generator_repo()
    write_given(repo)
    (repo.path / "tests" / "test_nuevo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    diff = mod.generated_diff(repo)
    assert "tests/test_nuevo.py" in diff and "+def test_x" in diff
    assert not mod.matches_target(repo, CHANGE), "el generador añadió un archivo que no estaba en el cambio dado"
    assert mod.mismatch_files(repo, CHANGE) == ["tests/test_nuevo.py"]


@pytestmark_git
def test_control_the_exact_change_still_matches_and_a_new_file_is_split_into_its_own_pass():
    repo = mod.build_generator_repo()
    write_given(repo)
    assert mod.matches_target(repo, CHANGE) and mod.mismatch_files(repo, CHANGE) == []
    (repo.path / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert "extra.py" in mod.split_diff(mod.generated_diff(repo)), "la pasada por archivo también revisa el archivo nuevo"


@pytestmark_git
def test_generated_diff_can_be_called_twice_with_the_same_result():
    repo = mod.build_generator_repo()
    write_given(repo)
    (repo.path / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert mod.generated_diff(repo) == mod.generated_diff(repo)


# --- (14) el repositorio del generador no guarda el futuro ----------------------------------------------------------------------

def git_out(path, *args):
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, encoding="utf-8", check=True).stdout


@pytestmark_git
def test_generator_repo_history_has_only_the_base_commit_and_its_reflog_shows_nothing_else():
    repo = mod.build_generator_repo()
    assert git_out(repo.path, "rev-list", "--all", "--count").strip() == "1"
    assert len(git_out(repo.path, "reflog").strip().splitlines()) == 1
    assert git_out(repo.path, "rev-parse", "HEAD").strip() == repo.base


@pytestmark_git
def test_no_file_under_dot_git_contains_the_messages_of_the_change():
    """El revisor tiene `Grep`: el mensaje del commit 2 no debe estar en el reflog ni en ningún otro archivo de `.git`."""
    repo = mod.build_generator_repo()
    for path in (repo.path / ".git").rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert CHANGE["message_2"].encode() not in data and CHANGE["message_1"].encode() not in data, path


@pytestmark_git
def test_the_target_diff_is_computed_apart_and_is_the_one_of_the_first_commit():
    repo = mod.build_generator_repo()
    full = m11.build_review_repo()
    assert repo.target_diff == m11.diff_of(full, full.base, full.commit_1)
    assert "debe_escalar_lote" in repo.target_diff


@pytestmark_git
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

TWO_FILES = (
    "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"
    "diff --git a/dir/b.py b/dir/b.py\n--- a/dir/b.py\n+++ b/dir/b.py\n@@ -1 +1 @@\n-p\n+q\n"
)


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


@pytestmark_git
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


@pytestmark_git
def test_run_revision_una_pasada_makes_one_review_pass_and_then_the_verification(monkeypatch):
    calls = []
    finding = f("notificaciones/avisos.py", 20, category="security", confidence=0.9)
    fake_headless(monkeypatch, calls, [finding])
    mod.run_revision(Args("una_pasada"), "m", 5.0)
    kinds = [k for k, _ in calls]
    assert kinds == ["generador", "pasada", "verificacion"], kinds
    review = calls[1][1]
    assert "--resume" not in review and review[review.index("--tools") + 1] == "Read,Grep,Glob"


@pytestmark_git
def test_run_revision_default_still_makes_one_pass_per_file_plus_integration(monkeypatch):
    """Control del otro lado: sin `una_pasada` el reparto es el de siempre (4 archivos y la integración)."""
    calls = []
    fake_headless(monkeypatch, calls, [])
    mod.run_revision(Args(None), "m", 5.0)
    kinds = [k for k, _ in calls]
    assert kinds == ["generador", *(["pasada"] * (len(CHANGE["commit_1"]) + 1))], kinds
