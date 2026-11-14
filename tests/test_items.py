"""Tests de `harness/items.py`: cada pregunta y comprobación corta como un ítem con id, enunciado y respuesta separados. Sin modelo.

PROPÓSITO: fijar el contrato del ítem, la unidad que comparten el repaso de fallos, la práctica
mezclada y D3 en el narrador (plan de mejoras, fase 3). Un ítem es una pregunta tipo examen de un
módulo (`app1/01:P1`), una comprobación corta (`app1/02:C1`) o una pregunta de la sección 4 de D3
(`d3:C1`…`d3:C5` para las comprobaciones por TS y `d3:P1`…`d3:P3` para las integradas).

POR QUÉ EXISTE: el narrador entrega fases enteras de un módulo. Para repasar una viñeta fallada o
mezclar preguntas de módulos distintos hace falta sacar una sola pregunta, sin su respuesta y sin las
demás. Los README siguen siendo la única fuente: el ítem se lee de ellos cada vez.

QUÉ NO HACE: no juzga el contenido de las preguntas ni comprueba el formato de los README (eso es de
`tests/test_readme_modulos.py`, `tests/test_comprobaciones_cortas.py` y `tests/test_d3_comprobaciones.py`).
"""

import re
from pathlib import Path

import pytest

from tests.contrato import require

require("3.1")  # se salta entero mientras falte `harness/items.py`

from harness.items import Item, UnknownItem, all_items, find_item, item_for  # noqa: E402
from harness.narrador import main, route  # noqa: E402
from tests.test_comprobaciones_cortas import cited  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONCEPT_ROW = re.compile(r"^\| (TS \d\.\d-[KS]\d) \| (\S+) \| ☑ \|", re.MULTILINE)
ITEM_ID = re.compile(r"(app\d/\d{2}|d3):[PC]\d+")
# Las líneas cortas («```», «---») se repiten legítimamente; solo las largas delatan una respuesta.
MIN_LEAK_LINE = 25


def destinations() -> dict[str, str]:
    """{viñeta: origen}, con el destino de `CONCEPTOS.md` reducido a `appN/NN` o `d3`."""
    text = (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")
    return {vignette: destination.split("_", 1)[0] for vignette, destination in CONCEPT_ROW.findall(text)}


def leak_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if len(line.strip()) >= MIN_LEAK_LINE]


# --- Inventario ----------------------------------------------------------------

def test_every_item_has_a_well_formed_unique_id():
    items = all_items()
    ids = [item.id for item in items]
    assert len(ids) == len(set(ids))
    for item in items:
        assert isinstance(item, Item)
        assert ITEM_ID.fullmatch(item.id), item.id
        assert item.id.startswith(item.source + ":")
        assert item.kind == ("pregunta" if ":P" in item.id else "comprobacion")


def test_every_delivered_module_has_its_first_question():
    ids = {item.id for item in all_items()}
    for module in route():
        assert f"{module.id}:P1" in ids, module.id


def test_a_module_with_two_questions_gives_two_items():
    # `app2/04` lleva una pregunta de respuesta única y otra multiple-response, cada una con su «Paso 4».
    first, second = find_item("app2/04:P1"), find_item("app2/04:P2")
    assert "Pregunta 1" in first.statement and "Pregunta 2" not in first.statement
    assert "Pregunta 2" in second.statement and "Selecciona" in second.statement
    assert first.answer != second.answer


def test_short_checks_are_items_numbered_like_in_the_readme():
    item = find_item("app1/02:C1")
    assert item.kind == "comprobacion"
    assert "**C1 · TS 2.5-K3, K4, S3.**" in item.statement and "- D. " in item.statement
    assert "C2 ·" not in item.statement, "un ítem es una sola comprobación"


def test_d3_gives_five_short_checks_and_three_integrated_questions():
    d3 = [item.id for item in all_items() if item.source == "d3"]
    assert d3 == ["d3:C1", "d3:C2", "d3:C3", "d3:C4", "d3:C5", "d3:P1", "d3:P2", "d3:P3"]
    assert "monorepo" in find_item("d3:C1").statement  # la comprobación de TS 3.1
    assert find_item("d3:P1").kind == "pregunta"


def test_items_follow_the_reading_route_and_d3_goes_last():
    sources = list(dict.fromkeys(item.source for item in all_items()))
    assert sources == [module.id for module in route()] + ["d3"]


# --- Enunciado y respuesta, separados --------------------------------------------

@pytest.mark.parametrize("item", all_items(), ids=lambda item: item.id)
def test_statement_never_carries_its_answer(item):
    assert "<details>" not in item.statement and "<summary>" not in item.statement
    assert "Paso 5" not in item.statement
    assert "- A. " in item.statement, "el enunciado trae sus opciones"
    assert re.match(r"\*\*[A-D]", item.answer.strip()), f"la respuesta empieza por la letra: {item.answer[:40]!r}"
    for line in leak_lines(item.answer):
        assert line not in item.statement, f"el enunciado adelanta: {line[:60]}"


@pytest.mark.parametrize("item", all_items(), ids=lambda item: item.id)
def test_vignettes_are_the_ones_the_item_names(item):
    """Las viñetas de un ítem son las que citan su respuesta y, en una comprobación corta, su título."""
    assert cited(item.answer) <= item.vignettes
    assert item.domains == {f"D{vignette[3]}" for vignette in item.vignettes}


def test_only_the_support_module_has_a_question_without_vignettes():
    """`app2/03` es apoyo técnico sin viñeta propia: su pregunta se alcanza por id, pero no evalúa la guía."""
    assert [item.id for item in all_items() if not item.vignettes] == ["app2/03:P1"]
    assert find_item("app2/03:P1").domains == frozenset()


# --- Buscar ----------------------------------------------------------------------

@pytest.mark.parametrize("text", ["app1/02:C1", "APP1/02:c1", " app1/02:C1 "])
def test_find_item_accepts_common_spellings(text):
    assert find_item(text).id == "app1/02:C1"


@pytest.mark.parametrize("text", ["app1/02:C99", "app9/01:P1", "app1/02", "d3:C9", ""])
def test_find_item_rejects_what_does_not_exist(text):
    with pytest.raises(UnknownItem):
        find_item(text)
    assert issubclass(UnknownItem, ValueError)


@pytest.mark.parametrize("vignette, source", sorted(destinations().items()))
def test_every_vignette_has_an_item_to_review_it(vignette, source):
    """Sin módulo, el ítem sale del destino de `CONCEPTOS.md`; si es de una app, lo cita."""
    item = item_for(vignette)
    assert item.source == source
    if source != "d3":
        # La cobertura de evaluación garantiza que el módulo de destino la cita en alguna respuesta.
        assert vignette in item.vignettes


def test_item_for_prefers_the_short_check_that_names_the_vignette():
    # TS 2.5-K3 va en el título de C1 de `app1/02`: es el ángulo más directo para repasarla.
    assert item_for("TS 2.5-K3", "app1/02").id == "app1/02:C1"


def test_item_for_falls_back_to_the_first_question_of_the_module():
    # Una viñeta que el módulo indicado no cita (la persona anotó otro módulo): se repasa con su pregunta.
    assert item_for("TS 2.5-K3", "app1/01").id == "app1/01:P1"


def test_item_for_d3_uses_the_short_check_of_its_task_statement():
    # No todas las viñetas de D3 se citan en una respuesta: se repasan con la comprobación de su TS.
    assert item_for("TS 3.3-K1").id in {"d3:C3", "d3:P1"}
    assert item_for("TS 3.4-K1").source == "d3"


def test_item_for_d3_goes_to_the_destination_when_d3_has_no_check_for_that_task_statement():
    # TS 3.6 es del dominio 3, pero la introduce `app3/11` y D3 solo tiene comprobaciones de 3.1 a 3.5.
    # Anotarla con módulo «D3» es un error fácil: se repasa con el ítem de su destino, no se descarta.
    item = item_for("TS 3.6-K1", "D3")
    assert item.source == "app3/11" and "TS 3.6-K1" in item.vignettes


def test_item_for_rejects_an_unknown_vignette():
    with pytest.raises(UnknownItem):
        item_for("TS 9.9-K9")


# --- Línea de comandos -------------------------------------------------------------

def test_cli_item_prints_the_statement_and_only_then_the_answer(capsys):
    item = find_item("app1/02:C1")
    assert main(["item", "app1/02:C1"]) == 0
    statement = capsys.readouterr().out
    assert "**C1 · TS 2.5-K3, K4, S3.**" in statement
    for line in leak_lines(item.answer):
        assert line not in statement
    assert main(["item", "app1/02:C1", "--respuesta"]) == 0
    answer = capsys.readouterr().out
    for line in leak_lines(item.answer):
        assert line in answer


def test_cli_item_reports_an_unknown_id_without_a_traceback(capsys):
    assert main(["item", "app1/02:C99"]) == 2
    assert "[narrador]" in capsys.readouterr().err
