"""Hook que reescribe argumentos: `updatedInput` frente a deny con motivo.

CONCEPTO (apoyo, sin viñeta propia): imponer el valor de un argumento desde un
hook `PreToolUse`, sobre lo que ya introdujeron app2/01 y app2/02.

QUÉ DICE LA GUÍA: no tiene una viñeta para reescribir argumentos. Lo que se
aplica aquí está en app2/01 (código frente a prompt, 1.4-K1, 1.4-K2) y en
app2/02 (interceptar la llamada saliente, 1.5-K2). El patrón que la guía enseña
para hacer cumplir una regla es bloquear: el prerrequisito de 1.4-S1 y el
bloqueo con redirección de 1.5-S2.

EN PRODUCCIÓN (no evaluable): además de deny con un motivo, que solo vuelve al
modelo como texto, `PreToolUse` puede devolver allow con `updatedInput`, que
sustituye los argumentos antes de ejecutar la tool
(`PreToolUseHookSpecificOutput` de claude-agent-sdk). La guía no nombra
`updatedInput`: lo que la guía sostiene es el hook que bloquea. Qué opciones
traerá una pregunta real no se sabe desde aquí.

POR QUÉ IMPORTA: cuando hay que garantizar un *valor* (el ID del empleado que
verificó `verify_employee`), deny dice «escríbelo así» y confía en que el modelo
reintente bien. Con `updatedInput`, la llamada ya llega con el valor correcto en
la primera. Una llamada con ID erróneo no se ejecuta en ninguna de las dos
variantes (el hook comprueba); lo que cambia es que el pago correcto deja de
depender de un reintento del modelo. La garantía es solo de ese campo: que el
ticket y el importe sean del verificado lo sigue comprobando el handler. Y
reescribir en silencio corrige un descuido, pero también tapa un intento que no
lo es (pagar el ticket de otro con el ID de otro), que un deny haría visible.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: en diseño, devolver deny con el ID correcto en
el motivo y dar por hecho que el modelo lo reenviará bien; para imponer un
valor, el hook sobrescribe el argumento. La trampa inversa es descartar el hook
que bloquea porque no fija el valor: si no hay opción de reescribir, bloquear
es lo que la guía sostiene (1.4-S1, 1.5-S2).

Este módulo NO llama al modelo. Con Haiku 5.5 y Haiku 4.5 el modelo casi no se
equivoca de ID (calibración en docs/hallazgos.md), así que una tasa no mostraría
la diferencia, que es de estructura y no de probabilidad. En su lugar se fuerza
la llamada con el ID erróneo y se ejecuta el hook y el handler reales, uno tras
otro. Lo que haría el modelo tras un deny son hipótesis, y se imprimen como
tales. Aquí el hook es el único control: el servidor se construye con
`gate=False` para que no se mezcle con la puerta del handler de app2/01.

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 07.

USA: TS 1.4-K1, TS 1.4-K2, TS 1.5-K2

Uso: `uv run python app2_agente_con_control/07_hook_reescritura.py [--anti]`
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import HookMatcher  # noqa: E402

from app2_agente_con_control.servers.helpdesk import (  # noqa: E402
    HelpdeskState,
    make_tools,
    tool_name,
)
from harness.offline import call_tool, run_hook  # noqa: E402

PAY = tool_name("process_reimbursement")

# Empleado verificado, su ticket y dos descuidos de dígitos que no son de nadie.
OWN_USER, OWN_TICKET, OWN_AMOUNT = "EMP-1028", "TCK-4047", 120.0
WRONG_USER, WRONG_USER_AGAIN = "EMP-1082", "EMP-1280"

# --- PreToolUse: imponer el ID verificado (1.5-K2) ------------------------------


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def allow_with(updated_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            # Sustituye los argumentos completos: se parte de los del modelo y
            # solo se cambia el campo que el hook garantiza.
            "updatedInput": updated_input,
        }
    }


def make_rewrite_hook(state: HelpdeskState, anti: str | None):
    """Hook de `process_reimbursement` que garantiza que `user_id` sea el verificado.

    El ID sale del estado del servidor (lo escribió `verify_employee`), no de lo
    que el modelo haya copiado después. Con `anti`, deniega con el ID en el
    motivo; sin `anti`, lo sobrescribe y deja pasar la llamada.
    """

    async def rewrite_hook(hook_input: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
        tool_input = hook_input["tool_input"]
        if not state.verified:
            # Prerrequisito: sin verificación no hay ID que imponer.
            return deny("Ningún empleado verificado: llama antes a verify_employee con el ID exacto (EMP-NNNN).")
        if len(state.verified) > 1:
            # Falla en cerrado: con dos verificados el hook no adivina cuál es.
            return deny("Hay más de un empleado verificado en la sesión: no se puede decidir a quién pagar.")
        (verified,) = state.verified
        if tool_input.get("user_id") == verified:
            return {}
        if anti:
            # Anti-patrón: el valor correcto vuelve al modelo como texto y es él quien debe reescribirlo.
            return deny(f"El user_id debe ser el del empleado verificado: {verified}. Reintenta con ese ID.")
        return allow_with({**tool_input, "user_id": verified})

    return rewrite_hook


def build_hooks(state: HelpdeskState, anti: str | None) -> dict[str, list[HookMatcher]]:
    # El matcher es el nombre MCP completo de la tool.
    return {"PreToolUse": [HookMatcher(matcher=PAY, hooks=[make_rewrite_hook(state, anti)])]}


# --- Escenario determinista -----------------------------------------------------


@dataclass
class Step:
    """Una llamada a `process_reimbursement`: qué decidió el hook y qué llegó a la tool."""

    state: HelpdeskState
    decision: str | None  # allow | deny | None (el hook no intervino)
    reason: str | None
    tool_input: dict[str, Any] | None  # lo que recibió la tool; None si no se ejecutó
    executed: bool
    is_error: bool


@dataclass
class Outcome:
    label: str
    calls: int
    paid_with: list[str]  # user_id de cada pago ejecutado

    @property
    def completed(self) -> bool:
        return OWN_USER in self.paid_with


def verified_state() -> HelpdeskState:
    """Sesión en la que `verify_employee` ya verificó al empleado."""
    state = HelpdeskState()
    state.verified.add(OWN_USER)
    return state


def wrong_call(user_id: str = WRONG_USER) -> dict[str, Any]:
    """La llamada del modelo con un descuido de dígitos en el ID (EMP-1028 → EMP-1082)."""
    return {"user_id": user_id, "ticket_id": OWN_TICKET, "amount_eur": OWN_AMOUNT}


def run_step(state: HelpdeskState, anti: str | None, tool_input: dict[str, Any], *, hook: bool = True) -> Step:
    """Pasa una llamada por el hook real y, si no se deniega, por el handler real.

    `hook=False` quita el hook (control: qué pasa sin él).
    """
    decision, reason, final = None, None, tool_input
    if hook:
        result = run_hook(make_rewrite_hook(state, anti), "PreToolUse", PAY, tool_input)
        decision, reason = result.decision, result.reason
        if decision == "deny":
            return Step(state, decision, reason, None, executed=False, is_error=False)
        final = result.updated_input or tool_input
    # gate=False: el hook es el único control; no se mezcla con la puerta de app2/01.
    handler = {t.name: t for t in make_tools(state, gate=False)}["process_reimbursement"]
    outcome = call_tool(handler, final)
    return Step(state, decision, reason, final, executed=True, is_error=outcome.is_error)


def outcomes(anti: str | None) -> list[Outcome]:
    """Desenlaces posibles de que el modelo escriba un ID erróneo.

    Con `updatedInput` hay uno. Con deny hay tres, y qué ocurre depende de lo
    que haga el modelo después: no son observaciones, son hipótesis.
    """
    if not anti:
        state = verified_state()
        run_step(state, None, wrong_call())
        return [Outcome("el hook reescribe el ID", 1, [p["user_id"] for p in state.paid])]

    results = []
    # (etiqueta, llamadas del modelo tras el deny inicial)
    branches = [
        ("el modelo reintenta con el ID correcto", [wrong_call(OWN_USER)]),
        ("el modelo reintenta con otro ID erróneo", [wrong_call(WRONG_USER_AGAIN)]),
        ("el modelo no reintenta", []),
    ]
    for label, retries in branches:
        state = verified_state()
        run_step(state, anti, wrong_call())
        for retry in retries:
            run_step(state, anti, retry)
        results.append(Outcome(label, 1 + len(retries), [p["user_id"] for p in state.paid]))
    return results


def print_step(title: str, step: Step) -> None:
    if step.decision == "deny":
        print(f"{title}\n    hook: deny · motivo para el modelo: {step.reason}\n    la tool NO se ejecuta")
        return
    changed = "reescribe" if step.decision == "allow" else "no interviene"
    print(f"{title}\n    hook: {changed} · la tool recibe user_id={step.tool_input['user_id']} · "
          f"{'error de validación' if step.is_error else 'pago ejecutado'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anti", nargs="?", const="deny", choices=["deny"],
                        help="deny con el ID correcto en el motivo (anti-patrón); sin la opción, updatedInput")
    args = parser.parse_args()
    variant = args.anti or "updatedInput"

    print(f"[escenario] {OWN_USER} está verificado. El modelo escribe {WRONG_USER} (dígitos cambiados) "
          f"al pagar {OWN_TICKET} ({OWN_AMOUNT:.2f} EUR). Sin modelo: se ejecutan el hook y el handler reales.")
    print(f"[esperado] variante {variant}: el pago con ID erróneo nunca se ejecuta")
    print()
    print_step("[control] sin hook (qué pasa si nadie lo corrige)", run_step(verified_state(), None, wrong_call(), hook=False))
    print_step(f"[llamada 1] variante {variant}", run_step(verified_state(), args.anti, wrong_call()))
    print()
    if args.anti:
        print("[hipótesis] lo que pasa después depende del modelo; el hook no lo controla:")
    for outcome in outcomes(args.anti):
        done = "pago propio completado" if outcome.completed else "pago propio SIN completar"
        print(f"  - {outcome.label}: {outcome.calls} llamada(s) · pagos con {outcome.paid_with or 'ningún ID'} · {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
