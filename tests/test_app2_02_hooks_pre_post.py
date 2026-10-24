"""Tests de app2/02_hooks_pre_post: frontera del umbral, redirección al escalamiento y normalización de fechas y estados. Sin modelo."""

import json

import pytest

from datos.generar_sinteticos import STATUS_VARIANTS
from harness.data import load
from harness.offline import run_hook
from tests.cargar import load as load_module

mod = load_module("app2_agente_con_control/02_hooks_pre_post.py")


def pay(amount):
    return run_hook(mod.threshold_hook, "PreToolUse", mod.PAY,
                    {"user_id": "EMP-1020", "ticket_id": "TCK-4039", "amount_eur": amount})


@pytest.mark.parametrize("amount", [39.9, 499.99, 500.0])
def test_threshold_allows_up_to_500(amount):
    result = pay(amount)
    assert result.decision is None and result.raw == {}


@pytest.mark.parametrize("amount", [500.01, 845.5, 1290.0])
def test_threshold_denies_and_redirects(amount):
    result = pay(amount)
    assert result.decision == "deny"
    assert "escalate_to_human" in result.reason and "Finanzas" in result.reason


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1788449580, "2026-09-03T15:33:00+00:00"),
        ("29/09/2026 10:33", "2026-09-29T10:33:00+00:00"),
        ("2026-09-21T17:18:00+00:00", "2026-09-21T17:18:00+00:00"),
    ],
)
def test_dates_to_iso(raw, expected):
    assert mod.normalize_date(raw) == expected


def test_every_generated_status_variant_maps_to_canonical():
    for canonical, variants in STATUS_VARIANTS.items():
        for variant in variants:
            assert mod.normalize_status(variant) == canonical


def test_unknown_status_is_flagged_not_guessed():
    assert mod.normalize_status("pendiente de proveedor") == "unknown:pendiente de proveedor"


def test_every_generated_ticket_normalizes():
    for ticket in load("tickets.json"):
        normalized = mod.normalize_ticket(ticket)
        assert normalized["status"] in {"open", "in_progress", "resolved"}
        assert normalized["created_at"].endswith("+00:00")


@pytest.mark.parametrize("shape", ["list", "dict", "str"])
def test_post_hook_replaces_mcp_output(shape):
    ticket = next(t for t in load("tickets.json") if isinstance(t["created_at"], int))
    text = json.dumps(ticket)
    blocks = [{"type": "text", "text": text}]
    response = {"list": blocks, "dict": {"content": blocks}, "str": text}[shape]
    result = run_hook(mod.normalize_hook, "PostToolUse", mod.GET_TICKET, {"ticket_id": ticket["ticket_id"]},
                      tool_response=response)
    replaced = result.replaced_output
    replaced_text = {"list": lambda r: r[0]["text"], "dict": lambda r: r["content"][0]["text"], "str": lambda r: r}[shape](replaced)
    data = json.loads(replaced_text)
    assert data["created_at"] == mod.normalize_date(ticket["created_at"])
    assert data["status"] in {"open", "in_progress", "resolved"}


def test_post_hook_leaves_errors_alone():
    blocks = [{"type": "text", "text": json.dumps({"errorCategory": "not_found"})}]
    result = run_hook(mod.normalize_hook, "PostToolUse", mod.GET_TICKET, {"ticket_id": "TCK-0"}, tool_response=blocks)
    assert result.raw == {}


def test_hooks_registered_only_in_correct_variant():
    assert set(mod.build_hooks(anti=None)) == {"PreToolUse", "PostToolUse"}
    assert mod.build_hooks(anti="prompt") is None
    assert "500" in mod.system_prompt(anti="prompt") and "500" not in mod.system_prompt(anti=None)
