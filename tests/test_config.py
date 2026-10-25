"""Tests de `harness/config.py`: prioridad `.env` > entorno > defecto, vacíos descartados y presupuesto positivo. Sin modelo."""

import pytest

from harness.config import (
    BUDGET_DEFAULTS,
    BUDGET_VARS,
    MODEL_DEFAULTS,
    MODEL_VARS,
    describe,
    resolve_budget,
    resolve_model,
)


def write_env(tmp_path, text):
    (tmp_path / ".env").write_text(text, encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Ningún test depende de lo que haya exportado quien ejecuta pytest.
    for name in [*MODEL_VARS.values(), *BUDGET_VARS.values()]:
        monkeypatch.delenv(name, raising=False)


def test_defaults_without_env_or_dotenv(tmp_path):
    for role, default in MODEL_DEFAULTS.items():
        assert resolve_model(role, root=tmp_path) == (default, "defecto")
    for kind, default in BUDGET_DEFAULTS.items():
        assert resolve_budget(kind, root=tmp_path) == (default, "defecto")


def test_dotenv_wins_over_process_env(tmp_path, monkeypatch):
    write_env(tmp_path, "CCARF_MODEL_AGENT=modelo-del-repo\nCCARF_BUDGET_AGENT=0.10\n")
    monkeypatch.setenv("CCARF_MODEL_AGENT", "modelo-de-la-shell")
    monkeypatch.setenv("CCARF_BUDGET_AGENT", "3")
    assert resolve_model("agent", root=tmp_path) == ("modelo-del-repo", ".env")
    assert resolve_budget("agent", root=tmp_path) == (0.10, ".env")


def test_enforcement_role_is_independent_of_agent(tmp_path):
    # app2/01 necesita un modelo que falle más sin cambiar el del resto de módulos.
    write_env(tmp_path, "CCARF_MODEL_AGENT=claude-haiku-5-5\n")
    assert resolve_model("enforcement", root=tmp_path) == ("claude-haiku-4-5", "defecto")
    write_env(tmp_path, "CCARF_MODEL_ENFORCEMENT=otro\n")
    assert resolve_model("enforcement", root=tmp_path) == ("otro", ".env")
    assert resolve_model("agent", root=tmp_path) == ("claude-haiku-5-5", "defecto")


def test_enforcement_budget_is_independent_of_agent(tmp_path):
    write_env(tmp_path, "CCARF_BUDGET_AGENT=0.10\n")
    assert resolve_budget("enforcement", root=tmp_path) == (0.50, "defecto")
    write_env(tmp_path, "CCARF_BUDGET_ENFORCEMENT=0.80\n")
    assert resolve_budget("enforcement", root=tmp_path) == (0.80, ".env")
    assert resolve_budget("agent", root=tmp_path) == (0.25, "defecto")


def test_process_env_used_when_dotenv_lacks_key(tmp_path, monkeypatch):
    write_env(tmp_path, "# sin claves CCARF\n")
    monkeypatch.setenv("CCARF_MODEL_SUBAGENT", "modelo-de-la-shell")
    assert resolve_model("subagent", root=tmp_path) == ("modelo-de-la-shell", "entorno")


def test_empty_values_are_skipped(tmp_path, monkeypatch):
    write_env(tmp_path, "CCARF_MODEL_COORDINATOR=\nCCARF_BUDGET_MULTIAGENT=''\n")
    monkeypatch.setenv("CCARF_MODEL_COORDINATOR", "   ")
    assert resolve_model("coordinator", root=tmp_path) == (MODEL_DEFAULTS["coordinator"], "defecto")
    assert resolve_budget("multiagent", root=tmp_path) == (BUDGET_DEFAULTS["multiagent"], "defecto")


@pytest.mark.parametrize("value", ["0", "-1", "gratis", "nan", "inf"])
def test_budget_must_be_positive_amount(tmp_path, value):
    write_env(tmp_path, f"CCARF_BUDGET_AGENT={value}\n")
    with pytest.raises(ValueError):
        resolve_budget("agent", root=tmp_path)


def test_unknown_role_or_kind_fails(tmp_path):
    with pytest.raises(KeyError):
        resolve_model("revisor", root=tmp_path)
    with pytest.raises(KeyError):
        resolve_budget("batch", root=tmp_path)


def test_describe_lines():
    assert describe("modelo", rol="agent", valor="claude-haiku-5-5", origen=".env") == (
        "[modelo] rol=agent valor=claude-haiku-5-5 origen=.env"
    )
    assert describe("presupuesto", valor=0.25, origen="defecto") == "[presupuesto] valor=0.25 origen=defecto"
