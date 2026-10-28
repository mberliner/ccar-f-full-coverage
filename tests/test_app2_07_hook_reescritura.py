"""Tests de app2/07_hook_reescritura: allow con `updatedInput` frente a deny con motivo, prerrequisito del ID verificado y los desenlaces del escenario determinista. Sin modelo."""

import pytest

from app2_agente_con_control.servers.helpdesk import HelpdeskState
from harness.offline import run_hook
from tests.cargar import load

mod = load("app2_agente_con_control/07_hook_reescritura.py")
PAY = mod.PAY
OWN, OTHER = mod.OWN_USER, "EMP-1003"
OTHER_TICKET, OTHER_AMOUNT = "TCK-4051", 39.9  # ticket de gastos real de EMP-1003


def state_with(*verified):
    state = HelpdeskState()
    state.verified.update(verified)
    return state


def pay(state, anti, user=OTHER, ticket="TCK-4047", amount=120.0):
    hook = mod.make_rewrite_hook(state, anti)
    return run_hook(hook, "PreToolUse", PAY, {"user_id": user, "ticket_id": ticket, "amount_eur": amount})


def test_correct_variant_rewrites_user_id_and_keeps_the_rest():
    result = pay(state_with(OWN), anti=None)
    assert result.decision == "allow"
    assert result.updated_input == {"user_id": OWN, "ticket_id": "TCK-4047", "amount_eur": 120.0}


def test_anti_variant_denies_with_the_verified_id_in_the_reason():
    result = pay(state_with(OWN), anti="deny")
    assert result.decision == "deny" and OWN in result.reason
    assert result.updated_input is None


@pytest.mark.parametrize("anti", [None, "deny"])
def test_correct_id_passes_untouched(anti):
    result = pay(state_with(OWN), anti, user=OWN)
    assert result.decision is None and result.raw == {}


@pytest.mark.parametrize("anti", [None, "deny"])
def test_without_verified_id_it_is_denied(anti):
    # Prerrequisito: sin verificación no hay ID que imponer, y la llamada no corre.
    result = pay(state_with(), anti)
    assert result.decision == "deny" and "verify_employee" in result.reason


@pytest.mark.parametrize("anti", [None, "deny"])
def test_ambiguous_verification_fails_closed(anti):
    # Con dos empleados verificados el hook no puede elegir: no adivina.
    result = pay(state_with(OWN, OTHER), anti)
    assert result.decision == "deny"


def test_hook_is_registered_on_the_pay_tool_in_both_variants():
    for anti in (None, "deny"):
        hooks = mod.build_hooks(HelpdeskState(), anti)
        assert set(hooks) == {"PreToolUse"}
        assert hooks["PreToolUse"][0].matcher == PAY


# --- Escenario determinista: el modelo escribe un ID erróneo --------------------


def test_wrong_id_is_not_a_real_employee():
    # El ID erróneo del escenario es un descuido de dígitos, no el de otra persona.
    from harness.data import load as load_data

    real = {u["user_id"] for u in load_data("usuarios.json")}
    assert mod.WRONG_USER not in real and mod.WRONG_USER_AGAIN not in real


def test_rewrite_step_executes_with_the_verified_id_in_one_call():
    step = mod.run_step(mod.verified_state(), None, mod.wrong_call())
    assert step.executed and step.tool_input["user_id"] == OWN
    assert step.state.paid[0]["user_id"] == OWN and not step.is_error


def test_deny_step_does_not_execute_and_pays_nothing():
    step = mod.run_step(mod.verified_state(), "deny", mod.wrong_call())
    assert not step.executed and step.state.paid == []
    assert OWN in step.reason


def test_without_hook_the_wrong_id_reaches_the_tool_and_fails_in_the_handler():
    # Control sin hook (gate=False): la tool recibe el ID tal cual y lo rechaza por validación.
    step = mod.run_step(mod.verified_state(), None, mod.wrong_call(), hook=False)
    assert step.executed and step.tool_input["user_id"] == mod.WRONG_USER
    assert step.is_error and step.state.paid == []


def test_outcomes_rewrite_completes_in_one_call():
    (outcome,) = mod.outcomes(None)
    assert outcome.calls == 1 and outcome.completed and outcome.paid_with == [OWN]


def test_outcomes_deny_depends_on_the_retry():
    by_label = {o.label: o for o in mod.outcomes("deny")}
    assert set(by_label) == {"el modelo reintenta con el ID correcto", "el modelo reintenta con otro ID erróneo",
                             "el modelo no reintenta"}
    ok = by_label["el modelo reintenta con el ID correcto"]
    assert ok.calls == 2 and ok.completed and ok.paid_with == [OWN]
    for label in ("el modelo reintenta con otro ID erróneo", "el modelo no reintenta"):
        assert not by_label[label].completed and by_label[label].paid_with == []
    assert by_label["el modelo no reintenta"].calls == 1
    assert by_label["el modelo reintenta con otro ID erróneo"].calls == 2


def test_deny_never_executes_a_wrong_id_in_any_outcome():
    # El matiz de la cabecera: con deny y comprobación, un ID erróneo tampoco se ejecuta.
    for outcome in mod.outcomes("deny"):
        assert mod.WRONG_USER not in outcome.paid_with


def test_rewrite_of_another_employees_ticket_is_stopped_by_the_handler():
    # La garantía del hook es solo user_id: si el modelo intenta pagar el ticket de otro
    # con el ID de otro, el hook pone el verificado y es el handler quien lo rechaza.
    step = mod.run_step(mod.verified_state(), None, {"user_id": OTHER, "ticket_id": OTHER_TICKET,
                                                     "amount_eur": OTHER_AMOUNT})
    assert step.decision == "allow" and step.tool_input["user_id"] == OWN
    assert step.is_error and step.state.paid == []
