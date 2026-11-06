"""Tests de estructura de la sección 4 de `d3_claude_code/README.md`: una comprobación corta por TS (3.1 a 3.5) y las preguntas integradas. Sin modelo.

PROPÓSITO: D3 no tiene módulos ejecutables, así que su práctica de recuperación vive en la sección 4. El
test comprueba que cada TS de 3.1 a 3.5 tiene su comprobación corta, que cada pregunta sigue el formato
(4 opciones, respuesta plegada que empieza por la letra y cita viñetas de su TS) y que las respuestas
no se delatan por posición ni por longitud (docs/estandares-flujo.md, «Ejercicios de evaluación»).

POR QUÉ EXISTE: la auditoría (D-04) vio 40 viñetas de D3 con solo tres preguntas finales.

QUÉ NO HACE: no juzga si la pregunta evalúa bien la viñeta ni si la respuesta es correcta; eso lo hace la
revisión contra la guía.
"""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "d3_claude_code" / "README.md").read_text(encoding="utf-8")
SHORT_TS = ["3.1", "3.2", "3.3", "3.4", "3.5"]
MAX_PER_LETTER = 3  # de 8 preguntas: ninguna letra domina
OPTION = re.compile(r"^- ([A-D])\. (.+)$", re.MULTILINE)
ANSWER = re.compile(r"<details>\s*<summary>Respuesta</summary>\s*\*\*([A-D])\.\*\*(.*?)</details>", re.DOTALL)


def section_four() -> str:
    return README.split("\n## 4 · ", 1)[1]


def question_blocks() -> dict[str, str]:
    """{título: texto} de cada pregunta (`####`) de la sección 4, hasta el siguiente encabezado."""
    blocks: dict[str, str] = {}
    current = None
    for line in section_four().splitlines():
        if line.startswith("#### "):
            current = line[5:].strip()
            blocks[current] = ""
        elif line.startswith("## ") or line.startswith("### "):
            current = None
        elif current is not None:
            blocks[current] += line + "\n"
    return blocks


def correct_letter(block: str) -> str:
    return ANSWER.search(block).group(1)


def test_every_ts_from_3_1_to_3_5_has_a_short_check():
    titles = [title for title in question_blocks() if title.startswith("TS ")]
    assert [title.split(" ")[1] for title in titles] == SHORT_TS, titles


def test_every_question_has_four_options_and_a_folded_answer():
    blocks = question_blocks()
    assert len(blocks) == 8, f"se esperan 5 comprobaciones cortas y 3 preguntas integradas, hay {len(blocks)}"
    for title, block in blocks.items():
        assert [letter for letter, _ in OPTION.findall(block)] == ["A", "B", "C", "D"], title
        assert ANSWER.search(block), f"{title}: falta la respuesta plegada que empieza por **X.**"


def test_each_short_check_cites_viñetas_of_its_own_ts():
    for title, block in question_blocks().items():
        if title.startswith("TS "):
            ts = title.split(" ")[1]
            answer = ANSWER.search(block).group(2)
            assert re.search(rf"TS {re.escape(ts)}-[KS]\d", answer), f"{title}: la respuesta no cita ninguna viñeta de TS {ts}"


def test_answers_are_spread_over_the_letters():
    letters = Counter(correct_letter(block) for block in question_blocks().values())
    assert len(letters) >= 3, letters
    assert max(letters.values()) <= MAX_PER_LETTER, letters


def test_the_correct_option_is_not_usually_the_longest():
    """Que la correcta sea la más larga la delata: como mucho en la mitad de las preguntas."""
    longest = 0
    for block in question_blocks().values():
        options = dict(OPTION.findall(block))
        right = correct_letter(block)
        if len(options[right]) > max(len(text) for letter, text in options.items() if letter != right):
            longest += 1
    assert longest <= 4, f"la correcta es la más larga en {longest} de 8 preguntas"
