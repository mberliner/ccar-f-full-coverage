"""Tests de app3/12_revision_independiente: reparto de pasadas, prompts de cada rama (una diferencia), fusión de hallazgos, confianza y coste de la sesión reanudada. Sin modelo."""

import shutil

import jsonschema
import pytest

from harness import headless
from harness.data import load
from tests.cargar import load as load_module

mod = load_module("app3_sistema_multiagente/12_revision_independiente.py")
m11 = mod.m11
LABELS = load("cambio_revision_etiquetas.json")
CHANGE = load("cambio_revision.json")
pytestmark_git = pytest.mark.skipif(shutil.which("git") is None, reason="necesita git")

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

@pytestmark_git
def test_generator_repo_starts_at_the_base_without_the_change():
    repo = mod.build_generator_repo()
    assert "restante_horas" in (repo.path / "core" / "sla.py").read_text(encoding="utf-8")
    assert not mod.generated_diff(repo).strip()


@pytestmark_git
def test_generated_diff_matches_the_target_when_the_files_are_written_as_given():
    repo = mod.build_generator_repo()
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))
    assert mod.matches_target(repo, CHANGE)
    assert m11.diff_of(repo, repo.base, repo.commit_1) == mod.generated_diff(repo)
    (repo.path / "config.py").write_text("distinto\n", encoding="utf-8")
    assert not mod.matches_target(repo, CHANGE)


@pytestmark_git
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


@pytestmark_git
def test_mismatch_files_names_the_files_that_differ_from_the_given_content_and_any_extra_file():
    repo = mod.build_generator_repo()
    for name, content in CHANGE["commit_1"].items():
        (repo.path / name).write_bytes(content.encode("utf-8"))
    assert mod.mismatch_files(repo, CHANGE) == []
    (repo.path / "config.py").write_text("distinto", encoding="utf-8")
    (repo.path / "extra.py").write_text("x = 1", encoding="utf-8")
    assert mod.mismatch_files(repo, CHANGE) == ["config.py", "extra.py"]
