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
import re
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


# Paquete `repo_mesa` para app1/02 (TS 2.5): un repositorio pequeño sobre el que
# el agente busca con Grep/Glob y edita con Edit/Write. Está diseñado para tres
# trampas: `calcular_sla` se reexporta con alias en `api.py` (hay llamadores que
# nunca escriben el nombre original), los tests están repartidos en varios
# directorios (para Glob) y `config.py` repite `TIMEOUT = 30` en dos bloques
# (para que Edit falle por ancla no única). El mensaje «SLA vencido para» solo
# existe en `core/sla.py`. Es texto fijo: no usa el generador aleatorio.
REPO_MESA_DIR = "repo_mesa"
REPO_MESA_FILES = {
    "__init__.py": '''"""Núcleo de la mesa de ayuda (repositorio de ejemplo)."""
''',
    "config.py": '''"""Configuración de los clientes de la mesa de ayuda."""

# Cliente de la API de tickets
API_URL = "https://api.mesa-ejemplo.test/tickets"
TIMEOUT = 30
REINTENTOS = 3

# Cliente de notificaciones
NOTIF_URL = "https://notif.mesa-ejemplo.test/avisos"
TIMEOUT = 30
CANAL = "correo"
''',
    "core/__init__.py": "",
    "core/sla.py": '''"""Cálculo de plazos de SLA."""

# Horas máximas de resolución por prioridad.
LIMITE_HORAS = {"urgente": 4, "alta": 8, "normal": 24, "baja": 72}


def calcular_sla(prioridad, horas_abiertas):
    limite = LIMITE_HORAS[prioridad]
    if horas_abiertas > limite:
        raise ValueError(f"SLA vencido para prioridad {prioridad}: {horas_abiertas} h de {limite} h")
    return {"limite_horas": limite, "restante_horas": limite - horas_abiertas}
''',
    "api.py": '''"""Interfaz pública del paquete: reexporta funciones con el nombre que usa el resto."""

from .core.sla import calcular_sla as sla_ticket

__all__ = ["sla_ticket"]
''',
    "tickets/__init__.py": "",
    "tickets/escalado.py": '''"""Decide si un ticket hay que escalarlo."""

from ..core.sla import calcular_sla


def debe_escalar(prioridad, horas_abiertas):
    try:
        calcular_sla(prioridad, horas_abiertas)
    except ValueError:
        return True
    return False
''',
    "tickets/tests/test_escalado.py": '''from repo_mesa.tickets.escalado import debe_escalar


def test_escala_cuando_vence():
    assert debe_escalar("urgente", 5)
    assert not debe_escalar("urgente", 1)
''',
    "informes/__init__.py": "",
    "informes/resumen.py": '''"""Resumen de plazos para el informe semanal."""

from ..api import sla_ticket


def horas_restantes(tickets):
    return {t["ticket_id"]: sla_ticket(t["prioridad"], t["horas"])["restante_horas"] for t in tickets}
''',
    "informes/tests/test_resumen.py": '''from repo_mesa.informes.resumen import horas_restantes


def test_horas_restantes():
    assert horas_restantes([{"ticket_id": "T1", "prioridad": "normal", "horas": 4}]) == {"T1": 20}
''',
    "notificaciones/__init__.py": "",
    "notificaciones/avisos.py": '''"""Avisos de plazo a la persona responsable."""

from ..api import sla_ticket as plazo


def texto_aviso(ticket_id, prioridad, horas):
    restante = plazo(prioridad, horas)["restante_horas"]
    return f"{ticket_id}: quedan {restante} h"
''',
    "tests/test_sla.py": '''import pytest

from repo_mesa.core.sla import calcular_sla


def test_dentro_de_plazo():
    assert calcular_sla("alta", 3)["restante_horas"] == 5


def test_vencido():
    with pytest.raises(ValueError):
        calcular_sla("alta", 9)
''',
}


# Catálogo de URLs y afirmaciones para app3/03 (TS 2.3). Unas URLs son
# documentos (`/docs/…`, con contenido) y otras no (login, seguimiento, imagen):
# `load_document` solo acepta las primeras y `fetch_url` abre cualquiera. Cada
# afirmación dice si se verifica de forma simple (un artículo) o compleja
# (varios). Los IDs de artículo salen de `KB_TOPICS`: KB-101 + posición.
DOCS_HOST = "https://docs.mesa-ejemplo.test"
DOCUMENT_URLS = [
    (f"{DOCS_HOST}/docs/vpn-perfil-tcp", "Perfil TCP de la VPN", "Cambiar al perfil TCP en el cliente de VPN y reiniciar la conexión. Si la red doméstica bloquea el puerto 443, usar el puerto alternativo."),
    (f"{DOCS_HOST}/docs/reembolsos", "Reembolsos de material", "Hasta 500 EUR aprueba soporte. Por encima, aprueba Finanzas. El pago se hace en la nómina siguiente a la aprobación."),
    (f"{DOCS_HOST}/docs/licencias", "Licencias de software", "Las renovaciones se solicitan 15 días antes de caducar. Las altas fuera de catálogo no se compran."),
    (f"{DOCS_HOST}/docs/acceso-carpetas", "Acceso a carpetas compartidas", "La persona responsable de la carpeta aprueba la solicitud desde el catálogo de accesos."),
]
NON_DOCUMENT_URLS = [
    f"{DOCS_HOST}/login?next=/docs",
    f"{DOCS_HOST}/tracking?id=TCK-4001",
    f"{DOCS_HOST}/static/logo-mesa.png",
    f"{DOCS_HOST}/perfil/preferencias",
]
CLAIMS = [
    ("C-1", "Los reembolsos hasta 500 EUR los aprueba soporte.", ["KB-114"], "simple"),
    ("C-2", "Las renovaciones de licencia se piden 15 días antes de caducar.", ["KB-112"], "simple"),
    ("C-3", "Las salas de reuniones usan la red de invitados.", ["KB-111"], "simple"),
    ("C-4", "Un reembolso de 520 EUR se aprueba en soporte y se paga en la nómina siguiente.", ["KB-114", "KB-115"], "compleja"),
    ("C-5", "La VPN inestable se arregla con el perfil TCP y no con el perfil UDP antiguo.", ["KB-109", "KB-110"], "compleja"),
]


def build_documents() -> dict:
    urls = [{"url": url, "is_document": True, "title": title, "content": content} for url, title, content in DOCUMENT_URLS]
    urls += [{"url": url, "is_document": False, "title": None, "content": None} for url in NON_DOCUMENT_URLS]
    claims = [{"claim_id": cid, "text": text, "article_ids": ids, "verifiable": kind} for cid, text, ids, kind in CLAIMS]
    return {"urls": urls, "afirmaciones": claims}


# Documentos de compra de equipos de la mesa para app3/07–09 (TS 4.2, 4.3, 4.4, 4.5).
# Formatos variados (tabla, prosa, líneas sueltas), campos ausentes en la fuente,
# dos tipos que no encajan en el `enum` (garantía y presupuesto), un fragmento
# ilegible, dos totales que no cuadran (`stated_total` ≠ suma de líneas), una
# factura sin pedido (el dato no está en ninguna parte) y un albarán largo que
# desborda un `max_tokens` corto (para el troceo de app3/09). Las etiquetas van
# en un archivo aparte que el agente nunca ve. Texto fijo: no usa el generador aleatorio.
PURCHASE_DOCS = [
    (
        "DC-01",
        '''FACTURA F-2026-0412
Proveedor: Suministros Ibéricos S.L.
Fecha: 14/09/2026
Pedido: PO-7731

| Descripción | Uds | Precio unidad |
| Portátil 14" | 3 | 899,00 € |
| Base de conexión USB-C | 3 | 129,50 € |

Total factura: 3.085,50 €
''',
        {
            "doc_type": "invoice", "doc_type_detail": None,
            "fields": {"vendor": "Suministros Ibéricos S.L.", "document_number": "F-2026-0412", "issue_date": "2026-09-14", "po_number": "PO-7731", "currency": "EUR", "stated_total": 3085.5},
            "line_items": [("Portátil 14\"", 3, 899.0), ("Base de conexión USB-C", 3, 129.5)],
        },
    ),
    (
        "DC-02",
        "Por la presente Tecnoequipos Norte S.A. le factura, con fecha 3 de septiembre de 2026 y número de factura F-2026-0398, dos monitores de 27 pulgadas a 310 euros cada uno y un teclado mecánico a 45,90 euros. El importe total a pagar es de 665,90 euros.",
        {
            "doc_type": "invoice", "doc_type_detail": None,
            "fields": {"vendor": "Tecnoequipos Norte S.A.", "document_number": "F-2026-0398", "issue_date": "2026-09-03", "po_number": None, "currency": "EUR", "stated_total": 665.9},
            "line_items": [("Monitor 27 pulgadas", 2, 310.0), ("Teclado mecánico", 1, 45.9)],
        },
    ),
    (
        "DC-03",
        '''ALBARÁN AL-5521
Distribuciones Levante
Fecha de entrega: 2026-09-20
Pedido: PO-7745
5 x Ratón inalámbrico
5 x Alfombrilla ergonómica
2 x Cable HDMI 2 m
''',
        {
            "doc_type": "delivery_note", "doc_type_detail": None,
            "fields": {"vendor": "Distribuciones Levante", "document_number": "AL-5521", "issue_date": "2026-09-20", "po_number": "PO-7745", "currency": None, "stated_total": None},
            "line_items": [("Ratón inalámbrico", 5, None), ("Alfombrilla ergonómica", 5, None), ("Cable HDMI 2 m", 2, None)],
        },
    ),
    (
        "DC-04",
        '''ALBARÁN AL-5530 — Papelería y Oficina Costa

| Artículo | Cantidad |
| Auriculares con micrófono | 8 |
| Webcam HD | 4 |

Pedido de referencia: PO-7752
''',
        {
            "doc_type": "delivery_note", "doc_type_detail": None,
            "fields": {"vendor": "Papelería y Oficina Costa", "document_number": "AL-5530", "issue_date": None, "po_number": "PO-7752", "currency": None, "stated_total": None},
            "line_items": [("Auriculares con micrófono", 8, None), ("Webcam HD", 4, None)],
        },
    ),
    (
        "DC-05",
        '''FACTURA F-2026-0431
Proveedor: Suministros Ibéricos S.L.
Fecha: 21/09/2026
Pedido: PO-7760

| Descripción | Uds | Precio unidad |
| Monitor 24" | 4 | 210,00 € |
| Soporte de pared | 4 | 90,00 € |

Total factura: 1.250,00 €
''',
        {
            "doc_type": "invoice", "doc_type_detail": None,
            "fields": {"vendor": "Suministros Ibéricos S.L.", "document_number": "F-2026-0431", "issue_date": "2026-09-21", "po_number": "PO-7760", "currency": "EUR", "stated_total": 1250.0},
            "line_items": [("Monitor 24\"", 4, 210.0), ("Soporte de pared", 4, 90.0)],
        },
    ),
    (
        "DC-06",
        '''CERTIFICADO DE GARANTÍA EXTENDIDA G-2026-077
Emitido por Tecnoequipos Norte S.A. el 12/09/2026.
Cubre 3 portátiles del pedido PO-7731 durante 24 meses adicionales.
''',
        {
            "doc_type": "other", "doc_type_detail": "garantía",
            "fields": {"vendor": "Tecnoequipos Norte S.A.", "document_number": "G-2026-077", "issue_date": "2026-09-12", "po_number": "PO-7731", "currency": None, "stated_total": None},
            "line_items": [],
        },
    ),
    (
        "DC-07",
        '''Pendiente de pago. Ver adjunto.
Ref. interna 7731.
Gracias.
''',
        {
            "doc_type": "unclear", "doc_type_detail": None,
            "fields": {"vendor": None, "document_number": None, "issue_date": None, "po_number": None, "currency": None, "stated_total": None},
            "line_items": [],
        },
    ),
    (
        "DC-08",
        '''INVOICE F-2026-0440 · Global Peripherals Ltd.
Issued: 22 Sep 2026 · Your order: PO-7768
2 x Docking station @ $425.00
1 x Cable bundle @ $400.00
Total due: US$ 1,250.00
''',
        {
            "doc_type": "invoice", "doc_type_detail": None,
            "fields": {"vendor": "Global Peripherals Ltd.", "document_number": "F-2026-0440", "issue_date": "2026-09-22", "po_number": "PO-7768", "currency": "USD", "stated_total": 1250.0},
            "line_items": [("Docking station", 2, 425.0), ("Cable bundle", 1, 400.0)],
        },
    ),
    (
        "DC-09",
        '''Factura F-2026-0455 · Servidores del Sur S.L. · 28-09-2026 · Pedido PO-7790
1 Servidor torre ........ 2.450,00
2 SAI 1500 VA ........ 180,00 c/u
TOTAL 2.830,00
''',
        {
            "doc_type": "invoice", "doc_type_detail": None,
            "fields": {"vendor": "Servidores del Sur S.L.", "document_number": "F-2026-0455", "issue_date": "2026-09-28", "po_number": "PO-7790", "currency": "EUR", "stated_total": 2830.0},
            "line_items": [("Servidor torre", 1, 2450.0), ("SAI 1500 VA", 2, 180.0)],
        },
    ),
    (
        "DC-10",
        "Albarán AL-5544: el 15 de septiembre de 2026 Distribuciones Levante entregó en la oficina de Valencia seis docks de portátil y diez fundas de 14 pulgadas, correspondientes al pedido PO-7790. Recibido sin incidencias.",
        {
            "doc_type": "delivery_note", "doc_type_detail": None,
            "fields": {"vendor": "Distribuciones Levante", "document_number": "AL-5544", "issue_date": "2026-09-15", "po_number": "PO-7790", "currency": None, "stated_total": None},
            "line_items": [("Dock de portátil", 6, None), ("Funda de 14 pulgadas", 10, None)],
        },
    ),
    (
        "DC-11",
        '''PRESUPUESTO P-2026-310
Servidores del Sur S.L.
Validez: hasta el 31/10/2026
1 x Armario rack 42U — 1.380,00 €
''',
        {
            "doc_type": "other", "doc_type_detail": "presupuesto",
            "fields": {"vendor": "Servidores del Sur S.L.", "document_number": "P-2026-310", "issue_date": None, "po_number": None, "currency": "EUR", "stated_total": None},
            "line_items": [("Armario rack 42U", 1, 1380.0)],
        },
    ),
]

# Albarán largo (DC-12): 40 líneas que dan una extracción de unos mil tokens y
# desbordan un `max_tokens` corto. Se construye con un bucle sobre una lista fija.
LONG_NOTE_ITEMS = [
    "Cable HDMI 2 m", "Adaptador USB-C a HDMI", "Ratón inalámbrico", "Teclado compacto", "Alfombrilla ergonómica",
    "Soporte de portátil", "Auriculares con micrófono", "Webcam HD", "Hub USB 4 puertos", "Cargador 65 W",
]


def build_long_note() -> tuple[str, dict]:
    header = "ALBARÁN AL-5560\nAlmacén Central Peninsular\nFecha de entrega: 2026-09-27\nPedido: PO-7800\n"
    items = [(f"{LONG_NOTE_ITEMS[n % len(LONG_NOTE_ITEMS)]} (ref {n + 1:03d})", 1 + n % 4) for n in range(40)]
    text = header + "".join(f"{quantity} x {name}\n" for name, quantity in items)
    label = {
        "doc_type": "delivery_note", "doc_type_detail": None,
        "fields": {"vendor": "Almacén Central Peninsular", "document_number": "AL-5560", "issue_date": "2026-09-27", "po_number": "PO-7800", "currency": None, "stated_total": None},
        "line_items": [(name, quantity, None) for name, quantity in items],
    }
    return text, label


# Pedidos de compra que cita algún documento, para la parte `enriquecimiento` de app3/07
# (la tool `lookup_purchase_order`). Más un pedido que ningún documento cita (PO-7999).
# Texto fijo; el handler de la tool solo lee este archivo.
PURCHASE_ORDERS = [
    {"po_number": "PO-7731", "vendor": "Suministros Ibéricos S.L.", "status": "recibido", "expected_total": 3085.5, "lines": 2},
    {"po_number": "PO-7745", "vendor": "Distribuciones Levante", "status": "recibido", "expected_total": 142.0, "lines": 3},
    {"po_number": "PO-7752", "vendor": "Papelería y Oficina Costa", "status": "recibido", "expected_total": 388.0, "lines": 2},
    {"po_number": "PO-7760", "vendor": "Suministros Ibéricos S.L.", "status": "facturado", "expected_total": 1200.0, "lines": 2},
    {"po_number": "PO-7768", "vendor": "Global Peripherals Ltd.", "status": "facturado", "expected_total": 1250.0, "lines": 2},
    {"po_number": "PO-7790", "vendor": "Servidores del Sur S.L.", "status": "parcial", "expected_total": 2830.0, "lines": 2},
    {"po_number": "PO-7800", "vendor": "Almacén Central Peninsular", "status": "recibido", "expected_total": 460.0, "lines": 40},
    {"po_number": "PO-7999", "vendor": "Tecnoequipos Norte S.A.", "status": "abierto", "expected_total": 799.0, "lines": 1},
]


# Fuentes de investigación para app3/04–06 (TS 5.3, 5.6, 5.1 y 5.4): calidad del servicio de la
# mesa de ayuda en el tercer trimestre. Diez fuentes: seis que discrepan en tres pares de cifras
# (tiempo de resolución, satisfacción y tickets reabiertos; los dos primeros se explican por el
# método, la muestra, el periodo o la población, el tercero no) y, de ellas, tickets y auditoría
# también concuerdan en el total de tickets cerrados; una que falla siempre por *timeout*
# (monitorización); una que falla solo la primera vez (red de sedes, que solo ve app3/04); una que
# responde vacía de forma legítima (archivo); y un informe largo con el hallazgo clave en mitad.
# Texto fijo, sin generador aleatorio. Las afirmaciones etiquetadas van en un archivo aparte que el agente nunca ve.
CONFLICT_SHARED_CONTEXT = "Tercer trimestre de 2026, sobre los 1.240 tickets cerrados, medido de apertura a cierre en el sistema."


def sectioned(*sections: tuple[str, str]) -> str:
    """Informe con secciones `## título`: la ubicación en la fuente que el investigador puede citar (TS 5.1-S5)."""
    return "\n\n".join(f"## {title}\n{text}" for title, text in sections)


SOURCE_REPORTS = [
    ("SRC-TICKETS", "Informe del sistema de tickets", "2026-10-02", "ok", sectioned(
        ("Resumen", "Resumen del tercer trimestre de 2026. Se cerraron 1.240 tickets."),
        ("Tiempos de resolución", "El tiempo medio de resolución fue de 18 horas, medido desde la apertura hasta el cierre registrado en el sistema."),
    )),
    ("SRC-AUDITORIA", "Auditoría interna de calidad", "2026-10-09", "ok", sectioned(
        ("Resultados de la muestra", "Sobre una muestra de 300 tickets del tercer trimestre de 2026, el tiempo medio de resolución fue de 26 horas, "
         "contando las esperas de respuesta de la persona usuaria."),
        ("Volumen", "El total de tickets cerrados en el trimestre fue de 1.240."),
    )),
    ("SRC-ENCUESTA", "Encuesta interna de satisfacción", "2026-09-30", "ok", sectioned(
        ("Metodología", "Encuesta enviada a quienes cerraron un ticket en el trimestre: 212 respuestas."),
        ("Resultados", "La satisfacción media fue de 4,1 sobre 5."),
    )),
    ("SRC-PROVEEDOR", "Informe del proveedor de soporte externo", "2026-10-15", "ok", sectioned(
        ("Metodología", "Encuesta del proveedor a 95 usuarios con corte a 31 de agosto de 2026."),
        ("Resultados", "La satisfacción media fue de 3,6 sobre 5."),
    )),
    # Tercer par, el contraste: mismo periodo, mismo método y misma población (`CONFLICT_SHARED_CONTEXT`
    # está en las dos fuentes, dicho igual) y cifras que discrepan sin que nada de los metadatos lo explique.
    ("SRC-CUADRO", "Cuadro de mandos de operaciones", "2026-10-05", "ok", sectioned(
        ("Alcance", CONFLICT_SHARED_CONTEXT),
        ("Resultados", "El porcentaje de tickets reabiertos fue del 7,3 %."),
    )),
    ("SRC-OFICINA", "Informe de la oficina de calidad", "2026-10-06", "ok", sectioned(
        ("Alcance", CONFLICT_SHARED_CONTEXT),
        ("Resultados", "El porcentaje de tickets reabiertos fue del 12,4 %."),
    )),
    ("SRC-MONITOR", "Monitorización de red", "2026-10-01", "timeout", None),
    # Transitoria (app3/04, TS 5.3-S3): falla con timeout la primera vez que se consulta en una ejecución
    # y responde bien a la siguiente. Solo la ve el servidor con `transient=True`.
    ("SRC-REDES", "Informe de disponibilidad de la red de sedes", "2026-10-03", "timeout_once", sectioned(
        ("Disponibilidad", "Durante el tercer trimestre de 2026 la disponibilidad de la red de las tres sedes fue del 99,2 %."),
    )),
    ("SRC-ARCHIVO", "Archivo de informes de incidentes graves", "2026-10-01", "ok", ""),
    ("SRC-LARGO", "Informe trimestral de incidencias de red", "2026-10-12", "ok", "LONG"),
]


def locate_figure(report: str, figure_text: str) -> tuple[str, str]:
    """(título de la sección, frase literal) donde aparece la cifra en un informe con secciones."""
    for block in report.split("\n\n"):
        title, _, body = block.removeprefix("## ").partition("\n")
        for sentence in re.split(r"(?<=[.])\s+", body):
            if figure_text in sentence:
                return title, sentence
    raise ValueError(f"{figure_text} no está en el informe")


# Relleno del informe largo (TS 5.1-K2): párrafos distintos entre sí y con cifras de distracción del mismo tipo que el
# hallazgo (porcentajes de incidencias de red), todas menores que la clave. Sin marcas de apartado: el hallazgo no se
# distingue por ser la única frase con cifra, sino que hay que leerlo para encontrarlo.
FILLER_CAUSES = [
    "un conmutador con el firmware sin actualizar", "cortes de suministro en el armario de comunicaciones",
    "un fallo de resolución DNS en el servidor secundario", "certificados caducados en los puntos de acceso",
    "la saturación del enlace durante las copias nocturnas", "una regla del cortafuegos aplicada por error",
    "cables de parcheo dañados en la planta baja", "licencias sin renovar del cliente de acceso remoto",
    "un reinicio no programado del controlador inalámbrico", "interferencias de una nueva instalación eléctrica",
    "un cambio de direccionamiento sin comunicar a la mesa", "baterías agotadas en el sistema de alimentación",
]
FILLER_SEDES = ["Norte", "Centro", "Sur"]
FILLER_MESES = ["julio", "agosto", "septiembre"]
FILLER_PERCENTAGES = ["6", "9", "11", "7", "14", "8,5", "12", "5", "16", "10", "13", "4", "15", "9,5", "18", "7,5", "17"]
FILLER_ACTIONS = [
    "con un cambio de pieza", "tras una actualización", "con una reconfiguración remota", "al ajustar la planificación",
    "con apoyo del proveedor", "al sustituir el equipo",
]
FILLER_NEUTRAL = [
    "El equipo de red revisó los registros de los puntos de acceso de la sede {sede} y no encontró cambios de configuración fuera de calendario.",
    "La ventana de mantenimiento de la sede {sede} se comunicó con antelación y se cumplió, salvo una hora que se aplazó por petición de la dirección.",
    "Se unificó el formato de las fichas de alta de dispositivos de la sede {sede} con el que usan las demás.",
    "La guardia de red de la sede {sede} mantuvo la rotación semanal y atendió las incidencias fuera de horario por el canal de la mesa.",
    "El inventario de conmutadores de la sede {sede} recoge la ubicación de cada armario y la persona que lo mantiene.",
    "Las pruebas de conmutación entre líneas de {sede} se repitieron y los tiempos quedaron anotados en la hoja de seguimiento.",
    "El personal de la sede {sede} completó la formación de refuerzo sobre el portal de incidencias.",
    "El proveedor de comunicaciones entregó el informe de disponibilidad de los enlaces de {sede} y se archivó con la documentación del contrato.",
    "En {sede} se etiquetaron los 24 puertos del armario principal con el mismo criterio que en el resto de sedes.",
    "El plan de contingencia de la sede {sede} se revisó con las dos personas responsables y no requirió cambios.",
    "Se retiraron de {sede} 7 equipos de red fuera de servicio y su baja quedó registrada en el inventario.",
    "La sala de comunicaciones de {sede} pasó la inspección anual de seguridad sin observaciones.",
    "En {sede} se probó el acceso de invitados con tres perfiles distintos y se documentó el resultado.",
    "El calendario de copias de configuración de los equipos de {sede} se ajustó para evitar solapes con el mantenimiento.",
    "La persona responsable de {sede} actualizó el diagrama de red tras mover dos puestos de trabajo.",
    "Se revisaron los contratos de línea de {sede} y se pidió al proveedor el desglose de la facturación del trimestre.",
    "En {sede} se sustituyó el cartel de contacto de la mesa de ayuda por uno con el número interno nuevo.",
    "El equipo de {sede} midió la cobertura inalámbrica de la planta alta y anotó las zonas con señal débil.",
    "Se archivaron las actas de las reuniones de coordinación con la sede {sede} del trimestre.",
    "La sede {sede} recibió el material de repuesto pedido y se guardó en el armario de la sala de comunicaciones.",
]
LONG_KEY_FINDING = "El 41 % de las incidencias de red del trimestre se debió a un único perfil de VPN obsoleto que seguía desplegado en los portátiles antiguos."
LONG_SUMMARY_LINE = "Hallazgo clave: el 41 % de las incidencias de red del trimestre se debió a un único perfil de VPN obsoleto."


# Secciones del informe largo con encabezados (variante de TS 5.1-S4): (índice del primer párrafo, título).
# El hallazgo clave está en el índice 30, dentro de «Incidencias y causas» (25 a 39) y sin abrir sección:
# el encabezado ayuda a ubicarlo, no lo señala.
LONG_SECTIONS = [
    (0, "Revisión de la red"), (10, "Mantenimiento y guardia"), (20, "Documentación e inventario"),
    (25, "Incidencias y causas"), (40, "Formación y proveedores"), (50, "Seguimiento y cierre"),
]


def long_report_paragraphs() -> list[str]:
    """Los 61 párrafos del informe largo: 60 de relleno distintos entre sí y el hallazgo clave en el índice 30.

    Dos de cada tres párrafos de relleno llevan un porcentaje de incidencias de red (cifra de distracción del mismo
    tipo que el hallazgo); el resto, una actividad sin cifra de ese tipo.
    """
    combos = [(c, e, m) for c in range(len(FILLER_CAUSES)) for e in range(len(FILLER_SEDES)) for m in range(len(FILLER_MESES))]
    paragraphs: list[str] = []
    with_figure = neutral = 0
    for n in range(60):
        if n % 3 == 2:
            sede = FILLER_SEDES[(neutral * 2) % len(FILLER_SEDES)]
            paragraphs.append(FILLER_NEUTRAL[neutral].format(sede=sede))
            neutral += 1
        else:
            cause, sede, month = combos[(with_figure * 7) % len(combos)]  # 7 y 108 son coprimos: no se repite ninguna combinación
            pct = FILLER_PERCENTAGES[with_figure % len(FILLER_PERCENTAGES)]
            action = FILLER_ACTIONS[(with_figure * 5) % len(FILLER_ACTIONS)]
            paragraphs.append(
                f"En la sede {FILLER_SEDES[sede]}, el {pct} % de las incidencias de red de {FILLER_MESES[month]} se debió a "
                f"{FILLER_CAUSES[cause]}, que se resolvió {action}."
            )
            with_figure += 1
    paragraphs.insert(30, LONG_KEY_FINDING)
    return paragraphs


def build_long_report() -> str:
    """Informe largo: 30 párrafos de relleno, el hallazgo clave en el 31.º (índice 30) y otros 30 de relleno después."""
    return "\n\n".join(long_report_paragraphs())


def build_headed_long_report() -> str:
    """El mismo informe largo con un encabezado `## título` antes de cada sección; sin ellos queda igual que el original."""
    starts = dict(LONG_SECTIONS)
    parts: list[str] = []
    for index, paragraph in enumerate(long_report_paragraphs()):
        if index in starts:
            parts.append(f"## {starts[index]}")
        parts.append(paragraph)
    return "\n\n".join(parts)


def build_research_sources() -> tuple[list[dict], dict]:
    """Fuentes (lo que ve el agente) y etiquetas (solo para puntuar)."""
    long_report = build_long_report()
    sources = [
        {
            "source_id": source_id, "name": name, "published_at": published, "availability": availability,
            "report": long_report if report == "LONG" else report,
        }
        for source_id, name, published, availability, report in SOURCE_REPORTS
    ]
    by_id = {source_id: report for source_id, _, _, _, report in SOURCE_REPORTS}
    labels = {
        "established": {
            "topic": "tickets cerrados en el trimestre", "figure": 1240, "figure_text": "1.240",
            "source_ids": ["SRC-TICKETS", "SRC-AUDITORIA"],
        },
        "conflicts": [
            {
                # Cada par dice cómo lo explican (o no) los metadatos: `periodo`, `metodo`, `muestra`,
                # `poblacion` o `sin_explicacion`, y la frase de las fuentes que lo respalda.
                "topic": "tiempo medio de resolución", "unit": "horas",
                "explained_by": ["metodo", "muestra"],
                "evidence": {"metodo": "contando las esperas de respuesta", "muestra": "muestra de 300 tickets"},
                "claims": [
                    {"source_id": "SRC-TICKETS", "figure": 18, "figure_text": "18 horas", "published_at": "2026-10-02"},
                    {"source_id": "SRC-AUDITORIA", "figure": 26, "figure_text": "26 horas", "published_at": "2026-10-09"},
                ],
            },
            {
                "topic": "satisfacción media", "unit": "sobre 5",
                "explained_by": ["periodo", "poblacion"],
                "evidence": {"periodo": "corte a 31 de agosto de 2026", "poblacion": "95 usuarios"},
                "claims": [
                    {"source_id": "SRC-ENCUESTA", "figure": 4.1, "figure_text": "4,1 sobre 5", "published_at": "2026-09-30"},
                    {"source_id": "SRC-PROVEEDOR", "figure": 3.6, "figure_text": "3,6 sobre 5", "published_at": "2026-10-15"},
                ],
            },
            {
                # El contraste: mismo periodo, método y población (`shared_context`, igual en las dos fuentes)
                # y cifras distintas. Nada en los metadatos explica la diferencia.
                "topic": "tickets reabiertos", "unit": "%",
                "explained_by": ["sin_explicacion"], "evidence": {}, "shared_context": CONFLICT_SHARED_CONTEXT,
                "claims": [
                    {"source_id": "SRC-CUADRO", "figure": 7.3, "figure_text": "7,3 %", "published_at": "2026-10-05"},
                    {"source_id": "SRC-OFICINA", "figure": 12.4, "figure_text": "12,4 %", "published_at": "2026-10-06"},
                ],
            },
        ],
        "failed_sources": ["SRC-MONITOR"],
        "transient_sources": [{"source_id": "SRC-REDES", "figure_text": "99,2 %"}],
        "empty_sources": ["SRC-ARCHIVO"],
        "long_report": {
            "source_id": "SRC-LARGO", "key_finding": LONG_KEY_FINDING, "figure": 41, "figure_text": "41 %",
            "summary_line": LONG_SUMMARY_LINE,
            # Variante con encabezados de sección (TS 5.1-S4): el mismo texto con `## título` antes de cada sección.
            "headed_report": build_headed_long_report(), "section_headings": [title for _, title in LONG_SECTIONS],
        },
    }
    # Ubicación en la fuente y fragmento literal de cada afirmación en conflicto (TS 5.1-S5, 5.6-S1): solo para puntuar.
    for conflict in labels["conflicts"]:
        for claim in conflict["claims"]:
            claim["location"], claim["excerpt"] = locate_figure(by_id[claim["source_id"]], claim["figure_text"])
    return sources, labels


def build_purchase_docs() -> tuple[list[dict], dict]:
    """Documentos (lo que ve el agente) y etiquetas (solo para puntuar), con el total calculado de cada uno."""
    entries = [*PURCHASE_DOCS, ("DC-12", *build_long_note())]
    documents, labels = [], {}
    for doc_id, text, label in entries:
        documents.append({"doc_id": doc_id, "text": text})
        items = [{"description": d, "quantity": q, "unit_price": p} for d, q, p in label["line_items"]]
        priced = [i for i in items if i["unit_price"] is not None]
        calculated = round(sum(i["quantity"] * i["unit_price"] for i in priced), 2) if priced else None
        stated = label["fields"]["stated_total"]
        labels[doc_id] = {
            **label,
            "line_items": items,
            "calculated_total": calculated,
            "total_mismatch": stated is not None and calculated is not None and abs(stated - calculated) > 0.01,
        }
    return documents, labels


# Población de extracciones con confianza por campo para app3/10 (TS 5.5). Simula lo que
# devolvería un modelo que declara su confianza en cada campo: 292 documentos de compra
# (facturas, albaranes y un tipo raro, «other») y 6 campos cada uno. La exactitud agregada ronda
# el 97 %, pero el tipo raro acierta alrededor de la mitad y las facturas en prosa fallan en la
# fecha (TS 5.5-K1). La confianza simulada es optimista donde se equivoca: la mayoría de los
# errores del tipo raro llega con confianza alta. Hay documentos con conflicto (`conflict_detected`
# de app3/08) y ambiguos, con confianza alta. Las etiquetas (qué campo es correcto) van aparte;
# la mitad de cada tipo es el conjunto de calibración y la otra mitad, producción.
CONFIDENCE_FIELDS = ["vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"]
CONFIDENCE_BASE_ERROR = 0.004
CONFIDENCE_SEGMENTS = [
    # (tipo, formato, documentos, probabilidad de error por campo; el resto usa la base)
    ("invoice", "tabla", 90, {}),
    ("invoice", "prosa", 50, {"issue_date": 0.18}),
    ("invoice", "lineas", 60, {}),
    ("delivery_note", "tabla", 30, {}),
    ("delivery_note", "lineas", 50, {}),
    ("other", "prosa", 12, {"vendor": 0.10, "document_number": 0.40, "issue_date": 0.60, "po_number": 0.70, "currency": 0.20, "stated_total": 0.60}),
]


def build_confidence_population(rng: random.Random) -> tuple[list[dict], dict]:
    """Registros (lo que ve el módulo) y etiquetas (solo para puntuar), con la mitad en cada conjunto."""
    shells = [(kind, form, errors) for kind, form, count, errors in CONFIDENCE_SEGMENTS for _ in range(count)]
    rng.shuffle(shells)
    records, labels = [], {}
    seen_by_type: dict[str, int] = {}
    for index, (kind, form, errors) in enumerate(shells, start=1):
        record_id = f"X-{index:03d}"
        confidences, correct = {}, {}
        for name in CONFIDENCE_FIELDS:
            ok = rng.random() >= errors.get(name, CONFIDENCE_BASE_ERROR)
            if ok:
                value = min(max(rng.gauss(0.95, 0.03), 0.6), 0.995)
            elif rng.random() < 0.3:
                value = rng.uniform(0.35, 0.70)  # el modelo duda y acierta a dudar
            else:
                value = rng.uniform(0.86, 0.98)  # se equivoca con seguridad
            confidences[name] = round(value, 2)
            correct[name] = ok
        # El reparto alterna dentro de cada tipo: los dos conjuntos tienen documentos de cada uno.
        turn = seen_by_type.get(kind, 0)
        seen_by_type[kind] = turn + 1
        records.append(
            {
                "record_id": record_id,
                "split": "calibracion" if turn % 2 == 0 else "produccion",
                "doc_type": kind,
                "doc_format": form,
                "conflict_detected": kind == "invoice" and rng.random() < 0.06,
                "ambiguous": rng.random() < 0.04,
                "doc_confidence": round(sum(confidences.values()) / len(confidences), 2),
                "confidences": confidences,
            }
        )
        labels[record_id] = {"correct": correct}
    return records, labels


def build_all() -> dict[str, str]:
    """Genera todos los archivos en memoria: nombre → contenido serializado."""
    # Un generador por conjunto: añadir un conjunto nuevo no altera los existentes.
    users = build_users(random.Random(f"{SEED}-users"))
    tickets, labels = build_tickets(random.Random(f"{SEED}-tickets"), users)
    articles = build_kb_articles(random.Random(f"{SEED}-kb"))
    purchase_documents, purchase_labels = build_purchase_docs()
    research_sources, research_labels = build_research_sources()
    population, population_labels = build_confidence_population(random.Random(f"{SEED}-confianza"))
    datasets = {
        "usuarios.json": users,
        "tickets.json": tickets,
        "tickets_etiquetas.json": labels,
        "articulos_kb.json": articles,
        "documentos.json": build_documents(),
        "documentos_compra.json": purchase_documents,
        "documentos_compra_etiquetas.json": purchase_labels,
        "pedidos_compra.json": PURCHASE_ORDERS,
        "fuentes_investigacion.json": research_sources,
        "fuentes_investigacion_etiquetas.json": research_labels,
        "poblacion_extracciones.json": population,
        "poblacion_extracciones_etiquetas.json": population_labels,
    }
    files = {name: json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n" for name, data in datasets.items()}
    # Las rutas con subcarpeta usan «/»: mismo nombre en Windows y en Linux.
    files.update({f"{LEGACY_DIR}/{name}": content for name, content in LEGACY_FILES.items()})
    files.update({f"{REPO_MESA_DIR}/{name}": content for name, content in REPO_MESA_FILES.items()})
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
