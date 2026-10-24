"""Permisos del Agent SDK: qué pre-aprueba, qué quita y qué deniega cada opción.

CONCEPTO (apoyo, sin viñeta propia): `allowed_tools`, `disallowed_tools`,
`permission_mode="dontAsk"` y la herencia del modo en un subagente.

QUÉ DICE LA GUÍA: no tiene una viñeta para los permisos del SDK; los da por
supuestos en 1.4 y 1.5. Este módulo existe porque la trampa más común al
construir es leer `allowed_tools` como una lista blanca (roadmap §7 y
conceptos-generales §4.3 del repositorio de estudio).

POR QUÉ IMPORTA (documentación del SDK, consultada el 2026-10-22):
- `allowed_tools` **pre-aprueba**: lo listado no pide permiso. No restringe:
  lo no listado sigue visible y pasa al modo de permisos.
- `disallowed_tools` con el nombre a secas **quita** la tool: no aparece en las
  tools disponibles de `init`.
- `permission_mode="dontAsk"` con `allowed_tools` es un agente cerrado: lo
  listado se aprueba y todo lo que pediría permiso se deniega.
- Un subagente hereda el modo del padre.
- Orden de evaluación: hooks → reglas deny → reglas ask → modo → reglas
  allow → `can_use_tool`. Por eso lo que debe cumplirse siempre va en un hook
  `PreToolUse`, que se evalúa primero (lección de app2/02).

ANTI-PATRÓN / TRAMPA DEL EXAMEN: «`allowed_tools: [lectura]` y así el agente no
puede pagar». Puede intentarlo: la tool sigue ahí y el resultado depende del
modo. Para que no exista, `disallowed_tools`; para que no pase nada sin
aprobar, `dontAsk`; para una regla de negocio, un hook.

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 03.

USA: TS 1.4-K1

Uso: `uv run python app2_agente_con_control/03_permisos.py [--config allowed|disallowed|dontAsk|subagente]`
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query  # noqa: E402

from app2_agente_con_control.servers.helpdesk import (  # noqa: E402
    SERVER_NAME,
    HelpdeskState,
    build_server,
    reimbursement_ticket,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import record  # noqa: E402

PAY = tool_name("process_reimbursement")
VERIFY = tool_name("verify_employee")
READ_TOOLS = [VERIFY, tool_name("get_ticket"), tool_name("list_employee_tickets")]
CONFIGS = ["allowed", "disallowed", "dontAsk", "subagente"]
EXPECTED = {
    "allowed": "process_reimbursement visible; la llamada pasa al modo por defecto y, sin nadie que apruebe, se deniega",
    "disallowed": "según la documentación, process_reimbursement desaparece; con una tool MCP (CLI 2.1.309) "
    "sigue en init y la llamada se deniega",
    "dontAsk": "visible, pero cualquier llamada no pre-aprobada se deniega sin preguntar",
    "subagente": "el subagente declara process_reimbursement, pero hereda dontAsk del padre y se le deniega",
}


def build_options(config: str, *, budget: float, model: str, subagent_model: str, state: HelpdeskState) -> ClaudeAgentOptions:
    """Opciones de cada configuración, visibles y comparables entre sí."""
    common = dict(
        max_budget_usd=budget,
        model=model,
        system_prompt="Eres el agente de la mesa de ayuda TI de una empresa ficticia. Responde en español y breve.",
        mcp_servers={SERVER_NAME: build_server(state)},
        tools=[],  # sin tools integradas: solo cuentan las de la mesa de ayuda
        max_turns=8,  # red de seguridad
    )
    if config == "allowed":
        # Pre-aprueba la lectura. PAY no está, pero tampoco está prohibida.
        return isolated_options(**common, allowed_tools=READ_TOOLS)
    if config == "disallowed":
        # Quita PAY de las tools disponibles; el resto pasa por el modo por defecto.
        return isolated_options(**common, allowed_tools=READ_TOOLS, disallowed_tools=[PAY])
    if config == "dontAsk":
        return isolated_options(**common, allowed_tools=READ_TOOLS, permission_mode="dontAsk")
    if config == "subagente":
        return isolated_options(
            **{**common, "tools": ["Agent"]},  # `tools=[]` quitaría también la tool integrada Agent
            # "Agent" es la tool que lanza subagentes (la guía la llama "Task").
            allowed_tools=[*READ_TOOLS, "Agent"],
            permission_mode="dontAsk",
            agents={
                "pagos": AgentDefinition(
                    description="Paga reembolsos ya aprobados. Úsalo para cualquier pago.",
                    prompt="Eres el subagente de pagos. Verifica al empleado y paga el reembolso que te indiquen.",
                    tools=[VERIFY, PAY],
                    model=subagent_model,
                    # Sin permissionMode propio: hereda el del padre.
                    # En primer plano (regla 4): por defecto se lanzaba en
                    # segundo plano y el padre terminaba antes de ver su resultado.
                    background=False,
                )
            },
        )
    raise ValueError(config)


async def run(config: str, budget: float, model: str, subagent_model: str) -> None:
    state = HelpdeskState()
    options = build_options(config, budget=budget, model=model, subagent_model=subagent_model, state=state)
    ticket = reimbursement_ticket(39.9)
    prompt = (
        f"Soy {ticket['user_id']}. Verifícame y págame el reembolso de 39,90 EUR del ticket {ticket['ticket_id']}."
        + (" No pagues tú: delega el pago en el subagente «pagos»." if config == "subagente" else "")
    )
    print(f"\n=== configuración {config} ===\n[esperado] {EXPECTED[config]}")
    rec = await record(query(prompt=prompt, options=options))
    print(f"[medida] PAY en tools de init: {PAY in rec.init.get('tools', [])} · "
          f"intentos de pago: {sum(c.name == PAY for c in rec.tool_calls)} · denegaciones: {len(rec.denials)} · "
          f"pagos ejecutados: {len(state.paid)}")


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=[])
    parser.add_argument("--config", choices=CONFIGS, help="una sola configuración (por defecto, las cuatro)")
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "agent")
    for config in [args.config] if args.config else CONFIGS:
        await run(config, budget, model, subagent_model)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
