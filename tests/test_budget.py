"""Tests de `harness/budget.py`: coste por `usage`, tramo de contexto largo y corte al superar el tope. Sin modelo."""

from types import SimpleNamespace

import pytest

from harness.budget import BudgetExceeded, CostGuard, cost_of


def usage(inp=0, out=0, cache_write=None, cache_read=None):
    # Mismos atributos que `anthropic.types.Usage`; los de caché pueden ser None.
    return SimpleNamespace(
        input_tokens=inp, output_tokens=out,
        cache_creation_input_tokens=cache_write, cache_read_input_tokens=cache_read,
    )


def test_cost_of_haiku_and_sonnet():
    # 100K de entrada no supera el tramo corto de Haiku.
    assert cost_of("claude-haiku-5-5", usage(100_000, 1_000_000)) == pytest.approx(0.01 + 0.50)
    assert cost_of("claude-sonnet-5-5", usage(1_000_000, 100_000)) == pytest.approx(2.00 + 1.00)


def test_cache_tokens_are_priced():
    # Escritura en caché a 1,25× la entrada y lectura a 0,1×.
    assert cost_of("claude-sonnet-5-5", usage(cache_write=1_000_000)) == pytest.approx(2.50)
    assert cost_of("claude-sonnet-5-5", usage(cache_read=1_000_000)) == pytest.approx(0.20)


def test_haiku_long_prompt_tier():
    # Por encima de 100K tokens de entrada, Haiku 5.5 cobra 0,50/2,50.
    assert cost_of("claude-haiku-5-5", usage(200_000, 10_000)) == pytest.approx(0.10 + 0.025)


def test_unknown_model_fails():
    with pytest.raises(KeyError):
        cost_of("modelo-sin-precio", usage(1, 1))


def test_guard_accumulates_and_cuts():
    guard = CostGuard("claude-sonnet-5-5", max_usd=0.05)
    guard.add(usage(10_000, 1_000))  # 0.02 + 0.01
    assert guard.spent == pytest.approx(0.03)
    with pytest.raises(BudgetExceeded) as exc:
        guard.add(usage(10_000, 1_000))
    assert "0.05" in str(exc.value) and guard.spent == pytest.approx(0.06)


def test_guard_requires_positive_budget():
    with pytest.raises(ValueError):
        CostGuard("claude-haiku-5-5", max_usd=0)
