# NOTAS

Avance de construcción del proyecto: igual para todo el mundo y versionado. Los hallazgos de producto están en [docs/hallazgos.md](docs/hallazgos.md); las sesiones, la práctica propia y los fallos son personales y viven en `estado/<perfil>/` (plantillas en `plantillas/estado/`).

Marcas para el roadmap (flujo en `docs/estandares-flujo.md`): `→ roadmap` pendiente de llevar; `✓ roadmap <fecha> §x` ya está allí y manda lo de allí.

## Hitos (roadmap §10)

El roadmap es una plantilla sin seguimiento: el avance vive aquí y el criterio de cada hito es su columna «Hecho cuando».

**Hito 0** (cerrado el 2026-10-24):

- [x] Esqueleto de directorios, `pyproject.toml` con SDK fijado, `NOTAS.md`, `FALLOS.md`
- [x] Aislamiento de las sesiones de construcción (comprobado con `/memory`, `/mcp` y `/plugin`, 2026-10-23)
- [x] `git init` y `uv sync`
- [x] `CONCEPTOS.md` con las 240 filas (solo identificadores y módulo, sin texto de la guía)
- [x] Test «una vez por viñeta» y test de perímetro
- [x] Arnés: `options.py`, `recorder.py`, `offline.py`, `credentials.py`, con sus tests sin modelo (2026-10-23)
- [x] `datos/generar_sinteticos.py`: usuarios, tickets (con etiquetas aparte) y artículos de KB, deterministas y con `--check`; los conjuntos de las entregas 2 y 3 se añaden con su módulo (2026-10-24)
- [x] Capa meta §4.1: `docs/estandares-*.md`, `.claude/rules/`, skill, comando, permisos y hooks; 27 viñetas de D3 con su `INTRODUCE` (2026-10-24)
- [x] Verificación §11.5 de la capa meta en una sesión nueva (2026-10-24):
  - `/memory` lista `CLAUDE.md` y sus dos `@import`.
  - La skill corre en fork, con argumento y sin él.
  - `datos/sinteticos/` queda protegido: la regla `deny` actúa en `Edit` y el hook en la shell.
  - Regla por ruta: `apps-comentarios.md` no se carga al leer un `.md` y sí al leer un `.py` de `app*/`, con línea `Loaded` y contenido en contexto; `tests.md` se carga al leer un test fuera de `app*/` (glob por tipo de archivo).
- [x] `ANTHROPIC_API_KEY` disponible desde `.env` (plantilla en `.env.example`); `credentials.py` la detecta. Clave válida y `apiKeySource=ANTHROPIC_API_KEY` en la línea `[contexto]` de la primera ejecución con modelo (2026-10-24)

**Entregas:**

- [x] Entrega 1 · D1 (`S-4`): diseño aprobado en `docs/diseno-entrega-1.md` (2026-10-24). Construida en la rama `entrega-1` y fusionada a `main` (2026-10-24):
  - [x] Arnés: `config.py`, `cli.py`, `budget.py`, `data.py`; `skills=[]` por defecto en `options.py`; el recorder guarda `session_id` y el texto de cada resultado.
  - [x] 8 módulos con `INTRODUCE` y ☑: 49 viñetas, 76/240. `pytest` en verde y `generar_sinteticos.py --check` limpio.
  - [x] §11.1 observado: credencial, versiones, `[modelo]` y `[presupuesto]` con su origen.
  - [x] Señales con modelo: `app2/02` (500.01 denegado y escalado; fecha y estado normalizados), `app2/05` (sin case facts se pierde la fecha de compra), `app2/06` (sin aviso responde con datos viejos), `app3/01` (`estrecha` pierde la wifi; `simple` solo invoca `kb_analyst`), `app3/02` (3 `Agent` en `r1`, ×1,66 de latencia).
  - [x] **Señal de `app2/01`** (2026-10-24):
    - Con Haiku 5.5, 0 pagos sin verificar en 40 ejecuciones sin puerta, con cuatro mensajes distintos.
    - Con `claude-haiku-4-5` (el modelo más simple disponible para la clave, consultado con `models.list()`): sin puerta, 8 de 10 pagaron sin verificar; con puerta, 9 de 10 lo intentaron y 0 de 10 pagaron.
    - `app2/01` tiene su propio rol, `enforcement` (`CCARF_MODEL_ENFORCEMENT`, por defecto Haiku 4.5), en sus dos variantes; el resto de módulos sigue con Haiku 5.5. El ×10 de coste queda limitado a este módulo (cambio de diseño anotado en `docs/diseno-entrega-1.md`). Presupuesto propio `CCARF_BUDGET_ENFORCEMENT` (0,50 $): con 0,25 $ y `--repeat 10`, la variante con puerta usaba de media el 95 % del tope de cada repetición (máximo 106 %) y la variante anti, el 54 %.
  - [x] Prioridad de `.env` con el `.env` real (diseño, verificación 4; 2026-10-24): con las cinco `CCARF_*` en `.env` y otros valores exportados en la shell, todas las líneas dicen `origen=.env`. Con `CCARF_MODEL_AGENT` falso exportado, `app1/01` (Messages API) y `app2/02` (Agent SDK) se ejecutaron con `claude-haiku-5-5`. `--budget 5` no sube el tope y `--budget 0.05` lo baja.
  - [x] Revisión por una instancia independiente (subagente sin el contexto de la sesión que escribió el código, 2026-10-24): 21 hallazgos, ninguno de gravedad alta, todos aplicados. Los principales: el conteo de pagos ejecutados de `app2/01` sale ahora del estado de la puerta; el hook de umbral falla en cerrado; presupuestos repartidos; y la señal de dependencia escondida, que antes daba falsos positivos.
  - [x] Merge a `main` (2026-10-24).
  - **Criterio de presupuesto** (decidido en la revisión): `CCARF_BUDGET_*` es el tope de **toda la ejecución del script**. Se reparte entre `--repeat`, configuraciones, turnos o ramas; el diseño decía «por ejecución» sin precisarlo.
  - **`resume` y `fork_session`: el `total_cost_usd` es acumulado y `resume` modifica la base** (comprobado 2026-10-24, sonda desechable con Haiku 5.5, ~0,01 $): ✓ roadmap 2026-10-24 §4.3 y §7 (`app2/06`):
    - `total_cost_usd` de una sesión reanudada o bifurcada = coste de la historia de la sesión + coste propio. Con una base de 0,00285 $ y una reanudación trivial: 0,00358 $ = 0,00285 + 0,00073, y 0,00073 $ es justo el valor de los 5830 tokens de caché escritos en esa ejecución. Con base barata, igual.
    - `resume` sin `fork_session` conserva el `session_id` y añade su turno a la sesión base: un fork posterior ve ese turno (preguntado: recuerda ALFA y BRAVO) y su coste acumulado incluye el de la reanudación.
    - Efecto en `app2/06 --rama todas`: antes, `reanudar` iba antes que los forks, que no partían de la base «limpia» y arrastraban ese coste. Corregido el 2026-10-24: `reanudar` va la última. Ejecutado `app2/06` completo tras el cambio (2026-10-24): base 0,0016 $; sesión nueva 0,0014 $; forks 0,0025 y 0,0026 $ (el segundo no arrastra al primero); reanudar 0,0024 $ con el mismo `session_id` que la base. README de app2 ampliado con predicción, observaciones y estos dos hechos.
- [ ] Entrega 2 · D2 y D3 (`S-3`)
  - [x] Diseño aprobado en `docs/diseno-entrega-2.md` (2026-10-25): 55 viñetas, 76 → 131/240. Siguiente paso: rama `entrega-2`, piezas compartidas (datos, `copy_to_temp`, servidores) y después `app1/02`. Antes de los módulos afectados, las sondas de la sección «Riesgos» (aprobación de `.mcp.json`, `tool_choice` con Haiku 5.5, variable de *tool search*).
  - [x] Piezas compartidas en la rama `entrega-2` (2026-10-26), con modelo de la sesión Sonnet 5.5 según el diseño: `repo_mesa/` y `documentos.json` en el generador, `copy_to_temp`, `servers/mesa.py` (familias `routing`, `errores`, `amplio`/`acotado`), `catalogo_stdio.py` e `inventario_stdio.py` (stdio, probados lanzando el script desde otro `cwd`) y `investigacion.py` ampliado con `extended=True` (por defecto sigue igual para `app3/01` y `app3/02`). `pytest`: 303 en verde.
  - **Cambios respecto al diseño:** `FastMCP` es `MCPServer` en mcp 2.x (corregido en el diseño); un tool de `MCPServer` no admite `CallToolResult` en una unión de tipos, así que se anota `-> Any`. Los `USA` de TS 2.2-K1/S1 en `mesa.py`, `helpdesk.py` e `investigacion.py` y en `mcp-servers.md` se añaden con `app1/04`, que introduce 2.2 (`test_una_vez` no admite un `USA` sin su `INTRODUCE`); mientras, `mesa.py` lo cita en prosa.
  - [x] `app1/02_tools_integradas` (2026-10-26): 9 viñetas con `INTRODUCE` y ☑, 85/240; `pytest` 325 en verde. Código y tests con Sonnet 5.5; la cabecera `QUÉ DICE LA GUÍA` · `ANTI-PATRÓN` y la sección del README (con su pregunta) son un primer borrador de Sonnet y **quedan para la pasada con Opus 5.5** (agrupada con los demás módulos de `app1`, según el diseño).
    - Cambio de diseño: la primera pregunta de `--parte busqueda` localiza el mensaje de error «SLA vencido para…» (2.5-S1) y no los llamadores de `calcular_sla`, que ya son el reto de `--parte wrapper` (S5).
    - [x] Pasada con Opus 5.5 de los textos didácticos (2026-10-26): cabecera parafraseada de nuevo contra la TS 2.5, con nota sobre `Bash` (en el enunciado, sin viñeta) y `ANTI-PATRÓN` dividido en hechos de la guía e inferencias propias; en el README, predicciones más abiertas y tabla «Qué observar» con el riesgo de `Write` en `edicion`. La pregunta tipo examen se mantiene. Sin cambios de lógica ni de tests.
    - [x] Ejecutado con modelo (2026-10-26, Haiku 5.5, `--repeat 3`, ~0,05 $ en total) tras la pasada de Opus:
      - `wrapper`: 4/4 llamadores en las 3 ejecuciones correctas y 2/4 con `solo_nombre` en las 3 (siempre faltan `informes/resumen.py` y `notificaciones/avisos.py`).
      - `incremental`: correcta con 3–4 `Read` y ~0,0012 $; `leer_todo` con 14 `Read` y ~0,0022 $ (×1,8).
      - `busqueda`: `Grep` + 0 `Read` para el error y `Glob` para los tests; con `sin_grep`, 2 `Read` más en el error (~×1,4–2 de coste). La pregunta de los tests no cambia: usa `Glob` en ambas.
      - `edicion`: sin petición especial, `Edit` no falla ni con Haiku 5.5 (0/3) ni con Haiku 4.5 (0/8): el modelo amplía el ancla tras el `Read`. **Decidido (2026-10-26): provocar el fallo en el prompt** (un único `Edit` con `old_string` exacto, sin nombrar `Read`/`Write`). Resultado: `Edit` falla en 3/6, siempre recuperado con `Edit` de más contexto (nunca `Write`), archivo correcto 6/6. Detalle y los otros dos hallazgos (ruta corta de Windows, tool inexistente) en `docs/hallazgos.md`.
      - Arreglo: `copy_to_temp` devuelve la ruta resuelta (con la corta, `Edit` salía denegado).
    - Pendiente: revisión por una instancia independiente.
  - [x] Sonda de `.mcp.json` (2026-10-26): los servidores se conectan sin aprobación con `setting_sources=["project"]`; el `.claude/settings.json` de reserva no hace falta en `app1/06`. Detalle en `docs/hallazgos.md`.
  - [x] `app1/03_servidor_mcp` (2026-10-26): 8 viñetas con `INTRODUCE` y ☑, 93/240; `pytest` 336 en verde. Cabecera y README son borrador de Sonnet: **quedan para la pasada con Opus 5.5**.
    - Con modelo (Haiku 5.5, 6 peticiones × 3, ~0,03 $): correcta 18/18; `minimas` 15/18 (solo falla `articulo-resumen`, 3/3); `palabra_clave` 12/18 (las 2 peticiones con «documento», 3/3 cada una).
    - Riesgo del diseño («la señal puede no verse con Haiku 5.5»): la señal de `minimas` es moderada (-17 puntos) y la de `palabra_clave` es fuerte; no se pasa al rol `enforcement`. Si se quisiera más caída en `minimas`, es la variante a repetir con Haiku 4.5 (~×15 de coste).
    - Pendiente: revisión independiente.
  - [x] `app1/04_errores_estructurados` (2026-10-26): 7 viñetas con `INTRODUCE` y ☑, 100/240; `pytest` 348 en verde. Cabecera y README son borrador de Sonnet (**pasada con Opus pendiente**). Los `USA` de TS 2.2-K1/S1 ya están en `mesa.py`, `helpdesk.py`, `investigacion.py` y `mcp-servers.md`.
    - Con modelo (Haiku 5.5, 5 ejecuciones por variante, ~0,02 $): correcta 5/5 con 1 reintento útil (transitorio) y 0 inútiles; `generico` 5/5 con 1 reintento inútil (`export_audit_log`); `fallo_como_vacio` 5/5 sin reintentar el transitorio y 4/5 afirmando que no hay histórico.
    - La rama de validación no se ejercita en ejecución: el modelo corrige el ID por la descripción (hallazgo en `docs/hallazgos.md`).
    - Sonda con Haiku 4.5 (2026-10-26, ~0,12 $): validación tampoco (0/10) y `generico` sin reintentos inútiles; sí se rinde ante el timeout (2/5 con metadatos, 0/5 con error genérico). Se mantiene Haiku 5.5 como rol del módulo.
  - [x] Sondas de `app1/05` (2026-10-26): `tool_choice` `any` y forzado funcionan con Haiku 5.5 y 4.5 y dan 400 con Sonnet 5.5 (la parte `tool_choice` usa el rol `agent`, sin `enforcement`); la variable es `ENABLE_TOOL_SEARCH`, pero ningún valor activó la carga diferida con 18 tools en proceso, así que el efecto no se puede demostrar (se fija en `env` como precaución y se confirma `tool_search_loads == 0`). Detalle en `docs/hallazgos.md`.
  - [x] `app1/05_scoping_y_tool_choice` (2026-10-26): 4 viñetas con `INTRODUCE` y ☑, 104/240; `pytest` 365 en verde. Cabecera y README son borrador de Sonnet (**pasada con Opus pendiente**).
    - `tool_choice` (Haiku 5.5, 6 repeticiones): `auto` 0/6 empiezan por tool, `any` 6/6, forzado 6/6 (la petición es de opinión a propósito: con «¿qué te parece?» `auto` también llamaba a la tool).
    - `scoping`: 30/30 con 5 y con 18 tools (Haiku 5.5) y 18/18 en ambas (Haiku 4.5), **sin caída de acierto**; la señal es el coste (+36 % con Haiku 5.5, +58 % con Haiku 4.5) y, con Haiku 4.5, un alias distinto entre repeticiones. Sin pasar al rol `enforcement`. `tool_search_loads == 0` en todas las ejecuciones.
  - [x] `app1/06_mcp_config` (2026-10-26): 9 viñetas con `INTRODUCE` y ☑, 113/240; `pytest` 383 en verde. Cabecera y README son borrador de Sonnet (**pasada con Opus pendiente**).
    - `conexion`: tres servidores (dos stdio por `.mcp.json` y uno en proceso), 9 tools y `token_recibido: true`; `init` a veces trae la lista de tools parcial (2 de ~8), el módulo lo avisa.
    - `recursos` (Haiku 5.5, 4 repeticiones): con resource, 2 llamadas a resources y 0 exploratorias (~0,0009 $); sin él, 19–31 exploratorias (×2,3–3,7). Hay que avisar al agente de que existen: sin la frase del prompt no los usa.
    - `descripcion`: **sin señal**; `Grep` 0/6 con la descripción completa y con la mínima (con aviso de archivos, 4/6 y 5/6). Se documenta sin fabricarla.
    - Comprobaciones heredadas cerradas: `setting_sources=["project"]`/`["project","local"]` dejan fuera el `CLAUDE.md` y las reglas de usuario; los plugins `@builtin` no añaden tools (hooks sin comprobar). Detalle en `docs/hallazgos.md`.
  - [ ] Siguiente: `app3/03`, sección D3, pasada con Opus de `app1/03`–`06`, revisión independiente.
- [ ] Entrega 3 · D4 y D5 (`S-2`)
- [ ] `S-1` · repaso sin código nuevo
- [ ] Entrega 4 · opcional, después del examen

## Notas de construcción

- **Cobertura 240/240:** `test_full_coverage` está en `xfail(strict=True)`; cuando pase, pytest lo marcará como XPASS fallido y hay que quitar la marca.
- **Viñetas de D3 pendientes para `d3_claude_code/README.md`** (entrega 2): 3.1-S1, 3.1-S4, 3.2-K4, 3.2-S5 y las 9 de 3.5. Las otras 27 ya tienen su marcador en `CLAUDE.md`, `docs/` y `.claude/`.

Los hallazgos de producto y de implementación están en [docs/hallazgos.md](docs/hallazgos.md). Tu estado de estudio (fallos, sesiones, práctica) vive fuera de git, en `estado/<perfil>/`.

## Citas en prosa por convertir a `# USA`

El arnés cita estas viñetas en prosa porque aún no están introducidas (roadmap §2). Se convierten en el mismo cambio que las introduce:

Todas convertidas en la entrega 1 (2026-10-24): `TS 1.4-K1` en `harness/options.py` y `harness/recorder.py`; `TS 1.2-K1` y `TS 1.3-S3` en `harness/recorder.py`.
