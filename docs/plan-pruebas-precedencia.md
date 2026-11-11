# Pruebas de precedencia y superposición de nombres

Producto observado (no evaluable). Pruebas propias para los puntos que la documentación oficial de Claude Code no resuelve. Sus resultados son la fuente de las claves [P-n] de `docs/precedencia-y-nombres.md`. **Estado: P1 a P5 ejecutadas; P6, sin ejecutar.** Ningún resultado cambia una respuesta de examen.

## 1. Condiciones comunes

- **Dónde.** En un directorio desechable con `git init`, fuera de este repositorio (`<lab>`), para que ni `claudeMdExcludes` ni las reglas del proyecto alteren el resultado.
- **Nombres.** Todo lo que se crea lleva el prefijo `zz-prec-`.
- **Contenido marcador.** Cada definición responde con una cadena que dice de dónde viene (`ORIGEN=usuario-command`, `ORIGEN=proyecto-skill`…), así que el resultado se lee en la salida.
- **Coste.** Las ejecuciones con `claude -p` llevan `--max-budget-usd` y `--max-turns` (este último, solo como red de seguridad).
- **Tipo de señal.** Con las categorías de `docs/tipos-de-senal.md`.
- **Git Bash en Windows.** Hace falta `MSYS_NO_PATHCONV=1`: sin ella, un prompt como `/zz-prec-p3` llega convertido en una ruta.

## 2. Pruebas ejecutadas

Todas el 2026-11-11, con Claude Code 2.1.322 y modelo de la medida Opus 5.5. Una ejecución por caso.

| Prueba | Pregunta | Preparación | Resultado | Tipo de señal |
|---|---|---|---|---|
| P1 | Command de usuario y command de proyecto con el mismo nombre: ¿cuál ejecuta `/nombre`? | `zz-prec-p1.md` en `~/.claude/commands/` y en `<lab>/.claude/commands/` | El de usuario (`ORIGEN=usuario-command`). El menú `/` y `/skills` listan los dos, sin marcar cuál se ejecuta | Determinista (origen) |
| P2a | Command de usuario frente a skill de proyecto | `~/.claude/commands/zz-prec-p2.md` y `<lab>/.claude/skills/zz-prec-p2/SKILL.md` | La skill de proyecto (`ORIGEN=proyecto-skill`). El menú la pone primera | Determinista (origen y orden del menú) |
| P2b | Skill de usuario frente a command de proyecto | `~/.claude/skills/zz-prec-p2/SKILL.md` y `<lab>/.claude/commands/zz-prec-p2.md` | La skill de usuario (`ORIGEN=usuario-skill`). El menú la pone primera | Determinista (origen y orden del menú) |
| P3a | Agente y skill con el mismo nombre: ¿chocan o conviven? | `<lab>/.claude/agents/zz-prec-p3.md` y `<lab>/.claude/skills/zz-prec-p3/SKILL.md` | Conviven: el agente figura en la lista de agentes y la skill en la de skills. `/zz-prec-p3` devolvió `ORIGEN=skill` y `@zz-prec-p3`, `ORIGEN=agente` | Determinista (listas); el origen lo confirma |
| P3b | Agente y command con el mismo nombre | El mismo agente y `<lab>/.claude/commands/zz-prec-p3.md` en lugar de la skill | Conviven: `/zz-prec-p3` devolvió `ORIGEN=command` y `@zz-prec-p3`, `ORIGEN=agente` | Determinista (listas); el origen lo confirma |
| P4a | Skill con `context: fork`: ¿`allowed-tools` da al subagente una tool que su `tools` no incluye? | Skill con `allowed-tools: Bash(python *)` y `agent` con `tools: Read, Grep`; el cuerpo pide ejecutar un comando `python` con Bash | No: el subagente declaró solo `Read` y `Grep` y no hubo ninguna llamada a Bash. Manda `tools` del agente | Determinista (no hay llamada en el registro); la lista de tools la declara el modelo |
| P4b | ¿El permiso de `allowed-tools` llega al subagente para una tool que sí tiene? | La misma skill con un `agent` con `tools: Read, Bash`; sin reglas `allow` para Bash | Sí: la llamada a Bash se ejecutó sin denegación | Determinista |
| P4c | Control de P4b | Como P4b, sin `allowed-tools` | La misma llamada figura en las denegaciones de permiso | Determinista |
| P5 | Agente de plugin y agente de proyecto con el mismo nombre corto | Plugin `zz-prec-plugin` con `agents/zz-prec-p5.md`, cargado con `--plugin-dir`, y `<lab>/.claude/agents/zz-prec-p5.md` | Conviven. Solo con el plugin, la lista trae únicamente `zz-prec-plugin:zz-prec-p5`. Con los dos, `zz-prec-p5` devolvió `ORIGEN=proyecto-agente` y `zz-prec-plugin:zz-prec-p5`, `ORIGEN=plugin-agente` | Determinista (listas); el origen lo confirma |

**Cómo se observó.**

- **P1 y P2:** en sesión interactiva (`claude --model claude-opus-5-5`), con los niveles `user` y `project` activos y una sesión nueva por caso. Se miraron el menú `/` y `/skills`, y el origen se obtuvo enviando `/nombre`. `/skills` lista también los commands, sin distinguir el tipo.
- **P3 a P5:** con `claude -p --model claude-opus-5-5 --setting-sources project --output-format stream-json --verbose --max-budget-usd 0.50 --max-turns 6`. Las listas de agentes y skills salen del mensaje inicial del registro; las llamadas a tools y las denegaciones, del resto.
- **`/doctor` no sirve de señal para estos choques:** su texto lo redacta el modelo y no avisa de forma coherente (lo hizo en P1 y P2b, no en P2a).

## 3. Prueba pendiente

### P6. Contradicción entre CLAUDE.md: ¿se sigue el más cercano?

- **Pregunta.** La documentación dice que lo más cercano al directorio de arranque se lee al final y que, ante una contradicción, el modelo puede elegir arbitrariamente. ¿Hay de hecho una preferencia medible?
- **Preparación.**
  - `<lab>/CLAUDE.md`: «Termina siempre tu respuesta con la palabra ALFA en una línea aparte».
  - `<lab>/sub/CLAUDE.md`: «Termina siempre tu respuesta con la palabra BETA en una línea aparte».
- **Pasos.**
  1. Sin modelo: abrir `claude` en `<lab>/sub` y comprobar con `/memory` que están cargados los dos archivos.
  2. Con modelo, desde `<lab>/sub`: 10 ejecuciones de `claude -p "Di hola." --setting-sources project --max-budget-usd 0.20 --max-turns 2`. Contar ALFA, BETA, ambas y ninguna.
  3. Control de posición: intercambiar las palabras entre los dos archivos y repetir las 10 ejecuciones, para separar el efecto de la cercanía del de la palabra.
  4. Anotar el modelo de la medida y la salida de `claude --version`.
- **Lectura.** Solo se afirma preferencia si el archivo cercano gana en al menos 9 de 10 en las dos tandas. Cualquier otro resultado se registra como `Sin señal estable`, que es lo que la documentación ya advierte.
- **Tipo de señal.** Probabilística con control positivo (el control es el intercambio del paso 3). El paso 1 es determinista.
- **Coste máximo.** 20 ejecuciones × 0,20 USD = 4 USD.

**Al cerrarla:**

- El resultado pasa a la tabla de la sección 2 y, como hecho con la clave [P-6], a `docs/precedencia-y-nombres.md`, donde sale de la sección 8.
- Se añade una línea con fecha y versión a `docs/hallazgos.md`. Si el resultado compara modelos, va solo allí.
- Se borra `<lab>`. Las sesiones abiertas en él dejan una entrada en `projects` de `~/.claude.json` y una carpeta en `~/.claude/projects/`, que también se pueden borrar.
