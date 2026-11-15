"""Argumentos comunes de los módulos de app (roadmap §2 y §13).

PROPÓSITO: construir el `argparse` de cada módulo con las tres opciones que
comparten todos: `--anti [variante]` (par anti-patrón / correcto), `--repeat N`
(medir una tasa en varias ejecuciones) y `--budget` (bajar el tope de coste
para una prueba barata), y calcular el presupuesto efectivo.

POR QUÉ EXISTE: repetir el mismo `argparse` en 8 módulos invita a que cada uno
lo haga a su manera. El módulo puede añadir sus propias opciones al parser
devuelto (`--parte` en app3/02).

QUÉ NO HACE: no tiene `--model`, para que el `.env` sea siempre la fuente que
manda (ver `harness/config.py`), y `--budget` nunca sube el tope resuelto: una
prueba puntual no puede gastar más de lo que fija el repositorio. No esconde
ninguna opción del agente: eso sigue visible en el módulo.
"""

import argparse

from harness import credentials
from harness.config import describe, report_model, resolve_budget


def positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("debe ser un importe positivo")
    return value


def positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("debe ser un entero positivo")
    return value


def build_parser(
    description: str,
    *,
    anti_variants: list[str] | None = None,
    parts: list[str] | None = None,
    anti_by_part: dict[str, list[str]] | None = None,
    default_part: str | None = None,
    model_roles: list[str] | None = None,
    default_role: str | None = None,
    role_flag: str = "--rol-modelo",
    part_help: str | None = None,
    role_help: str | None = None,
) -> argparse.ArgumentParser:
    """Parser con `--budget`, `--repeat` y, según se pida, `--anti`, `--parte` y `--rol-modelo`."""
    # Las definiciones incoherentes son errores de programación, no de uso.
    if anti_variants and anti_by_part:
        raise ValueError("anti_variants y anti_by_part son excluyentes")
    if anti_by_part and not parts:
        raise ValueError("anti_by_part necesita parts")
    if anti_by_part and set(anti_by_part) - set(parts):
        raise ValueError("anti_by_part tiene una parte que no está en parts")
    if default_part is not None and default_part not in (parts or []):
        raise ValueError(f"default_part desconocida: {default_part}")
    if default_role is not None and default_role not in (model_roles or []):
        raise ValueError(f"default_role desconocido: {default_role}")

    parser = argparse.ArgumentParser(description=description)
    if parts:
        parser.add_argument(
            "--parte",
            choices=parts,
            default=default_part,
            required=default_part is None,
            # El módulo puede conservar su propio texto de ayuda («» = sin texto, como un `add_argument` sin
            # `help`); si no lo da, uno genérico con las partes.
            help=f"parte del módulo ({', '.join(parts)})" if part_help is None else part_help,
        )
    if anti_by_part:
        # La validación depende de la parte elegida: se hace tras el análisis, no con `choices`.
        # La ayuda lista las variantes de cada parte, como hacía `choices` en el `--help` del módulo.
        by_part_help = "; ".join(f"{part}: {', '.join(names)}" for part, names in anti_by_part.items())
        parser.add_argument(
            "--anti", nargs="?", const="", help=f"ejecuta el anti-patrón de la parte elegida ({by_part_help}); sin valor: el primero de esa parte"
        )
        original_parse = parser.parse_args

        def parse_args(argv=None, namespace=None):
            args = original_parse(argv, namespace)
            if args.anti is None:
                return args
            valid = anti_by_part.get(args.parte, [])
            if args.anti == "":
                if not valid:
                    parser.error(f"la parte {args.parte} no tiene variantes de --anti")
                args.anti = valid[0]
            elif args.anti not in valid:
                every = "; ".join(f"{part}: {', '.join(names)}" for part, names in anti_by_part.items())
                parser.error(f"--anti {args.anti} no vale en la parte {args.parte}. Variantes válidas: {every}")
            return args

        parser.parse_args = parse_args
    elif anti_variants:
        # `--anti` sin valor elige la primera variante: la que el módulo
        # considera el anti-patrón principal.
        parser.add_argument(
            "--anti",
            nargs="?",
            const=anti_variants[0],
            choices=anti_variants,
            help=f"ejecuta el anti-patrón ({', '.join(anti_variants)}); sin valor: {anti_variants[0]}",
        )
    else:
        parser.set_defaults(anti=None)
    if model_roles:
        parser.add_argument(
            role_flag,
            choices=model_roles,
            default=default_role or model_roles[0],
            # Igual que `--parte`: el texto propio del módulo (qué modelo es cada rol) se conserva.
            help=f"rol cuyo modelo se usa ({', '.join(model_roles)})" if role_help is None else role_help,
        )
    parser.add_argument("--repeat", type=positive_int, default=1, help="número de ejecuciones (por defecto 1)")
    parser.add_argument("--budget", type=positive_float, help="baja el tope en USD; nunca lo sube")
    return parser


def effective_budget(requested: float | None, resolved: float, origin: str) -> tuple[float, str, str | None]:
    """Devuelve (tope, origen, aviso). El tope es `min(--budget, resuelto)`."""
    if requested is None or requested == resolved:
        return resolved, origin, None
    if requested < resolved:
        return requested, "--budget", None
    return resolved, origin, f"--budget {requested} no sube el tope: se usa {resolved} ({origin})"


def report_budget(requested: float | None, kind: str) -> float:
    """Resuelve el presupuesto de `kind`, imprime `[presupuesto]` (y el aviso) y devuelve el tope efectivo."""
    resolved, origin = resolve_budget(kind)
    value, final_origin, warning = effective_budget(requested, resolved, origin)
    if warning:
        print(f"[aviso] {warning}")
    print(describe("presupuesto", valor=value, origen=final_origin))
    return value


def preamble(
    requested_budget: float | None, *roles: str, budget_kind: str | None = None, require_api_key: bool = False
) -> tuple[list[str], float]:
    """Imprime credencial, modelo de cada rol y presupuesto; devuelve (modelos, tope efectivo)."""
    if not roles:
        raise ValueError("preamble necesita al menos un rol")
    print(credentials.describe())
    if require_api_key:
        credentials.require_api_key()
    models = [report_model(role) for role in roles]
    return models, report_budget(requested_budget, budget_kind or roles[0])
