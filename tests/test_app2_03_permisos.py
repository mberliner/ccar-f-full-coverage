"""Tests de app2/03_permisos: cada configuración construye lo que dice el README. Sin modelo."""

import pytest

from app2_agente_con_control.servers.helpdesk import HelpdeskState
from tests.cargar import load

mod = load("app2_agente_con_control/03_permisos.py")


def build(config):
    return mod.build_options(config, budget=0.05, model="m", subagent_model="s", state=HelpdeskState())


def test_allowed_preapproves_without_removing():
    options = build("allowed")
    assert mod.PAY not in options.allowed_tools and options.disallowed_tools == []
    assert options.permission_mode is None


def test_disallowed_removes_the_tool():
    options = build("disallowed")
    assert options.disallowed_tools == [mod.PAY]


def test_dont_ask_denies_unlisted():
    options = build("dontAsk")
    assert options.permission_mode == "dontAsk" and mod.PAY not in options.allowed_tools


def test_subagent_inherits_parent_mode():
    options = build("subagente")
    assert options.permission_mode == "dontAsk" and "Agent" in options.allowed_tools
    assert options.tools == ["Agent"]
    agent = options.agents["pagos"]
    # El subagente declara la tool, pero el modo del padre decide.
    assert mod.PAY in agent.tools and agent.permissionMode is None and agent.model == "s"


@pytest.mark.parametrize("config", mod.CONFIGS)
def test_every_config_is_isolated_and_budgeted(config):
    options = build(config)
    assert options.setting_sources == [] and options.max_budget_usd == 0.05
    assert set(options.mcp_servers) == {"helpdesk"}
