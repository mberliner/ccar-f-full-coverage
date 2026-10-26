# ccar-f-full-coverage

Apps agénticas de demostración para practicar, con código ejecutable, todas las viñetas de la **Exam Guide v1.0 del examen CCAR-F**. Cada concepto de la guía se introduce **una sola vez**, en un módulo pequeño que se puede ejecutar y romper a propósito para ver el anti-patrón.

## Cómo se usa

El repositorio es un **curso práctico en código**. La guía del examen se divide en viñetas (conocimientos `K` y destrezas `S`, identificadas como `TS x.y-Kn` o `TS x.y-Sn`). Cada viñeta tiene asignado un módulo pequeño que la demuestra.

Una sesión de estudio típica:

1. **Elige una viñeta** y busca en `CONCEPTOS.md` el módulo que la introduce.
2. **Lee la cabecera del módulo.** Explica el concepto, qué dice la guía, por qué importa y cuál es el anti-patrón o la trampa del examen.
3. **Predice** qué hará el agente y ejecuta el módulo. El agente trabaja sobre una mesa de ayuda TI con datos sintéticos.
4. **Ejecútalo con `--anti`** (si la viñeta describe un error) y compara el resultado con el comportamiento correcto.
5. **Anota tus fallos** en tu `FALLOS.md` (`estado/<perfil>/`, ver «Primeros pasos»): las predicciones y respuestas que no acertaste.
6. **Repasa la cobertura** con `/verificar-concepto TS x.y-Kn`, que comprueba que la viñeta está introducida una sola vez y en su sitio.

Las ejecuciones con modelo tienen coste, por eso todas llevan un presupuesto máximo (`max_budget_usd`). Los tests con `pytest` no llaman al modelo y no cuestan nada.

Las apps siguen el temario por dominios:

| App | Dominios | Tema |
| :--- | :--- | :--- |
| `app1_agente_unico/` | D1, D2 y D5 | Bucle agéntico, tools integradas, servidores MCP, errores, scoping y `tool_choice`, configuración MCP y recorte de contexto |
| `app2_agente_con_control/` | D1, D4 y D5 | Hooks, permisos, sesiones, *few-shot*, escalamiento y *handoff* |
| `app3_sistema_multiagente/` | D1 a D5 | Coordinador y subagentes, tools entre roles, procedencia, extracción, lotes y CI |

Cada módulo introduce las viñetas que `CONCEPTOS.md` le asigna, así que una app puede cubrir varios dominios. Además, el propio repositorio muestra la configuración de Claude Code (`CLAUDE.md`, `.claude/`, `docs/`) y `d3_claude_code/` la recorre: ahí están las viñetas del dominio D3 que no son de ninguna app.

## Qué encontrarás aquí

| Ruta | Contenido |
| :--- | :--- |
| `app1_agente_unico/`, `app2_agente_con_control/`, `app3_sistema_multiagente/` | Las tres apps (ver arriba) |
| `d3_claude_code/` | Material sobre Claude Code (la configuración vive en `.claude/`, `docs/` y `CLAUDE.md`) |
| `harness/` | Arnés común: opciones aisladas, grabador de ejecuciones, modo sin conexión, credenciales |
| `datos/` | Datos **sintéticos** de una mesa de ayuda TI y su generador |
| `tests/` | Tests sin modelo (`pytest`): una-vez-por-viñeta, perímetro, arnés, datos, hooks |
| `CONCEPTOS.md` | Registro viñeta → módulo donde se introduce (240 viñetas) |
| `NOTAS.md` / `docs/hallazgos.md` | Avance de construcción / hallazgos de producto (versionados) |
| `plantillas/estado/` | Plantillas de tu estado personal (`FALLOS.md`, `NOTAS_PERSONALES.md`) |
| `estado/<perfil>/` | **Tu** estado de estudio: fallos, sesiones, práctica. Lo crea `harness/estado.py`; git lo ignora |
| `docs/` | Estándares de código y de flujo de trabajo |

## Si la guía cambia

Las 240 viñetas (113 `K` y 127 `S`) corresponden a la **Exam Guide v1.0**. Si la guía cambia, el repositorio debe cambiar con ella:

- Se actualiza `CONCEPTOS.md`: se añaden, quitan o renombran filas y se corrige el total.
- Se mueven o crean los módulos y sus marcadores `INTRODUCE` para que cada viñeta nueva tenga su destino. Los de viñetas eliminadas se retiran.
- Se ajusta `tests/perimetro_excluido.yaml` si cambia qué mecanismos entran en la guía.
- Los tests `test_una_vez.py` y `test_perimetro.py` fallan mientras `CONCEPTOS.md`, los marcadores y el perímetro no coincidan. Así se detecta lo que falta.
- `claude-agent-sdk` sigue fijado y solo se actualiza de forma deliberada, por si la guía nueva lo exige.

## El proyecto practica lo que enseña

El repositorio se construye con las mismas prácticas que evalúa la certificación, así que también sirve de ejemplo:

- **Configuración de Claude Code versionada:** `CLAUDE.md` con `@import`, reglas por tipo de archivo en `.claude/rules/`, skills, comandos de proyecto y hooks.
- **Plan mode** para diseñar y ejecución directa para módulos acotados; subagente `Explore` para el descubrimiento verboso.
- **Enforcement por código, no por prompt:** el presupuesto se exige en `harness/options.py` y la protección de `datos/sinteticos/` y de `.env` la aplican un hook y reglas `deny`.
- **Tests primero** y revisión por una instancia independiente de la que escribió el código.
- **Aislamiento de contexto** y sesiones con nombre por app.

Detalle en `docs/estandares-flujo.md`.

## Reglas que conviene conocer

- **Una vez:** cada viñeta tiene un único marcador `INTRODUCE`; después solo `USA`. Lo comprueba `tests/test_una_vez.py`.
- **Perímetro:** solo los mecanismos que nombra la guía. Lo comprueba `tests/test_perimetro.py`.
- **Datos siempre sintéticos:** `datos/sinteticos/` se cambia solo ejecutando el generador; un hook bloquea la edición directa.
- **Coste acotado:** toda ejecución con modelo exige `max_budget_usd` (lo impone `harness/options.py`).
- **Aislamiento:** los agentes de las apps no heredan `CLAUDE.md`, skills, hooks ni memoria del repositorio.

## Requisitos

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/)
- [Claude Code](https://claude.com/claude-code) (para trabajar en el proyecto, no para ejecutar los tests)
- Una `ANTHROPIC_API_KEY` solo para las ejecuciones con modelo

## Primeros pasos

### 1. Clonar e instalar

```bash
git clone <url-del-repositorio>
cd ccar-f-full-coverage
uv sync
```

`claude-agent-sdk` está fijado a una versión concreta en `pyproject.toml`; se actualiza solo de forma deliberada.

### 2. Comprobar que todo funciona (sin modelo, sin coste)

```bash
uv run pytest
```

Los tests no llaman al modelo.

### 3. Verificar los datos sintéticos

```bash
uv run python datos/generar_sinteticos.py --check
```

Para regenerarlos (son deterministas: misma semilla, mismos bytes):

```bash
uv run python datos/generar_sinteticos.py
```

### 4. Configurar la credencial (solo para ejecuciones con modelo)

```bash
cp .env.example .env     # en PowerShell: Copy-Item .env.example .env
```

Edita `.env` y sustituye `sk-ant-REEMPLAZAR` por tu clave. El archivo está en `.gitignore`. `harness/credentials.py` solo lee `.env` si no hay `ANTHROPIC_API_KEY` en el entorno.

### 5. Crear tu estado personal

Tus fallos, sesiones y práctica no se versionan: viven en `estado/<perfil>/`, que git ignora, y se crean desde `plantillas/estado/`.

```bash
uv run python -m harness.estado init                  # perfil «default»
uv run python -m harness.estado init --perfil intento2
uv run python -m harness.estado where                 # muestra la ruta y de dónde sale
```

- Un clon admite varios perfiles (una persona, o varios intentos del examen). Se eligen con `--perfil` o con `CCARF_PERFIL` en `.env`.
- `CCARF_ESTADO_DIR` mueve la base fuera del clon, por ejemplo a una carpeta sincronizada. Debe ser una ruta absoluta (o `estado`): una carpeta relativa con otro nombre quedaría dentro del clon sin ignorar y se rechaza.
- `init` solo crea lo que falta y nunca sobrescribe lo que ya escribiste.
- `uv run pytest` no necesita este estado: un clon recién hecho pasa los tests igual.

### 6. Si trabajas con Claude Code en este repositorio

Los `CLAUDE.md` de directorios padre contaminarían las pruebas, así que se excluyen en un archivo local que no se versiona:

```bash
cp .claude/settings.local.example.json .claude/settings.local.json
```

Edítalo: un patrón en `claudeMdExcludes` por cada `CLAUDE.md` padre que aparezca en `/memory`, y en `enabledPlugins` los plugins de tu cuenta que deban apagarse aquí. Comprueba con `/memory` y `/plugin`.

## Flujo de trabajo para añadir un módulo

1. Consulta en `CONCEPTOS.md` qué viñetas asigna el módulo.
2. Crea el esqueleto, tests primero, con el comando de proyecto:
   ```
   /nuevo-modulo app1/01_bucle_manual
   ```
3. Escribe la lógica hasta que `uv run pytest` pase. Construye las opciones del agente con `harness.options.isolated_options(max_budget_usd=...)`.
4. Al añadir un `INTRODUCE`, marca ☑ la fila en `CONCEPTOS.md` y actualiza su contador en el mismo cambio.
5. Comprueba la viñeta con la skill `/verificar-concepto TS x.y-Kn`.
6. Registra el avance de construcción en `NOTAS.md`, los hallazgos en `docs/hallazgos.md` y tus fallos en tu `FALLOS.md` personal.

Cada módulo debería poder ejecutarse con y sin `--anti` cuando la viñeta describe un error, para comparar el comportamiento correcto con el anti-patrón.

## Convenciones de código

- Comentarios en español, identificadores en inglés.
- Cabecera de módulo de app: `CONCEPTO` · `QUÉ DICE LA GUÍA` · `POR QUÉ IMPORTA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`.
- Cabecera de infraestructura: `PROPÓSITO` · `POR QUÉ EXISTE` · `QUÉ NO HACE`.
- No se copia texto de la guía oficial ni preguntas reales del examen.

Detalle en [`docs/estandares-codigo.md`](docs/estandares-codigo.md) y [`docs/estandares-flujo.md`](docs/estandares-flujo.md).
