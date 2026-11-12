"""Tests de las «Comprobaciones cortas» de los módulos y de la cobertura de evaluación. Sin modelo.

PROPÓSITO: comprobar el formato del bloque opcional `### Comprobaciones cortas` de una sección de
módulo (una pregunta breve por idea que la pregunta principal no toca) y que cada viñeta que un
módulo introduce aparece en alguna respuesta evaluable de ese módulo: la del «Paso 4» o la de una
comprobación corta.

POR QUÉ EXISTE: la pregunta tipo examen de un módulo cubre unas pocas de sus viñetas. Las demás solo
se veían desde un ángulo (la predicción y su contraste). El formato es el que ya usa D3
(`tests/test_d3_comprobaciones.py`), llevado a las apps.

QUÉ NO HACE: no juzga si la pregunta evalúa bien la viñeta ni si la respuesta es correcta: eso es de
la revisión contra la guía. La cobertura es por módulo de destino, no por dominio.
"""

import re
from pathlib import Path

import pytest

from tests.test_readme_modulos import ANSWER_BLOCK, MAX_CORRECT_RATIO, all_sections, correct_ratio

ROOT = Path(__file__).resolve().parent.parent
HEADING = "### Comprobaciones cortas"
# «**C1 · TS 2.5-K3, K4, S3.** Enunciado…»: número, viñetas que practica y enunciado.
CHECK = re.compile(r"^\*\*C(\d+) · (TS [^*]+?)\.\*\* ", re.MULTILINE)
CHECK_ANSWER = re.compile(r"<details>\s*<summary>Comprobación C(\d+) · Respuesta</summary>\s*\*\*([A-D])\.\*\*(.*?)</details>", re.DOTALL)
OPTION = re.compile(r"^- ([A-D])\. (.+)$", re.MULTILINE)
VIGNETTE_RUN = re.compile(r"TS (\d\.\d)-([KS]\d)((?:(?:, | y )(?:\d\.\d-)?[KS]\d)*)")
# Viñetas que un módulo introduce y que aún no tienen respuesta evaluable en su sección. Vacía desde la fase 2b
# (R4); se conserva por si un módulo nuevo necesita entrar por fases, con la forma {"app1/01": {"TS 1.1-K3"}}.
# `test_pending_coverage_is_really_missing` obliga a borrar las que ya están.
PENDING_COVERAGE: dict[str, set[str]] = {}


def cited(text: str) -> set[str]:
    """Las viñetas que nombra un texto, desplegando «TS 2.5-K3, K4, S3» y «TS 4.6-K3, 1.6-S2»."""
    found = set()
    for run in VIGNETTE_RUN.finditer(text):
        ts = run.group(1)
        found.add(f"TS {ts}-{run.group(2)}")
        for other_ts, code in re.findall(r"(?:, | y )(?:(\d\.\d)-)?([KS]\d)", run.group(3)):
            ts = other_ts or ts
            found.add(f"TS {ts}-{code}")
    return found


def checks_block(section: str) -> str:
    """El cuerpo de `### Comprobaciones cortas`, hasta el siguiente `###` o la línea del paso 5; «» si no hay."""
    start = section.find(HEADING)
    if start < 0:
        return ""
    body = section[start + len(HEADING):]
    for stop in ("\n### ", "\n**Paso 5 ·**"):
        cut = body.find(stop)
        if cut >= 0:
            body = body[:cut]
    return body


def check_problems(section: str) -> list[str]:
    """Desvíos del formato de las comprobaciones cortas de una sección."""
    block = checks_block(section)
    if not block:
        return []
    problems = []
    titles = list(CHECK.finditer(block))
    answers = {int(number): (letter, body) for number, letter, body in CHECK_ANSWER.findall(block)}
    if [int(title.group(1)) for title in titles] != list(range(1, len(titles) + 1)):
        problems.append("las comprobaciones no van numeradas C1, C2… en orden")
    for position, title in enumerate(titles):
        number = int(title.group(1))
        end = titles[position + 1].start() if position + 1 < len(titles) else len(block)
        text = block[title.start():end]
        options = dict(OPTION.findall(text.split("<details>", 1)[0]))
        if list(options) != ["A", "B", "C", "D"]:
            problems.append(f"C{number} no tiene las opciones A a D")
            continue
        if number not in answers:
            problems.append(f"C{number} sin respuesta plegada «Comprobación C{number} · Respuesta» que empiece por **X.**")
            continue
        letter, body = answers[number]
        if not cited(title.group(2)) & cited(body):
            problems.append(f"la respuesta de C{number} no cita ninguna de las viñetas de su título")
        if correct_ratio(letter, {key: len(value) for key, value in options.items()}) > MAX_CORRECT_RATIO:
            problems.append(f"en C{number} la opción correcta es mucho más larga que las demás")
    letters = [letter for letter, _ in answers.values()]
    if len(letters) >= 3 and len(set(letters)) == 1:
        problems.append("todas las comprobaciones tienen la misma letra correcta")
    return problems


def introduced() -> dict[str, set[str]]:
    """{`app1/02`: viñetas que `CONCEPTOS.md` le asigna y están introducidas}."""
    found: dict[str, set[str]] = {}
    for line in (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| (TS [\d.]+-[KS]\d) \| (app\d/\d{2})_[^|]* \| ☑ \|", line)
        if match:
            found.setdefault(match.group(2), set()).add(match.group(1))
    return found


def evaluated() -> dict[str, set[str]]:
    """{`app1/02`: viñetas citadas en sus respuestas del Paso 4 y de las comprobaciones cortas}."""
    found = {}
    for name, body in all_sections().items():
        folder, number = name.split(" ")
        answers = " ".join(ANSWER_BLOCK.findall(body)) + " ".join(text for _, _, text in CHECK_ANSWER.findall(body))
        found[f"{folder.split('_')[0]}/{number}"] = cited(answers)
    return found


def missing_coverage() -> dict[str, set[str]]:
    seen = evaluated()
    return {module: vignettes - seen.get(module, set()) for module, vignettes in introduced().items() if vignettes - seen.get(module, set())}


# --- Lógica, con texto sintético ----------------------------------------------

GOOD = """### Pregunta tipo examen

Pregunta principal.

### Comprobaciones cortas

Opcionales.

**C1 · TS 2.5-K3, K4.** ¿Qué pasa?

- A. una cosa cualquiera
- B. otra cosa distinta
- C. una tercera cosa
- D. la cuarta opción

<details>
<summary>Comprobación C1 · Respuesta</summary>

**B.** Porque sí (TS 2.5-K4).
</details>

**Paso 5 ·** anota.
"""


def test_cited_expands_runs_of_vignettes():
    assert cited("(TS 2.5-K3, K4, S3)") == {"TS 2.5-K3", "TS 2.5-K4", "TS 2.5-S3"}
    assert cited("TS 4.6-K3, 4.6-S2, 1.6-K2 y S2") == {"TS 4.6-K3", "TS 4.6-S2", "TS 1.6-K2", "TS 1.6-S2"}
    assert cited("sin viñetas") == set()


def test_check_problems_accepts_the_documented_format():
    assert check_problems(GOOD) == []
    assert check_problems("### Pregunta tipo examen\nsin comprobaciones\n") == []


def test_check_problems_detects_each_deviation():
    three = GOOD.replace("- D. la cuarta opción\n", "")
    assert check_problems(three) == ["C1 no tiene las opciones A a D"]
    unanswered = GOOD.replace("Comprobación C1", "Comprobación C2")
    assert check_problems(unanswered) == ["C1 sin respuesta plegada «Comprobación C1 · Respuesta» que empiece por **X.**"]
    foreign = GOOD.replace("(TS 2.5-K4)", "(TS 1.1-K1)")
    assert check_problems(foreign) == ["la respuesta de C1 no cita ninguna de las viñetas de su título"]
    long = GOOD.replace("- B. otra cosa distinta", "- B. otra cosa distinta, pero explicada con muchísimas más palabras que las demás")
    assert check_problems(long) == ["en C1 la opción correcta es mucho más larga que las demás"]
    misnumbered = GOOD.replace("**C1 ·", "**C2 ·").replace("Comprobación C1", "Comprobación C2")
    assert "las comprobaciones no van numeradas C1, C2… en orden" in check_problems(misnumbered)


# --- Sobre los README reales ---------------------------------------------------

def test_short_checks_follow_the_format():
    failing = {name: check_problems(body) for name, body in all_sections().items() if check_problems(body)}
    assert not failing, f"comprobaciones cortas mal formadas: {failing}"


def test_short_checks_only_cite_introduced_vignettes():
    """Regla «una vez»: una comprobación practica viñetas ya introducidas, en cualquier destino."""
    known = set(re.findall(r"\| (TS [\d.]+-[KS]\d) \| [^|]+ \| ☑ \|", (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")))
    failing = {}
    for name, body in all_sections().items():
        unknown = cited(checks_block(body)) - known
        if unknown:
            failing[name] = sorted(unknown)
    assert not failing, f"comprobaciones que citan viñetas no introducidas: {failing}"


def test_every_introduced_vignette_is_evaluated_in_its_module():
    failing = {
        module: sorted(vignettes - PENDING_COVERAGE.get(module, set()))
        for module, vignettes in missing_coverage().items()
        if vignettes - PENDING_COVERAGE.get(module, set())
    }
    assert not failing, f"viñetas sin ninguna respuesta evaluable en su módulo (Paso 4 o comprobación corta): {failing}"


@pytest.mark.parametrize("module", sorted(PENDING_COVERAGE))
def test_pending_coverage_is_really_missing(module):
    """Una viñeta pendiente que ya tiene respuesta debe borrarse de la lista."""
    stale = PENDING_COVERAGE[module] - missing_coverage().get(module, set())
    assert not stale, f"{module}: ya están evaluadas, bórralas de PENDING_COVERAGE: {sorted(stale)}"
