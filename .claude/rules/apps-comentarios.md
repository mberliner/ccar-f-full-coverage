---
paths: ["app*/**/*.py"]
---
<!--
CONCEPTO [TS 3.1-K4, S3 · TS 3.3-K1, K2, S1]: reglas temáticas y carga condicional.
QUÉ DICE LA GUÍA: .claude/rules/ divide las convenciones por tema en vez de
acumularlas en un CLAUDE.md monolítico. El frontmatter YAML `paths`, con globs,
hace que la regla solo se cargue al trabajar con archivos que coinciden, lo que
ahorra contexto y tokens.
POR QUÉ IMPORTA: estas convenciones solo sirven al escribir módulos de app;
cargarlas al editar un test o un README sería contexto irrelevante.
ANTI-PATRÓN: meter en el CLAUDE.md raíz todo lo que solo aplica a un tipo de archivo.
INTRODUCE: TS 3.1-K4, TS 3.1-S3, TS 3.3-K1, TS 3.3-K2, TS 3.3-S1
-->
# Módulos de app

- **Cabecera fija:** `CONCEPTO [TS x.y-Kn/Sn]` · `QUÉ DICE LA GUÍA` (parafraseado, nunca copiado) · `POR QUÉ IMPORTA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`.
- **Hechos e inferencias:** se separan los hechos de la guía de las inferencias propias y de las notas `EN PRODUCCIÓN (no evaluable)`.
- **Pregunta tipo examen:** el módulo solo la enlaza. El escenario, las 4 opciones y la respuesta plegada en `<details>` van en el `README.md` de la app.
- **Par anti-patrón / correcto:** cuando la viñeta describe un error, el módulo implementa ambas variantes y se elige con `--anti`.
- **`ClaudeAgentOptions`:** se construye visible en el módulo con `harness/options.py`; nunca se esconde qué tools existen, cuáles se aprueban ni el modo de permisos.
- **Ejecución y datos:** las ejecuciones pasan por `harness/recorder.py` y los datos se leen de `datos/sinteticos/`.
- **Viñetas:** un `INTRODUCE` por viñeta en su módulo de destino (`CONCEPTOS.md`); las que ya están introducidas se marcan con `USA` y no se reexplican.
