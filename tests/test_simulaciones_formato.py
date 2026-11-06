"""Tests del formato de las simulaciones por escenario (`docs/simulaciones-por-escenario.md`, `plantillas/simulacion/`). Sin modelo.

PROPÓSITO: definir y comprobar el formato antes de escribir ningún caso. Un caso (`simulaciones/E<n>_*.md`) agrupa
8 a 10 preguntas sobre un mismo escenario de la guía, con un contexto y unas restricciones compartidas, y mezcla las
preguntas de respuesta única y las multiple-response. El validador `case_problems` comprueba esa estructura; la
especificación se comprueba contra los seis escenarios de la guía y los pesos del blueprint de `CONCEPTOS.md`.

POR QUÉ EXISTE: auditoría G-07. El examen presenta 4 escenarios de un banco de 6, cada uno con varias preguntas que
comparten contexto, y la práctica era solo de preguntas sueltas por módulo. Fijar el formato ahora permite que las
tandas C y D lo tengan en cuenta, y que los casos nazcan ya comprobados.

QUÉ NO HACE: no escribe ningún caso ni comprueba que una pregunta evalúe bien su viñeta (lo hace la revisión contra
la guía). Hoy `simulaciones/` no existe, así que la comprobación sobre casos reales no se ejerce hasta que haya uno.
"""

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "simulaciones-por-escenario.md"
TEMPLATE = ROOT / "plantillas" / "simulacion" / "ESCENARIO.md"
CASES = sorted((ROOT / "simulaciones").glob("E*.md")) if (ROOT / "simulaciones").is_dir() else []
# Los seis escenarios de la guía v1.0 y sus dominios principales.
SCENARIOS = {
    "E1": ("Customer Support Resolution Agent", {"D1", "D2", "D5"}),
    "E2": ("Code Generation with Claude Code", {"D3", "D5"}),
    "E3": ("Multi-Agent Research System", {"D1", "D2", "D5"}),
    "E4": ("Developer Productivity with Claude", {"D1", "D2", "D3"}),
    "E5": ("Claude Code for Continuous Integration", {"D3", "D4"}),
    "E6": ("Structured Data Extraction", {"D4", "D5"}),
}
EXAM_ITEMS = 60  # la guía: 60 ítems
# Un caso de estudio lleva de 8 a 10 preguntas; uno de examen completo, 15 (60 ítems entre 4 escenarios).
MIN_Q, MAX_Q, MIN_MULTI = 8, 15, 2
WORDS = {"dos": 2, "tres": 3, "cuatro": 4}
SECTIONS = ["## Contexto", "## Restricciones compartidas", "## Plan de preguntas", "## Preguntas"]
HEADING = re.compile(r"^### Pregunta (\d+) \((TS \d\.\d(?: y \d\.\d)*) · (una respuesta|multiple-response)\)$", re.MULTILINE)
OPTION = re.compile(r"^- ([A-D])\. ", re.MULTILINE)
ANSWER = re.compile(r"<details>\s*<summary>Respuesta</summary>\s*\*\*([A-D](?:(?:, | y )[A-D])*)\.\*\*(.*?)</details>", re.DOTALL)


def questions(text: str) -> list[dict]:
    """Cada `### Pregunta N (…)` con su formato, sus viñetas de TS y su cuerpo."""
    found = list(HEADING.finditer(text))
    blocks = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        blocks.append({"n": int(match.group(1)), "ts": re.findall(r"\d\.\d", match.group(2)), "kind": match.group(3), "body": text[match.end():end]})
    return blocks


def case_problems(text: str) -> list[str]:
    """Desvíos del formato de un caso. Vacía si cumple."""
    problems = []
    scenario = re.search(r"> \*\*Escenario:\*\* (E[1-6])\b", text)
    domains = re.search(r"> \*\*Dominios principales:\*\* (.+)", text)
    declared = re.search(r"> \*\*Preguntas:\*\* (\d+)", text)
    if not scenario:
        problems.append("falta «> **Escenario:** E1…E6»")
    elif domains and set(re.findall(r"D\d", domains.group(1))) != SCENARIOS[scenario.group(1)][1]:
        problems.append(f"los dominios principales no son los de {scenario.group(1)}")
    if not domains:
        problems.append("falta «> **Dominios principales:**»")
    problems += [f"falta la sección «{section}»" for section in SECTIONS if section not in text]
    if len(re.findall(r"^- R\d+: ", text, re.MULTILINE)) < 2:
        problems.append("hacen falta al menos 2 restricciones compartidas («- R1: …»)")

    blocks = questions(text)
    if not MIN_Q <= len(blocks) <= MAX_Q:
        problems.append(f"un caso lleva entre {MIN_Q} y {MAX_Q} preguntas y hay {len(blocks)}")
    if not declared or int(declared.group(1)) != len(blocks):
        problems.append("«> **Preguntas:**» no coincide con las preguntas que hay")
    if [block["n"] for block in blocks] != list(range(1, len(blocks) + 1)):
        problems.append("las preguntas no están numeradas de 1 a N en orden")
    plan_rows = [line for line in text.split("## Plan de preguntas", 1)[-1].split("## Preguntas", 1)[0].splitlines() if re.match(r"\| \d+ \|", line)]
    if len(plan_rows) != len(blocks):
        problems.append("el plan de preguntas no tiene una fila por pregunta")

    multi = 0
    single_letters = []
    for block in blocks:
        label = f"pregunta {block['n']}"
        options = OPTION.findall(block["body"].split("<details>", 1)[0])
        if options != ["A", "B", "C", "D"]:
            problems.append(f"{label}: debe tener las opciones A a D")
        answer = ANSWER.search(block["body"])
        if not answer:
            problems.append(f"{label}: falta la respuesta plegada que empieza por «**X.**»")
            continue
        letters = re.split(r", | y ", answer.group(1))
        if not re.search(rf"TS (?:{'|'.join(re.escape(ts) for ts in block['ts'])})-[KS]\d", answer.group(2)):
            problems.append(f"{label}: la respuesta no cita ninguna viñeta de su TS")
        if block["kind"] == "una respuesta":
            single_letters.append(letters[0])
            if len(letters) != 1:
                problems.append(f"{label}: es de respuesta única y la respuesta nombra {len(letters)}")
        else:
            multi += 1
            wanted = re.search(r"\*\*Selecciona (dos|tres|cuatro)\*\*", block["body"], re.IGNORECASE)
            if not wanted:
                problems.append(f"{label}: una multiple-response dice «**Selecciona dos**» (o tres, cuatro)")
            elif len(set(letters)) != WORDS[wanted.group(1).lower()]:
                problems.append(f"{label}: dice «Selecciona {wanted.group(1)}» pero la respuesta nombra {len(set(letters))}")
    if multi < MIN_MULTI:
        problems.append(f"un caso lleva al menos {MIN_MULTI} preguntas multiple-response y hay {multi}")
    if single_letters and max(single_letters.count(letter) for letter in set(single_letters)) > math.ceil(len(single_letters) / 2):
        problems.append("una misma letra es la correcta en más de la mitad de las preguntas de respuesta única")
    return problems


def make_case(n: int = 8, multi: int = 2) -> str:
    """Un caso sintético válido, para probar el validador y sus desvíos."""
    letters = "ABCD"
    rows, bodies = [], []
    for k in range(1, n + 1):
        is_multi = k > n - multi
        kind = "multiple-response" if is_multi else "una respuesta"
        right = "A y C" if is_multi else letters[k % 4]
        select = " **Selecciona dos**." if is_multi else ""
        rows.append(f"| {k} | TS 1.2 | {kind} |")
        bodies.append(
            f"### Pregunta {k} (TS 1.2 · {kind})\n\nEnunciado {k}.{select}\n\n- A. uno\n- B. dos\n- C. tres\n- D. cuatro\n\n"
            f"<details>\n<summary>Respuesta</summary>\n\n**{right}.** Porque sí (TS 1.2-K1).\n</details>\n"
        )
    return (
        "# E3 · Caso de prueba\n\n> **Escenario:** E3\n> **Dominios principales:** D1 · D2 · D5\n"
        f"> **Preguntas:** {n}\n\n## Contexto\n\nUn contexto.\n\n## Restricciones compartidas\n\n- R1: una.\n- R2: otra.\n\n"
        "## Plan de preguntas\n\n| Nº | TS | Formato |\n| :--- | :--- | :--- |\n" + "\n".join(rows) + "\n\n## Preguntas\n\n" + "\n".join(bodies)
    )


# --- El validador, con casos sintéticos ----------------------------------------------------------

def test_a_well_formed_case_has_no_problems():
    assert case_problems(make_case()) == []
    assert case_problems(make_case(n=10, multi=3)) == []
    assert case_problems(make_case(n=15, multi=4)) == []  # un caso de examen completo


def test_each_deviation_is_reported():
    good = make_case()
    assert any("entre 8 y 15" in p for p in case_problems(make_case(n=7)))
    assert any("entre 8 y 15" in p for p in case_problems(make_case(n=16)))
    assert any("multiple-response" in p for p in case_problems(make_case(multi=1)))
    assert any("falta la sección" in p for p in case_problems(good.replace("## Contexto", "## Otra cosa")))
    assert any("restricciones" in p for p in case_problems(good.replace("- R2: otra.\n", "")))
    assert any("Escenario" in p for p in case_problems(good.replace("> **Escenario:** E3\n", "")))
    assert any("dominios principales" in p for p in case_problems(good.replace("D1 · D2 · D5", "D3 · D4")))
    assert any("Selecciona" in p for p in case_problems(good.replace(" **Selecciona dos**.", "")))
    assert any("opciones A a D" in p for p in case_problems(good.replace("- D. cuatro\n", "", 1)))
    assert any("no cita" in p for p in case_problems(good.replace("(TS 1.2-K1)", "(TS 5.9-K1)", 1)))
    assert any("no coincide" in p for p in case_problems(good.replace("> **Preguntas:** 8", "> **Preguntas:** 9")))


def test_a_wrong_number_of_correct_letters_is_reported():
    wrong = make_case().replace("**A y C.**", "**A, B y C.**", 1)
    assert any("nombra 3" in p for p in case_problems(wrong))


def test_the_same_correct_letter_everywhere_is_reported():
    text = make_case(n=8, multi=2)
    for letter in "BCD":
        text = text.replace(f"**{letter}.**", "**A.**")
    assert any("misma letra" in p for p in case_problems(text))


# --- La especificación y la plantilla ----------------------------------------------------------

def largest_remainder(total: int, weights: dict[str, float]) -> dict[str, int]:
    base = {key: math.floor(total * w) for key, w in weights.items()}
    for key in sorted(weights, key=lambda k: total * weights[k] - base[k], reverse=True)[: total - sum(base.values())]:
        base[key] += 1
    return base


def blueprint_weights() -> dict[str, float]:
    text = (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")
    return {m.group(1): int(m.group(2)) / 100 for m in re.finditer(r"\| (D\d) \| [^|]+ \| (\d+)% \|", text)}


def doc_rows(first_cell: str) -> list[list[str]]:
    """Filas de tabla del documento cuya primera celda coincide con la expresión (p. ej. `E[1-6]` o `D[1-5]`)."""
    rows = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if re.fullmatch(first_cell, cells[0]):
                rows.append(cells)
    return rows


def test_the_spec_lists_the_six_scenarios_with_their_primary_domains():
    assert DOC.is_file(), "falta docs/simulaciones-por-escenario.md"
    rows = {cells[0]: cells for cells in doc_rows(r"E[1-6]")}
    assert sorted(rows) == sorted(SCENARIOS)
    for key, (name, domains) in SCENARIOS.items():
        assert name in rows[key][1], key
        assert set(re.findall(r"D\d", rows[key][2])) == domains, key


def test_the_full_simulation_follows_the_blueprint_weights():
    expected = largest_remainder(EXAM_ITEMS, blueprint_weights())
    assert sum(expected.values()) == EXAM_ITEMS
    rows = {cells[0]: int(cells[2]) for cells in doc_rows(r"D[1-5]")}
    assert rows == expected, f"el reparto de la simulación completa debe ser {expected}"


def test_the_spec_says_which_scenarios_can_be_written_now():
    text = DOC.read_text(encoding="utf-8")
    for key in SCENARIOS:
        assert re.search(rf"\| {key} \|[^\n]*\|\s*(Listo|Casi|Espera)", text), f"{key}: falta su estado de preparación"


def test_the_template_has_the_required_structure():
    assert TEMPLATE.is_file(), "falta plantillas/simulacion/ESCENARIO.md"
    text = TEMPLATE.read_text(encoding="utf-8")
    for needle in SECTIONS + ["> **Escenario:**", "> **Dominios principales:**", "> **Preguntas:**", "### Pregunta 1 (TS", "multiple-response", "**Selecciona dos**"]:
        assert needle in text, f"la plantilla no tiene «{needle}»"


# --- Los casos reales (hoy ninguno) -------------------------------------------------------------

def test_every_written_case_follows_the_format():
    failing = {case.name: case_problems(case.read_text(encoding="utf-8")) for case in CASES}
    assert all(not problems for problems in failing.values()), {name: p for name, p in failing.items() if p}
