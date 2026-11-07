"""Tests de `harness/headless.py`: la orden aislada de `claude -p`, el tope y la lectura del resultado.

PROPÓSITO: fijar sin modelo lo que la sonda C1 midió con modelo (docs/hallazgos.md, tanda C).

POR QUÉ EXISTE: la orden de `claude -p` es la lección de `app3/11` y `12`: si un flag de
aislamiento o el tope desaparecen, la ejecución dependería de la máquina o no tendría coste
acotado, y ningún otro test lo notaría.

QUÉ NO HACE: no ejecuta la CLI ni llama al modelo; el ejecutor se sustituye por uno falso.
"""

import json
import os
from pathlib import Path

import pytest

from harness import headless
from harness.options import ISOLATION_ENV

SCHEMA = {
    "type": "object",
    "properties": {"n": {"type": "integer"}},
    "required": ["n"],
    "additionalProperties": False,
}


def build(tmp_path: Path, **kwargs):
    kwargs.setdefault("model", "claude-sonnet-5-5")
    kwargs.setdefault("max_budget_usd", 0.2)
    return headless.build_command(cwd=tmp_path, **kwargs)


def value_after(cmd: list[str], flag: str) -> str:
    return cmd[cmd.index(flag) + 1]


# --- la orden ---------------------------------------------------------------


def test_command_is_print_mode_json_with_budget(tmp_path):
    cmd = build(tmp_path)
    assert "-p" in cmd
    assert value_after(cmd, "--output-format") == "json"
    assert value_after(cmd, "--max-budget-usd") == "0.2"
    assert value_after(cmd, "--model") == "claude-sonnet-5-5"


@pytest.mark.parametrize("budget", [None, 0, -1, float("nan")])
def test_budget_is_required(tmp_path, budget):
    with pytest.raises(ValueError):
        build(tmp_path, max_budget_usd=budget)


def test_isolation_flags(tmp_path):
    cmd = build(tmp_path)
    # Solo el proyecto: la memoria y la configuración de usuario no entran.
    assert value_after(cmd, "--setting-sources") == "project"
    assert "--strict-mcp-config" in cmd
    assert "--disable-slash-commands" in cmd
    # `--bare` y `--setting-sources ""` también quitarían el CLAUDE.md del cwd, que aquí es el contexto de CI.
    assert "--bare" not in cmd
    assert value_after(cmd, "--setting-sources") != ""


def test_only_cwd_claude_md_is_kept(tmp_path):
    """`--setting-sources project` deja pasar el CLAUDE.md de los directorios padre; la exclusión negada lo corta."""
    cmd = build(tmp_path)
    settings = json.loads(value_after(cmd, "--settings"))
    assert settings == {"claudeMdExcludes": ["!" + tmp_path.resolve().as_posix() + "/**"]}


def test_default_tools_are_read_only_and_denied_otherwise(tmp_path):
    cmd = build(tmp_path)
    assert value_after(cmd, "--tools") == "Read,Grep,Glob"
    assert value_after(cmd, "--allowedTools") == "Read,Grep,Glob"
    # `dontAsk`: lo que no está permitido se deniega en vez de esperar una respuesta que no llegará (3.6-S1).
    assert value_after(cmd, "--permission-mode") == "dontAsk"


def test_tools_can_be_changed_for_the_generator(tmp_path):
    cmd = build(tmp_path, tools=("Read", "Edit"))
    assert value_after(cmd, "--tools") == "Read,Edit"
    assert value_after(cmd, "--allowedTools") == "Read,Edit"


def test_schema_goes_as_compact_json(tmp_path):
    cmd = build(tmp_path, schema=SCHEMA)
    assert json.loads(value_after(cmd, "--json-schema")) == SCHEMA
    assert "--json-schema" not in build(tmp_path)


def test_resume_keeps_the_session_and_fresh_runs_are_not_persisted(tmp_path):
    fresh = build(tmp_path)
    assert "--no-session-persistence" in fresh and "--resume" not in fresh
    resumed = build(tmp_path, resume="abc-123")
    assert value_after(resumed, "--resume") == "abc-123"
    # Sin persistencia no habría nada que reanudar.
    assert "--no-session-persistence" not in resumed


def test_generator_that_will_be_resumed_must_persist(tmp_path):
    cmd = build(tmp_path, persist=True)
    assert "--no-session-persistence" not in cmd


def test_prompt_is_not_in_the_command(tmp_path):
    """El prompt (con el diff) va por stdin: la orden queda corta y legible."""
    cmd = build(tmp_path)
    assert all("diff --git" not in part for part in cmd)


def test_cli_defaults_to_the_one_bundled_with_the_pinned_sdk(tmp_path):
    cmd = build(tmp_path)
    assert Path(cmd[0]).name.startswith("claude")
    assert "_bundled" in cmd[0]


def test_cli_can_be_overridden(tmp_path):
    assert build(tmp_path, cli="claude")[0] == "claude"


def test_cwd_must_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        headless.build_command(cwd=tmp_path / "no_existe", model="m", max_budget_usd=0.1)


def test_env_has_the_isolation_values(tmp_path):
    env = headless.build_env()
    for key, value in ISOLATION_ENV.items():
        assert env[key] == value
    # El resto del entorno (PATH, la credencial) se conserva.
    assert env["PATH"] == os.environ["PATH"]


def test_command_is_printed_whole_before_running(tmp_path, capsys):
    cmd = build(tmp_path, schema=SCHEMA)
    headless.print_command(cmd, stdin_chars=1234)
    out = capsys.readouterr().out
    assert out.startswith("[orden] ")
    for part in ("--max-budget-usd", "--setting-sources", "--json-schema", "--strict-mcp-config"):
        assert part in out
    assert "1234" in out  # el prompt se anuncia por su tamaño, no se omite en silencio


def test_printed_command_can_be_pasted_in_a_shell(tmp_path):
    line = headless.format_command(build(tmp_path, schema=SCHEMA))
    # El JSON del schema lleva comillas y llaves: se cita para que sobreviva.
    assert "'" in line or '"' in line


# --- el resultado -----------------------------------------------------------


def raw(**fields) -> str:
    base = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "terminal_reason": "completed",
        "num_turns": 3,
        "session_id": "sid-1",
        "total_cost_usd": 0.01,
        "result": "texto",
    }
    base.update(fields)
    return json.dumps(base)


def test_parse_structured_output_valid():
    result = headless.parse_result(raw(structured_output={"n": 3}), SCHEMA)
    assert result.structured == {"n": 3}
    assert result.status == "ok" and result.ok
    assert result.session_id == "sid-1" and result.cost_usd == 0.01


def test_parse_structured_output_invalid_against_schema():
    """El CLI da por buena una salida; el módulo valida de nuevo por si acaso."""
    result = headless.parse_result(raw(structured_output={"n": "tres"}), SCHEMA)
    assert result.status == "schema_invalid" and not result.ok
    assert "n" in result.detail


def test_parse_missing_structured_output_is_not_a_success():
    """Sonda C1: con un schema imposible el CLI devuelve `subtype: success` y texto libre."""
    result = headless.parse_result(raw(result="No pude cumplir el esquema"), SCHEMA)
    assert result.status == "no_structured_output" and not result.ok
    assert result.text == "No pude cumplir el esquema"


def test_parse_without_schema_only_needs_a_success():
    result = headless.parse_result(raw(), None)
    assert result.status == "ok" and result.structured is None


def test_parse_budget_exhausted():
    result = headless.parse_result(
        raw(subtype="error_max_budget_usd", is_error=True, terminal_reason="budget_exhausted", result=None, total_cost_usd=0.0042),
        SCHEMA,
    )
    assert result.status == "budget_exhausted" and not result.ok
    assert result.cost_usd == 0.0042


def test_parse_not_json():
    result = headless.parse_result("Traceback...", SCHEMA)
    assert result.status == "not_json" and not result.ok


def test_parse_other_error():
    result = headless.parse_result(raw(subtype="error_during_execution", is_error=True, result=None), SCHEMA)
    assert result.status == "error" and "error_during_execution" in result.detail


# --- coste acumulado de la sesión reanudada --------------------------------


def test_resumed_cost_is_cumulative_so_the_invocation_cost_is_the_difference():
    """Sonda C1: `total_cost_usd` de `--resume` incluye el de la sesión (0,001186 → 0,001464 → 0,001528)."""
    ledger = headless.Ledger(limit_usd=0.5)
    generator = headless.parse_result(raw(total_cost_usd=0.001186), None)
    review = headless.parse_result(raw(total_cost_usd=0.001464), None)
    assert ledger.add(generator) == pytest.approx(0.001186)
    assert ledger.add(review, resumed_from=generator) == pytest.approx(0.000278)
    assert ledger.spent == pytest.approx(0.001464)  # no 0,00265: no se cuenta dos veces


def test_fresh_runs_add_up():
    ledger = headless.Ledger(limit_usd=0.5)
    ledger.add(headless.parse_result(raw(total_cost_usd=0.01), None))
    ledger.add(headless.parse_result(raw(total_cost_usd=0.02), None))
    assert ledger.spent == pytest.approx(0.03)


def test_remaining_feeds_the_next_flag_and_stops_at_zero():
    """El flag de la CLI no cuenta el histórico de la sesión: el tope de la rama lo lleva el arnés."""
    ledger = headless.Ledger(limit_usd=0.05)
    ledger.add(headless.parse_result(raw(total_cost_usd=0.02), None))
    assert ledger.remaining() == pytest.approx(0.03)
    ledger.add(headless.parse_result(raw(total_cost_usd=0.04), None))
    with pytest.raises(headless.BudgetExhausted):
        ledger.remaining()


def test_ledger_limit_is_required():
    with pytest.raises(ValueError):
        headless.Ledger(limit_usd=0)


# --- ejecución con ejecutor falso ------------------------------------------


class FakeRun:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout, self.returncode, self.stderr = stdout, returncode, ""
        self.calls: list[dict] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append({"cmd": cmd, **kwargs})
        return self

    # `subprocess.CompletedProcess` expone estos tres atributos


def test_run_prints_command_then_runs_and_passes_prompt_by_stdin(tmp_path, capsys):
    fake = FakeRun(raw(structured_output={"n": 1}))
    cmd = build(tmp_path, schema=SCHEMA)
    result = headless.run(cmd, "PROMPT LARGO", cwd=tmp_path, schema=SCHEMA, runner=fake)
    out = capsys.readouterr().out
    assert out.index("[orden]") < out.index("[resultado]")
    call = fake.calls[0]
    assert call["input"] == "PROMPT LARGO"
    assert Path(call["cwd"]) == tmp_path
    assert call["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert result.ok and result.structured == {"n": 1}


def test_run_reports_nonzero_exit_with_budget_error(tmp_path):
    fake = FakeRun(raw(subtype="error_max_budget_usd", is_error=True, result=None), returncode=1)
    result = headless.run(build(tmp_path), "p", cwd=tmp_path, schema=None, runner=fake)
    assert result.status == "budget_exhausted"


# --- [contexto]: qué ve el proceso al empezar (verificación §11.6) -------------------------------------------------


def init_line(**fields) -> str:
    base = {"type": "system", "subtype": "init", "tools": ["Read", "Grep", "Glob"], "mcp_servers": [], "skills": [], "slash_commands": [],
            "plugins": [{"name": "cc-plugin-agents-md"}], "apiKeySource": "ANTHROPIC_API_KEY", "model": "claude-sonnet-5-5"}
    base.update(fields)
    return json.dumps(base)


def test_stream_json_output_needs_verbose(tmp_path):
    cmd = build(tmp_path, stream=True)
    assert value_after(cmd, "--output-format") == "stream-json" and "--verbose" in cmd
    assert "--verbose" not in build(tmp_path)


def test_parse_init_reads_the_system_init_line_among_other_messages():
    stream = "\n".join(['{"type":"assistant"}', init_line(), '{"type":"result","subtype":"success"}'])
    init = headless.parse_init(stream)
    assert init["tools"] == ["Read", "Grep", "Glob"]
    assert headless.parse_init("no es json\n") is None
    assert headless.parse_init('{"type":"result"}') is None


def test_context_line_reports_tools_mcp_skills_plugins_credential_and_model():
    line = headless.context_line(headless.parse_init(init_line()))
    assert line.startswith("[contexto] ")
    for part in ("tools=3", "mcp=[]", "skills=[]", "plugins=['cc-plugin-agents-md']", "credencial=ANTHROPIC_API_KEY", "modelo=claude-sonnet-5-5"):
        assert part in line


def test_isolation_problems_flag_skills_commands_and_mcp_servers():
    assert headless.isolation_problems(headless.parse_init(init_line())) == []
    dirty = headless.parse_init(init_line(skills=["deep-research"], mcp_servers=[{"name": "x"}], slash_commands=["init"]))
    problems = headless.isolation_problems(dirty)
    assert any("skills" in p for p in problems) and any("mcp" in p for p in problems)


def test_isolation_problems_accept_the_builtin_commands_that_the_cli_always_lists():
    """Con `--disable-slash-commands` la lista de comandos queda vacía; si no lo está, se avisa."""
    assert headless.isolation_problems(headless.parse_init(init_line(slash_commands=["init", "compact"]))) != []


# --- bifurcar la sesión (autorrevisión de app3/12) ------------------------------------------------------------------------------


def test_fork_creates_a_new_session_from_the_resumed_one(tmp_path):
    cmd = build(tmp_path, resume="abc-123", fork=True)
    assert value_after(cmd, "--resume") == "abc-123" and "--fork-session" in cmd
    assert "--fork-session" not in build(tmp_path, resume="abc-123")


def test_fork_without_resume_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path, fork=True)


# --- (9) `run` y `probe_context`: la orden sin tope no se ejecuta, y la sonda imprime su orden y cuenta su coste -----------------


def stream_with_cost(cost: float) -> str:
    return "\n".join([init_line(), json.dumps({"type": "result", "subtype": "success", "total_cost_usd": cost})])


def test_run_rejects_a_command_without_the_budget_flag_and_never_calls_the_runner(tmp_path):
    fake = FakeRun(raw())
    no_cap = [part for i, part in enumerate(build(tmp_path)) if part != "--max-budget-usd" and build(tmp_path)[i - 1] != "--max-budget-usd"]
    assert "--max-budget-usd" not in no_cap
    with pytest.raises(ValueError, match="max-budget-usd"):
        headless.run(no_cap, "p", cwd=tmp_path, schema=None, runner=fake)
    assert fake.calls == [], "una orden sin tope no llega a ejecutarse"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "mucho"])
def test_run_rejects_a_budget_flag_that_is_not_a_positive_amount(tmp_path, value):
    cmd = build(tmp_path)
    cmd[cmd.index("--max-budget-usd") + 1] = value
    fake = FakeRun(raw())
    with pytest.raises(ValueError):
        headless.run(cmd, "p", cwd=tmp_path, schema=None, runner=fake)
    assert fake.calls == []


def test_run_accepts_a_command_with_a_positive_budget(tmp_path):
    """Control: la orden que construye `build_command` sigue ejecutándose."""
    fake = FakeRun(raw())
    assert headless.run(build(tmp_path), "p", cwd=tmp_path, schema=None, runner=fake).ok and len(fake.calls) == 1


def test_probe_context_prints_the_whole_command_before_running_it(tmp_path, capsys):
    fake = FakeRun(stream_with_cost(0.01))
    cmd = build(tmp_path, stream=True)
    headless.probe_context(cmd, cwd=tmp_path, ledger=headless.Ledger(1.0), runner=fake)
    out = capsys.readouterr().out
    assert out.startswith("[orden] ") and headless.format_command(cmd) in out and "--max-budget-usd" in out
    assert len(fake.calls) == 1


def test_probe_context_adds_its_cost_to_the_ledger_and_returns_the_init_line(tmp_path):
    ledger = headless.Ledger(1.0)
    init = headless.probe_context(build(tmp_path, stream=True), cwd=tmp_path, ledger=ledger, runner=FakeRun(stream_with_cost(0.0425)))
    assert init["model"] == "claude-sonnet-5-5"
    assert ledger.spent == pytest.approx(0.0425)


def test_the_probe_cost_can_exhaust_the_ledger_so_the_next_run_is_refused(tmp_path):
    """Falso negativo de antes: la sonda gastaba fuera del tope y `11` podía pasar de `--budget`."""
    ledger = headless.Ledger(0.05)
    headless.probe_context(build(tmp_path, stream=True), cwd=tmp_path, ledger=ledger, runner=FakeRun(stream_with_cost(0.06)))
    with pytest.raises(headless.BudgetExhausted):
        ledger.remaining()


def test_a_probe_without_a_cost_line_adds_nothing_and_a_probe_without_cap_is_rejected(tmp_path):
    ledger = headless.Ledger(1.0)
    assert headless.probe_context(build(tmp_path, stream=True), cwd=tmp_path, ledger=ledger, runner=FakeRun(init_line())) is not None
    assert ledger.spent == 0.0
    cmd = build(tmp_path, stream=True)
    i = cmd.index("--max-budget-usd")
    fake = FakeRun(init_line())
    with pytest.raises(ValueError):
        headless.probe_context(cmd[:i] + cmd[i + 2:], cwd=tmp_path, ledger=ledger, runner=fake)
    assert fake.calls == []


def test_parse_stream_cost_reads_the_result_line_among_other_messages():
    assert headless.parse_stream_cost(stream_with_cost(0.02)) == pytest.approx(0.02)
    assert headless.parse_stream_cost('{"type":"assistant"}\nno es json') == 0.0
