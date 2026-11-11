# ccar-f-full-coverage

Apps agénticas de demostración para practicar, con código ejecutable, todas las viñetas de la **Exam Guide v1.0 del examen CCAR-F**. Cada concepto de la guía se introduce **una sola vez**, en un módulo pequeño que se puede ejecutar y romper a propósito para ver el anti-patrón.

## Empieza aquí

**Qué es.** Un curso práctico en código para el examen CCAR-F: aprender a construir agentes con Claude (el bucle agéntico, las tools y los servidores MCP, hacer cumplir reglas con código, las sesiones, los sistemas con coordinador y subagentes, y la configuración de Claude Code). El temario sale de la Exam Guide v1.0, organizada en dominios (D1–D5) y en **viñetas**, cada uno de sus puntos evaluables (`TS x.y-Kn` o `TS x.y-Sn`). Aquí no se copia la guía: cada módulo explica su concepto con sus palabras y cierra con una pregunta propia en formato de examen.

**Qué es un módulo.** Un ejercicio, con dos partes: un script de una app (por ejemplo, `app1_agente_unico/05_scoping_y_tool_choice.py`) y su sección `## NN` en el `README.md` de esa app. La sección dice qué hacer en cada paso; el script no hace falta leerlo.

**Qué necesitas.** Usar la terminal. Saber leer Python ayuda, pero no es imprescindible: el ciclo se sigue con los textos y la salida. Para ejecutar con modelo hace falta una API key o, en los módulos del Agent SDK, la suscripción de Claude Code ([Instalación](#instalación-una-vez)). Sin credencial puedes hacer en modo ligero los módulos que lo permiten, pero cuatro son de ejecución obligatoria: qué pide cada módulo está en [credenciales y modos](docs/credenciales-y-modos.md). Los términos están en el [glosario](docs/glosario.md).

**Qué te da cada camino.** Hacer los módulos en modo ligero es *preparación conceptual sin coste*: fija los conceptos y el vocabulario de la guía. No equivale a *competencia práctica demostrada*. La guía describe a un candidato con seis meses o más construyendo con las APIs de Claude, el Agent SDK, Claude Code y MCP, y para prepararse recomienda construir (un agente, una configuración de Claude Code, tools MCP, una extracción estructurada), no solo leer. Ejecutar los módulos y hacer la práctica propia de D3 se acerca más a eso, pero tampoco sustituye construir un sistema tuyo. Y no toda ejecución con modelo muestra el mecanismo: [tipos de señal](docs/tipos-de-senal.md) dice, parte a parte, cuáles lo enseñan y cuáles solo se explican.

### Cómo empezar: con guía (recomendado)

Un asistente te narra cada módulo paso a paso: te explica de qué va, espera tus predicciones, te dice cuándo ejecutar y no te enseña el resultado ni la respuesta antes de tiempo. No tienes que abrir ningún archivo.

1. Clona e instala (`git clone …`, `cd ccar-f-full-coverage`, `uv sync`; ver [Instalación](#instalación-una-vez)). Necesitas [Claude Code](https://claude.com/claude-code).
2. Abre `claude` en la carpeta del repositorio y escribe `/practica-guiada`.
3. La primera vez, elige **Puesta en marcha**: comprueba si tienes la credencial y tu `FALLOS.md`, y te dice qué hacer con lo que falte. Solo hace falta una vez.
4. Elige un módulo del menú (el recomendado va marcado con ★) o escríbelo directamente: `/practica-guiada app1/01`.

### Por tu cuenta

Si prefieres leer a tu ritmo, cada sección de módulo se sigue sola con el ciclo de abajo. **Tu primer módulo:** [app1 · 01 · Bucle manual](app1_agente_unico/README.md#01--bucle-manual).

### Cómo se hace un módulo

Es el mismo ciclo con guía o sin ella; con `/practica-guiada`, el asistente te lleva por cada paso. Cada sección de módulo tiene las mismas partes, en este orden:

1. **Oriéntate.** Lee la ficha del principio (qué vas a hacer, qué necesitas antes y el **Modo**), «Antes de empezar» y «El ejercicio».
2. **Predice.** Responde por escrito, con tus palabras, las preguntas de «Predice antes de ejecutar». No hay un número que acertar. Las marcadas `(guía)` evalúan un concepto del examen; las `(módulo)`, un detalle de ese ejercicio.
3. **Ejecuta o no, y contrasta.** Si el Modo es *ejecución ligera*, puedes hacerlo sin ejecutar nada; si es *obligatoria*, ejecuta los comandos de «Ejecutar». Después abre el bloque plegado **«Paso 3 · Contrastar»** de «Qué observar» y compáralo con lo que predijiste.
4. **Responde.** Contesta la «Pregunta tipo examen» y, después, abre **«Paso 4 · Respuesta»**.
5. **Anota.** Cada predicción `(guía)` o respuesta fallida va en tu `FALLOS.md` ([estado personal](#5-crear-tu-estado-personal)): es lo que repasarás antes del examen.

Para profundizar, la cabecera del script explica el concepto, qué dice la guía, por qué importa y la trampa del examen.

### Orden, tiempo y coste

**Orden recomendado.** Las apps van de lo simple a lo compuesto, y cada una se apoya en la anterior. Dentro de cada app, el orden es el de la tabla «Ruta de lectura» de su `README.md`:

1. [`app1_agente_unico/`](app1_agente_unico/README.md): `01` (bucle escrito a mano) → `02` a `07` (Agent SDK, tools integradas, MCP, errores, scoping, configuración MCP y recorte de contexto).
2. [`app2_agente_con_control/`](app2_agente_con_control/README.md): `01` → `07` (reglas en código, hooks, permisos, *few-shot* y escalamiento, *handoff*, sesiones).
3. [`app3_sistema_multiagente/`](app3_sistema_multiagente/README.md): `01` → `12` (coordinador y subagentes, paralelo, tools por rol, errores, procedencia, contexto largo, extracción con schema, validación con reintento, lotes, confianza y revisión, criterios y CI, revisión independiente).
4. [`d3_claude_code/`](d3_claude_code/README.md): la configuración de Claude Code (dominio D3, el 20 % del examen). No depende de las apps: se puede leer en cualquier momento, y conviene antes de `app3` `11` y `12`, que usan Claude Code en CI.

Si prefieres ir por viñeta, `CONCEPTOS.md` dice qué módulo introduce cada una.

**Documentos de apoyo.** El [glosario](docs/glosario.md), cuando un término no quede claro; [tipos de señal](docs/tipos-de-senal.md), antes de decidir si ejecutas una parte en modo ligero (dice si esa ejecución enseña algo); y tu `FALLOS.md`, para repasar lo anotado al cerrar cada app y antes del examen.

**Tiempo orientativo.** Unos 10 minutos por módulo sin ejecutar y unos 25 ejecutando las variantes.

**Coste.** Los tests no llaman al modelo y no cuestan nada. Las ejecuciones con modelo sí, y todas llevan un tope (`max_budget_usd`); `--budget` lo baja para una prueba barata, salvo en los módulos que miden una tasa, donde un tope menor puede cortar repeticiones (lo avisa su «Ejecutar»). La credencial se prepara en [Configurar la credencial](#4-configurar-la-credencial-solo-para-ejecuciones-con-modelo).

**Si falta tiempo.** Haz los módulos en modo ligero: predices y contrastas con el resultado de referencia plegado, sin ejecutar. Los de ejecución obligatoria lo dicen en su ficha y conviene ejecutarlos igualmente (ver [modo ligero](docs/glosario.md#el-repositorio-y-el-ejercicio)).

## Qué encontrarás aquí

Las apps siguen el temario por dominios:

| App | Dominios | Tema |
| :--- | :--- | :--- |
| `app1_agente_unico/` | D1, D2 y D5 | Bucle agéntico, tools integradas, servidores MCP, errores, scoping y `tool_choice`, configuración MCP y recorte de contexto |
| `app2_agente_con_control/` | D1, D4 y D5 | Hooks, permisos, sesiones, *few-shot*, escalamiento y *handoff* |
| `app3_sistema_multiagente/` | D1 a D5 | Coordinador y subagentes, tools entre roles, procedencia, extracción, lotes y CI |

Cada módulo introduce las viñetas que `CONCEPTOS.md` le asigna, así que una app puede cubrir varios dominios. Además, el propio repositorio muestra la configuración de Claude Code (`CLAUDE.md`, `.claude/`, `docs/`) y `d3_claude_code/` la recorre: ahí están las viñetas del dominio D3 que no son de ninguna app.

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

## Instalación (una vez)

### Requisitos

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/)
- [Claude Code](https://claude.com/claude-code) (para la práctica guiada y para trabajar en el proyecto; no para ejecutar los tests ni los módulos)
- Para las ejecuciones con modelo, una `ANTHROPIC_API_KEY` o, solo en los módulos del Agent SDK, la suscripción de Claude Code (tabla por módulo en [`docs/credenciales-y-modos.md`](docs/credenciales-y-modos.md))

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

## Para quien construye el repositorio

Lo que sigue no hace falta para estudiar: es para mantener y ampliar el repositorio.

### El proyecto practica lo que enseña

El repositorio se construye con las mismas prácticas que evalúa la certificación, así que también sirve de ejemplo:

- **Configuración de Claude Code versionada:** `CLAUDE.md` con `@import`, reglas por tipo de archivo en `.claude/rules/`, skills, comandos de proyecto y hooks.
- **Plan mode** para diseñar y ejecución directa para módulos acotados; subagente `Explore` para el descubrimiento verboso.
- **Enforcement por código, no por prompt:** el presupuesto se exige en `harness/options.py` y la protección de `datos/sinteticos/` y de `.env` la aplican un hook y reglas `deny`.
- **Tests primero** y revisión por una instancia independiente de la que escribió el código.
- **Aislamiento de contexto** y sesiones con nombre por app.

Detalle en `docs/estandares-flujo.md`.

### Reglas que conviene conocer

- **Una vez:** cada viñeta tiene un único marcador `INTRODUCE`; después solo `USA`. Lo comprueba `tests/test_una_vez.py`.
- **Perímetro:** solo los mecanismos que nombra la guía. Lo comprueba `tests/test_perimetro.py`.
- **Datos siempre sintéticos:** `datos/sinteticos/` se cambia solo ejecutando el generador; un hook bloquea la edición directa.
- **Coste acotado:** toda ejecución con modelo exige `max_budget_usd` (lo impone `harness/options.py`).
- **Aislamiento:** los agentes de las apps no heredan `CLAUDE.md`, skills, hooks ni memoria del repositorio.

### Si trabajas con Claude Code en este repositorio

Los `CLAUDE.md` de directorios padre contaminarían las pruebas, así que se excluyen en un archivo local que no se versiona:

```bash
cp .claude/settings.local.example.json .claude/settings.local.json
```

Edítalo: un patrón en `claudeMdExcludes` por cada `CLAUDE.md` padre que aparezca en `/memory`, y en `enabledPlugins` los plugins de tu cuenta que deban apagarse aquí. Comprueba con `/memory` y `/plugin`.

### Flujo de trabajo para añadir un módulo

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

### Si la guía cambia

Las 240 viñetas (113 `K` y 127 `S`) corresponden a la **Exam Guide v1.0**. Si la guía cambia, el repositorio debe cambiar con ella:

- Se actualiza `CONCEPTOS.md`: se añaden, quitan o renombran filas y se corrige el total.
- Se mueven o crean los módulos y sus marcadores `INTRODUCE` para que cada viñeta nueva tenga su destino. Los de viñetas eliminadas se retiran.
- Se ajusta `tests/perimetro_excluido.yaml` si cambia qué mecanismos entran en la guía.
- Los tests `test_una_vez.py` y `test_perimetro.py` fallan mientras `CONCEPTOS.md`, los marcadores y el perímetro no coincidan. Así se detecta lo que falta.
- `claude-agent-sdk` sigue fijado y solo se actualiza de forma deliberada, por si la guía nueva lo exige.

### Convenciones de código

- Comentarios en español, identificadores en inglés.
- Cabecera de módulo de app: `CONCEPTO` · `QUÉ DICE LA GUÍA` · `POR QUÉ IMPORTA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`.
- Cabecera de infraestructura: `PROPÓSITO` · `POR QUÉ EXISTE` · `QUÉ NO HACE`.
- No se copia texto de la guía oficial ni preguntas reales del examen.

Detalle en [`docs/estandares-codigo.md`](docs/estandares-codigo.md) y [`docs/estandares-flujo.md`](docs/estandares-flujo.md).
