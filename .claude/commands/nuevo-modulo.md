---
description: Crea el esqueleto de un módulo de app (tests primero) a partir de las viñetas que CONCEPTOS.md le asigna.
argument-hint: "<appN/NN_concepto>"
# CONCEPTO [TS 3.2-K1, S1]: comando de proyecto.
# QUÉ DICE LA GUÍA: los comandos de .claude/commands/ se versionan con el
# repositorio y están disponibles para todo el equipo; los de ~/.claude/commands/
# son personales.
# POR QUÉ IMPORTA: crear un módulo sigue siempre los mismos pasos (cabecera,
# opciones del arnés, tests, CONCEPTOS.md); como comando compartido, cualquiera
# que clone el repositorio los repite igual.
# ANTI-PATRÓN: guardar el flujo del equipo como comando de usuario, que no llega
# a nadie más.
# INTRODUCE: TS 3.2-K1, TS 3.2-S1
---

Crea el módulo `$ARGUMENTS`.

1. **Viñetas del destino:** lee en `CONCEPTOS.md` las filas cuyo destino es `$ARGUMENTS`. Si no hay ninguna, para y dilo.
2. **Contenido de la guía:** lee en el roadmap la fila del módulo y la parte de la Exam Guide v1.0 de esas viñetas. Si no tienes acceso a la guía, pídela antes de seguir: los comentarios parafrasean la guía, no se inventan.
3. **Tests primero:** crea `tests/test_<app>_<NN_concepto>.py` con la lógica sin modelo (handlers, hooks, validadores) y comprueba que falla.
4. **Módulo:** crea `<app>_<nombre>/<NN_concepto>.py` con:
   - la cabecera fija (`CONCEPTO [TS x.y-Kn/Sn]` · `QUÉ DICE LA GUÍA` · `POR QUÉ IMPORTA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`);
   - un marcador `INTRODUCE` con todas las viñetas del paso 1;
   - las opciones construidas con `harness/options.py` (con `max_budget_usd`) y ejecutadas con `harness/recorder.py`;
   - la variante `--anti` si la viñeta describe un error.
5. **Registro:** en el mismo cambio, marca ☑ esas filas en `CONCEPTOS.md` y actualiza el contador. Añade al `README.md` de la app la fila viñeta→módulo, las predicciones y la pregunta tipo examen con la respuesta en `<details>`.
6. **Comprobación:** ejecuta `uv run pytest -q` y deja los tests en verde.
