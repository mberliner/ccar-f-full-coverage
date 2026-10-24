"""Observación de una ejecución del Agent SDK (roadmap §5).

PROPÓSITO: recorrer los mensajes de `query()` o de `ClaudeSDKClient` y mostrar
por pantalla cada llamada a tool (con la respuesta en la que llegó y el
subagente que la hizo), el texto final, los turnos, el coste y las
denegaciones, y devolver todo en un `RunRecord` para comprobarlo en código.

POR QUÉ EXISTE: lo que enseñan los módulos es observable en el flujo de
mensajes, no en el texto final: llamadas intentadas frente a ejecutadas (ver
TS 1.4-K1), varias llamadas en una misma respuesta (ver TS 1.3-S3), llamadas
por subagente (ver TS 1.2-K1) y coste acumulado (roadmap §3, regla 7).

QUÉ NO HACE: no guarda nada (cada ejecución es nueva, §13), no reintenta ni
corta la ejecución (el corte por presupuesto lo hace el SDK y aquí solo se
registra) y no maqueta la salida: una línea por evento con `print`.

USA: TS 1.4-K1, TS 1.2-K1
"""

from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

# Tool que lanza subagentes: la guía la llama `Task`; el producto, `Agent`.
SUBAGENT_TOOLS = {"Task", "Agent"}
# Carga de definiciones diferidas: la decide el mecanismo de tool search, no
# es una elección de tool del modelo, así que no cuenta como llamada.
TOOL_SEARCH = "ToolSearch"
MAIN = "principal"
PREVIEW = 160


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]
    response: str  # «r1», «r2»…: respuesta del modelo en la que llegó
    agent: str  # MAIN o el subagent_type que la hizo
    executed: bool = False
    is_error: bool | None = None
    result_text: str | None = None  # texto del resultado, para extraer hechos (app2/05)


@dataclass
class RunRecord:
    init: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_search_loads: int = 0
    final_text: str | None = None
    num_turns: int | None = None
    cost_usd: float | None = None
    denials: list[Any] = field(default_factory=list)
    budget_exceeded: bool = False
    is_error: bool = False
    session_id: str | None = None  # para reanudar o bifurcar la sesión (app2/06)

    def parallel_groups(self) -> dict[str, list[ToolCall]]:
        """Respuestas con dos o más llamadas: el modelo las pidió a la vez."""
        groups: dict[str, list[ToolCall]] = {}
        for call in self.tool_calls:
            groups.setdefault(call.response, []).append(call)
        return {resp: calls for resp, calls in groups.items() if len(calls) > 1}

    def by_agent(self) -> dict[str, list[ToolCall]]:
        groups: dict[str, list[ToolCall]] = {}
        for call in self.tool_calls:
            groups.setdefault(call.agent, []).append(call)
        return groups


def result_text(content: Any) -> str | None:
    """Texto de un `tool_result`: la cadena tal cual o los bloques de texto concatenados."""
    if content is None or isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def short(value: Any) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= PREVIEW else text[: PREVIEW - 1] + "…"


class Recorder:
    """Acumula el estado de una ejecución mensaje a mensaje."""

    def __init__(self, echo: bool = True) -> None:
        self.record = RunRecord()
        self.echo = echo
        self.responses: dict[str, str] = {}  # message_id -> «rN»
        self.subagents: dict[str, str] = {}  # tool_use_id de Task/Agent -> subagent_type
        self.calls: dict[str, ToolCall] = {}

    def out(self, line: str) -> None:
        if self.echo:
            print(line)

    def response_label(self, message: AssistantMessage) -> str:
        # Una respuesta del modelo puede llegar partida en varios
        # AssistantMessage con el mismo message_id (uno por bloque).
        key = message.message_id or f"sin-id-{id(message)}"
        return self.responses.setdefault(key, f"r{len(self.responses) + 1}")

    def agent_of(self, parent_tool_use_id: str | None) -> str:
        if parent_tool_use_id is None:
            return MAIN
        return self.subagents.get(parent_tool_use_id, f"subagente {parent_tool_use_id}")

    def feed(self, message: Message) -> None:
        if isinstance(message, SystemMessage) and message.subtype == "init":
            self.on_init(message.data)
        elif isinstance(message, AssistantMessage):
            self.on_assistant(message)
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    self.on_tool_result(block)
        elif isinstance(message, ResultMessage):
            self.on_result(message)

    def on_init(self, data: dict[str, Any]) -> None:
        # Evidencia de aislamiento (§11.6): qué ve el agente al empezar.
        self.record.init = data
        servers = [s.get("name") for s in data.get("mcp_servers", [])]
        plugins = [p.get("name") for p in data.get("plugins", [])]
        self.out(
            f"[contexto] tools={len(data.get('tools', []))} mcp={servers} "
            f"skills={data.get('skills', [])} plugins={plugins} "
            f"credencial={data.get('apiKeySource')} modelo={data.get('model')}"
        )

    def on_assistant(self, message: AssistantMessage) -> None:
        label = self.response_label(message)
        agent = self.agent_of(message.parent_tool_use_id)
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                self.out(f"[texto {label} · {agent}] {short(block.text)}")
            elif isinstance(block, ToolUseBlock):
                if block.name == TOOL_SEARCH:
                    self.record.tool_search_loads += 1
                    self.out(f"[tool search {label}] carga de definiciones (no cuenta como llamada)")
                    continue
                if block.name in SUBAGENT_TOOLS:
                    self.subagents[block.id] = block.input.get("subagent_type", block.name)
                call = ToolCall(block.id, block.name, block.input, label, agent)
                self.calls[block.id] = call
                self.record.tool_calls.append(call)
                self.out(f"[llamada {label} · {agent}] {block.name} {short(block.input)}")

    def on_tool_result(self, block: ToolResultBlock) -> None:
        call = self.calls.get(block.tool_use_id)
        if call is None:
            return  # resultado de una carga de tool search
        call.executed = True
        call.is_error = bool(block.is_error)
        call.result_text = result_text(block.content)
        state = "error" if call.is_error else "ok"
        self.out(f"[resultado {call.response} · {call.agent}] {call.name} {state}: {short(block.content)}")

    def on_result(self, message: ResultMessage) -> None:
        rec = self.record
        rec.final_text = message.result
        rec.num_turns = message.num_turns
        rec.cost_usd = message.total_cost_usd
        rec.is_error = message.is_error
        rec.session_id = message.session_id
        rec.denials = message.permission_denials or []
        # Una llamada denegada recibe un tool_result con el motivo, pero la
        # tool no llegó a ejecutarse: intentada no es ejecutada.
        for denial in rec.denials:
            call = self.calls.get(denial.get("tool_use_id", "")) if isinstance(denial, dict) else None
            if call:
                call.executed = False
        rec.budget_exceeded = message.subtype == "error_max_budget_usd"
        if rec.budget_exceeded:
            self.out("[corte] presupuesto agotado (max_budget_usd)")
        if rec.final_text:
            self.out(f"[final] {short(rec.final_text)}")
        cost = f"{rec.cost_usd:.4f}" if rec.cost_usd is not None else "?"
        executed = sum(c.executed for c in rec.tool_calls)
        self.out(
            f"[fin] {message.subtype} · turnos={rec.num_turns} · coste=${cost} · "
            f"llamadas={len(rec.tool_calls)} (ejecutadas {executed}) · denegaciones={len(rec.denials)}"
        )


async def record(stream: AsyncIterable[Message], *, echo: bool = True) -> RunRecord:
    """Consume `query(...)` o `client.receive_response()` y devuelve el registro."""
    recorder = Recorder(echo)
    async for message in stream:
        recorder.feed(message)
    return recorder.record
