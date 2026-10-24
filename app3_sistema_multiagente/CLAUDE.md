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
- **Código legacy:** `app3/02` lee `datos/sinteticos/legacy_inventario/` como `cwd`, solo con tools de lectura; el paquete se regenera con `datos/generar_sinteticos.py`.
