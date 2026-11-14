"""Tests de D3 en el narrador (`harness.narrador.d3_phase` y `narrador fase d3 …`): comprobaciones y preguntas integradas sin revelar antes de tiempo. Sin modelo.

PROPÓSITO: fijar el contrato de D3 en el narrador (plan de mejoras, fase 3). D3 no tiene módulos
ejecutables ni ciclo de 5 pasos, así que solo expone cuatro fases, tomadas de la sección 4 de
`d3_claude_code/README.md`: `comprobaciones` y `soluciones` (4.1, una por TS) y `pregunta` y
`respuesta` (4.2, las integradas).

POR QUÉ EXISTE: D3 pesa un 20 % del examen y quedaba fuera de `/practica-guiada`: sus respuestas solo
estaban plegadas en el README, sin la garantía de revelación por código que tienen los módulos.

QUÉ NO HACE: no narra las secciones 1 a 3 de D3 (ruta por archivos, guion y práctica propia), que se
leen en el README. No comprueba el formato de la sección 4: eso es de `tests/test_d3_comprobaciones.py`.
"""

import pytest

from tests.contrato import require

require("3.3")  # se salta entero mientras falte `harness.narrador.d3_phase`

from harness.narrador import D3_PHASES, EXTRA_PHASES, PHASES, d3_phase, main, menu  # noqa: E402
from tests.test_d3_comprobaciones import ANSWER, question_blocks  # noqa: E402

MIN_LEAK_LINE = 25


def answer_lines(short: bool) -> list[str]:
    """Líneas largas de las respuestas de 4.1 (`short`) o de 4.2."""
    lines = []
    for title, block in question_blocks().items():
        if title.startswith("TS ") == short:
            body = ANSWER.search(block).group(0)
            lines += [line.strip() for line in body.splitlines() if len(line.strip()) >= MIN_LEAK_LINE]
    return lines


def test_d3_has_exactly_four_phases():
    assert D3_PHASES == ("comprobaciones", "soluciones", "pregunta", "respuesta")


def test_short_checks_phase_brings_the_five_statements_and_no_answer():
    text = d3_phase("comprobaciones")
    assert "<details>" not in text and "<summary>" not in text
    for ts in ("3.1", "3.2", "3.3", "3.4", "3.5"):
        assert f"TS {ts} · " in text
    assert text.count("- A. ") == 5 and text.count("- D. ") == 5
    assert "Pregunta 1" not in text, "las integradas son otra fase"
    for line in answer_lines(short=True) + answer_lines(short=False):
        assert line not in text, f"comprobaciones adelanta: {line[:60]}"


def test_solutions_phase_brings_the_five_answers_and_only_those():
    text = d3_phase("soluciones")
    for line in answer_lines(short=True):
        assert line in text
    for line in answer_lines(short=False):
        assert line not in text, f"soluciones adelanta una integrada: {line[:60]}"
    # Cada respuesta dice de qué TS es: sin eso, cinco letras seguidas no se pueden cotejar.
    for ts in ("3.1", "3.2", "3.3", "3.4", "3.5"):
        assert f"TS {ts}" in text


def test_question_phase_brings_the_three_integrated_statements_and_no_answer():
    text = d3_phase("pregunta")
    assert "<details>" not in text and "<summary>" not in text
    assert text.count("- A. ") == 3
    for number in (1, 2, 3):
        assert f"Pregunta {number}" in text
    for line in answer_lines(short=True) + answer_lines(short=False):
        assert line not in text, f"pregunta adelanta: {line[:60]}"


def test_answer_phase_brings_the_three_integrated_answers():
    text = d3_phase("respuesta")
    for line in answer_lines(short=False):
        assert line in text
    for number in (1, 2, 3):
        assert f"Pregunta {number}" in text


@pytest.mark.parametrize("name", sorted(set(PHASES + EXTRA_PHASES) - {"comprobaciones", "soluciones", "pregunta", "respuesta"}) + ["todo"])
def test_the_cycle_phases_do_not_exist_for_d3(name):
    # `ficha`, `ejercicio`, `ejecutar` y `contraste` son del ciclo de un módulo; el mensaje dice cuáles hay.
    with pytest.raises(ValueError, match="comprobaciones"):
        d3_phase(name)


# --- Línea de comandos y menú --------------------------------------------------------

@pytest.mark.parametrize("name", ["comprobaciones", "soluciones", "pregunta", "respuesta"])
def test_cli_gives_each_d3_phase(name, capsys):
    assert main(["fase", "d3", name]) == 0
    assert capsys.readouterr().out == d3_phase(name)


def test_cli_accepts_d3_in_capitals(capsys):
    assert main(["fase", "D3", "pregunta"]) == 0
    assert capsys.readouterr().out == d3_phase("pregunta")


def test_cli_rejects_a_cycle_phase_for_d3_without_a_traceback(capsys):
    assert main(["fase", "d3", "ficha"]) == 2
    assert "[narrador]" in capsys.readouterr().err


def test_menu_offers_d3_with_its_phases_and_keeps_the_pointer_to_the_readme():
    text = menu()
    assert "d3_claude_code/README.md" in text, "las secciones 1 a 3 se siguen leyendo en el README"
    line = next(line for line in text.splitlines() if "fase d3" in line)
    for name in ("comprobaciones", "pregunta"):
        assert name in line
    for line in answer_lines(short=True) + answer_lines(short=False):
        assert line not in text
