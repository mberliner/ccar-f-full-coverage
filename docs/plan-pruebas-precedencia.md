# Plan de pruebas: precedencia y superposición de nombres

Producto observado (no evaluable). Cubre los puntos que la documentación oficial de Claude Code no resuelve y que `docs/precedencia-y-nombres.md` lista en su sección 8. **Estado: P3, P4 y P5 ejecutadas el 2026-11-11 (sección 3); P1, P2 y P6, sin ejecutar.** Ningún resultado de este plan cambia una respuesta de examen.

## 1. Condiciones comunes

- **Versión.** Anotar la salida de `claude --version` al ejecutar. El plan se escribió con Claude Code 2.1.322.
- **Dónde.** En un directorio desechable fuera de este repositorio, con `git init`, para que ni `claudeMdExcludes` ni las reglas del proyecto alteren el resultado. En el plan se llama `<lab>`.
- **Nombres.** Todo lo que se crea lleva el prefijo `zz-prec-`, para no chocar con nada real y poder borrarlo sin dudas.
- **Nivel de usuario.** P1 y P2 escriben en `~/.claude/commands/` y `~/.claude/skills/`. Solo se crean archivos `zz-prec-*` y se borran al acabar (sección 4). Si se prefiere no tocar la configuración propia, se puede apuntar `CLAUDE_CONFIG_DIR` a un directorio vacío, lo que exige autenticarse de nuevo en él.
- **Contenido marcador.** Cada definición devuelve una cadena única que dice de dónde viene (`ORIGEN=proyecto-command`, `ORIGEN=usuario-skill`…). Así el resultado se lee en la salida y no depende de interpretar al modelo.
- **Coste.** Las pruebas con modelo se lanzan con `claude -p … --max-budget-usd 0.50 --max-turns 6`. `--max-turns` es solo red de seguridad.
- **Tipo de señal.** Cada prueba declara el suyo con las categorías de `docs/tipos-de-senal.md`. Se prefiere la señal sin modelo (`/skills`, `/agents`, `/doctor`, menú `/`).
- **Fuentes de configuración.** No usar `--setting-sources` ni `--bare`: las pruebas necesitan los niveles `user` y `project` activos.

## 2. Pruebas

### P1. Command de usuario frente a command de proyecto

- **Pregunta.** Con el mismo nombre en `~/.claude/commands/` y en `<lab>/.claude/commands/`, ¿cuál ejecuta `/nombre`?
- **Lo documentado.** Entre skills, la personal gana a la de proyecto. Para dos archivos de command no hay regla escrita.
- **Preparación.**
  - `~/.claude/commands/zz-prec-p1.md`: `description: P1 usuario`; cuerpo: «Responde solo con: ORIGEN=usuario-command».
  - `<lab>/.claude/commands/zz-prec-p1.md`: `description: P1 proyecto`; cuerpo: «Responde solo con: ORIGEN=proyecto-command».
- **Pasos.**
  1. Abrir `claude` en `<lab>`. Escribir `/zz-prec-p1` sin enviar y anotar cuántas entradas muestra el menú y con qué descripción.
  2. Ejecutar `/skills` y anotar qué entrada aparece y con qué origen.
  3. Ejecutar `/doctor` y anotar si avisa del duplicado.
  4. Con modelo: `claude -p "/zz-prec-p1" --max-budget-usd 0.50 --max-turns 6` y anotar el `ORIGEN`.
- **Resultados posibles.** Gana usuario (igual que en skills), gana proyecto, o se listan las dos.
- **Tipo de señal.** Determinista (pasos 1 a 3). El paso 4 solo confirma.

### P2. Skill y command con el mismo nombre en niveles distintos

- **Pregunta.** La documentación dice que la skill gana al command. ¿Se mantiene cuando el command está en un nivel que, entre skills, tendría prioridad?
- **Preparación y casos.** Se ejecutan por separado, borrando el anterior.
  - **P2a:** command de usuario (`~/.claude/commands/zz-prec-p2.md`, `ORIGEN=usuario-command`) frente a skill de proyecto (`<lab>/.claude/skills/zz-prec-p2/SKILL.md`, `ORIGEN=proyecto-skill`).
  - **P2b:** skill de usuario (`~/.claude/skills/zz-prec-p2/SKILL.md`, `ORIGEN=usuario-skill`) frente a command de proyecto (`<lab>/.claude/commands/zz-prec-p2.md`, `ORIGEN=proyecto-command`).
- **Pasos.** Los mismos cuatro de P1, con `/zz-prec-p2`.
- **Resultados posibles.** La skill gana en los dos casos (el tipo manda sobre el nivel) o gana el nivel personal en los dos (el nivel manda sobre el tipo). P2a es el caso que distingue las dos reglas.
- **Tipo de señal.** Determinista.

### P3. Agente frente a skill y frente a command

- **Pregunta.** ¿Un agente y una skill (o un command) con el mismo nombre chocan o conviven?
- **Lo documentado.** Los agentes se invocan por lenguaje natural, con mención `@` o como sesión completa con `--agent`; las skills, con `/nombre` o con la tool `Skill`. Nada dice de un nombre compartido.
- **Hipótesis (inferencia propia).** Conviven, porque las vías de invocación son distintas.
- **Preparación.**
  - `<lab>/.claude/agents/zz-prec-p3.md`: `name: zz-prec-p3`, `description: P3 agente`, `tools: Read`; cuerpo: «Responde solo con: ORIGEN=agente».
  - **P3a:** `<lab>/.claude/skills/zz-prec-p3/SKILL.md` con `ORIGEN=skill`.
  - **P3b:** en lugar de la skill, `<lab>/.claude/commands/zz-prec-p3.md` con `ORIGEN=command`.
- **Pasos.**
  1. `/agents` lista el agente y `/skills` lista la skill o el command. Anotar si alguno falta o aparece renombrado.
  2. `/doctor`: anotar avisos.
  3. Escribir `/zz-prec-p3` y `@zz-prec-p3` sin enviar y anotar qué ofrece cada menú.
  4. Con modelo, dos ejecuciones: `claude -p "/zz-prec-p3"` y `claude -p "@zz-prec-p3 responde"`, ambas con el tope de coste. Anotar el `ORIGEN` de cada una.
- **Resultados posibles.** Conviven (cada vía devuelve su origen), uno oculta al otro, o hay aviso de conflicto.
- **Tipo de señal.** Determinista (pasos 1 a 3).

### P4. `allowed-tools` de la skill y `tools` del agente con `context: fork`

- **Pregunta.** En una skill con `context: fork`, ¿`allowed-tools` puede dar al subagente una tool que su `tools` no incluye? ¿Y concede permiso dentro del subagente para una tool que sí tiene?
- **Lo documentado.** `allowed-tools` concede permiso y no restringe; `tools` del agente es la lista de tools disponibles; con `context: fork`, el campo `agent` determina modelo, tools y permisos. No se describe la combinación.
- **Preparación.**
  - `<lab>/datos.txt` con una línea: `MARCA-P4`.
  - Agente `zz-prec-p4-lector`: `tools: Read, Grep`.
  - Agente `zz-prec-p4-shell`: `tools: Read, Bash`.
  - Skill `zz-prec-p4`: `context: fork`, `background: false`, `allowed-tools: Bash(cat *)`; cuerpo: «Ejecuta con Bash `cat datos.txt` y devuelve la salida literal. Si no tienes la tool Bash, responde SIN-BASH. Si se te deniega el permiso, responde DENEGADO».
  - Sin reglas `allow` para Bash en ningún nivel de settings.
- **Casos.**
  - **P4a:** `agent: zz-prec-p4-lector`. ¿Aparece Bash entre las tools del subagente?
  - **P4b:** `agent: zz-prec-p4-shell`. ¿Se ejecuta `cat` sin pedir permiso?
  - **P4c (control):** como P4b pero sin `allowed-tools`. Debe pedir permiso o denegarse; si no, P4b no demuestra nada.
- **Pasos.** Para cada caso: `claude -p "/zz-prec-p4" --output-format stream-json --verbose --max-budget-usd 0.50 --max-turns 6`. En el registro, mirar la lista de tools del subagente, si hay un `tool_use` de Bash y su resultado.
- **Resultados posibles.** P4a: `SIN-BASH` (manda `tools`) o `MARCA-P4` (`allowed-tools` amplía). P4b: `MARCA-P4` (el permiso llega al fork) o `DENEGADO` (no llega).
- **Tipo de señal.** Determinista en lo que importa: la lista de tools del subagente y la decisión de permiso salen del registro. Que el modelo intente la llamada es probabilístico, así que cada caso se repite hasta tres veces si no hay intento.

### P5. Agente de plugin frente a agente de proyecto

- **Pregunta.** La documentación pone los agentes de plugin en el último lugar de prioridad y, a la vez, dice que se registran con nombre calificado (`plugin:agente`). Con el mismo nombre corto en un plugin y en el proyecto, ¿se cargan los dos o el de proyecto oculta al de plugin?
- **Preparación.**
  - Plugin mínimo en `<lab>/../zz-prec-plugin/`: `.claude-plugin/plugin.json` con `"name": "zz-prec-plugin"` y `agents/zz-prec-p5.md` (`ORIGEN=plugin-agente`).
  - `<lab>/.claude/agents/zz-prec-p5.md` (`ORIGEN=proyecto-agente`).
- **Pasos.**
  1. `claude --plugin-dir ../zz-prec-plugin` en `<lab>`.
  2. `/agents`: anotar si aparecen `zz-prec-p5` y `zz-prec-plugin:zz-prec-p5`, o solo uno.
  3. Escribir `@zz-prec` sin enviar y anotar las entradas.
  4. Con modelo, mención `@` a cada nombre que exista y anotar el `ORIGEN`.
  5. Repetir los pasos 2 y 3 tras borrar el agente de proyecto, para ver si el de plugin responde también al nombre corto.
- **Resultados posibles.** Conviven con nombres distintos (la prioridad 5 solo se aplicaría al nombre corto) o el de proyecto oculta al de plugin.
- **Tipo de señal.** Determinista (pasos 2, 3 y 5).

### P6. Contradicción entre CLAUDE.md: ¿se sigue el más cercano?

- **Pregunta.** La documentación dice que lo más cercano al directorio de arranque se lee al final y que, ante una contradicción, el modelo puede elegir arbitrariamente. ¿Hay de hecho una preferencia medible?
- **Preparación.**
  - `<lab>/CLAUDE.md`: «Termina siempre tu respuesta con la palabra ALFA en una línea aparte».
  - `<lab>/sub/CLAUDE.md`: «Termina siempre tu respuesta con la palabra BETA en una línea aparte».
- **Pasos.**
  1. Sin modelo: abrir `claude` en `<lab>/sub` y comprobar con `/memory` que están cargados los dos archivos.
  2. Con modelo, desde `<lab>/sub`: 10 ejecuciones de `claude -p "Di hola." --max-budget-usd 0.20 --max-turns 2`. Contar ALFA, BETA, ambas y ninguna.
  3. Control de posición: intercambiar las palabras entre los dos archivos y repetir las 10 ejecuciones, para separar el efecto de la cercanía del de la palabra.
  4. Anotar el modelo de la medida.
- **Lectura.** Solo se afirma preferencia si el archivo cercano gana en al menos 9 de 10 en las dos tandas. Cualquier otro resultado se registra como `Sin señal estable`, que es lo que la documentación ya advierte.
- **Tipo de señal.** Probabilística con control positivo (el control es el intercambio del paso 3). El paso 1 es determinista.
- **Coste máximo.** 20 ejecuciones × 0,20 USD = 4 USD.

## 3. Registro de resultados

| Prueba | Fecha | Versión | Modelo (si aplica) | Resultado | Tipo de señal |
|---|---|---|---|---|---|
| P1 | | | | | |
| P2a | | | | | |
| P2b | | | | | |
| P3a | 2026-11-11 | 2.1.322 | Opus 5.5 | Conviven: el agente figura en la lista de agentes y la skill en la de skills; `/zz-prec-p3` devolvió `ORIGEN=skill` y `@zz-prec-p3`, `ORIGEN=agente` | Determinista (listas); el origen lo confirma |
| P3b | 2026-11-11 | 2.1.322 | Opus 5.5 | Conviven: `/zz-prec-p3` devolvió `ORIGEN=command` y `@zz-prec-p3`, `ORIGEN=agente` | Determinista (listas); el origen lo confirma |
| P4a | 2026-11-11 | 2.1.322 | Opus 5.5 | `SIN-BASH`: el subagente declaró solo `Read` y `Grep` y no hubo ninguna llamada a Bash. Manda `tools` del agente | Determinista (no hay llamada en el registro); la lista de tools la declara el modelo |
| P4b | 2026-11-11 | 2.1.322 | Opus 5.5 | `MARCA-P4`: la llamada a Bash se ejecutó sin denegación. El permiso llega al fork | Determinista |
| P4c | 2026-11-11 | 2.1.322 | Opus 5.5 | `DENEGADO`: la misma llamada figura en las denegaciones de permiso. El control funciona | Determinista |
| P5 | 2026-11-11 | 2.1.322 | Opus 5.5 | Conviven. Solo plugin: la lista trae únicamente `zz-prec-plugin:zz-prec-p5`. Con los dos: `zz-prec-p5` (devolvió `ORIGEN=proyecto-agente`) y `zz-prec-plugin:zz-prec-p5` (`ORIGEN=plugin-agente`) | Determinista (listas); el origen lo confirma |
| P6 | | | | | |

**Cómo se ejecutaron P3, P4 y P5.** Con `claude -p --model claude-opus-5-5 --setting-sources project --output-format stream-json --verbose --max-budget-usd 0.50 --max-turns 6`, una ejecución por caso; coste total aproximado, 0,52 USD. Diferencias con lo planificado:

- Los pasos de menú (`/agents`, `/skills`, `/doctor`, autocompletado) se sustituyeron por las listas `agents` y `skills` del mensaje inicial del registro. `/doctor` y el autocompletado quedan sin hacer.
- En P4, el comando fue `python -c "print(open('datos.txt').read())"` con `allowed-tools: Bash(python *)`, en lugar de `cat`, para que el control P4c no dependiera de si un comando de solo lectura necesita permiso.
- En P5, la variante sin agente de proyecto se ejecutó primero, para no tener que borrarlo.
- Desde Git Bash en Windows hace falta `MSYS_NO_PATHCONV=1`: sin ella, el prompt `/zz-prec-p3` llega convertido en una ruta.

Al cerrar una prueba:

- El resultado pasa como hecho a la tabla correspondiente de `docs/precedencia-y-nombres.md`, con la referencia «prueba Pn, fecha, versión» en lugar de una clave de documentación, y su fila sale de la sección 8 de ese documento.
- Se añade una línea con fecha y versión a `docs/hallazgos.md`, marcada `→ roadmap` si le serviría a otra persona.
- Un resultado de P6 que compare modelos va solo a `docs/hallazgos.md`.

## 4. Limpieza

- Borrar `~/.claude/commands/zz-prec-*.md` y `~/.claude/skills/zz-prec-*/`.
- Si `~/.claude/commands/` no existía antes de P1, borrarlo también (anotarlo antes de empezar).
- Borrar `<lab>` y `zz-prec-plugin`.
- Rastro que deja Claude Code por abrir sesiones en `<lab>`, inocuo pero fuera del laboratorio: la entrada de `<lab>` en `projects` de `~/.claude.json` (confianza del directorio) y su carpeta de sesiones en `~/.claude/projects/`. Se pueden borrar.
- Durante las pruebas no aceptar ningún permiso con «no volver a preguntar» ni cambiar estados en el menú `/skills`: ambas acciones escriben `<lab>/.claude/settings.local.json`, y la primera vez que Claude Code escribe ese archivo añade `**/.claude/settings.local.json` al archivo global de exclusiones de git. Si ocurre, esa línea es lo único que quedaría fuera de `<lab>` y de `~/.claude/`; revisar el archivo global de exclusiones (`core.excludesFile` o `~/.config/git/ignore`).
- Comprobar con `/skills` y `/agents`, en una sesión nueva de este repositorio, que no queda ninguna entrada `zz-prec-`.
