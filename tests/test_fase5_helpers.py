"""Tests de los helpers comunes de la fase 5 (paquete 5.1): preámbulo, parser ampliado, corte por presupuesto, carga de módulos hermanos y los pequeños comunes. Sin modelo.

PROPÓSITO: fijar el contrato del paquete 5.1. Estos helpers sustituyen bloques que hoy se repiten en
los módulos: el preámbulo de credencial, modelo y presupuesto (25 módulos), la validación de `--anti`
por parte (8) y de `--rol-modelo` (6), `make_create` y el `try/except BudgetExceeded`, `load_sibling`
(4 copias) y `ok`/`error`/`deny`/`rate_text`/`accuracy`.

POR QUÉ EXISTE: cada copia derivaba por su lado (`rate_text` ya tiene dos formatos). Con el helper
fijado por tests, 5.2 puede migrar los módulos sin cambiar lo que imprimen.

QUÉ NO HACE: no migra ningún módulo ni comprueba que lo estén (eso es 5.2). No esconde las opciones
del agente: siguen visibles en cada módulo. La firma antigua de `build_parser` la sigue probando
`tests/test_cli.py`.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contrato import require

require("5.1")  # se salta entero mientras falte algún helper de 5.1

from harness import budget as budget_mod  # noqa: E402
from harness import cli  # noqa: E402
from harness.budget import PRICES, BudgetExceeded, CostGuard, make_create, run_guarded  # noqa: E402
from harness.cargar import load_path, load_sibling  # noqa: E402
from harness.metrics import accuracy, fmt_usd, rate_text  # noqa: E402
from harness.results import deny, error, ok  # noqa: E402
from tests import cargar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = next(iter(PRICES))


# --- preamble ------------------------------------------------------------------------------------------


@pytest.fixture
def fake_preamble(monkeypatch):
    """Sustituye credencial, modelo y presupuesto por versiones que solo apuntan qué se pidió."""
    calls = []
    monkeypatch.setattr(cli.credentials, "describe", lambda: "[credencial] falsa")
    monkeypatch.setattr(cli.credentials, "require_api_key", lambda: calls.append("api_key"))
    monkeypatch.setattr(cli, "report_model", lambda role: print(f"[modelo] rol={role}") or f"modelo-{role}")
    monkeypatch.setattr(cli, "report_budget", lambda requested, kind: print(f"[presupuesto] {kind} {requested}") or 0.25)
    return calls


def test_preamble_prints_credential_models_and_budget_in_order(fake_preamble, capsys):
    models, budget = cli.preamble(None, "coordinator", "subagent", budget_kind="multiagent")
    assert models == ["modelo-coordinator", "modelo-subagent"]
    assert budget == 0.25
    assert capsys.readouterr().out.splitlines() == [
        "[credencial] falsa",
        "[modelo] rol=coordinator",
        "[modelo] rol=subagent",
        "[presupuesto] multiagent None",
    ]
    assert fake_preamble == []  # sin `require_api_key=True` no se exige la API key


def test_preamble_budget_kind_defaults_to_the_first_role_and_passes_the_requested_cap(fake_preamble, capsys):
    cli.preamble(0.1, "enforcement")
    assert capsys.readouterr().out.splitlines()[-1] == "[presupuesto] enforcement 0.1"


def test_preamble_requires_the_api_key_after_the_credential_line(fake_preamble, capsys):
    cli.preamble(None, "agent", require_api_key=True)
    assert fake_preamble == ["api_key"]
    assert capsys.readouterr().out.splitlines()[0] == "[credencial] falsa"


def test_preamble_without_roles_is_an_error(fake_preamble):
    with pytest.raises(ValueError):
        cli.preamble(None)


# --- build_parser ampliado -----------------------------------------------------------------------------


def parse_fails(parser, argv, capsys) -> str:
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(argv)
    assert exc.value.code == 2
    return capsys.readouterr().err


def by_part(**extra):
    return cli.build_parser("d", parts=["p1", "p2", "p3"], anti_by_part={"p1": ["a", "b"], "p2": ["c"]}, **extra)


def test_old_signature_still_works():
    args = cli.build_parser("d", anti_variants=["a", "b"]).parse_args(["--anti"])
    assert (args.anti, args.repeat, args.budget) == ("a", 1, None)
    assert not hasattr(args, "parte") and not hasattr(args, "rol_modelo")


def test_anti_variants_is_now_optional():
    assert cli.build_parser("d").parse_args([]).anti is None


def test_anti_by_part_accepts_a_variant_of_the_chosen_part():
    args = by_part(default_part="p1").parse_args(["--parte", "p2", "--anti", "c"])
    assert (args.parte, args.anti) == ("p2", "c")


def test_bare_anti_takes_the_first_variant_of_the_chosen_part():
    assert by_part(default_part="p1").parse_args(["--parte", "p2", "--anti"]).anti == "c"
    assert by_part(default_part="p1").parse_args(["--anti"]).anti == "a"


def test_anti_of_another_part_is_rejected_naming_the_valid_ones(capsys):
    err = parse_fails(by_part(default_part="p1"), ["--parte", "p2", "--anti", "a"], capsys)
    assert "--anti a" in err and "p2" in err and "p1: a, b" in err


def test_anti_in_a_part_without_variants_is_rejected(capsys):
    err = parse_fails(by_part(default_part="p1"), ["--parte", "p3", "--anti"], capsys)
    assert "p3" in err


def test_unknown_anti_and_unknown_part_are_rejected(capsys):
    parse_fails(by_part(default_part="p1"), ["--anti", "zzz"], capsys)
    parse_fails(by_part(default_part="p1"), ["--parte", "p9"], capsys)


def test_default_part_and_required_part():
    assert by_part(default_part="p1").parse_args([]).parte == "p1"
    with pytest.raises(SystemExit):
        by_part().parse_args([])  # sin `default_part`, `--parte` es obligatoria


def test_parts_without_anti_by_part_only_add_parte():
    args = cli.build_parser("d", anti_variants=["x"], parts=["a", "b"], default_part="b").parse_args(["--anti"])
    assert (args.parte, args.anti) == ("b", "x")


def test_inconsistent_definitions_are_programming_errors():
    with pytest.raises(ValueError):
        cli.build_parser("d", anti_variants=["a"], parts=["p1"], anti_by_part={"p1": ["a"]})
    with pytest.raises(ValueError):
        cli.build_parser("d", parts=["p1"], anti_by_part={"p9": ["a"]})
    with pytest.raises(ValueError):
        cli.build_parser("d", anti_by_part={"p1": ["a"]})  # sin `parts`
    with pytest.raises(ValueError):
        cli.build_parser("d", parts=["p1"], default_part="p9")
    with pytest.raises(ValueError):
        cli.build_parser("d", model_roles=["agent"], default_role="enforcement")


def test_model_roles_add_rol_modelo_with_its_default(capsys):
    parser = cli.build_parser("d", model_roles=["agent", "enforcement"])
    assert parser.parse_args([]).rol_modelo == "agent"  # sin `default_role`, el primero
    assert parser.parse_args(["--rol-modelo", "enforcement"]).rol_modelo == "enforcement"
    parse_fails(parser, ["--rol-modelo", "coordinator"], capsys)
    assert cli.build_parser("d", model_roles=["agent", "enforcement"], default_role="enforcement").parse_args([]).rol_modelo == "enforcement"


def test_role_flag_names_the_option_for_a_subagent_role(capsys):
    # `app3/05` elige el modelo del subagente con `--rol-subagente`, no con `--rol-modelo`.
    parser = cli.build_parser("d", model_roles=["subagent", "enforcement"], role_flag="--rol-subagente")
    assert parser.parse_args([]).rol_subagente == "subagent"
    assert parser.parse_args(["--rol-subagente", "enforcement"]).rol_subagente == "enforcement"
    parse_fails(parser, ["--rol-modelo", "enforcement"], capsys)


def test_without_model_roles_there_is_no_rol_modelo(capsys):
    parse_fails(cli.build_parser("d"), ["--rol-modelo", "agent"], capsys)


# --- make_create y run_guarded ---------------------------------------------------------------------------


def usage(tokens_in: int, tokens_out: int):
    return SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out, cache_creation_input_tokens=0, cache_read_input_tokens=0)


class FakeClient:
    def __init__(self, response):
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)
        self.response = response

    def _create(self, **request):
        self.requests.append(request)
        return self.response


def test_make_create_lives_next_to_cost_guard_and_adds_each_response():
    assert budget_mod.make_create is make_create
    client = FakeClient(SimpleNamespace(usage=usage(1000, 100)))
    guard = CostGuard(MODEL, 10.0)
    create = make_create(client, guard)
    assert create(model=MODEL, max_tokens=5, messages=[]) is client.response
    assert client.requests == [{"model": MODEL, "max_tokens": 5, "messages": []}]
    assert guard.spent > 0


def test_make_create_with_batch_applies_the_batch_discount():
    # `app3/09` paga los lotes con descuento: el helper lo aplica con `batch=True` (lo calcula `cost_of`).
    response = SimpleNamespace(usage=usage(10_000, 2_000))
    normal, batched = CostGuard(MODEL, 10.0), CostGuard(MODEL, 10.0)
    make_create(FakeClient(response), normal)(messages=[])
    make_create(FakeClient(response), batched, batch=True)(messages=[])
    assert batched.spent == pytest.approx(normal.spent * budget_mod.BATCH_DISCOUNT)


def test_make_create_cuts_when_the_cap_is_passed():
    create = make_create(FakeClient(SimpleNamespace(usage=usage(10_000_000, 0))), CostGuard(MODEL, 0.0001))
    with pytest.raises(BudgetExceeded):
        create(messages=[])


def test_run_guarded_returns_zero_and_prints_the_end_line(capsys):
    guard = CostGuard(MODEL, 1.0)
    assert run_guarded(guard, lambda: None) == 0
    assert capsys.readouterr().out == "\n[fin] coste=$0.0000 de $1.0\n"


def test_run_guarded_keeps_the_action_exit_code():
    assert run_guarded(CostGuard(MODEL, 1.0), lambda: 3, report_end=False) == 3


def test_run_guarded_turns_the_cut_into_exit_code_one(capsys):
    def action():
        raise BudgetExceeded("coste acumulado $2 supera el tope $1")

    assert run_guarded(CostGuard(MODEL, 1.0), action) == 1
    assert capsys.readouterr().out == "[corte] coste acumulado $2 supera el tope $1\n"  # sin línea [fin]


def test_run_guarded_without_end_line(capsys):
    run_guarded(CostGuard(MODEL, 1.0), lambda: None, report_end=False)
    assert capsys.readouterr().out == ""


def test_run_guarded_lets_other_errors_through():
    def action():
        raise KeyError("x")

    with pytest.raises(KeyError):
        run_guarded(CostGuard(MODEL, 1.0), action)


# --- load_path y load_sibling ----------------------------------------------------------------------------

APP3 = ROOT / "app3_sistema_multiagente"


def test_load_sibling_and_tests_cargar_share_the_same_module():
    # Un solo objeto por archivo: las dataclass de `07` son las mismas para `08` y para los tests.
    from_tests = cargar.load("app3_sistema_multiagente/07_extraccion_schema.py")
    from_sibling = load_sibling(APP3 / "08_validacion_reintento.py", "07_extraccion_schema.py")
    assert from_sibling is from_tests
    assert from_tests.__name__ == "_app_app3_sistema_multiagente_07_extraccion_schema"
    assert sys.modules[from_tests.__name__] is from_tests


def test_load_path_is_cached():
    path = APP3 / "07_extraccion_schema.py"
    assert load_path(path) is load_path(path)


def test_load_sibling_accepts_a_string_anchor():
    assert load_sibling(str(APP3 / "10_confianza_y_revision.py"), "07_extraccion_schema.py") is load_path(APP3 / "07_extraccion_schema.py")


def test_missing_file_raises_and_leaves_nothing_registered():
    with pytest.raises(FileNotFoundError):
        load_sibling(APP3 / "08_validacion_reintento.py", "99_no_existe.py")
    assert "_app_app3_sistema_multiagente_99_no_existe" not in sys.modules


# --- ok, error y deny --------------------------------------------------------------------------------------


def test_ok_wraps_the_data_as_json_text_keeping_accents():
    result = ok({"nombre": "Íñigo"})
    assert result == {"content": [{"type": "text", "text": json.dumps({"nombre": "Íñigo"}, ensure_ascii=False)}]}
    assert "is_error" not in result


def test_error_carries_category_retryable_message_and_extra_fields():
    result = error("validation", "falta el ID", ticket_id="T-1")
    assert result["is_error"] is True
    assert json.loads(result["content"][0]["text"]) == {"errorCategory": "validation", "isRetryable": False, "message": "falta el ID", "ticket_id": "T-1"}
    assert list(json.loads(result["content"][0]["text"])) == ["errorCategory", "isRetryable", "message", "ticket_id"]
    assert json.loads(error("transient", "timeout", retryable=True)["content"][0]["text"])["isRetryable"] is True


def test_deny_is_a_pre_tool_use_decision_with_its_reason():
    assert deny("motivo") == {
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "motivo"}
    }


# --- rate_text, accuracy y fmt_usd -------------------------------------------------------------------------


def test_rate_text_with_percent_is_the_default():
    # Formato de app1/03 y app1/05.
    assert rate_text((3, 4)) == "3/4 (75 %)"
    assert rate_text((1, 3)) == "1/3 (33 %)"
    assert rate_text((2, 3)) == "2/3 (67 %)"


def test_rate_text_without_percent_keeps_app2_04():
    assert rate_text((3, 4), percent=False) == "3/4"


def test_rate_text_without_data():
    assert rate_text((0, 0)) == "sin datos"
    assert rate_text((0, 0), percent=False) == "sin datos"


def test_accuracy_counts_hits_and_a_missing_call_is_a_miss():
    assert accuracy([("a", "a"), ("b", "a"), (None, "a")]) == (1, 3)
    assert accuracy([]) == (0, 0)


def test_accuracy_with_a_custom_match_keeps_app1_05():
    # app1/05 compara con su `is_correct`, no con `==`.
    assert accuracy([("A", "a"), ("b", "a")], match=lambda chosen, expected: (chosen or "").lower() == expected) == (1, 2)


def test_fmt_usd_has_four_decimals():
    assert fmt_usd(0.01234) == "$0.0123"
    assert fmt_usd(0) == "$0.0000"
    assert fmt_usd(1.5) == "$1.5000"
