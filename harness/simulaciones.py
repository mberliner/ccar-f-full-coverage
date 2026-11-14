"""Simulaciones por escenario en el narrador: lista de casos, contexto, una pregunta y su respuesta por separado.

PROPÓSITO: entregar un caso de `simulaciones/E<n>_*.md` por partes. El contexto trae el escenario, las
restricciones compartidas, cuántas preguntas son y cuánto tiempo se da; cada pregunta sale sin su
task statement (solo se dice el formato) y su respuesta sale aparte, con su TS y sin etiquetas de plegado.

POR QUÉ EXISTE: un caso trae las respuestas plegadas junto a las preguntas, y el título de cada pregunta
y la tabla «Plan de preguntas» dicen su TS. Si la skill leyera el archivo, no revelar antes de tiempo
dependería solo de sus instrucciones; aquí lo garantiza el código, como en los módulos y en D3.

QUÉ NO HACE: no comprueba el formato de los casos (eso es de `tests/test_simulaciones_formato.py`), no
puntúa ni guarda las respuestas de la persona, no llama al modelo y no mezcla preguntas de casos distintos.
"""

import re
from pathlib import Path

from harness.credentials import ROOT

CASE_FILE = re.compile(r"(E[1-6])_.*\.md")
CASE_CODE = re.compile(r"E[1-6]")
TITLE = re.compile(r"^# (E[1-6]) · (.+)$", re.MULTILINE)
QUESTION_HEADING = re.compile(r"^### Pregunta (\d+) \((TS [^·)]+) · ([^)]+)\)$", re.MULTILINE)
DETAILS_ANSWER = re.compile(r"<details>\s*<summary>Respuesta</summary>(.*?)</details>", re.DOTALL)
QUESTIONS_SECTION = "## Preguntas"
COUNT = re.compile(r"> \*\*Preguntas:\*\* (\d+)")
TIME = re.compile(r"> \*\*Tiempo orientativo:\*\* (.+)")


class UnknownCase(ValueError):
    """El caso o la pregunta no existen."""


def _files(root: Path) -> dict[str, Path]:
    folder = root / "simulaciones"
    found = {}
    for path in sorted(folder.glob("E*.md")) if folder.is_dir() else []:
        match = CASE_FILE.fullmatch(path.name)
        if match:
            found[match.group(1)] = path
    return found


def _text(code: str, root: Path) -> tuple[str, str]:
    """(código normalizado, texto del caso)."""
    wanted = code.strip().upper()
    path = _files(root).get(wanted) if CASE_CODE.fullmatch(wanted) else None
    if path is None:
        known = ", ".join(_files(root)) or "ninguno"
        raise UnknownCase(f"no existe el caso «{code}» (casos: {known})")
    return wanted, path.read_text(encoding="utf-8")


def _questions(text: str) -> list[tuple[int, str, str, str]]:
    """[(número, TS, formato, cuerpo)] de cada `### Pregunta N (…)`, con el encabezado original dentro del cuerpo."""
    found = list(QUESTION_HEADING.finditer(text))
    blocks = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        blocks.append((int(match.group(1)), match.group(2).strip(), match.group(3).strip(), text[match.start():end]))
    return blocks


def _question(code: str, number: int, root: Path) -> tuple[str, str, str, str]:
    wanted, text = _text(code, root)
    for found in _questions(text):
        if found[0] == number:
            return found
    raise UnknownCase(f"el caso {wanted} no tiene la pregunta {number}")


def list_cases(root: Path = ROOT) -> list[tuple[str, str, int]]:
    """[(código, título, número de preguntas)] de los casos escritos, en orden."""
    cases = []
    for code, path in _files(root).items():
        text = path.read_text(encoding="utf-8")
        title = TITLE.search(text)
        cases.append((code, title.group(2).strip() if title else path.stem, len(_questions(text))))
    return cases


def case_context(code: str, root: Path = ROOT) -> str:
    """Escenario, restricciones compartidas, número de preguntas y tiempo; sin plan, preguntas ni TS."""
    wanted, text = _text(code, root)
    title = TITLE.search(text)
    setting = text.split("## Contexto", 1)[1].split("\n## ", 1)[0].strip()
    rules = text.split("## Restricciones compartidas", 1)[1].split("\n## ", 1)[0].strip()
    count = COUNT.search(text)
    minutes = TIME.search(text)
    size = int(count.group(1)) if count else len(_questions(text))
    lines = [
        f"# {wanted} · {title.group(2).strip() if title else ''}".rstrip(" ·"),
        "",
        f"{size} preguntas · tiempo orientativo: {minutes.group(1).strip() if minutes else 'sin indicar'}",
        "",
        "## Contexto",
        "",
        setting,
        "",
        "## Restricciones compartidas",
        "",
        rules,
    ]
    return "\n".join(lines) + "\n"


def case_question(code: str, number: int, root: Path = ROOT) -> str:
    """La pregunta sin su respuesta y con el encabezado `### Pregunta N (formato)`, sin TS."""
    _, _, kind, body = _question(code, number, root)
    statement = body.split("<details>", 1)[0].split("\n", 1)[1].strip()
    return f"### Pregunta {number} ({kind})\n\n{statement}\n"


def case_answer(code: str, number: int, root: Path = ROOT) -> str:
    """La respuesta de una pregunta, con su encabezado (TS incluida) y sin las etiquetas del plegado."""
    _, ts, kind, body = _question(code, number, root)
    found = DETAILS_ANSWER.search(body)
    answer = found.group(1).strip() if found else ""
    return f"### Pregunta {number} ({ts} · {kind})\n\n{answer}\n"
