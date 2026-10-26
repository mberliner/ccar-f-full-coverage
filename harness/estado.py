"""Estado personal fuera de git: perfiles y plantillas.

PROPÓSITO: resolver dónde vive el estado de estudio de una persona (fallos,
sesiones, práctica propia, *scratchpad*) y crearlo a partir de las plantillas
versionadas de `plantillas/estado/`, sin pisar nunca lo que ya exista.

POR QUÉ EXISTE: el repositorio se comparte y el estado de estudio no. Mezclarlos
confunde a quien clona y ensucia el historial. Es el patrón de `.env` y
`.claude/settings.local.json` (plantilla versionada, copia local ignorada)
llevado a los registros, con un perfil por persona o por intento para que un
solo clon sirva a varios. La construcción del proyecto (`CONCEPTOS.md`, hitos de
`NOTAS.md`) sigue versionada porque `tests/test_una_vez.py` la contrasta con el
código.

QUÉ NO HACE: no lee ni migra contenido ya escrito, no sincroniza el estado entre
máquinas ni lo versiona, y resolver la ruta no crea nada: solo `init` escribe.
El perfil y la base siguen el orden de `harness/config.py` (argumento, `.env`,
entorno, defecto). Un perfil no puede salir del directorio base y la base solo
puede ser `estado/` o una ruta absoluta: una carpeta relativa con otro nombre
quedaría dentro del clon sin que `.gitignore` la cubriera.
"""

import argparse
import re
import shutil
from pathlib import Path

from harness.config import lookup
from harness.credentials import ROOT

PROFILE_VAR = "CCARF_PERFIL"
BASE_VAR = "CCARF_ESTADO_DIR"
DEFAULT_PROFILE = "default"
DEFAULT_BASE = "estado"
TEMPLATES = ROOT / "plantillas" / "estado"

# Un perfil es un único nombre de carpeta: sin separadores, sin «..» ni punto inicial.
PROFILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def resolve_profile(profile: str | None, root: Path) -> tuple[str, str]:
    """Perfil y su origen (`argumento`, `.env`, `entorno` o `defecto`). Corta si no es un nombre válido."""
    if profile is not None:
        name, origin = profile, "argumento"
    else:
        found = lookup(PROFILE_VAR, root)
        name, origin = found if found else (DEFAULT_PROFILE, "defecto")
    if not PROFILE_RE.fullmatch(name):
        label = PROFILE_VAR if origin in (".env", "entorno") else origin
        raise ValueError(f"perfil {name!r} inválido ({label}): usa letras, números, «_» o «-», sin empezar por símbolo")
    return name, origin


def resolve_base(root: Path) -> tuple[Path, str]:
    """Directorio base y su origen. Solo `estado` (desde la raíz del clon) o una ruta absoluta."""
    found = lookup(BASE_VAR, root)
    value, origin = found if found else (DEFAULT_BASE, "defecto")
    base = Path(value)
    if base.is_absolute():
        return base, origin
    # `.gitignore` solo cubre `/estado/`; otra carpeta relativa dentro del clon la vería git.
    if value.strip("/\\") != DEFAULT_BASE:
        raise ValueError(f"{BASE_VAR}={value!r} ({origin}): usa una ruta absoluta o «{DEFAULT_BASE}»")
    return root / DEFAULT_BASE, origin


def state_dir(profile: str | None = None, *, root: Path = ROOT) -> tuple[Path, str]:
    """Carpeta del estado del perfil y de dónde sale cada parte. No crea nada."""
    name, profile_origin = resolve_profile(profile, root)
    base, base_origin = resolve_base(root)
    return base / name, f"perfil={profile_origin} base={base_origin}"


def init_state(
    profile: str | None = None, *, root: Path = ROOT, templates: Path = TEMPLATES
) -> tuple[list[Path], list[Path]]:
    """Copia las plantillas que falten al estado del perfil y devuelve (creados, respetados)."""
    target, _ = state_dir(profile, root=root)
    if not templates.is_dir():
        raise FileNotFoundError(f"faltan las plantillas en {templates}: ¿el clon está completo?")
    target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    kept: list[Path] = []
    for template in sorted(templates.iterdir()):
        destination = target / template.name
        # Lo que ya existe es trabajo de la persona: nunca se sobrescribe.
        if destination.exists():
            kept.append(destination)
            continue
        shutil.copyfile(template, destination)
        created.append(destination)
    return created, kept


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Estado personal fuera de git (perfiles y plantillas).")
    parser.add_argument("action", choices=["init", "where"], help="`init` crea lo que falte; `where` solo muestra la ruta")
    parser.add_argument("--perfil", dest="profile", help=f"nombre del perfil (por defecto {PROFILE_VAR} o «{DEFAULT_PROFILE}»)")
    args = parser.parse_args(argv)

    # Un perfil o una base inválidos, o un clon sin plantillas, son errores de uso: mensaje, no traza.
    try:
        target, origin = state_dir(args.profile)
        print(f"[estado] ruta={target} origen=({origin})")
        if args.action == "init":
            created, kept = init_state(args.profile)
            for path in created:
                print(f"[estado] creado {path.name}")
            for path in kept:
                print(f"[estado] respetado {path.name} (ya existía)")
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
