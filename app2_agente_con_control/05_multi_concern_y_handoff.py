"""Peticiones con varios asuntos, case facts persistentes y handoff estructurado.

CONCEPTO [TS 1.4-K3, S2, S3 · TS 5.1-K1, S1, S2]: descomponer una petición
con varios asuntos, conservar los datos críticos entre turnos y escalar con un
resumen que la persona que lo recibe pueda usar sin la conversación.

QUÉ DICE LA GUÍA:
- Una petición con varios asuntos se descompone en elementos distintos, se
  investiga cada uno en paralelo con un contexto compartido y se sintetiza una
  resolución unificada (1.4-S2).
- La sumarización progresiva tiene un riesgo: condensa importes, porcentajes,
  fechas y lo que el cliente dijo esperar en resúmenes vagos (5.1-K1).
- Los hechos transaccionales (importes, fechas, números de pedido, estados) se
  extraen a un bloque de «case facts» persistente que va en cada prompt, fuera
  del historial resumido (5.1-S1); en sesiones con varios asuntos, los datos
  de cada asunto van en una capa de contexto separada (5.1-S2).
- Un escalamiento a mitad de proceso sigue un protocolo de handoff
  estructurado con los datos del cliente, el análisis de la causa raíz y las
  acciones recomendadas (1.4-K3): ID del cliente, causa raíz, importe del
  reembolso y acción recomendada, porque la persona que lo recibe no tiene la
  transcripción (1.4-S3).

POR QUÉ IMPORTA: el error no está en resumir, sino en resumir los números. Un
resumen en prosa sirve para el hilo de la conversación; los importes y las
fechas tienen que viajar como datos, igual que en el handoff.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: «ampliar la ventana de contexto» o «pedir un
resumen más detallado» cuando se pierden importes entre turnos. El arreglo es
sacar los hechos del resumen a un bloque estructurado. Y en el escalamiento,
un párrafo en texto libre deja a la persona sin el ID, el importe o la acción.

Inferencia propia: aquí la descomposición en asuntos y la extracción de los
hechos las hace código determinista (palabras clave y expresiones regulares)
para poder probarlas sin modelo. En producción, la extracción puede hacerla el
propio modelo con un schema (TS 4.3, entrega 3).

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 05.

INTRODUCE: TS 1.4-K3, TS 1.4-S2, TS 1.4-S3, TS 5.1-K1, TS 5.1-S1, TS 5.1-S2
USA: TS 1.4-K1

Uso: `uv run python app2_agente_con_control/05_multi_concern_y_handoff.py [--anti resumen|handoff_libre]`
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeSDKClient  # noqa: E402

from app2_agente_con_control.servers.helpdesk import (  # noqa: E402
    HANDOFF_FIELDS,
    SERVER_NAME,
    HelpdeskState,
    build_server,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

GET_TICKET = tool_name("get_ticket")
SEARCH_KB = tool_name("search_kb")
LIST_TICKETS = tool_name("list_employee_tickets")
ESCALATE = tool_name("escalate_to_human")
ANTI_VARIANTS = ["resumen", "handoff_libre"]

# Palabras que asignan una frase o un resultado a un asunto. El orden es el de
# la capa por asunto en el bloque.
CONCERN_KEYWORDS = {
    "red": ["vpn", "wifi", "red "],
    "licencias": ["licencia"],
    "gastos": ["reembolso", "ratón", "eur", "costó", "cobrar"],
}
AMOUNT_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*EUR", re.IGNORECASE)
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

SYSTEM_PROMPT = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Cuando un mensaje trae varios asuntos, "
    "sepáralos, investiga cada uno (puedes pedir varias tools en la misma respuesta) y responde con una "
    "resolución unificada, un apartado por asunto. Si escalas a una persona, usa escalate_to_human: esa "
    "persona no verá esta conversación. Responde en español y de forma breve."
)
# Igual en las dos variantes. Un resumen corto es lo habitual cuando el
# historial crece; con dos o tres frases, Haiku 5.5 conservó los importes
# (2026-10-24) y el riesgo de 5.1-K1 no se veía.
SUMMARY_REQUEST = "Resume en una sola frase, de 25 palabras como máximo, lo que sabemos del caso para continuar en otra sesión."


def multi_concern_ticket() -> dict[str, Any]:
    """El ticket de VPN, licencia y reembolso del ratón."""
    return next(t for t in load("tickets.json") if "VPN" in t["description"] and "reembolso" in t["description"])


def concerns_in(text: str) -> list[str]:
    lowered = text.lower()
    return [c for c, words in CONCERN_KEYWORDS.items() if any(w in lowered for w in words)]


def decompose(text: str) -> list[str]:
    """Asuntos distintos de una petición, en el orden de la capa por asunto (1.4-S2)."""
    return concerns_in(text)


def extract_user_facts(message: str) -> dict[str, dict[str, list[Any]]]:
    """Importes y fechas que dice el empleado, asignados al asunto de cada frase."""
    facts: dict[str, dict[str, list[Any]]] = {}
    for sentence in re.split(r"(?<=[.;])\s+", message):
        for concern in concerns_in(sentence):
            layer = facts.setdefault(concern, {})
            if concern == "gastos":
                amounts = [float(a.replace(",", ".")) for a in AMOUNT_RE.findall(sentence)]
                if amounts:
                    layer.setdefault("amounts_eur", []).extend(amounts)
            dates = DATE_RE.findall(sentence)
            if dates:
                layer.setdefault("dates", []).extend(dates)
    return {concern: layer for concern, layer in facts.items() if layer}


def extract_tool_facts(rec: RunRecord, case_ticket_id: str) -> dict[str, dict[str, Any]]:
    """Hechos de los resultados de las tools: el ticket del caso y los artículos por asunto.

    La capa «caso» solo la llena el ticket del enunciado: si el modelo consulta
    otro ticket, no sustituye al del caso.
    """
    facts: dict[str, dict[str, Any]] = {}
    for call in rec.tool_calls:
        if not call.executed or call.is_error or not call.result_text:
            continue
        try:
            data = json.loads(call.result_text)
        except json.JSONDecodeError:
            continue
        if call.name == GET_TICKET and data.get("ticket_id") == case_ticket_id:
            facts["caso"] = {k: data[k] for k in ("ticket_id", "user_id", "status", "created_at")}
        elif call.name == SEARCH_KB:
            for article in data.get("articles", []):
                label = article["article_id"]
                if article.get("superseded_by"):
                    label += f" (sustituido por {article['superseded_by']})"
                for concern in concerns_in(article["title"]):
                    facts.setdefault(concern, {}).setdefault("kb", []).append(label)
        elif call.name == LIST_TICKETS:
            for ticket in data.get("tickets", []):
                for concern in concerns_in(ticket["description"]):
                    facts.setdefault(concern, {}).setdefault("tickets", []).append(
                        f"{ticket['ticket_id']} ({ticket['status']})"
                    )
    return facts


def merge_facts(old: dict[str, dict[str, Any]], new: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fusiona sin perder nada: las listas se unen sin duplicados y el escalar nuevo sustituye al viejo."""
    merged = {concern: dict(layer) for concern, layer in old.items()}
    for concern, layer in new.items():
        target = merged.setdefault(concern, {})
        for key, value in layer.items():
            if isinstance(value, list):
                current = list(target.get(key, []))
                target[key] = current + [v for v in value if v not in current]
            else:
                target[key] = value
    return merged


def render_case_facts(facts: dict[str, dict[str, Any]]) -> str:
    """Bloque de case facts: primero el caso y después una capa por asunto (5.1-S1, 5.1-S2)."""
    lines = ["CASE FACTS (datos exactos; no los resumas ni los redondees)"]
    for concern in ["caso", *CONCERN_KEYWORDS]:
        if concern in facts:
            values = "; ".join(f"{k}={v}" for k, v in facts[concern].items())
            lines.append(f"[{concern}] {values}")
    return "\n".join(lines)


def turn_prompt(summary: str | None, facts: dict[str, dict[str, Any]], message: str, *, anti: str | None) -> str:
    """Prompt de cada turno. El bloque va fuera del resumen; la variante `resumen` no lo lleva."""
    parts = []
    if summary:
        parts.append(f"Resumen de la conversación hasta ahora:\n{summary}")
    if facts and anti != "resumen":
        parts.append(render_case_facts(facts))
    parts.append(f"Mensaje nuevo del empleado:\n{message}")
    return "\n\n".join(parts)


def check_handoff(handoff: dict[str, Any], facts: dict[str, dict[str, Any]]) -> list[str]:
    """Problemas del handoff frente a los case facts (vacía si la persona tiene lo que necesita)."""
    problems = [f"sin campo {f}" for f in HANDOFF_FIELDS if handoff.get(f) in (None, "")]
    if problems:
        return problems
    case = facts.get("caso", {})
    for key in ("user_id", "ticket_id"):
        if case.get(key) and handoff[key] != case[key]:
            problems.append(f"{key} {handoff[key]} ≠ {case[key]}")
    amounts = facts.get("gastos", {}).get("amounts_eur", [])
    if amounts and float(handoff["amount_eur"]) not in amounts:
        problems.append(f"amount_eur {handoff['amount_eur']} ≠ {amounts[-1]}")
    # Las fechas tienen que llegar completas: «hasta el 30/10» sin año es
    # justo la vaguedad de la sumarización progresiva (5.1-K1). Se aceptan
    # dd/mm/aaaa y aaaa-mm-dd; una fecha escrita en palabras no cuenta.
    text = f"{handoff['root_cause']} {handoff['recommended_action']}"
    dates = [d for layer in facts.values() for d in layer.get("dates", [])]
    problems += [f"falta la fecha {d}" for d in dict.fromkeys(dates) if not date_in(d, text)]
    return problems


def date_in(date: str, text: str) -> bool:
    day, month, year = (int(part) for part in date.split("/"))
    forms = {date, f"{day:02d}/{month:02d}/{year}", f"{day}/{month}/{year}", f"{year}-{month:02d}-{day:02d}"}
    return any(form in text for form in forms)


def user_turns(ticket: dict[str, Any]) -> list[str]:
    return [
        f"Soy {ticket['user_id']} (ticket {ticket['ticket_id']}). {ticket['description']}",
        "El ratón me costó 34,50 EUR y lo compré el 12/09/2026; necesito cobrarlo antes del 30/10/2026. "
        "La licencia del editor caduca el 28/10/2026.",
        "Llevo demasiado esperando: pásalo ya a una persona con todo lo que sabes.",
    ]


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    ticket = multi_concern_ticket()
    print(f"[asuntos] {ticket['ticket_id']}: {decompose(ticket['description'])}")
    state = HelpdeskState()
    server = build_server(state, handoff="free_text" if args.anti == "handoff_libre" else "structured")
    summary: str | None = None
    facts: dict[str, dict[str, Any]] = {}
    spent = 0.0

    for number, message in enumerate(user_turns(ticket), start=1):
        if budget - spent <= 0:
            print(f"[corte] presupuesto agotado antes del turno {number} (${spent:.4f} de ${budget})")
            break
        # Cada turno empieza una sesión nueva con el resumen: es la
        # sumarización progresiva. Lo que cambia entre variantes es si los
        # hechos viajan aparte del resumen.
        prompt = turn_prompt(summary, facts, message, anti=args.anti)
        options = isolated_options(
            max_budget_usd=budget - spent,  # el tope es de toda la ejecución
            model=model,
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={SERVER_NAME: server},
            tools=[],
            allowed_tools=[tool_name(n) for n in ("verify_employee", "get_ticket", "list_employee_tickets",
                                                   "search_kb", "escalate_to_human")],
            # El caso no tiene ticket de reembolso que pagar: se quita la tool.
            disallowed_tools=[tool_name("process_reimbursement")],
            max_turns=10,  # red de seguridad
        )
        print(f"\n=== turno {number} · variante {args.anti or 'case facts'} ===\n[prompt]\n{prompt}\n")
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            rec = await record(client.receive_response())
            # Los hechos se extraen siempre, también en la variante anti, para
            # poder comparar al final qué se perdió.
            facts = merge_facts(facts, merge_facts(extract_tool_facts(rec, ticket["ticket_id"]),
                                                   extract_user_facts(message)))
            await client.query(SUMMARY_REQUEST)
            summary_rec = await record(client.receive_response(), echo=False)
        summary = summary_rec.final_text
        # Se suman las dos consultas de la sesión. Si el SDK diera el coste
        # acumulado de la sesión, esto lo sobrestima: se queda del lado seguro.
        spent += (rec.cost_usd or 0.0) + (summary_rec.cost_usd or 0.0)
        print(f"[resumen para el turno siguiente] {summary}")

    print(f"\n{render_case_facts(facts)}")
    if not state.escalations:
        print("[medida] no hubo escalamiento")
        return 0
    handoff = state.escalations[-1]
    problems = check_handoff(handoff, facts)
    print(f"[handoff] {json.dumps(handoff, ensure_ascii=False)}")
    print(f"[medida] handoff {'completo' if not problems else 'con problemas: ' + '; '.join(problems)} · coste≈${spent:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
