"""Tests de app1/04_errores_estructurados: lectura de errores del RunRecord, reintentos útiles e inútiles, detección de «no hay datos» y configuración por variante. Sin modelo."""

import json

from app1_agente_unico.servers.mesa import ErroresState
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app1_agente_unico/04_errores_estructurados.py")

TRANSIENT = json.dumps({"errorCategory": "transient", "isRetryable": True, "message": "timeout"})
BUSINESS = json.dumps({"errorCategory": "business", "isRetryable": False, "message": "supera el cupo"})
VALIDATION = json.dumps({"errorCategory": "validation", "isRetryable": False, "message": "ID mal formado"})
PERMISSION = json.dumps({"errorCategory": "permission", "isRetryable": False, "message": "sin permiso"})


def call(n, tool, args, *, error=False, text="{}"):
    return ToolCall(f"id{n}", f"mcp__mesa__{tool}", args, "r1", "principal", True, error, text)


def record(*calls):
    return RunRecord(tool_calls=list(calls))


# --- categoría del error ----------------------------------------------------------

def test_error_category_from_structured_text():
    assert mod.error_category(TRANSIENT) == "transient"
    assert mod.error_category(BUSINESS) == "business"


def test_generic_and_unparseable_errors_have_no_category():
    assert mod.error_category("Operation failed") == "sin categoría"
    assert mod.error_category(None) == "sin categoría"
    assert mod.error_category(json.dumps({"ok": True})) == "sin categoría"


# --- análisis del registro --------------------------------------------------------

GOOD = record(
    call(1, "fetch_ticket_history", {"ticket_id": "TCK-4001"}, error=True, text=TRANSIENT),
    call(2, "fetch_ticket_history", {"ticket_id": "TCK-4001"}, text='{"events": [1]}'),
    call(3, "get_user_profile", {"user_id": "1001"}, error=True, text=VALIDATION),
    call(4, "get_user_profile", {"user_id": "EMP-1001"}, text="{}"),  # entrada corregida: no es un reintento ciego
    call(5, "reassign_license", {"user_id": "EMP-1001", "license": "editor", "seats": "12"}, error=True, text=BUSINESS),
    call(6, "export_audit_log", {"scope": "all"}, error=True, text=PERMISSION),
    call(7, "search_tickets_by_user", {"user_id": "EMP-9999"}, text='{"tickets": []}'),
)
USELESS = record(
    call(1, "reassign_license", {"seats": "12"}, error=True, text="Operation failed"),
    call(2, "reassign_license", {"seats": "12"}, error=True, text="Operation failed"),
    call(3, "reassign_license", {"seats": "12"}, error=True, text="Operation failed"),
    call(4, "export_audit_log", {"scope": "all"}, error=True, text="Operation failed"),
    call(5, "export_audit_log", {"scope": "all"}, error=True, text="Operation failed"),
)


def test_analyze_counts_calls_and_categories():
    analysis = mod.analyze(GOOD)
    assert analysis.calls["fetch_ticket_history"] == 2 and analysis.calls["reassign_license"] == 1
    assert analysis.categories["fetch_ticket_history"] == ["transient", None]
    assert analysis.categories["get_user_profile"] == ["validation", None]
    assert analysis.categories["export_audit_log"] == ["permission"]


def test_retry_is_an_identical_call_after_an_error():
    analysis = mod.analyze(GOOD)
    assert analysis.retries["fetch_ticket_history"] == 1
    # Corregir la entrada tras un error de validación no es reintentar a ciegas.
    assert analysis.retries.get("get_user_profile", 0) == 0
    assert analysis.retries.get("reassign_license", 0) == 0


def test_blind_repeats_of_a_failing_call_count_as_retries():
    analysis = mod.analyze(USELESS)
    assert analysis.retries == {"reassign_license": 2, "export_audit_log": 1}


def test_useless_retries_only_count_non_retryable_tools():
    assert mod.useless_retries(mod.analyze(GOOD)) == 0  # el reintento del transitorio es útil
    assert mod.useless_retries(mod.analyze(USELESS)) == 3


def test_transient_recovered_needs_a_retry_that_succeeds():
    assert mod.transient_recovered(GOOD) is True
    no_retry = record(call(1, "fetch_ticket_history", {"ticket_id": "TCK-4001"}, error=True, text=TRANSIENT))
    assert mod.transient_recovered(no_retry) is False
    retry_fails = record(
        call(1, "fetch_ticket_history", {"ticket_id": "TCK-4001"}, error=True, text=TRANSIENT),
        call(2, "fetch_ticket_history", {"ticket_id": "TCK-4001"}, error=True, text=TRANSIENT),
    )
    assert mod.transient_recovered(retry_fails) is False
    assert mod.transient_recovered(RunRecord()) is False


# --- vacío válido frente a fallo --------------------------------------------------

def test_says_no_history_detects_a_claim_of_no_data():
    assert mod.says_no_history("El ticket no tiene histórico de eventos.")
    assert mod.says_no_history("No hay eventos registrados para TCK-4001.")
    assert mod.says_no_history("El histórico está vacío.")
    assert not mod.says_no_history("El histórico tiene 2 eventos: creación y cambio de estado.")
    assert not mod.says_no_history("No pude consultar el histórico: tiempo de espera agotado.")
    assert not mod.says_no_history(None)


# --- configuración ----------------------------------------------------------------

def test_variants():
    assert mod.ANTI_VARIANTS == ["generico", "fallo_como_vacio"]


def test_prompt_asks_for_all_five_tasks_with_a_malformed_id():
    for needle in ("TCK-4001", "1001", "licencia", "auditoría", "EMP-9999"):
        assert needle in mod.PROMPT


def test_options_use_a_fresh_state_per_variant_and_only_the_mesa_tools():
    state = ErroresState()
    options = mod.build_options(None, state, budget=0.1, model="m")
    assert options.tools == [] and options.setting_sources == [] and options.max_budget_usd == 0.1
    assert set(options.allowed_tools) == {
        f"mcp__mesa__{n}" for n in (
            "fetch_ticket_history", "get_user_profile", "reassign_license", "export_audit_log", "search_tickets_by_user",
        )
    }
    assert options.permission_mode == "dontAsk" and "mesa" in options.mcp_servers


def test_system_prompt_does_not_explain_the_error_policy():
    # La política sale de los metadatos del error, no del prompt (si no, no se mediría nada).
    prompt = mod.SYSTEM.lower()
    for word in ("reintent", "transitorio", "isretryable", "cupo"):
        assert word not in prompt
