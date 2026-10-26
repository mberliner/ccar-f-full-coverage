# CONCEPTOS

Registro viñeta → módulo o sección D3 donde se INTRODUCE. Cobertura objetivo: 240/240 (113 K y 127 S) contra la Exam Guide v1.0. Solo identificadores y destino: el texto de cada viñeta está en la guía oficial.

- **Destino:** `appN/NN_concepto` es el módulo que lleva el marcador; `d3` es la sección D3, cuyo marcador va en `d3_claude_code/`, `.claude/`, `docs/` o `CLAUDE.md` (roadmap §4).
- **Estado:** ☐ sin marcador todavía · ☑ con su único `INTRODUCE`. Se marca ☑ en el mismo cambio que añade el marcador; `tests/test_una_vez.py` comprueba que ambos coinciden.

## Dominios de la guía

`Dn` es el dominio `n` de la Exam Guide v1.0 y el prefijo de sus viñetas `TS n.x`.

| Dominio | Nombre | Peso |
| :--- | :--- | :---: |
| D1 | Agentic Architecture & Orchestration | 27% |
| D2 | Tool Design & MCP Integration | 18% |
| D3 | Claude Code Configuration & Workflows | 20% |
| D4 | Prompt Engineering & Structured Output | 20% |
| D5 | Context Management & Reliability | 15% |

## Reparto por entregas

Las apps se ordenan por complejidad creciente, pero se entregan por bloques de dominio (roadmap §10). Por eso una entrega reparte sus módulos entre varias apps y el dominio no coincide con la app.

| Entrega | Semana | Dominios | Módulos |
| :--- | :--- | :--- | :--- |
| 1 | `S-4` | D1 · bucle, control y sesiones | `app1/01` · `app2/01`, `02`, `03`, `05`, `06` · `app3/01`, `02` |
| 2 | `S-3` | D2 y D3 · tools, MCP y Claude Code | `app1/02`–`06` · `app3/03` · sección D3 |
| 3 | `S-2` | D4 y D5 · extracción, calidad, contexto y CI | `app1/07` · `app2/04` · `app3/04`–`12` |
| — | `S-1` | Repaso sin código nuevo | — |

El avance de cada entrega se registra en `NOTAS.md`.

**Introducidas: 113/240**

| Viñeta | Destino | Estado |
| :--- | :--- | :---: |
| TS 1.1-K1 | app1/01_bucle_manual | ☑ |
| TS 1.1-K2 | app1/01_bucle_manual | ☑ |
| TS 1.1-K3 | app1/01_bucle_manual | ☑ |
| TS 1.1-S1 | app1/01_bucle_manual | ☑ |
| TS 1.1-S2 | app1/01_bucle_manual | ☑ |
| TS 1.1-S3 | app1/01_bucle_manual | ☑ |
| TS 1.2-K1 | app3/01_coordinador | ☑ |
| TS 1.2-K2 | app3/01_coordinador | ☑ |
| TS 1.2-K3 | app3/01_coordinador | ☑ |
| TS 1.2-K4 | app3/01_coordinador | ☑ |
| TS 1.2-S1 | app3/01_coordinador | ☑ |
| TS 1.2-S2 | app3/01_coordinador | ☑ |
| TS 1.2-S3 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.2-S4 | app3/01_coordinador | ☑ |
| TS 1.3-K1 | app3/01_coordinador | ☑ |
| TS 1.3-K2 | app3/01_coordinador | ☑ |
| TS 1.3-K3 | app3/01_coordinador | ☑ |
| TS 1.3-K4 | app2/06_sesiones | ☑ |
| TS 1.3-S1 | app3/01_coordinador | ☑ |
| TS 1.3-S2 | app3/05_procedencia | ☐ |
| TS 1.3-S3 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.3-S4 | app3/01_coordinador | ☑ |
| TS 1.4-K1 | app2/01_prompt_vs_enforcement | ☑ |
| TS 1.4-K2 | app2/01_prompt_vs_enforcement | ☑ |
| TS 1.4-K3 | app2/05_multi_concern_y_handoff | ☑ |
| TS 1.4-S1 | app2/01_prompt_vs_enforcement | ☑ |
| TS 1.4-S2 | app2/05_multi_concern_y_handoff | ☑ |
| TS 1.4-S3 | app2/05_multi_concern_y_handoff | ☑ |
| TS 1.5-K1 | app2/02_hooks_pre_post | ☑ |
| TS 1.5-K2 | app2/02_hooks_pre_post | ☑ |
| TS 1.5-K3 | app2/02_hooks_pre_post | ☑ |
| TS 1.5-S1 | app2/02_hooks_pre_post | ☑ |
| TS 1.5-S2 | app2/02_hooks_pre_post | ☑ |
| TS 1.5-S3 | app2/02_hooks_pre_post | ☑ |
| TS 1.6-K1 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.6-K2 | app3/12_revision_independiente | ☐ |
| TS 1.6-K3 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.6-S1 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.6-S2 | app3/12_revision_independiente | ☐ |
| TS 1.6-S3 | app3/02_paralelo_y_descomposicion | ☑ |
| TS 1.7-K1 | app2/06_sesiones | ☑ |
| TS 1.7-K2 | app2/06_sesiones | ☑ |
| TS 1.7-K3 | app2/06_sesiones | ☑ |
| TS 1.7-K4 | app2/06_sesiones | ☑ |
| TS 1.7-S1 | app2/06_sesiones | ☑ |
| TS 1.7-S2 | app2/06_sesiones | ☑ |
| TS 1.7-S3 | app2/06_sesiones | ☑ |
| TS 1.7-S4 | app2/06_sesiones | ☑ |
| TS 2.1-K1 | app1/03_servidor_mcp | ☑ |
| TS 2.1-K2 | app1/03_servidor_mcp | ☑ |
| TS 2.1-K3 | app1/03_servidor_mcp | ☑ |
| TS 2.1-K4 | app1/03_servidor_mcp | ☑ |
| TS 2.1-S1 | app1/03_servidor_mcp | ☑ |
| TS 2.1-S2 | app1/03_servidor_mcp | ☑ |
| TS 2.1-S3 | app1/03_servidor_mcp | ☑ |
| TS 2.1-S4 | app1/03_servidor_mcp | ☑ |
| TS 2.2-K1 | app1/04_errores_estructurados | ☑ |
| TS 2.2-K2 | app1/04_errores_estructurados | ☑ |
| TS 2.2-K3 | app1/04_errores_estructurados | ☑ |
| TS 2.2-K4 | app1/04_errores_estructurados | ☑ |
| TS 2.2-S1 | app1/04_errores_estructurados | ☑ |
| TS 2.2-S2 | app1/04_errores_estructurados | ☑ |
| TS 2.2-S3 | app3/04_errores_entre_agentes | ☐ |
| TS 2.2-S4 | app1/04_errores_estructurados | ☑ |
| TS 2.3-K1 | app1/05_scoping_y_tool_choice | ☑ |
| TS 2.3-K2 | app3/03_tools_entre_roles | ☐ |
| TS 2.3-K3 | app3/03_tools_entre_roles | ☐ |
| TS 2.3-K4 | app1/05_scoping_y_tool_choice | ☑ |
| TS 2.3-S1 | app3/03_tools_entre_roles | ☐ |
| TS 2.3-S2 | app3/03_tools_entre_roles | ☐ |
| TS 2.3-S3 | app3/03_tools_entre_roles | ☐ |
| TS 2.3-S4 | app1/05_scoping_y_tool_choice | ☑ |
| TS 2.3-S5 | app1/05_scoping_y_tool_choice | ☑ |
| TS 2.4-K1 | app1/06_mcp_config | ☑ |
| TS 2.4-K2 | app1/06_mcp_config | ☑ |
| TS 2.4-K3 | app1/06_mcp_config | ☑ |
| TS 2.4-K4 | app1/06_mcp_config | ☑ |
| TS 2.4-S1 | app1/06_mcp_config | ☑ |
| TS 2.4-S2 | app1/06_mcp_config | ☑ |
| TS 2.4-S3 | app1/06_mcp_config | ☑ |
| TS 2.4-S4 | app1/06_mcp_config | ☑ |
| TS 2.4-S5 | app1/06_mcp_config | ☑ |
| TS 2.5-K1 | app1/02_tools_integradas | ☑ |
| TS 2.5-K2 | app1/02_tools_integradas | ☑ |
| TS 2.5-K3 | app1/02_tools_integradas | ☑ |
| TS 2.5-K4 | app1/02_tools_integradas | ☑ |
| TS 2.5-S1 | app1/02_tools_integradas | ☑ |
| TS 2.5-S2 | app1/02_tools_integradas | ☑ |
| TS 2.5-S3 | app1/02_tools_integradas | ☑ |
| TS 2.5-S4 | app1/02_tools_integradas | ☑ |
| TS 2.5-S5 | app1/02_tools_integradas | ☑ |
| TS 3.1-K1 | d3 | ☑ |
| TS 3.1-K2 | d3 | ☑ |
| TS 3.1-K3 | d3 | ☑ |
| TS 3.1-K4 | d3 | ☑ |
| TS 3.1-S1 | d3 | ☐ |
| TS 3.1-S2 | d3 | ☑ |
| TS 3.1-S3 | d3 | ☑ |
| TS 3.1-S4 | d3 | ☐ |
| TS 3.2-K1 | d3 | ☑ |
| TS 3.2-K2 | d3 | ☑ |
| TS 3.2-K3 | d3 | ☑ |
| TS 3.2-K4 | d3 | ☐ |
| TS 3.2-S1 | d3 | ☑ |
| TS 3.2-S2 | d3 | ☑ |
| TS 3.2-S3 | d3 | ☑ |
| TS 3.2-S4 | d3 | ☑ |
| TS 3.2-S5 | d3 | ☐ |
| TS 3.3-K1 | d3 | ☑ |
| TS 3.3-K2 | d3 | ☑ |
| TS 3.3-K3 | d3 | ☑ |
| TS 3.3-S1 | d3 | ☑ |
| TS 3.3-S2 | d3 | ☑ |
| TS 3.3-S3 | d3 | ☑ |
| TS 3.4-K1 | d3 | ☑ |
| TS 3.4-K2 | d3 | ☑ |
| TS 3.4-K3 | d3 | ☑ |
| TS 3.4-K4 | d3 | ☑ |
| TS 3.4-S1 | d3 | ☑ |
| TS 3.4-S2 | d3 | ☑ |
| TS 3.4-S3 | d3 | ☑ |
| TS 3.4-S4 | d3 | ☑ |
| TS 3.5-K1 | d3 | ☐ |
| TS 3.5-K2 | d3 | ☐ |
| TS 3.5-K3 | d3 | ☐ |
| TS 3.5-K4 | d3 | ☐ |
| TS 3.5-S1 | d3 | ☐ |
| TS 3.5-S2 | d3 | ☐ |
| TS 3.5-S3 | d3 | ☐ |
| TS 3.5-S4 | d3 | ☐ |
| TS 3.5-S5 | d3 | ☐ |
| TS 3.6-K1 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-K2 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-K3 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-K4 | app3/12_revision_independiente | ☐ |
| TS 3.6-S1 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-S2 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-S3 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-S4 | app3/11_criterios_y_ci | ☐ |
| TS 3.6-S5 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-K1 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-K2 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-K3 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-S1 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-S2 | app3/11_criterios_y_ci | ☐ |
| TS 4.1-S3 | app3/11_criterios_y_ci | ☐ |
| TS 4.2-K1 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 4.2-K2 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 4.2-K3 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 4.2-K4 | app3/07_extraccion_schema | ☐ |
| TS 4.2-S1 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 4.2-S2 | app3/11_criterios_y_ci | ☐ |
| TS 4.2-S3 | app3/11_criterios_y_ci | ☐ |
| TS 4.2-S4 | app3/07_extraccion_schema | ☐ |
| TS 4.2-S5 | app3/07_extraccion_schema | ☐ |
| TS 4.3-K1 | app3/07_extraccion_schema | ☐ |
| TS 4.3-K2 | app3/07_extraccion_schema | ☐ |
| TS 4.3-K3 | app3/07_extraccion_schema | ☐ |
| TS 4.3-K4 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S1 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S2 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S3 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S4 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S5 | app3/07_extraccion_schema | ☐ |
| TS 4.3-S6 | app3/07_extraccion_schema | ☐ |
| TS 4.4-K1 | app3/08_validacion_reintento | ☐ |
| TS 4.4-K2 | app3/08_validacion_reintento | ☐ |
| TS 4.4-K3 | app3/08_validacion_reintento | ☐ |
| TS 4.4-K4 | app3/08_validacion_reintento | ☐ |
| TS 4.4-S1 | app3/08_validacion_reintento | ☐ |
| TS 4.4-S2 | app3/08_validacion_reintento | ☐ |
| TS 4.4-S3 | app3/08_validacion_reintento | ☐ |
| TS 4.4-S4 | app3/08_validacion_reintento | ☐ |
| TS 4.5-K1 | app3/09_batches | ☐ |
| TS 4.5-K2 | app3/09_batches | ☐ |
| TS 4.5-K3 | app3/09_batches | ☐ |
| TS 4.5-K4 | app3/09_batches | ☐ |
| TS 4.5-S1 | app3/09_batches | ☐ |
| TS 4.5-S2 | app3/09_batches | ☐ |
| TS 4.5-S3 | app3/09_batches | ☐ |
| TS 4.5-S4 | app3/09_batches | ☐ |
| TS 4.6-K1 | app3/12_revision_independiente | ☐ |
| TS 4.6-K2 | app3/12_revision_independiente | ☐ |
| TS 4.6-K3 | app3/12_revision_independiente | ☐ |
| TS 4.6-S1 | app3/12_revision_independiente | ☐ |
| TS 4.6-S2 | app3/12_revision_independiente | ☐ |
| TS 4.6-S3 | app3/12_revision_independiente | ☐ |
| TS 5.1-K1 | app2/05_multi_concern_y_handoff | ☑ |
| TS 5.1-K2 | app3/05_procedencia | ☐ |
| TS 5.1-K3 | app1/07_recorte_de_contexto | ☐ |
| TS 5.1-K4 | app1/01_bucle_manual | ☑ |
| TS 5.1-S1 | app2/05_multi_concern_y_handoff | ☑ |
| TS 5.1-S2 | app2/05_multi_concern_y_handoff | ☑ |
| TS 5.1-S3 | app1/07_recorte_de_contexto | ☐ |
| TS 5.1-S4 | app3/05_procedencia | ☐ |
| TS 5.1-S5 | app3/05_procedencia | ☐ |
| TS 5.1-S6 | app3/05_procedencia | ☐ |
| TS 5.2-K1 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-K2 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-K3 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-K4 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-S1 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-S2 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-S3 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-S4 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.2-S5 | app2/04_few_shot_y_escalamiento | ☐ |
| TS 5.3-K1 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-K2 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-K3 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-K4 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-S1 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-S2 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-S3 | app3/04_errores_entre_agentes | ☐ |
| TS 5.3-S4 | app3/04_errores_entre_agentes | ☐ |
| TS 5.4-K1 | app3/06_contexto_largo | ☐ |
| TS 5.4-K2 | app3/06_contexto_largo | ☐ |
| TS 5.4-K3 | app3/06_contexto_largo | ☐ |
| TS 5.4-K4 | app3/06_contexto_largo | ☐ |
| TS 5.4-S1 | app3/06_contexto_largo | ☐ |
| TS 5.4-S2 | app3/06_contexto_largo | ☐ |
| TS 5.4-S3 | app3/06_contexto_largo | ☐ |
| TS 5.4-S4 | app3/06_contexto_largo | ☐ |
| TS 5.4-S5 | app3/06_contexto_largo | ☐ |
| TS 5.5-K1 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-K2 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-K3 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-K4 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-S1 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-S2 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-S3 | app3/10_confianza_y_revision | ☐ |
| TS 5.5-S4 | app3/10_confianza_y_revision | ☐ |
| TS 5.6-K1 | app3/05_procedencia | ☐ |
| TS 5.6-K2 | app3/05_procedencia | ☐ |
| TS 5.6-K3 | app3/05_procedencia | ☐ |
| TS 5.6-K4 | app3/05_procedencia | ☐ |
| TS 5.6-S1 | app3/05_procedencia | ☐ |
| TS 5.6-S2 | app3/05_procedencia | ☐ |
| TS 5.6-S3 | app3/05_procedencia | ☐ |
| TS 5.6-S4 | app3/05_procedencia | ☐ |
| TS 5.6-S5 | app3/05_procedencia | ☐ |

## Recuento por Task Statement

| TS | K | S |
| :--- | ---: | ---: |
| 1.1 | 3 | 3 |
| 1.2 | 4 | 4 |
| 1.3 | 4 | 4 |
| 1.4 | 3 | 3 |
| 1.5 | 3 | 3 |
| 1.6 | 3 | 3 |
| 1.7 | 4 | 4 |
| 2.1 | 4 | 4 |
| 2.2 | 4 | 4 |
| 2.3 | 4 | 5 |
| 2.4 | 4 | 5 |
| 2.5 | 4 | 5 |
| 3.1 | 4 | 4 |
| 3.2 | 4 | 5 |
| 3.3 | 3 | 3 |
| 3.4 | 4 | 4 |
| 3.5 | 4 | 5 |
| 3.6 | 4 | 5 |
| 4.1 | 3 | 3 |
| 4.2 | 4 | 5 |
| 4.3 | 4 | 6 |
| 4.4 | 4 | 4 |
| 4.5 | 4 | 4 |
| 4.6 | 3 | 3 |
| 5.1 | 4 | 6 |
| 5.2 | 4 | 5 |
| 5.3 | 4 | 4 |
| 5.4 | 4 | 5 |
| 5.5 | 4 | 4 |
| 5.6 | 4 | 5 |
