"""Tests del enunciado sin rótulo de viñeta (`harness.items.blind_statement` y `narrador item <id> --ciego`). Sin modelo.

PROPÓSITO: fijar el enunciado que usa la práctica mezclada. El rótulo de una comprobación corta
(`**C1 · TS 2.5-K3, K4, S3.**`) y el título de una pregunta de D3 (`TS 3.1 · Jerarquía…`,
`Pregunta 1 (TS 3.1 y 3.3)`) dicen de qué viñeta va la pregunta antes de contestarla.

POR QUÉ EXISTE: la práctica mezclada sirve para discriminar entre conceptos, y eso exige no saber de
qué tema es cada pregunta. La lista de `mixto` ya no enseña las viñetas; el enunciado tampoco debe.

QUÉ NO HACE: no cambia `Item.statement` ni el repaso de fallos, donde la viñeta ya se conoce. No quita
las menciones a una TS que formen parte de la prosa de la pregunta (`app2/07`).
"""

import re

import pytest

from tests.contrato import require

require("3.7-codigo")  # se salta entero mientras falte `harness.items.blind_statement`

from harness.items import all_items, blind_statement, find_item  # noqa: E402
from harness.narrador import main  # noqa: E402

TS = re.compile(r"TS \d\.\d")
MIN_LINE = 25


def first_line(text: str) -> str:
    return text.strip().splitlines()[0]


def test_a_short_check_keeps_its_number_and_loses_its_vignettes():
    text = blind_statement(find_item("app1/02:C1"))
    assert text.startswith("**C1.** Un agente tiene que cambiar")
    assert "TS 2.5" not in text and "- D. " in text


def test_a_d3_check_loses_the_title_that_names_its_task_statement():
    item = find_item("d3:C1")
    text = blind_statement(item)
    assert "Jerarquía y modularidad" not in text and not TS.search(text)
    assert first_line(text).startswith("Un monorepo")


def test_a_d3_integrated_question_keeps_its_number_only():
    text = blind_statement(find_item("d3:P1"))
    assert first_line(text) == "Pregunta 1"
    assert not TS.search(text)


@pytest.mark.parametrize("item", [item for item in all_items() if item.kind == "comprobacion"], ids=lambda item: item.id)
def test_no_short_check_names_a_task_statement_in_its_first_line(item):
    assert not TS.search(first_line(blind_statement(item)))


@pytest.mark.parametrize("item", all_items(), ids=lambda item: item.id)
def test_the_blind_statement_only_drops_the_label(item):
    text = blind_statement(item)
    assert "- A. " in text
    # Todo lo demás sigue igual: las líneas largas del enunciado, salvo la primera, están tal cual.
    for line in item.statement.strip().splitlines()[1:]:
        if len(line.strip()) >= MIN_LINE:
            assert line.strip() in text, f"{item.id} pierde: {line[:60]}"
    # La primera línea es la que pierde el rótulo; las demás no se reescriben.
    for line in text.strip().splitlines()[1:]:
        if len(line.strip()) >= MIN_LINE:
            assert line.strip() in item.statement, f"{item.id} añade: {line[:60]}"


def test_a_question_without_label_is_left_as_it_is():
    item = find_item("app1/01:P1")
    assert blind_statement(item).strip() == item.statement.strip()


# --- Línea de comandos ---------------------------------------------------------------

def test_cli_item_blind_prints_the_statement_without_the_label(capsys):
    assert main(["item", "app1/02:C1", "--ciego"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("**C1.** ") and "TS 2.5" not in out


def test_cli_item_without_the_flag_keeps_the_label(capsys):
    assert main(["item", "app1/02:C1"]) == 0
    assert "**C1 · TS 2.5-K3, K4, S3.**" in capsys.readouterr().out


def test_cli_the_answer_is_never_blind(capsys):
    # Con la respuesta ya se puede saber la viñeta: `--ciego` no la recorta.
    assert main(["item", "app1/02:C1", "--respuesta", "--ciego"]) == 0
    assert "TS 2.5" in capsys.readouterr().out
