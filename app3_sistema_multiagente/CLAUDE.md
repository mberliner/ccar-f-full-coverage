<!--
CLAUDE.md de directorio: solo lo específico de app3. Lo común viene del CLAUDE.md
del proyecto y de sus @import.
USA: TS 3.1-K1, TS 3.1-K3
-->
# app3 · Sistema multiagente

- **Modelos y presupuesto:** coordinador con el rol `coordinator` y subagentes con `subagent` (`harness/config.py`); presupuesto `multiagent`.
- **Subagentes:** `tools=["Agent"]` en el coordinador (la guía dice `Task`), `background=False` en cada `AgentDefinition` y, en el `env`, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`, `CLAUDE_CODE_FORK_SUBAGENT=0` y `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`. Sin esta última, la CLI 2.1.309 lanza los subagentes en segundo plano aunque la definición diga lo contrario.
- **Permisos:** el coordinador va en `dontAsk` y pre-aprueba `Agent` y las tools de búsqueda; los subagentes heredan ese modo.
- **Servidor compartido:** `servers/investigacion.py` separa siempre `content` de `metadata`. Un módulo nuevo que lo use no cambia ese formato.
- **Módulos de extracción (`07`–`09`):** usan la Messages API (no el Agent SDK) con `harness/budget.py`, así que necesitan API key y no llevan coordinador ni subagentes. `07` y `09` usan el rol `agent` (Sonnet 5.5 devuelve 400 con `tool_choice` `any` y forzado); `08` usa `enforcement` (Haiku 4.5), porque en la sonda A2 Haiku 5.5 no tuvo fallos de formato que reintentar. `08` y `09` cargan `07` con `importlib` (su nombre empieza por un dígito) y reutilizan su esquema y su puntuación. Los documentos de compra y sus etiquetas (que el agente nunca ve) los genera `datos/generar_sinteticos.py`.
- **Código legacy:** `app3/02` lee `datos/sinteticos/legacy_inventario/` como `cwd`, solo con tools de lectura; el paquete se regenera con `datos/generar_sinteticos.py`.
