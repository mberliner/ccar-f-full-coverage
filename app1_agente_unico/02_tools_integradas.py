"""Tools integradas del Agent SDK: elegir la herramienta adecuada para explorar y editar un repositorio.

CONCEPTO [TS 2.5-K1, K2, K3, K4, S1, S2, S3, S4, S5]: `Grep` para el contenido,
`Glob` para las rutas, `Read`/`Write` para el archivo completo, `Edit` para un
cambio dirigido con respaldo `Read` + `Write`, exploración incremental y rastreo
de nombres exportados por módulos *wrapper*.

QUÉ DICE LA GUÍA:
- `Grep` busca patrones dentro del contenido: nombres de función, mensajes de
  error, sentencias `import` (2.5-K1). Se elige para dar con todos los sitios
  que llaman a una función o con el archivo que emite un error (2.5-S1).
- `Glob` casa patrones de ruta, es decir, encuentra archivos por su nombre o su
  extensión (2.5-K2), como el conjunto de archivos de tests (2.5-S2).
- `Read` y `Write` operan sobre el archivo entero; `Edit` hace un cambio
  localizado que depende de que el texto de referencia aparezca una sola vez
  (2.5-K3). Cuando ese texto se repite y `Edit` falla, el respaldo fiable es
  cargar el archivo con `Read` y guardarlo completo con `Write` (2.5-K4, 2.5-S3).
- Un código desconocido se entiende por pasos: `Grep` localiza los puntos de
  entrada y `Read` sigue desde ahí los imports y el flujo, en lugar de leer
  todos los archivos por adelantado (2.5-S4).
- Para rastrear una función que pasa por módulos *wrapper*, primero se reúnen
  todos los nombres con que se exporta y después se busca cada uno (2.5-S5).
- El enunciado de la TS 2.5 incluye `Bash` en la lista de tools, pero ninguna
  viñeta lo concreta. Este módulo no se lo da al agente.

POR QUÉ IMPORTA (inferencia propia): con las mismas tools, el agente gasta más
o menos llamadas, lecturas y coste según cuál elija para cada pregunta. Y un
rastreo que se queda en el nombre original devuelve una lista incompleta que
parece completa: nada en la respuesta avisa de lo que falta.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: leer todo de entrada en vez de explorar con `Grep` →
  `Read` va contra 2.5-S4 (`--anti leer_todo`); buscar solo el nombre original
  cuando hay reexportaciones contradice 2.5-S5 (`--anti solo_nombre`); ante un
  `Edit` con ancla repetida, el respaldo que nombra la guía es `Read` + `Write`.
- Inferencias propias: quitar `Grep` (`--anti sin_grep`) es una forma de forzar
  la lectura archivo por archivo, no un caso que la guía describa; la trampa
  probable de examen es confundir `Glob` (rutas) con `Grep` (contenido), o
  reintentar el mismo `Edit` como si el fallo fuera pasajero. Ampliar el ancla
  con más contexto también resuelve el fallo y es válido en la práctica; la
  guía no lo menciona y el comprobador acepta ambos caminos porque mira el
  archivo final.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 02.

INTRODUCE: TS 2.5-K1, TS 2.5-K2, TS 2.5-K3, TS 2.5-K4, TS 2.5-S1, TS 2.5-S2, TS 2.5-S3, TS 2.5-S4, TS 2.5-S5

Uso: `uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda|incremental|wrapper|edicion [--anti sin_grep|leer_todo|solo_nombre]`
"""

import ast
import asyncio
import re
import sys
from collections import Counter
from pathlib import Path

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeAgentOptions, query  # noqa: E402

from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import copy_to_temp  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

PARTS = ["busqueda", "incremental", "wrapper", "edicion"]
# Cada variante anti-patrón pertenece a una parte: `--anti` solo vale con la suya.
ANTI_PART = {"sin_grep": "busqueda", "leer_todo": "incremental", "solo_nombre": "wrapper"}
TARGET = "calcular_sla"
ANCHOR = "TIMEOUT = 30"

# --- Llamadores esperados, calculados con `ast` (2.5-S5) ------------------------


def python_files(root: Path) -> dict[str, ast.Module]:
    """Todos los `.py` del repositorio de prueba, por ruta relativa con «/»."""
    return {
        path.relative_to(root).as_posix(): ast.parse(path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.py"))
    }


def exported_names(root: Path, target: str = TARGET) -> set[str]:
    """Nombres con los que `target` circula por el repositorio, siguiendo los alias encadenados."""
    trees = python_files(root)
    names = {target}
    changed = True
    # Punto fijo: `api.py` la reexporta como `sla_ticket` y otro módulo la reimporta como `plazo`.
    while changed:
        changed = False
        for tree in trees.values():
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in names and alias.asname and alias.asname not in names:
                            names.add(alias.asname)
                            changed = True
    return names


def called_names(tree: ast.Module) -> set[str]:
    """Nombres de las funciones que el módulo llama (`f(...)` o `modulo.f(...)`)."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def defines(tree: ast.Module, name: str) -> bool:
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree))


def expected_callers(root: Path) -> set[str]:
    """Archivos que llaman a `calcular_sla` con cualquiera de sus nombres (no la definición ni el reexport)."""
    names = exported_names(root)
    return {
        path for path, tree in python_files(root).items()
        if not defines(tree, TARGET) and called_names(tree) & names
    }


def alias_only_callers(root: Path) -> set[str]:
    """Llamadores que nunca escriben el nombre original: los que una búsqueda por nombre pierde."""
    trees = python_files(root)
    return {path for path in expected_callers(root) if TARGET not in called_names(trees[path])}


def expected_tests(root: Path) -> set[str]:
    """Archivos de tests que `Glob` encontraría con `**/test_*.py`."""
    return {path.relative_to(root).as_posix() for path in root.rglob("test_*.py")}


def check_paths(answer: str | None, expected: set[str]) -> tuple[set[str], set[str]]:
    """(encontrados, que faltan): qué rutas esperadas aparecen en la respuesta."""
    # Barras unificadas y sin que un nombre cuente por estar dentro de otro más largo.
    text = (answer or "").replace("\\", "/")
    found = {path for path in expected if re.search(r"(?<!\w)" + re.escape(path), text)}
    return found, expected - found


# --- Edición con ancla no única (2.5-K3, 2.5-K4, 2.5-S3) ------------------------


def anchor_count(text: str) -> int:
    return text.count(ANCHOR)


def expected_config(original: str) -> str:
    """El archivo tras cambiar solo la última aparición del ancla (el bloque de notificaciones)."""
    head, _, tail = original.rpartition(ANCHOR)
    return head + "TIMEOUT = 60" + tail


def edit_is_correct(final: str, original: str) -> bool:
    # Se compara el resultado, no el camino: `Edit` con el ancla ampliada o `Read` + `Write` valen igual.
    return final.replace("\r\n", "\n") == expected_config(original)


# --- Señales del RunRecord ---------------------------------------------------------


def tool_counts(rec: RunRecord) -> dict[str, int]:
    return dict(Counter(call.name for call in rec.tool_calls))


def edit_fallback(rec: RunRecord) -> tuple[bool, bool]:
    """(algún `Edit` falló, hubo un `Write` después del primer fallo)."""
    failed = next((i for i, c in enumerate(rec.tool_calls) if c.name == "Edit" and c.is_error), None)
    if failed is None:
        return False, False
    return True, any(c.name == "Write" for c in rec.tool_calls[failed + 1:])


def recovered_with_edit(rec: RunRecord) -> bool:
    """Tras un `Edit` fallido, otro `Edit` correcto: el ancla ampliada con más contexto."""
    failed = next((i for i, c in enumerate(rec.tool_calls) if c.name == "Edit" and c.is_error), None)
    if failed is None:
        return False
    return any(c.name == "Edit" and c.is_error is False for c in rec.tool_calls[failed + 1:])


# --- Configuración por parte y variante --------------------------------------------


def tools_for(part: str, anti: str | None) -> list[str]:
    """Tools integradas de la parte. Las de lectura nunca llevan `Write` ni `Edit`."""
    if part == "edicion":
        return ["Read", "Write", "Edit", "Grep"]
    tools = ["Read", "Grep", "Glob"]
    if anti == "sin_grep":
        # Anti-patrón: sin `Grep` el agente solo puede leer archivo por archivo.
        tools.remove("Grep")
    return tools


def prompts_for(part: str, anti: str | None) -> list[tuple[str, str]]:
    if part == "busqueda":
        return [
            ("error", "¿En qué archivo se lanza el error «SLA vencido para…»? Dime la ruta."),
            ("tests", "Lista las rutas de todos los archivos de tests del repositorio."),
        ]
    if part == "incremental":
        prompt = "Explica cómo se calcula el SLA de un ticket en este repositorio, citando los archivos que intervienen."
        if anti == "leer_todo":
            # Anti-patrón: leer todo antes de responder en vez de empezar por un punto de entrada.
            prompt += " Antes de responder, lee todos los archivos .py del repositorio."
        return [("sla", prompt)]
    if part == "wrapper":
        return [("usos", f"Encuentra todos los usos de `{TARGET}` en el repositorio y lista las rutas de los archivos que la llaman.")]
    return [(
        "timeout",
        f"En `config.py` hay dos asignaciones `{ANCHOR}`. Cambia solo el segundo (el del cliente de notificaciones) "
        "a 60 y deja todo lo demás igual.",
    )]


BASE_SYSTEM = (
    "Eres un agente que explora un repositorio Python de la mesa de ayuda de una empresa ficticia. "
    "Trabajas solo con las tools que tienes. Responde en español y de forma breve."
)


def system_prompt(part: str, anti: str | None) -> str:
    if part != "wrapper":
        return BASE_SYSTEM
    if anti == "solo_nombre":
        return BASE_SYSTEM + " Busca solo el nombre original de la función con Grep y lista los archivos que lo contienen."
    # Método correcto: los nombres exportados primero, y después una búsqueda por cada uno.
    return BASE_SYSTEM + (
        " Si una función se reexporta con otro nombre desde un módulo wrapper, identifica primero todos los "
        "nombres exportados y busca cada uno."
    )


def build_options(part: str, anti: str | None, *, cwd: Path, budget: float, model: str) -> ClaudeAgentOptions:
    tools = tools_for(part, anti)
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=system_prompt(part, anti),
        tools=tools,  # tools integradas que existen para el agente
        allowed_tools=tools,  # y se aprueban sin preguntar; con `dontAsk`, lo no aprobado se deniega
        permission_mode="dontAsk",
        cwd=str(cwd),  # la copia temporal: `Edit` y `Write` nunca tocan `datos/sinteticos/`
        max_turns=25,  # red de seguridad, no la parada
    )


# --- Ejecución ---------------------------------------------------------------------


def report(part: str, label: str, rec: RunRecord, cwd: Path, original: str | None) -> None:
    counts = tool_counts(rec)
    print(f"[medida] llamadas={counts} · Read={counts.get('Read', 0)} · coste=${rec.cost_usd or 0:.4f}")
    if part == "busqueda":
        expected = {"core/sla.py"} if label == "error" else expected_tests(cwd)
        found, missing = check_paths(rec.final_text, expected)
        print(f"[comprobación {label}] encontrados={sorted(found)} · faltan={sorted(missing)}")
    elif part == "wrapper":
        found, missing = check_paths(rec.final_text, expected_callers(cwd))
        print(f"[comprobación] llamadores encontrados={len(found)}/{len(found) + len(missing)} · faltan={sorted(missing)}")
        print(f"[comprobación] solo por alias (los que pierde buscar el nombre): {sorted(alias_only_callers(cwd))}")
    elif part == "edicion":
        failed, wrote = edit_fallback(rec)
        final = (cwd / "config.py").read_text(encoding="utf-8")
        print(
            f"[comprobación] Edit fallido={failed} · Write después={wrote} · ancla ampliada={recovered_with_edit(rec)} "
            f"· archivo correcto={edit_is_correct(final, original or '')}"
        )


def expectation(part: str, anti: str | None) -> str:
    return {
        ("busqueda", None): "Grep localiza core/sla.py y Glob lista los 3 tests, con pocos Read",
        ("busqueda", "sin_grep"): "sin Grep, más Read para dar con el mensaje de error",
        ("incremental", None): "Grep al punto de entrada y Read de los archivos que importa; pocos Read",
        ("incremental", "leer_todo"): "un Read por cada .py del repositorio y más coste",
        ("wrapper", None): "los 4 llamadores, incluidos los dos que usan alias",
        ("wrapper", "solo_nombre"): "solo 2 de los 4: los llamadores por alias se pierden",
        ("edicion", None): "Edit falla por ancla no única; después Read + Write (o Edit con más contexto); solo cambia el segundo bloque",
    }[(part, anti)]


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=list(ANTI_PART))
    parser.add_argument("--parte", choices=PARTS, required=True)
    args = parser.parse_args()
    if args.anti and ANTI_PART[args.anti] != args.parte:
        parser.error(f"--anti {args.anti} es de la parte {ANTI_PART[args.anti]}, no de {args.parte}")
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    prompts = prompts_for(args.parte, args.anti)
    for run in range(1, args.repeat + 1):
        for label, prompt in prompts:
            # Copia nueva por petición: `edicion` escribe en ella y cada ejecución parte del original.
            cwd = copy_to_temp("repo_mesa")
            original = (cwd / "config.py").read_text(encoding="utf-8")
            options = build_options(
                args.parte, args.anti, cwd=cwd,
                budget=budget / (args.repeat * len(prompts)),  # tope de toda la ejecución, repartido
                model=model,
            )
            print(f"\n=== ejecución {run}/{args.repeat} · {args.parte}/{label} · variante {args.anti or 'correcta'} ===")
            print(f"[esperado] {expectation(args.parte, args.anti)}")
            rec = await record(query(prompt=prompt, options=options))
            report(args.parte, label, rec, cwd, original)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
