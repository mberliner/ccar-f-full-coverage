---
paths: ["**/servers/**"]
---
# Servidores MCP de las apps

- **Código compartido:** los `servers/` los usan varios módulos. Solo llevan marcadores `USA`; el `INTRODUCE` va siempre en el módulo que enseña el concepto.
- **Descripciones:** cada tool lleva una descripción que dice qué hace, qué entrada espera y en qué se diferencia de las tools parecidas del mismo servidor.
- **Errores:** se devuelven como resultado con error y con metadatos estructurados, nunca como texto suelto ni como excepción sin capturar.
- **Datos:** salen de `datos/sinteticos/` y nunca de un sistema real.
- **Lógica:** cada handler tiene su test sin modelo con `harness/offline.call_tool`.

<!-- USA: TS 2.2-K1, TS 2.2-S1 -->
