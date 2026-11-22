# Hallazgos

Notas de producto y hallazgos de esta implementación. Qué va aquí, qué va al estado personal y las marcas para el roadmap (`→ roadmap`, `✓ roadmap <fecha> §x`): `docs/estandares-flujo.md`, «Registro entre sesiones».

## Índice

- «Abiertos»: pendientes vivos, con la entrada donde se explican.
- Notas de las entregas 1 y 2, del Hito T y generales: «Aislamiento y configuración de la sesión», «SDK y arnés», «Hooks de la sesión de construcción», «Medidas por módulo de las entregas 1 y 2», «Práctica D3 y skills», «Hito T y práctica guiada» y «TS 5.6 · una lección externa».
- Entrega 3: «tanda A», «tanda B, después de las correcciones B4», «Auditoría 2026-11-06 · G-01», «Comparaciones entre modelos y calibración», «tanda C, sonda C1», «tanda C4» y «tanda D».
- Mejoras didácticas: «Práctica guiada · preguntas de «Predice antes de ejecutar» confusas», «Precedencia y superposición de nombres», «Fase 3 · paquetes sin interacción» y «Fases 4 y 5 · documentos y código».
- Medidas superadas por otras posteriores, con sus cifras (tanda B antes de B4, tanda C antes de C4, `app2/04` primera a tercera medida), y las tablas de filas ya aplicadas en `docs/tipos-de-senal.md`: en `docs/historico/hallazgos-medidas-superadas.md`.

## Abiertos

Pendientes que siguen vivos. Cada uno se explica en su entrada; aquí solo se reúnen.

- **Hooks de los plugins `@builtin`:** si aportan hooks, sin comprobar (entradas «Plugins en la línea `[contexto]`…» y «Los plugins `@builtin` no añaden tools», en «Aislamiento y configuración de la sesión»).
- **Varios `AssistantMessage` por respuesta:** por qué son 3, sin mirar (entrada «Una respuesta del modelo puede llegar en varios `AssistantMessage`», en «SDK y arnés»).
- **Sugerencias de entrada:** qué pasa si la configuración de usuario las activa (entrada «Sugerencias de entrada desactivadas», en «Aislamiento y configuración de la sesión»).
- ***Tool search*:** una configuración que lo active, para demostrar el efecto; único `→ roadmap` vivo (entrada «Variable de *tool search* en la CLI 2.1.309», en «SDK y arnés»).
- **`disableBundledSkills`:** sin probar (entrada «Patrones para excluir `CLAUDE.md` y reglas, y para apagar skills»).
- **Hooks de usuario:** sin estudiar (entrada «`claudeMdExcludes` aísla también la memoria de usuario…»).
- **Recarga en caliente:** por qué recibió `anthropic-skills:pdf` (entrada «Las skills sincronizadas comunes se apagan desde `.claude/settings.json`»).
- **`app3/04`, vacío falso producido por el código:** pendiente de comprobar en otra máquina si se generaliza (`docs/historico/hallazgos-medidas-superadas.md`, «Entrega 3 · tanda B, antes de las correcciones B4»).
- **`app3/11 --anti conservador`:** hipótesis sin comprobar sobre el criterio de comentarios («tanda C4», «`app3/11 --parte revision`»).
- **`app3/11 --parte rerevision`:** sin rehacer tras C4 (misma sección).
- **`app3/11 --parte tests`:** posible ampliación de la clave de `expected`, no hecha («tanda C4», «`app3/11 --parte tests`»).
- **`app2/04`:** si la comprobación laxa explicó la señal de los ejemplos de la segunda medida; inferencia sin comprobar, para la próxima revisión (`docs/historico/hallazgos-medidas-superadas.md`, «`app2/04_few_shot_y_escalamiento`, tercera medida»).
- **`app3/02`:** las dudas sobre la API y el SDK del paralelo siguen sin comprobar (entrada «`app3/02`, el paralelo no lo garantiza el código», en «Práctica guiada…»).
- **Prueba P6:** si ante una contradicción se sigue el `CLAUDE.md` más cercano, sin respaldo en la documentación y sin probar («Precedencia y superposición de nombres»).

## Aislamiento y configuración de la sesión

- **Plugins sincronizados desde claude.ai** (`<nombre>@synced`): ✓ roadmap 2026-10-24 §4.3.
- **Conectores de claude.ai** (`ENABLE_CLAUDEAI_MCP_SERVERS=false` también en la sesión de construcción): ✓ roadmap 2026-10-24 §3, regla 3.
- **Skills sincronizadas de claude.ai** (`docx`, `pdf`, `deep-research`…): no afectan a las apps (`setting_sources=[]`); en la sesión de construcción se apagan por nombre con `skillOverrides` (ver las entradas del 2026-10-27 y del 2026-10-29 más abajo). Origen de las 18 skills de `[contexto]`: ✓ roadmap 2026-10-24 §4.3 (vienen de la CLI; con `CLAUDE_CONFIG_DIR` vacío salen las mismas).
- **`claudeMdExcludes` en Windows:** ✓ roadmap 2026-10-24 §4.3.
- **`skills=None` no apaga las skills** (`skills=[]` por defecto y `setting_sources=None` rechazado): ✓ roadmap 2026-10-24 §3, regla 3, y §5; comprobado que el modelo no ve las skills con `skills=[]`: ✓ roadmap 2026-10-24 §3, regla 3. Lo propio de esta implementación: la primera ejecución con modelo listó 18 skills en `[contexto]`, y la sonda (Haiku 5.5, ~0,004 $) recibió `Skill simplify is not in this session's skills allowlist`.
- **Plugins en la línea `[contexto]` con `setting_sources=[]`** (2026-10-24): ✓ roadmap 2026-10-24 §4.3 (origen `@builtin`, no de la cuenta). Que no añaden tools (comprobado en `app1/06`, 2026-10-26): ✓ roadmap 2026-11-03 §4.3. Si aportan hooks sigue sin comprobar.
- **Varios directorios de configuración (`CLAUDE_CONFIG_DIR`)** y decisión de credencial (`apiKeyHelper` solo en la CLI, clave en `.env`): ✓ roadmap 2026-10-24 §4.3. Lo propio de esta implementación:
  - **Credencial:** las apps usan la clave empresarial cargada desde `.env`. Si la clave está exportada, el módulo la usa y el coste va a esa cuenta.
  - `app2/06` reanuda sesiones del directorio de configuración del proceso que lo ejecuta.
  - **`.env` y el hook:** `proteger_rutas.py` impide crear o editar `.env` desde la sesión de construcción; lo crea la persona copiando `.env.example`. `.gitignore` cubre solo `.env` (patrón exacto), no variantes.
  - **`CLAUDE_CONFIG_DIR` para las apps:** en `app2/06` (2026-10-24), `resume` y `fork_session` funcionaron con el directorio de configuración del proceso que ejecuta el módulo, sin fijarlo. Con la clave en `.env` no hace falta login de respaldo. No se amplía `credentials.py`. Se queda aquí: depende del directorio de configuración de cada persona.
- **`/memory` no lista las reglas por ruta:** ✓ roadmap 2026-10-24 §11.5.
- **La configuración de usuario no se apaga desde el repositorio:** ✓ roadmap 2026-10-24 §3 (regla 3) y §4.3. Que `setting_sources=["project"]` y `["project","local"]` dejan fuera el `CLAUDE.md` y las reglas de usuario: ✓ roadmap 2026-11-03 §3, regla 3 (sonda hermética en `app1/06`, 2026-10-26).
- **Sugerencias de entrada desactivadas** (2026-10-25): la caja de entrada de Claude Code propone texto gris con la siguiente respuesta y puede revelar la letra correcta de un ejercicio. Se fija `promptSuggestionEnabled: false` en `.claude/settings.json`. Comprobado (2026-10-25, sesiones de la CLI, observado por la persona en su caja de entrada):
  - Una sesión nueva abierta con la setting de proyecto no muestra sugerencias.
  - **La clave no se aplica en caliente:** la sesión que ya estaba abierta siguió mostrándolas tras fijar `false` en `.claude/settings.json`; la sesión que ya no las mostraba siguió sin ellas tras crear `.claude/settings.local.json` con `true`; una sesión nueva sí aplicó el `true` local. El archivo local de la prueba se borró después.
  - Consecuencia: no hay forma dinámica dentro de una sesión; el valor se fija al arrancarla. Un comando que escribiera el archivo local solo valdría para la siguiente sesión.
  - Pendiente de comprobar: qué pasa si la configuración de usuario la activa (la de proyecto debería ganar, pero `settings.local.json` o la variable `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` pueden anularla).
- **`setting_sources` frente a la configuración de usuario** (sonda hermética, 2026-10-26): ✓ roadmap 2026-11-03 §3, regla 3. Lo propio de esta implementación, la matriz completa: `[]` no ve nada; `["project"]`, solo lo del proyecto; `["user"]`, solo lo de usuario; `["project","local"]` añade `CLAUDE.local.md`; `["user","project","local"]` lo ve todo.
- **Los plugins `@builtin` no añaden tools** (2026-10-26): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: con `setting_sources=["project"]`, `init` lista `cc-plugin-agents-md`, `cc-plugin-telemetry` y `cc-plugin-plugin-authoring`, y `tools` trae exactamente las configuradas (9 con tres servidores, 6 con resources). Hooks sin comprobar.
- **`/skills` mezcla comandos de proyecto, skills de proyecto, skills sincronizadas y skills de un plugin sincronizado** (práctica D3, 2026-10-27, Claude Code 2.1.311): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: 17 entradas, `verificar-concepto` y `nuevo-modulo` como `project`, 13 `claude.ai sync` y 2 `locked by plugin`.
- **Patrones para excluir `CLAUDE.md` y reglas, y para apagar skills** (2026-10-27, CLI 2.1.311 para el esquema y 2.1.309 para las pruebas): ✓ roadmap 2026-11-03 §4.3 (confirmado con la cuenta real en la entrada del aislamiento local). Lo propio de esta implementación: probado con un árbol temporal de dos padres, el proyecto y una subcarpeta; las skills que trae Claude Code se apagarían con `disableBundledSkills`, sin probar.
- **`claudeMdExcludes` aísla también la memoria de usuario, no las skills ni los plugins de usuario** (2026-10-27, CLI 2.1.309): ✓ roadmap 2026-11-03 §3, regla 3, y §4.3. Lo propio de esta implementación: con el patrón en `.claude/settings.local.json`, la sesión sigue cargando su `CLAUDE.md` y los dos `@import`. Los hooks de usuario no se han estudiado.
- **El aislamiento local funciona sobre una cuenta real** (sesión interactiva, 2026-10-27, Claude Code 2.1.311): ✓ roadmap 2026-11-03 §3, regla 3. Lo propio de esta implementación: `/context` pasó a listar solo el `CLAUDE.md` del proyecto y sus dos `@import` (3,8k tokens) y, como skills, las 2 del proyecto más 16 Built-in (~2,5k tokens).
- **Plugins `builtin` en una sesión interactiva** (`/plugin`, 2026-10-27, Claude Code 2.1.311): ✓ roadmap 2026-11-03 §4.3 (el plugin de más). Lo propio de esta implementación: `nuevo-modulo` sale como `Skill · project · never used`, es decir, el producto cuenta el uso de skills y trata el comando como una de ellas; ningún plugin sincronizado aparece activado con el aislamiento local.
- **`enabledPlugins` apaga el plugin sincronizado y lo deja visible como apagado** (`/plugin`, 2026-10-27, Claude Code 2.1.311): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: `cowork-plugin-management@synced`, cuyas dos skills desaparecen de `/context`.
- **Las skills sincronizadas comunes se apagan desde `.claude/settings.json`** (2026-10-29, decisión del proyecto): ✓ roadmap 2026-11-03 §3, regla 3, y §4.3 (nombre inexistente ignorado). Lo propio de esta implementación: comprobado con Claude Code 2.1.312. El local no las vuelve a encender al arrancar (`"pdf": "on"` en local y `"off"` en proyecto no listó `pdf`), pero una recarga en caliente sí recibió `anthropic-skills:pdf`; no se ha investigado por qué.

## SDK y arnés

- **Subagentes fork activos por defecto** (`CLAUDE_CODE_FORK_SUBAGENT="0"` en los módulos con subagentes): ✓ roadmap 2026-10-24 §3, regla 4.
- **Subagentes en segundo plano aunque `background=False`** (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`): ✓ roadmap 2026-10-24 §3, regla 4. Lo propio de esta implementación: sin la variable, `query()` emitía varios `ResultMessage`; con ella, un solo `[fin]` y resultado «Subagent hand-back».
- **`tools=[]` quita también la tool `Agent`:** ✓ roadmap 2026-10-24 §4.3.
- **`disallowed_tools` con una tool MCP no la quita:** ✓ roadmap 2026-10-24 §4.3 y §7 (`app2/03`).
- **La denegación de un subagente no aparece en `permission_denials`** del padre: ✓ roadmap 2026-10-24 §4.3.
- **Un modelo reciente puede no mostrar la tasa de fallo del prompt** (`app2/01`): ✓ roadmap 2026-10-24 §4.3, §7 y §13. Lo propio de esta implementación: rol `enforcement` y presupuesto `CCARF_BUDGET_ENFORCEMENT` en `harness/config.py`.
- **El corte de `max_budget_usd` lanza `ResultError`:** ✓ roadmap 2026-10-24 §4.3 y §5 (`recorder.py`).
- **Tope por ejecución del script**, repartido entre repeticiones, configuraciones, turnos o ramas: ✓ roadmap 2026-10-24 §3, regla 7.
- **Una respuesta del modelo puede llegar en varios `AssistantMessage`** con el mismo `message_id`: ✓ roadmap 2026-10-24 §5 (`recorder.py`). Lo propio de esta implementación: `RunRecord.messages_per_response` y `partidas=` en `[fin]`. En `app3/02 --parte paralelo`, `r1` llegó en 3 mensajes con las 3 llamadas `Agent`, y en modo secuencial también en 3 con una sola llamada. Pendiente: por qué son 3 (¿razonamiento o texto en mensajes aparte?); no se ha mirado.
- **La CLI hereda `os.environ` completo** y encima aplica `options.env`: ✓ roadmap 2026-10-24 §5 (`credentials.py`).
- **Ruta corta de Windows (8.3) en el `cwd` y `Edit`/`Write` denegados** (`app1/02`, 2026-10-26): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: arreglado en `copy_to_temp`, con 3 de 3 `Edit` aplicados tras resolver la ruta.
- **Una tool que no está en `tools` se puede intentar y falla con error** (`app1/02 --anti sin_grep`): el modelo llamó a `Grep` aunque `init` solo listaba `Glob` y `Read`; el resultado fue `No such tool available: Grep. Grep is disabled for this session`. El recorder lo cuenta como llamada con `is_error` y `executed=True`, porque llegó un `tool_result`: «ejecutada» significa «hubo resultado», no «la tool existía». No es una fuga: quitar una tool en `tools` la elimina de verdad.
- **Los servidores de `.mcp.json` no piden aprobación con `setting_sources=["project"]`** (sonda de `app1/06`, 2026-10-26, Haiku 5.5, ~0,0005 $): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: los dos servidores stdio salen `connected` con `source: project`, con tools `mcp__<servidor>__*`, y el servidor informó `token_recibido: true`.
- **Un script sin `credentials.describe()` no carga `.env`:** una sonda que llamó a `query()` sin pasar por `credentials` terminó con «Not logged in · Please run /login» y coste 0. Los módulos lo evitan porque `describe()` carga la clave. Se queda aquí: es una nota de uso del arnés.
- **Variable de *tool search* en la CLI 2.1.309:** el nombre es `ENABLE_TOOL_SEARCH` (sin prefijo `CLAUDE_CODE_`), con valores `true`, `force`, `auto:N` (un número) y, por el mensaje de error de la CLI, un valor inválido se rechaza; se leyó de las cadenas del binario empaquetado. Con el servidor de 18 tools en proceso, **ningún valor produjo carga diferida**: `tool_search_loads` fue 0 con Haiku 5.5 y con Sonnet 5.5 sin variable, con `false`, `true`, `force` y `auto:0`, y la tool se llamó directamente. No hay control positivo, así que no se puede afirmar que `false` apague algo; solo que con estas tools y este arnés no se activa. `app1/05` lo fija en `env` como precaución, comentado, y el recorder confirma `tool_search_loads == 0`. Pendiente: encontrar una configuración (más tools, servidor stdio, `ListTools` largo) donde sí se active, para poder demostrar el efecto. → roadmap (§3, regla 4) solo cuando se confirme el efecto.
- **`init` puede traer las tools de un servidor stdio sin cargar** (`app1/06`, 2 de ~8 ejecuciones con tres servidores): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: el módulo avisa con `[aviso]`.
- **Salida redirigida en Windows y `UnicodeEncodeError`** (recorrido del narrador, 2026-11-03): ✓ roadmap 2026-11-03 §4.3 y §5. Lo propio de esta implementación: visto al ejecutar `app1/05` con `!` desde Claude Code; `harness/__init__.py` reconfigura los dos flujos y lo prueba `tests/test_consola.py`.

## Hooks de la sesión de construcción

- **Hooks de la sesión de construcción:**
  - Instantánea de hooks al arrancar, fallo en cerrado, dos barreras (`deny` y hook), falso positivo con `git commit -F` y UTF-8 en Windows: ✓ roadmap 2026-10-24 §4.3.
  - El filtro de shell de `proteger_rutas.py` es heurístico:
    - bloquea cualquier comando que nombre `datos/sinteticos` o un `.env`, salvo `git status|diff|log|show|add` sin nada encadenado (el salto de línea cuenta como separador);
    - no ve un script que escriba por dentro, ni variables o comodines que compongan la ruta. Esa vía la cubre `generar_sinteticos.py --check`.
  - **Variantes de `.env`:** protege `.env` y `.env.*`, salvo las plantillas `.env.example` y `.env.sample`, sin distinguir mayúsculas.
  - La regla `deny` se vio rechazar el `Edit` («directory that is denied by your permission settings») y el hook bloquear por shell (2026-10-24).
  - **Una instrucción en contexto puede tapar la prueba:** ✓ roadmap 2026-10-24 §11.5. Caso visto: al pedir «edita `datos/sinteticos/tickets.json`», la sesión fue directa al generador sin intentar el `Edit`.
- **Los hooks se lanzan con `uv run`, no con `python`:** ✓ roadmap 2026-10-24 §4.3.

## Medidas por módulo de las entregas 1 y 2

- **El modelo amplía el ancla de `Edit` por sí solo y el fallo no se observa** (`app1/02 --parte edicion`, 2026-10-26): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: sin petición especial, 0 de 3 fallos con Haiku 5.5 y 0 de 8 con Haiku 4.5; con el prompt de un único `Edit` exacto, «Found 2 matches» en 3 de 6, siempre recuperado con otro `Edit` y archivo correcto en 6 de 6.
- **Una buena descripción evita el error de validación** (`app1/04`, Haiku 5.5, 15 ejecuciones): con `get_user_profile` descrita con el formato `EMP-1001`, el modelo corrige el ID «1001» antes de llamar y el error de validación nunca llega a producirse (0 de 15). No es un fallo del módulo, sino TS 2.1-K2 en acción; la forma del error de validación solo se ejercita en los tests sin modelo. Si hiciera falta observarlo en ejecución, habría que quitar el formato de la descripción, lo que contradice la regla de descripciones. Se queda aquí.
- **`app1/04` con Haiku 4.5** (sonda, 2026-10-26, 10 ejecuciones, ~0,12 $): no aclara los matices por bajar de modelo. La validación sigue sin verse (0 de 10: también corrige el ID por la descripción) y `generico` no produce reintentos inútiles (0 de 5): el modelo es más cauto y no reintenta nada. Lo que sí cambia: ante el timeout, Haiku 4.5 se rinde con frecuencia: lo recupera en 2 de 5 con metadatos estructurados y en 0 de 5 con el error genérico (Haiku 5.5: 5 de 5 en ambos casos). Muestra pequeña, pero la información estructurada ayuda más a un modelo menos hábil. El rol `agent` (Haiku 5.5) sigue dando mejor señal para `generico`.
- **`tool_choice` `any` y forzado según el modelo** (sonda de `app1/05`, 2026-10-26, Messages API, `max_tokens=300`): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: el 400 de Sonnet 5.5 es «tool_choice: type "tool" and "any" are not supported for this model» y confirma la tabla de `conceptos-generales.md` §4.6 del repositorio de estudio.
- **18 frente a 5 tools no bajó el acierto, pero sí el coste y la consistencia** (`app1/05 --parte scoping`, 2026-10-26): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: Haiku 5.5, 30/30 con 5 y con 18 tools y +36 % de coste por petición; Haiku 4.5, 18/18 en ambas, +58 % y una petición con dos alias distintos entre repeticiones.
- **Con `tool_choice: auto` el modelo llama a la tool salvo que la petición sea de opinión** (`app1/05 --parte tool_choice`, Haiku 5.5): con «¿qué te parece este ticket?» llamó a `extract_ticket_metadata` en 6 de 6 y con «¿es urgente?» en 4 de 5; con una petición de opinión («¿crees que este tipo de tickets suelen ser un problema grave?») contestó con texto en 5 de 5 y en 6 de 6 en el módulo. Con `any` y con forzado empezó por `tool_use` en 6 de 6. Lo propio de esta implementación: la petición del módulo es de opinión a propósito, para que el contraste de TS 2.3-S5 se vea.
- **Los resources hay que anunciarlos al agente** (`app1/06 --parte recursos`, 2026-10-26, Haiku 5.5): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: sin la frase del prompt, 19–31 llamadas exploratorias; con ella, 2 (`ListMcpResourcesTool` y `ReadMcpResourceTool` sobre `kb://catalogo`) y un coste entre 2,3 y 3,7 veces menor. Con `tools=[]` las tools de resources no están.
- **La descripción mínima no hizo preferir `Grep`** (`app1/06 --parte descripcion`, 2026-10-26): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: Haiku 5.5, `Grep` 0/6 sin aviso de archivos con ambas descripciones y 4/6 y 5/6 con aviso; Haiku 4.5, entre 0/6 y 2/6.
- **`app3/03`: la herramienta genérica sí mete basura; las demás señales de diseño no se cumplieron** (2026-10-26, coordinador Sonnet 5.5, subagentes Haiku 5.5, 3 ejecuciones por variante, ~0,04–0,05 $ cada una): ✓ roadmap 2026-11-03 §8. Lo propio de esta implementación: `fetch_url` abrió las 4 páginas basura en 2 de 3; `--anti todas`, 0 de 3 fuera de rol (también con Haiku 4.5, ~0,076 $); `--anti sin_verify`, 1 delegación en 5 de 6 frente a 2, a ~0,03 $ frente a ~0,05 $.
- **Revisión independiente de la entrega 2 (2026-10-26)** y lo que se comprobó al corregir. (1) *Barrera del coordinador:* con `tools=["Agent"]` el agente principal sigue viendo las tools del servidor MCP; sin barrera, el coordinador de `app3/03`, pedido expresamente, llamó a `verify_fact` y obtuvo el resultado, y con un hook `PreToolUse` que deniega cuando la entrada no trae `agent_id` recibió el rechazo, mientras los subagentes siguieron llamando a sus tools (`researcher` 8–11, `synthesizer` 5). Con la barrera el coordinador no intentó ninguna en 5 ejecuciones. El mismo patrón (coordinador con acceso a las tools MCP y solo el prompt como barrera) existía en `app3/01` y `app3/02`, de la entrega 1; corregido el 2026-10-27 con el mismo hook, compartido en `app3_sistema_multiagente/coordinator_gate.py` (ver la entrada siguiente). ✓ roadmap 2026-11-03 §4.3 y §8. (2) *`AgentDefinition(tools=[])`:* significa ninguna tool (el sintetizador respondió «SIN TOOLS», 2 de 2). (3) *Señales que dependen del modelo (`app1/03`):* con Haiku 5.5, `palabra_clave` 12/18 y `minimas` inestable (15/18 en una medida, luego 30/30, 30/30 y 29/30 tras hacer que cada tool atienda un solo tipo de ID); con Haiku 4.5, `palabra_clave` 24/24 (no obedece la regla del prompt), `minimas` 14/24 y 14/18, `correcta` 24/24. Se añade `--rol-modelo` para elegir el rol. Que cada señal se ve con un modelo distinto: ✓ roadmap 2026-11-03 §4.3 y §6. (4) *Servidor `mesa`:* `search_tickets` partía `EMP-1002` en «emp» y «1002» y devolvía tickets cuyo texto contenía «emp» (`EMP-9999`, sin tickets, devolvía uno ajeno); `reassign_license` lanzaba `ValueError` con `seats` no numérico; y un ID de ticket inválido gastaba el fallo transitorio. Corregidos, con tests. (5) *Detector de texto de `app1/04`:* «sin problemas» o «no hay ningún problema» activaban «no hay histórico»; se corrigió y la señal robusta sale ahora del registro.
- **Barrera del coordinador en `app3/01` y `app3/02`** (2026-10-27, Sonnet 5.5 de coordinador y Haiku 5.5 de subagentes): sonda desechable con un prompt que pide al coordinador buscar él con `search_tickets`. Sin hook, en los dos módulos lo hizo y obtuvo los 7 tickets; con el hook recibió el rechazo, delegó en `tickets_analyst` y el subagente buscó con normalidad (~0,08 $ las cuatro). Al repetir la medida con la barrera (`01` correcta, `estrecha` y `--pregunta simple`; `02 --parte paralelo`, una ejecución cada una), 0 intentos del coordinador y las señales documentadas se mantienen: `simple` solo `kb_analyst`; `paralelo` 3 `Agent` en `r1` (×1,37). En `estrecha` las consultas fueron solo de VPN, pero el detector de subtemas dio `wifi: True` porque la respuesta decía que no había buscado wifi: el detector de palabras de `01` es aproximado (falso positivo), y la señal fiable está en las consultas delegadas.
- **Un nombre de tool engañoso no confunde a estos modelos** (`app1/03 --anti nombre_enganoso`, práctica D3, 2026-10-27): ✓ roadmap 2026-11-03 §4.3 y §6. Lo propio de esta implementación: `get_ticket_status` dio 30/30 (Haiku 5.5) y 24/24 (Haiku 4.5); en una sonda con Haiku 4.5, `delete_ticket` y los nombres cruzados, 24/24 cada uno (102 de 102). La variante se conserva documentada.
- **Imponer un valor con un hook: la diferencia entre `updatedInput` y deny no se ve en una tasa** (`app2/07`, 2026-10-28, Haiku 5.5 y Haiku 4.5, ~0,05 $ en total): ✓ roadmap 2026-11-03 §4.3 y §7 (módulo opcional y ejercicio determinista). Lo propio de esta implementación: Haiku 5.5 no escribió un ID erróneo en 6 de 6; con Haiku 4.5, la regla «más de un verificado → deny» bloqueó el pago propio en 2 de 5 en las dos variantes, un artefacto del escenario. El `UnicodeEncodeError` con un emoji en la consola de Windows ya no necesita `PYTHONUTF8=1`: lo resuelve el arnés (entrada del 2026-11-03).

## Práctica D3 y skills

- **`argument-hint` no obliga a pasar el argumento** (Claude Code 2.1.310). La guía lo presenta como el mecanismo para pedir el parámetro; en el producto, el hint solo se muestra en el autocompletado y la skill se lanza igual sin argumento. Por eso `verificar-concepto` comprueba `$ARGUMENTS` y se detiene si llega vacío. En el examen vale la lectura de la guía (registrado en `conceptos-generales.md` §4.6 del repositorio de estudio). Comprobado el 2026-10-24: el fork funciona y a la conversación principal solo llegó el resultado.
- **La skill con `context: fork` corre en segundo plano en la sesión interactiva y su validación de argumentos la hace el modelo, no el código** (práctica D3, 2026-10-27, Claude Code 2.1.311): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: el informe llegó a los 32 s y el asistente principal lo reformuló; señaló además que las 13 viñetas de `d3_claude_code/README.md` no llevaban `POR QUÉ IMPORTA` ni `ANTI-PATRÓN` (corregido, `NOTAS.md`).
- **El informe de `/verificar-concepto` varía entre ejecuciones en lo que el modelo juzga** (práctica D3, 2026-10-27): ✓ roadmap 2026-11-03 §4.3. Lo propio de esta implementación: con TS 3.5-K1, la pregunta tipo examen salió como presente en una ejecución y como «no aplica a este destino» en otra; `SKILL.md` solo la exige en el README de una app.
- **`allowed-tools` en una skill sin `context: fork` preautoriza, no restringe** (2026-11-01, Claude Code 2.1.316): ✓ roadmap 2026-11-01 §4.3. Lo propio de esta implementación: la sonda fue `claude -p` con `--setting-sources project`, una ejecución por caso, ~0,23 $; `d3_claude_code/README.md` mantiene la lectura de la guía.

## Hito T y práctica guiada

- **Los ejercicios deben abrir con contexto y preguntar por patrones, no por números** (`app1/01`, 2026-10-30): ✓ roadmap 2026-10-30 §13 y 2026-10-31 §10 (Hito T) y §13 (regla 5). Aplicado a todos los módulos entregados en el Hito T (`NOTAS.md`).
- **La plantilla de módulo necesitó piezas que la regla 5 no nombraba** (Hito T, 2026-11-01): «El ejercicio», el resultado de referencia plegado, el ejemplo de predicción por valor del ciclo, el modo ligero que contrasta con el resultado plegado y la fila T sin la sección D3. ✓ roadmap 2026-11-01 §13 (ciclo, modos y regla 5) y §10 (fila T). Lo propio de esta implementación: `plantillas/modulo/README.md` y `tests/test_readme_modulos.py`.
- **La orientación falla aunque el contenido funcione** (prueba de usabilidad del Hito T, 2026-11-01; una participante sin Python; autonomía 2/7): ✓ roadmap 2026-11-01 §13 (reglas 1 y 5) y §11.8. Lo propio de esta implementación: el guion y el informe están en `docs/historico/prompts-hito-t/paso8-*.md`; la corrección es «Empieza aquí» en el `README.md` raíz, la ficha por módulo y los pasos con nombre.
- **Asistente que narra el módulo** (misma prueba): ✓ roadmap 2026-11-01 §13 (criterios del asistente narrador), §4.1 y §11.8. Lo propio de esta implementación: `/practica-guiada`, `harness/narrador.py` y `tests/test_narrador.py`; encargo en `docs/historico/encargo-asistente-narrador.md`.
- **El estado personal vive fuera de git y las notas `→ roadmap` van aparte de `NOTAS.md`** (2026-11-01): ✓ roadmap 2026-11-01 §4.1, §4.2, §4.3, §5, §10, §12 y §13. Lo propio de esta implementación: `estado/<perfil>/` con plantillas en `plantillas/estado/`, y este documento como notas de producto.

## TS 5.6 · una lección externa

- **Una lección externa resuelve los conflictos entre fuentes con una regla que la guía no fija** (TS 5.6, 2026-11-09). Un ejercicio de práctica pide reglas para resolver discrepancias en un corpus con niveles de autoridad (organismos oficiales, guías secundarias, white papers de proveedores); entre sus opciones está preferir la fuente más reciente, preferir la autoritativa y escalar a un humano lo irresoluble. No se dispone de la clave ni de la lección, y esa regla no aparece en `fuentes/` ni en `docs/` del repositorio de estudio.
  - **Lo que dice la guía** (TS 5.6-K3, K4 y S3): ante estadísticas en conflicto de fuentes creíbles, anotar ambas con su atribución y no elegir una de forma arbitraria; pedir las fechas para que una diferencia temporal no se lea como contradicción; y dejar que el coordinador decida cómo reconciliar antes de la síntesis. No dice preferir la más reciente ni la autoritativa. La referencia v1.2 del curso de estudio trata «elegir la más creíble» como distractor, y su quiz, «citar solo el dato más reciente».
  - **Inferencia propia:** la opción de la lección es la clave más probable, porque el enunciado pide resolver y sus fuentes no son igual de creíbles, un caso que K3 no cubre de forma directa. Anotar y reconciliar serían fases distintas y no alternativas. Para una pregunta tipo examen, sin ese encuadre, vale la lectura de la guía.

## Entrega 3 · tanda A (sondas A2 y medidas de los módulos, 2026-11-03)

Las sondas se hicieron con la Messages API y `CostGuard`, con scripts desechables fuera del repositorio. Costaron ~0,35 $ en total. Las líneas «Medido en `app3/NN`» vienen de ejecutar el módulo; el resto, de la sonda. Los documentos son `documentos_compra.json`.

- **Message Batches con Haiku 5.5** (`app3/09`, ~0,0005 $): ✓ roadmap 2026-11-03 §4.3 y §8.
  - Disponible. Un lote de 3 peticiones pasó de `in_progress` a `ended` en ~2 min (`request_counts` con `processing=3` hasta el final), así que se puede esperar en una sesión; el módulo sigue sin esperar de forma obligatoria (`--enviar` y `--batch-id`).
  - Los resultados no salen en el orden de envío (llegaron `DC-01`, `DC-12`, `DC-03`): se emparejan por `custom_id`.
  - Una respuesta truncada llega como `succeeded` (✓ roadmap §4.3).
  - `usage` por resultado, igual que en la API síncrona; con el 50 % (`BATCH_DISCOUNT`) las 3 peticiones costaron 0,00048 $.
  - **Medido en `app3/09` (12 peticiones y dos reenvíos, ~0,005 $ en total):** el lote terminó en minutos y los resultados llegaron en otro orden (emparejar por posición da datos de otro documento en 9 de 12 en la medición inicial; con el recuento corregido, sin contar los resultados sin datos y sobre los 11 documentos con número en la etiqueta, 11 de 11); la Batches API no tiene un corte de coste a mitad de lote, así que el módulo estima una cota superior antes de enviar. **Un trozo de 10 líneas también se truncó con `max_tokens` 600** (3 de 4 correctos); partir el documento entero en trozos de 5 líneas lo resolvió (8 de 8 y las 40 líneas coinciden con la etiqueta). Reenviar un trozo suelto con el mismo tamaño no basta. En una segunda ejecución el reenvío de 4 trozos de 10 líneas salió completo (4 de 4): que un trozo se trunque o no varía entre ejecuciones, así que el re-troceo en cadena (hasta una línea por trozo) se comprueba con tests y no se pudo ver de nuevo en vivo.
- **Reintento con error concreto frente a genérico** (`app3/08`, Haiku 5.5 y Haiku 4.5, ~0,2 $): ✓ roadmap 2026-11-03 §4.3 y §8.
  - **Con Haiku 5.5 no hay nada que reintentar**: 0 de 36 primeros intentos con fecha mal formateada, aunque la descripción del campo solo diga «Fecha del documento».
  - Con **Haiku 4.5** sí: 17 de 36 salen con la fecha tal como aparece (`14/09/2026`, `22 Sep 2026`, `28-09-2026`). Reintento con el error concreto (campo, valor y regla): **12 de 12 corregidos**; reintento «Inténtalo de nuevo»: **2 de 12** (el modelo repite la misma fecha). `app3/08` usa por eso el rol `enforcement` (cambio de diseño, mismo precedente que `app2/01`).
  - Dato que no está en la fuente (`DC-02`): insistir lo hace inventar con los dos modelos (✓ roadmap §4.3). Haiku 5.5: `<UNKNOWN>`, `PO-<UNKNOWN>`, `PO-0000`; Haiku 4.5: `PO-0398`, `PO-2026`, `PO-398`.
  - **Medido en `app3/08` (Haiku 4.5, 3 repeticiones por variante, ~0,14–0,19 $ cada una):** con el error concreto, 5, 5 y 7 reintentos de fecha (útiles 5, 5 y 6), la factura sin pedido marcada sin reintentar y el documento que remite a un adjunto (`DC-07`) marcado aparte; con el genérico, 10–11 reintentos con 1–3 útiles; insistiendo, el pedido inventado y el número de documento inventado en las 3 repeticiones. **Pedirle al modelo que revise un total que no cuadra por culpa del documento** (`conflict_detected`) lo lleva a **cambiar el total declarado** para que cuadre: con `--anti insistir`, en los 2 documentos con total incoherente en las 3 repeticiones. Depende de esta implementación: el mensaje pedía «revisa cantidades, precios y total», y eso lo induce en parte (revisión independiente A5). Por eso no va al roadmap tal cual: la variante correcta de `08` ya no reintenta los totales que no cuadran, los marca `conflict_detected` directamente.
- **Señal de *nullable* y de `enum` cerrado** (sonda para `app3/07`, Haiku 5.5 y Haiku 4.5, 12 documentos, ~0,12 $): ✓ roadmap 2026-11-03 §4.3 y §8. Las ejecuciones del módulo con Haiku 5.5 dieron las mismas señales (cifras en el Paso 3 del README).
  - **Campos opcionales como obligatorios**: 21 de 21 campos ausentes se rellenan (con la cadena `'null'`, con `''`, o con un valor deducido); con el campo *nullable* y fuera de `required`, 1–2 de 21 (Haiku 5.5: el total de un presupuesto deducido de su única línea; Haiku 4.5, además, una fecha de validez como fecha del documento). Con las dos versiones del modelo.
  - Un `enum` cerrado casi no fuerza el tipo: el modelo devuelve `other` fuera de la lista (✓ roadmap §4.3). Con Haiku 5.5, solo el ilegible salió como `invoice`; con Haiku 4.5, como `<UNKNOWN>`.
  - El identificador de la petición se cuela en el dato (✓ roadmap §4.3).
  - **Medido en `app3/07`, parte `enriquecimiento` (4.3-S3; 12 documentos × 3, ~0,04 $ con Haiku 5.5 y ~0,24 $ con Haiku 4.5):** con el primer turno forzado a `extract_metadata`, la extracción va primero en todos los documentos. Con `auto` desde el inicio también: **0/12 consultas antes de extraer y 0 números ajenos al documento** con Haiku 5.5 y con Haiku 4.5, y el resultado final usa el pedido extraído en 7/12 y 9/12, igual que con el forzado. **Sin señal del anti-patrón**: el forzado garantiza el orden por construcción, pero no se ha podido provocar el fallo que evita. No se probó con ningún otro modelo.
  - Bucle manual con Haiku 5.5: hay que devolver los bloques `thinking` con su `signature` (✓ roadmap §4.3).
  - **Medido en `app3/07`, parte `few_shot` con los campos faltantes (3 repeticiones, ~0,03 $ con Haiku 5.5 y ~0,23 $ con Haiku 4.5):** campos con valor en la etiqueta que salen `null`: **0** con los dos modelos, con y sin ejemplos. Los ejemplos corrigen el formato de fecha (Haiku 4.5: 5–6 fechas incorrectas sin ejemplos, 0 con ellos), no los vacíos.

## Entrega 3 · tanda B, después de las correcciones B4 (2026-11-04)

> Las mediciones anteriores están en `docs/historico/hallazgos-medidas-superadas.md`, «Entrega 3 · tanda B, antes de las correcciones B4».

Mediciones nuevas con Sonnet 5.5 de coordinador y Haiku 5.5 de subagente, separadas de las anteriores (que se conservan). Coste total de la tarea: ~2,28 $ (04 ~0,26 $, 05 ~1,18 $ con 0,13 $ de una prueba que no valió, `medio` 0,78 $ y 06 ~0,07 $).

- **`app3/04`**
  - **El mensaje genérico no cambia lo que hace el coordinador (corrige la medición anterior de `generico`).** Con el reintento local igual que la correcta, el coordinador delegó una sola vez en 3 de 3; antes, con «no reintentes», volvió a delegar en 3 de 3. La re-delegación a ciegas venía de que nadie había reintentado, no del mensaje (5.3-K3 sin señal propia con este modelo). La brecha se anotó en 3 de 3 igualmente.
  - **Recuperación local de lo transitorio (5.3-S3):** la fuente transitoria falló una vez y se recuperó en el reintento en 3 de 3, sin que el coordinador la viera como fallo (informe `ok`, ninguna brecha anotada).
  - `silenciar`: fallo tragado en 3 de 3; la brecha salió anotada en 1 de 3 (antes 0 de 3), con una frase que dice «falta información» y «respondió vacía, no es un fallo». La correcta y `abortar` repiten lo anterior.
  - Medidas corregidas: `gap_noted` con negación, `silenced_sources` renombrada `unreported_failures` (lo que mide `silenciar` es `swallowed_sources`), vacíos legítimos separados de los tragados, `partial_delivered` sin fechas ni fuentes no pedidas y con el aborto detectado sin la marca exacta.
- **`app3/05`**
  - **Ubicación y fragmento (5.1-S5, 5.6-S1):** válidos en las 40 afirmaciones de la correcta; **no llegan al informe final** (0 de 6 fuentes en las 3 ejecuciones): el sintetizador los parafrasea.
  - **Decisión del coordinador (5.6-S3):** presente y acertada en el prompt del sintetizador en 9 de 9 pares de la correcta (8 de 9 en `sin_procedencia`).
  - **Formato por tipo (5.6-S5):** con `formato_uniforme`, tabla en 0 de 3; en la correcta, tabla en 3 de 3 y los tres pares con sus cifras dentro en 2 de 3.
  - **Estructurado frente a verboso (5.1-S6): al revés de lo esperado.** La salida estructurada pesó más (8.781–10.045 caracteres del investigador y 3.320–5.703 hasta el sintetizador) que la verbosa (6.597–9.134 y 2.594–3.059). No hay señal de volumen con estos tamaños.
  - **Control positivo `inventar_explicacion`:** con Haiku 5.5, par sin explicación atribuido 0 de 3 (no inventó). Con Haiku 4.5 (`--rol-subagente enforcement`, sin tocar `.env`; 3 + 3 ejecuciones, ~0,60 $), el informe final lo deja disputado en 6 de 6, pero el borrador del sintetizador **inventó la causa en 1 de 3** de las ejecuciones medidas, y en otra el coordinador dice que quitó una lista de hipótesis. **El coordinador que revisa al sintetizador borra del informe final el fallo que se quería observar**: el control solo se ve midiendo el borrador. Desde ahora el módulo mide las dos cosas. La medida acertó por una palabra equivocada («población»), así que sigue siendo laxa. Un primer intento cambió `CCARF_MODEL_SUBAGENT` en el entorno, que `.env` sobrescribe; la vía es el rol `enforcement` (✓ roadmap 2026-11-05 §4.3, con la medida en el punto donde ocurre el fallo).
  - `promedio` fusionó en 1 de 3 (igual que antes). `sin_procedencia` verbosa, sin señal en el informe final.
  - ***Lost in the middle***, con relleno distinto y porcentajes de distracción: el resumen citó el 41 % en 12 de 12, con y sin resumen o encabezados. Sin señal.
  - Medidas corregidas: negación en `conflicts_presented`, verbo frente a sustantivo y «mismo» en `explanation_found`, promedios redondeados con unidad en `merged_figures` y `sources_passed` exige la afirmación junto a la fuente.
- **`app3/06`**
  - `read_manifest` valida bytes, tipos, claves y versión, y el retomar comprueba el *scratchpad* (recuento y huella); `read_scratchpad` ignora una última línea cortada con aviso y falla con la línea si la corrupción está en medio; el estado va a `estado/<perfil>/app3-06/`. Todo con tests, sin modelo.
  - Una pasada de caída simulada y reanudación: sin consultas repetidas, 5 de 5 hechos, estado en `estado/default/app3-06/`.

## Auditoría 2026-11-06 · G-01, modo estricto en `app3/07`

Haiku 5.5 (rol `agent`), Messages API. Coste total: ~0,021 $ (sonda de aceptación 0,0008 $ y `--parte estricto --repeat 3` 0,020 $).

- **`strict: true` es un campo de la definición de la tool** (junto a `name`, `description` e `input_schema`), no de `tool_choice`, y exige `additionalProperties: false` en cada objeto del esquema.
- **Sondeado: la API acepta el esquema de `extract_metadata` tal cual.** Con `type: ["string", "null"]`, con `anyOf` en su lugar y con todo en `required`, las tres variantes devolvieron `tool_use` sin error; hizo falta solo cerrar los objetos. No hay que reescribir los campos *nullable* para usar `strict`.
- **`strict` arregla la forma y no el significado, y puede empeorar el tipo.** Con el `enum` cerrado (`invoice`, `delivery_note`): sin `strict`, forma válida 10/12, 2 fuera del `enum` y tipo correcto 11/12; con `strict`, forma válida 12/12, 0 fuera del `enum` y tipo correcto **9/12**. El modelo escribía `other` (correcto) en la garantía y el presupuesto; con `strict` no puede y los fuerza a una categoría que no es. Idéntico en las 3 repeticiones. Es la razón de que el `enum` abierto con `other` y `unclear` (TS 4.3-K4) siga haciendo falta con `strict`.
- Corrige una afirmación previa del repositorio: la guía **sí** nombra el modo estricto (TS 4.3-K1, K3 y la lista de tecnologías), así que no es «EN PRODUCCIÓN (no evaluable)».

## Comparaciones entre modelos y calibración (no evaluable) · auditoría G-04, 2026-11-06

La guía deja fuera de alcance las métricas de comparación entre modelos. Los README de módulo usan un modelo como banco de pruebas de un mecanismo (una fila por modelo y por variante, con «modelo de la medida»), pero no enfrentan dos modelos en una fila (`tests/test_sin_comparacion_de_modelos.py`). Aquí queda lo que se sacó de los README, tal como estaba. Es calibración de esta implementación, no materia del examen.

- **`app1/03`, tabla original con una columna por modelo** (Haiku 5.5 con `--rol-modelo agent` y Haiku 4.5 con `--rol-modelo enforcement`). La mayoría de estas cifras ya figuraban en la revisión independiente de la entrega 2 (punto 3) y en la entrada de `nombre_enganoso`; la fila `correcta` con Haiku 5.5 (18/18) solo estaba en el README.

  | Variante | Haiku 5.5 | Haiku 4.5 |
  | :--- | :--- | :--- |
  | correcta | 18/18 | 24/24 |
  | `minimas` | **inestable**: 15/18 en una medida y 89/90 en otras tres | 14/24 y 14/18 (58–78 %) |
  | `palabra_clave` | 12/18: las 2 peticiones con «documento», siempre | 24/24: **no obedece la regla** |
  | `nombre_enganoso` | 30/30 | 24/24 (y 48/48 en dos casos más duros) |

  Qué se conserva en el README: cada variante con el modelo en que su señal se ve (`minimas` con Haiku 4.5, `palabra_clave` y `nombre_enganoso` con Haiku 5.5, la correcta como control), y las notas que explican por qué la señal depende del modelo.
- **`app1/05`, coste de pasar a 18 tools** (`scoping`): +36 % con Haiku 5.5 y **+58 % con Haiku 4.5**. El README conserva la cifra de Haiku 5.5 y remite aquí. La ausencia de degradación de acierto (18/18 con los dos modelos) y la petición cuya tool cambió con Haiku 4.5 siguen en la nota del módulo.
- **Coste de ejecutar con el rol `enforcement`** (Haiku 4.5): `app1/03 --anti minimas` es unas 15 veces más caro que con Haiku 5.5, y `app3/07 --parte few_shot --rol-modelo enforcement --repeat 3` cuesta unos 0,23 $ frente a 0,03–0,04 $ de las otras partes. Esas cifras se dejan en los README como aviso de gasto antes de ejecutar (no como comparación).
- **`app3/07`, `enriquecimiento --anti auto_desde_inicio`:** la fila que nombraba los dos modelos pasó a dos filas, una por modelo (Haiku 5.5: 7/12 con el pedido extraído; Haiku 4.5: 9/12; consulta antes de extraer 0/12 y número ajeno 0 en los dos). No se movió ningún dato.

## Entrega 3 · tanda C, sonda C1 de `claude -p` (2026-11-06)

CLI instalada 2.1.319 y CLI incluida en el SDK fijado (`claude-agent-sdk` 0.2.173, CLI 2.1.309); cada resultado se comprobó en las dos y **no difiere**. Modelo: Sonnet 5.5 (rol `reviewer`) en las pruebas de contexto y Haiku 5.5 en las de forma y coste. Coste total ~0,4 $, **sin poder comprobarlo**: la sonda no registró el coste de cada ejecución (ver «Costes reconciliados», tanda C4). Los módulos usan la CLI del SDK. Construye la orden `harness/headless.py`, con sus tests sin modelo (`tests/test_headless.py`).

- **Forma de la salida** (`--output-format json`): un único objeto `type: result` con `result` (texto), `session_id`, `total_cost_usd`, `num_turns`, `subtype`, `is_error`, `terminal_reason`, `usage` y `modelUsage`. Con `--json-schema` añade `structured_output` (el objeto ya parseado) y `result` trae el mismo JSON como texto; hace falta un turno más (`num_turns` 3). Cada llamada arrastra ~23.000 tokens de contexto base, casi todo de caché.
- **Si el modelo no cumple el schema, la CLI no falla:** con un schema imposible (`minimum` 10 y `maximum` 5) el resultado fue `subtype: success`, `is_error: false`, **sin `structured_output`** y con texto libre en `result` explicando que no pudo (mismo comportamiento con las dos CLI). Un módulo que solo mire `subtype` da por buena una respuesta sin objeto, así que `parse_result` exige `structured_output` y valida de nuevo con `jsonschema`. ✓ roadmap 2026-11-07 §5
- **Aislamiento** (marcas distintas en la memoria de usuario, en un `CLAUDE.md` de un directorio padre y en el del `cwd`; `CLAUDE_CONFIG_DIR` temporal):

  | Flags | Marcas que llegan |
  | :--- | :--- |
  | ninguno | usuario, padre y `cwd` |
  | `--setting-sources project` | padre y `cwd` |
  | `--setting-sources ""` | ninguna |
  | `--bare` (con o sin `--add-dir <cwd>`) | ninguna |
  | `--setting-sources project` + `--settings '{"claudeMdExcludes":["!<cwd>/**"]}'` | **solo la del `cwd`** |

  **Hueco de la prueba:** las marcas de memoria de usuario (`~/.claude/CLAUDE.md` y `~/.claude/rules/`) solo se probaron con ese `CLAUDE_CONFIG_DIR` temporal. Con la configuración de usuario real de la cuenta se miraron skills, servidores MCP y comandos (entrada siguiente), no la memoria ni las reglas de usuario.

  `--setting-sources project` no basta: los `CLAUDE.md` de los directorios padre siguen entrando. `--bare` y `--setting-sources ""` aíslan, pero también quitan el del `cwd`, que en `11` es el contexto de CI (TS 3.6-K3); `--bare --add-dir` tampoco lo recupera. La combinación de la última fila lo conserva y deja fuera todo lo demás (es la negación que ya usa `.claude/settings.local.json`). ✓ roadmap 2026-11-07 §3 regla 3
- **Qué ve el proceso aislado** (línea `init` con `--output-format stream-json --verbose`, config de usuario real de la cuenta): sin flags, 18 skills, unos 50 comandos y 27 tools; con `--setting-sources project --strict-mcp-config --disable-slash-commands` y `claudeMdExcludes`, 0 servidores MCP, 0 skills, 0 comandos y sin la tool `Skill`. Los cuatro plugins `@builtin` y los agentes integrados siguen (como en el Agent SDK, `app1/06`). `--tools` fija el conjunto de tools: `Read,Grep,Glob` para revisar.
- **Tope de coste:** hay flag, `--max-budget-usd`. Al agotarse: `subtype: error_max_budget_usd`, `is_error: true`, `terminal_reason: budget_exhausted`, código de salida 1 y sin `result`. Se comprueba entre turnos: con 0,003 $ de tope la ejecución costó 0,0042 $. No es un corte exacto. `--max-turns` queda solo como red.
- **`--resume` desde `claude -p`:** conserva el `session_id` y el contexto (el generador, que había editado `f.py`, recordó por qué). Se probó siempre desde el mismo `cwd` y con la sesión de origen persistida; con `--no-session-persistence` no habría nada que reanudar (deducido, sin probar), por eso `build_command` solo lo omite cuando no hay `resume` ni `persist=True`.
  - **El `total_cost_usd` es acumulado**, como en el SDK (✓ roadmap §4.3): generador 0,001186 $, primer `resume` 0,001464 $ (propio 0,000278 $, recalculado desde `usage`), segundo `resume` 0,001528 $ (se suma al anterior, porque `resume` sin `--fork-session` modifica la sesión). Con la CLI del SDK, igual (0,001032 → 0,001272 → 0,001334).
  - **`--max-budget-usd` no cuenta ese histórico:** con 0,0013 $ de tope y 0,0018 $ ya acumulados, un `resume` de dos turnos terminó con `success` (0,0022 $ acumulados, 0,0005 $ propios). El tope de una rama con `--resume` lo tiene que llevar el arnés: coste de cada invocación = diferencia de acumulados, y el flag de la siguiente = tope de la rama − gastado (`headless.Ledger`). ✓ roadmap 2026-11-07 §4.3 y §5

## Entrega 3 · tanda C4, medición tras las correcciones de código (2026-11-07)

Sonnet 5.5 (rol `reviewer`) con `claude -p` aislado y CLI 2.1.309 del SDK; Haiku 4.5 (rol `enforcement`) para la parte con modelo de `app3/10`. Mismo commit y **misma puntuación en toda la batería** (el código no se tocó mientras corrían). Correcciones medidas: cada revisión corre sobre un árbol en el commit que revisa y sin `.git` (antes, el del segundo commit); la clave de un escenario de test incluye lo que espera; el símbolo se compara como nombre completo y la línea manda sobre él; `TIMEOUT` ya no está duplicado (`NOTIF_TIMEOUT`, un cambio de datos); `--sin-categoria comment` quita solo esa categoría; el prompt de **todas** las variantes cambia (la línea de `bug` ya no cita el docstring y cambió el ejemplo de `minor`); `confianza_global` usa un umbral por segmento; el diff generado de `12` incluye los archivos nuevos y su repositorio no guarda el cambio. Cada cifra «antes» está en `docs/historico/hallazgos-medidas-superadas.md` (secciones marcadas «antes de las correcciones C4»).

**Coste real de esta batería: 1,52 $** (tope de la tarea, 4 $): `11` revisión 0,369 $, `11` tests 0,258 $, `10` con modelo 0,129 $, `12` 0,761 $. Una primera tanda de `11` no llegó a ejecutarse (el proceso murió al lanzarla; 0 $).

### `app3/11 --parte revision` (5 ejecuciones por variante, fallos sembrados A, B, C, D y F)

| Variante | Fallos encontrados | Falsos positivos | Marcó lo correcto | Coste | Antes (C4) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| correcta | las 5 en **5/5** (25/25) | 0 | **5/5 ejecuciones** (3 veces el comentario de `REINTENTOS`, 2 el renombrado a `NOTIF_TIMEOUT`) | 0,096 $ | A a D en 7 de 8; marca 3 de 8 (8 ejecuciones) |
| `--anti conservador` | las 5 en **5/5** | 0 | **0/5** | 0,085 $ | A se pierde 2 de 8; sin diferencia |
| `--anti sin_ejemplos` | **24/25** (B falta en 1) | 0 | 4/5 (1 duplicado) | 0,098 $ | B falta 3 de 5; inestable |
| `--sin-categoria comment` | **24/25** (C falta en 1) | 0 | **1/5** | 0,090 $ | C 3 de 3 como `bug`; seguía marcando |

- **Qué cambió.** (a) «Marcó lo correcto» **sí separa variantes ahora**: 5/5 en la correcta, 4/5 en `sin_ejemplos`, 0/5 con `conservador` y 1/5 sin la categoría `comment`. Esas cifras incluyen un artefacto: 2 de las 5 marcas de la correcta, y la única de la variante `comment`, son el renombrado a `NOTIF_TIMEOUT` (ver el punto siguiente). Si cada ejecución marcó una sola cosa (3 + 2; es una lectura de los recuentos, no una medida directa), la marca que depende del criterio de comentarios, la del comentario de `REINTENTOS`, sale en **3/5 con la correcta frente a 0/5 sin la categoría `comment`**. Antes `--sin-categoria comment` «solo reclasificaba» el hallazgo; ahora lo quita en todas. (b) `conservador` ya no pierde A: encuentra todo y no marca el cambio correcto, al revés de lo que dice la guía sobre «sé conservador» (4.1-K2). Hipótesis **sin comprobar**: esa variante sustituye todos los criterios, también el de comentarios, que es el que invita a revisar la justificación de `REINTENTOS`; lo que desaparece sería el criterio, no la prudencia. Con n = 5 es una pista, no una prueba, y la respuesta de examen sigue siendo la de la guía. (c) La variante `comment` pierde C en 1 de 5: el modelo marcó el renombrado como `bug` y no el comentario.
- **Efecto no previsto del arreglo de `TIMEOUT`:** 4 de las 20 ejecuciones (2 de la correcta, 1 de `sin_ejemplos` y 1 de `comment`) señalan que renombrar a `NOTIF_TIMEOUT` rompería a quien lo importara. No es un fallo (no hay nadie que lo importe). Se puntúa como marca del cambio correcto porque cita la línea 6, la del señuelo; sube la cifra de «marcó lo correcto» (2 de las 5 marcas de la correcta y la única de `comment`) y no cambia los fallos encontrados.
- **`detected_pattern`:** sigue cambiando casi cada vez para la misma marca (`misleading_comment`, `dubious_comment`, `comment_does_not_match_code`…); no se normalizó.
- **Sin rehacer:** la segunda revisión (`--parte rerevision`) no está en este alcance y queda con las cifras de «antes»; su árbol (el estado final) ya era el correcto, pero la puntuación por símbolo es la nueva.

### `app3/11 --parte tests` (5 ejecuciones por variante, puntuando `expected`)

| Variante | Tests propuestos por ejecución | Escenarios repetidos | Sobre lo que cambió | Coste |
| :--- | :--- | :--- | :--- | :--- |
| correcta | 8, 8, 8, 7, 7 | **0** en 5/5 | 6, 7, 6, 6, 6 (31 de 38) | 0,095 $ |
| `--anti sin_tests_existentes` | 8, 8, 8, 9, 8 | **0** en 5/5 | 0, 6, 6, 7, 6 (25 de 41) | 0,077 $ |
| `--anti sin_estandares` | 12, 9, 10, 10, 10 | **0** en 5/5 | 8, 7, 7, 7, 7 (36 de 51) | 0,087 $ |

- **«Al revés de lo esperado» desapareció, y no por una señal a favor de la guía:** con los tests existentes en el contexto 0 repetidos y sin ellos 0 (antes 1 y 0). Puntuar lo que espera explica la parte «antes»: el cambio pasa las horas a minutos, así que quien actualiza un test roto ya no repite el escenario. Pero solo 2 de los 5 escenarios existentes (`calcular_sla(alta, 3)` y `horas_restantes`) son los que el cambio rompe (`datos/generar_sinteticos.py`, `REVIEW_EXISTING_SCENARIOS`); los otros 3 (`calcular_sla(alta, 9)` con `ValueError` y los dos de `debe_escalar`) no cambian, y repetirlos sería un duplicado real. **Limitación de la medida:** `_norm_expected` exige que coincidan todos los números del texto de `expected`, así que un duplicado real escrito con un número de más («lanza ValueError: 9 h de 8 h») deja de contarse; el 0 frente a 0 puede ser en parte un artefacto de la clave y **no demuestra que no hubiera duplicados reales**. Ningún test cubre ese caso, y las propuestas no se guardaron (el módulo solo imprime recuentos y repetidos), así que no se revisaron a mano. El 0 no es señal ni a favor ni en contra de 3.6-S4.
- **Posible ampliación (no hecha):** relajar la clave para comparar solo el número principal y la excepción de `expected`, guardar las propuestas y revisarlas a mano.
- **Señal nueva y en el sentido de la guía (3.6-S5):** sin los estándares en el `CLAUDE.md` el modelo propone **más tests** en 5 de 5 ejecuciones (9–12 frente a 7–8 de la correcta, sin solapamiento) y una proporción algo menor sobre lo que cambió (71 % frente a 82 %). Es una diferencia de cantidad, no de duplicados; los estándares piden un test por escenario y `parametrize`, que es coherente con menos tests. No se midió si los tests extra aportan menos.
- `sin_tests_existentes`, ejecución 1: 8 tests y 0 sobre lo que cambió (en las otras cuatro, 6 o 7). Sin explicar.

### `app3/10` (sin modelo, con el umbral por segmento) y parte con modelo

| Variante (`--parte poblacion`) | Automatizado | Errores entre lo automatizado | Del tipo raro | Antes (C4) |
| :--- | :--- | :--- | :--- | :--- |
| correcta | 765 valores | 6 (0,8 %) | 0 | igual |
| `--anti precision_agregada` | 805 | 17 (2,1 %) | 11 (34 valores raros aceptados) | igual |
| `--anti confianza_global` | **768** | **8 (1,0 %)** | **0** | 780, 14 (1,8 %), 8 raros |

- **Cambia una señal:** con un umbral por segmento, la confianza por documento **ya no deja pasar el tipo raro** (0 frente a 8) y solo añade 2 errores a los 6 de la correcta. Lo que dejaba pasar al tipo raro era el **umbral global único**, no la confianza por documento. La lección de `confianza_global` (la media por documento esconde el campo dudoso) queda con una diferencia pequeña (8 frente a 6 errores, 768 frente a 765 automatizados), en el límite de lo que muestra una sola población simulada.
- **Muestreo (sin cambios):** error del tipo raro visto en el 53,4 % de las muestras simples y el 100 % de las estratificadas (500 repeticiones, muestra de 60 de 871). Nuevo: la **tasa de error real** del conjunto de confianza alta es 2,0 %; la de la muestra simple, 1,8 %; la de la estratificada, **10,8 %** (sobre-representa el tipo raro, que tiene un mínimo por estrato), y **ponderada por el tamaño de cada estrato, 2,0 %**. Sin la ponderación, vigilar con una muestra estratificada sobreestima la tasa de error en 5 veces. La ponderada solo se define si todos los estratos tienen muestra, y la simple no lo garantiza (queda sin cifra).
- **Parte con modelo (Haiku 4.5, `--sin-reglas-de-formato`, 3 × 12 documentos, 0,129 $):** 6, 7 y 7 errores por repetición, con confianza ≥ 0,85 en 5, 7 y 5 (antes 6, 7 y 8 y 5, 7 y 7). Banda 0,97–1,00: acierta el **82,9 %** y declara el 100 % (antes 85,5 % frente a 99,5 %); hueco de calibración 0,076. La confianza de los campos en `null` (0,21–0,33) sigue siendo la de la ausencia. Se mantiene la señal.

### `app3/12 --parte revision` (5 ejecuciones por rama; fallos A, B, C, D y F)

En las dos ramas la sesión generadora **escribió exactamente el cambio dado** (93 líneas, 4 archivos; la nueva línea «no crees ningún otro archivo» del prompt generador no se probó sin ella, así que no se sabe si evitó que añadiera uno como en la medida anterior).

| Rama | Fallos encontrados | Por archivo / solo por integración | Falsos positivos | Marcó lo correcto | Coste |
| :--- | :--- | :--- | :--- | :--- | :--- |
| instancia nueva | las 5 en **5/5** (25/25) | A, B, C 5/5; D 3/5 y F 1/5 por archivo; solo por integración D 2/5, F 4/5 | 0 | 1 en 5 ejecuciones | **0,498 $** (generador 0,047 $ + ~0,090 $ por revisión) |
| `--anti una_pasada` | **24/25** (C falta en 1) | una única pasada | 0 | 6 en 5 ejecuciones | **0,263 $** (generador 0,050 $ + ~0,042 $ por revisión) |

- **El contraste que faltaba a 4.6-K3/S2 no aparece con este diff:** una única pasada larga sobre todo el diff encuentra D y F en 5/5 (la instancia nueva por pasadas, 5/5 también), y cuesta **2,1 veces menos** por revisión (0,042 $ frente a 0,090 $). A 93 líneas y cinco fallos no se ve la atención diluida que describe la guía; el reparto en pasadas cuesta el doble. Lo que sí se mantiene es la pauta de dónde salen D y F con la instancia nueva: la pasada por archivo ve D en 3 de 5 y F en 1 de 5, y la de integración completa D (2 de 5) y F (4 de 5); es la misma pauta que antes (D 1/5 y 4/5; F 0/5 y 5/5), con la misma explicación (la pasada de archivo no ve a los llamadores). Respuesta de examen: manda la guía (4.6-K3, S2), el reparto es lo que prescribe y esto **no lo respalda como mejora medida** en un diff tan pequeño.
- **`una_pasada` marca más el cambio correcto** (6 marcas frente a 1), y la verificación lo distingue: en la banda de confianza 0,00–0,50 hay 5 hallazgos y ninguno coincide con un fallo sembrado (la verificación decía 23 %); en las otras bandas acierta el 94–100 %. Hueco de calibración 0,129 (frente a 0,215 de la instancia nueva, que se queda corta: 0,00–0,50 y 100 % de aciertos). Aquí la confianza sí separa algo.
- **La instancia nueva con el diff exacto** (la medida anterior la había hecho sobre un diff de 125 líneas con un archivo de tests añadido por el generador): ya hay una rama sobre el mismo diff. D y F por integración, 2/5 y 4/5, es consistente con «antes» (4/5 y 5/5).

### Costes reconciliados

- **Sonda C1: ~0,4 $ (`hallazgos.md`) o ~0,3 $ (`NOTAS.md`).** No se puede sumar: la sonda no dejó un registro por ejecución, solo los costes de las pruebas de coste y de `--resume` (centésimas de céntimo cada una) y la matriz de aislamiento, cuyo coste no se anotó. Se deja **~0,4 $**, la cifra del registro detallado, y se anota que ~0,3 $ en `NOTAS.md` era una estimación anterior. Es la menos segura de las dos reconciliaciones.
- **`app3/11`: ~1,0 $ (README) o ~1,1 $ (`hallazgos.md`, `NOTAS.md`).** Sumando las ejecuciones registradas en `hallazgos.md` hay 49 revisiones (10 de la correcta, 8 de `conservador`, 10 de `sin_ejemplos`, 3 de `comment`, 6 de la segunda revisión y 12 de tests). A ~0,02 $ cada una (0,017–0,022 $ medidas ahora, más ~0,01 $ de la sonda de contexto por invocación) salen **~1,0 $**; el ~1,1 $ incluía las ejecuciones de prueba que no están registradas. Se deja ~1,0 $.
- **Coste real total de la tanda C:** C (sonda ~0,4 $, `10` ~0,16 $, `11` ~1,0 $, `12` ~1,3 $) ≈ **2,9 $**, más la batería de `autorrevision` (1,90 $), más esta batería C4 (1,52 $): **≈ 6,3 $ en total.**

**Filas para `docs/tipos-de-senal.md`:** aplicadas en el pase de textos C; manda `docs/tipos-de-senal.md`. La propuesta, con sus dos decisiones, está en `docs/historico/hallazgos-medidas-superadas.md`.

## Entrega 3 · tanda D, medidas de `app1/07` y `app2/04` (2026-11-07)

Versiones: claude-agent-sdk 0.2.173, CLI 2.1.309. Coste con modelo de la tanda, estimado: ≈ 3,9 $ (`app1/07` ≈ 0,15 $ y `app2/04` ≈ 3,7 $, repartido en tres medidas de ≈ 0,87 $, ≈ 0,97 $ y ≈ 1,84 $ más ≈ 0,04 $ de sondeos; ≈ 3,2 $ del total son de Haiku 4.5), con `max_budget_usd` en cada ejecución. Ese total no incluye la cuarta medida de `app2/04`, posterior (sus costes por variante, abajo). Los costes por variante registrados de la tercera medida no llegan a sus ≈ 1,84 $: el resto corresponde a ejecuciones intermedias sin registrar, cuyo coste no consta.

### `app1/07_recorte_de_contexto` (Messages API, Haiku 5.5, 5 ejecuciones por variante)

| Variante | Peticiones | Tokens de entrada en total | Máximo en una petición | Respuestas correctas |
| :--- | :--- | :--- | :--- | :--- |
| correcta (5 campos) | 11 en las 5 | 14 864 – 17 071 | 2 078 – 2 400 | 5/5 y 5/5 |
| `sin_recorte` (40 campos) | 11 en las 5 | 53 319 – 54 607 | 9 076 – 9 209 | 5/5 y 5/5 |

- La diferencia es de unas 3,4 veces en el total y unas 4,2 en el máximo (medias de las cinco ejecuciones). El coste por ejecución es ~0,0020 $ con recorte y ~0,006 $ sin él. Los tokens no dependen de la comprobación de la respuesta: las cifras de la medida anterior (14 741 – 15 073 y 52 788 – 55 849) eran de otras ejecuciones, y estas, de la tercera versión de la comprobación (ver abajo), son las vigentes.
- **La comprobación de la respuesta marcaba como incorrectas respuestas correctas** (0/10 en la primera medida). Primera causa: exigía que se nombrara un solo equipo y «Seguridad (EQ-06)» nombra al mismo equipo por nombre y por ID. Segunda causa, que solo se vio al volver a medir: la respuesta correcta suma «le siguen Finanzas TI y Redes». Tercera causa, señalada en la revisión independiente: cuatro equipos se llaman con palabras comunes (Redes, Datos, Seguridad, Plataforma), y la búsqueda sin mayúsculas daba falsos positivos («por seguridad revisé…» → equipo Seguridad) y falsos negativos («según los datos…»). Ahora cuenta el primer equipo que se nombra, buscando por ID antes que por nombre y con la mayúscula del nombre, con los límites de que no distingue «es X, no Y» de «es Y, no X» y de que una frase que empiece por «Datos…» sin ningún ID se tomaría por ese equipo. Las cifras de arriba son las de la comprobación corregida. ✓ roadmap 2026-11-08 §4.3.

### `app2/04_few_shot_y_escalamiento`, cuarta medida (Agent SDK, 13 casos por repetición, 2026-11-08)

**Vigente.** Tras la segunda revisión independiente se corrigió el detector de «pidió un ID» (exige una petición y el dato; un «?» o un posesivo solos ya no bastan) y no se lanza la insistencia sobre un primer turno cortado o con error. Las cifras de la tercera medida **no son comparables** con estas: el detector es otro. Las salidas completas están en `estado/<perfil>/medidas/` (fuera de git) y traen por caso la acción y si pidió el ID, **no el texto del agente**, así que los aciertos de homónimos no se pueden auditar uno a uno.

Los topes son los de `.env` (0,25 $ y 0,50 $ por ejecución del script; un intento de subirlos desde la shell no se aplicó, porque `.env` manda). Ningún caso cortado ni con error en las seis ejecuciones; la de Haiku 4.5 con la variante correcta usó 0,457 $ de 0,50 $.

Haiku 5.5 (rol `agent`, 5 repeticiones: 65 casos por variante).

| Variante | Correctos | Por tipo |
| :--- | :--- | :--- |
| correcta (criterios y 4 ejemplos) | 58/65 | petición de humano 15/15 · frustración 10/15 · vacío de política 15/15 · sin avance 9/10 · homónimos 9/10 |
| `sin_ejemplos` | 56/65 | petición de humano 15/15 · frustración 12/15 · vacío de política 15/15 · sin avance 9/10 · homónimos 5/10 |
| `sentimiento` | 30/65 | petición de humano 15/15 · frustración 0/15 · vacío de política 1/15 · sin avance 5/10 · homónimos 9/10 |
| `confianza` | 44/65 | petición de humano 15/15 · frustración 1/15 · vacío de política 15/15 · sin avance 6/10 · homónimos 7/10 |

Haiku 4.5 (rol `enforcement`, 3 repeticiones: 39 casos por variante).

| Variante | Correctos | Por tipo |
| :--- | :--- | :--- |
| correcta | 31/39 | petición de humano 9/9 · frustración 4/9 · vacío de política 9/9 · sin avance 4/6 · homónimos 5/6 |
| `sin_ejemplos` | 33/39 | petición de humano 9/9 · frustración 6/9 · vacío de política 9/9 · sin avance 4/6 · homónimos 5/6 |

- **Homónimos con Haiku 5.5:** correcta 9/10 y `sin_ejemplos` 5/10. Los fallos son el caso ESC-10, que sin ejemplos **no pidió el ID en las 5 repeticiones** y con ejemplos, en 1 de 5; ESC-11 lo pidió siempre en las dos variantes. Es un único caso con 5 repeticiones, y el detector solo mira el texto en los homónimos.
- **Frustración con Haiku 5.5:** correcta 10/15 y `sin_ejemplos` 12/15, es decir, en sentido contrario al de los homónimos. Con 15 casos y sin repetir, no se sostiene como diferencia en ninguna dirección. Total: 58/65 frente a 56/65.
- **Con Haiku 4.5 los ejemplos no se notan:** 31/39 frente a 33/39, con la frustración en 4/9 con ejemplos y 6/9 sin ellos. `sin_ejemplos` en frustración dio **7/9 (segunda medida), 4/9 (tercera) y 6/9 (cuarta)**, con el mismo prompt: la oscilación es de 3/9 entre medidas, del mismo tamaño que la «señal» que se atribuyó a los ejemplos. No es una señal estable.
- **`sentimiento` y `confianza`:** `sentimiento` 30/65 y `confianza` 44/65, frente a 56/65 de su control (`sin_ejemplos`). Fallan en la frustración sencilla (0/15 y 1/15); `sentimiento` deja pasar el vacío de política (1/15).
- **Confianza declarada:** media de 62,9 en los aciertos y 56,4 en los fallos. En las medidas anteriores el sentido cambió (60,6 y 50,3; 54,7 y 61,0; 60,8 y 61,7): no es una señal estable.
- **Coste por variante:** Haiku 5.5, 0,033 $ (`sentimiento`), 0,042 $ (`confianza`, correcta y `sin_ejemplos`); Haiku 4.5, 0,457 $ (correcta) y 0,388 $ (`sin_ejemplos`).
- **Coste total declarado de la tanda (≈ 3,9 $, al principio de esta sección):** no incluye esta cuarta medida, y el intento intermedio de la tercera no se desglosa: su coste **no consta**.

Las medidas tercera, segunda y primera de `app2/04` están en `docs/historico/hallazgos-medidas-superadas.md`, y la tabla de filas propuestas para `docs/tipos-de-senal.md` (ya aplicadas; manda `docs/tipos-de-senal.md`), también.

## Práctica guiada · preguntas de «Predice antes de ejecutar» confusas (2026-11-10)

Observado al seguir `app3/07`, `app3/08`, `app3/09`, `app2/04`, `app3/01` y `app3/02` con la práctica guiada. Es una impresión de una persona que practica, no una medida.

**Criterio general: ✓ roadmap 2026-11-12 §13** (ciclo, pasos 1, 4 y 5; regla 5 y regla 6, «Predicciones autónomas», de «Incorporación»; fases opcionales del narrador) **y §11.9** (revisión de los textos didácticos con otro modelo). Manda lo de allí: predicciones autónomas, de una sola cosa, marcadas `(guía)` o `(módulo)`, con su contraste `Pn` (con viñeta si son de guía) y lo no contrastable en «Para pensar»; opciones sin pistas de longitud ni de posición; comprobaciones cortas y cobertura de evaluación por módulo.

Lo propio de esta implementación (aplicado en las fases 1, 2 y 2b de «Mejoras didácticas», 2026-11-11 y 2026-11-12; detalle en `NOTAS.md`):

- **Dónde vive el criterio:** `plantillas/modulo/README.md`; lo comprueban `tests/test_readme_modulos.py` (forma de las predicciones, viñeta en cada `Pn` de guía, longitud de la correcta ≤ 1,25 × la media de las demás, ninguna letra > 40 % por app) y `tests/test_comprobaciones_cortas.py` (formato y cobertura; 0 pendientes). El narrador sirve las comprobaciones con las fases `comprobaciones` y `soluciones`.
- **Casos que lo originaron** (observados con la práctica guiada el 2026-11-10): `app3/07` predicciones 2 y 4 (escenario incompleto; cuatro preguntas en una), `app3/08` predicción 4 (mezclaba el mecanismo del módulo con el concepto), `app3/09` predicción 1 (sin los datos del plazo en el enunciado; hoy se parte en la idea de guía y el cálculo `(módulo)` con el margen de 2 h, sin la corrección síncrona que proponía la observación, porque el módulo no la define), `app2/04` (nombres sin fijar: hoy tablas T1–T5 y V1–V4, y el detector en «solo si ejecutas»), `app3/01` (papel del sintetizador y predicciones sobre él).
- **`app3/02`, el paralelo no lo garantiza el código:** resuelto con la nota «Cómo se consigue el paralelo» de la ficha (se pide por prompt y se comprueba en el registro). Las dos dudas sobre la API y el SDK que planteaba la observación siguen sin comprobar y no cambian la respuesta de examen (TS 1.3-S3).
- **Revisiones:** dos lecturas independientes con modelos distintos (Opus 5.5 sobre lo escrito con Fable 5.2, y al revés) encontraron 41 y 8 + 16 casos; las correcciones de la última no han pasado otra lectura. La comprobación con una persona (`app2/04` y `app3/09`) se hizo el 2026-11-12.

## Precedencia y superposición de nombres (2026-11-11, Claude Code 2.1.322)

Detalle y grilla unificada en `docs/referencia/precedencia/precedencia-y-nombres.md`; las pruebas propias, en `plan-pruebas.md` de la misma carpeta. Producto observado (no evaluable), leído de la documentación oficial de Claude Code, sin ejecutar nada en este repositorio.

- **Orden de prioridad entre nombres repetidos, y lo comprobado con pruebas propias** (2026-11-11, `claude -p` y sesión interactiva; P1 y P2 del plan): ✓ roadmap 2026-11-12 §4.3 («Nombres repetidos entre agentes, skills y commands»). Lo propio de esta implementación: la grilla unificada en `docs/referencia/precedencia/precedencia-y-nombres.md` y los casos, con sus órdenes, en `docs/referencia/precedencia/plan-pruebas.md`, sección 2 (modelo de la medida Opus 5.5, una observación por caso, fuera de este repositorio).
- **`settings.local.json` y `CLAUDE.local.md` no se ignoran solos:** ✓ roadmap 2026-11-12 §4.3. Lo propio de esta implementación: `.gitignore` lleva los dos.
- **Un subagente puede lanzar otros:** ✓ roadmap 2026-11-12 §4.3. Lo propio de esta implementación: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` en los módulos de `app3`.
- **`allowed-tools` concede permiso, no restringe tools:** ✓ roadmap 2026-11-01 §4.3, ampliado el 2026-11-12 con lo comprobado en una skill con `context: fork`. Detalle en `docs/referencia/precedencia/precedencia-y-nombres.md`; la sonda propia, en la entrada «`allowed-tools` en una skill sin `context: fork` preautoriza, no restringe» de «Práctica D3 y skills».
- **Sin respaldo en la documentación y sin probar:** si ante una contradicción se sigue el CLAUDE.md más cercano (prueba P6 del plan).

## Fase 3 · paquetes sin interacción con `claude -p` (2026-11-14 y 2026-11-15)

Cada paquete de la fase 3 se lanzó con `claude -p`, sin nadie que respondiera, y lo revisó después la sesión interactiva. Comprobado en 3.10 con Claude Code 2.1.325.

- **`acceptEdits` no escribe en `.claude/`, las órdenes compuestas se deniegan y un paquete hecho se marca «✓ hecho, no repetir»:** ✓ roadmap 2026-11-15 §4.3. Lo propio de esta implementación: la skill de 3.10-doc se escribió como borrador en `estado/<perfil>/headless/` y la copió la sesión interactiva.
- **Los textos escritos sin interacción copian los ejemplos de la guía, y una viñeta puede citarse de forma plausible sin respaldar la frase:** ✓ roadmap 2026-11-15 §4.3. Lo propio de esta implementación: E1, E2, E4 y E6 (revisión 3.9) y la cita de TS 4.1-K2 en E5, cambiada por TS 4.1-S1.
- **Una revisión de solo lectura no puede ejecutar `--check` ni búsquedas compuestas**; tiene que decir en su informe qué deja sin cubrir.
- **Los datos reales sacaron lo que los contratos no previeron:** la celda «Viñeta» de `FALLOS.md` se escribe a mano (varias viñetas, comentarios, solo la TS), y el repaso descartaba esas filas hasta 3.7-codigo.
- **Llevado también al roadmap el 2026-11-15** (eran reglas del proyecto sin marca `→ roadmap`): los dos formatos de pregunta (§2), el tipo de señal de cada parte y «un modelo es un banco de pruebas» (§13), y lo construido en la fase 3: repaso espaciado, práctica mezclada, hojas de repaso y simulaciones por escenario (§5, §10 `S-1` y §13).

## Fases 4 y 5 · documentos y código (2026-11-15)

Lo que se aprendió al reorganizar `docs/` y al refactorizar el código. Las lecciones que le servirían a otra implementación ya están en el roadmap; aquí queda lo propio de esta.

- **Una fuente por regla, con dos excepciones (el resumen de `CLAUDE.md` y las reglas por ruta):** ✓ roadmap 2026-11-15 §4. Lo propio: el mapa 4.0 y las decisiones de 4.1 en `NOTAS.md`.
- **`docs/` en estudio, construcción e histórico, con índice; lo superado a `docs/historico/` sin reescribir sus rutas:** ✓ roadmap 2026-11-15 §5.
- **Ninguna opción aceptada sin efecto y la variante correcta siempre `correcta`:** ✓ roadmap 2026-11-15 §2. Lo propio: `--repeat` repite en `app2/05` y en `app3/02` `paralelo` y se rechaza en `app2/03`, `06`, `07` y `app3/09`.
- **Helpers del arnés (`preamble`, `build_parser` por partes, `make_create`/`run_guarded`, `cargar`, `results`, `metrics`, `salida`):** ✓ roadmap 2026-11-15 §5. Lo propio: lo que se dejó sin migrar y por qué, en «5.2-app1» a «5.2-app3» de `NOTAS.md`.
- **Salida para quien estudia (`[mecanismo]`, `[esperado]`, `[clave]`, `[medida]`):** ✓ roadmap 2026-11-15 §13. Lo propio: solo en `app1/01`; vista con modelo (Haiku 5.5, 0,0006 $ con `--budget 0.05`), y extenderla al resto queda por decidir.
- **Con `--repeat N`, una ejecución cortada por presupuesto no cuenta en la tasa:** ✓ roadmap 2026-11-15 §4.3 (amplía la entrada de `app2/04`).
- **Tests de reglas por AST con control positivo; referencia de `--help`, salidas sin modelo y cadenas largas antes de refactorizar; lista de tests recogidos al fusionar:** ✓ roadmap 2026-11-15 §11.10–12.
- **Worktree con el mismo nombre de carpeta; dos corridas en paralelo para un paquete de diseño; tests de contrato que nunca se han ejecutado:** ✓ roadmap 2026-11-15 §4.3. Lo propio: 5.0 con Opus 5.5 y otra herramienta de otra familia de modelos; base de Opus por encajar con el código, con piezas de la otra (detalle en «5.0 · contratos» de `NOTAS.md`).
- **Revisiones independientes con otra herramienta cuando el modelo previsto no está:** 4.5 y 5.5 se hicieron así, con un encargo autónomo fuera de git (`estado/<perfil>/headless/4.5-encargo.md` y `5.5-encargo.md`), y cada hallazgo se comprobó en la sesión interactiva antes de aplicarlo. Sin hallazgos altos en ninguna de las dos.
