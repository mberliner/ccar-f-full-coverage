"""Contexto largo: scratchpad, resumen entre fases y manifest para retomar tras una caída.

CONCEPTO [TS 5.4-K1, K2, K3, K4, S1, S2, S3, S4, S5]: cómo se sostiene una
investigación en varias fases sin que el contexto de un solo hilo se llene y se
degrade, y cómo se retoma si el proceso se corta.

BORRADOR (texto pendiente del pase de Opus 5.5, ver NOTAS.md): este módulo se
escribió contra el diseño de la entrega 3 y contra un resumen de las viñetas, no
contra el texto de la guía. Las viñetas se citan por Task Statement; el reparto
exacto de cada K y S y la parte de `QUÉ DICE LA GUÍA` se contrastan con la guía
en ese pase.

QUÉ DICE LA GUÍA (según el resumen de las viñetas; contrastar):
- En sesiones largas el contexto se degrada: las respuestas se vuelven
  inconsistentes y el modelo recurre a «patrones típicos» en vez de a lo que
  descubrió (K1).
- Se mitiga con un *scratchpad* donde se guardan los hallazgos clave y que se
  consulta en las preguntas siguientes (K2, S2), y delegando las preguntas
  concretas a subagentes mientras el agente principal coordina (K3, S1).
- Al pasar de una fase a la siguiente, el resumen de la fase se inyecta en el
  contexto inicial de la siguiente (S3).
- Para retomar tras un fallo, cada agente exporta su estado a un sitio conocido
  y el coordinador carga un *manifest* al reanudar y lo inyecta en los prompts
  (K4, S4).
- `/compact` reduce el contexto de una sesión interactiva de Claude Code (S5).

POR QUÉ IMPORTA (inferencia propia): lo que no está en el contexto no se puede
usar, y lo que está pero muy lejos, tampoco se usa bien. Sacar el detalle a un
archivo y dejar en el contexto solo un resumen y un puntero mantiene el hilo
corto, y además es lo único que sobrevive a que el proceso se corte.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- `--anti todo_en_contexto`: las tres fases en un solo hilo, sin *scratchpad*,
  sin resumen y con el coordinador consultando las fuentes él mismo: los informes
  en bruto se acumulan en su contexto.
- Inferencia propia: con una investigación de este tamaño la degradación puede
  no aparecer; lo que se mide es cuánto contexto se acumula, no un fallo que se
  fuerce.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 06.

INTRODUCE: TS 5.4-K1, TS 5.4-K2, TS 5.4-K3, TS 5.4-K4, TS 5.4-S1, TS 5.4-S2, TS 5.4-S3, TS 5.4-S4, TS 5.4-S5

# USA: TS 3.4-K4, TS 3.4-S3
# `Explore` (el subagente de solo lectura de Claude Code para las fases de descubrimiento
# verbosas) y `/compact` son de Claude Code, no del Agent SDK: no se ejecutan aquí. Se
# explican en la sección D3 (`d3_claude_code/`); aquí solo se señala su papel. `Explore`
# hace con una sesión interactiva lo que `researcher` hace en este módulo: el detalle
# verboso queda fuera del hilo principal. `/compact` (TS 5.4-S5) resume la conversación
# de una sesión interactiva cuando se llena, y también se le pueden dar instrucciones sobre
# qué conservar; en este módulo el equivalente programático es el resumen de cada fase.

Uso: `uv run python app3_sistema_multiagente/06_contexto_largo.py [--anti todo_en_contexto] [--simular-caida] [--desde-cero] [--repeat N]`
"""

import asyncio
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, create_sdk_mcp_server, query, tool  # noqa: E402

from app3_sistema_multiagente.coordinator_gate import coordinator_attempts, coordinator_gate, coordinator_hooks  # noqa: E402, F401
from app3_sistema_multiagente.servers.investigacion import SERVER_NAME, build_server, ok, structured_error, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import MAIN, RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["todo_en_contexto"]
SCRATCHPAD_SERVER = "scratchpad"
QUERY_SOURCE = tool_name("query_source")
SAVE_FINDING = f"mcp__{SCRATCHPAD_SERVER}__save_finding"
READ_SCRATCHPAD = f"mcp__{SCRATCHPAD_SERVER}__read_scratchpad"
# Sitio conocido del estado: lo que escribe un proceso lo retoma otro. Es un directorio temporal, no del repositorio.
STATE_DIR = Path(tempfile.gettempdir()) / "ccarf-app3-06"
SCRATCHPAD_FILE = "scratchpad.jsonl"
MANIFEST_FILE = "manifest.json"
MAX_SUMMARY_CHARS = 1200  # el resumen de una fase es corto a propósito: es lo que se inyecta en la siguiente

LABELS = load("fuentes_investigacion_etiquetas.json")
LONG_SOURCE = LABELS["long_report"]["source_id"]

# Tres fases. La 2 trae el informe largo (~9.400 caracteres): es lo que más llena el contexto en un solo hilo.
# La 3 sintetiza lo descubierto y no consulta fuentes. Las peticiones no dicen las cifras que se esperan.
PHASES: list[dict[str, Any]] = [
    {
        "id": 1, "name": "descubrir", "sources": ["SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-PROVEEDOR"],
        "task": (
            "Fase 1 (descubrir): consulta las fuentes SRC-TICKETS, SRC-AUDITORIA, SRC-ENCUESTA y SRC-PROVEEDOR y anota, de cada una, "
            "qué dice sobre el tiempo de resolución y la satisfacción, con su fuente y su fecha."
        ),
    },
    {
        "id": 2, "name": "informe largo", "sources": [LONG_SOURCE],
        "task": f"Fase 2 (informe largo): consulta {LONG_SOURCE} (informe trimestral de incidencias de red) y anota su hallazgo clave.",
    },
    {
        "id": 3, "name": "informe", "sources": [],
        "task": (
            "Fase 3 (informe): redacta un informe breve con lo descubierto: el tiempo medio de resolución y la satisfacción, cada "
            "cifra con su fuente, y el hallazgo clave del informe largo. Las fuentes ya cubiertas no hace falta volver a consultarlas."
        ),
    },
]

# Lo que el informe final debería recoger de lo descubierto: cifras de las dos primeras magnitudes en conflicto y el hallazgo clave.
EXPECTED_FACTS: list[dict[str, str]] = [
    {"text": c["figure_text"].split()[0], "pattern": rf"(?<!\d)(?<!\d[.,/-]){re.escape(c['figure_text'].split()[0])}(?!\d)(?![.,-]\d)(?!/(?!5(?!\d)))"}
    for conflict in LABELS["conflicts"][:2] for c in conflict["claims"]
] + [{"text": LABELS["long_report"]["figure_text"], "pattern": r"(?<!\d)41\s?(%|por ciento)"}]
GENERIC_WORDS = re.compile(r"normalmente|por lo general|en general|suele(?:n)?|t[ií]pic[oa]s?|habitualmente|generalmente", re.I)


# --- Scratchpad: hallazgos clave en un archivo conocido (TS 5.4-K2, S2) ------------------------------


def read_scratchpad(directory: Path) -> list[dict[str, Any]]:
    path = directory / SCRATCHPAD_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_scratchpad_tools(directory: Path) -> list[Any]:
    """`save_finding` y `read_scratchpad` sobre un archivo del directorio de estado."""

    @tool(
        "save_finding",
        "Guarda un hallazgo clave en el scratchpad. Entrada: `source_id`, `claim` (el hallazgo, en una frase) y, si es una cifra, "
        "`figure`. Devuelve cuántos hallazgos hay guardados. No consulta fuentes: para eso, query_source.",
        {"type": "object", "properties": {"source_id": {"type": "string"}, "claim": {"type": "string"}, "figure": {"type": "number"}},
         "required": ["source_id", "claim"]},
    )
    async def save_finding(args: dict[str, Any]) -> dict[str, Any]:
        if not str(args.get("claim", "")).strip():
            return structured_error("hallazgo vacío: escribe el hallazgo en `claim`")
        entry = {"source_id": args["source_id"], "claim": args["claim"].strip()}
        if "figure" in args:
            entry["figure"] = args["figure"]
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / SCRATCHPAD_FILE).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return ok({"saved": len(read_scratchpad(directory))})

    @tool(
        "read_scratchpad",
        "Lee todos los hallazgos guardados en el scratchpad, en el orden en que se guardaron. No tiene entrada. "
        "Consúltalo antes de volver a consultar una fuente que ya cubriste. No guarda nada: para eso, save_finding.",
        {"type": "object", "properties": {}},
    )
    async def read_scratchpad_tool(args: dict[str, Any]) -> dict[str, Any]:
        return ok({"findings": read_scratchpad(directory)})

    return [save_finding, read_scratchpad_tool]


def build_scratchpad_server(directory: Path) -> Any:
    return create_sdk_mcp_server(SCRATCHPAD_SERVER, tools=make_scratchpad_tools(directory))


# --- Manifest: el estado para retomar (TS 5.4-K4, S4) ---------------------------------------------------


def new_manifest() -> dict[str, Any]:
    return {"version": 1, "total_phases": len(PHASES), "phases_done": [], "summaries": {}, "sources_covered": [], "findings": 0}


def complete_phase(manifest: dict[str, Any], phase_id: int, summary: str, covered: list[str], *, findings: int) -> dict[str, Any]:
    """Manifest con la fase terminada: su resumen, las fuentes cubiertas y los hallazgos guardados. No muta el original."""
    return {
        **manifest,
        "phases_done": [*manifest["phases_done"], phase_id],
        "summaries": {**manifest["summaries"], str(phase_id): summary},
        "sources_covered": sorted(set(manifest["sources_covered"]) | set(covered)),
        "findings": findings,
    }


def next_phase(manifest: dict[str, Any] | None) -> int | None:
    """Primera fase sin terminar (1 si no hay manifest), o None si ya están todas."""
    done = set((manifest or {}).get("phases_done", []))
    return next((p["id"] for p in PHASES if p["id"] not in done), None)


def is_complete(manifest: dict[str, Any]) -> bool:
    return next_phase(manifest) is None


def write_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / MANIFEST_FILE).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def read_manifest(directory: Path) -> dict[str, Any] | None:
    """Manifest del directorio, o None si no hay o está roto: un estado ilegible no se retoma a ciegas."""
    path = directory / MANIFEST_FILE
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return manifest if isinstance(manifest, dict) and "phases_done" in manifest else None


# --- Resumen entre fases y prompt de cada fase (TS 5.4-S3) -----------------------------------------------


def summarize(text: str | None) -> str:
    """Resumen de una fase: el cierre que escribió el coordinador, recortado para que la fase siguiente empiece con poco contexto."""
    text = (text or "").strip()
    return text if len(text) <= MAX_SUMMARY_CHARS else text[: MAX_SUMMARY_CHARS - 1].rstrip() + "…"


def phase_prompt(phase: dict[str, Any], manifest: dict[str, Any] | None) -> str:
    """Contexto inicial de una fase: su tarea y, si hay fases hechas, el estado del manifest y el resumen de cada una."""
    parts = [phase["task"]]
    if manifest and manifest["phases_done"]:
        covered = ", ".join(manifest["sources_covered"]) or "ninguna"
        parts.append(
            f"Retomas una investigación en curso. Estado del manifest: fases hechas {manifest['phases_done']} de {manifest['total_phases']}; "
            f"fuentes ya cubiertas: {covered}; {manifest['findings']} hallazgos en el scratchpad (léelos con read_scratchpad antes de "
            "volver a consultar una fuente)."
        )
        parts += [f"Resumen de la fase {pid}: {manifest['summaries'][str(pid)]}" for pid in manifest["phases_done"]]
    return "\n\n".join(parts)


def all_phases_prompt() -> str:
    """`todo_en_contexto`: las tres fases en una sola petición y un solo hilo, sin resumen ni estado."""
    return "Haz esta investigación en tres fases, una tras otra, y entrega al final el informe de la fase 3:\n\n" + "\n\n".join(
        p["task"] for p in PHASES
    )


# --- Agentes y opciones -------------------------------------------------------------------------------


def researcher_prompt() -> str:
    return (
        "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. Por cada hallazgo clave, "
        "guárdalo con save_finding (source_id, claim y, si es una cifra, figure). Devuelve al coordinador solo una línea por "
        "hallazgo, no el texto de las fuentes."
    )


def build_agents(subagent_model: str) -> dict[str, AgentDefinition]:
    return {
        "researcher": AgentDefinition(
            description="Consulta fuentes concretas, guarda los hallazgos clave en el scratchpad y devuelve un resumen corto.",
            prompt=researcher_prompt(),
            tools=[QUERY_SOURCE, SAVE_FINDING],
            model=subagent_model,
            background=False,  # en primer plano: el coordinador necesita el resultado (regla 4)
        )
    }


def coordinator_prompt(anti: str | None) -> str:
    """Objetivos y criterios, no pasos (1.3-S4)."""
    if anti == "todo_en_contexto":
        return (
            "Objetivo: llevar una investigación en tres fases en esta misma conversación y entregar el informe de la fase 3. "
            "Consulta tú las fuentes con query_source."
        )
    return (
        "Objetivo: llevar una investigación por fases. En cada fase recibes la tarea y, si retomas, el resumen de las anteriores y "
        "el estado de un manifest. Criterios: las consultas a las fuentes las hace el subagente researcher (pásale las fuentes "
        "concretas; tú no consultas); antes de volver a consultar una fuente, mira con read_scratchpad si ya está cubierta; y termina "
        "siempre con un resumen de tres líneas de lo descubierto en la fase (cifras con su fuente), que será el contexto de la siguiente."
    )


def build_options(anti: str | None, *, scratch_dir: Path, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    env = {
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",  # coste acotado: un subagente no lanza otros
        "CLAUDE_CODE_FORK_SUBAGENT": "0",  # sin fork: el subagente no hereda el contexto
        "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",  # primer plano (CLI 2.1.309, ver app3/01)
    }
    if anti == "todo_en_contexto":
        # Un solo hilo: el coordinador consulta las fuentes él mismo y todo se acumula en su contexto.
        return isolated_options(
            max_budget_usd=budget, model=model, system_prompt=coordinator_prompt(anti),
            mcp_servers={SERVER_NAME: build_server(sources=True)},
            tools=[], allowed_tools=[QUERY_SOURCE], permission_mode="dontAsk", env=env, max_turns=30,  # red de seguridad
        )
    return isolated_options(
        max_budget_usd=budget, model=model, system_prompt=coordinator_prompt(anti),
        mcp_servers={SERVER_NAME: build_server(sources=True), SCRATCHPAD_SERVER: build_scratchpad_server(scratch_dir)},
        tools=["Agent"],  # solo la tool integrada que lanza subagentes (la guía la llama "Task")
        # query_source y save_finding las usa el subagente; al coordinador se le deniega query_source y solo lee el scratchpad.
        allowed_tools=["Agent", QUERY_SOURCE, SAVE_FINDING, READ_SCRATCHPAD],
        permission_mode="dontAsk", agents=build_agents(subagent_model), hooks=coordinator_hooks(), env=env,
        max_turns=20,  # red de seguridad
    )


# --- Medidas sobre el RunRecord (sin modelo) -----------------------------------------------------------


def main_context_chars(rec: RunRecord) -> int:
    """Caracteres de resultados de tools que llegan al contexto del coordinador (lo del subagente no cuenta, solo su respuesta)."""
    return sum(len(c.result_text or "") for c in rec.tool_calls if c.agent == MAIN)


def requeried_sources(rec: RunRecord, covered: list[str]) -> list[str]:
    """Consultas a fuentes que ya estaban cubiertas: al retomar con el estado cargado no debería haber ninguna."""
    return [c.input.get("source_id") for c in rec.tool_calls if c.name == QUERY_SOURCE and c.input.get("source_id") in covered]


def queried_sources(rec: RunRecord) -> list[str]:
    return sorted({c.input.get("source_id") for c in rec.tool_calls if c.name == QUERY_SOURCE and c.input.get("source_id")})


def scratchpad_reads(rec: RunRecord) -> int:
    return sum(1 for c in rec.tool_calls if c.name == READ_SCRATCHPAD)


def facts_found(text: str | None) -> tuple[int, int, list[str]]:
    """(hechos descubiertos que recoge el texto, total, los que faltan): coherencia del informe con lo descubierto."""
    missing = [f["text"] for f in EXPECTED_FACTS if not re.search(f["pattern"], text or "")]
    return len(EXPECTED_FACTS) - len(missing), len(EXPECTED_FACTS), missing


def generic_phrases(text: str | None) -> list[str]:
    """Expresiones de «patrón típico» (K1): el texto habla de lo habitual en vez de lo que se descubrió."""
    return [m.group(0).lower() for m in GENERIC_WORDS.finditer(text or "")]


# --- Ejecución -------------------------------------------------------------------------------------------


def start_state(directory: Path, *, resume: bool) -> dict[str, Any]:
    """Retoma el manifest si hay una investigación a medias y se permite; si no, empieza con un directorio limpio."""
    existing = read_manifest(directory)
    if resume and existing and not is_complete(existing):
        print(f"[manifest] retomando: fases hechas {existing['phases_done']}, fuentes cubiertas {existing['sources_covered']}")
        return existing
    shutil.rmtree(directory, ignore_errors=True)
    manifest = new_manifest()
    write_manifest(directory, manifest)
    print(f"[manifest] investigación nueva en {directory}")
    return manifest


def print_result_measures(rec: RunRecord) -> None:
    found, total, missing = facts_found(rec.final_text)
    print(f"[medida] hechos descubiertos que recoge el informe final: {found}/{total} · faltan {missing or 'ninguno'}")
    print(f"[medida] expresiones de patrón típico en el informe final: {generic_phrases(rec.final_text) or 'ninguna'}")


async def run_phased(args: Any, model: str, subagent_model: str, budget: float) -> None:
    resume = args.repeat == 1 and not args.simular_caida and not args.desde_cero
    manifest = start_state(STATE_DIR, resume=resume)
    last: RunRecord | None = None
    total_chars = 0
    while (phase_id := next_phase(manifest)) is not None:
        phase = PHASES[phase_id - 1]
        options = build_options(None, scratch_dir=STATE_DIR, budget=budget, model=model, subagent_model=subagent_model)
        prompt = phase_prompt(phase, manifest)
        print(f"\n--- fase {phase_id} ({phase['name']}) · prompt inicial de {len(prompt)} caracteres ---")
        rec = await record(query(prompt=prompt, options=options))
        print(f"[respuesta completa]\n{rec.final_text}")
        chars = main_context_chars(rec)
        total_chars += chars
        print(f"[medida] fase {phase_id}: contexto del coordinador {chars} caracteres de resultados de tools · "
              f"consultas repetidas a fuentes ya cubiertas {requeried_sources(rec, manifest['sources_covered']) or 'ninguna'} · "
              f"lecturas del scratchpad {scratchpad_reads(rec)} · intentos denegados al coordinador {coordinator_attempts(rec)}")
        manifest = complete_phase(
            manifest, phase_id, summarize(rec.final_text), sorted(set(manifest["sources_covered"]) | set(queried_sources(rec))),
            findings=len(read_scratchpad(STATE_DIR)),
        )
        write_manifest(STATE_DIR, manifest)
        print(f"[manifest] escrito: fases hechas {manifest['phases_done']}, {manifest['findings']} hallazgos en el scratchpad")
        last = rec
        if args.simular_caida and phase_id == 1:
            print("\n[caída simulada] el proceso se corta tras la fase 1. Vuelve a ejecutar sin --simular-caida: retomará desde el manifest.")
            return
    print(f"\n[medida] contexto acumulado en las fases de esta ejecución: {total_chars} caracteres")
    if last is not None:
        print_result_measures(last)


async def run_single_thread(args: Any, model: str, subagent_model: str, budget: float) -> None:
    options = build_options("todo_en_contexto", scratch_dir=STATE_DIR, budget=budget, model=model, subagent_model=subagent_model)
    prompt = all_phases_prompt()
    print(f"\n--- una sola conversación con las tres fases · prompt de {len(prompt)} caracteres ---")
    rec = await record(query(prompt=prompt, options=options))
    print(f"[respuesta completa]\n{rec.final_text}")
    print(f"[medida] contexto del coordinador {main_context_chars(rec)} caracteres de resultados de tools · fuentes consultadas por él: {queried_sources(rec)}")
    print_result_measures(rec)


def expectation(anti: str | None, simular_caida: bool) -> str:
    if anti == "todo_en_contexto":
        return "un solo hilo: los informes en bruto se acumulan en el contexto del coordinador; la degradación puede no aparecer con este tamaño"
    if simular_caida:
        return "corta tras la fase 1 y deja el manifest y el scratchpad en un sitio conocido, para retomar en la siguiente ejecución"
    return "tres fases con contexto corto cada una: el resumen y el manifest se inyectan, el detalle queda en el scratchpad y no se repiten consultas"


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--simular-caida", action="store_true", help="corta tras la fase 1; la siguiente ejecución retoma desde el manifest")
    parser.add_argument("--desde-cero", action="store_true", help="ignora un manifest a medias y empieza de nuevo")
    args = parser.parse_args()
    if args.simular_caida and (args.anti or args.repeat > 1):
        parser.error("--simular-caida solo vale con la variante correcta y --repeat 1")
    print(credentials.describe())
    model = report_model("coordinator")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "multiagent")
    # El tope es de toda la ejecución del script, repartido entre repeticiones y entre las consultas de cada una.
    per_query = budget / (args.repeat * (1 if args.anti else len(PHASES)))

    for run in range(1, args.repeat + 1):
        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta'}{' · caída simulada' if args.simular_caida else ''} ===")
        print(f"[esperado] {expectation(args.anti, args.simular_caida)}")
        if args.anti:
            await run_single_thread(args, model, subagent_model, per_query)
        else:
            await run_phased(args, model, subagent_model, per_query)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
