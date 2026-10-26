"""Servidor MCP stdio `inventario` (app1/06): el segundo servidor del `.mcp.json`.

PROPÓSITO: aportar una tool (`stock_equipo`) de un segundo servidor, para que
la línea `[contexto]` de app1/06 muestre las tools de varios servidores a la
vez, cada una con su prefijo `mcp__<servidor>__`.

POR QUÉ EXISTE: descubrir las tools de todos los servidores configurados
necesita al menos dos. Este es pequeño a propósito.

QUÉ NO HACE: no lee el inventario real ni el paquete `legacy_inventario`; las
cifras salen de una tabla fija sintética. No usa token ni resources.

Uso: `python servers/inventario_stdio.py` (lo lanza `.mcp.json`).
"""

import sys
from pathlib import Path

# Proyecto virtual: al lanzarse por ruta, la raíz no está en el path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.mcpserver import MCPServer  # noqa: E402

SERVER_NAME = "inventario"
STOCK = {"portatil": 6, "monitor": 14, "movil": 3, "periferico": 41}


def build_server() -> MCPServer:
    server = MCPServer(SERVER_NAME)

    def stock_equipo(tipo: str) -> dict[str, object]:
        return {"tipo": tipo, "disponibles": STOCK.get(tipo, 0)}

    server.tool(
        name="stock_equipo",
        description="Devuelve cuántas unidades hay disponibles de un tipo de equipo (portatil, monitor, movil o periferico). "
        "Un tipo desconocido devuelve 0.",
    )(stock_equipo)
    return server


if __name__ == "__main__":
    build_server().run("stdio")
