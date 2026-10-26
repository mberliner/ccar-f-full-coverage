"""Configuración de servidores MCP: ámbitos, credenciales, descubrimiento, resources y descripciones.

CONCEPTO [TS 2.4-K1, K2, K3, K4, S1, S2, S3, S4, S5]: `.mcp.json` del proyecto frente
al ámbito de usuario, variables `${VAR}` para las credenciales, tools de varios
servidores disponibles a la vez, *resources* para exponer catálogos y descripciones que
evitan que el agente prefiera una tool integrada.

QUÉ DICE LA GUÍA:
- Los servidores MCP se configuran en dos ámbitos: el del proyecto (`.mcp.json`), para
  las herramientas compartidas del equipo, y el del usuario (`~/.claude.json`), para
  los servidores personales o experimentales (2.4-K1, 2.4-S2).
- `.mcp.json` admite expansión de variables de entorno como `${GITHUB_TOKEN}`: las
  credenciales se gestionan sin subir secretos al repositorio (2.4-K2, 2.4-S1).
- Las tools de todos los servidores configurados se descubren al conectar y están
  disponibles a la vez para el agente (2.4-K3).
- Los *MCP resources* exponen catálogos de contenido (resúmenes de issues, jerarquías de
  documentación, esquemas de base de datos) y reducen las llamadas exploratorias
  (2.4-K4, 2.4-S5).
- Descripciones que detallan capacidades y salidas evitan que el agente prefiera una tool
  integrada, como `Grep`, sobre una tool MCP más capaz (2.4-S3).
- Servidores comunitarios para las integraciones estándar y propios para los flujos
  específicos del equipo (2.4-S4).

Decisión (2.4-S4), sin código: una integración estándar y ya resuelta por otros (Jira,
GitHub, Slack) pide un servidor comunitario: se mantiene fuera y se actualiza con su
proyecto. Un flujo propio de la mesa de ayuda (su catálogo, sus reglas, sus datos) pide
un servidor propio: es el único que conoce el dominio. El criterio no es el esfuerzo de
escribirlo, sino quién debe mantener el contrato de la tool.

POR QUÉ IMPORTA (inferencia propia): una configuración que funciona en la máquina de una
persona y no en la de otra, o que deja un token en el repositorio, o que obliga al agente
a explorar a ciegas, falla de forma silenciosa. Los ámbitos y las variables resuelven los
dos primeros casos; los resources y las descripciones, el tercero.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: no ofrecer el catálogo como resource, de modo que el agente explora
  con llamadas repetidas (`--anti sin_recursos`), y una descripción mínima en la tool MCP,
  con lo que el agente prefiere `Grep` (`--anti descripcion_minima`).
- Inferencias propias: el token en un archivo versionado, o un servidor personal en
  `.mcp.json`, son las respuestas tentadoras que el examen suele poner como distractores.
- EN PRODUCCIÓN (no evaluable): el agente no sabe que existen resources si nadie se lo
  dice; en el SDK se alcanzan con `ListMcpResourcesTool` y `ReadMcpResourceTool`, y la
  aplicación debe indicarlo (aquí, en el prompt del sistema). Con `setting_sources=["project"]`
  el SDK conecta los servidores de `.mcp.json` sin pedir aprobación.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 06.

INTRODUCE: TS 2.4-K1, TS 2.4-K2, TS 2.4-K3, TS 2.4-K4, TS 2.4-S1, TS 2.4-S2, TS 2.4-S3, TS 2.4-S4, TS 2.4-S5

Uso: `uv run python app1_agente_unico/06_mcp_config.py --parte conexion|recursos|descripcion [--anti sin_recursos|descripcion_minima] [--repeat N]`
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claude_agent_sdk import ClaudeAgentOptions, query  # noqa: E402

from app1_agente_unico.servers.mesa import build_server, make_tools, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import copy_to_temp, load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

PARTS = ["conexion", "recursos", "descripcion"]
# Cada variante anti-patrón pertenece a una parte: `--anti` solo vale con la suya.
ANTI_PART = {"sin_recursos": "recursos", "descripcion_minima": "descripcion"}
SERVERS_DIR = ROOT / "app1_agente_unico" / "servers"
# Token sintético: sirve solo para comprobar que `${CCARF_DEMO_TOKEN}` se expandió. No es una credencial.
DEMO_TOKEN = "token-sintetico-ccarf"
# Tools de las que el SDK dispone para los resources (nombres leídos de la CLI fijada, no supuestos).
RESOURCE_TOOLS = ["ListMcpResourcesTool", "ReadMcpResourceTool"]
CATALOGO_TOOLS = ["search_kb", "get_article", "token_status"]


# --- `.mcp.json` del proyecto (2.4-K1, 2.4-K2, 2.4-S1) -----------------------------------


def stdio_server(script: str, root: Path) -> dict[str, Any]:
    # `uv run --no-sync --project <raíz>`: el servidor se lanza con el entorno del proyecto, sin
    # reinstalar nada, aunque el `cwd` del agente sea otro directorio.
    return {"command": "uv", "args": ["run", "--no-sync", "--project", str(root), "python", str(SERVERS_DIR / script)]}


def build_mcp_json(root: Path, *, descripcion: str | None = None) -> dict[str, Any]:
    catalogo = stdio_server("catalogo_stdio.py", root)
    # El archivo lleva la VARIABLE, nunca el valor: el secreto no se versiona. La expansión la hace la CLI
    # al conectar, con el entorno del proceso (aquí, el `env` de las opciones).
    catalogo["env"] = {"CATALOGO_TOKEN": "${CCARF_DEMO_TOKEN}"}
    if descripcion:
        catalogo["env"]["CATALOGO_DESCRIPCION"] = descripcion
    return {"mcpServers": {"catalogo": catalogo, "inventario": stdio_server("inventario_stdio.py", root)}}


def write_mcp_json(cwd: Path, *, descripcion: str | None = None) -> None:
    (cwd / ".mcp.json").write_text(json.dumps(build_mcp_json(ROOT, descripcion=descripcion), indent=2), encoding="utf-8")


def user_scope_command(root: Path) -> str:
    """Comando que registraría el servidor en el ámbito de usuario (2.4-K1, 2.4-S2). Solo se imprime."""
    # Se imprime y no se ejecuta: `~/.claude.json` es personal y este módulo no lo toca. Un servidor
    # experimental de una persona va ahí; el compartido del equipo, en `.mcp.json`.
    script = SERVERS_DIR / "catalogo_stdio.py"
    return f"claude mcp add --scope user catalogo-personal -e CATALOGO_TOKEN=<tu-token> -- uv run --no-sync --project {root} python {script}"


def write_articles(cwd: Path) -> None:
    """Los artículos como archivos del `cwd`, para que `Grep` y `Read` también puedan encontrarlos (2.4-S3)."""
    folder = cwd / "articulos"
    folder.mkdir(exist_ok=True)
    for article in load("articulos_kb.json"):
        text = (
            f"# {article['title']}\n\ncategoría: {article['category']}\nactualizado: {article['updated_at']}\n"
            f"superseded_by: {article['superseded_by']}\n\n{article['body']}\n"
        )
        (folder / f"{article['article_id']}.md").write_text(text, encoding="utf-8")


# --- Medida --------------------------------------------------------------------------------


def data_calls(rec: RunRecord) -> int:
    """Llamadas de datos al catálogo (búsqueda y lectura por ID): las exploratorias de la parte `recursos`."""
    return sum(c.name in ("mcp__catalogo__search_kb", "mcp__catalogo__get_article") for c in rec.tool_calls)


def resource_calls(rec: RunRecord) -> int:
    return sum(c.name in RESOURCE_TOOLS for c in rec.tool_calls)


def grep_vs_mcp(rec: RunRecord) -> tuple[int, int]:
    """(llamadas a `Grep`, llamadas a `search_kb` del servidor MCP)."""
    return (
        sum(c.name == "Grep" for c in rec.tool_calls),
        sum(c.name == "mcp__catalogo__search_kb" for c in rec.tool_calls),
    )


def tools_by_server(tools: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Tools MCP agrupadas por servidor (2.4-K3) y, aparte, las demás."""
    servers: dict[str, list[str]] = {}
    builtins = []
    for name in tools:
        if name.startswith("mcp__"):
            _, server, tool = name.split("__", 2)
            servers.setdefault(server, []).append(tool)
        else:
            builtins.append(name)
    return {server: sorted(names) for server, names in servers.items()}, builtins


def servers_without_tools(init: dict[str, Any]) -> list[str]:
    """Servidores conectados cuyas tools no figuran en `init`: la lista de tools es parcial."""
    listed = {name.split("__", 2)[1] for name in init.get("tools", []) if name.startswith("mcp__")}
    connected = [s["name"] for s in init.get("mcp_servers", []) if s.get("status") == "connected"]
    return [name for name in connected if name not in listed]


def token_received(rec: RunRecord) -> bool | None:
    """¿Dijo el servidor que recibió el token? None si el agente no llamó a `token_status`."""
    for call in rec.tool_calls:
        if call.name == "mcp__catalogo__token_status":
            try:
                return bool(json.loads(call.result_text or "").get("token_recibido"))
            except (json.JSONDecodeError, AttributeError):
                return None
    return None


# --- Configuración -------------------------------------------------------------------------

BASE_SYSTEM = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Atiende la petición con tus tools y "
    "responde en español y de forma breve."
)
RESOURCES_HINT = (
    " Los servidores MCP exponen catálogos de contenido como resources: consúltalos con ListMcpResourcesTool "
    "y ReadMcpResourceTool antes de buscar."
)
PROMPTS = {
    "conexion": (
        f"Llama a token_status, a stock_equipo con tipo portatil y a get_ticket con el ticket "
        f"{load('tickets.json')[0]['ticket_id']}. Dime los tres resultados."
    ),
    "recursos": "¿Qué artículos hay en el catálogo de la base de conocimiento? Dame los IDs y títulos de todos.",
    "descripcion": "¿Qué artículo vigente explica cómo arreglar una VPN inestable desde casa? Dame su ID y los pasos.",
}


def build_options(part: str, anti: str | None, *, cwd: Path, budget: float, model: str) -> ClaudeAgentOptions:
    if part not in PARTS:
        raise ValueError(f"parte desconocida: {part}")
    catalogo = [f"mcp__catalogo__{n}" for n in CATALOGO_TOOLS]
    inventario = ["mcp__inventario__stock_equipo"]
    mcp_servers: dict[str, Any] = {}
    system = BASE_SYSTEM
    if part == "conexion":
        write_mcp_json(cwd)
        tools: list[str] = []
        # Tres servidores a la vez: dos stdio por `.mcp.json` y uno en proceso por `mcp_servers`.
        mcp_servers = {"mesa": build_server("acotado")}
        allowed = catalogo + inventario + [tool_name(t.name) for t in make_tools("acotado")]
    elif part == "recursos":
        write_mcp_json(cwd)
        tools = [] if anti == "sin_recursos" else list(RESOURCE_TOOLS)
        allowed = catalogo + inventario + tools
        if anti != "sin_recursos":
            system += RESOURCES_HINT  # la aplicación avisa de que existen los resources
    else:
        write_mcp_json(cwd, descripcion="minima" if anti == "descripcion_minima" else None)
        write_articles(cwd)
        tools = ["Grep", "Read"]  # las integradas que compiten con la tool MCP
        allowed = tools + ["mcp__catalogo__search_kb", "mcp__catalogo__get_article"]
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=system,
        mcp_servers=mcp_servers,
        # Excepción del aislamiento: el agente debe leer el `.mcp.json` del `cwd`. `["project"]` carga solo
        # el ámbito de proyecto (el `.mcp.json` temporal), no el de usuario ni el del repositorio.
        setting_sources=["project"],
        cwd=str(cwd),
        tools=tools,
        allowed_tools=allowed,
        permission_mode="dontAsk",
        env={"CCARF_DEMO_TOKEN": DEMO_TOKEN},
        max_turns=12,  # red de seguridad: la exploración a ciegas necesita muchas llamadas
    )


def expectation(part: str, anti: str | None) -> str:
    return {
        ("conexion", None): "las tools de los tres servidores a la vez, el token recibido y una llamada ok a cada uno",
        ("recursos", None): "ListMcpResourcesTool y ReadMcpResourceTool sobre el catálogo, y 0–1 llamadas exploratorias",
        ("recursos", "sin_recursos"): "muchas llamadas exploratorias (search_kb y get_article repetidas) hasta dar con todos",
        ("descripcion", None): "usa search_kb del servidor MCP (ranking y filtro de obsoletos) y no Grep",
        # La guía dice que con una descripción mínima el agente prefiere `Grep`. Con Haiku 5.5 y 4.5 no se
        # observó diferencia (docs/hallazgos.md): el modelo usa `search_kb` igualmente si el nombre lo sugiere.
        ("descripcion", "descripcion_minima"): "según la guía, prefiere Grep; con modelos recientes la diferencia es pequeña o nula",
    }[(part, anti)]


def report(part: str, rec: RunRecord) -> None:
    if part == "conexion":
        servers, builtins = tools_by_server(rec.init.get("tools", []))
        print(f"[medida] tools por servidor={servers} · otras={builtins}")
        partial = servers_without_tools(rec.init)
        if partial:
            # Observado (1 de 4 ejecuciones): `init` se emite antes de que un servidor stdio termine de cargar
            # sus tools. Las llamadas de la ejecución sí lo usan: la lista de `init` no es la verdad completa.
            print(f"[aviso] lista de tools parcial en init: sin tools de {partial} (conectados); se usan igualmente")
        print(f"[medida] token recibido={token_received(rec)} · coste=${rec.cost_usd or 0:.4f}")
    elif part == "recursos":
        print(f"[medida] llamadas exploratorias (search_kb/get_article)={data_calls(rec)} · llamadas a resources={resource_calls(rec)} · coste=${rec.cost_usd or 0:.4f}")
    else:
        grep, mcp = grep_vs_mcp(rec)
        print(f"[medida] Grep={grep} · search_kb (MCP)={mcp} · coste=${rec.cost_usd or 0:.4f}")


# --- Ejecución -----------------------------------------------------------------------------


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=list(ANTI_PART))
    parser.add_argument("--parte", choices=PARTS, required=True)
    args = parser.parse_args()
    if args.anti and ANTI_PART[args.anti] != args.parte:
        parser.error(f"--anti {args.anti} es de la parte {ANTI_PART[args.anti]}, no de {args.parte}")
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")
    if args.parte == "conexion":
        # Ámbito de usuario: se muestra, no se ejecuta (2.4-K1, 2.4-S2).
        print(f"[ámbito usuario] no se ejecuta; registraría un servidor personal en ~/.claude.json con:\n  {user_scope_command(ROOT)}")

    for run in range(1, args.repeat + 1):
        # Directorio temporal nuevo por ejecución: el `.mcp.json` se escribe en él, nunca en el repositorio.
        cwd = copy_to_temp("repo_mesa")
        options = build_options(args.parte, args.anti, cwd=cwd, budget=budget / args.repeat, model=model)
        print(f"\n=== ejecución {run}/{args.repeat} · {args.parte} · variante {args.anti or 'correcta'} ===")
        print(f"[esperado] {expectation(args.parte, args.anti)}")
        rec = await record(query(prompt=PROMPTS[args.parte], options=options), echo=args.parte == "conexion")
        report(args.parte, rec)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
