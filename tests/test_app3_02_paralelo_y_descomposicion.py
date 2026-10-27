"""Tests de app3/02_paralelo_y_descomposicion: agrupación de llamadas por respuesta, latencia, comprobador de brechas, cadena de prompts y paquete legacy. Sin modelo."""

import pytest

from app3_sistema_multiagente.coordinator_gate import coordinator_gate
from harness.recorder import RunRecord, ToolCall
from tests.cargar import load

mod = load("app3_sistema_multiagente/02_paralelo_y_descomposicion.py")


def test_coordinator_options_carry_the_gate():
    # Lo usan paralelo, refinamiento y la parte adaptativa de descomposicion; la cadena fija y legacy no tienen coordinador.
    options = mod.coordinator_options("x", budget=0.5, model="sonnet", subagent_model="haiku")
    (matcher,) = options.hooks["PreToolUse"]
    assert matcher.hooks == [coordinator_gate]


def agent(cid, subagent, response):
    return ToolCall(cid, "Agent", {"subagent_type": subagent, "prompt": "x"}, response, "principal", True, False, "ok")


PARALLEL = RunRecord(tool_calls=[
    agent("a1", "tickets_analyst", "r1"), agent("a2", "tickets_analyst", "r1"), agent("a3", "kb_analyst", "r1"),
    ToolCall("s1", "mcp__investigacion__search_tickets", {}, "r2", "tickets_analyst", True, False, "{}"),
])
SEQUENTIAL = RunRecord(tool_calls=[agent("a1", "tickets_analyst", "r1"), agent("a2", "tickets_analyst", "r3"),
                                   agent("a3", "kb_analyst", "r5")])


def test_agent_calls_grouped_by_response():
    assert mod.agent_groups(PARALLEL) == {"r1": ["tickets_analyst", "tickets_analyst", "kb_analyst"]}
    assert mod.agent_groups(SEQUENTIAL) == {"r1": ["tickets_analyst"], "r3": ["tickets_analyst"], "r5": ["kb_analyst"]}
    assert mod.max_parallel(PARALLEL) == 3 and mod.max_parallel(SEQUENTIAL) == 1
    assert mod.max_parallel(RunRecord()) == 0


def test_latency_comparison():
    assert mod.speedup(parallel_s=20.0, sequential_s=50.0) == pytest.approx(2.5)
    assert mod.speedup(parallel_s=0.0, sequential_s=5.0) is None


def test_gap_checker_lists_missing_subtopics():
    text = "La VPN falla desde casa (TCK-4015) y la wifi de las salas no funciona (TCK-4012)."
    assert mod.gaps(text) == ["impresora"]
    assert mod.gaps("Todo: VPN, wifi y la impresora de planta.") == []
    assert mod.gaps(None) == list(mod.REQUIRED_SUBTOPICS)


def test_refinement_message_targets_only_the_gaps():
    message = mod.refinement_message(["impresora"])
    assert "impresora" in message and "vpn" not in message.lower()


def test_chain_feeds_each_step_with_previous_output():
    prompts = mod.chain_prompts(["paso uno", "paso dos", "paso tres"], ["salida 1", "salida 2"])
    assert prompts[0] == "paso uno"
    assert "salida 1" in prompts[1] and "paso dos" in prompts[1]
    assert "salida 2" in prompts[2] and "salida 1" not in prompts[2]


def test_hidden_dependency_detection():
    assert mod.mentions_hidden_dependency(
        "Ojo: depreciacion importa almacen dentro de valor_actual y lee _CACHE_ASIGNADOS, que llena asignaciones."
    )
    assert not mod.mentions_hidden_dependency("Plan: tests para fechas, modelos e informes.")
    # Los imports de cabecera de informes.py o asignaciones.py no son la dependencia escondida.
    assert not mod.mentions_hidden_dependency("informes.py hace from . import almacen y usa _CACHE_ASIGNADOS de asignaciones.")
    assert mod.mentions_hidden_dependency("Un equipo asignado conserva un valor residual: depreciacion depende de asignaciones.")


def test_legacy_package_location():
    files = sorted(p.name for p in mod.LEGACY_DIR.glob("*.py"))
    assert files == ["__init__.py", "almacen.py", "asignaciones.py", "depreciacion.py", "fechas.py",
                     "informes.py", "modelos.py"]


def test_parts_and_variants():
    assert mod.PARTS == ["paralelo", "refinamiento", "descomposicion", "legacy"]
    assert mod.coordinator_prompt("paralelo") != mod.coordinator_prompt("secuencial")
