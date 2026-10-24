"""Sesiones: reanudar, bifurcar o empezar de nuevo con un resumen.

CONCEPTO [TS 1.7-K1, K2, K3, K4, S1, S2, S3, S4 · TS 1.3-K4]: estado de
sesión, reanudación y bifurcación.

QUÉ DICE LA GUÍA:
- Una sesión con nombre se reanuda con `--resume <nombre>` para seguir una
  conversación concreta, también entre jornadas de trabajo (1.7-K1, 1.7-S1).
- `fork_session` crea ramas independientes desde una base de análisis común
  para explorar enfoques distintos, como dos estrategias de tests o de
  refactorización (1.7-K2, 1.7-S2; la gestión de sesiones por bifurcación,
  1.3-K4).
- Al reanudar después de cambios, hay que decirle al agente qué cambió en lo
  que ya analizó (1.7-K3), y decírselo en concreto, para que reanalice solo eso
  en vez de explorar todo otra vez (1.7-S4).
- Empezar una sesión nueva con un resumen estructurado es más fiable que
  reanudar con resultados de tools obsoletos (1.7-K4). Se reanuda cuando el
  contexto previo sigue valiendo en su mayor parte y se empieza de nuevo
  cuando los resultados previos están obsoletos (1.7-S3).

POR QUÉ IMPORTA: una sesión reanudada no sabe que el mundo cambió. Sus
resultados de tools son una foto del pasado, y el modelo los trata como el
presente salvo que alguien le diga lo contrario.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: reanudar sin aviso tras cambios y fiarse de
la respuesta; o, al revés, pedir «vuelve a revisarlo todo» cuando solo
cambiaron dos cosas. Y confundir `fork_session` (dos ramas independientes desde
una base común) con reanudar la misma sesión dos veces.

Equivalencia CLI ↔ SDK: la guía habla de `--resume <nombre>` de la CLI. El SDK
reanuda por ID (`resume=session_id`) y bifurca con `fork_session=True`; el
módulo imprime el comando de la CLI equivalente. La práctica con nombre se hace
con las sesiones de construcción (`claude -n app2`, `claude --resume app2`),
como guía el README.

EN PRODUCCIÓN (no evaluable): el SDK tiene además `rename_session` para poner
nombre a una sesión desde código; la guía no lo nombra.

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 06.

INTRODUCE: TS 1.7-K1, TS 1.7-K2, TS 1.7-K3, TS 1.7-K4, TS 1.7-S1, TS 1.7-S2, TS 1.7-S3, TS 1.7-S4, TS 1.3-K4

Uso: `uv run python app2_agente_con_control/06_sesiones.py [--rama reanudar|nueva|fork|todas] [--anti]`
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeSDKClient  # noqa: E402

from app2_agente_con_control.servers.helpdesk import (  # noqa: E402
    SERVER_NAME,
    HelpdeskState,
    build_server,
    find_ticket,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

LIST_TICKETS = tool_name("list_employee_tickets")
GET_TICKET = tool_name("get_ticket")
SEARCH_KB = tool_name("search_kb")
EMPLOYEE = "EMP-1040"  # cuatro tickets: TCK-4008 (correo y carpeta), 4015, 4034 y 4054 (reembolso de 1290 EUR)
RESOLVED_TICKET = "TCK-4054"  # el reembolso pasa a resuelto entre fases
OBSOLETE_ARTICLE = "KB-108"  # el artículo de sincronización de correo queda obsoleto
# Proporción de resultados previos obsoletos a partir de la cual se empieza de nuevo.
FRESH_THRESHOLD = 0.5
BRANCHES = ["reanudar", "nueva", "fork"]

SYSTEM_PROMPT = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Analiza los tickets con las tools y apoya "
    "cada recomendación en un ticket o un artículo de la base de conocimiento (cítalos por su ID). No pagues ni "
    "escales nada: solo analiza. Responde en español y de forma breve."
)
BASE_TASK = (
    f"Analiza todos los tickets de {EMPLOYEE}: estado de cada uno y, para cada ticket abierto, el artículo de "
    "la base de conocimiento que aplicarías."
)
FOLLOW_UP = "¿Qué queda pendiente de ese empleado y qué artículo aplicarías a cada cosa pendiente?"
FORK_STRATEGIES = {
    "autoservicio": "Estrategia A: propón resolver todo lo pendiente por autoservicio con los artículos de la KB.",
    "escalar": "Estrategia B: propón qué escalar a una persona y con qué datos, sin autoservicio.",
}


# --- Lógica sin modelo ---------------------------------------------------------


def apply_phase_change(state: HelpdeskState) -> None:
    """Cambios entre la sesión base y la siguiente, solo en el estado de esta ejecución."""
    state.ticket_overrides[RESOLVED_TICKET] = {"status": "RESOLVED"}
    state.kb_overrides[OBSOLETE_ARTICLE] = {
        "obsolete": True,
        "body": "Retirado: el cliente de correo nuevo resincroniza solo; si falla, abrir un ticket de software.",
    }


def snapshot(state: HelpdeskState) -> dict[str, dict[str, Any]]:
    """Estado actual de los tickets del empleado y de la vigencia de los artículos."""
    ids = [t["ticket_id"] for t in load("tickets.json") if t["user_id"] == EMPLOYEE]
    articles = load("articulos_kb.json")
    return {
        "tickets": {tid: find_ticket(state, tid)["status"] for tid in ids},
        "kb": {
            a["article_id"]: bool(a["superseded_by"] or state.kb_overrides.get(a["article_id"], {}).get("obsolete"))
            for a in articles
        },
    }


def diff_states(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Lista concreta de lo que cambió entre dos fotos."""
    changes = [
        {"kind": "ticket", "id": tid, "before": before["tickets"][tid], "after": status}
        for tid, status in after["tickets"].items()
        if before["tickets"].get(tid) != status
    ]
    label = {False: "vigente", True: "obsoleto"}
    changes += [
        {"kind": "kb", "id": aid, "before": label[before["kb"][aid]], "after": label[flag]}
        for aid, flag in after["kb"].items()
        if before["kb"].get(aid) != flag
    ]
    return changes


def change_notice(changes: list[dict[str, str]]) -> str:
    """Aviso para la sesión reanudada: qué cambió, en concreto, y que solo eso se reconsulte."""
    if not changes:
        return ""
    lines = ["Aviso: desde tu análisis anterior han cambiado estos datos:"]
    lines += [f"- {c['id']}: {c['before']} → {c['after']}" for c in changes]
    lines.append("Vuelve a consultar solo estos elementos; el resto de tu análisis sigue siendo válido.")
    return "\n".join(lines)


def findings(rec: RunRecord) -> dict[str, Any]:
    """Hallazgos de la sesión base: estado de cada ticket y artículos consultados."""
    tickets: dict[str, str] = {}
    kb: list[str] = []
    for call in rec.tool_calls:
        if not call.executed or call.is_error or not call.result_text:
            continue
        data = json.loads(call.result_text)
        if call.name == LIST_TICKETS:
            tickets.update({t["ticket_id"]: t["status"] for t in data.get("tickets", [])})
        elif call.name == GET_TICKET and "ticket_id" in data:
            tickets[data["ticket_id"]] = data["status"]
        elif call.name == SEARCH_KB:
            kb += [a["article_id"] for a in data.get("articles", []) if a["article_id"] not in kb]
    return {"tickets": tickets, "kb": kb}


def stale_ratio(rec: RunRecord, changes: list[dict[str, str]]) -> float:
    """Proporción de resultados previos que mencionan algo que cambió."""
    results = [c for c in rec.tool_calls if c.executed and not c.is_error and c.result_text]
    if not results:
        return 0.0
    changed = {c["id"] for c in changes}
    stale = sum(any(cid in call.result_text for cid in changed) for call in results)
    return stale / len(results)


def decide(ratio: float) -> str:
    """Reanudar si el contexto previo vale en su mayor parte; si no, sesión nueva con resumen (1.7-S3)."""
    return "nueva" if ratio >= FRESH_THRESHOLD else "reanudar"


def structured_summary(found: dict[str, Any], changes: list[dict[str, str]]) -> str:
    """Resumen para una sesión nueva: lo que sigue valiendo, separado de lo que cambió."""
    changed = {c["id"] for c in changes}
    lines = [f"Resumen estructurado del análisis previo de {EMPLOYEE}.", "Hallazgos que siguen valiendo:"]
    lines += [f"- {tid}: {status}" for tid, status in found["tickets"].items() if tid not in changed]
    valid_kb = [a for a in found["kb"] if a not in changed]
    if valid_kb:
        lines.append(f"- Artículos consultados y vigentes: {', '.join(valid_kb)}")
    lines.append("Cambiado desde entonces (vuelve a consultarlo):")
    lines += [f"- {c['id']}: {c['before']} → {c['after']}" for c in changes]
    return "\n".join(lines)


def cli_resume_command(name: str) -> str:
    """Comando equivalente de la CLI para una sesión con nombre (1.7-K1)."""
    return f"claude --resume {name}"


# --- Ejecución con modelo ------------------------------------------------------


def options_for(state: HelpdeskState, *, budget: float, model: str, cwd: str, **session: Any) -> Any:
    """Opciones de una sesión. Para `resume`, `budget` ya incluye el coste de la base (ver main_async)."""
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={SERVER_NAME: build_server(state)},
        tools=[],
        allowed_tools=[LIST_TICKETS, GET_TICKET, SEARCH_KB],
        # Se quitan las que modifican: este módulo solo analiza.
        disallowed_tools=[tool_name("process_reimbursement"), tool_name("escalate_to_human")],
        # Directorio temporal: las sesiones de la lección no se mezclan con
        # las del proyecto ni entre ejecuciones.
        cwd=cwd,
        max_turns=12,  # red de seguridad
        **session,  # resume=… y fork_session=… según la rama
    )


async def run_session(prompt: str, options: Any, label: str) -> RunRecord:
    print(f"\n=== {label} ===\n[prompt] {prompt}")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        rec = await record(client.receive_response())
    # Respuesta completa: la lección está en si cita datos viejos, y el
    # recorder solo muestra el principio.
    print(f"[respuesta completa]\n{rec.final_text}\n[sesión] {rec.session_id}")
    return rec


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=["sin_aviso"])
    parser.add_argument("--rama", choices=[*BRANCHES, "todas"], default="todas")
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")
    branches = BRANCHES if args.rama == "todas" else [args.rama]
    # Reparto del tope entre la base y cada rama (los forks son dos sesiones).
    sessions = 1 + sum(2 if b == "fork" else 1 for b in branches)
    per_session = budget / sessions

    state = HelpdeskState()
    cwd = tempfile.mkdtemp(prefix="ccarf-app2-06-")
    print(f"[cwd] {cwd}")
    base = await run_session(BASE_TASK, options_for(state, budget=per_session, model=model, cwd=cwd), "sesión base")
    print(f"[cli] equivalente con nombre: claude -n app2-06 y después {cli_resume_command('app2-06')}")

    # Una sesión reanudada o bifurcada arrastra el coste de la base (en la
    # primera ejecución, el fork sin llamadas costó más que la base): su tope
    # es ese coste más su parte del presupuesto.
    resumed_budget = (base.cost_usd or 0.0) + per_session

    before = snapshot(HelpdeskState())
    apply_phase_change(state)
    changes = diff_states(before, snapshot(state))
    ratio = stale_ratio(base, changes)
    print(f"\n[cambios] {changes}\n[obsoletos] {ratio:.0%} de los resultados previos → decisión: {decide(ratio)}")

    if "reanudar" in branches:
        notice = "" if args.anti else change_notice(changes)
        prompt = f"{notice}\n\n{FOLLOW_UP}" if notice else FOLLOW_UP
        label = "reanudar sin aviso (anti)" if args.anti else "reanudar con aviso de cambios"
        await run_session(prompt, options_for(state, budget=resumed_budget, model=model, cwd=cwd,
                                              resume=base.session_id), label)
    if "nueva" in branches:
        prompt = f"{structured_summary(findings(base), changes)}\n\n{FOLLOW_UP}"
        await run_session(prompt, options_for(state, budget=per_session, model=model, cwd=cwd), "sesión nueva con resumen")
    if "fork" in branches:
        notice = change_notice(changes)
        for name, strategy in FORK_STRATEGIES.items():
            # Cada fork parte de la misma base y no ve al otro.
            options = options_for(state, budget=resumed_budget, model=model, cwd=cwd,
                                  resume=base.session_id, fork_session=True)
            fork = await run_session(f"{notice}\n\n{strategy}", options, f"fork {name}")
            print(f"[fork] {name}: sesión {fork.session_id} (base {base.session_id})")
    print(f"\n[esperado] con aviso o con resumen, {RESOLVED_TICKET} ya no está pendiente y {OBSOLETE_ARTICLE} "
          "no se recomienda; sin aviso, la respuesta usa los resultados viejos.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
