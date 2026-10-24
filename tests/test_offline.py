"""Tests de `harness/offline.py`: hooks y handlers de tools invocados como el SDK. Sin modelo."""

import json

from claude_agent_sdk import tool

from harness.offline import call_tool, run_hook

# --- Hooks de ejemplo (datos sintéticos) ---------------------------------------


async def deny_large_refund(hook_input, tool_use_id, context):
    if hook_input["tool_input"].get("amount", 0) > 500:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "importe sobre el umbral: escalar",
            }
        }
    return {}


async def force_ticket_prefix(hook_input, tool_use_id, context):
    ticket = hook_input["tool_input"]["ticket_id"]
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"ticket_id": ticket if ticket.startswith("TCK-") else f"TCK-{ticket}"},
        }
    }


async def normalize_status(hook_input, tool_use_id, context):
    response = hook_input["tool_response"]
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedMCPToolOutput": {**response, "status": response["status"].lower()},
        }
    }


def test_pre_tool_use_deny_and_allow():
    denied = run_hook(deny_large_refund, "PreToolUse", "issue_refund", {"amount": 900})
    assert denied.decision == "deny" and "escalar" in denied.reason
    allowed = run_hook(deny_large_refund, "PreToolUse", "issue_refund", {"amount": 20})
    assert allowed.decision is None and allowed.raw == {}


def test_pre_tool_use_rewrites_input():
    result = run_hook(force_ticket_prefix, "PreToolUse", "get_ticket", {"ticket_id": "42"})
    assert result.decision == "allow"
    assert result.updated_input == {"ticket_id": "TCK-42"}


def test_post_tool_use_replaces_output():
    result = run_hook(normalize_status, "PostToolUse", "get_ticket", {}, tool_response={"status": "OPEN"})
    assert result.replaced_output == {"status": "open"}


def test_hook_receives_sdk_fields():
    seen = {}

    async def spy(hook_input, tool_use_id, context):
        seen.update(hook_input, tool_use_id=tool_use_id, context=context)
        return {}

    run_hook(spy, "PreToolUse", "Read", {"file_path": "x"}, agent_id="ag-1")
    assert seen["hook_event_name"] == "PreToolUse" and seen["agent_id"] == "ag-1"
    assert seen["tool_use_id"].startswith("toolu_offline_") and seen["context"] == {"signal": None}
    assert {"session_id", "transcript_path", "cwd", "tool_name", "tool_input"} <= set(seen)


# --- Tools de ejemplo ------------------------------------------------------------


@tool("lookup_ticket", "Busca un ticket sintético", {"ticket_id": str})
async def lookup_ticket(args):
    if args["ticket_id"] == "TCK-0":
        payload = {"errorCategory": "business", "isRetryable": False}
        return {"content": [{"type": "text", "text": json.dumps(payload)}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps({"ticket_id": args["ticket_id"]})}]}


@tool("broken", "Lanza una excepción", {})
async def broken(args):
    raise ConnectionError("backend sintético caído")


def test_tool_success_and_structured_error():
    ok = call_tool(lookup_ticket, {"ticket_id": "TCK-7"})
    assert not ok.is_error and json.loads(ok.text) == {"ticket_id": "TCK-7"}
    err = call_tool(lookup_ticket, {"ticket_id": "TCK-0"})
    assert err.is_error and json.loads(err.text)["isRetryable"] is False


def test_tool_exception_becomes_error_result():
    outcome = call_tool(broken, {})
    assert outcome.is_error and "ConnectionError" in outcome.text
