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
módulo y queda fuera de las fases.
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
    if name not in PHASES:
        raise ValueError(f"fase «{name}» desconocida: usa una de {', '.join(PHASES)}")
    section = module.section()
    parts = subsections(strip_details(section))
    headings = [heading for heading, _ in parts]

    def index(prefix: str) -> int:
        return next(i for i, heading in enumerate(headings) if heading.startswith(prefix))

    exercise, run, question = index("El ejercicio"), index("Ejecutar"), index("Pregunta tipo examen")
    script = module.script.relative_to(module.app_dir.parent).as_posix()

    if name == "ficha":
        head = f"# {module.id} · {module.label}\n\nViñetas: {module.vignettes}\nScript: {script}\n\n"
        context = app_context(readme_text(module.app_dir))
        return head + render(parts[:exercise]) + "\n## Contexto común de la app\n\n" + context
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
    lines.append("D3 (configuración de Claude Code) no es un módulo narrado: se lee en `d3_claude_code/README.md`.")
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


def main(argv: list[str] | None = None) -> int:
    # Claude Code lee UTF-8; en Windows la salida por defecto sería cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fases de los módulos para /practica-guiada.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("menu", help="todo lo disponible, con el módulo recomendado")
    commands.add_parser("setup", help="comprobaciones de puesta en marcha")
    phase_parser = commands.add_parser("fase", help="el texto de una fase de un módulo")
    phase_parser.add_argument("args", nargs="+", metavar="MÓDULO… FASE", help=f"p. ej. app1/01 ficha; fases: {', '.join(PHASES)}")
    args = parser.parse_args(argv)

    if args.command == "menu":
        print(menu(), end="")
        return 0
    if args.command == "setup":
        print(setup_report(), end="")
        return 0
    if len(args.args) < 2:
        parser.error("faltan el módulo y la fase: fase app1/01 ficha")
    try:
        print(phase(resolve(" ".join(args.args[:-1])), args.args[-1]), end="")
    except ValueError as error:
        # Un id o una fase mal escritos son errores de uso: mensaje y pista, no traza.
        print(f"[narrador] {error}. Lista de módulos: uv run python -m harness.narrador menu", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
