"""Tests de app3/11 tras la revisión independiente (tanda C4, grupo 1): el árbol de cada revisión, la clave de un escenario de test con lo que espera y la coincidencia estricta por símbolo. Sin modelo."""

import shutil

import pytest

from harness.data import load
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


def score(findings, scope=1):
    return mod.score_findings(findings, LABELS, scope=scope)


# --- (1) cada revisión corre sobre un árbol en el commit que revisa ----------------------------------------------------------

def read_in(tree, name):
    return (tree / name).read_text(encoding="utf-8")


@pytestmark_git
def test_tree_at_the_first_commit_has_the_seeded_flaw_and_not_the_fix_nor_the_second_commit(repo):
    tree = mod.tree_at(repo, repo.commit_1)
    assert 'debe_escalar(t["horas"], t["prioridad"])' in read_in(tree, "tickets/escalado.py")
    assert 'debe_escalar(t["prioridad"], t["horas"])' not in read_in(tree, "tickets/escalado.py")
    assert "promedio_restante" not in read_in(tree, "informes/resumen.py"), "el bug del segundo commit aún no existe"


@pytestmark_git
def test_tree_at_the_second_commit_has_the_fix_and_the_new_bug(repo):
    """Control del otro lado: la segunda revisión sí revisa el estado final."""
    tree = mod.tree_at(repo, repo.commit_2)
    assert 'debe_escalar(t["prioridad"], t["horas"])' in read_in(tree, "tickets/escalado.py")
    assert "promedio_restante" in read_in(tree, "informes/resumen.py")


@pytestmark_git
def test_tree_at_does_not_touch_the_repo_and_is_a_new_directory_each_time(repo):
    before = read_in(repo.path, "tickets/escalado.py")
    first, second = mod.tree_at(repo, repo.commit_1), mod.tree_at(repo, repo.commit_1)
    assert first != second and first != repo.path
    assert read_in(repo.path, "tickets/escalado.py") == before and 'debe_escalar(t["prioridad"], t["horas"])' in before
    (first / "tickets" / "escalado.py").write_text("x", encoding="utf-8")
    assert read_in(second, "tickets/escalado.py") != "x", "ninguna copia comparte archivos con otra"


@pytestmark_git
def test_tree_at_has_no_git_history_to_read_the_future_from(repo):
    """El revisor tiene Grep y Read: sin `.git` no puede leer el mensaje del commit siguiente."""
    tree = mod.tree_at(repo, repo.commit_1)
    assert not (tree / ".git").exists() and (tree / "CLAUDE.md").is_file()
    assert not any(CHANGE["message_2"] in p.read_text(encoding="utf-8", errors="ignore") for p in tree.rglob("*") if p.is_file())


class Args:
    anti = None
    sin_categoria = None
    repeat = 1


def spy_on_headless_run(monkeypatch, seen):
    def fake_run(cmd, prompt, *, cwd, schema, **kwargs):
        seen.append({"cwd": cwd, "escalado": read_in(cwd, "tickets/escalado.py"), "resumen": read_in(cwd, "informes/resumen.py")})
        structured = {"findings": []} if "findings" in schema["properties"] else {"tests": []}
        return mod.headless.HeadlessResult("ok", structured=structured, cost_usd=0.01)

    monkeypatch.setattr(mod.headless, "run", fake_run)


@pytestmark_git
def test_run_revision_reviews_a_tree_at_the_first_commit_with_the_flaw(repo, monkeypatch):
    seen = []
    spy_on_headless_run(monkeypatch, seen)
    mod.run_revision(repo, Args(), "m", 1.0, mod.headless.Ledger(1.0))
    assert len(seen) == 1 and seen[0]["cwd"] != repo.path
    assert 'debe_escalar(t["horas"], t["prioridad"])' in seen[0]["escalado"] and "promedio_restante" not in seen[0]["resumen"]


@pytestmark_git
def test_run_rerevision_reviews_the_final_state_and_run_tests_the_first_commit(repo, monkeypatch):
    seen = []
    spy_on_headless_run(monkeypatch, seen)
    mod.run_rerevision(repo, Args(), "m", 1.0, mod.headless.Ledger(1.0))
    assert 'debe_escalar(t["prioridad"], t["horas"])' in seen[0]["escalado"] and "promedio_restante" in seen[0]["resumen"]
    seen.clear()
    mod.run_tests(repo, Args(), "m", 1.0, mod.headless.Ledger(1.0))
    assert 'debe_escalar(t["horas"], t["prioridad"])' in seen[0]["escalado"] and "promedio_restante" not in seen[0]["resumen"]


# --- (2) la clave de un escenario de test incluye lo que espera ----------------------------------------------------------------

def test_a_test_updated_to_the_new_unit_is_not_a_duplicate_of_the_old_one():
    """Falso positivo de antes: calcular_sla(alta, 3) esperando minutos contaba como repetido del test que espera horas."""
    hours = mod.scenario_key("calcular_sla", {"prioridad": "alta", "horas_abiertas": 3}, "restante_horas 5")
    minutes = mod.scenario_key("calcular_sla", {"prioridad": "alta", "horas_abiertas": 3}, "restante_minutos 300")
    assert hours != minutes


def test_the_same_expected_in_another_wording_is_still_the_same_scenario():
    """Falso negativo a evitar: «restante_horas: 5» y «restante_horas 5» son el mismo resultado."""
    a = mod.scenario_key("calcular_sla", {"prioridad": "alta", "horas_abiertas": 3}, "restante_horas 5")
    assert a == mod.scenario_key("CALCULAR_SLA", {"horas_abiertas": 3.0, "prioridad": "Alta"}, "restante_horas: 5")
    assert mod.scenario_key("calcular_sla", {"p": 1}, "ValueError") == mod.scenario_key("calcular_sla", {"p": 1}, "lanza ValueError")
    assert mod.scenario_key("f", {"x": 1}, "True") != mod.scenario_key("f", {"x": 1}, "False")


def test_nested_arguments_ignore_key_order_in_the_key():
    one = mod.scenario_key("horas_restantes", {"tickets": [{"ticket_id": "T1", "prioridad": "normal", "horas": 4}]}, "{'T1': 20}")
    two = mod.scenario_key("horas_restantes", {"tickets": [{"horas": 4, "ticket_id": "t1", "prioridad": "Normal"}]}, "{'T1': 20}")
    assert one == two


def test_score_tests_does_not_count_a_minutes_test_as_a_duplicate_but_does_count_the_stale_one():
    proposed = [
        {"function": "calcular_sla", "args": {"prioridad": "alta", "horas_abiertas": 3}, "expected": "restante_minutos 300"},
        {"function": "calcular_sla", "args": {"prioridad": "alta", "horas_abiertas": 3}, "expected": "restante_horas 5"},
        {"function": "horas_restantes", "args": {"tickets": [{"ticket_id": "T1", "prioridad": "normal", "horas": 4}]}, "expected": "{'T1': 20}"},
    ]
    result = mod.score_tests(proposed, LABELS)
    assert result.duplicates == 2 and result.new == 1, "el test con minutos es nuevo; los otros dos ya existen (con horas)"


def test_the_scenario_of_the_resumen_test_that_the_change_breaks_is_among_the_existing_ones():
    assert any(s["function"] == "horas_restantes" for s in LABELS["existing_scenarios"])
    assert all("expected" in s for s in LABELS["existing_scenarios"])


# --- (7) coincidencia por símbolo estricta -----------------------------------------------------------------------------------

def test_a_decoy_finding_that_names_a_flawed_symbol_of_the_same_file_stays_a_decoy():
    """Falso positivo de antes: un hallazgo sobre REINTENTOS que nombra NOTIF_TIMEOUT puntuaba como acierto de C."""
    decoy_line = next(d["line"] for d in LABELS["correct_changes"] if d["id"] == "OK-1")
    result = score([finding(file="config.py", line=decoy_line, category="comment", severity="minor", pattern="x",
                            problem="REINTENTOS sube a 5; compáralo con NOTIF_TIMEOUT")])
    assert result.found == set() and len(result.flagged_ok) == 1 and result.false_positives == []


def test_the_flaw_is_still_found_by_its_own_line_or_by_its_symbol_far_from_it():
    c_line = next(f["line"] for f in LABELS["seeded"] if f["id"] == "C")
    assert score([finding(file="config.py", line=c_line, category="comment", severity="minor")]).found == {"C"}
    assert score([finding(file="config.py", line=60, category="comment", severity="minor", problem="NOTIF_TIMEOUT contradice su comentario")]).found == {"C"}


def test_a_symbol_inside_a_longer_name_does_not_count():
    """`TIMEOUT` suelto no es `NOTIF_TIMEOUT` y `os.systematic` no es `os.system`."""
    assert score([finding(file="config.py", line=60, category="comment", severity="minor", problem="el TIMEOUT de la API")]).found == set()
    assert score([finding(file="notificaciones/avisos.py", line=60, problem="usa os.systematic")]).found == set()
