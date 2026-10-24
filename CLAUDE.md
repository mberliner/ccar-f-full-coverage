<!--
CONCEPTO [TS 3.1-K1, K2, K3, S2]: jerarquía de CLAUDE.md e @import.
QUÉ DICE LA GUÍA: hay tres niveles (usuario en ~/.claude/CLAUDE.md, proyecto en
CLAUDE.md o .claude/CLAUDE.md, y directorio en subcarpetas). El de usuario solo
aplica a esa persona y no viaja por git. @import trae archivos externos para
mantener CLAUDE.md modular e incluir solo los estándares que cada parte necesita.
POR QUÉ IMPORTA: una regla del equipo puesta en el nivel de usuario no le llega a
nadie más; un CLAUDE.md monolítico carga en todas partes lo que solo vale en una.
ANTI-PATRÓN: guardar instrucciones compartidas en ~/.claude/CLAUDE.md, o copiar
los mismos estándares en cada CLAUDE.md en vez de importarlos.
INTRODUCE: TS 3.1-K1, TS 3.1-K2, TS 3.1-K3, TS 3.1-S2
-->
# ccar-f-full-coverage

Apps agénticas de demostración para practicar todas las viñetas del examen CCAR-F. El diseño completo vive en el roadmap del repositorio de estudio (`claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`).

## Contexto heredado

Los `CLAUDE.md` de directorios padre no aplican aquí y contaminarían las pruebas. Se excluyen con `claudeMdExcludes` en `.claude/settings.local.json`, que no se versiona porque el patrón depende de la ubicación de cada persona. Se crea copiando `.claude/settings.local.example.json`: un patrón por cada `CLAUDE.md` padre que aparezca en `/memory`, y en `enabledPlugins` los plugins de la cuenta propia que deban apagarse aquí (o la clave vacía). Comprobar con `/memory` y `/plugin`; si alguno vuelve a aparecer en contexto, se ignora y se corrige el patrón.

## Jerarquía

- Este archivo es el nivel de proyecto y se comparte por git.
- Cada app tendrá su propio `CLAUDE.md`, solo con lo específico de esa app.
- Las convenciones por tipo de archivo viven en `.claude/rules/`.
- Nada del proyecto va en `~/.claude/CLAUDE.md`, porque no le llegaría a nadie más.

## Reglas del proyecto

- **Perímetro de la guía:** solo los mecanismos que nombra la Exam Guide v1.0.
- **Aislamiento de los agentes de las apps:** lo aplica `harness/options.py`.
- **Regla «una vez»:** un único `INTRODUCE` por viñeta; después, solo `USA`.
- **Datos:** siempre sintéticos y generados por `datos/generar_sinteticos.py`.
- **Coste:** `max_budget_usd` en toda ejecución con modelo.
- **Registros:** `CLAUDE.md` solo lleva contexto y reglas estables. El avance de los hitos y el *scratchpad* de sesión van en `NOTAS.md`; las predicciones y respuestas fallidas, en `FALLOS.md`.

Detalle de código y de flujo:

@docs/estandares-codigo.md
@docs/estandares-flujo.md
