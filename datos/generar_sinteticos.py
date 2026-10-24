"""Generador de los datos sintéticos de la mesa de ayuda TI (roadmap §4.1 y §5).

PROPÓSITO: crear `datos/sinteticos/` (usuarios, tickets y artículos de la base
de conocimiento) de forma determinista: misma semilla y misma fecha de
referencia, mismos bytes en cada ejecución.

POR QUÉ EXISTE: es la única vía para crear o cambiar los datos de prueba. Los
archivos generados se versionan para que los módulos funcionen sin ejecutar
nada, y `--check` (también en `tests/test_datos_sinteticos.py`) detecta
cualquier edición a mano. El hook `PreToolUse` de la capa meta bloqueará además
editar esa carpeta directamente.

QUÉ NO HACE: no usa datos reales ni nombres de empresas, y los correos van al
dominio reservado `.test`. Las etiquetas de lo que debería pasar con cada
ticket van en un archivo aparte (`tickets_etiquetas.json`): el agente nunca
debe verlas, solo el módulo que puntúa. `legacy_inventario/` es código Python
de ejemplo para app3/02, sin tests a propósito. Los conjuntos de las entregas 2 y 3
(documentos de extracción, inventario de 40 campos, informes con cifras en
conflicto) se añaden aquí en el mismo cambio que su módulo.

Uso: `uv run python datos/generar_sinteticos.py [--check]`
"""

import argparse
import json
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "sinteticos"
SEED = 20261024
# Fecha fija: nunca `date.today()`, o los datos cambiarían cada día.
REFERENCE_DATE = date(2026, 10, 1)
EMAIL_DOMAIN = "mesa-ejemplo.test"

# Umbral de la regla de negocio del dominio. Equivale al «reembolso sobre 500»
# de los escenarios del examen (roadmap §12, tabla de equivalencias).
REIMBURSEMENT_THRESHOLD_EUR = 500

FIRST_NAMES = [
    "Laura", "Javier", "Marta", "Andrés", "Lucía", "Diego", "Elena", "Pablo",
    "Carmen", "Sergio", "Irene", "Raúl", "Nuria", "Óscar", "Beatriz", "Hugo",
]
LAST_NAMES = [
    "Gómez", "Navarro", "Ruiz", "Ortega", "Delgado", "Castro", "Vidal", "Moreno",
    "Iglesias", "Prieto", "Serrano", "Molina", "Rubio", "Herrero", "Blanco", "Cano",
]
DEPARTMENTS = ["Finanzas", "Ventas", "Operaciones", "Personas", "Ingeniería", "Legal"]
CATEGORIES = ["acceso", "hardware", "software", "red", "licencias", "gastos"]

# Estados y fechas en formatos mezclados a propósito: el sistema de origen no es
# homogéneo y la normalización la hará un hook `PostToolUse` (ver TS 1.5).
STATUS_VARIANTS = {
    "open": ["OPEN", "abierto", "Open"],
    "in_progress": ["IN_PROGRESS", "en curso", "in-progress"],
    "resolved": ["RESOLVED", "resuelto", "Closed-Resolved"],
}

# Plantillas por categoría para los tickets ordinarios (un solo asunto).
SINGLE_ISSUE = {
    "acceso": [
        "No puedo entrar en el portal de nóminas desde esta mañana.",
        "Se me ha bloqueado la cuenta tras varios intentos de contraseña.",
        "Necesito acceso de lectura a la carpeta compartida de {dept}.",
    ],
    "hardware": [
        "El portátil se apaga solo cuando lleva un rato con la batería.",
        "La pantalla externa no se detecta en la base de conexión.",
        "El teclado tiene varias teclas que no responden.",
    ],
    "software": [
        "La aplicación de gastos se cierra al adjuntar un recibo.",
        "El cliente de correo no sincroniza la carpeta de enviados.",
        "No consigo instalar la actualización del navegador corporativo.",
    ],
    "red": [
        "La VPN se desconecta cada pocos minutos desde casa.",
        "En la sala de reuniones 3 no hay wifi.",
        "La conexión a la impresora de planta va muy lenta.",
    ],
    "licencias": [
        "Me caduca la licencia del editor de diagramas la semana que viene.",
        "Necesito una licencia de la herramienta de análisis para un proyecto.",
    ],
}

# Casos de escalamiento: el texto lleva la señal; la etiqueta dice qué debería
# hacer el agente (ver TS 5.2). Sentimiento negativo por sí solo no es criterio.
ESCALATION_CASES = [
    ("explicit_human", "acceso", "Quiero hablar con una persona, no con un bot. Tengo la cuenta bloqueada."),
    ("explicit_human", "software", "Por favor, pásame con alguien del equipo de soporte directamente."),
    ("frustration", "red", "Es la tercera vez esta semana que la VPN se cae y pierdo el trabajo. Estoy harto."),
    ("frustration", "hardware", "Llevo días sin poder usar el portátil y nadie me dice nada. Esto es un desastre."),
    ("policy_gap", "hardware", "En otra empresa dan monitores de 34 pulgadas a todos. ¿Me podéis dar uno igual?"),
    ("policy_gap", "licencias", "Un proveedor me ofrece la licencia más barata; ¿podéis comprarla por fuera del catálogo?"),
    ("ambiguous_user", "acceso", "Soy Laura Gómez y necesito que me restablezcáis la contraseña."),
]

# Tickets con varios asuntos en un mismo mensaje (ver TS 1.4 y TS 5.1).
MULTI_CONCERN_CASES = [
    (["hardware", "acceso"], "El portátil nuevo no arranca y, además, sigo sin acceso al portal de nóminas."),
    (["red", "licencias", "gastos"], "La VPN no conecta, me caduca la licencia del editor y quiero saber cómo va el reembolso del ratón."),
    (["software", "acceso"], "El correo no sincroniza y tampoco puedo entrar en la carpeta compartida de Ventas."),
]

# Reembolsos de material comprado por el empleado: por debajo, en y sobre el
# umbral, para probar el límite exacto (`>` frente a `>=`).
REIMBURSEMENT_AMOUNTS = [39.9, 120.0, 499.99, 500.0, 500.01, 845.5, 1290.0]

KB_TOPICS = [
    ("acceso", "Restablecer la contraseña corporativa", "Pasos para restablecer la contraseña desde el portal de autoservicio."),
    ("acceso", "Desbloquear una cuenta tras intentos fallidos", "La cuenta se desbloquea sola a los 30 minutos o la desbloquea soporte tras verificar la identidad."),
    ("acceso", "Solicitar acceso a una carpeta compartida", "La persona responsable de la carpeta aprueba la solicitud desde el catálogo."),
    ("hardware", "Diagnóstico de batería del portátil", "Ejecutar el diagnóstico del fabricante y adjuntar el informe al ticket."),
    ("hardware", "Pantalla externa no detectada", "Revisar el cable, actualizar el firmware de la base y probar otro puerto."),
    ("hardware", "Política de monitores y periféricos", "El catálogo incluye monitores de 24 y 27 pulgadas; otros modelos requieren aprobación de la dirección del área."),
    ("software", "La aplicación de gastos se cierra al adjuntar", "Reducir el tamaño del recibo por debajo de 5 MB o usar PDF."),
    ("software", "Sincronización del cliente de correo", "Reconstruir el perfil local; la carpeta de enviados se recupera del servidor."),
    ("red", "VPN inestable desde casa", "Cambiar al perfil TCP de la VPN y comprobar la red doméstica."),
    ("red", "VPN: perfil antiguo (obsoleto)", "Instrucciones del perfil UDP retirado. Sustituido por «VPN inestable desde casa»."),
    ("red", "Wifi en salas de reuniones", "Las salas usan la red de invitados con portal cautivo."),
    ("licencias", "Renovar una licencia de software", "Las renovaciones se piden 15 días antes de caducar desde el catálogo."),
    ("licencias", "Compras fuera de catálogo", "No se compran licencias fuera del catálogo; se puede proponer una alta nueva."),
    ("gastos", "Reembolso de material comprado por el empleado", f"Hasta {REIMBURSEMENT_THRESHOLD_EUR} EUR lo aprueba soporte; por encima, requiere aprobación de Finanzas."),
    ("gastos", "Plazos de pago de reembolsos", "Los reembolsos aprobados se pagan en la nómina siguiente."),
]


def build_users(rng: random.Random) -> list[dict]:
    users = []
    for index in range(40):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        users.append({"user_id": f"EMP-{1001 + index}", "name": f"{first} {last}", "department": rng.choice(DEPARTMENTS)})
    # Dos homónimos garantizados en departamentos distintos: el agente debe pedir
    # un identificador en vez de elegir uno al azar (ver TS 5.2).
    users[3].update(name="Laura Gómez", department="Finanzas")
    users[17].update(name="Laura Gómez", department="Ventas")
    for user in users:
        user["email"] = f"{user['user_id'].lower()}@{EMAIL_DOMAIN}"
    # Fuera de los dos homónimos fijados no debe haber otra «Laura Gómez».
    for index, user in enumerate(users):
        if user["name"] == "Laura Gómez" and index not in (3, 17):
            user["name"] = "Laura Gómez Prieto"
    return users


def format_date(rng: random.Random, moment: datetime) -> str | int:
    """Devuelve la fecha en uno de los tres formatos que mezcla el sistema de origen."""
    style = rng.randrange(3)
    if style == 0:
        return moment.isoformat()
    if style == 1:
        return moment.strftime("%d/%m/%Y %H:%M")
    return int(moment.timestamp())


def make_ticket(rng: random.Random, user: dict, category: str, text: str) -> dict:
    status = rng.choice(list(STATUS_VARIANTS))
    day = REFERENCE_DATE - timedelta(days=rng.randrange(1, 30))
    moment = datetime.combine(day, time(rng.randrange(8, 19), rng.randrange(60)), tzinfo=timezone.utc)
    return {
        "ticket_id": None,  # se asigna tras barajar (build_tickets)
        "user_id": user["user_id"],
        "category": category,
        "status": rng.choice(STATUS_VARIANTS[status]),
        "created_at": format_date(rng, moment),
        "description": text,
        "amount_eur": None,
    }


def build_tickets(rng: random.Random, users: list[dict]) -> tuple[list[dict], dict]:
    cases: list[tuple[dict, dict]] = []

    def add(category: str, text: str, label: dict, user: dict | None = None) -> dict:
        ticket = make_ticket(rng, user or rng.choice(users), category, text)
        cases.append((ticket, label))
        return ticket

    for _ in range(40):
        category = rng.choice([c for c in CATEGORIES if c != "gastos"])
        user = rng.choice(users)
        text = rng.choice(SINGLE_ISSUE[category]).format(dept=user["department"])
        add(category, text, {"expected_action": "resolve", "concerns": [category]}, user)

    for kind, category, text in ESCALATION_CASES:
        action = {
            "explicit_human": "escalate_now",
            "frustration": "offer_resolution",
            "policy_gap": "escalate_policy_gap",
            "ambiguous_user": "ask_identifier",
        }[kind]
        # El homónimo no lleva user_id fiable: el agente solo tiene el nombre.
        ticket = add(category, text, {"expected_action": action, "concerns": [category]})
        if kind == "ambiguous_user":
            ticket["user_id"] = None

    for concerns, text in MULTI_CONCERN_CASES:
        add(concerns[0], text, {"expected_action": "resolve", "concerns": concerns})

    for amount in REIMBURSEMENT_AMOUNTS:
        over = amount > REIMBURSEMENT_THRESHOLD_EUR
        ticket = add(
            "gastos",
            f"Compré material para el puesto por {amount:.2f} EUR y pido el reembolso.",
            {"expected_action": "escalate_finance" if over else "approve_reimbursement", "concerns": ["gastos"]},
        )
        ticket["amount_eur"] = amount

    # Se baraja antes de numerar: si no, los casos especiales tendrían
    # identificadores consecutivos y el número delataría el caso.
    rng.shuffle(cases)
    for number, (ticket, _) in enumerate(cases, start=4001):
        ticket["ticket_id"] = f"TCK-{number}"
    return [ticket for ticket, _ in cases], {ticket["ticket_id"]: label for ticket, label in cases}


def build_kb_articles(rng: random.Random) -> list[dict]:
    articles = []
    for index, (category, title, summary) in enumerate(KB_TOPICS):
        article = {
            "article_id": f"KB-{101 + index}",
            "category": category,
            "title": title,
            "body": summary,
            "updated_at": (REFERENCE_DATE - timedelta(days=rng.randrange(10, 400))).isoformat(),
            "superseded_by": None,
        }
        articles.append(article)
    # El artículo obsoleto apunta a su sustituto y es más antiguo que él.
    old = next(a for a in articles if "obsoleto" in a["title"])
    new = next(a for a in articles if a["title"] == "VPN inestable desde casa")
    old["superseded_by"] = new["article_id"]
    old["updated_at"] = (date.fromisoformat(new["updated_at"]) - timedelta(days=200)).isoformat()
    return articles


# Paquete «legacy» de inventario de la mesa de ayuda para app3/02 (ver TS 1.6):
# código sin tests que el agente debe mapear antes de planificar los tests.
# La dependencia escondida: `depreciacion.valor_actual` importa `almacen`
# dentro de la función y lee la caché que solo llena `asignaciones.asignar`.
# No aparece en los imports de cabecera de `depreciacion`: un Grep de la caché
# la insinúa, pero su efecto (valor residual del 10 %) solo se ve al leer
# `valor_actual`. Es texto fijo: no usa el generador aleatorio.
LEGACY_DIR = "legacy_inventario"
LEGACY_FILES = {
    "__init__.py": '''"""Inventario de equipos de la mesa de ayuda (código heredado, sin tests)."""
''',
    "modelos.py": '''"""Modelos del inventario."""

from dataclasses import dataclass


@dataclass
class Equipo:
    serial: str
    tipo: str  # portatil | monitor | movil | periferico
    precio_compra: float
    fecha_compra: str  # dd/mm/aaaa, como lo exporta el ERP antiguo


@dataclass
class Asignacion:
    serial: str
    user_id: str
    fecha: str
''',
    "fechas.py": '''"""Utilidades de fechas del ERP antiguo."""

from datetime import date


def parse_fecha(texto):
    # El ERP exporta dd/mm/aaaa; algunos registros vienen con guiones.
    dia, mes, anio = texto.replace("-", "/").split("/")
    return date(int(anio), int(mes), int(dia))


def anios_entre(desde, hasta):
    return (hasta - desde).days / 365.25
''',
    "almacen.py": '''"""Almacén en memoria de equipos y asignaciones."""

from .modelos import Equipo

_EQUIPOS = {}
# Caché de asignaciones activas: serial -> user_id. La llena asignaciones.asignar.
_CACHE_ASIGNADOS = {}


def alta(serial, tipo, precio, fecha):
    _EQUIPOS[serial] = Equipo(serial, tipo, precio, fecha)
    return _EQUIPOS[serial]


def obtener(serial):
    return _EQUIPOS.get(serial)


def todos():
    return list(_EQUIPOS.values())


def reset():
    _EQUIPOS.clear()
    _CACHE_ASIGNADOS.clear()
''',
    "asignaciones.py": '''"""Asignación de equipos a empleados."""

from . import almacen
from .modelos import Asignacion

_HISTORICO = []


def asignar(serial, user_id, fecha):
    if almacen.obtener(serial) is None:
        raise KeyError(f"equipo desconocido: {serial}")
    if serial in almacen._CACHE_ASIGNADOS:
        raise ValueError(f"{serial} ya está asignado a {almacen._CACHE_ASIGNADOS[serial]}")
    almacen._CACHE_ASIGNADOS[serial] = user_id
    _HISTORICO.append(Asignacion(serial, user_id, fecha))


def devolver(serial):
    almacen._CACHE_ASIGNADOS.pop(serial, None)


def de_empleado(user_id):
    return [s for s, u in almacen._CACHE_ASIGNADOS.items() if u == user_id]
''',
    "depreciacion.py": '''"""Valor contable de los equipos."""

from datetime import date

from .fechas import anios_entre, parse_fecha

VIDA_UTIL = {"portatil": 4, "monitor": 6, "movil": 3, "periferico": 2}


def valor_actual(serial, hoy=None):
    # Import tardío para evitar un ciclo con almacen (deuda técnica conocida).
    from . import almacen

    equipo = almacen.obtener(serial)
    hoy = hoy or date.today()
    anios = anios_entre(parse_fecha(equipo.fecha_compra), hoy)
    vida = VIDA_UTIL[equipo.tipo]
    valor = equipo.precio_compra * max(0.0, 1 - anios / vida)
    # Un equipo asignado conserva un 10 % de valor residual mínimo.
    if serial in almacen._CACHE_ASIGNADOS:
        valor = max(valor, equipo.precio_compra * 0.10)
    return round(valor, 2)
''',
    "informes.py": '''"""Informes para Finanzas."""

from . import almacen
from .depreciacion import valor_actual


def valor_total(hoy=None):
    return round(sum(valor_actual(e.serial, hoy) for e in almacen.todos()), 2)


def por_tipo():
    conteo = {}
    for equipo in almacen.todos():
        conteo[equipo.tipo] = conteo.get(equipo.tipo, 0) + 1
    return conteo
''',
}


def build_all() -> dict[str, str]:
    """Genera todos los archivos en memoria: nombre → contenido serializado."""
    # Un generador por conjunto: añadir un conjunto nuevo no altera los existentes.
    users = build_users(random.Random(f"{SEED}-users"))
    tickets, labels = build_tickets(random.Random(f"{SEED}-tickets"), users)
    articles = build_kb_articles(random.Random(f"{SEED}-kb"))
    datasets = {
        "usuarios.json": users,
        "tickets.json": tickets,
        "tickets_etiquetas.json": labels,
        "articulos_kb.json": articles,
    }
    files = {name: json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n" for name, data in datasets.items()}
    # Las rutas con subcarpeta usan «/»: mismo nombre en Windows y en Linux.
    files.update({f"{LEGACY_DIR}/{name}": content for name, content in LEGACY_FILES.items()})
    return files


def check(output_dir: Path = OUTPUT_DIR) -> list[str]:
    """Devuelve los archivos que faltan, sobran o difieren de lo que genera el script."""
    expected = build_all()
    problems = []
    for name, content in expected.items():
        path = output_dir / name
        if not path.is_file():
            problems.append(f"falta {name}")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"difiere {name}")
    for path in sorted(output_dir.rglob("*")):
        rel = path.relative_to(output_dir).as_posix()
        # La caché de Python aparece si algún módulo importa el paquete legacy.
        if path.is_file() and "__pycache__" not in rel and rel not in expected:
            problems.append(f"sobra {rel}")
    return problems


def write(output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in build_all().items():
        # newline="\n": mismos bytes en Windows y en Linux.
        path = output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="comprueba sin escribir; sale con 1 si hay diferencias")
    args = parser.parse_args()
    if args.check:
        problems = check()
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    write()
    print(f"Datos generados en {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
