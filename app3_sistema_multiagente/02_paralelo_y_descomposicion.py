"""Subagentes en paralelo, refinamiento por brechas y estrategias de descomposición.

CONCEPTO [TS 1.2-S3 · TS 1.3-S3 · TS 1.6-K1, K3, S1, S3]: paralelismo en una
misma respuesta, bucle de refinamiento del coordinador y elección entre
cadena fija y descomposición adaptativa.

QUÉ DICE LA GUÍA:
- Los subagentes en paralelo se lanzan emitiendo varias llamadas a Task en
  una sola respuesta del coordinador, no repartidas en turnos (1.3-S3).
- Bucle de refinamiento: el coordinador evalúa la síntesis, detecta brechas,
  vuelve a delegar con consultas dirigidas y sintetiza otra vez hasta que la
  cobertura basta (1.2-S3).
- Una cadena secuencial fija (*prompt chaining*) conviene cuando el trabajo es
  predecible; la descomposición dinámica, cuando depende de lo que se va
  descubriendo (1.6-K1). Se elige el patrón según el flujo: cadena para
  revisiones previsibles con varios aspectos, descomposición dinámica para
  investigaciones abiertas (1.6-S1).
- Un plan de investigación adaptativo genera subtareas a partir de lo que
  encuentra en cada paso (1.6-K3). Para una tarea abierta como «añadir tests
  completos a un código *legacy*»: primero se mapea la estructura, después se
  identifican las zonas de mayor impacto y se hace un plan priorizado que se
  adapta cuando aparecen dependencias (1.6-S3).

POR QUÉ IMPORTA: tres subagentes independientes en tres turnos cuestan tres
esperas; en una respuesta, una. Y un plan fijo para una tarea abierta se
rompe en cuanto el código esconde algo que el plan no previó.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: lanzar los subagentes de uno en uno cuando
no dependen entre sí; usar una cadena fija para una investigación abierta (o
lo contrario); y empezar a escribir tests de un código *legacy* archivo por
archivo, sin mapearlo antes.

Inferencia propia: el comprobador de brechas es determinista (subtemas
esperados en el texto), para que el bucle se pueda probar sin modelo. Y «No
buscas tú» en el prompt del coordinador es una petición: lo que se lo impide
es el hook `PreToolUse` compartido (`coordinator_gate.py`, explicado en
`03_tools_entre_roles`). La cadena fija y `legacy` no tienen coordinador.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 02.

INTRODUCE: TS 1.2-S3, TS 1.3-S3, TS 1.6-K1, TS 1.6-K3, TS 1.6-S1, TS 1.6-S3
USA: TS 1.2-K2, TS 1.3-K1, TS 1.3-S1

Uso: `uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte paralelo|refinamiento|descomposicion|legacy [--anti secuencial]`
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, query  # noqa: E402

from app3_sistema_multiagente.coordinator_gate import coordinator_attempts, coordinator_hooks  # noqa: E402
from app3_sistema_multiagente.servers.investigacion import (  # noqa: E402
    NETWORK_SUBTOPICS,
    SERVER_NAME,
    build_server,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import DATA_DIR, load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import SUBAGENT_TOOLS, RunRecord, record  # noqa: E402

PARTS = ["paralelo", "refinamiento", "descomposicion", "legacy"]
SEARCH_TICKETS = tool_name("search_tickets")
SEARCH_KB = tool_name("search_kb")
LEGACY_DIR = DATA_DIR / "legacy_inventario"
# Subtemas que una síntesis de «problemas de red» debe cubrir según los datos.
REQUIRED_SUBTOPICS = NETWORK_SUBTOPICS
MAX_REFINEMENT_ROUNDS = 2
# Señales que solo da quien leyó `depreciacion.valor_actual`: el import dentro
# de la función y el valor residual del 10 % de los equipos asignados. Los
# imports de cabecera de otros módulos no cuentan.
HIDDEN_DEPENDENCY_SIGNS = ["import tardío", "dentro de valor_actual", "dentro de la función", "valor residual", "10 %", "10%"]

# Neutralizar valores por defecto (roadmap §3, regla 4): sin subagentes en
# segundo plano ni fork, y sin que un subagente lance otros.
SUBAGENT_ENV = {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
    "CLAUDE_CODE_FORK_SUBAGENT": "0",
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
}


def build_agents(subagent_model: str) -> dict[str, AgentDefinition]:
    """Dos analistas por tipo de fuente; el contexto les llega solo por el prompt."""
    return {
        "tickets_analyst": AgentDefinition(
            description="Busca en los tickets de la mesa de ayuda sobre el tema que se le indique.",
            prompt="Eres el analista de tickets. Busca con search_tickets y devuelve los hallazgos con ticket_id y fecha.",
            tools=[SEARCH_TICKETS], model=subagent_model,
            # En primer plano: con la ejecución en segundo plano el coordinador
            # no espera y la latencia medida no sería la del trabajo (regla 4).
            background=False,
        ),
        "kb_analyst": AgentDefinition(
            description="Busca en la base de conocimiento sobre el tema que se le indique.",
            prompt="Eres el analista de la KB. Busca con search_kb y devuelve los artículos con article_id y fecha.",
            tools=[SEARCH_KB], model=subagent_model, background=False,
        ),
    }


def coordinator_options(system_prompt: str, *, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=system_prompt,
        mcp_servers={SERVER_NAME: build_server()},
        tools=["Agent"],  # la tool que lanza subagentes (en la guía, "Task")
        allowed_tools=["Agent", SEARCH_TICKETS, SEARCH_KB],
        permission_mode="dontAsk",
        agents=build_agents(subagent_model),
        # `tools=["Agent"]` no oculta las tools MCP al coordinador: la barrera es este hook, no el prompt.
        hooks=coordinator_hooks(),
        env=SUBAGENT_ENV,
        max_turns=20,  # red de seguridad
    )


# --- Parte paralelo (1.3-S3) -------------------------------------------------

PARALLEL_TASK = (
    "Necesito tres datos independientes: (a) qué tickets hay de licencias, (b) qué tickets hay de hardware y "
    "(c) qué artículos de la base de conocimiento hay sobre acceso. Delega cada uno en un subagente y "
    "resume el resultado en tres líneas."
)


def coordinator_prompt(mode: str) -> str:
    base = "Eres el coordinador. No buscas tú: delegas en los subagentes y les das en el prompt todo lo que necesitan. "
    if mode == "secuencial":
        # Anti de 1.3-S3: una delegación por turno aunque no dependan entre sí.
        return base + "Lanza un subagente cada vez y espera su resultado antes de lanzar el siguiente."
    return base + "Cuando las subtareas son independientes, lanza todos los subagentes en la misma respuesta."


def agent_groups(rec: RunRecord) -> dict[str, list[str]]:
    """Llamadas a subagentes del coordinador, agrupadas por la respuesta en que llegaron."""
    groups: dict[str, list[str]] = {}
    for call in rec.tool_calls:
        if call.name in SUBAGENT_TOOLS:
            groups.setdefault(call.response, []).append(call.input.get("subagent_type", "?"))
    return groups


def max_parallel(rec: RunRecord) -> int:
    return max((len(v) for v in agent_groups(rec).values()), default=0)


def speedup(*, parallel_s: float, sequential_s: float) -> float | None:
    return sequential_s / parallel_s if parallel_s > 0 else None


async def timed_run(prompt: str, options: ClaudeAgentOptions) -> tuple[RunRecord, float]:
    start = time.monotonic()
    rec = await record(query(prompt=prompt, options=options))
    return rec, time.monotonic() - start


async def part_parallel(args: Any, budget: float, model: str, subagent_model: str) -> None:
    modes = ["secuencial"] if args.anti else ["paralelo", "secuencial"]
    elapsed: dict[str, float] = {}
    for mode in modes:
        print(f"\n=== paralelo · modo {mode} ===")
        options = coordinator_options(coordinator_prompt(mode), budget=budget / len(modes), model=model,
                                      subagent_model=subagent_model)
        rec, seconds = await timed_run(PARALLEL_TASK, options)
        elapsed[mode] = seconds
        print(f"[medida] subagentes por respuesta: {agent_groups(rec)} · máximo en una respuesta: {max_parallel(rec)}")
        print(f"[medida] latencia: {seconds:.1f} s · intentos del coordinador, denegados: {coordinator_attempts(rec)}")
    if len(elapsed) == 2:
        ratio = speedup(parallel_s=elapsed["paralelo"], sequential_s=elapsed["secuencial"])
        print(f"\n[resumen] paralelo {elapsed['paralelo']:.1f} s · secuencial {elapsed['secuencial']:.1f} s · "
              f"aceleración ×{ratio:.2f}" if ratio else "")


# --- Parte refinamiento (1.2-S3) ---------------------------------------------


def gaps(text: str | None) -> list[str]:
    """Subtemas esperados que la síntesis no menciona."""
    lowered = (text or "").lower()
    return [topic for topic, words in REQUIRED_SUBTOPICS.items() if not any(w in lowered for w in words)]


def refinement_message(missing: list[str]) -> str:
    return (
        f"Tu síntesis no cubre estos subtemas: {', '.join(missing)}. Vuelve a delegar con consultas dirigidas "
        "solo a ellos y entrega la síntesis completa, con lo anterior más lo nuevo."
    )


async def part_refinement(args: Any, budget: float, model: str, subagent_model: str) -> None:
    prompt = (
        "Eres el coordinador. Haz una primera pasada rápida: una sola consulta por analista. Después sintetiza, "
        "citando cada problema con su ticket_id."
    )
    options = coordinator_options(prompt, budget=budget, model=model, subagent_model=subagent_model)
    question = "¿Qué problemas de red tienen los empleados?"
    async with ClaudeSDKClient(options=options) as client:
        message = question
        for round_number in range(1, MAX_REFINEMENT_ROUNDS + 2):
            print(f"\n=== refinamiento · ronda {round_number} ===\n[prompt] {message}")
            await client.query(message)
            rec = await record(client.receive_response())
            missing = gaps(rec.final_text)
            print(f"[medida] brechas: {missing or 'ninguna'} · intentos del coordinador, denegados: {coordinator_attempts(rec)}")
            if not missing or round_number > MAX_REFINEMENT_ROUNDS:
                break
            # El coordinador recibe solo las brechas: re-delegación dirigida.
            message = refinement_message(missing)
    print(f"[respuesta completa]\n{rec.final_text}")


# --- Parte descomposición (1.6-K1, 1.6-S1, 1.6-K3) ----------------------------

CHAIN_STEPS = [
    "Paso 1 de 3. Para cada ticket de gastos de esta lista, extrae en una línea: ticket_id, importe y estado.\n{data}",
    "Paso 2 de 3. Aplica la política (hasta 500 EUR lo aprueba soporte; por encima, Finanzas) a cada línea.",
    "Paso 3 de 3. Redacta un informe de cinco líneas para Finanzas con lo que les toca aprobar.",
]


def chain_prompts(steps: list[str], outputs: list[str]) -> list[str]:
    """Cada paso de la cadena recibe solo la salida del anterior."""
    return [steps[0]] + [f"{step}\n\nEntrada (salida del paso anterior):\n{out}" for step, out in zip(steps[1:], outputs)]


async def part_decomposition(args: Any, budget: float, model: str, subagent_model: str) -> None:
    # Cadena fija: una revisión previsible con aspectos conocidos de antemano.
    expenses = "\n".join(
        f"- {t['ticket_id']}: {t['description']} (estado {t['status']})"
        for t in load("tickets.json") if t["category"] == "gastos" and t["amount_eur"] is not None
    )
    steps = [CHAIN_STEPS[0].format(data=expenses), *CHAIN_STEPS[1:]]
    outputs: list[str] = []
    print("\n=== descomposición · cadena fija (prompt chaining) ===")
    for number in range(len(steps)):
        prompt = chain_prompts(steps, outputs)[number]
        # max_turns=1: red de seguridad; sin tools, cada paso es una sola respuesta.
        options = isolated_options(max_budget_usd=budget / 6, model=subagent_model, tools=[], max_turns=1,
                                   system_prompt="Responde en español, solo con lo que pide el paso.")
        rec = await record(query(prompt=prompt, options=options), echo=False)
        outputs.append(rec.final_text or "")
        print(f"[paso {number + 1}] {(rec.final_text or '').strip()[:300]}")

    # Descomposición adaptativa: una investigación abierta.
    print("\n=== descomposición · adaptativa ===")
    prompt = (
        "Eres el coordinador de una investigación abierta. No buscas tú: delegas en los analistas y les das en el "
        "prompt lo que necesitan. No hay un plan fijo: empieza con una exploración amplia "
        "y, según lo que encuentres en cada paso, genera nuevas subtareas para los analistas. Al final, explica qué "
        "subtareas surgieron de qué hallazgo."
    )
    options = coordinator_options(prompt, budget=budget / 2, model=model, subagent_model=subagent_model)
    rec = await record(query(prompt="En septiembre llegaron muchos tickets. ¿Qué está pasando y qué habría que hacer?",
                             options=options))
    for response, agents in agent_groups(rec).items():
        prompts = [c.input.get("prompt", "")[:120] for c in rec.tool_calls if c.response == response and c.name in SUBAGENT_TOOLS]
        print(f"[subtareas {response}] {agents}: {prompts}")
    print(f"[medida] rondas de delegación: {len(agent_groups(rec))} · intentos del coordinador, denegados: "
          f"{coordinator_attempts(rec)}\n[respuesta completa]\n{rec.final_text}")


# --- Parte legacy (1.6-S3) -----------------------------------------------------


def mentions_hidden_dependency(text: str | None) -> bool:
    lowered = (text or "").lower()
    return any(sign in lowered for sign in HIDDEN_DEPENDENCY_SIGNS)


async def part_legacy(args: Any, budget: float, model: str, subagent_model: str) -> None:
    options = isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=(
            "Eres un ingeniero que planifica tests para código heredado. Solo puedes leer: no escribas archivos. "
            "Primero mapea la estructura del paquete (Glob y Grep), después lee los módulos de mayor impacto, y "
            "entrega un plan de tests priorizado. Si al leer descubres una dependencia que cambia el plan, dilo y "
            "ajusta el orden."
        ),
        # Solo tools de lectura, en el directorio del paquete.
        tools=["Glob", "Grep", "Read"],
        allowed_tools=["Glob", "Grep", "Read"],
        permission_mode="dontAsk",
        cwd=str(LEGACY_DIR),
        max_turns=25,  # red de seguridad
    )
    print(f"\n=== legacy · {LEGACY_DIR.name} ===")
    rec = await record(query(prompt="Añade tests completos a este paquete legacy. Empieza por el plan.", options=options))
    reads = [c.input.get("file_path", "") for c in rec.tool_calls if c.name == "Read"]
    print(f"[medida] orden: {[c.name for c in rec.tool_calls]}")
    print(f"[medida] archivos leídos: {[Path(r).name for r in reads]}")
    print(f"[medida] el plan menciona la dependencia escondida: {mentions_hidden_dependency(rec.final_text)}")
    print(f"[respuesta completa]\n{rec.final_text}")


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=["secuencial"])
    parser.add_argument("--parte", choices=PARTS, required=True)
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("coordinator")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "multiagent")
    handler = {"paralelo": part_parallel, "refinamiento": part_refinement,
               "descomposicion": part_decomposition, "legacy": part_legacy}[args.parte]
    await handler(args, budget, model, subagent_model)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
