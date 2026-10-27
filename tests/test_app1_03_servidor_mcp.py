"""Tests de app1/03_servidor_mcp: batería de peticiones, acierto de enrutamiento sobre la primera llamada MCP y configuración por variante. Sin modelo."""

from harness.data import load
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load as load_module

mod = load_module("app1_agente_unico/03_servidor_mcp.py")

SPLIT = {"extract_ticket_facts", "extract_article_steps", "summarize_article", "verify_claim_against_article"}


def call(name, response="r1"):
    return ToolCall(f"id-{name}-{response}", name, {}, response, "principal", True, False, "x")


# --- batería -------------------------------------------------------------------

def test_battery_has_six_requests_with_real_ids():
    assert len(mod.BATTERY) == 6
    ticket_ids = {t["ticket_id"] for t in load("tickets.json")}
    article_ids = {a["article_id"] for a in load("articulos_kb.json")}
    for request in mod.BATTERY:
        ids = [word.strip(".,:«»?") for word in request.prompt.split()]
        assert any(i in ticket_ids or i in article_ids for i in ids), request.label


def test_expected_tools_cover_each_split_tool():
    assert {r.expected for r in mod.BATTERY} == SPLIT
    assert [r.expected for r in mod.BATTERY].count("verify_claim_against_article") == 2


def test_expected_tool_depends_on_the_configuration():
    request = next(r for r in mod.BATTERY if r.expected == "extract_article_steps")
    assert mod.expected_for(request, None) == "extract_article_steps"
    assert mod.expected_for(request, "palabra_clave") == "extract_article_steps"
    # Con las dos tools solapadas, lo esperable es «tickets → contenido, artículos → documento».
    assert mod.expected_for(request, "minimas") == "analyze_document"
    ticket = next(r for r in mod.BATTERY if r.expected == "extract_ticket_facts")
    assert mod.expected_for(ticket, "minimas") == "analyze_content"


def test_keyword_trap_hits_exactly_two_requests_that_do_not_expect_summarize():
    hit = [r for r in mod.BATTERY if mod.TRAP_WORD in r.prompt.lower()]
    assert len(hit) == 2
    assert all(r.expected != "summarize_article" for r in hit)
    # La petición de resumen sí espera `summarize_article`, y no lleva la palabra: nada que anular.
    assert all(mod.TRAP_WORD not in r.prompt.lower() for r in mod.BATTERY if r.expected == "summarize_article")


# --- medida ------------------------------------------------------------------------

def test_first_mcp_call_ignores_other_tools_and_later_calls():
    rec = RunRecord(tool_calls=[call("Read"), call("mcp__mesa__summarize_article"), call("mcp__mesa__extract_article_steps", "r2")])
    assert mod.first_mcp_call(rec) == "summarize_article"
    assert mod.first_mcp_call(RunRecord()) is None
    assert mod.first_mcp_call(RunRecord(tool_calls=[call("Grep")])) is None


def test_accuracy_counts_hits_and_treats_no_call_as_a_miss():
    results = [("a", "a"), ("b", "a"), (None, "a"), ("c", "c")]
    assert mod.accuracy(results) == (2, 4)
    assert mod.accuracy([]) == (0, 0)


def test_rate_text():
    assert mod.rate_text((5, 6)) == "5/6 (83 %)"
    assert mod.rate_text((0, 0)) == "sin datos"


def test_model_role_is_chosen_by_role_so_the_env_stays_the_source_of_the_model():
    # La señal de cada variante depende del modelo (`minimas` se ve con el rol `enforcement`, `palabra_clave` con `agent`):
    # se elige el ROL, nunca el nombre del modelo, que sigue saliendo de `.env` (harness/config.py).
    from harness import config

    assert mod.MODEL_ROLES == ["agent", "enforcement"]
    for role in mod.MODEL_ROLES:
        assert role in config.MODEL_DEFAULTS and role in config.BUDGET_DEFAULTS


# --- configuración -----------------------------------------------------------------

def test_variants():
    assert mod.ANTI_VARIANTS == ["minimas", "palabra_clave"]
    assert mod.tool_variant(None) is None and mod.tool_variant("palabra_clave") is None
    assert mod.tool_variant("minimas") == "minimas"


def test_system_prompt_has_the_keyword_rule_only_in_palabra_clave():
    assert mod.TRAP_WORD in mod.system_prompt("palabra_clave").lower()
    assert "summarize_article" in mod.system_prompt("palabra_clave")
    for anti in (None, "minimas"):
        assert mod.TRAP_WORD not in mod.system_prompt(anti).lower() and "summarize_article" not in mod.system_prompt(anti)


def test_options_expose_only_the_mcp_tools_with_budget_and_isolation():
    options = mod.build_options(None, budget=0.1, model="m")
    assert options.tools == [] and options.setting_sources == [] and options.max_budget_usd == 0.1
    assert set(options.allowed_tools) == {f"mcp__mesa__{n}" for n in SPLIT}
    assert options.permission_mode == "dontAsk" and "mesa" in options.mcp_servers
    minimal = mod.build_options("minimas", budget=0.1, model="m")
    assert set(minimal.allowed_tools) == {"mcp__mesa__analyze_content", "mcp__mesa__analyze_document"}
