"""Ítems de evaluación: cada pregunta tipo examen y cada comprobación corta, con enunciado y respuesta separados.

PROPÓSITO: ofrecer la unidad que comparten el repaso de fallos, la práctica mezclada y D3 en el
narrador (plan de mejoras, fase 3). Un ítem es una pregunta de un módulo (`app1/01:P1`), una
comprobación corta (`app1/02:C1`) o una pregunta de la sección 4 de D3 (`d3:C1`…`d3:C5` para las
comprobaciones por TS y `d3:P1`…`d3:P3` para las integradas).

POR QUÉ EXISTE: el narrador entrega fases enteras de un módulo. Para repasar una viñeta fallada o
mezclar preguntas de módulos distintos hace falta sacar una sola pregunta, sin su respuesta y sin las
demás. Los README siguen siendo la única fuente: el ítem se lee de ellos y no se guarda copia (solo
una caché en memoria que se invalida cuando cambia algún README).

QUÉ NO HACE: no llama al modelo, no escribe nada, no quita el rótulo de viñeta salvo en
`blind_statement` (para la práctica mezclada) y no juzga el contenido de las preguntas ni el
formato de los README (eso es de `tests/test_readme_modulos.py`, `tests/test_comprobaciones_cortas.py`
y `tests/test_d3_comprobaciones.py`). Cuál es la respuesta correcta lo dice el README, no este módulo.
"""

import random
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from harness.credentials import ROOT
from harness.narrador import DETAILS, STEP4, CHECKS_HEADING, route, subsections

D3_README = Path("d3_claude_code") / "README.md"
QUESTION_HEADING = "Pregunta tipo examen"
# «**C1 · TS 2.5-K3, K4, S3.** Enunciado…»: número, viñetas que practica y enunciado.
CHECK_TITLE = re.compile(r"^\*\*C(\d+) · (TS [^*]+?)\.\*\* ", re.MULTILINE)
ITEM_ID = re.compile(r"(app\d+/\d{1,2}|d3):([pc])(\d+)")
SOURCE = re.compile(r"(app\d+)[/ ](\d{1,2})|\bd3\b")
VIGNETTE_RUN = re.compile(r"TS (\d\.\d)-([KS]\d)((?:(?:, | y )(?:\d\.\d-)?[KS]\d)*)")
TASK_ONLY = re.compile(r"TS \d\.\d")
CONCEPT_ROW = re.compile(r"^\| (TS \d\.\d-[KS]\d) \| (\S+) \| ☑ \|", re.MULTILINE)


class UnknownItem(ValueError):
    """El id o la viñeta no corresponde a ningún ítem."""


@dataclass(frozen=True)
class Item:
    id: str  # «app1/02:C1», «d3:P2»
    source: str  # «app1/02» o «d3»
    kind: str  # «pregunta» o «comprobacion»
    vignettes: frozenset[str]
    statement: str  # enunciado con sus opciones, sin respuesta
    answer: str  # cuerpo de la respuesta plegada, que empieza por la letra

    @property
    def domains(self) -> frozenset[str]:
        return frozenset(f"D{vignette[3]}" for vignette in self.vignettes)


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


def title_vignettes(item: Item) -> set[str]:
    """Las viñetas que el título de una comprobación corta nombra (vacío en una pregunta)."""
    match = CHECK_TITLE.match(item.statement)
    return cited(match.group(2)) if match else set()


# --- Lectura de los README -----------------------------------------------------------

def _answers(text: str, summary_prefix: str) -> list[tuple[int, int, str]]:
    """[(inicio, fin, cuerpo)] de cada `<details>` cuyo `summary` empieza por el prefijo."""
    return [
        (match.start(), match.end(), match.group(2).strip())
        for match in DETAILS.finditer(text)
        if match.group(1).strip().startswith(summary_prefix)
    ]


def _module_items(module) -> list[Item]:
    section = module.section()
    parts = subsections(section)
    items: list[Item] = []

    # Preguntas: el enunciado va desde la respuesta anterior (o el inicio) hasta su propio «Paso 4».
    for heading, body in parts:
        if heading.startswith(QUESTION_HEADING):
            previous = 0
            for number, (start, end, answer) in enumerate(_answers(body, STEP4), start=1):
                statement = DETAILS.sub("", body[previous:start]).strip() + "\n"
                items.append(
                    Item(f"{module.id}:P{number}", module.id, "pregunta", frozenset(cited(answer)), statement, answer)
                )
                previous = end
            break

    # Comprobaciones cortas: una por título «**Cn · TS …**».
    for heading, body in parts:
        if heading.startswith(CHECKS_HEADING):
            titles = list(CHECK_TITLE.finditer(body))
            for position, title in enumerate(titles):
                stop = titles[position + 1].start() if position + 1 < len(titles) else len(body)
                chunk = body[title.start():stop]
                number = int(title.group(1))
                found = _answers(chunk, f"Comprobación C{number} ")
                if not found:
                    continue
                statement = chunk.split("<details>", 1)[0].strip() + "\n"
                answer = found[0][2]
                items.append(
                    Item(
                        f"{module.id}:C{number}",
                        module.id,
                        "comprobacion",
                        frozenset(cited(answer) | cited(title.group(2))),
                        statement,
                        answer,
                    )
                )
            break
    return items


class D3Block(NamedTuple):
    """Un `####` de la sección 4 de D3: el número de su `###` («4.1»…, «» si no hay), su título y su cuerpo."""

    subsection: str
    title: str
    body: str


def d3_section4(root: Path = ROOT) -> list[D3Block]:
    """Los `####` de la sección 4 del README de D3, en orden. Es el único sitio que parte el README por su sección 4."""
    text = (root / D3_README).read_text(encoding="utf-8").split("\n## 4 · ", 1)[1]
    blocks: list[D3Block] = []
    subsection = ""
    collecting = False
    for line in text.splitlines():
        if line.startswith("#### "):
            blocks.append(D3Block(subsection, line[5:].strip(), ""))
            collecting = True
        elif line.startswith("### "):
            # «### 4.1 · …» → «4.1»; un `###` sin número deja la subsección vacía.
            match = re.match(r"### (\d+\.\d+)", line)
            subsection = match.group(1) if match else ""
            collecting = False
        elif line.startswith("## "):
            collecting = False
        elif collecting:
            last = blocks[-1]
            blocks[-1] = last._replace(body=last.body + line + "\n")
    return blocks


def _d3_items(root: Path) -> list[Item]:
    kinds = {"4.1": ("comprobacion", "C"), "4.2": ("pregunta", "P")}
    counts = {"4.1": 0, "4.2": 0}
    items: list[Item] = []
    for block in d3_section4(root):
        if block.subsection not in kinds:
            continue
        found = _answers(block.body, "Respuesta")
        if not found:
            continue
        kind, prefix = kinds[block.subsection]
        counts[block.subsection] += 1
        answer = found[0][2]
        statement = f"{block.title}\n\n" + DETAILS.sub("", block.body.split("<details>", 1)[0]).strip() + "\n"
        items.append(
            Item(
                f"d3:{prefix}{counts[block.subsection]}",
                "d3",
                kind,
                frozenset(cited(answer) | cited(block.title)),
                statement,
                answer,
            )
        )
    return items


@lru_cache(maxsize=4)
def _load(root: Path, stamp: tuple) -> tuple[Item, ...]:
    items: list[Item] = []
    for module in route(root):
        if module.delivered:
            items += _module_items(module)
    items += _d3_items(root)
    return tuple(items)


def all_items(root: Path = ROOT) -> list[Item]:
    """Todos los ítems en el orden de la ruta de lectura, con D3 al final."""
    files = sorted(root.glob("app*/README.md")) + [root / D3_README]
    stamp = tuple((str(path), path.stat().st_mtime_ns) for path in files if path.exists())
    return list(_load(root, stamp))


# --- Buscar ----------------------------------------------------------------------------

def find_item(text: str, root: Path = ROOT) -> Item:
    """El ítem de un id como `app1/02:C1` o `d3:P2`, sin distinguir mayúsculas ni espacios sobrantes."""
    match = ITEM_ID.fullmatch(text.strip().lower())
    if not match:
        raise UnknownItem(f"«{text}» no tiene la forma appN/NN:P1 o appN/NN:C1 (por ejemplo, app1/02:C1 o d3:P1)")
    source = match.group(1)
    if source.startswith("app"):
        app, number = source.split("/")
        source = f"{app}/{int(number):02d}"
    wanted = f"{source}:{match.group(2).upper()}{int(match.group(3))}"
    for item in all_items(root):
        if item.id == wanted:
            return item
    raise UnknownItem(f"no existe el ítem {wanted}")


LABEL = re.compile(r"^\*\*([CP]\d+) · [^*]+?\.\*\* ")
D3_CHECK_TITLE = re.compile(r"\A(?:TS \d\.\d · [^\n]*)\n+")
D3_QUESTION_TITLE = re.compile(r"\A(Pregunta \d+) \(TS [^)\n]*\)")


def blind_statement(item: Item) -> str:
    """El enunciado sin el rótulo de viñeta, para la práctica mezclada.

    `**C1 · TS 2.5-K3, K4, S3.** …` → `**C1.** …`; en D3, sin la línea de título `TS 3.x · …` de una
    comprobación y con `Pregunta N` a secas en una integrada. La prosa de la pregunta no se toca.
    """
    text = item.statement
    if item.source == "d3":
        return D3_QUESTION_TITLE.sub(r"\1", D3_CHECK_TITLE.sub("", text, count=1), count=1)
    return LABEL.sub(r"**\1.** ", text, count=1)


# --- Práctica mezclada -------------------------------------------------------------------

def mixed_selection(n: int = 10, domain: str | None = None, seed: int | None = None, root: Path = ROOT) -> list[Item]:
    """N ítems con viñetas, sorteados con semilla y sin dos seguidos del mismo origen mientras se pueda.

    El sorteo es uniforme entre los ítems disponibles (de un dominio, si se pide). Si hay menos de N,
    se entregan todos. Un ítem sin viñetas (`app2/03:P1`) no practica la guía y nunca entra.
    """
    if n < 1:
        raise ValueError(f"-n tiene que ser al menos 1 (recibido {n})")
    wanted = None
    if domain is not None:
        wanted = domain.strip().upper()
        if not re.fullmatch(r"D[1-5]", wanted):
            raise ValueError(f"«{domain}» no es un dominio: usa D1 a D5")
    pool = [item for item in all_items(root) if item.vignettes and (wanted is None or wanted in item.domains)]
    rng = random.Random(seed)
    chosen = rng.sample(pool, min(n, len(pool)))

    # Orden: en cada paso, del origen con más ítems por colocar que no sea el anterior (así nunca se
    # queda un origen grande para el final); si solo queda el anterior, se repite antes que recortar.
    ordered: list[Item] = []
    while chosen:
        remaining = Counter(item.source for item in chosen)
        previous = ordered[-1].source if ordered else None
        options = [item for item in chosen if item.source != previous] or chosen
        top = max(remaining[item.source] for item in options)
        pick = next(item for item in options if remaining[item.source] == top)
        chosen.remove(pick)
        ordered.append(pick)
    return ordered


def source_of(text: str | None) -> str | None:
    """`app1/01` o `d3` a partir de una celda de «Módulo» escrita a mano; None si no se lee."""
    match = SOURCE.search((text or "").lower())
    if not match:
        return None
    return "d3" if match.group(1) is None else f"{match.group(1)}/{int(match.group(2)):02d}"


def introduced(root: Path = ROOT) -> list[str]:
    """Las viñetas introducidas (☑) de `CONCEPTOS.md`, en su orden."""
    return [found for found, _ in CONCEPT_ROW.findall((root / "CONCEPTOS.md").read_text(encoding="utf-8"))]


def destination(vignette: str, root: Path = ROOT) -> str | None:
    """El origen que `CONCEPTOS.md` asigna a una viñeta introducida (`appN/NN` o `d3`)."""
    rows = dict(CONCEPT_ROW.findall((root / "CONCEPTOS.md").read_text(encoding="utf-8")))
    found = rows.get(vignette)
    return found.split("_", 1)[0] if found else None


def item_for(vignette: str, source: str | None = None, root: Path = ROOT) -> Item:
    """El ítem con el que se repasa una viñeta.

    Por este orden: la comprobación corta del origen cuyo título la nombra; un ítem del origen cuya
    respuesta la cita. Si el origen anotado no nombra ni cita la viñeta, o es ilegible o desconocido,
    se repasa con el destino de `CONCEPTOS.md` (mismo orden). Solo si el destino tampoco la nombra ni
    la cita se usa su primera pregunta (en D3, la comprobación de su TS: vale únicamente para viñetas
    `TS 3.x` con destino D3). Una TS a secas (`TS 5.5`) se resuelve como su primera viñeta introducida.
    """
    if TASK_ONLY.fullmatch(vignette.strip()):
        # Solo la task statement: se resuelve como su primera viñeta introducida en CONCEPTOS.md.
        first = next((found for found in introduced(root) if found.startswith(vignette.strip() + "-")), None)
        if first is None:
            raise UnknownItem(f"la task statement «{vignette}» no tiene viñetas introducidas en CONCEPTOS.md")
        vignette = first
    items = all_items(root)
    sources = {item.source for item in items}
    fallback = destination(vignette, root)
    if fallback is None:
        raise UnknownItem(f"la viñeta «{vignette}» no está introducida en CONCEPTOS.md")
    origin = source_of(source)
    if origin not in sources:
        origin = fallback
    if origin not in sources:
        raise UnknownItem(f"la viñeta «{vignette}» no tiene ítem de repaso")
    candidates = [item for item in items if item.source == origin]
    for item in candidates:
        if item.kind == "comprobacion" and vignette in title_vignettes(item):
            return item
    for item in candidates:
        if vignette in item.vignettes:
            return item
    if origin != fallback:
        # El origen anotado no nombra ni cita la viñeta: preguntar otra cosa de ese módulo no la repasa.
        # Se usa el destino de CONCEPTOS.md, con el mismo orden (comprobación que la nombra, ítem que la cita).
        return item_for(vignette, fallback, root)
    if origin == "d3":
        # «TS 3.4-K1» → la comprobación C4: cada TS de D3 tiene la suya. Solo vale para viñetas TS 3.x
        # cuyo destino es D3 (el origen y el destino coinciden aquí).
        return find_item(f"d3:C{vignette[5]}", root)
    return find_item(f"{origin}:P1", root)
