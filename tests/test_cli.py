"""Tests de `harness/cli.py`: `--anti [variante]`, `--repeat` y `--budget` que solo baja el tope. Sin modelo."""

import pytest

from harness.cli import build_parser, effective_budget


def parser(variants=("texto", "tope")):
    return build_parser("módulo de prueba", anti_variants=list(variants))


def test_defaults():
    args = parser().parse_args([])
    assert args.anti is None and args.repeat == 1 and args.budget is None


def test_anti_without_value_uses_first_variant():
    assert parser().parse_args(["--anti"]).anti == "texto"
    assert parser().parse_args(["--anti", "tope"]).anti == "tope"


def test_anti_rejects_unknown_variant():
    with pytest.raises(SystemExit):
        parser().parse_args(["--anti", "inventada"])


def test_single_variant_module_accepts_bare_anti():
    args = build_parser("x", anti_variants=["prompt"]).parse_args(["--anti"])
    assert args.anti == "prompt"


def test_module_without_anti_has_no_flag():
    with pytest.raises(SystemExit):
        build_parser("x", anti_variants=[]).parse_args(["--anti"])


@pytest.mark.parametrize("bad", ["0", "-2"])
def test_repeat_must_be_positive(bad):
    with pytest.raises(SystemExit):
        parser().parse_args(["--repeat", bad])


def test_budget_only_lowers():
    assert effective_budget(None, 0.25, ".env") == (0.25, ".env", None)
    assert effective_budget(0.05, 0.25, ".env") == (0.05, "--budget", None)
    value, origin, warning = effective_budget(5.0, 0.25, "defecto")
    assert (value, origin) == (0.25, "defecto") and "no sube" in warning
    # Pedir exactamente el tope no lo reduce: el origen sigue siendo el resuelto.
    assert effective_budget(0.25, 0.25, "entorno") == (0.25, "entorno", None)


def test_budget_flag_must_be_positive():
    with pytest.raises(SystemExit):
        parser().parse_args(["--budget", "0"])
