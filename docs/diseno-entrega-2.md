# Diseño de la entrega 2 · D2 y D3 (tools, MCP y Claude Code)

Aprobado el 2026-10-25 en plan mode. El avance se registra en `NOTAS.md`; este documento solo cambia si cambia el diseño.

## Contexto

Entrega 1 cerrada y fusionada (76/240). La entrega 2 (roadmap §10, semana `S-3`) construye `app1/02`–`06`, `app3/03` y la sección D3 (`d3_claude_code/README.md`). **Hecho cuando:** sus viñetas tienen `INTRODUCE` y ☑ en `CONCEPTOS.md`, incluidas las 13 del README de D3, y la práctica propia de §4.2 queda anotada en tu `NOTAS_PERSONALES.md` (`estado/<perfil>/`).

Viñetas que introduce: 2.1 (8), 2.2 salvo S3 (7), 2.3 (9: K1, K4, S4, S5 en `app1/05`; K2, K3, S1–S3 en `app3/03`), 2.4 (9), 2.5 (9) y las 13 de D3 (3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5, 3.5 completo) = **55**. El contador pasa de 76 a **131/240**. (2.2-S3 va a `app3/04`, en la entrega 3.)

**Decisiones que se mantienen de la entrega 1:** Haiku 5.5 para agente único y subagentes, Sonnet 5.5 para el coordinador, `CCARF_BUDGET_AGENT` (0,25 $) y `CCARF_BUDGET_MULTIAGENT` (1,00 $) como topes de **toda la ejecución del script**, repartidos entre partes, configuraciones y repeticiones. No se añaden roles ni variables salvo que una sonda lo exija (ver Riesgos).

## Lecturas previas

Este diseño solo recoge lo propio de la entrega 2 y se apoya en el repositorio de estudio que nombra `CLAUDE.md`. Las rutas son relativas a la raíz de ese repositorio, esté donde esté clonado. Nada de esto se copia aquí: allí está la fuente única. Un `§` sin nombre de documento se refiere al roadmap.

| Antes de… | Leer |
| :--- | :--- |
| Cualquier módulo | `docs/roadmap-apps-demo-ccar-f.md` §2 (cabecera, regla «una vez», par `--anti`, pregunta tipo examen), §3 (perímetro y aislamiento, reglas 3, 4 y 7), §4.3 (trampas ya conocidas) y §13 (ciclo del README) |
| `QUÉ DICE LA GUÍA` y las preguntas de cada módulo | `docs/resumen-guia-examen-ccar-f.md` §6, la Task Statement del módulo (2.1–2.5, 3.1–3.5) |
| `app1/03`, `04` y `06` | El mismo resumen, §8: Exercise 1 (tools parecidas y errores estructurados) y Exercise 2 (`.mcp.json` y `~/.claude.json`) |
| `app1/05` | `docs/conceptos-generales.md` §4.2 (`tool_choice`) y §4.6 (400 con `any` y forzado) |
| `app1/06` y D3 | `docs/conceptos-generales.md` §4.5 (ámbitos compartido y personal) y §4.6 (`/memory`, `argument-hint`) |
| `app1/02`–`06` y `app3/03` | `docs/roadmap-apps-demo-ccar-f.md` §6 y §8 (las filas del módulo) |
| `d3_claude_code/README.md` | `docs/roadmap-apps-demo-ccar-f.md` §4.1, §4.2 y §11 (pasos 5 y 6) |
| Cierre de la entrega | `docs/roadmap-apps-demo-ccar-f.md` §10 (fila de la entrega 2) |

## Piezas compartidas (primero)

1. **Rama `entrega-2`**, con un commit por módulo y merge a `main` cuando todo pase.
2. **Datos** (`datos/generar_sinteticos.py`, con `--check` y test de determinismo):
   - `repo_mesa/`: un paquete pequeño de la mesa de ayuda para `app1/02`.
     - `core/sla.py` con `calcular_sla`.
     - Un *wrapper* `api.py` que la reexporta con alias (`from .core.sla import calcular_sla as sla_ticket`).
     - Llamadores directos y por alias en varios módulos, y un mensaje de error único («SLA vencido para…») para buscar con `Grep`.
     - Tests `test_*.py` repartidos en varios directorios, para `Glob`.
     - `config.py` con un ancla repetida (`TIMEOUT = 30` dos veces, en bloques distintos), para que `Edit` falle por no ser única.
   - `documentos.json`: un catálogo de URLs para `app3/03`, unas de documentos (`/docs/…`, con contenido) y otras que no lo son (login, tracking, una imagen). También guarda, para cada afirmación de prueba, si es verificable de forma simple o compleja.
   - El catálogo de *resources* de `app1/06` se deriva de `articulos_kb.json` y no necesita archivo nuevo.
3. **`harness/data.py`: `copy_to_temp(name) -> Path`** (con test). Copia un conjunto de `datos/sinteticos/` a un directorio temporal que sirve de `cwd`. Lo usan `app1/02` (porque `Edit`/`Write` escriben) y `app1/06` (porque genera ahí su `.mcp.json`). Así `datos/sinteticos/` no se toca nunca.
4. **Servidores MCP** (regla `mcp-servers.md`: solo `USA`, handlers testeados con `harness/offline.call_tool`):
   - **`app1_agente_unico/servers/mesa.py`**, en proceso. Contiene **familias de tools que se eligen por parámetro**, para que cada módulo monte la que enseña:
     - `routing`: `analyze_content`/`analyze_document` con descripción mínima frente a `extract_ticket_facts` + `extract_article_steps`, `summarize_article` y `verify_claim_against_article`, con descripciones completas (03).
     - `errores`: tools que fallan de forma transitoria, de validación, de negocio y de permisos, y una búsqueda sin coincidencias (04). Un parámetro elige entre errores estructurados y genéricos.
     - `amplio`: 18 tools frente a `acotado`, que tiene 5 (05).
   - **`app1_agente_unico/servers/catalogo_stdio.py`**: servidor stdio con `mcp` (FastMCP, ya instalado en la versión 2.3.0). Expone `search_kb` y `get_article`, y el catálogo de artículos como *resources*. Lee un token de su entorno y solo informa de si lo recibió, sin mostrarlo (06).
   - **`app3_sistema_multiagente/servers/investigacion.py`** (ampliación): `fetch_url` (genérica), `load_document` (valida que la URL sea de documento y, si no, devuelve un error de validación) y `verify_fact` (acotada: solo afirmaciones simples; las complejas devuelven «enrutar al coordinador»).
5. **Prosa → `USA`** en el mismo cambio que introduce 2.2: `helpdesk.error` y `investigacion.validation_error` ya devuelven `errorCategory`/`isRetryable`. Reciben el marcador `USA` de TS 2.2-K1 y TS 2.2-S1, igual que `.claude/rules/mcp-servers.md`, que lleva el marcador como comentario HTML.
6. **Por app:**
   - `app1_agente_unico/CLAUDE.md`: se actualiza la línea de servidores (ya existen `servers/`) y se añade la excepción `setting_sources=["project"]` de 06.
   - `app1/README.md` y `app3/README.md`: una sección por módulo, con su comando, predicciones, qué observar y una pregunta tipo examen en `<details>`.
   - `d3_claude_code/README.md`: nuevo.

Cada módulo sigue `/nuevo-modulo`: tests sin modelo primero → módulo con cabecera fija e `INTRODUCE` → ☑ y contador en `CONCEPTOS.md` → sección en el README → `uv run pytest -q` en verde.

## Módulos (orden de construcción)

### `app1_agente_unico/02_tools_integradas.py` · 2.5 K1–4, S1–5
- Agent SDK con `tools=["Read", "Write", "Edit", "Grep", "Glob"]` y `cwd` en la copia temporal de `repo_mesa/`.
- `--parte busqueda` (K1, K2, S1, S2): «¿quién llama a `calcular_sla`?» (con `Grep`) y «lista todos los tests» (con `Glob`). `--anti sin_grep`: sin `Grep`, el modelo tiene que leer archivo por archivo. Se comparan llamadas, `Read` y coste.
- `--parte incremental` (S4): «explica cómo se calcula el SLA de un ticket». Lo correcto es empezar con `Grep` para encontrar el punto de entrada y seguir con `Read` los imports. `--anti leer_todo`: el prompt pide leer todos los archivos antes de responder. Se comparan los `Read` y el coste.
- `--parte wrapper` (S5): «encuentra todos los usos de `calcular_sla`». Lo correcto es sacar primero los nombres exportados de `api.py` y buscar cada uno. `--anti solo_nombre`: buscar solo el nombre original pierde los llamadores por alias. Un comprobador determinista compara los archivos de la respuesta con los llamadores esperados, que se calculan con `ast`.
- `--parte edicion` (K3, K4, S3): «cambia el segundo `TIMEOUT = 30` a 60». `Edit` falla por coincidencia no única y el respaldo es `Read` + `Write`. Se observa en el recorder (`Edit` con `is_error` y después `Write`), y un comprobador verifica el archivo final: cambió solo el segundo bloque. El modelo también puede ampliar el ancla: es válido y el README lo comenta.
- Tests: llamadores esperados con `ast` sobre `repo_mesa`, comprobador de la respuesta, precondición de que el ancla aparece exactamente dos veces y comprobador del archivo editado.

### `app1_agente_unico/03_servidor_mcp.py` · 2.1 K1–4, S1–4
- Batería de 6 peticiones de mesa de ayuda, cada una con su tool esperada. Cada petición se envía con `query()` y se registra la **primera** llamada MCP, para medir la tasa de acierto de enrutamiento por configuración.
- Configuraciones:
  - **Correcta:** tools renombradas y divididas, con descripciones que dicen propósito, formato de entrada, ejemplo de consulta, casos borde y en qué se diferencian de la tool parecida (K2, S1–S3).
  - `--anti minimas`: `analyze_content`/`analyze_document` con descripciones de una línea, que se solapan (K1, K3).
  - `--anti palabra_clave`: las descripciones buenas, pero el *system prompt* dice «si aparece la palabra "documento", usa `summarize_article`», lo que anula las descripciones en dos peticiones (K4). La corrección (S4) es la configuración correcta.
- Tests: tasa de acierto sobre un `RunRecord` construido a mano y contrato de cada tool dividida (entrada y salida).

### `app1_agente_unico/04_errores_estructurados.py` · 2.2 K1–4, S1, S2, S4
- Un ticket que obliga a llamar a cuatro tools. Una sufre un *timeout* la primera vez (`transient`, `isRetryable: true`), otra recibe un ID mal formado (`validation`), otra choca con una regla de negocio y la última no tiene permiso (`permission`). La regla de negocio es reasignar una licencia por encima del cupo, con `isRetryable: false` y un mensaje para la persona usuaria; la guía, en S2, lo escribe `retriable: false` y el comentario lo señala. Además, una búsqueda de tickets sin coincidencias devuelve una lista vacía válida, que no es error (S4).
- **Correcta:** el agente reintenta solo el transitorio, explica la regla de negocio sin reintentarla y distingue «no hay tickets» de «no se pudo consultar».
- `--anti generico`: todos los errores devuelven `"Operation failed"` (K3). Se esperan reintentos inútiles o una explicación equivocada.
- `--anti fallo_como_vacio`: el *timeout* devuelve `[]`, y el agente afirma que no hay tickets (S4).
- Señal: reintentos por tool y categoría, leídos del `RunRecord`.
- Tests: forma de cada error, la secuencia del transitorio (falla y luego responde), el contador de reintentos y la diferencia entre vacío válido y fallo de acceso.

### `app1_agente_unico/05_scoping_y_tool_choice.py` · 2.3 K1, K4, S4, S5
- `--parte scoping` (K1): Agent SDK con la familia `amplio` (18 tools, varias casi solapadas) frente a `acotado` (5), con la misma batería de peticiones y el acierto medido igual que en 03. *Tool search* se apaga en `env`, comentado (roadmap §3, regla 4). El nombre exacto de la variable se comprueba contra la CLI fijada antes de codificar, y el recorder confirma `tool_search_loads == 0`.
- `--parte tool_choice` (K4, S4, S5), con la Messages API (`harness/budget.CostGuard`, como en `app1/01`):
  - La misma petición con `auto` (puede responder en texto), con `any` (siempre una tool, S5) y con `{"type": "tool", "name": "extract_ticket_metadata"}` forzada en el primer turno, seguida de `auto` en los siguientes para el enriquecimiento (S4).
  - Se imprime si cada respuesta empieza por `tool_use` o por texto.
  - Comentario `EN PRODUCCIÓN (no evaluable)`: `any` y forzado devuelven 400 en Opus 5.5, Sonnet 5.5 y Fable 5.1 (`conceptos-generales.md` §4.6). En el examen manda la guía.
- Tests: constructor de la petición por modo, la secuencia forzado → `auto` y el clasificador de la primera respuesta (`tool_use` o texto).

### `app1_agente_unico/06_mcp_config.py` · 2.4 K1–4, S1–5
- Genera en la copia temporal un `.mcp.json` con dos servidores stdio: `catalogo` (el de `servers/catalogo_stdio.py`) y un segundo pequeño (`inventario`, con una tool). Ambos se lanzan con `uv run --no-sync --project <raíz> python …`. El token va como `"env": {"CATALOGO_TOKEN": "${CCARF_DEMO_TOKEN}"}`, y el módulo pone un valor sintético en `CCARF_DEMO_TOKEN` (K2, S1). Se ejecuta con `setting_sources=["project"]`, la excepción ya prevista en `harness/options.py`, más el servidor en proceso de `mesa.py` por `mcp_servers`.
- La línea `[contexto]` muestra las tools de todos los servidores a la vez (K3). El servidor confirma que recibió el token, sin mostrarlo.
- **Ámbito de usuario** (K1, S2): solo en comentario y en el README, con el comando `claude mcp add --scope user …` impreso y no ejecutado. No se toca `~/.claude.json`.
- `--parte recursos` (K4, S5): con el catálogo como *resources*, el agente sabe qué artículos hay. `--anti sin_recursos`: tiene que hacer llamadas exploratorias (`search_kb` repetidas). Se cuentan las llamadas exploratorias.
- `--parte descripcion` (S3): en el mismo `cwd` están los artículos como archivos y el agente tiene `Grep` y `Read`. `--anti descripcion_minima`: `search_kb` con una línea de descripción, y el agente prefiere `Grep`. Lo correcto es una descripción que detalla capacidades y salidas (ranking y filtrado de obsoletos con `superseded_by`), y entonces usa la tool MCP. Se cuentan `Grep` frente a `mcp__catalogo__search_kb`.
- **Comunitario frente a propio** (S4): tabla de decisión en la cabecera y en el README (Jira o GitHub → servidor comunitario; el flujo propio de la mesa → servidor propio). No lleva código.
- Tests: el `.mcp.json` generado (estructura y `${VAR}` sin expandir en el archivo), los handlers y *resources* del servidor stdio (`call_tool` en proceso de FastMCP) y el contador de llamadas exploratorias.

### `app3_sistema_multiagente/03_tools_entre_roles.py` · 2.3 K2, K3, S1–S3
- El mismo patrón que `app3/01` (coordinador Sonnet y subagentes Haiku con `AgentDefinition`, `tools=["Agent"]` en el coordinador; en `env`, `FORK_SUBAGENT="0"`, `DISABLE_BACKGROUND_TASKS="1"` y `MAX_SUBAGENT_SPAWN_DEPTH=1`).
- **Correcta (S1):** `researcher` con `search_kb` y `load_document`, y `synthesizer` solo con `verify_fact`. Las verificaciones complejas vuelven al coordinador (K3, S3).
- `--anti todas` (K2): el sintetizador tiene todas las tools y se pone a buscar.
- `--anti fetch_url` (S2): el investigador tiene `fetch_url` genérica, abre URLs que no son documentos y las mete en los hallazgos.
- `--anti sin_verify` (S3): sin `verify_fact`, cada comprobación simple da una vuelta por el coordinador.
- Señal: llamadas por agente fuera de su rol (`RunRecord.by_agent()`), URLs no válidas cargadas y número de delegaciones.
- Tests: `build_agents()` por variante (tools de cada rol), `load_document` (acepta solo documentos), `verify_fact` (simple frente a compleja) y el contador de llamadas fuera de rol.

### `d3_claude_code/README.md` · 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5, 3.5 K1–4, S1–5
- **Ruta por los archivos reales:** tabla de las 27 viñetas que ya tienen marcador, con el archivo de la capa meta donde está su `INTRODUCE` y un `USA` en el README. La tabla se genera a partir de `CONCEPTOS.md` y de un `grep` de los marcadores, para que no se desalinee.
- **Las 13 nuevas, cada una como comentario HTML `INTRODUCE`**, con ejemplos de este proyecto:
  - **3.1-S1** (diagnóstico de jerarquía): una regla puesta en `~/.claude/CLAUDE.md` no llega a otra sesión abierta con otro `CLAUDE_CONFIG_DIR`. Es el mismo motivo de la regla de directivas de `docs/estandares-flujo.md`.
  - **3.1-S4** (`/memory`): incluye la diferencia con el producto (`/context` y la línea `Loaded`, `conceptos-generales.md` §4.6).
  - **3.2-K4** (variantes personales): en `~/.claude/skills/`, con otro nombre (por ejemplo `verificar-concepto-rapido`), sin tocar la de proyecto.
  - **3.2-S5** (skill frente a `CLAUDE.md`): `verificar-concepto` frente a las reglas de `CLAUDE.md`.
  - **3.5** (refinamiento iterativo):
    - ejemplos de entrada/salida: los formatos de fecha del hook de `app2/02`;
    - tests primero: `/nuevo-modulo`;
    - *interview pattern*: el diseño de la capa meta en el hito 0;
    - casos con entrada y salida esperada para casos borde: los 500.00 y 500.01 $;
    - problemas que interactúan en un solo mensaje, y los independientes de uno en uno: la revisión de 21 hallazgos de la entrega 1.
- **Guion comentado:** reglas por ruta frente a `CLAUDE.md` por subdirectorio, y plan mode frente a ejecución directa con las 3 complejidades del Exercise 2 (bug en un archivo, migración multi-archivo y funcionalidad con varios enfoques), usando esta misma entrega como caso: diseño en plan mode y módulos en ejecución directa.
- **Práctica propia** (la hace la persona en su sesión):
  - la verificación de §11.5;
  - un cambio multi-archivo pequeño con plan mode: por ejemplo, una variante `--anti` nueva en `app1/03` con su test y su README;
  - uno acotado con ejecución directa: por ejemplo, ajustar un mensaje de error de `mesa.py` con su test;
  - anotar en tu `NOTAS_PERSONALES.md` cuál eligió para cada cambio y por qué.
- **3 preguntas tipo examen** (una de 3.1 y 3.3, otra de 3.2 y otra de 3.4 y 3.5), con la respuesta en `<details>`.
- `tests/test_una_vez.py` ya acepta el destino `d3` en `d3_claude_code/`, `.claude/` y `docs/`, así que no hay que tocarlo.

## Riesgos y sondas (antes de codificar el módulo afectado)

- **`app1/06`: aprobación de los servidores de `.mcp.json`.** Con `setting_sources=["project"]`, la CLI puede exigir que se aprueben. Una sonda barata lo comprueba. Si hace falta, el `cwd` de prueba lleva su propio `.claude/settings.json` con `enableAllProjectMcpServers: true`, comentado. → Si se confirma, `docs/hallazgos.md` y `→ roadmap` (§4.3).
- **`app1/05` `tool_choice`:** comprobar que Haiku 5.5 acepta `any` y el forzado. Si devuelve 400, la parte usa el rol `enforcement` (Haiku 4.5), con el mismo precedente que `app2/01`, y se anota como cambio de diseño.
- **`app1/05` scoping y `app1/03` enrutamiento: la señal puede no verse** con Haiku 5.5, que podría acertar igual con 18 tools o con descripciones mínimas. Primero se ejecuta con Haiku 5.5. Si no hay diferencia, se usa el rol `enforcement` en las dos variantes, igual que en `app2/01`, y se anota.
- **Nombre de la variable de *tool search*** y forma de las tools de *resources* en la CLI fijada (`ListMcpResources`/`ReadMcpResource`): se comprueban en el `init` de la primera ejecución y no se inventan (roadmap §2).

## Modelo de la sesión de construcción

Es el modelo de la sesión de Claude Code que construye la entrega. Los modelos con los que se ejecutan las apps los fijan `.env` y `harness/config.py`, y no cambian.

| Fase | Modelo | Por qué |
| :--- | :--- | :--- |
| Datos, `copy_to_temp`, servidores y sus tests | Sonnet 5.5 | Trabajo mecánico que validan los tests |
| Código y tests de `app1/02`–`06` y `app3/03` | Sonnet 5.5 | Siguen el patrón de la entrega 1; los tests sin modelo y las ejecuciones con `--anti` muestran si funcionan |
| Sondas de «Riesgos» | Sonnet 5.5 | Se ejecutan de verdad y su resultado se anota en `docs/hallazgos.md`; no se da nada por supuesto (roadmap §2) |
| Cabeceras `QUÉ DICE LA GUÍA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`, preguntas tipo examen y `d3_claude_code/README.md` | Opus 5.5 | Piden criterio didáctico (distractores plausibles, sin copiar la guía, guía frente a producto) y ningún test lo comprueba |
| Revisión por una instancia independiente, antes del merge | Opus 5.5 | Es la última barrera, sobre todo para lo que no cubren los tests. Si se hace con un subagente, se le asigna Opus al lanzarlo y la sesión no tiene que cambiar de modelo |
| Rehacer una pieza que la revisión señale como floja | Opus 5.5 | Solo esa pieza, no el módulo entero |

**El cambio se pide, no se asume.** La sesión no puede cambiar su propio modelo. Al empezar una fase cuyo modelo no es el de la sesión actual, se detiene, dice qué fase empieza y qué modelo le corresponde, y pide a la persona que lo cambie con `/model`. No sigue hasta que la persona lo confirma o decide quedarse con el modelo actual. Si la persona se queda con el actual, se anota en `NOTAS.md`.

**Orden dentro de cada módulo:** primero, con Sonnet, el código, los tests y una cabecera con los campos técnicos; después, con Opus, los textos de cabecera de la guía y la sección del README con su pregunta. Para no cambiar de modelo en cada módulo, los textos con Opus pueden agruparse: por ejemplo, todos los de `app1` antes de empezar `app3/03`.

## Registro y cierre

- `CONCEPTOS.md`: ☑ y contador en el mismo cambio que cada `INTRODUCE`.
- `NOTAS.md`: casilla de la entrega 2.
- `docs/hallazgos.md`: resultado de las sondas y notas nuevas `→ roadmap`.
- Tu `NOTAS_PERSONALES.md`: tabla de sesiones (`app1`, `app3` y `d3`).
- Revisión de cada módulo por una instancia independiente (un subagente sin el contexto de la sesión que escribió el código), antes del merge.

## Verificación

1. `uv run pytest -q`: todo en verde (salvo el `xfail` de cobertura completa); `test_una_vez` con 131/240 y `test_perimetro` limpio.
2. `uv run python datos/generar_sinteticos.py --check`.
3. Por módulo, con modelo, con y sin `--anti`. Señales que hay que comprobar:
   - `app1/02`: `sin_grep` y `leer_todo` con más `Read` y más coste; `solo_nombre` pierde los llamadores por alias; `Edit` falla y el respaldo `Read` + `Write` deja bien el archivo.
   - `app1/03`: menor acierto con `minimas` y con `palabra_clave`.
   - `app1/04`: con `generico`, reintentos inútiles o una explicación equivocada; con `fallo_como_vacio`, «no hay tickets».
   - `app1/05`: acierto con 18 frente a 5 tools y `tool_search_loads == 0`; con `any` o forzada, la respuesta siempre empieza por `tool_use`.
   - `app1/06`: tools de los tres servidores en `[contexto]`, token recibido, menos exploración con *resources* y `Grep` preferido con `descripcion_minima`.
   - `app3/03`: llamadas fuera de rol con `todas`, URL no válida con `fetch_url` y más delegaciones con `sin_verify`.
4. `[contexto]` sin la capa meta (§11.6). En `app1/06`, solo el `.mcp.json` del `cwd` temporal, no el del repositorio. Coste dentro del tope en cada `[fin]`.
5. `/verificar-concepto TS x.y-Kn` sobre una muestra de cada módulo y de D3.
6. La práctica propia de D3 queda anotada en tu `NOTAS_PERSONALES.md` (lo hace la persona).

Coste orientativo de la entrega en modo normal: unos 3–6 $. La mayor parte se va en `app3/03` (Sonnet como coordinador, 4 variantes) y en las baterías de `app1/03` y `app1/05`.
