"""Tests de las simulaciones en el narrador (`harness/simulaciones.py` y `narrador simulacion`): contexto, una pregunta y su respuesta por separado. Sin modelo.

PROPÓSITO: fijar cómo se entrega un caso de `simulaciones/E<n>_*.md` por partes: la lista de casos, el
contexto con sus restricciones, cada pregunta sin su respuesta y la respuesta aparte.

POR QUÉ EXISTE: un caso trae las respuestas plegadas junto a las preguntas, y el título de cada
pregunta y la tabla «Plan de preguntas» dicen su task statement. Si la skill leyera el archivo, no
revelar antes de tiempo dependería solo de sus instrucciones; aquí lo garantiza el código, como en los
módulos y en D3.

QUÉ NO HACE: no comprueba el formato de los casos (eso es de `tests/test_simulaciones_formato.py`), no
puntúa ni guarda las respuestas de la persona y no mezcla preguntas de casos distintos.
"""

import re
from pathlib import Path

import pytest

from tests.contrato import require

require("3.7-codigo")  # se salta entero mientras falte `harness/simulaciones.py`

from harness.narrador import main, menu  # noqa: E402
from harness.simulaciones import UnknownCase, case_answer, case_context, case_question, list_cases  # noqa: E402
from tests.test_simulaciones_formato import ANSWER, CASES, questions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TS = re.compile(r"TS \d\.\d")
MIN_LEAK_LINE = 25
CODES = [path.name.split("_", 1)[0] for path in CASES]


def text_of(code: str) -> str:
    return next(path for path in CASES if path.name.startswith(code + "_")).read_text(encoding="utf-8")


def answer_lines(code: str) -> list[str]:
    """Líneas largas de todas las respuestas del caso, sin las etiquetas del plegado."""
    lines = []
    for question in questions(text_of(code)):
        body = ANSWER.search(question["body"]).group(0)
        lines += [line.strip() for line in body.splitlines() if len(line.strip()) >= MIN_LEAK_LINE and not line.strip().startswith("<")]
    return lines


def numbered(code: str) -> list[tuple[str, int]]:
    return [(code, question["n"]) for question in questions(text_of(code))]


EVERY_QUESTION = [pair for code in CODES for pair in numbered(code)]


# --- Lista de casos ----------------------------------------------------------------

def test_the_six_cases_are_listed_in_order_with_title_and_size():
    cases = list_cases()
    assert [code for code, _, _ in cases] == ["E1", "E2", "E3", "E4", "E5", "E6"]
    for code, title, size in cases:
        heading = text_of(code).split("\n# ", 1)[1].splitlines()[0]
        assert title and title in heading and not title.startswith(code)
        assert size == len(questions(text_of(code)))


# --- Contexto ----------------------------------------------------------------------

@pytest.mark.parametrize("code", CODES)
def test_the_context_brings_the_setting_and_the_constraints_and_nothing_else(code):
    text = case_context(code)
    source = text_of(code)
    setting = source.split("## Contexto", 1)[1].split("## ", 1)[0].strip()
    assert setting in text
    for rule in re.findall(r"^- R\d: .*$", source, flags=re.MULTILINE):
        assert rule in text
    # Cuántas preguntas son y cuánto tiempo se da: quien practica lo necesita para medirse.
    assert str(len(questions(source))) in text and "minutos" in text
    # Ni el plan de preguntas (dice la TS de cada una) ni las preguntas ni las respuestas.
    assert not TS.search(text) and "Plan de preguntas" not in text
    assert "- A. " not in text and "<details>" not in text
    for line in answer_lines(code):
        assert line not in text


# --- Pregunta y respuesta ------------------------------------------------------------

@pytest.mark.parametrize("code, number", EVERY_QUESTION)
def test_a_question_comes_alone_without_task_statement_or_answer(code, number):
    text = case_question(code, number)
    question = next(q for q in questions(text_of(code)) if q["n"] == number)
    heading = text.strip().splitlines()[0]
    assert heading == f"### Pregunta {number} ({question['kind']})", "el formato sí se dice; la TS, no"
    assert text.count("- A. ") == 1 and "<details>" not in text and "<summary>" not in text
    assert f"Pregunta {number + 1}" not in text
    for line in answer_lines(code):
        assert line not in text, f"{code}-{number} adelanta: {line[:60]}"


@pytest.mark.parametrize("code, number", EVERY_QUESTION)
def test_an_answer_comes_alone_with_its_task_statement_and_without_fold_tags(code, number):
    text = case_answer(code, number)
    question = next(q for q in questions(text_of(code)) if q["n"] == number)
    own = [line.strip() for line in ANSWER.search(question["body"]).group(0).splitlines() if len(line.strip()) >= MIN_LEAK_LINE and not line.strip().startswith("<")]
    assert text.strip().splitlines()[0].startswith(f"### Pregunta {number} (TS ")
    assert "<details>" not in text and "</details>" not in text and "<summary>" not in text
    assert re.search(r"^\*\*[A-D]", text, flags=re.MULTILINE), "la respuesta empieza por la letra"
    for line in own:
        assert line in text
    others = set(answer_lines(code)) - set(own)
    for line in others:
        assert line not in text, f"{code}-{number} trae la respuesta de otra pregunta"


def test_a_multiple_response_question_keeps_how_many_to_choose():
    assert "**Selecciona dos**" in case_question("E3", 3)


@pytest.mark.parametrize("code", ["e3", " E3 ", "E3"])
def test_the_case_code_is_read_in_any_case(code):
    assert case_context(code) == case_context("E3")


@pytest.mark.parametrize("call", [lambda: case_context("E9"), lambda: case_context("app1"), lambda: case_question("E3", 0), lambda: case_question("E3", 99), lambda: case_answer("E3", 99)])
def test_what_does_not_exist_is_rejected(call):
    with pytest.raises(UnknownCase):
        call()
    assert issubclass(UnknownCase, ValueError)


def test_cases_are_read_from_the_given_root(tmp_path):
    # Como el resto del narrador: con `root` se prueba sobre una copia sin tocar el repositorio.
    (tmp_path / "simulaciones").mkdir()
    (tmp_path / "simulaciones" / "E3_copia.md").write_text(text_of("E3").replace("# E3 · ", "# E3 · Copia de ", 1), encoding="utf-8")
    assert [(code, title.startswith("Copia de ")) for code, title, _ in list_cases(root=tmp_path)] == [("E3", True)]
    assert case_question("E3", 1, root=tmp_path) == case_question("E3", 1)


# --- Línea de comandos y menú --------------------------------------------------------

def test_cli_without_a_case_lists_them(capsys):
    assert main(["simulacion"]) == 0
    out = capsys.readouterr().out
    for code, title, size in list_cases():
        line = next(line for line in out.splitlines() if code in line)
        assert title in line and str(size) in line
    assert "- A. " not in out and not TS.search(out)


def test_cli_gives_the_context_a_question_and_its_answer(capsys):
    assert main(["simulacion", "E3"]) == 0
    assert capsys.readouterr().out == case_context("E3")
    assert main(["simulacion", "e3", "2"]) == 0
    assert capsys.readouterr().out == case_question("E3", 2)
    assert main(["simulacion", "E3", "2", "--respuesta"]) == 0
    assert capsys.readouterr().out == case_answer("E3", 2)


@pytest.mark.parametrize("args", [["simulacion", "E9"], ["simulacion", "E3", "99"], ["simulacion", "E3", "dos"], ["simulacion", "E3", "--respuesta"], ["simulacion", "--respuesta"]])
def test_cli_reports_a_bad_request_without_a_traceback(args, capsys):
    # La respuesta se pide de una pregunta concreta: `--respuesta` sin número no vuelca las del caso.
    assert main(args) == 2
    assert "[narrador]" in capsys.readouterr().err


def test_menu_offers_the_simulations_without_revealing_anything():
    text = menu()
    line = next(line for line in text.splitlines() if "simulacion" in line)
    assert "E1" in line or "E<n>" in line
    for code in CODES:
        for answer_line in answer_lines(code):
            assert answer_line not in text
