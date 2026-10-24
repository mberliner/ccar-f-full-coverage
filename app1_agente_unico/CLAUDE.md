<!--
CLAUDE.md de directorio: solo lo específico de app1. Lo común viene del CLAUDE.md
del proyecto y de sus @import.
USA: TS 3.1-K1, TS 3.1-K3
-->
# app1 · Agente único

- **Nivel:** un solo agente, sus tools y su bucle. Sin subagentes ni hooks (llegan en app2 y app3).
- **Messages API frente a Agent SDK:** `01_bucle_manual` usa el cliente `anthropic` directamente; no tiene `max_budget_usd`, así que su tope lo pone `harness/budget.py` (`CostGuard`). Los módulos del Agent SDK usan `harness/options.py`.
- **Credencial:** la Messages API solo admite API key; el módulo llama a `credentials.require_api_key()` antes de la primera petición.
- **Modelo:** rol `agent` de `harness/config.py`.
- **Tools locales:** las de `01` leen `datos/sinteticos/` con `harness/data.py`. El servidor MCP de la app llega en `03_servidor_mcp` (entrega 2).
