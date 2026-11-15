"""Tests del lector único de la sección 4 de `d3_claude_code/README.md` (paquete 5.4): `harness.items.d3_section4` y sus tres usuarios dan los mismos bloques. Sin modelo.

PROPÓSITO: fijar el contrato del paquete 5.4. `d3_section4(root)` devuelve, en orden, un `D3Block`
(`subsection`, `title`, `body`) por cada `####` de la sección 4: `subsection` es el número del `###`
que lo contiene («4.1», «4.2»…, o «» si no hay ninguno), `title` el texto del `####` sin espacios
sobrantes y `body` sus líneas hasta el siguiente encabezado (`##`, `###` o `####`), cada una con su
salto de línea. El narrador (`d3_blocks`), los ítems (`d3:C1`…, `d3:P1`…) y
`tests/test_d3_comprobaciones.py` lo usan en lugar de partir el README cada uno a su manera.

POR QUÉ EXISTE: tres lectores del mismo texto acaban discrepando en un caso borde (un `###` nuevo,
un `####` sin respuesta) y el narrador entrega entonces un bloque que los ítems no conocen.

QUÉ NO HACE: no comprueba el contenido de D3 (eso es `tests/test_d3_comprobaciones.py`) ni la no
revelación de las fases (`tests/test_narrador_d3.py`).
"""

from pathlib import Path

from tests.contrato import require

require("5.4")  # se salta entero mientras falte `harness.items.d3_section4`

from harness import items, narrador  # noqa: E402
from harness.items import D3Block, d3_section4  # noqa: E402
from tests import test_d3_comprobaciones  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_blocks_have_the_agreed_shape():
    blocks = d3_section4(ROOT)
    assert blocks and all(isinstance(b, D3Block) for b in blocks)
    assert D3Block._fields == ("subsection", "title", "body")
    assert {b.subsection for b in blocks} >= {"4.1", "4.2"}
    assert all(b.body == "" or b.body.endswith("\n") for b in blocks)


def test_short_checks_and_integrated_questions_are_in_their_subsections():
    by_title = {b.title: b.subsection for b in d3_section4(ROOT)}
    assert by_title["TS 3.1 · Jerarquía y modularidad de `CLAUDE.md`"] == "4.1"
    assert all(sub == "4.2" for title, sub in by_title.items() if title.startswith("Pregunta "))


def test_narrator_reads_the_same_blocks():
    assert narrador.d3_blocks(ROOT) == [(b.title, b.body) for b in d3_section4(ROOT)]


def test_d3_structure_tests_read_the_same_blocks():
    assert test_d3_comprobaciones.question_blocks() == {b.title: b.body for b in d3_section4(ROOT)}


def test_d3_items_are_the_answered_blocks_of_4_1_and_4_2_in_order():
    d3_items = [i for i in items.all_items(ROOT) if i.source == "d3"]
    answered = [b for b in d3_section4(ROOT) if b.subsection in ("4.1", "4.2") and "<summary>Respuesta</summary>" in b.body]
    assert [i.statement.splitlines()[0] for i in d3_items] == [b.title for b in answered]
    assert [i.id for i in d3_items] == [f"d3:C{n}" for n in range(1, 6)] + [f"d3:P{n}" for n in range(1, len(d3_items) - 4)]


def test_nobody_else_splits_section_4():
    # Solo `harness/items.py` parte el README por «## 4 · ».
    for path in ("harness/narrador.py", "tests/test_d3_comprobaciones.py"):
        assert "## 4 · " not in (ROOT / path).read_text(encoding="utf-8"), path
    assert (ROOT / "harness/items.py").read_text(encoding="utf-8").count("## 4 · ") == 1
