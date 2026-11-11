"""Tests de estructura de los README de módulo (roadmap §13, regla 5). Sin modelo.

PROPÓSITO: comprobar que cada sección `## NN · …` de `app*/README.md` contiene
los bloques «Antes de empezar» y «Pregunta tipo examen», y que sigue la forma de
la plantilla en lo que es determinista: «Predice antes de ejecutar» antes de
«Ejecutar» (el ciclo de §13), el resultado medido plegado en «Resultado de
referencia» y la indicación de ejecución obligatoria o ligera, la ficha del
principio y los pasos 3–5 con nombre (prueba de usabilidad del Hito T). También
la forma de las predicciones: cada una marcada `(guía)` o `(módulo)`, con dos
interrogantes como máximo y con su contraste `**Pn**` en el Paso 3.

POR QUÉ EXISTE: la incorporación de quien llega de cero se quedó sin dueño y solo
`app1/01` la cumplía. Un test barato impide que un módulo nuevo nazca sin ella.

QUÉ NO HACE: no juzga la calidad ni decide qué módulos son obligatorios. Que el contexto no adelante el resultado o que
la predicción pida patrones y no valores lo comprueba la revisión independiente.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("Antes de empezar", "Pregunta tipo examen")

# Módulos entregados antes de la regla 5 que aún no tienen «Antes de empezar».
# Se vacía según avanza la retroadaptación; al quedar vacía, el hito T está cerrado.
# `test_pending_really_fail` obliga a borrar una entrada en cuanto el módulo cumple.
PENDING_ONBOARDING: set[str] = set()


def split_sections(text: str) -> dict[str, str]:
    """Devuelve {número de módulo: texto de su sección `## NN · …`} (hasta el siguiente `## `)."""
    sections: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"## (\d{2}) ·", line)
        if match:
            current = match.group(1)
            sections[current] = ""
        elif line.startswith("## "):
            current = None  # otra sección de nivel 2: ya no es del módulo
        elif current is not None:
            sections[current] += line + "\n"
    return sections


def missing_blocks(section: str) -> list[str]:
    return [block for block in REQUIRED if block not in section]


PREDICT = "### Predice antes de ejecutar"
RUN = "### Ejecutar"
BEFORE = "### Antes de empezar"
FICHA = ("> **Qué vas a hacer:**", "> **Necesitas antes:**", "> **Modo:**")
FOLDED = "<summary>Paso 3 · Contrastar"
ANSWER = "<summary>Paso 4 · Respuesta"
STEP5 = "**Paso 5 ·**"
RUN_MODE = re.compile(r"> \*\*Modo:\*\* [Ee]jecución (obligatoria|ligera)")


def shape_problems(section: str) -> list[str]:
    """Desvíos deterministas de la plantilla: ficha, orden del ciclo, bloques plegados y paso 5."""
    problems = []
    start = section.find(BEFORE)
    head = section if start < 0 else section[:start]
    if not all(line in head for line in FICHA):
        problems.append("falta la ficha (Qué vas a hacer · Necesitas antes · Modo) antes de «Antes de empezar»")
    elif not RUN_MODE.search(head):
        problems.append("la ficha no dice si la ejecución es obligatoria o ligera")
    if PREDICT not in section or RUN not in section:
        problems.append("faltan «Predice antes de ejecutar» o «Ejecutar» como `###`")
    elif section.index(PREDICT) > section.index(RUN):
        problems.append("«Predice antes de ejecutar» va después de «Ejecutar»")
    if FOLDED not in section:
        problems.append("sin «Paso 3 · Contrastar» plegado")
    if ANSWER not in section or STEP5 not in section:
        problems.append("falta «Paso 4 · Respuesta» o la línea «Paso 5»")
    return problems


MULTI = re.compile(r"\*\*Selecciona (dos|tres|cuatro)\*\*", re.IGNORECASE)
COUNTS = {"dos": 2, "tres": 3, "cuatro": 4}
# `AskUserQuestion`, con el que `practica-guiada` plantea la pregunta, admite 4 opciones como máximo.
MAX_OPTIONS = 4
# Un módulo que introduce al menos tantas viñetas debe llevar una pregunta multiple-response (auditoría G-06, D-01).
DENSE_MIN = 10
ANSWER_BLOCK = re.compile(r"<details>\s*<summary>Paso 4 · Respuesta[^<]*</summary>(.*?)</details>", re.DOTALL)
ANSWER_HEAD = re.compile(r"\s*\*\*([A-F](?:(?:, | y )[A-F])*)\.\*\*")


def multi_response_problems(section: str) -> list[str]:
    """Desvíos del formato multiple-response: cuántas elegir, opciones, respuesta con sus letras y una justificación por opción.

    Convención: el enunciado dice «**Selecciona dos**» (o tres, cuatro); la respuesta plegada empieza por
    «**A y C.**» y justifica cada opción con una viña `- **A** …`.
    """
    problems = []
    for match in MULTI.finditer(section):
        wanted = COUNTS[match.group(1).lower()]
        after = section[match.end():]
        letters = re.findall(r"^- ([A-F])\. ", after.split("<details>", 1)[0], re.MULTILINE)
        if len(letters) < wanted + 1:
            problems.append(f"«Selecciona {wanted}» necesita al menos {wanted + 1} opciones y hay {len(letters)}")
        if len(letters) > MAX_OPTIONS:
            problems.append(f"«Selecciona {wanted}» admite como máximo {MAX_OPTIONS} opciones y hay {len(letters)}")
        block = ANSWER_BLOCK.search(after)
        head = ANSWER_HEAD.match(block.group(1)) if block else None
        if not head:
            problems.append(f"«Selecciona {wanted}» sin respuesta plegada que empiece por «**X y Y.**»")
            continue
        correct = set(re.split(r", | y ", head.group(1)))
        if len(correct) != wanted:
            problems.append(f"dice «Selecciona {wanted}» pero la respuesta nombra {len(correct)}")
        if not correct <= set(letters):
            problems.append("la respuesta nombra una letra que no es una opción")
        problems += [f"la respuesta no justifica la opción {letter}" for letter in letters if f"**{letter}**" not in block.group(1)]
    return problems


PREDICT_BLOCK = re.compile(r"### Predice antes de ejecutar\n(.*?)\n### ", re.DOTALL)
CONTRAST_BLOCK = re.compile(r"<summary>Paso 3 · Contrastar[^<]*</summary>(.*?)</details>", re.DOTALL)
LANES = ("(guía)", "(módulo)")
# Una predicción pregunta una cosa; dos interrogantes admiten «qué pasa y por qué».
MAX_QUESTIONS = 2


def predictions(section: str) -> list[tuple[int, str]]:
    """Las predicciones numeradas de «Predice antes de ejecutar», como (número, texto)."""
    block = PREDICT_BLOCK.search(section)
    if not block:
        return []
    return [(int(number), text) for number, text in re.findall(r"^(\d+)\. (.*)$", block.group(1), re.MULTILINE)]


def prediction_problems(section: str) -> list[str]:
    """Desvíos del criterio de predicciones autónomas (`plantillas/modulo/README.md`).

    Cada predicción dice si evalúa la guía o un detalle del módulo, pregunta una sola cosa
    y tiene su contraste `**Pn**` dentro del Paso 3, para que ninguna quede sin respuesta.
    """
    problems = []
    contrast = CONTRAST_BLOCK.search(section)
    answers = contrast.group(1) if contrast else ""
    for number, text in predictions(section):
        if not text.startswith(LANES):
            problems.append(f"la predicción {number} no empieza por (guía) o (módulo)")
        if text.count("¿") > MAX_QUESTIONS:
            problems.append(f"la predicción {number} junta {text.count('¿')} preguntas (máximo {MAX_QUESTIONS})")
        if not re.search(rf"\*\*P{number}\b", answers):
            problems.append(f"el Paso 3 no contrasta la predicción {number} (falta «**P{number}**»)")
    return problems


# Módulos anteriores al criterio de predicciones autónomas. Se vacía según se adaptan;
# `test_pending_predictions_really_fail` obliga a borrar la entrada en cuanto el módulo cumple.
PENDING_PREDICTIONS: set[str] = {
    *(f"app3_sistema_multiagente {n:02d}" for n in range(1, 13)),
}


def all_sections() -> dict[str, str]:
    found = {}
    for readme in sorted(ROOT.glob("app*/README.md")):
        for number, body in split_sections(readme.read_text(encoding="utf-8")).items():
            found[f"{readme.parent.name} {number}"] = body
    return found


# --- Lógica del analizador, con texto sintético -------------------------------

def test_split_sections_stops_at_next_level_two():
    text = "## 01 · A\nuno\n### Sub\ndos\n## Otra cosa\nfuera\n## 02 · B\ntres\n"
    sections = split_sections(text)
    assert set(sections) == {"01", "02"}
    assert "dos" in sections["01"] and "fuera" not in sections["01"]


def test_missing_blocks_reports_each_absent_block():
    assert missing_blocks("### Antes de empezar\n### Pregunta tipo examen") == []
    assert missing_blocks("### Pregunta tipo examen") == ["Antes de empezar"]
    assert missing_blocks("nada") == list(REQUIRED)


def test_shape_problems_detects_each_deviation():
    ficha = "> **Qué vas a hacer:** x.\n> **Necesitas antes:** nada.\n> **Modo:** ejecución ligera (y).\n"
    body = f"{PREDICT}\n1. ?\n{RUN}\n{FOLDED}: z</summary>\n{ANSWER}</summary>\n{STEP5} anota\n"
    good = f"{ficha}{BEFORE}\n{body}"
    assert shape_problems(good) == []
    late = f"{BEFORE}\n{ficha}{body}"
    assert shape_problems(late) == ["falta la ficha (Qué vas a hacer · Necesitas antes · Modo) antes de «Antes de empezar»"]
    no_mode = good.replace("ejecución ligera", "a tu gusto")
    assert shape_problems(no_mode) == ["la ficha no dice si la ejecución es obligatoria o ligera"]
    swapped = good.replace(f"{PREDICT}\n1. ?\n{RUN}", f"{RUN}\n{PREDICT}\n1. ?")
    assert shape_problems(swapped) == ["«Predice antes de ejecutar» va después de «Ejecutar»"]
    no_steps = good.replace(FOLDED, "<summary>Resultado").replace(STEP5, "")
    assert len(shape_problems(no_steps)) == 2


GOOD_MULTI = """**Selecciona dos**

- A. uno
- B. dos
- C. tres
- D. cuatro

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**A y C.** porque sí.

- **A** correcta.
- **B** no.
- **C** correcta.
- **D** no.
</details>
"""


def test_multi_response_accepts_the_documented_format():
    assert multi_response_problems(GOOD_MULTI) == []
    assert multi_response_problems("Una sola respuesta.\n- A. x\n") == []  # sin «Selecciona N»: no aplica


def test_multi_response_detects_each_deviation():
    wrong_count = GOOD_MULTI.replace("**A y C.**", "**A, B y C.**")
    assert multi_response_problems(wrong_count) == ["dice «Selecciona 2» pero la respuesta nombra 3"]
    few = GOOD_MULTI.replace("- C. tres\n- D. cuatro\n", "").replace("- **C** correcta.\n- **D** no.\n", "")
    assert any("necesita al menos 3 opciones" in problem for problem in multi_response_problems(few))
    unknown = GOOD_MULTI.replace("**A y C.**", "**A y E.**")
    assert "la respuesta nombra una letra que no es una opción" in multi_response_problems(unknown)
    unexplained = GOOD_MULTI.replace("- **D** no.\n", "")
    assert multi_response_problems(unexplained) == ["la respuesta no justifica la opción D"]
    five = GOOD_MULTI.replace("- D. cuatro\n", "- D. cuatro\n- E. cinco\n").replace("- **D** no.\n", "- **D** no.\n- **E** no.\n")
    assert multi_response_problems(five) == [f"«Selecciona 2» admite como máximo {MAX_OPTIONS} opciones y hay 5"]
    no_answer = GOOD_MULTI.split("<details>")[0]
    assert multi_response_problems(no_answer) == ["«Selecciona 2» sin respuesta plegada que empiece por «**X y Y.**»"]


GOOD_PREDICTIONS = """### Predice antes de ejecutar

Con tus palabras:

1. (guía) ¿Qué pasa? ¿Por qué?
2. (módulo) ¿Qué línea lo muestra?

### Ejecutar

<details>
<summary>Paso 3 · Contrastar: lo que se observó</summary>

- **P1** pasa esto.
- **P2** esta línea.
</details>
"""


def test_predictions_are_read_from_their_block():
    assert predictions(GOOD_PREDICTIONS) == [(1, "(guía) ¿Qué pasa? ¿Por qué?"), (2, "(módulo) ¿Qué línea lo muestra?")]
    assert predictions("sin bloque") == []


def test_prediction_problems_detects_each_deviation():
    assert prediction_problems(GOOD_PREDICTIONS) == []
    unmarked = GOOD_PREDICTIONS.replace("1. (guía) ", "1. ")
    assert prediction_problems(unmarked) == ["la predicción 1 no empieza por (guía) o (módulo)"]
    crowded = GOOD_PREDICTIONS.replace("¿Por qué?", "¿Por qué? ¿Y si no?")
    assert prediction_problems(crowded) == ["la predicción 1 junta 3 preguntas (máximo 2)"]
    unanswered = GOOD_PREDICTIONS.replace("- **P2** esta línea.\n", "")
    assert prediction_problems(unanswered) == ["el Paso 3 no contrasta la predicción 2 (falta «**P2**»)"]
    # «**P1**» no vale como contraste de la predicción 10.
    ten = GOOD_PREDICTIONS.replace("2. (módulo)", "10. (módulo)").replace("**P2**", "**P1**")
    assert "el Paso 3 no contrasta la predicción 10 (falta «**P10**»)" in prediction_problems(ten)


# --- Comprobación sobre los README reales -------------------------------------

def test_readmes_have_module_sections():
    assert all_sections(), "no se encontró ninguna sección `## NN ·` en app*/README.md"


def test_every_module_has_required_blocks():
    failing = {
        name: missing_blocks(body)
        for name, body in all_sections().items()
        if missing_blocks(body) and name not in PENDING_ONBOARDING
    }
    assert not failing, f"módulos sin los bloques exigidos (roadmap §13, regla 5): {failing}"


def test_every_module_follows_template_shape():
    failing = {
        name: shape_problems(body)
        for name, body in all_sections().items()
        if shape_problems(body)
    }
    assert not failing, f"módulos que se desvían de plantillas/modulo/README.md: {failing}"


def test_multi_response_questions_follow_the_format():
    failing = {name: multi_response_problems(body) for name, body in all_sections().items() if multi_response_problems(body)}
    assert not failing, f"preguntas multiple-response mal formadas: {failing}"


def test_predictions_are_self_contained():
    failing = {
        name: prediction_problems(body)
        for name, body in all_sections().items()
        if prediction_problems(body) and name not in PENDING_PREDICTIONS
    }
    assert not failing, f"predicciones que no siguen plantillas/modulo/README.md: {failing}"


@pytest.mark.parametrize("name", sorted(PENDING_PREDICTIONS))
def test_pending_predictions_really_fail(name):
    """Una entrada pendiente que ya cumple debe borrarse de la lista."""
    sections = all_sections()
    assert name in sections, f"{name} ya no existe: bórralo de PENDING_PREDICTIONS"
    assert prediction_problems(sections[name]), f"{name} ya cumple: bórralo de PENDING_PREDICTIONS"


def assigned_counts() -> dict[str, int]:
    """{destino de `CONCEPTOS.md`: nº de viñetas que le asigna}, contando las ya introducidas y las pendientes."""
    counts: dict[str, int] = {}
    for line in (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| TS [\d.]+-[KS]\d \| ([^|]+?) \| [☑☐] \|", line)
        if match:
            counts[match.group(1).strip()] = counts.get(match.group(1).strip(), 0) + 1
    return counts


def dense_modules() -> list[str]:
    """Los módulos entregados que introducen `DENSE_MIN` viñetas o más, con la clave de `all_sections()`."""
    counts = assigned_counts()
    dense = []
    for key in all_sections():
        folder, number = key.split(" ")
        prefix = f"{folder.split('_')[0]}/{number}_"
        if sum(n for destination, n in counts.items() if destination.startswith(prefix)) >= DENSE_MIN:
            dense.append(key)
    return dense


def test_dense_modules_are_found():
    """Con el umbral actual, los tres módulos que la auditoría llama densos (D-01) y `app3/11`, que nace denso en la tanda C; si cambia, cambia esto."""
    assert dense_modules() == [
        "app2_agente_con_control 04", "app3_sistema_multiagente 01", "app3_sistema_multiagente 05", "app3_sistema_multiagente 07", "app3_sistema_multiagente 11",
    ]


def test_dense_modules_practice_multiple_response():
    """G-06: un módulo que introduce `DENSE_MIN` viñetas o más lleva, además de la de respuesta única, una multiple-response.

    Los módulos nuevos de las tandas C y D nacen sujetos a esta regla (`app2/04` y `app3/11` la cumplirán al entregarse).
    """
    sections = all_sections()
    missing = [name for name in dense_modules() if not MULTI.search(sections[name])]
    assert not missing, f"módulos densos (≥ {DENSE_MIN} viñetas) sin una pregunta «Selecciona N»: {missing}"


@pytest.mark.parametrize("name", sorted(PENDING_ONBOARDING))
def test_pending_really_fail(name):
    """Una entrada pendiente que ya cumple debe borrarse de la lista."""
    sections = all_sections()
    assert name in sections, f"{name} ya no existe: bórralo de PENDING_ONBOARDING"
    assert missing_blocks(sections[name]), f"{name} ya cumple: bórralo de PENDING_ONBOARDING"
