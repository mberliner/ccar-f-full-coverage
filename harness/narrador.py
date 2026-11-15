"""Reparto por fases de los módulos para la skill `/practica-guiada`.

PROPÓSITO: leer la «Ruta de lectura» y las secciones `## NN · …` de los
`app*/README.md` y entregar cada módulo en fases que siguen el ciclo de 5 pasos
de «Empieza aquí» (`ficha`, `ejercicio`, `ejecutar`, `contraste`, `pregunta`,
`respuesta`). Además, un menú con todo lo disponible y una comprobación de
puesta en marcha para quien llega de cero.

POR QUÉ EXISTE: el narrador no debe enseñar el resultado de referencia ni la
respuesta antes de tiempo. Una instrucción en la skill no lo garantiza, y
`allowed-tools` en una skill sin fork preautoriza pero no restringe
(`docs/hallazgos.md`). Así que la revelación la controla el código: las fases
previas no llevan los bloques `<details>` y la cabecera del script solo sale
con la respuesta. `tests/test_narrador.py` lo comprueba en todos los módulos.

QUÉ NO HACE: no llama al modelo ni ejecuta los módulos (el gasto lo decide la
persona), no escribe nada y no guarda copia del contenido: lo lee cada vez de
los README, que siguen siendo la única fuente. Del `.env` solo mira si existe;
nunca muestra su contenido ni el de `ANTHROPIC_API_KEY`. D3 no tiene formato de
módulo: expone solo las cuatro fases de la sección 4 de su README (`d3_phase`).
El «Contexto común de la app» es una fase propia por app (`fase appN contexto`,
`app_phase`): la `ficha` de cada módulo ya no lo trae, solo dice cómo pedirlo.
Además lee `FALLOS.md` para `repaso`, saca ítems sueltos con `item` (con `--ciego`,
sin el rótulo de viñeta, para la práctica mezclada), sortea preguntas de módulos
distintos con `mixto` y entrega los casos de `simulaciones/` por partes con
`simulacion` (contexto, una pregunta, su respuesta aparte). La respuesta de un
ítem sale solo con `--respuesta`, y `repaso` y `mixto` listan ids, nunca
enunciados; `mixto` ni siquiera las viñetas.
"""

import argparse
import ast
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from harness.credentials import ROOT
from harness.estado import state_dir

PHASES = ("ficha", "ejercicio", "ejecutar", "contraste", "pregunta", "respuesta")
# Fases opcionales, fuera del ciclo: las comprobaciones cortas de un módulo y sus respuestas.
EXTRA_PHASES = ("comprobaciones", "soluciones")
# Fases de app, no de módulo: el contexto común se entrega una vez por app (`fase appN contexto`).
APP_PHASES = ("contexto",)
CONTEXT_HEADING = "## Contexto común de la app"
APP_ID = re.compile(r"app\d+", re.IGNORECASE)
CHECKS_HEADING = "Comprobaciones cortas"
CHECK_SUMMARY = "Comprobación C"
NO_CHECKS = "Este módulo no tiene comprobaciones cortas.\n"
STEP3 = "Paso 3 · Contrastar"
STEP4 = "Paso 4 · Respuesta"
STEP5 = "**Paso 5 ·**"
ROUTE_HEADING = "## Ruta de lectura"

MODULE_HEADING = re.compile(r"## (\d{2}) · (.+)")
DETAILS = re.compile(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", re.DOTALL)
# Celda de la ruta: enlace = entregado; solo código = pendiente; «a … b» = rango pendiente.
ROUTE_FILE = re.compile(r"`(\d{2})_[\w]+\.py`")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MODE = re.compile(r"\*\*Modo:\*\* [Ee]jecución (obligatoria|ligera)")
NEEDS = re.compile(r"\*\*Necesitas antes:\*\* (.+)")
FIRST_MODULE = re.compile(r"\*\*Tu primer módulo:\*\* \[[^\]]*\]\((app\d+)_[^/]*/README\.md#(\d{2})")
MODULE_ID = re.compile(r"(app\d+)[/ ](\d{1,2})(?:_\w*)?")


class UnknownModule(ValueError):
    """El id no corresponde a ningún módulo de la ruta."""


class PendingModule(ValueError):
    """El módulo está en la ruta, pero aún no se ha entregado."""


@dataclass(frozen=True)
class Module:
    app: str  # «app1»
    number: str  # «05»
    app_dir: Path
    label: str  # título de la sección o, si está pendiente, la celda de la ruta
    vignettes: str
    delivered: bool
    script: Path

    @property
    def id(self) -> str:
        return f"{self.app}/{self.number}"

    def section(self) -> str:
        return module_sections(readme_text(self.app_dir)).get(self.number, ("", ""))[1]

    def script_docstring(self) -> str:
        return ast.get_docstring(ast.parse(self.script.read_text(encoding="utf-8"))) or ""


# --- Análisis del Markdown ----------------------------------------------------

def readme_text(app_dir: Path) -> str:
    return (app_dir / "README.md").read_text(encoding="utf-8")


def module_sections(text: str) -> dict[str, tuple[str, str]]:
    """{número: (título, cuerpo)} de cada `## NN · …`, hasta el siguiente `## `."""
    sections: dict[str, tuple[str, str]] = {}
    current = None
    for line in text.splitlines():
        match = MODULE_HEADING.match(line)
        if match:
            current = match.group(1)
            sections[current] = (match.group(2).strip(), "")
        elif line.startswith("## "):
            current = None  # otra sección de nivel 2: ya no es del módulo
        elif current is not None:
            title, body = sections[current]
            sections[current] = (title, body + line + "\n")
    return sections


def subsections(text: str) -> list[tuple[str, str]]:
    """[(título del `###`, cuerpo)], con el preámbulo como título vacío. Ignora `###` dentro de bloques de código."""
    parts: list[tuple[str, str]] = [("", "")]
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("### "):
            parts.append((line[4:].strip(), ""))
            continue
        heading, body = parts[-1]
        parts[-1] = (heading, body + line + "\n")
    return parts


def strip_details(text: str) -> str:
    """Quita todos los bloques plegados: lo que se abre después nunca va en una fase previa."""
    return DETAILS.sub("", text)


def details_body(text: str, summary_prefix: str) -> str:
    """Cuerpo del primer `<details>` cuyo `summary` empieza por `summary_prefix`, o «» si no hay."""
    for summary, body in DETAILS.findall(text):
        if summary.strip().startswith(summary_prefix):
            return body.strip("\n") + "\n"
    return ""


def all_details_body(text: str, summary_prefix: str) -> str:
    """Cuerpos de todos los `<details>` cuyo `summary` empieza por `summary_prefix`, en orden y separados.

    Un módulo con varias preguntas (p. ej. una de respuesta única y otra multiple-response) lleva un
    «Paso 4 · Respuesta» por pregunta; la fase `respuesta` los muestra todos.
    """
    bodies = [body.strip("\n") + "\n" for summary, body in DETAILS.findall(text) if summary.strip().startswith(summary_prefix)]
    return "\n".join(bodies)


def app_context(text: str) -> str:
    """Lo común de la app antes de «Ruta de lectura» (intro, equivalencias, servidor y sus tools)."""
    head = text.split(ROUTE_HEADING, 1)[0]
    lines = head.splitlines()
    return "\n".join(lines[1:] if lines and lines[0].startswith("# ") else lines).strip() + "\n"


def app_phase(app: str, name: str) -> str:
    """El contexto común de una app (fase propia, fuera de la ficha de cada módulo)."""
    if name not in APP_PHASES:
        raise ValueError(f"fase de app «{name}» desconocida: usa {', '.join(APP_PHASES)}")
    app_id = app.strip().lower()
    readme = next(iter(sorted(ROOT.glob(f"{app_id}_*/README.md"))), None) if APP_ID.fullmatch(app_id) else None
    if readme is None:
        raise ValueError(f"app «{app}» desconocida")
    return f"{CONTEXT_HEADING}\n\n" + app_context(readme_text(readme.parent))


def plain(text: str) -> str:
    """Quita los enlaces Markdown y deja su texto: el menú es para leer en la terminal."""
    return MARKDOWN_LINK.sub(r"\1", text).strip()


# --- Ruta de módulos ----------------------------------------------------------

def app_dirs(root: Path) -> list[Path]:
    return sorted(path.parent for path in root.glob("app*/README.md"))


def route_rows(text: str) -> list[tuple[str, str]]:
    """[(celda del módulo, celda de viñetas)] de la tabla de «Ruta de lectura»."""
    route = text.split(ROUTE_HEADING, 1)[1].split("\n## ", 1)[0] if ROUTE_HEADING in text else ""
    rows = []
    for line in route.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and ROUTE_FILE.search(cells[0]):
            rows.append((cells[0], cells[1]))
    return rows


def route(root: Path = ROOT) -> list[Module]:
    """Todos los módulos de la ruta, en el orden de lectura, entregados o no."""
    modules = []
    for app_dir in app_dirs(root):
        app = app_dir.name.split("_", 1)[0]
        text = readme_text(app_dir)
        titles = {number: title for number, (title, _) in module_sections(text).items()}
        for cell, vignettes in route_rows(text):
            numbers = ROUTE_FILE.findall(cell)
            delivered = "](" in cell and numbers[0] in titles
            # Un rango («04_… … 12_…») es un único bloque pendiente: cada número del rango cuenta.
            span = range(int(numbers[0]), int(numbers[-1]) + 1) if not delivered else [int(numbers[0])]
            for value in span:
                number = f"{value:02d}"
                script = next(app_dir.glob(f"{number}_*.py"), app_dir / f"{number}_pendiente.py")
                label = titles.get(number, plain(cell)) if delivered else plain(cell)
                modules.append(Module(app, number, app_dir, label, plain(vignettes), delivered, script))
    return modules


def resolve(text: str, root: Path = ROOT) -> Module:
    """Módulo entregado a partir de `app1/05`, `app1/05_nombre`, `app1 05` o `app1/5`."""
    match = MODULE_ID.fullmatch(text.strip().lower())
    if not match:
        raise UnknownModule(f"«{text}» no tiene la forma appN/NN (por ejemplo, app1/01)")
    wanted = f"{match.group(1)}/{int(match.group(2)):02d}"
    for module in route(root):
        if module.id == wanted:
            if not module.delivered:
                raise PendingModule(f"{wanted} está en la ruta pero aún no se ha entregado")
            return module
    raise UnknownModule(f"{wanted} no está en ninguna «Ruta de lectura»")


def recommended(root: Path = ROOT) -> str | None:
    """El id que «Empieza aquí» da como primer módulo."""
    match = FIRST_MODULE.search((root / "README.md").read_text(encoding="utf-8"))
    return f"{match.group(1)}/{match.group(2)}" if match else None


# --- Fases ------------------------------------------------------------------

def render(parts: list[tuple[str, str]]) -> str:
    return "".join((f"### {heading}\n" if heading else "") + body for heading, body in parts).strip() + "\n"


def phase(module: Module, name: str) -> str:
    """El texto de una fase. Ninguna fase previa a `contraste` lleva bloques plegados."""
    if name not in PHASES + EXTRA_PHASES:
        raise ValueError(f"fase «{name}» desconocida: usa una de {', '.join(PHASES + EXTRA_PHASES)}")
    section = module.section()
    parts = subsections(strip_details(section))
    headings = [heading for heading, _ in parts]

    if name == "comprobaciones":
        # Solo los enunciados y las opciones: sus respuestas plegadas salen con `soluciones`.
        found = [(heading, body) for heading, body in parts if heading.startswith(CHECKS_HEADING)]
        if not found:
            return NO_CHECKS
        heading, body = found[0]
        body = "\n".join(line for line in body.splitlines() if not line.startswith(STEP5) and line.strip() != "---")
        return render([(heading, body + "\n")])
    if name == "soluciones":
        return all_details_body(section, CHECK_SUMMARY) or NO_CHECKS

    def index(prefix: str) -> int:
        return next(i for i, heading in enumerate(headings) if heading.startswith(prefix))

    exercise, run, question = index("El ejercicio"), index("Ejecutar"), index("Pregunta tipo examen")
    script = module.script.relative_to(module.app_dir.parent).as_posix()

    if name == "ficha":
        head = f"# {module.id} · {module.label}\n\nViñetas: {module.vignettes}\nScript: {script}\n\n"
        # El contexto común va aparte, una vez por app: la ficha solo dice cómo pedirlo.
        pointer = f"\n_Contexto común de la app: `uv run python -m harness.narrador fase {module.app} contexto`._\n"
        return head + render(parts[:exercise]) + pointer
    if name == "ejercicio":
        return render(parts[exercise:run])
    if name == "ejecutar":
        return render(parts[run:question])
    if name == "contraste":
        return details_body(section, STEP3)
    if name == "pregunta":
        # La línea del paso 5 y el separador van después de la respuesta, no con la pregunta.
        heading, body = parts[question]
        body = "\n".join(line for line in body.splitlines() if not line.startswith(STEP5) and line.strip() != "---")
        return render([(heading, body + "\n")])
    step5 = next((line for line in section.splitlines() if line.startswith(STEP5)), "")
    return (
        all_details_body(section, STEP4)
        + f"\n{step5}\n\n## Para profundizar: cabecera de `{script}`\n\n"
        + module.script_docstring()
        + "\n"
    )


# --- D3 -------------------------------------------------------------------------------

D3_PHASES = ("comprobaciones", "soluciones", "pregunta", "respuesta")


def d3_blocks(root: Path = ROOT) -> list[tuple[str, str]]:
    """[(título del `####`, cuerpo)] de la sección 4 del README de D3, en orden."""
    text = (root / "d3_claude_code" / "README.md").read_text(encoding="utf-8").split("\n## 4 · ", 1)[1]
    blocks: list[tuple[str, str]] = []
    collecting = False
    for line in text.splitlines():
        if line.startswith("#### "):
            blocks.append((line[5:].strip(), ""))
            collecting = True
        elif line.startswith("## ") or line.startswith("### "):
            collecting = False
        elif collecting:
            title, body = blocks[-1]
            blocks[-1] = (title, body + line + "\n")
    return blocks


def d3_phase(name: str, root: Path = ROOT) -> str:
    """Una fase de D3: `comprobaciones` y `soluciones` (4.1, una por TS) o `pregunta` y `respuesta` (4.2)."""
    if name not in D3_PHASES:
        raise ValueError(f"D3 no tiene la fase «{name}»: usa una de {', '.join(D3_PHASES)}")
    short = name in ("comprobaciones", "soluciones")
    answers = name in ("soluciones", "respuesta")
    out = []
    for title, body in d3_blocks(root):
        if title.startswith("TS ") != short:
            continue
        if answers:
            # Cada respuesta lleva el título de su pregunta: sin él, varias letras seguidas no se pueden cotejar.
            # Solo el texto de la respuesta, sin las etiquetas del plegado (como la fase `respuesta` de un módulo).
            block = DETAILS.search(body)
            out.append(f"### {title}\n\n{block.group(2).strip() if block else ''}\n")
        else:
            question = "\n".join(line for line in strip_details(body).splitlines() if line.strip() != "---")
            out.append(f"### {title}\n\n{question.strip()}\n")
    return "\n".join(out)


# --- Menú y puesta en marcha ----------------------------------------------------

def menu(root: Path = ROOT) -> str:
    """Todo lo disponible, por app, con el primer módulo recomendado marcado con ★."""
    star = recommended(root)
    lines = [
        "# Práctica guiada · qué hay disponible",
        "",
        # Los nombres `app1/05` son lo primero que ve quien llega de cero: se explican antes de la lista.
        "Cómo se leen los nombres: `appN/NN` es una app y un módulo suyo. `app1/05` es el módulo 05 de la app 1 "
        "(el script `app1_agente_unico/05_…py`). Cada app agrupa un tema y el número solo ordena los módulos dentro de ella.",
        "",
        "- **Puesta en marcha**: comprobar instalación, credencial y estado personal (si empiezas de cero).",
        "",
    ]
    seen_pending: set[str] = set()
    for app_dir in app_dirs(root):
        title = readme_text(app_dir).splitlines()[0].lstrip("# ").strip()
        lines.append(f"## {title}")
        for module in route(root):
            if module.app_dir != app_dir:
                continue
            if not module.delivered:
                # Un rango pendiente se lista una vez, con su celda completa.
                key = f"{module.app}:{module.label}"
                if key not in seen_pending:
                    seen_pending.add(key)
                    lines.append(f"- {module.id} · {module.label} · próximamente")
                continue
            preface = subsections(module.section())[0][1]
            mode = MODE.search(preface)
            needs = NEEDS.search(preface)
            mark = " ★ recomendado para empezar" if module.id == star else ""
            lines.append(
                f"- {module.id} · {module.label}{mark}\n"
                f"  Modo: ejecución {mode.group(1) if mode else '¿?'} · Necesitas antes: {plain(needs.group(1)) if needs else '¿?'}\n"
                f"  Viñetas: {module.vignettes}"
            )
        lines.append("")
    lines.append(
        "Simulaciones por escenario: `simulacion` lista los casos; `simulacion E<n>` da el contexto, "
        "`simulacion E<n> <N>` una pregunta y `--respuesta` su respuesta.\n"
    )
    lines.append(
        "D3 (configuración de Claude Code): `fase d3 <fase>` con comprobaciones, soluciones, pregunta y respuesta "
        "(sección 4). Las secciones 1 a 3 no se narran: se leen en `d3_claude_code/README.md`."
    )
    return "\n".join(lines) + "\n"


def setup_report(root: Path = ROOT, environ: Mapping[str, str] | None = None) -> str:
    """Comprobaciones de quien llega de cero, con qué hacer si falta algo. Nunca muestra secretos."""
    environ = os.environ if environ is None else environ
    lines = ["# Puesta en marcha", "", "✓ uv: este informe ya se ejecuta con `uv run`."]

    if environ.get("ANTHROPIC_API_KEY"):
        lines.append("✓ Credencial: `ANTHROPIC_API_KEY` está en el entorno (su valor no se muestra).")
    elif (root / ".env").exists():
        # Solo se mira que existe: su contenido no se lee (y Claude tiene denegado leerlo).
        lines.append("✓ Credencial: existe `.env` (no se lee; si la clave no es válida, lo dirá la primera ejecución con modelo).")
    else:
        lines.append(
            "✗ Credencial: no hay `.env` ni `ANTHROPIC_API_KEY`. Para ejecutar con modelo: `cp .env.example .env` y pon tu clave."
            " Sin ella puedes hacer los módulos en modo ligero."
        )

    try:
        target, _ = state_dir(root=root)
    except ValueError as error:
        lines.append(f"✗ Estado personal: {error}")
    else:
        fallos = target / "FALLOS.md"
        if fallos.exists():
            lines.append(f"✓ Estado personal: {fallos}")
        else:
            lines.append(f"✗ Estado personal: falta {fallos}. Créalo con `uv run python -m harness.estado init`.")
    return "\n".join(lines) + "\n"


# --- Repaso e ítems -------------------------------------------------------------------

def item_command(args: argparse.Namespace) -> int:
    """`item <id> [--respuesta]`: el enunciado solo, o su respuesta; la revelación la decide este código."""
    from harness.items import blind_statement, find_item

    try:
        item = find_item(args.id)
    except ValueError as error:
        print(f"[narrador] {error}. Los ids salen de `repaso` y `mixto`.", file=sys.stderr)
        return 2
    # `--ciego` solo recorta el enunciado: con la respuesta la viñeta ya no es un secreto.
    text = item.answer if args.respuesta else (blind_statement(item) if args.ciego else item.statement)
    print(text, end="" if text.endswith("\n") else "\n")
    return 0


def simulacion_command(args: argparse.Namespace) -> int:
    """`simulacion [E<n> [N] [--respuesta]]`: lista de casos, contexto de un caso, una pregunta o su respuesta."""
    from harness.simulaciones import UnknownCase, case_answer, case_context, case_question, list_cases

    try:
        if args.caso is None:
            if args.respuesta:
                raise UnknownCase("la respuesta se pide de una pregunta concreta: simulacion E<n> <N> --respuesta")
            for code, title, size in list_cases():
                print(f"- {code} · {title} · {size} preguntas")
            print("\nContexto: `simulacion E<n>`; una pregunta: `simulacion E<n> <N>`; su respuesta: `simulacion E<n> <N> --respuesta`.")
            return 0
        if args.numero is None:
            if args.respuesta:
                raise UnknownCase("la respuesta se pide de una pregunta concreta: simulacion E<n> <N> --respuesta")
            print(case_context(args.caso), end="")
            return 0
        try:
            number = int(args.numero)
        except ValueError:
            raise UnknownCase(f"«{args.numero}» no es un número de pregunta") from None
        print((case_answer if args.respuesta else case_question)(args.caso, number), end="")
    except UnknownCase as error:
        print(f"[narrador] {error}", file=sys.stderr)
        return 2
    return 0


def repaso_command(args: argparse.Namespace) -> int:
    """`repaso [--hoy] [--todas]`: la cola de repaso como lista de ids. Solo lee `FALLOS.md`."""
    from datetime import date

    from harness.repaso import parse_failures, review_queue, unreadable_rows

    try:
        today = date.fromisoformat(args.hoy) if args.hoy else date.today()
    except ValueError:
        print(f"[narrador] «{args.hoy}» no es una fecha AAAA-MM-DD", file=sys.stderr)
        return 2
    try:
        target, _ = state_dir()
    except ValueError as error:
        print(f"[narrador] {error}", file=sys.stderr)
        return 2
    fallos = target / "FALLOS.md"
    if not fallos.exists():
        print(f"No hay {fallos}. Créalo con `uv run python -m harness.estado init`.")
        return 0

    failures = parse_failures(fallos.read_text(encoding="utf-8"))
    queue = review_queue(failures, today, include_future=args.todas)
    skipped = unreadable_rows(failures)
    print(f"# Repaso · {today.isoformat()}\n")
    if not queue:
        print("Nada que repasar.")
    for entry in queue:
        due = f"vence {entry.due.isoformat()}" if entry.due else "sin fecha"
        rows = f" · {entry.rows} filas" if entry.rows > 1 else ""
        print(f"- {entry.item.id} · {entry.vignette} · {due} · repasos {entry.reviews}{rows}")
    if queue:
        print("\nCada pregunta: `uv run python -m harness.narrador item <id>`; su respuesta, con `--respuesta`.")
    if skipped:
        print(f"\n{skipped} fila{'s' if skipped > 1 else ''} de FALLOS.md sin viñeta reconocible: no entra en el repaso.")
    return 0


def mixto_command(args: argparse.Namespace) -> int:
    """`mixto [--dominio Dn] [-n N] [--semilla S]`: ids de preguntas de módulos distintos, sin enunciados."""
    import random

    from harness.items import mixed_selection

    seed = args.semilla if args.semilla is not None else random.randrange(1_000_000)
    try:
        selection = mixed_selection(n=args.n, domain=args.dominio, seed=seed)
    except ValueError as error:
        print(f"[narrador] {error}", file=sys.stderr)
        return 2
    scope = f" · {args.dominio.upper()}" if args.dominio else ""
    print(f"# Práctica mezclada{scope}\n")
    print(f"semilla: {seed}\n")
    for item in selection:
        # Solo el id: las viñetas delatarían el tema antes de leer la pregunta.
        print(f"- {item.id}")
    print("\nCada pregunta: `uv run python -m harness.narrador item <id>`; su respuesta, con `--respuesta`.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # La salida ya va en UTF-8: lo fija `harness/__init__.py` al importar el paquete.
    parser =argparse.ArgumentParser(description="Fases de los módulos para /practica-guiada.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("menu", help="todo lo disponible, con el módulo recomendado")
    commands.add_parser("setup", help="comprobaciones de puesta en marcha")
    phase_parser = commands.add_parser("fase", help="el texto de una fase de un módulo")
    phase_parser.add_argument("args", nargs="+", metavar="MÓDULO… FASE", help=f"p. ej. app1/01 ficha; fases: {', '.join(PHASES + EXTRA_PHASES)}; de app: app2 contexto")
    repaso_parser = commands.add_parser("repaso", help="filas de FALLOS.md que tocan repasar hoy (ids, sin enunciados)")
    repaso_parser.add_argument("--hoy", help="fecha de hoy AAAA-MM-DD (por defecto, la del sistema)")
    repaso_parser.add_argument("--todas", action="store_true", help="incluye también las filas que aún no vencen")
    item_parser = commands.add_parser("item", help="una pregunta o comprobación corta por id, p. ej. app1/02:C1")
    item_parser.add_argument("id")
    item_parser.add_argument("--respuesta", action="store_true", help="muestra su respuesta en vez del enunciado")
    item_parser.add_argument("--ciego", action="store_true", help="enunciado sin el rótulo de viñeta (práctica mezclada)")
    sim_parser = commands.add_parser("simulacion", help="casos de simulaciones/: sin argumentos, la lista; con E<n>, su contexto; con N, la pregunta")
    sim_parser.add_argument("caso", nargs="?", help="E1 a E6")
    sim_parser.add_argument("numero", nargs="?", help="número de pregunta")
    sim_parser.add_argument("--respuesta", action="store_true", help="la respuesta de esa pregunta, con su TS")
    mixto_parser = commands.add_parser("mixto", help="práctica mezclada: ids de preguntas de módulos distintos")
    mixto_parser.add_argument("--dominio", help="solo un dominio, D1 a D5")
    mixto_parser.add_argument("-n", type=int, default=10, help="cuántas (por defecto 10)")
    mixto_parser.add_argument("--semilla", type=int, help="repite una tanda anterior")
    args = parser.parse_args(argv)

    if args.command in ("repaso", "item", "mixto", "simulacion"):
        # Lazy: `harness.items` importa este módulo, así que no puede importarse arriba.
        handlers = {"item": item_command, "repaso": repaso_command, "mixto": mixto_command, "simulacion": simulacion_command}
        return handlers[args.command](args)
    if args.command == "menu":
        print(menu(), end="")
        return 0
    if args.command == "setup":
        print(setup_report(), end="")
        return 0
    if len(args.args) < 2:
        parser.error("faltan el módulo y la fase: fase app1/01 ficha")
    try:
        if len(args.args) == 2 and args.args[0].lower() == "d3":
            print(d3_phase(args.args[1]), end="")
            return 0
        if len(args.args) == 2 and APP_ID.fullmatch(args.args[0]):
            print(app_phase(args.args[0], args.args[1]), end="")
            return 0
        print(phase(resolve(" ".join(args.args[:-1])), args.args[-1]), end="")
    except ValueError as error:
        # Un id o una fase mal escritos son errores de uso: mensaje y pista, no traza.
        print(f"[narrador] {error}. Lista de módulos: uv run python -m harness.narrador menu", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
