"""Contexto largo: scratchpad, resumen entre fases y manifest para retomar tras una caída.

CONCEPTO [TS 5.4-K1…K4, S1…S5]: cómo se sostiene una investigación en varias fases
sin que el contexto de un solo hilo se llene y se degrade, y cómo se retoma si el
proceso se corta.

QUÉ DICE LA GUÍA:
- Una sesión muy larga se degrada: las respuestas dejan de ser coherentes y el modelo
  recurre a «patrones típicos» en lugar de lo concreto que había descubierto (5.4-K1).
- Un *scratchpad* guarda los hallazgos clave fuera del contexto, así que sobreviven a
  sus límites (5.4-K2). El agente va anotando en él y lo vuelve a leer cuando le
  llega la pregunta siguiente (5.4-S2).
- La exploración verbosa se delega en subagentes, que la mantienen fuera del hilo
  principal mientras este conserva la visión de conjunto (5.4-K3). A cada subagente
  se le da una pregunta concreta (5.4-S1).
- Al cerrar una fase se resume lo encontrado, y la fase siguiente arranca con ese
  resumen en su contexto (5.4-S3).
- Para poder retomar tras una caída, cada agente deja su estado en un lugar
  acordado; al reanudar, el coordinador lee el *manifest* (5.4-K4) y pasa su
  contenido a los prompts de los agentes (5.4-S4).
- En una exploración larga, `/compact` libera contexto cuando se ha llenado de
  salida de descubrimiento (5.4-S5).

POR QUÉ IMPORTA (inferencia propia): lo que no está en el contexto no se puede usar,
y lo que está pero enterrado entre informes en bruto se usa peor. Sacar el detalle a
un archivo y dejar en el contexto solo un resumen mantiene el hilo corto, y además
es lo único que sobrevive a que el proceso se corte.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Hacer todas las fases en un solo hilo, sin *scratchpad* ni resumen, con el
    coordinador consultando las fuentes él mismo, así que los informes en bruto se
    acumulan en su contexto (`--anti todo_en_contexto`).
  - Retomar tras una caída sin estado exportado: se repite el trabajo hecho o se
    pierde (`--simular-caida` muestra la versión correcta).
- Inferencias propias, con lo observado aquí (cifras en el README y en
  `docs/hallazgos.md`):
  - La guía habla de explorar un código grande. Aquí se explora un conjunto de
    fuentes en tres fases, con los mismos mecanismos.
  - La degradación (5.4-K1) no se reprodujo: el hilo único juntó 11.134 caracteres
    (4.106 la fase más larga de la versión correcta) y aun así mantuvo los hechos
    (medición anterior a las correcciones B4, con el informe largo de entonces).
    Lo que se mide es cuánto contexto se acumula y si al retomar se repite trabajo,
    no un fallo que se fuerce.
  - `/compact` (5.4-S5) es de Claude Code y aquí no se ejecuta: el módulo lo explica,
    y su equivalente en código es el resumen de cada fase.
  - Un *manifest* solo sirve si se comprueba al cargarlo. Uno roto, de otra versión
    o que no cuadra con el *scratchpad* llevaría a la fase siguiente a leer hallazgos
    que no existen; el módulo lo rechaza y empieza de cero.
  - Las fases cuestan más que el hilo único (unas 2,5 veces en esa medición): el
    ahorro de contexto se paga en llamadas. Compensa cuando el hilo se acercaría a
    su límite o cuando hay que poder retomar.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 06.

INTRODUCE: TS 5.4-K1, TS 5.4-K2, TS 5.4-K3, TS 5.4-K4, TS 5.4-S1, TS 5.4-S2, TS 5.4-S3, TS 5.4-S4, TS 5.4-S5

USA: TS 3.4-K4, TS 3.4-S3
`Explore` (el subagente de solo lectura de Claude Code para las fases de descubrimiento
verbosas) y `/compact` son de Claude Code, no del Agent SDK: no se ejecutan aquí. Se
explican en la sección D3 (`d3_claude_code/`); aquí solo se señala su papel. `Explore`
hace en una sesión interactiva lo que `researcher` hace en este módulo: el detalle
verboso queda fuera del hilo principal. `/compact` (TS 5.4-S5) resume la conversación
de una sesión interactiva cuando se llena; en este módulo el equivalente en código es
el resumen de cada fase.

Uso: `uv run python app3_sistema_multiagente/06_contexto_largo.py [--anti todo_en_contexto] [--simular-caida] [--desde-cero] [--repeat N]`
"""

import asyncio
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
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
from harness.estado import state_dir  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import MAIN, RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["todo_en_contexto"]
SCRATCHPAD_SERVER = "scratchpad"
QUERY_SOURCE = tool_name("query_source")
SAVE_FINDING = f"mcp__{SCRATCHPAD_SERVER}__save_finding"
READ_SCRATCHPAD = f"mcp__{SCRATCHPAD_SERVER}__read_scratchpad"
# Sitio conocido del estado: lo que escribe un proceso lo retoma otro. Va bajo `estado/<perfil>/`, como el resto del
# estado personal (fuera de git y propio de cada persona), no en un directorio temporal compartido del sistema.
STATE_SUBDIR = "app3-06"
MANIFEST_VERSION = 1
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


def state_directory(profile: str | None = None, **kwargs: Any) -> Path:
    """Directorio de estado de este módulo: `estado/<perfil>/app3-06` (el perfil sale de `CCARF_PERFIL`). No crea nada."""
    return state_dir(profile, **kwargs)[0] / STATE_SUBDIR


def warn(message: str) -> None:
    print(f"[aviso] {message}")


class ScratchpadError(ValueError):
    """El scratchpad está corrupto en medio (no es solo una última línea cortada por una caída)."""


def read_scratchpad(directory: Path) -> list[dict[str, Any]]:
    """Hallazgos del scratchpad. Una última línea incompleta (caída a mitad de escritura) se ignora con un aviso;
    una línea ilegible en medio es corrupción de verdad y falla con la línea."""
    path = directory / SCRATCHPAD_FILE
    if not path.exists():
        return []
    lines = [(number, line) for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if line.strip()]
    entries: list[dict[str, Any]] = []
    for position, (number, line) in enumerate(lines):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as error:
            if position == len(lines) - 1:
                warn(f"el scratchpad termina con una línea incompleta (línea {number}): se ignora")
                break
            raise ScratchpadError(f"scratchpad corrupto en la línea {number} de {path}: {error.msg}") from error
    return entries


def repair_tail(directory: Path) -> None:
    """Antes de añadir una línea: deja el archivo terminado en salto de línea. Una última línea cortada se descarta."""
    path = directory / SCRATCHPAD_FILE
    if not path.exists() or path.stat().st_size == 0:
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.endswith("\n"):
        return
    head, _, tail = text.rpartition("\n")
    try:
        json.loads(tail)
        path.write_text(text + "\n", encoding="utf-8")  # estaba completa y solo le faltaba el salto de línea
    except json.JSONDecodeError:
        warn("el scratchpad terminaba con una línea incompleta: se descarta antes de guardar")
        path.write_text(head + "\n" if head else "", encoding="utf-8")


def scratchpad_digest(directory: Path, count: int) -> str:
    """Huella de los primeros `count` hallazgos: distingue un scratchpad ajeno aunque tenga el mismo número."""
    return hashlib.sha256(json.dumps(read_scratchpad(directory)[:count], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def scratchpad_problem(directory: Path, manifest: dict[str, Any]) -> str | None:
    """Por qué el scratchpad no cuadra con el manifest (None si cuadra). Un scratchpad con hallazgos de más no es incoherente."""
    try:
        entries = read_scratchpad(directory)
    except ScratchpadError as error:
        return str(error)
    if len(entries) < manifest["findings"]:
        return f"el manifest dice {manifest['findings']} hallazgos y el scratchpad tiene {len(entries)}"
    digest = manifest.get("scratchpad_digest")
    if digest and scratchpad_digest(directory, manifest["findings"]) != digest:
        return "los hallazgos del scratchpad no son los que dice el manifest"
    return None


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
        # Validación de entrada como error estructurado (formato de app1/04), no como excepción dentro del handler.
        claim, source_id = args.get("claim"), args.get("source_id")
        if not isinstance(claim, str) or not claim.strip():
            return structured_error("hallazgo vacío o que no es texto: escribe el hallazgo en `claim`")
        if not isinstance(source_id, str) or not source_id.strip():
            return structured_error("falta `source_id`: indica la fuente del hallazgo (texto)")
        if "figure" in args and (isinstance(args["figure"], bool) or not isinstance(args["figure"], int | float)):
            return structured_error("`figure` debe ser un número")
        entry = {"source_id": source_id, "claim": claim.strip()}
        if "figure" in args:
            entry["figure"] = args["figure"]
        directory.mkdir(parents=True, exist_ok=True)
        repair_tail(directory)  # una caída anterior pudo dejar la última línea cortada: no se pega la nueva a ella
        with (directory / SCRATCHPAD_FILE).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        try:
            return ok({"saved": len(read_scratchpad(directory))})
        except ScratchpadError as error:
            return structured_error(f"scratchpad corrupto: {error}")

    @tool(
        "read_scratchpad",
        "Lee todos los hallazgos guardados en el scratchpad, en el orden en que se guardaron. No tiene entrada. "
        "Consúltalo antes de volver a consultar una fuente que ya cubriste. No guarda nada: para eso, save_finding.",
        {"type": "object", "properties": {}},
    )
    async def read_scratchpad_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            return ok({"findings": read_scratchpad(directory)})
        except ScratchpadError as error:
            return structured_error(f"scratchpad corrupto: {error}")

    return [save_finding, read_scratchpad_tool]


def build_scratchpad_server(directory: Path) -> Any:
    return create_sdk_mcp_server(SCRATCHPAD_SERVER, tools=make_scratchpad_tools(directory))


# --- Manifest: el estado para retomar (TS 5.4-K4, S4) ---------------------------------------------------


def new_manifest() -> dict[str, Any]:
    return {"version": MANIFEST_VERSION, "total_phases": len(PHASES), "phases_done": [], "summaries": {}, "sources_covered": [], "findings": 0}


def complete_phase(
    manifest: dict[str, Any], phase_id: int, summary: str, covered: list[str], *, findings: int, digest: str | None = None,
) -> dict[str, Any]:
    """Manifest con la fase terminada: su resumen, las fuentes cubiertas y los hallazgos guardados (con su huella, si se da).

    No muta el original.
    """
    done = {
        **manifest,
        "phases_done": [*manifest["phases_done"], phase_id],
        "summaries": {**manifest["summaries"], str(phase_id): summary},
        "sources_covered": sorted(set(manifest["sources_covered"]) | set(covered)),
        "findings": findings,
    }
    if digest is not None:
        done["scratchpad_digest"] = digest
    return done


def next_phase(manifest: dict[str, Any] | None) -> int | None:
    """Primera fase sin terminar (1 si no hay manifest), o None si ya están todas."""
    done = set((manifest or {}).get("phases_done", []))
    return next((p["id"] for p in PHASES if p["id"] not in done), None)


def is_complete(manifest: dict[str, Any]) -> bool:
    return next_phase(manifest) is None


def write_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / MANIFEST_FILE).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def manifest_problem(manifest: Any) -> str | None:
    """Por qué un manifest no se puede retomar (None si es válido): claves, versión, tipos y coherencia con las fases."""
    if not isinstance(manifest, dict):
        return "no es un objeto JSON"
    missing = [key for key in ("version", "total_phases", "phases_done", "summaries", "sources_covered", "findings") if key not in manifest]
    if missing:
        return f"faltan claves: {', '.join(missing)}"
    if not is_int(manifest["version"]) or manifest["version"] != MANIFEST_VERSION:  # `True == 1`: un booleano no es una versión
        return f"versión {manifest['version']!r} (este módulo lee la versión {MANIFEST_VERSION})"
    if manifest["total_phases"] != len(PHASES):
        return f"total_phases es {manifest['total_phases']!r} y el módulo tiene {len(PHASES)} fases"
    done = manifest["phases_done"]
    if not isinstance(done, list) or not all(is_int(p) for p in done) or len(set(done)) != len(done) or not set(done) <= {p["id"] for p in PHASES}:
        return "phases_done no es una lista de fases válidas sin repetir"
    summaries = manifest["summaries"]
    if not isinstance(summaries, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in summaries.items()):
        return "summaries no es un diccionario de textos"
    if any(str(phase) not in summaries for phase in done):
        return "falta el resumen de una fase hecha"
    covered = manifest["sources_covered"]
    if not isinstance(covered, list) or not all(isinstance(c, str) for c in covered):
        return "sources_covered no es una lista de textos"
    if not is_int(manifest["findings"]) or manifest["findings"] < 0:
        return "findings no es un entero no negativo"
    return None


def read_manifest(directory: Path) -> dict[str, Any] | None:
    """Manifest del directorio, o None si no hay o no es de fiar (ilegible, de otra versión o con claves o tipos mal).

    Un estado dudoso no se retoma a ciegas: se avisa y se devuelve None.
    """
    path = directory / MANIFEST_FILE
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:  # JSONDecodeError y UnicodeDecodeError son ValueError
        warn(f"manifest ilegible en {path}: {type(error).__name__}")
        return None
    problem = manifest_problem(manifest)
    if problem:
        warn(f"manifest descartado en {path}: {problem}")
        return None
    return manifest


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


def back_up_state(directory: Path) -> Path:
    """Mueve el estado a `<directorio>.<fecha-hora>.bak` (con contador si ya existe uno de ese segundo) y devuelve la nueva ruta."""
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup = directory.with_name(f"{directory.name}.{stamp}.bak")
    counter = 1
    while backup.exists():
        counter += 1
        backup = directory.with_name(f"{directory.name}.{stamp}-{counter}.bak")
    directory.rename(backup)
    return backup


def start_state(directory: Path, *, resume: bool) -> dict[str, Any]:
    """Retoma el manifest si hay una investigación a medias y se permite; si no, empieza con un directorio limpio."""
    existing = read_manifest(directory)
    discarded = existing is None and (directory / MANIFEST_FILE).exists()  # ilegible, de otra versión o con claves o tipos mal
    if resume and existing and not is_complete(existing):
        problem = scratchpad_problem(directory, existing)
        if problem is None:
            print(f"[manifest] retomando: fases hechas {existing['phases_done']}, fuentes cubiertas {existing['sources_covered']}")
            return existing
        warn(f"el manifest no cuadra con el scratchpad ({problem}): se empieza desde cero")
        discarded = True
    if discarded and directory.exists():
        # Un estado dudoso puede ser trabajo de otra versión del módulo: se aparta, no se borra.
        warn(f"el estado anterior se guarda en {back_up_state(directory)}")
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
    state = state_directory()
    manifest = start_state(state, resume=resume)
    last: RunRecord | None = None
    total_chars = 0
    while (phase_id := next_phase(manifest)) is not None:
        phase = PHASES[phase_id - 1]
        options = build_options(None, scratch_dir=state, budget=budget, model=model, subagent_model=subagent_model)
        prompt = phase_prompt(phase, manifest)
        print(f"\n--- fase {phase_id} ({phase['name']}) · prompt inicial de {len(prompt)} caracteres ---")
        rec = await record(query(prompt=prompt, options=options))
        print(f"[respuesta completa]\n{rec.final_text}")
        chars = main_context_chars(rec)
        total_chars += chars
        print(f"[medida] fase {phase_id}: contexto del coordinador {chars} caracteres de resultados de tools · "
              f"consultas repetidas a fuentes ya cubiertas {requeried_sources(rec, manifest['sources_covered']) or 'ninguna'} · "
              f"lecturas del scratchpad {scratchpad_reads(rec)} · intentos denegados al coordinador {coordinator_attempts(rec)}")
        try:
            findings = len(read_scratchpad(state))
        except ScratchpadError as error:
            print(f"[error] {error}\n[error] no se guarda el manifest de la fase {phase_id}: arregla o borra el scratchpad y vuelve a ejecutar")
            return
        manifest = complete_phase(
            manifest, phase_id, summarize(rec.final_text), sorted(set(manifest["sources_covered"]) | set(queried_sources(rec))),
            findings=findings, digest=scratchpad_digest(state, findings),
        )
        write_manifest(state, manifest)
        print(f"[manifest] escrito: fases hechas {manifest['phases_done']}, {manifest['findings']} hallazgos en el scratchpad")
        last = rec
        if args.simular_caida and phase_id == 1:
            print("\n[caída simulada] el proceso se corta tras la fase 1. Vuelve a ejecutar sin --simular-caida: retomará desde el manifest.")
            return
    print(f"\n[medida] contexto acumulado en las fases de esta ejecución: {total_chars} caracteres")
    if last is not None:
        print_result_measures(last)


async def run_single_thread(args: Any, model: str, subagent_model: str, budget: float) -> None:
    options = build_options("todo_en_contexto", scratch_dir=state_directory(), budget=budget, model=model, subagent_model=subagent_model)
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
