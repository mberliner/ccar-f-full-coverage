"""Hojas de repaso por dominio (`docs/repaso/D1.md` … `D5.md`), generadas de las cabeceras. Sin modelo.

PROPÓSITO: reunir, para cada dominio de la guía, lo que las cabeceras de los módulos (y los archivos
de D3 con marcador `INTRODUCE`) ya dicen: qué viñetas introduce cada origen, qué dice la guía de ellas
y cuál es la trampa del examen. La unidad es el origen (una sección `## ` por módulo o por archivo de
D3), no la viñeta: un bullet de «QUÉ DICE LA GUÍA» suele citar varias y las cabeceras no se pueden
cortar por viñeta.

POR QUÉ EXISTE: para repasar un dominio había que abrir cada script y leer su cabecera. La hoja lo
junta sin duplicar contenido: se genera, y `--check` falla si deja de coincidir con las cabeceras,
igual que `datos/generar_sinteticos.py --check` con los datos.

QUÉ NO HACE: no escribe texto propio (copia las cabeceras, puede unir las líneas de un párrafo), no
comprueba que digan lo que dice la guía y no toca el modelo. Con `--check` nunca repara una hoja.

Uso: `uv run python -m harness.hojas_repaso [--check]`
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "docs" / "repaso"

CONCEPT_ROW = re.compile(r"^\| (TS \d\.\d-[KS]\d) \| (\S+) \| ☑ \|", re.MULTILINE)
DOMAIN_ROW = re.compile(r"^\| (D\d) \| ([^|]+) \|", re.MULTILINE)
# Línea del marcador de un archivo de D3: «INTRODUCE: TS 3.x…», con «# » si va en frontmatter.
MARKER_LINE = re.compile(r"^\s*(?:#\s*)?INTRODUCE: TS 3\.")
VIGNETTE = re.compile(r"TS (\d)\.(\d)-([KS])(\d)")
# Un bullet cita un dominio con «1.1-K1» (con o sin «TS ») o con un «TS 3.6» a secas.
DOMAIN_CITE = re.compile(r"(?<![\d.])(\d)\.\d-[KS]\d|TS (\d)\.\d(?![\d-])")
# Etiquetas de una cabecera. Solo cuentan al principio de línea; lo demás es texto de la etiqueta anterior.
LABEL = re.compile(
    r"^(QUÉ DICE LA GUÍA|POR QUÉ IMPORTA|ANTI-PATRÓN(?: / TRAMPA DEL EXAMEN)?|EN PRODUCCIÓN \(no evaluable\)"
    r"|Pregunta tipo examen|INTRODUCE|USA|Uso)\b[^:\n]*:"
)
HEAD_NOTE = (
    "> Hoja de repaso generada con `uv run python -m harness.hojas_repaso`: no se edita a mano.",
    "> Se lee después de hacer los módulos del dominio: reúne lo que el narrador solo enseña con la respuesta.",
)
NO_GUIDE = "Sin bullet propio en la cabecera."
NO_TRAP = "Sin trampa propia en la cabecera."


@dataclass(frozen=True)
class Origin:
    """Un origen de viñetas de un dominio: un módulo de app o un archivo de D3."""

    heading: str
    vignettes: tuple[str, ...]  # solo las que introduce y son del dominio de la hoja
    guide: list[str]  # líneas de «Qué dice la guía» ya filtradas por dominio
    trap: list[str]


def vignette_key(vignette: str) -> tuple[int, int, str, int]:
    """Orden de la guía: TS, subíndice, K antes que S, número."""
    major, minor, kind, number = VIGNETTE.fullmatch(vignette).groups()
    return int(major), int(minor), kind, int(number)


# --- Lectura de cabeceras --------------------------------------------------------

def header_blocks(lines: list[str]) -> dict[str, list[str]]:
    """Divide una cabecera en bloques por etiqueta: `guide`, `trap` y `other` (el resto)."""
    blocks: dict[str, list[str]] = {"guide": [], "trap": [], "other": []}
    current: str | None = None
    for line in lines:
        match = LABEL.match(line)
        if match:
            name = match.group(1)
            current = "guide" if name == "QUÉ DICE LA GUÍA" else "trap" if name.startswith("ANTI") else "other"
            rest = line[match.end():].strip()
            if rest and current != "other":
                blocks[current].append(rest)
            continue
        if current and current != "other":
            blocks[current].append(line)
    for block in blocks.values():
        while block and not block[-1].strip():
            block.pop()
    return blocks


def reflow(lines: list[str]) -> list[tuple[int, str]]:
    """Une las líneas de cada párrafo o bullet en una sola. Devuelve (sangría, texto); «» es un salto de párrafo."""
    items: list[tuple[int, str]] = []
    pending_break = False
    for raw in lines:
        if not raw.strip():
            pending_break = True
            continue
        indent = len(raw) - len(raw.lstrip())
        text = raw.strip()
        is_bullet = text.startswith("- ")
        if items and not pending_break and not is_bullet and items[-1][1]:
            items[-1] = (items[-1][0], items[-1][1] + " " + text)
        else:
            if pending_break and items:
                items.append((0, ""))
            items.append((indent, text))
        pending_break = False
    return items


def render(items: list[tuple[int, str]]) -> list[str]:
    return [" " * indent + text if text else "" for indent, text in items]


def groups(items: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Unidades filtrables: un bullet o párrafo de primer nivel con sus sub-bullets."""
    result: list[list[tuple[int, str]]] = []
    for item in items:
        if not item[1]:
            continue
        if result and item[0] > result[-1][0][0]:
            result[-1].append(item)
        else:
            result.append([item])
    return result


def domains_of(text: str) -> set[str]:
    return {f"D{first or second}" for first, second in DOMAIN_CITE.findall(text)}


def guide_for_domain(lines: list[str], domain: str, own_domains: set[str]) -> list[str]:
    """Los bullets de «QUÉ DICE LA GUÍA» que citan el dominio. Un bullet sin cita hereda el del anterior."""
    units = groups(reflow(lines))
    found = [domains_of(" ".join(text for _, text in unit)) for unit in units]
    # Herencia: un bullet sin citas va con el dominio del anterior (o del siguiente, si es el primero).
    for index, cites in enumerate(found):
        if not cites:
            previous = next((found[i] for i in range(index - 1, -1, -1) if found[i]), None)
            following = next((found[i] for i in range(index + 1, len(found)) if found[i]), None)
            found[index] = previous or following or set(own_domains)
    kept = [unit for unit, cites in zip(units, found) if domain in cites]
    return render([item for unit in kept for item in unit]) if kept else [NO_GUIDE]


# --- Orígenes --------------------------------------------------------------------

def concepts(root: Path) -> dict[str, str]:
    """{viñeta: destino completo de CONCEPTOS.md} de las filas ☑."""
    text = (root / "CONCEPTOS.md").read_text(encoding="utf-8")
    return dict(CONCEPT_ROW.findall(text))


def module_path(root: Path, destination: str) -> Path:
    app, rest = destination.split("/", 1)
    matches = sorted(root.glob(f"{app}_*/{rest}.py"))
    if not matches:
        raise FileNotFoundError(f"no hay módulo para {destination}")
    return matches[0]


def module_origin(root: Path, destination: str, domain: str, all_domains: set[str], own: list[str]) -> Origin:
    path = module_path(root, destination)
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    lines = doc.splitlines()
    title = lines[0].strip().rstrip(".") if lines else path.stem
    blocks = header_blocks(lines)
    trap = render(reflow(blocks["trap"])) or [NO_TRAP]
    source = destination.split("_", 1)[0]
    return Origin(f"{source} · {title}", tuple(own), guide_for_domain(blocks["guide"], domain, all_domains), trap)


def comment_header(text: str) -> list[str]:
    """Líneas de la cabecera de un archivo (comentario HTML o `#` en frontmatter) sin sus marcas, hasta el INTRODUCE."""
    lines = text.splitlines()
    stop = next(i for i, line in enumerate(lines[:60]) if MARKER_LINE.match(line))
    start = next(i for i in range(stop, -1, -1) if re.match(r"^\s*(?:<!--|#)?\s*CONCEPTO\b", lines[i]))
    cleaned = [re.sub(r"^\s*(<!--|#)\s?", "", line) for line in lines[start:stop + 1]]
    return [re.sub(r"\s*-->\s*$", "", line) for line in cleaned]


def file_origins(root: Path) -> list[tuple[Origin, tuple[str, ...]]]:
    """Orígenes de D3 con cabecera en comentario: CLAUDE.md, reglas, skills, comandos y estándares."""
    files = [root / "CLAUDE.md", *sorted((root / ".claude").rglob("*.md")), *sorted((root / "docs").glob("estandares-*.md"))]
    origins = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if not any(MARKER_LINE.match(line) for line in text.splitlines()[:60]):
            continue
        lines = comment_header(text)
        marker = next(line for line in lines if line.startswith("INTRODUCE:"))
        vignettes = tuple(f"TS {m.group(1)}.{m.group(2)}-{m.group(3)}{m.group(4)}" for m in VIGNETTE.finditer(marker))
        concept = next(line for line in lines if line.startswith("CONCEPTO"))
        topic = concept.split(":", 1)[1].strip().rstrip(".")
        blocks = header_blocks(lines)
        guide = render(reflow(blocks["guide"])) or [NO_GUIDE]
        trap = render(reflow(blocks["trap"])) or [NO_TRAP]
        relative = path.relative_to(root).as_posix()
        origins.append((Origin(f"`{relative}` · {topic}", vignettes, guide, trap), vignettes))
    return origins


def readme_origins(root: Path) -> list[tuple[Origin, tuple[str, ...]]]:
    """Orígenes de D3 en la prosa de la sección 2 de `d3_claude_code/README.md`."""
    text = (root / "d3_claude_code" / "README.md").read_text(encoding="utf-8")
    origins = []
    for part in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
        marker = re.search(r"<!-- INTRODUCE: (.*?) -->", part)
        if not marker:
            continue
        title = part.splitlines()[0].strip()
        vignettes = tuple(f"TS {m.group(1)}.{m.group(2)}-{m.group(3)}{m.group(4)}" for m in VIGNETTE.finditer(marker.group(1)))
        lines = part.splitlines()
        guide_lines = labelled_paragraph(lines, r"\*\*Qué dice la guía \([^)]*\):\*\* ")
        # Cuando la sección reúne varias técnicas, cada una trae su frase de la guía antes del «Caso».
        for line in lines:
            technique = re.match(r"^\*\*(.+? \(TS [^)]*\))\.\*\* (.*)$", line)
            if technique:
                guide_text = re.split(r"\s+Caso[: (]", technique.group(2))[0]
                guide_lines.append(f"- **{technique.group(1)}.** {guide_text}")
        trap_lines = labelled_paragraph(lines, r"\*\*Anti-patrón / trampa del examen:\*\* ")
        guide = render(reflow(guide_lines)) or [NO_GUIDE]
        trap = render(reflow(trap_lines)) or [NO_TRAP]
        origins.append((Origin(f"`d3_claude_code/README.md` §{title}", vignettes, guide, trap), vignettes))
    return origins


def labelled_paragraph(lines: list[str], label: str) -> list[str]:
    """El párrafo que empieza con `label` (sin la etiqueta) y la lista de bullets que lo sigue, si la hay."""
    for index, line in enumerate(lines):
        match = re.match(label, line)
        if not match:
            continue
        taken = [line[match.end():]]
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip():
            taken.append(lines[cursor])
            cursor += 1
        # Tras una línea en blanco puede venir una lista que sigue siendo parte del bloque.
        peek = cursor
        while peek < len(lines) and not lines[peek].strip():
            peek += 1
        if peek < len(lines) and lines[peek].startswith("- "):
            taken.append("")
            while peek < len(lines) and lines[peek].strip():
                taken.append(lines[peek])
                peek += 1
        return taken
    return []


# --- Hojas -----------------------------------------------------------------------

def build_sheets(root: Path = ROOT) -> dict[str, str]:
    """{"D1": texto, …}: una hoja por dominio, con una sección por origen."""
    names = {}
    for domain, name in DOMAIN_ROW.findall((root / "CONCEPTOS.md").read_text(encoding="utf-8")):
        names.setdefault(domain, name.strip())
    by_domain_destination: dict[str, dict[str, list[str]]] = {domain: {} for domain in names}
    module_domains: dict[str, set[str]] = {}
    for vignette, destination in concepts(root).items():
        domain = f"D{vignette[3]}"
        module_domains.setdefault(destination, set()).add(domain)
        if destination != "d3":
            by_domain_destination[domain].setdefault(destination, []).append(vignette)
    d3_origins = file_origins(root) + readme_origins(root)

    sheets = {}
    for domain, name in names.items():
        entries: list[tuple[tuple[int, int, str, int], Origin]] = []
        for destination, own in by_domain_destination[domain].items():
            own = sorted(own, key=vignette_key)
            origin = module_origin(root, destination, domain, module_domains[destination], own)
            entries.append((vignette_key(own[0]), origin))
        if domain == "D3":
            for origin, vignettes in d3_origins:
                entries.append((vignette_key(min(vignettes, key=vignette_key)), origin))
        entries.sort(key=lambda entry: entry[0])
        lines = [f"# {domain} · {name}", "", *HEAD_NOTE]
        for _, origin in entries:
            lines += ["", f"## {origin.heading}", "", f"Viñetas: {', '.join(origin.vignettes)}", "", "**Qué dice la guía**", ""]
            lines += origin.guide + ["", "**Trampa del examen**", ""] + origin.trap
        sheets[domain] = "\n".join(lines) + "\n"
    return sheets


def main(argv: list[str] | None = None, target: Path = SHEETS_DIR) -> int:
    parser = argparse.ArgumentParser(description="Genera docs/repaso/D1.md … D5.md a partir de las cabeceras.")
    parser.add_argument("--check", action="store_true", help="solo comprueba que las hojas coinciden; no escribe")
    args = parser.parse_args(argv)
    sheets = build_sheets()
    if args.check:
        stale = []
        for domain, text in sheets.items():
            path = target / f"{domain}.md"
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        if stale:
            print(f"Hojas desactualizadas o ausentes: {', '.join(stale)}. Regenera con `uv run python -m harness.hojas_repaso`.")
            return 1
        print("Hojas de repaso al día.")
        return 0
    target.mkdir(parents=True, exist_ok=True)
    for domain, text in sheets.items():
        (target / f"{domain}.md").write_text(text, encoding="utf-8")
    print(f"Escritas {len(sheets)} hojas en {target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
