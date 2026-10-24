"""Credencial y versiones en uso (roadmap §5 y §11.1).

PROPÓSITO: detectar qué credencial va a usar la ejecución y mostrarla junto con
las versiones del SDK y de la CLI incluida, sin enseñar nunca la clave.

POR QUÉ EXISTE: las mismas opciones se comportan distinto según la credencial
(con suscripción no hay Messages API ni Batches) y una variable vacía en el
entorno puede tapar otra válida. Saber qué se usa es el primer paso de la
verificación, antes de interpretar ninguna ejecución.

QUÉ NO HACE: no valida la clave contra la API ni guarda nada. Lo que la CLI
usa de verdad lo confirma `apiKeySource` en la línea `init` de `recorder.py`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import __version__ as SDK_VERSION
from claude_agent_sdk._cli_version import __cli_version__ as CLI_VERSION

ROOT = Path(__file__).resolve().parent.parent
API_KEY = "ANTHROPIC_API_KEY"
OAUTH_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"


@dataclass
class CredentialInfo:
    source: str
    api_key_available: bool
    sdk_version: str = SDK_VERSION
    cli_version: str = CLI_VERSION


def read_dotenv(path: Path) -> dict[str, str]:
    """Lee un `.env` mínimo (`KEY=VALUE`, comentarios con `#`, comillas opcionales)."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def drop_empty(*names: str) -> list[str]:
    """Quita del entorno las variables vacías y devuelve cuáles eran.

    La CLI hereda `os.environ` tal cual: una variable vacía le llegaría como
    definida. Se elimina para que no tape a la siguiente fuente.
    """
    dropped = [name for name in names if name in os.environ and not os.environ[name].strip()]
    for name in dropped:
        del os.environ[name]
    return dropped


def detect(root: Path = ROOT) -> CredentialInfo:
    """Resuelve la credencial: entorno > `.env` > token OAuth > login de claude.ai."""
    dropped = drop_empty(API_KEY, OAUTH_TOKEN)
    note = f" (descartadas por vacías: {', '.join(dropped)})" if dropped else ""

    if os.environ.get(API_KEY):
        return CredentialInfo(f"{API_KEY} del entorno{note}", True)

    # El `.env` no pisa el entorno: solo rellena lo que falta. Se copia a
    # `os.environ` para que lo hereden la CLI y el cliente `anthropic`.
    dotenv_key = read_dotenv(root / ".env").get(API_KEY, "")
    if dotenv_key:
        os.environ[API_KEY] = dotenv_key
        return CredentialInfo(f"{API_KEY} de .env{note}", True)

    if os.environ.get(OAUTH_TOKEN):
        return CredentialInfo(f"{OAUTH_TOKEN} (suscripción){note}", False)
    return CredentialInfo(f"ninguna variable; la CLI usará el login de claude.ai si existe{note}", False)


def describe(info: CredentialInfo | None = None) -> str:
    """Una línea con origen y versiones. Nunca incluye la clave."""
    info = info or detect()
    return f"credencial: {info.source} · claude-agent-sdk {info.sdk_version} · CLI {info.cli_version}"


def require_api_key(root: Path = ROOT) -> None:
    """Corta con un error claro si no hay API key.

    La Messages API (`tool_choice`, Batches) solo admite API key; con la
    credencial de una suscripción solo funcionan los módulos del Agent SDK.
    """
    info = detect(root)
    if not info.api_key_available:
        raise RuntimeError(f"este módulo necesita {API_KEY} (entorno o .env); detectado: {info.source}")


if __name__ == "__main__":
    print(describe())
