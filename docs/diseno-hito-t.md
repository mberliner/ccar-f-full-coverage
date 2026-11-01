# Diseño del Hito T · incorporación transversal («quien llega de cero»)

## Context
Los dos primeros ejercicios resultaron difíciles de seguir, para alguien de fuera y también para quien los escribió, y el resto repetía el mismo patrón: el problema es transversal. Del análisis salió la regla de roadmap §13 «Incorporación de quien llega de cero» (2026-10-30), pero **quedó sin dueño**: ningún hito de §10 la cubre, `NOTAS.md` no la lista y solo `app1/01` la aplica. `docs/hallazgos.md:75` ya describe lo pendiente: sitio común (entrada de principiante y glosario en el `README.md` raíz) y contexto específico en `app1/02`–`06` y en `app2`/`app3`.

Objetivo: convertir la regla en un estándar que cumplan por construcción los módulos de la entrega 3 y que, a bajo coste, alcance a los ya entregados; y reflejarlo en el roadmap origen.

## Hechos del estado actual (verificados)
- `README.md` raíz: tiene «Cómo se usa», requisitos y primeros pasos; **sin glosario ni orden de entrada por módulos**.
- `app1/README.md`: único con «Antes de empezar» (solo en la sección 01). `app2` y `app3`: sin él.
- `.claude/commands/nuevo-modulo.md` (comando; el listado lo muestra también como skill) crea el esqueleto sin exigir bloque de contexto.
- No hay test que compruebe la estructura de los README de módulo.
- Roadmap origen: `claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md` (§13 en l.270–302, §14 bitácora l.304+, §10 hitos l.187+).

## Pasos y modelo asignado
Criterio del proyecto (`NOTAS.md`): Sonnet escribe código y tests; **Opus 5.5 para los textos didácticos**. Revisión final por instancia independiente (`docs/estandares-flujo.md`).

| # | Paso | Modelo | Por qué |
|---|---|---|---|
| 1 | Roadmap origen: §13 gana una regla 5 («plantilla y comprobación mínima») y se declara dueño: nuevo bloque transversal «Hito T» en §10 (antes de la entrega 3, sin viñetas); línea en §14; §4.1 menciona el glosario. Pasar `hallazgos.md:75` a puntero `✓ roadmap <fecha> §13/§10` | **Opus** | Decide criterio de diseño y redacta texto agnóstico |
| 2 | `docs/glosario.md` único (tool, iteración, `stop_reason`, historial, anti-patrón, hook, case facts…) tomando como base el «Antes de empezar» de `app1/01`; el README raíz gana «Por dónde empezar» (orden de apps, coste, enlace al glosario) | **Opus** | Texto didáctico, sin adelantar resultados |
| 3 | Plantilla de README de módulo en `plantillas/` (Antes de empezar · tools · Predice por patrones · Ejecutar · Qué observar · Pregunta) y que `.claude/commands/nuevo-modulo.md` la use | **Sonnet** | Mecánico; el texto-guía de la plantilla lo fija el paso 1 |
| 4 | `tests/test_readme_modulos.py` (tests primero): cada sección `## NN ·` de `app*/README.md` tiene «Antes de empezar» y «Pregunta tipo examen». Se aplica solo a módulos nuevos al principio (lista de excepciones explícita para los 14 viejos) | **Sonnet** | Lógica sin modelo; no comprueba calidad (eso lo hace la revisión) |
| 5 | Retroadaptación **de todos los módulos** (el problema es transversal, no de dos ejercicios; las dos primeras pruebas lo destaparon y el resto repite el patrón). Por tandas: `app1/02`–`06` → `app2/01`–`07` → `app3/01`–`03`; `app1/01` solo se alinea con la plantilla. Solo texto: contexto específico y predicciones por patrón/rango; **no se tocan cifras medidas ni lógica** | **Opus** | Texto didáctico con riesgo de alterar cifras medidas |
| 6 | Revisión independiente (instancia sin contexto) de pasos 2–5 contra las 4 reglas de §13 | **Opus**, instancia nueva | Regla del proyecto: no revisa quien escribió |
| 7 | `NOTAS.md`: línea de hito T con fecha; retirar «pendiente» de hallazgos | Sonnet | Registro |

Orden: 1 → 2 → 3+4 (en paralelo; el test arranca con excepciones que se vacían según avanza el paso 5) → 5 (por tandas, tests en verde tras cada una) → 6 → 7. Todo antes de diseñar la entrega 3, que ya nacería con plantilla.

## Archivos críticos
- Roadmap: `claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md` (repositorio de estudio) (§4.1, §10, §13, §14). Es **otro repositorio**: commit aparte allí.
- Este repo: `README.md`, `docs/glosario.md` (nuevo), `plantillas/modulo/README.md` (nuevo), `.claude/commands/nuevo-modulo.md`, `tests/test_readme_modulos.py` (nuevo), `app{1,2,3}_*/README.md`, `NOTAS.md`, `docs/hallazgos.md`.
- Reutilizar: bloque «Antes de empezar» y tabla de tools de `app1_agente_unico/README.md` (l.23–40) como modelo; `tests/cargar.py` si sirve para localizar módulos.
- Regla «una vez»: el glosario no lleva marcadores `INTRODUCE`; no cambia `CONCEPTOS.md`.

## Verificación
- `uv run pytest` en verde (incluido el nuevo test; `test_full_coverage` sigue `xfail`).
- `/verificar-concepto` sobre 2–3 viñetas de módulos retroadaptados: cabecera sigue completa.
- Diff de los README retroadaptados: ninguna cifra medida cambia (revisar con `git diff` filtrando números).
- Prueba de lectura en frío: una instancia sin contexto lee README raíz + `app2/01` y dice si puede predecir sin ayuda.
- Roadmap: `grep` de «Hito T»/regla 5 coherente entre §10, §13 y §14, sin rutas absolutas ni nombres propios.

## Decisiones tomadas
- Alcance del paso 5: todos los módulos (el problema es transversal, no puntual).
- Roadmap: Hito T en §10 y regla 5 en §13 (confirmado).
- Pendiente menor: commit del roadmap en su propio repositorio (se confirma antes de commitear).

## Adaptación (2026-10-31): Opus no está disponible como subagente
Los subagentes con `model: opus` dieron 429 con la configuración de la cuenta de construcción y no editaron nada. Reparto corregido:
- **Aquí, con Sonnet 5.5:** pasos 3, 4 y 7 (plantilla, test, registro) y la coordinación.
- **Con Opus, fuera de esta sesión** (`claude -p --model opus` o a mano en otra sesión): pasos 1, 2, 5 y 6. Cada uno tiene un prompt autocontenido en `docs/prompts-hito-t/`. Tras cada uno, aquí se revisa el diff, se corre `pytest` y se sigue.
- Si Opus no llega a hacerse, el fallback es Sonnet con los mismos prompts, y la revisión del paso 6 la hace una instancia nueva (nunca la que escribió).
- El directorio del roadmap origen **no es un repositorio git**: no hay commit allí, solo edición.
