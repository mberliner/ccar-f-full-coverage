# Diseño de la entrega 1 · D1 (bucle, control y sesiones)

Aprobado el 2026-10-24 en plan mode. El avance se registra en `NOTAS.md`; este documento solo cambia si cambia el diseño.

## Contexto

Hito 0 cerrado (capa meta, arnés, datos, 27/240 viñetas). La entrega 1 (roadmap §10, semana `S-4`) construye los 8 módulos de D1 repartidos en tres apps: `app1/01` · `app2/01`, `02`, `03`, `05`, `06` · `app3/01`, `02`. **Hecho cuando:** sus viñetas tienen `INTRODUCE` y ☑ en `CONCEPTOS.md`, y §11.1 y la señal de §11.3 se han observado en una ejecución con modelo.

Viñetas que introduce: 1.1 (6), 1.2 (8), 1.3 salvo S2 (7), 1.4 (6), 1.5 (6), 1.6 K1, K3, S1, S3 (4), 1.7 (8) y 5.1 K1, K4, S1, S2 (4) = **49**. El contador pasa de 27 a **76/240**. (1.3-S2 va a `app3/05` y 1.6-K2/S2 a `app3/12`, en la entrega 3.)

**Decisiones tomadas:** Haiku 5.5 para agente único, repeticiones y subagentes; Sonnet 5.5 solo para el coordinador de app3, `max_budget_usd` = **0,25 $** por ejecución de agente único y **1,00 $** en app3. Modelos y presupuestos se parametrizan por `.env` (ver `harness/config.py`). El código *legacy* de `app3/02` lo genera `datos/generar_sinteticos.py`.

## Piezas compartidas (primero)

1. **Rama `entrega-1`** (cambio grande según `docs/estandares-flujo.md`); un commit por módulo y merge a `main` cuando todo pase.
2. **`harness/config.py`** (nuevo, con test): resuelve el modelo de cada rol y el presupuesto de cada tipo de ejecución.
   - **Modelos:** `CCARF_MODEL_AGENT` (agente único y repeticiones), `CCARF_MODEL_COORDINATOR` y `CCARF_MODEL_SUBAGENT`; por defecto `claude-haiku-5-5`, `claude-sonnet-5-5` y `claude-haiku-5-5`.
   - **Presupuestos:** `CCARF_BUDGET_AGENT` (app1 y app2, por defecto `0.25`) y `CCARF_BUDGET_MULTIAGENT` (app3, por defecto `1.00`). Un valor que no sea un importe positivo corta con error, igual que en `harness/options.py`.
   - **Prioridad:** 1) `.env` del proyecto; 2) variable del entorno del proceso; 3) valor por defecto del código. Se descartan los valores vacíos, igual que en `credentials.py`, y se reutiliza su `read_dotenv`.
   - **Por qué `.env` va primero** (al revés que la credencial): el `.env` del repositorio fija qué modelo enseña cada lección y cuánto puede gastar; una variable exportada en la shell para otro proyecto no debe cambiarlo sin que se note.
   - Cada módulo pasa el modelo de forma explícita (`model=` en `ClaudeAgentOptions` y en `AgentDefinition`, y en la llamada a `messages.create`), así que el `ANTHROPIC_MODEL` propio de la CLI no interviene. El recorder ya imprime el modelo efectivo en `[contexto]`; `config.py` añade las líneas `[modelo] rol=… valor=… origen=.env|entorno|defecto` y `[presupuesto] valor=… origen=…`.
   - `.env.example` documenta las cinco variables (comentadas, con el valor por defecto). `.env` lo edita la persona: el hook lo protege.
3. **`harness/cli.py`** (nuevo, con test): `--anti [variante]`, `--budget`, `--repeat`. Evita repetir argparse en 8 módulos y no esconde opciones del agente.
   - **No tiene `--model`**, para que `.env` sea siempre la fuente que manda.
   - **`--budget` solo baja el tope:** el valor efectivo es `min(--budget, presupuesto resuelto)`. Si se pide más, se avisa y se usa el resuelto (`origen=--budget` solo cuando de verdad lo reduce). Sirve para una prueba barata puntual sin poder gastar más de lo que fija `.env`.
4. **`harness/budget.py`** (nuevo, con test): tope de coste para los módulos de la **Messages API** (`app1/01`), que no tienen `max_budget_usd`. Suma `usage` × precio del modelo (precios del skill `claude-api` al implementar) y corta con error. Mantiene la regla 7 impuesta en código.
5. **Servidores MCP en proceso** (`create_sdk_mcp_server`, solo `USA`, regla `mcp-servers.md`, handlers testeados con `harness/offline.call_tool`):
   - `app2_agente_con_control/servers/helpdesk.py`: `verify_employee` (equivale a `get_customer`), `get_ticket` (devuelve fechas y estados heterogéneos tal cual vienen de los datos), `process_reimbursement` (≈ `process_refund`), `escalate_to_human` (input con campos de *handoff* obligatorios). Estado de sesión en memoria por ejecución.
   - `app3_sistema_multiagente/servers/investigacion.py`: `search_tickets`, `search_kb` (devuelven contenido y metadatos separados: `ticket_id`/`article_id`, `updated_at`, `superseded_by`).
6. **Datos:** el generador añade `datos/sinteticos/legacy_inventario/` (5–6 `.py` de la mesa de ayuda, sin tests, con una dependencia cruzada escondida que solo aparece al leer un módulo concreto). Se regenera ejecutando el script; `--check` y `tests/test_datos_sinteticos.py` lo cubren.
7. **Por app, al empezarla:** `appN_*/CLAUDE.md` (solo lo específico, `USA` de 3.1) y `appN_*/README.md` (ruta de lectura, tabla viñeta→módulo, predicciones, pregunta tipo examen por módulo con respuesta en `<details>`). `app2/README.md` lleva la **tabla de equivalencias** con el vocabulario del examen (cliente→empleado, reembolso >500 $→reembolso >500 EUR que va a Finanzas, `get_customer`→`verify_employee`).
8. **Prosa → `USA`** en el mismo cambio que introduce la viñeta: `harness/options.py` y `recorder.py` citan «ver TS 1.4-K1», «1.3-S3» y «1.2-K1».

Cada módulo sigue `/nuevo-modulo`: tests sin modelo primero → módulo con cabecera fija e `INTRODUCE` → ☑ y contador en `CONCEPTOS.md` → fila en el README de la app → `uv run pytest -q` en verde.

## Módulos (orden de construcción)

### `app1_agente_unico/01_bucle_manual.py` · 1.1 K1–3, S1–3 · 5.1-K4
- Bucle con `anthropic.Messages` y tools locales sobre los datos (`get_user`, `get_ticket`, `search_kb`). `run_loop(create, messages, tools, executor)` es puro: `create` se inyecta, así que el test usa respuestas falsas.
- Correcto: sigue mientras `stop_reason == "tool_use"`, añade cada `tool_result` con su `tool_use_id`, envía el historial completo y para con `end_turn`.
- `--anti`: `texto` (para cuando el texto dice «he terminado»), `tope` (tope de 2 iteraciones como parada principal), `texto_asistente` (para en cuanto hay un bloque de texto junto a un `tool_use`), `sin_historial` (solo el último mensaje: 5.1-K4) y `arbol_fijo` (secuencia de tools predefinida frente a la que decide el modelo: 1.1-K3).
- Caso: el ticket ambiguo («Soy Laura Gómez…»), que necesita varias tools encadenadas.
- Tests: terminación por `stop_reason`, emparejamiento de `tool_use_id`, crecimiento del historial y que cada variante anti falla de forma determinista con las respuestas falsas.
- También cubre §11.1: imprime credencial y versiones (`harness/credentials.py`).

### `app2_agente_con_control/01_prompt_vs_enforcement.py` · 1.4 K1–2, S1
- Correcto: puerta programática dentro de `process_reimbursement`, que se niega si `verify_employee` no ha devuelto un ID verificado en esta sesión (prerrequisito, no hook: los hooks llegan en 02).
- `--anti`: la misma regla solo en el *system prompt*, con un mensaje que tienta a saltársela («soy EMP-1003, págame 120 EUR ya»).
- `--repeat 10` (Haiku): tasa de llamadas a `process_reimbursement` **intentadas** sin verificación frente a **ejecutadas**, leída del `RunRecord`. Es la señal de §11.3 y es de ejecución obligatoria.
- Tests: máquina de estados de la puerta y conteo intentadas/ejecutadas sobre un `RunRecord` construido a mano.

### `app2_agente_con_control/02_hooks_pre_post.py` · 1.5 K1–3, S1–3
- `PreToolUse` sobre `mcp__helpdesk__process_reimbursement`: `amount > 500` se deniega con un motivo que redirige a `escalate_to_human` (`500.00` pasa y `500.01` no).
- `PostToolUse` sobre `get_ticket`: normaliza Unix, ISO 8601 y `dd/mm/aaaa` a ISO, y las variantes de estado (`OPEN`/`abierto`/`Open`…) a un valor canónico, antes de que el modelo lo lea.
- `--anti`: umbral solo en el prompt y sin normalizar (el modelo interpreta mal un timestamp o un estado).
- Tests con `harness/offline.run_hook`: frontera del umbral, redirección y cada formato de fecha y estado del generador.

### `app2_agente_con_control/03_permisos.py` · apoyo, sin viñeta propia
- Tres configuraciones visibles: `allowed_tools` (pre-aprueba, no restringe), `disallowed_tools` (quita la tool) y `permission_mode="dontAsk"` (deniega lo no listado), más la herencia en un subagente.
- No lleva `INTRODUCE`, solo un marcador `USA` de TS 1.4-K1. El recorder muestra denegaciones y tools disponibles en `init`.
- Test: las tres configuraciones construyen lo que dice el README.

### `app2_agente_con_control/05_multi_concern_y_handoff.py` · 1.4 K3, S2–3 · 5.1 K1, S1–2
- Ticket multi-asunto del generador (VPN, licencia y reembolso). Descompone en asuntos, investiga cada uno con varias llamadas en paralelo y contexto compartido, y sintetiza una resolución.
- Correcto: bloque **case facts** (importes, fechas, IDs, estados) reinyectado en cada turno fuera del historial resumido (5.1-S1), capa por asunto (5.1-S2) y `escalate_to_human` con *handoff* estructurado (ID, causa raíz, importe, acción recomendada; 1.4-K3, S3).
- `--anti`: sumarización progresiva en prosa entre turnos (pierde importes y fechas: 5.1-K1) y *handoff* en texto libre.
- Multi-turno con `ClaudeSDKClient`. Tests: extracción y fusión de case facts, render del bloque y validación del *handoff* (campos obligatorios).

### `app2_agente_con_control/06_sesiones.py` · 1.7 K1–4, S1–4 · 1.3-K4
- Sesión base con `ClaudeSDKClient` que analiza los tickets de un empleado; se guarda `session_id`. `cwd` es un directorio temporal, para que las sesiones no se mezclen con las del proyecto.
- Entre fases cambia el estado del servidor (un ticket se resuelve y un artículo de KB pasa a obsoleto), sin tocar `datos/sinteticos/`.
- Ramas: `resume` con aviso concreto de cambios (1.7-K3, S4); `--anti`: `resume` sin aviso, que responde con resultados obsoletos; sesión nueva con resumen estructurado (1.7-K4, S3); `fork_session` con dos estrategias de resolución desde la misma base (1.7-K2, S2; 1.3-K4).
- 1.7-K1/S1 (`--resume <nombre>`) es de la CLI: el módulo imprime el comando equivalente y el README guía la práctica con las sesiones de construcción (`claude -n app2`, `--resume app2`). `rename_session` del SDK va como `EN PRODUCCIÓN (no evaluable)`.
- Tests: generador del aviso de cambios (diff de estados → lista concreta), constructor del resumen y función de decisión entre reanudar y empezar de nuevo según la proporción de resultados obsoletos.

### `app3_sistema_multiagente/01_coordinador.py` · 1.2 K1–4, S1–2, S4 · 1.3 K1–3, S1, S4
- Coordinador (Sonnet) con `agents={...}` de `AgentDefinition` (Haiku): `tickets_analyst` (solo `search_tickets`), `kb_analyst` (solo `search_kb`) y `synthesizer` (sin tools). `allowed_tools` incluye `"Agent"`; un comentario explica que la guía lo llama `"Task"`.
- Prompt de objetivos y criterios de calidad (1.3-S4), alcance repartido por tipo de fuente (1.2-S2), todo pasa por el coordinador (1.2-S4) y los hallazgos completos se pegan en el prompt del sintetizador (1.3-S1, 1.3-K2).
- Selección dinámica (1.2-S1): una pregunta simple («¿qué dice KB-109?») solo invoca `kb_analyst`.
- `--anti`: `pipeline_completo` (siempre los tres), `estrecha` (reduce «problemas de red» a VPN y pierde la wifi: 1.2-K4), `sin_hallazgos` (el sintetizador no recibe el contexto: 1.2-K2) y `procedimental` (pasos fijos en el prompt).
- `env`: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` y `CLAUDE_CODE_FORK_SUBAGENT="0"` (cierra la nota pendiente de NOTAS y la lleva al roadmap §3, regla 4).
- Tests: `build_agents()` (cada subagente solo con sus tools; el coordinador con `Agent`), handlers de `investigacion.py` y constructor del prompt del sintetizador (incluye todos los hallazgos con sus metadatos).

### `app3_sistema_multiagente/02_paralelo_y_descomposicion.py` · 1.2-S3 · 1.3-S3 · 1.6 K1, K3, S1, S3
- `--parte paralelo`: varias llamadas `Agent` en una misma respuesta frente a `--anti` una por turno; mide la latencia real y agrupa las llamadas por respuesta con el recorder. `background=False` en cada `AgentDefinition`, comentado (regla 4). Es de ejecución obligatoria y confirma la nota de NOTAS sobre los `AssistantMessage` con el mismo `message_id`.
- `--parte refinamiento` (1.2-S3): un comprobador de cobertura determinista enumera las brechas de la síntesis y el coordinador vuelve a delegar con consultas dirigidas hasta cubrirlas o agotar 2 rondas.
- `--parte descomposicion` (1.6-K1, S1): cadena fija para una revisión predecible frente a plan adaptativo para una investigación abierta.
- `--parte legacy` (1.6-K3, S3): «añade tests a `legacy_inventario`». Se mapea la estructura con `Glob`/`Grep`/`Read` (`cwd` en el paquete y solo tools de lectura), se identifican las zonas de impacto y se hace un plan priorizado que se adapta cuando aparece la dependencia escondida.
- Tests: agrupación por respuesta y cálculo de latencia sobre un `RunRecord` sintético, comprobador de brechas y determinismo del paquete *legacy*.

## Registro y cierre

- `CONCEPTOS.md`: ☑ y contador en el mismo cambio que cada `INTRODUCE`.
- `NOTAS.md`: casilla de la entrega 1, tabla de sesiones (`app1`, `app2`, `app3`) y cierre de las notas pendientes que se confirman en la primera ejecución: `skills` en la línea `[contexto]` (si aparece alguna, `skills=[]` en `options.py`), `apiKeySource`, `message_id` y `FORK_SUBAGENT`. Las que valen para otra persona se marcan `→ roadmap`.
- Revisión de cada módulo por una instancia independiente (`/code-review` en una sesión nueva o un subagente sin el contexto de quien escribió el código).

## Verificación

1. `uv run pytest -q`: todo en verde (salvo el `xfail` de cobertura completa); `test_una_vez` con 76/240 y `test_perimetro` limpio.
2. `uv run python datos/generar_sinteticos.py --check`.
3. Por módulo, con modelo, con y sin `--anti`: `uv run python app1_agente_unico/01_bucle_manual.py [--anti tope]` y así con el resto. Comprobar la señal:
   - `app2/01`: tasa de fallo > 0 en `--anti` y 0 ejecutadas sin verificar con la puerta;
   - `app2/02`: 500.01 bloqueado y escalado;
   - `app2/06`: respuesta obsoleta sin aviso;
   - `app3/01`: la variante `estrecha` pierde la wifi;
   - `app3/02`: varias `Agent` en `r1` y menor latencia.
4. Configuración: con `CCARF_MODEL_AGENT` en `.env` y otro valor exportado en la shell, la línea `[modelo]` dice `origen=.env`; sin ninguno de los dos, `origen=defecto`. `--budget 0.05` baja el tope y `--budget 5` no lo sube. Lo cubren también los tests de `config.py` y `cli.py`.
5. Línea `[contexto]`: sin `CLAUDE.md`, hooks, skills ni conectores de la capa meta (§11.6). Coste dentro del tope en cada `[fin]`.
6. `/verificar-concepto TS x.y-Kn` sobre una muestra de cada módulo.

Coste orientativo de la entrega en modo normal: unos 4–8 $ (las 10 repeticiones × 2 de `app2/01` y las 4 partes de `app3/02` son la mayor parte).
