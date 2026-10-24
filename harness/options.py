"""Opciones aisladas para los agentes de las apps (roadmap §3, reglas 3 y 7, y §5).

PROPÓSITO: construir `ClaudeAgentOptions` con el aislamiento del proyecto por
defecto (`setting_sources=[]`, `skills=[]`, sin memoria automática y sin
conectores de claude.ai) y con un presupuesto obligatorio.

POR QUÉ EXISTE: sin `setting_sources`, el SDK carga lo mismo que la CLI
(`CLAUDE.md`, `.claude/rules/`, skills, hooks y memoria), así que el agente de
mesa de ayuda heredaría la capa meta del repositorio. Con la sesión de una
suscripción recibiría además las tools MCP de los conectores de claude.ai. Si
cada módulo lo repitiera a mano, bastaría un olvido para que una ejecución
dependiera de la credencial o de la máquina.

QUÉ NO HACE: no elige tools, permisos, modo ni prompt. Eso es lo que enseña
cada módulo y se escribe visible en su llamada; aquí solo se completan los
valores de aislamiento y cualquiera se puede sobrescribir.
"""

from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

# Variables que la CLI lee del entorno. Se fusionan con el `env` del módulo.
ISOLATION_ENV = {
    # La memoria automática escribiría y leería notas entre ejecuciones:
    # cada ejecución debe ser nueva (roadmap §13).
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    # `setting_sources=[]` no excluye los conectores de claude.ai.
    "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
}


# USA: TS 1.4-K1
def isolated_options(*, max_budget_usd: float, **kwargs: Any) -> ClaudeAgentOptions:
    """Devuelve `ClaudeAgentOptions` aisladas y con presupuesto.

    `max_budget_usd` es obligatorio: la regla de coste se impone en código y no
    en prosa, por la misma razón que una puerta programática gana a una
    instrucción en el prompt (ver TS 1.4-K1). `max_turns` no lo sustituye: es
    solo una red de seguridad.
    """
    if not max_budget_usd or max_budget_usd <= 0:
        raise ValueError("max_budget_usd debe ser un importe positivo (roadmap §3, regla 7)")

    # Se fusiona en vez de reemplazar: un módulo que pasa `env` para apagar un
    # valor por defecto (regla 4) no pierde el aislamiento por accidente. Una
    # clave explícita del módulo sí gana.
    env = {**ISOLATION_ENV, **kwargs.pop("env", {})}
    # `[]` aísla; un módulo puede pedir otra cosa (app1/06 usa ["project"]).
    kwargs.setdefault("setting_sources", [])
    # `skills=None` no apaga las skills: la CLI sigue listando las suyas y las
    # de los plugins (comprobado en la primera ejecución con modelo, SDK
    # 0.2.173). `[]` las oculta todas; un módulo que enseñe skills puede pedirlas.
    kwargs.setdefault("skills", [])
    return ClaudeAgentOptions(max_budget_usd=max_budget_usd, env=env, **kwargs)
