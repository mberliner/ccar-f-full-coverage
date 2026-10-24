"""Tests de `harness/options.py`: aislamiento por defecto y presupuesto obligatorio. Sin modelo."""

import pytest

from harness.options import ISOLATION_ENV, isolated_options


def test_isolation_by_default():
    options = isolated_options(max_budget_usd=0.05)
    assert options.setting_sources == []
    assert options.env == ISOLATION_ENV
    assert options.max_budget_usd == 0.05


def test_module_env_is_merged_not_replaced():
    options = isolated_options(max_budget_usd=0.05, env={"EXAMPLE_FLAG": "false"})
    assert options.env == {**ISOLATION_ENV, "EXAMPLE_FLAG": "false"}


def test_module_can_override_any_value():
    options = isolated_options(
        max_budget_usd=0.05,
        setting_sources=["project"],
        env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "0"},
        allowed_tools=["Read"],
        max_turns=5,
    )
    assert options.setting_sources == ["project"]
    assert options.env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "0"
    assert options.allowed_tools == ["Read"]
    assert options.max_turns == 5


@pytest.mark.parametrize("budget", [0, -1, None])
def test_budget_is_required(budget):
    with pytest.raises(ValueError):
        isolated_options(max_budget_usd=budget)
    with pytest.raises(TypeError):
        isolated_options()  # type: ignore[call-arg]
