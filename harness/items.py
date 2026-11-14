"""Ítems de evaluación: cada pregunta tipo examen y cada comprobación corta, con enunciado y respuesta separados.

PROPÓSITO: ofrecer la unidad que comparten el repaso de fallos, la práctica mezclada y D3 en el
narrador (plan de mejoras, fase 3). Un ítem es una pregunta de un módulo (`app1/01:P1`), una
comprobación corta (`app1/02:C1`) o una pregunta de la sección 4 de D3 (`d3:C1`…`d3:C5` para las
comprobaciones por TS y `d3:P1`…`d3:P3` para las integradas).

POR QUÉ EXISTE: el narrador entrega fases enteras de un módulo. Para repasar una viñeta fallada o
mezclar preguntas de módulos distintos hace falta sacar una sola pregunta, sin su respuesta y sin las
demás. Los README siguen siendo la única fuente: el ítem se lee de ellos y no se guarda copia (solo
una caché en memoria que se invalida cuando cambia algún README).

QUÉ NO HACE: no llama al modelo, no escribe nada y no juzga el contenido de las preguntas ni el
formato de los README (eso es de `tests/test_readme_modulos.py`, `tests/test_comprobaciones_cortas.py`
y `tests/test_d3_comprobaciones.py`). Cuál es la respuesta correcta lo dice el README, no este módulo.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from harness.credentials import ROOT
from harness.narrador import DETAILS, STEP4, CHECKS_HEADING, readme_text, route, subsections

D3_README = Path("d3_claude_code") / "README.md"
QUESTION_HEADING = "Pregunta tipo examen"
# «**C1 · TS 2.5-K3, K4, S3.** Enunciado…»: número, viñetas que practica y enunciado.
CHECK_TITLE = re.compile(r"^\*\*C(\d+) · (TS [^*]+?)\.\*\* ", re.MULTILINE)
ITEM_ID = re.compile(r"(app\d+/\d{1,2}|d3):([pc])(\d+)")
SOURCE = re.compile(r"(app\d+)[/ ](\d{1,2})|\bd3\b")
VIGNETTE_RUN = re.compile(r"TS (\d\.\d)-([KS]\d)((?:(?:, | y )(?:\d\.\d-)?[KS]\d)*)")
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


def _d3_items(root: Path) -> list[Item]:
    text = (root / D3_README).read_text(encoding="utf-8")
    sections = re.split(r"^### ", text, flags=re.MULTILINE)
    items: list[Item] = []
    for section in sections:
        if section.startswith("4.1"):
            kind, prefix = "comprobacion", "C"
        elif section.startswith("4.2"):
            kind, prefix = "pregunta", "P"
        else:
            continue
        number = 0
        for block in re.split(r"^#### ", section, flags=re.MULTILINE)[1:]:
            found = _answers(block, "Respuesta")
            if not found:
                continue
            number += 1
            title, _, rest = block.partition("\n")
            answer = found[0][2]
            statement = f"{title.strip()}\n\n" + DETAILS.sub("", rest.split("<details>", 1)[0]).strip() + "\n"
            items.append(
                Item(
                    f"d3:{prefix}{number}",
                    "d3",
                    kind,
                    frozenset(cited(answer) | cited(title)),
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


def source_of(text: str | None) -> str | None:
    """`app1/01` o `d3` a partir de una celda de «Módulo» escrita a mano; None si no se lee."""
    match = SOURCE.search((text or "").lower())
    if not match:
        return None
    return "d3" if match.group(1) is None else f"{match.group(1)}/{int(match.group(2)):02d}"


def destination(vignette: str, root: Path = ROOT) -> str | None:
    """El origen que `CONCEPTOS.md` asigna a una viñeta introducida (`appN/NN` o `d3`)."""
    rows = dict(CONCEPT_ROW.findall((root / "CONCEPTOS.md").read_text(encoding="utf-8")))
    found = rows.get(vignette)
    return found.split("_", 1)[0] if found else None


def item_for(vignette: str, source: str | None = None, root: Path = ROOT) -> Item:
    """El ítem con el que se repasa una viñeta.

    Por este orden: la comprobación corta del origen cuyo título la nombra; un ítem del origen cuya
    respuesta la cita; la primera pregunta del origen (en D3, la comprobación de su TS). Sin origen,
    o con uno ilegible o desconocido, se usa el destino de `CONCEPTOS.md`.
    """
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
    if origin == "d3":
        # «TS 3.4-K1» → la comprobación C4: cada TS de D3 tiene la suya. Sin comprobación (TS 3.6,
        # que vive en otro módulo), se repasa con el ítem del destino de CONCEPTOS.md.
        try:
            return find_item(f"d3:C{vignette[5]}", root)
        except UnknownItem:
            if fallback in sources and fallback != "d3":
                return item_for(vignette, fallback, root)
            raise
    return find_item(f"{origin}:P1", root)
