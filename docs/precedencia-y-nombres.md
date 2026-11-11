# Precedencia y superposición de nombres

Referencia de producto, no un estándar. Resume qué definición gana cuando dos comparten nombre y cómo se combinan las fuentes que se acumulan. El hallazgo que la enlaza está en `docs/hallazgos.md` (sección «Precedencia y superposición de nombres»).

**Estado de las comprobaciones (2026-11-11, Claude Code 2.1.322).** Todo lo de «Producto observado» sale de la lectura de la documentación oficial de Claude Code, no de una ejecución en este repositorio. Lo que la documentación no dice va marcado **no documentado** y lo que es razonamiento propio, **inferencia propia**. Este documento no cambia ninguna respuesta de examen.

## 1. Qué es examen y qué no

**Examen (guía v1.0).** La guía nombra:

- Los tres niveles de CLAUDE.md: usuario (`~/.claude/CLAUDE.md`, no se comparte por git), proyecto (`.claude/CLAUDE.md` o la raíz) y directorio (subdirectorios). Además `@import` y `.claude/rules/` con rutas glob.
- Commands de proyecto (`.claude/commands/`, compartidos por git) frente a personales (`~/.claude/commands/`).
- Skills en `.claude/skills/` con `context: fork`, `allowed-tools` y `argument-hint`. Las variantes personales viven en `~/.claude/skills/` **con otro nombre**, para no afectar al equipo.
- Hooks como garantía determinista frente a instrucciones probabilísticas.

**Producto observado (no evaluable).** La guía no nombra el orden de prioridad por nombre, `settings.local.json`, `CLAUDE.local.md`, `claudeMdExcludes`, `skillOverrides` ni el anidamiento de subagentes. Todo lo que sigue entra aquí.

La recomendación de la guía de dar otro nombre a la variante personal es justo lo que evita el choque de nombres; el orden de prioridad es lo que ocurre si no se sigue.

## 2. Dos preguntas distintas

| Pregunta | Mecanismos |
|---|---|
| **A. Sustitución:** dos definiciones con el mismo nombre, ¿cuál se usa? | Agentes, skills, commands |
| **B. Acumulación:** varias fuentes dicen cosas distintas, ¿cómo se combinan? | CLAUDE.md, hooks, permisos, settings (listas) |

La sustitución elige un ganador y oculta las demás definiciones. La acumulación carga todo y los conflictos los resuelve otra regla.

## 3. Superposición de nombres

### 3.1 Mismo tipo, distinto nivel (sustitución)

| Nivel | Agentes | Skills | Commands |
|---|---|---|---|
| Gestionado / enterprise | 1.º | 1.º | no documentado |
| Flag `--agents` de la CLI | 2.º | no aplica | no aplica |
| Proyecto (`.claude/…`) | 3.º | 3.º | no documentado |
| Usuario (`~/.claude/…`) | 4.º | 2.º | no documentado |
| Plugin | 5.º | no compite (`/plugin:skill`) | no documentado |

**Trampa:** la fila de proyecto y usuario se invierte. En agentes gana el proyecto; en skills gana el personal.

Commands de proyecto frente a usuario con el mismo nombre: **no documentado**. La documentación consultada no menciona `~/.claude/commands/`. Probarlo antes de depender de ello.

### 3.2 Distinto tipo, mismo nombre

| Choque | Resultado | Estado |
|---|---|---|
| Skill y command (`.claude/commands/deploy.md` y `skills/deploy/SKILL.md`) | Gana la skill | Documentado |
| Skill de plugin y skill propia | Conviven con prefijo `plugin:nombre` | Documentado |
| Agente y skill | Sin dato | No documentado |
| Agente y command | Sin dato | No documentado |

**Inferencia propia:** los agentes se invocan por otra vía que `/nombre`, así que probablemente no choquen con skills ni commands. Sin respaldo literal.

### 3.3 Acumulación

| Mecanismo | Cómo se combina | En un conflicto |
|---|---|---|
| CLAUDE.md | Se concatena | Nadie gana: lo más cercano se lee al final, pero ante contradicción el modelo puede elegir una arbitrariamente. La especificidad no es una prioridad documentada |
| Hooks | Se fusionan y corren en paralelo | `deny` > `defer` > `ask` > `allow`. Un `allow` de hook no salta las reglas `deny` y `ask` de permisos |
| Permisos | Las listas se fusionan entre niveles | `deny` > `ask` > `allow`, sea cual sea el origen |
| Settings escalares | Se sobrescriben | El nivel más alto |

## 4. Orden de niveles por mecanismo

| Mecanismo | De mayor a menor |
|---|---|
| Settings | gestionado > CLI (`--settings`) > local > proyecto > usuario |
| CLAUDE.md (carga) | gestionado, usuario, proyecto, local (`CLAUDE.local.md`); los de directorios padre se cargan al arrancar y los de subdirectorios bajo demanda |
| Agentes | gestionado > `--agents` > proyecto > usuario > plugin |
| Skills | enterprise > personal > proyecto; plugin con prefijo |

### `settings.local.json`

- Es el nivel más alto entre los archivos de settings.
- Solo gobierna settings: permisos, hooks, `env`, `enabledPlugins`, `claudeMdExcludes`, `skillOverrides`. No contiene definiciones de agentes, skills ni commands.
- No se versiona, pero **Claude Code solo lo añade a los *global git excludes* cuando él mismo crea el archivo**. Si se crea a mano (como hace este proyecto copiando el `.example`), hay que ignorarlo a mano. Lo mismo vale para `CLAUDE.local.md`, que no se añade a `.gitignore` por sí solo.
- Su efecto sobre `claudeMdExcludes` y `skillOverrides` es lo que usa este proyecto para aislarse del contexto heredado (ver `CLAUDE.md`).

## 5. Criterios comunes y diferencias

**Similitudes**

- Agentes, skills y commands sustituyen por nombre y gana la fuente más central: gestionado primero, plugin al final o aislado.
- CLAUDE.md, hooks y permisos acumulan.
- `deny` prevalece sobre `allow` en cualquier contexto: es el criterio más coherente del conjunto.

**Diferencias**

- La dirección proyecto/usuario no es uniforme (ver 3.1).
- Los plugins se tratan de dos formas: en agentes compiten en último lugar; en skills no compiten.
- Solo los agentes aíslan contexto. Las skills lo comparten, salvo con `context: fork`.
- Los mecanismos probabilísticos (CLAUDE.md, skills, agentes) orientan al modelo. Los hooks lo garantizan. Es la distinción de examen.

## 6. Detalles de subagentes y skills

- `context: fork` ejecuta la skill en un subagente del tipo indicado en `agent`, que recibe el contenido de la skill como prompt. No es un fork de la conversación actual.
- El campo `skills:` del frontmatter de un agente **precarga** el contenido completo de esas skills. No limita el acceso: sin él, el subagente puede descubrir e invocar skills de proyecto, usuario y plugin con la tool `Skill`. Un subagente que no es fork no ve el historial ni lo ya invocado por el padre.
- Un subagente **sí puede lanzar otros**, hasta tres niveles por debajo de la conversación principal. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` lo desactiva. En un subagente concreto, se impide quitando `Agent` de su `tools` o poniéndolo en `disallowedTools`.
- `allowed-tools` de una skill **concede permiso** sin preguntar durante el turno de la skill; la documentación dice que no restringe qué tools hay disponibles. `tools` en un agente es una lista blanca que sí restringe.
- `claudeMdExcludes`: patrones glob contra rutas absolutas, con arrays que se fusionan entre niveles; no puede excluir el CLAUDE.md gestionado. `skillOverrides`: `on`, `name-only`, `user-invocable-only` y `off`; no afecta a skills de plugin.

**Discrepancia con la guía.** La guía presenta `allowed-tools` como una restricción de acceso («limiting to file write operations to prevent destructive actions»). Esa es la respuesta de examen y manda en el examen. La documentación actual lo describe como concesión de permiso. Es producto observado y no cambia la respuesta tipo examen.

## 7. Pendiente de comprobar

1. Commands de usuario frente a proyecto con el mismo nombre.
2. Agente y skill con el mismo nombre, y agente y command.
3. Cómo interactúan `allowed-tools` (skill) y `tools` (agente) en una skill con `context: fork`.
4. Si ante una contradicción gana de hecho el CLAUDE.md más cercano.

Se pueden comprobar sin modelo con `/skills`, `/agents` y `/memory` (señal determinista). El primer punto exige crear a propósito dos commands con el mismo nombre y mirar cuál lista el menú.

## 8. Correcciones respecto a las primeras versiones de este análisis

Se dejan registradas porque son errores fáciles de repetir.

| Se afirmó | Resultado de la comprobación |
|---|---|
| Un subagente no puede lanzar otros | Falso: puede, hasta tres niveles |
| Los subagentes no heredan skills | Matiz: `skills:` controla la precarga, no el acceso |
| `allowed-tools` restringe tools | No: concede permiso; la lista blanca es `tools` del agente |
| Lo más específico de CLAUDE.md pesa más | No documentado |
| Commands: proyecto > usuario | No documentado |
| `settings.local.json` se añade a `.gitignore` | Solo a los *global git excludes*, y solo si lo crea Claude Code |
