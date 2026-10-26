"""Tests de app1/06_mcp_config: `.mcp.json` generado, comando de ámbito de usuario, archivos de artículos, contadores de llamadas, agrupación de tools por servidor y opciones por parte. Sin modelo."""

import json
from pathlib import Path

import pytest

from harness.data import copy_to_temp, load
from harness.recorder import RunRecord, ToolCall
from tests.cargar import ROOT
from tests.cargar import load as load_module

mod = load_module("app1_agente_unico/06_mcp_config.py")


def call(name, text="{}", error=False):
    return ToolCall(f"id-{name}", name, {}, "r1", "principal", True, error, text)


# --- .mcp.json generado --------------------------------------------------------------

def test_mcp_json_has_two_stdio_servers_launched_with_uv():
    config = mod.build_mcp_json(ROOT)
    assert set(config["mcpServers"]) == {"catalogo", "inventario"}
    for server in config["mcpServers"].values():
        assert server["command"] == "uv"
        assert server["args"][:4] == ["run", "--no-sync", "--project", str(ROOT)]
        assert server["args"][4] == "python" and Path(server["args"][5]).is_file()


def test_token_is_an_unexpanded_variable_and_the_value_never_reaches_the_file():
    config = mod.build_mcp_json(ROOT)
    assert config["mcpServers"]["catalogo"]["env"]["CATALOGO_TOKEN"] == "${CCARF_DEMO_TOKEN}"
    assert mod.DEMO_TOKEN not in json.dumps(config)
    assert "env" not in config["mcpServers"]["inventario"]


def test_minimal_description_variant_goes_in_the_server_env():
    assert "CATALOGO_DESCRIPCION" not in mod.build_mcp_json(ROOT)["mcpServers"]["catalogo"]["env"]
    minimal = mod.build_mcp_json(ROOT, descripcion="minima")["mcpServers"]["catalogo"]["env"]
    assert minimal["CATALOGO_DESCRIPCION"] == "minima" and minimal["CATALOGO_TOKEN"] == "${CCARF_DEMO_TOKEN}"


def test_write_mcp_json_writes_into_the_cwd(tmp_path):
    mod.write_mcp_json(tmp_path, descripcion=None)
    assert json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8")) == mod.build_mcp_json(ROOT)


def test_user_scope_command_is_text_and_names_the_user_scope():
    command = mod.user_scope_command(ROOT)
    assert command.startswith("claude mcp add --scope user ")
    assert "catalogo_stdio.py" in command and "--no-sync" in command
    # Solo se imprime: el módulo no ejecuta nada ni toca `~/.claude.json`.
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "subprocess" not in source and "os.system" not in source


# --- artículos como archivos (parte descripcion) --------------------------------------

def test_write_articles_creates_one_file_per_article(tmp_path):
    mod.write_articles(tmp_path)
    articles = load("articulos_kb.json")
    files = sorted((tmp_path / "articulos").glob("*.md"))
    assert len(files) == len(articles)
    old = next(a for a in articles if a["superseded_by"])
    text = (tmp_path / "articulos" / f"{old['article_id']}.md").read_text(encoding="utf-8")
    assert old["title"] in text and old["superseded_by"] in text


# --- contadores y agrupación ------------------------------------------------------------

def test_data_calls_count_search_and_get_article_only():
    rec = RunRecord(tool_calls=[
        call("mcp__catalogo__search_kb"), call("mcp__catalogo__get_article"), call("mcp__catalogo__get_article"),
        call("ListMcpResourcesTool"), call("mcp__catalogo__token_status"), call("Grep"),
    ])
    assert mod.data_calls(rec) == 3
    assert mod.resource_calls(rec) == 1
    assert mod.data_calls(RunRecord()) == 0


def test_grep_versus_mcp_search():
    rec = RunRecord(tool_calls=[call("Grep"), call("Grep"), call("mcp__catalogo__search_kb"), call("Read")])
    assert mod.grep_vs_mcp(rec) == (2, 1)
    assert mod.grep_vs_mcp(RunRecord()) == (0, 0)


def test_tools_by_server_groups_mcp_tools_and_separates_builtins():
    tools = ["mcp__catalogo__search_kb", "mcp__catalogo__get_article", "mcp__inventario__stock_equipo",
             "mcp__mesa__get_ticket", "ListMcpResourcesTool", "Read"]
    servers, builtins = mod.tools_by_server(tools)
    assert servers == {"catalogo": ["get_article", "search_kb"], "inventario": ["stock_equipo"], "mesa": ["get_ticket"]}
    assert builtins == ["ListMcpResourcesTool", "Read"]


def test_servers_without_tools_in_init_flags_a_partial_list():
    # Un servidor stdio puede constar como conectado cuando `init` aún no trae sus tools.
    init = {
        "mcp_servers": [{"name": "catalogo", "status": "connected"}, {"name": "mesa", "status": "connected"},
                        {"name": "roto", "status": "failed"}],
        "tools": ["mcp__mesa__get_ticket"],
    }
    assert mod.servers_without_tools(init) == ["catalogo"]  # `roto` no cuenta: no está conectado
    full = {**init, "tools": ["mcp__mesa__get_ticket", "mcp__catalogo__search_kb"]}
    assert mod.servers_without_tools(full) == []
    assert mod.servers_without_tools({}) == []


def test_token_received_reads_the_servers_answer_without_the_value():
    ok = RunRecord(tool_calls=[call("mcp__catalogo__token_status", '{"token_recibido":true}')])
    no = RunRecord(tool_calls=[call("mcp__catalogo__token_status", '{"token_recibido":false}')])
    assert mod.token_received(ok) is True and mod.token_received(no) is False
    assert mod.token_received(RunRecord()) is None


# --- opciones por parte -------------------------------------------------------------------

def opts(part, anti=None):
    cwd = copy_to_temp("repo_mesa")
    return mod.build_options(part, anti, cwd=cwd, budget=0.1, model="m"), cwd


def test_options_use_the_project_scope_exception_and_a_synthetic_token():
    options, cwd = opts("conexion")
    assert options.setting_sources == ["project"] and options.cwd == str(cwd)
    assert options.env["CCARF_DEMO_TOKEN"] == mod.DEMO_TOKEN and options.max_budget_usd == 0.1
    assert options.permission_mode == "dontAsk"


def test_conexion_adds_the_in_process_server_next_to_the_stdio_ones():
    options, _ = opts("conexion")
    assert "mesa" in options.mcp_servers and options.tools == []
    assert "mcp__catalogo__token_status" in options.allowed_tools and "mcp__inventario__stock_equipo" in options.allowed_tools
    assert "mcp__mesa__get_ticket" in options.allowed_tools


def test_recursos_gives_the_resource_tools_and_a_hint_except_in_the_anti():
    options, _ = opts("recursos")
    assert options.tools == ["ListMcpResourcesTool", "ReadMcpResourceTool"]
    assert "ListMcpResourcesTool" in options.system_prompt and "mesa" not in options.mcp_servers
    anti, _ = opts("recursos", "sin_recursos")
    assert anti.tools == [] and "resource" not in anti.system_prompt.lower()


def test_descripcion_gives_grep_and_read_and_writes_the_articles_and_mcp_json():
    options, cwd = opts("descripcion")
    assert set(options.tools) == {"Grep", "Read"} and "Grep" in options.allowed_tools
    assert (cwd / ".mcp.json").is_file() and any((cwd / "articulos").glob("*.md"))
    assert "CATALOGO_DESCRIPCION" not in json.loads((cwd / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["catalogo"]["env"]
    _, anti_cwd = opts("descripcion", "descripcion_minima")
    assert json.loads((anti_cwd / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["catalogo"]["env"]["CATALOGO_DESCRIPCION"] == "minima"


def test_variants_belong_to_their_part():
    assert mod.ANTI_PART == {"sin_recursos": "recursos", "descripcion_minima": "descripcion"}
    assert mod.PARTS == ["conexion", "recursos", "descripcion"]


def test_prompts_exist_for_every_part():
    for part in mod.PARTS:
        assert mod.PROMPTS[part].strip()
    assert "VPN" in mod.PROMPTS["descripcion"]


def test_unknown_part_fails():
    with pytest.raises(ValueError):
        mod.build_options("otra", None, cwd=Path("."), budget=0.1, model="m")
