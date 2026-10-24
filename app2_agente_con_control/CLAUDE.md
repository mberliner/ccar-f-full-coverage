<!--
CLAUDE.md de directorio: solo lo específico de app2. Lo común viene del CLAUDE.md
del proyecto y de sus @import.
USA: TS 3.1-K1, TS 3.1-K3
-->
# app2 · Agente con control

- **Servidor compartido:** todos los módulos usan `servers/helpdesk.py`. Su estado (`HelpdeskState`) es uno por ejecución; los cambios entre fases (app2/06) van en sus `*_overrides`, nunca en `datos/sinteticos/`.
- **Vocabulario:** el dominio es una mesa de ayuda TI, no un comercio. La tabla de equivalencias con el examen está en el `README.md` de la app; no se renombran las tools para parecerse al examen.
- **Tools integradas:** los módulos pasan `tools=[]` para que el agente solo vea la mesa de ayuda. Ojo: eso quita también `Agent`; un módulo con subagentes pasa `tools=["Agent"]`.
- **Enforcement:** la puerta de verificación vive en el handler (`gate=True`) y el umbral de 500 EUR en el hook de `02`. No se duplican en otros módulos.
- **Modelo y presupuesto:** rol `agent` y presupuesto `agent` de `harness/config.py`. Excepción: `01_prompt_vs_enforcement` usa el rol `enforcement` (Haiku 4.5) en sus dos variantes, porque Haiku 5.5 no se salta la regla del prompt y la tasa no se vería.
