# Precedencia y superposición de nombres

Referencia de producto, no un estándar. Resume qué definición gana cuando dos comparten nombre y cómo se combinan las fuentes que se acumulan. El hallazgo que la enlaza está en `docs/hallazgos.md` (sección «Precedencia y superposición de nombres»).

**Alcance de la verificación (2026-11-11, Claude Code 2.1.322).** Cada afirmación lleva la clave de su fuente entre corchetes; las claves se resuelven en la sección 7. Lo de examen se contrastó con la Exam Guide v1.0 y lo de producto, con la documentación oficial de Claude Code leída ese día. Lo que la documentación no resuelve se comprueba con las pruebas de `docs/plan-pruebas-precedencia.md`, que se ejecutan en un directorio desechable fuera de este repositorio: las ya ejecutadas figuran aquí con la clave [P-n] y las pendientes, en la sección 8. Este documento no cambia ninguna respuesta de examen.

## 1. Qué es examen y qué no

**Examen (guía v1.0).** La guía nombra:

- Los tres niveles de CLAUDE.md: usuario (`~/.claude/CLAUDE.md`, que no se comparte por control de versiones), proyecto (`.claude/CLAUDE.md` o el de la raíz) y directorio (subdirectorios). Además `@import` y `.claude/rules/` [G-3.1]. Las reglas admiten `paths` con patrones glob en el frontmatter [G-3.3].
- Commands de proyecto (`.claude/commands/`, compartidos por control de versiones) frente a personales (`~/.claude/commands/`) [G-3.2].
- Skills en `.claude/skills/` con `context: fork`, `allowed-tools` y `argument-hint`. Las variantes personales viven en `~/.claude/skills/` **con otro nombre**, para no afectar al equipo [G-3.2].
- Hooks como garantía determinista frente a instrucciones de prompt, de cumplimiento probabilístico [G-1.5].

**Producto observado (no evaluable).** La guía no nombra el orden de prioridad por nombre, `settings.local.json`, `CLAUDE.local.md`, `claudeMdExcludes`, `skillOverrides` ni el anidamiento de subagentes. Todo lo que sigue desde la sección 2 entra aquí.

La recomendación de la guía de dar otro nombre a la variante personal es justo lo que evita el choque de nombres; el orden de prioridad es lo que ocurre si no se sigue.

## 2. Dos preguntas distintas

| Pregunta | Mecanismos |
|---|---|
| **A. Sustitución:** dos definiciones con el mismo nombre, ¿cuál se usa? | Agentes, skills, commands |
| **B. Acumulación:** varias fuentes dicen cosas distintas, ¿cómo se combinan? | CLAUDE.md, hooks, permisos, settings (listas) |

La sustitución elige un ganador. La acumulación carga todo y los conflictos los resuelve otra regla.

## 3. Superposición de nombres

### 3.1 Mismo tipo, distinto nivel (sustitución)

| Nivel | Agentes [D-AG-1] | Skills [D-SK-1] |
|---|---|---|
| Gestionado / enterprise | 1.º | 1.º |
| Flag `--agents` de la CLI | 2.º | no aplica |
| Proyecto (`.claude/…`) | 3.º | 3.º |
| Usuario (`~/.claude/…`) | 4.º | 2.º |
| Plugin | 5.º | no compite: se carga como `/plugin:skill` |

**Trampa:** la fila de proyecto y usuario se invierte. En agentes gana el proyecto; en skills gana la personal.

Detalles del mismo tipo:

- **Commands de usuario y de proyecto con el mismo nombre:** se ejecuta el de usuario, como en las skills. El menú `/` y `/skills` listan los dos, sin marcar cuál se ejecuta [P-1].
- **Agentes en directorios de proyecto anidados:** se recorren todos los `.claude/agents/` desde el directorio de trabajo hasta la raíz del repositorio y gana la definición más cercana al directorio de trabajo [D-AG-1].
- **Dos agentes con el mismo `name` en un mismo `.claude/agents/`** (incluidas sus subcarpetas): se carga solo uno, elegido por orden de lectura del sistema de archivos, sin precedencia documentada. `/doctor` lo avisa [D-AG-1].
- **Agentes de plugin:** además de ocupar el último lugar de la tabla, se registran con nombre calificado (`plugin:agente`) [D-AG-1][D-PL-1]. Si dos plugins traen un agente con el mismo nombre, se desambigua con el nombre calificado [D-AG-2]. Cuando el nombre corto coincide con el de un agente de proyecto, conviven: el de proyecto responde al nombre corto y el de plugin, solo a `plugin:agente`. El agente de plugin se registra únicamente con el nombre calificado, también cuando no hay ningún otro con ese nombre corto [P-5].
- **Skill de proyecto anidada con el mismo nombre que una de la raíz:** se cargan las dos; `/nombre` ejecuta la de la raíz y la anidada queda como `/<subdir>:nombre` [D-SK-2].
- **Skill en un directorio añadido con `--add-dir`:** gana la enterprise, personal o de proyecto, y la del directorio añadido se ejecuta con prefijo [D-SK-1].

### 3.2 Distinto tipo, mismo nombre

| Choque | Resultado | Fuente |
|---|---|---|
| Skill y archivo en `.claude/commands/` (`commands/deploy.md` y `skills/deploy/SKILL.md`) | Gana la skill | [D-SK-1] |
| Skill y archivo en `.claude/commands/`, en niveles distintos | Gana la skill en los dos sentidos, también la de proyecto sobre un command de usuario: manda el tipo sobre el nivel | [P-2] |
| Skill de plugin y skill de cualquier otro nivel | Se cargan las dos; la de plugin es `/plugin:skill` | [D-SK-1] |
| Skill propia y skill incluida (*bundled*) | La propia sustituye al comando incluido, pero no a sus alias | [D-SK-1] |
| Skill propia y comando integrado (*built-in*) | En una sesión de terminal local, la propia sustituye al integrado, pero no a sus alias | [D-SK-1] |
| Cualquiera de las anteriores y el nombre corto de una skill sincronizada de claude.ai | Gana la otra; la sincronizada queda solo con su nombre completo | [D-SK-1] |
| Agente y skill | Conviven: `/nombre` ejecuta la skill y la mención `@nombre` lanza el agente | [P-3] |
| Agente y archivo en `.claude/commands/` | Conviven: `/nombre` ejecuta el command y la mención `@nombre` lanza el agente | [P-3] |

### 3.3 Acumulación

| Mecanismo | Cómo se combina | En un conflicto | Fuente |
|---|---|---|---|
| CLAUDE.md | Se concatena; no se sobrescribe | No hay ganador documentado: lo más cercano al directorio de arranque se lee al final, y si dos instrucciones se contradicen el modelo puede elegir una arbitrariamente | [D-ME-2][D-ME-3] |
| Reglas (`.claude/rules/`) | Las de usuario se cargan antes que las de proyecto | Ninguna anula a la otra: el modelo puede seguir cualquiera | [D-ME-4] |
| Hooks | Las entradas se fusionan entre niveles de settings y con las de los plugins activos; los que coinciden con un evento corren en paralelo | En `PreToolUse`: `deny` > `defer` > `ask` > `allow`. Un `allow` de hook no salta las reglas `deny` ni `ask` de permisos | [D-HK-1][D-HK-2][D-HK-3][D-PE-2] |
| Permisos | Las listas se fusionan entre archivos | `deny`, luego `ask`, luego `allow`. Un `deny` de cualquier nivel no lo levanta un `allow` de otro | [D-ST-2][D-PE-1][D-PE-3] |
| Settings escalares | Se sobrescriben | Vale el valor del nivel más alto que define la clave | [D-ST-1] |

## 4. Orden de niveles por mecanismo

| Mecanismo | De mayor a menor | Fuente |
|---|---|---|
| Settings | gestionado > línea de comandos (`--settings`) > local > proyecto > usuario | [D-ST-1] |
| CLAUDE.md (orden de carga, no prioridad) | gestionado, usuario, proyecto, local (`CLAUDE.local.md`). Los del directorio de trabajo y sus padres se cargan al arrancar, ordenados de la raíz del sistema de archivos hacia el directorio de trabajo; en cada directorio, `CLAUDE.local.md` va después de `CLAUDE.md`. Los de subdirectorios se cargan cuando Claude lee, escribe o edita un archivo de ese subdirectorio | [D-ME-1][D-ME-2] |
| Agentes | gestionado > `--agents` > proyecto > usuario > plugin | [D-AG-1] |
| Skills | enterprise > personal > proyecto; plugin con prefijo | [D-SK-1] |

### `settings.local.json`

- Está por encima de los settings de proyecto y de usuario, y por debajo de `--settings` y de los gestionados [D-ST-1].
- No se versiona, pero Claude Code solo lo añade a los *global git excludes* la primera vez que él mismo escribe el archivo. Si se crea a mano (como hace este proyecto copiando el `.example`), hay que ignorarlo a mano [D-ST-3].
- `CLAUDE.local.md` hay que añadirlo a `.gitignore` a mano. La única excepción documentada es `/init` con `CLAUDE_CODE_NEW_INIT=1` y la opción personal, que lo hace por ti [D-ME-5].
- `claudeMdExcludes` y `skillOverrides` son claves de settings y pueden ir en este archivo [D-ME-6][D-SK-6]. Es lo que usa este proyecto para aislarse del contexto heredado (ver `CLAUDE.md`).

## 5. Criterios comunes y diferencias

**Similitudes**

- Agentes y skills sustituyen por nombre, con el nivel gestionado primero y el plugin al final o aparte [D-AG-1][D-SK-1].
- CLAUDE.md, hooks y permisos acumulan [D-ME-2][D-HK-1][D-ST-2].
- `deny` prevalece sobre `allow` tanto entre reglas de permisos de distinto nivel como entre decisiones de hooks `PreToolUse` [D-PE-3][D-HK-3].

**Diferencias**

- La dirección proyecto/usuario no es uniforme (ver 3.1).
- Los plugins se tratan de dos formas: en agentes figuran en último lugar; en skills no compiten [D-AG-1][D-SK-1].
- Un subagente trabaja en su propia ventana de contexto [D-AG-5]. El contenido de una skill entra en la conversación y permanece en ella [D-SK-7], salvo con `context: fork` [D-SK-4].
- CLAUDE.md es contexto que el modelo intenta seguir, sin garantía de cumplimiento estricto; para bloquear una acción con independencia de lo que decida el modelo está el hook `PreToolUse` [D-ME-7]. Coincide con la distinción de examen [G-1.5].

## 6. Detalles de subagentes y skills

- `context: fork` arranca un subagente del tipo indicado en `agent` (por defecto, `general-purpose`), que recibe el contenido de la skill como prompt y no ve el historial de la conversación. No es un fork de la conversación actual. El campo `agent` determina el entorno de ejecución: modelo, tools y permisos [D-SK-4].
- El campo `skills:` del frontmatter de un agente **precarga** el contenido completo de esas skills. No limita el acceso: sin él, el subagente puede descubrir e invocar skills de proyecto, usuario y plugin con la tool `Skill`. Para impedírselo, se quita `Skill` de su `tools` o se pone en `disallowedTools` [D-AG-3].
- Un subagente que no es fork empieza con un contexto nuevo: no ve el historial, las skills ya invocadas ni los archivos ya leídos [D-AG-5].
- Un subagente **puede lanzar otros**, por defecto hasta tres capas por debajo de la conversación principal. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` cambia el límite y con el valor `1` desactiva el anidamiento. En un subagente concreto, se impide quitando `Agent` de su `tools` o poniéndolo en `disallowedTools` [D-AG-4].
- `allowed-tools` de una skill **concede permiso** sin preguntar durante el turno que invoca la skill y se retira con el siguiente mensaje. No restringe qué tools hay disponibles, y las reglas `deny` y `ask` siguen por encima. Para retirar tools mientras la skill está activa existe `disallowed-tools` [D-SK-5].
- En una skill con `context: fork`, `allowed-tools` no añade tools al subagente: si `tools` del agente no incluye Bash, el subagente no la tiene aunque la skill la liste. Sobre una tool que el agente sí tiene, el permiso de `allowed-tools` llega al subagente: la misma llamada se ejecuta con `allowed-tools` y se deniega sin él [P-4].
- `claudeMdExcludes`: patrones glob contra rutas absolutas; se puede configurar en cualquier nivel de settings y los arrays se fusionan entre niveles; no puede excluir el CLAUDE.md gestionado [D-ME-6].
- `skillOverrides`: `on`, `name-only`, `user-invocable-only` y `off`; no afecta a las skills de plugin [D-SK-6].

**Discrepancia con la guía.** La guía presenta `allowed-tools` como una forma de restringir el acceso a tools durante la ejecución de la skill [G-3.2]. Esa es la respuesta de examen y manda en el examen. La documentación actual lo describe como concesión de permiso [D-SK-5]. Es producto observado y no cambia la respuesta tipo examen.

## 7. Fuentes

Consultadas el 2026-11-11. La documentación de producto no está versionada por página; la versión instalada al consultarla era Claude Code 2.1.322.

**Exam Guide v1.0** (`fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio `claude-cert-ccar-f`):

| Clave | Lugar en la guía |
|---|---|
| G-1.5 | Task Statement 1.5, *Knowledge of* (hooks deterministas frente a instrucciones de prompt) |
| G-3.1 | Task Statement 3.1, *Knowledge of* (jerarquía de CLAUDE.md, `@import`, `.claude/rules/`) |
| G-3.2 | Task Statement 3.2, *Knowledge of* y *Skills in* (commands, skills, `context: fork`, `allowed-tools`, `argument-hint`, variantes personales) |
| G-3.3 | Task Statement 3.3, *Knowledge of* (`paths` con patrones glob) |

**Documentación oficial de Claude Code** (`https://code.claude.com/docs/en/<página>`):

| Clave | Página | Sección |
|---|---|---|
| D-AG-1 | `sub-agents` | *Choose the subagent scope* |
| D-AG-2 | `sub-agents` | *Invoke subagents explicitly* |
| D-AG-3 | `sub-agents` | *Preload skills into subagents* y tabla de campos del frontmatter (`skills`) |
| D-AG-4 | `sub-agents` | *Let subagents spawn their own subagents* |
| D-AG-5 | `sub-agents` | Introducción y *What loads at startup* |
| D-SK-1 | `skills` | *Resolve skills that share a name* |
| D-SK-2 | `skills` | *Load skills in monorepos and subdirectories* |
| D-SK-3 | `skills` | Nota inicial sobre la fusión de los commands en las skills y *Choose where skills load* |
| D-SK-4 | `skills` | *Run skills in a subagent* |
| D-SK-5 | `skills` | *Pre-approve tools for a skill* y tabla de frontmatter (`allowed-tools`, `disallowed-tools`) |
| D-SK-6 | `skills` | *Override skill visibility from settings* |
| D-SK-7 | `skills` | *Skill content lifecycle* |
| D-ST-1 | `settings` | *Settings precedence* |
| D-ST-2 | `settings` | *Lists merge instead of overriding* |
| D-ST-3 | `settings` | *Where settings live* y *Keep personal settings out of a repository* |
| D-ME-1 | `memory` | *Choose where to put CLAUDE.md files* |
| D-ME-2 | `memory` | *How CLAUDE.md files load* |
| D-ME-3 | `memory` | *Write effective instructions* (punto *Consistency*) y *Troubleshoot memory issues* |
| D-ME-4 | `memory` | *User-level rules* |
| D-ME-5 | `memory` | Tabla de ubicaciones (`CLAUDE.local.md`) y párrafo sobre `CLAUDE.local.md` |
| D-ME-6 | `memory` | *Exclude specific CLAUDE.md files* |
| D-ME-7 | `memory` | Introducción y *Claude isn't following my CLAUDE.md* |
| D-HK-1 | `hooks` | *Hook locations* (fusión entre niveles) y *Reference scripts by path* (hooks de plugin) |
| D-HK-2 | `hooks` | *Hook handler fields* (los hooks que coinciden con un evento corren en paralelo) |
| D-HK-3 | `hooks` | *PreToolUse*, control de decisión |
| D-PE-1 | `permissions` | *Manage permissions* (orden de evaluación de las reglas) |
| D-PE-2 | `permissions` | *Precedence among rules, hooks, and mods* |
| D-PE-3 | `permissions` | *Settings precedence* |
| D-PL-1 | `plugins-reference` | Campo `name` del manifiesto (espacio de nombres de los componentes) |

**Pruebas propias** (`docs/plan-pruebas-precedencia.md`), ejecutadas el 2026-11-11 con Claude Code 2.1.322; modelo de la medida: Opus 5.5. P-1 y P-2, en sesión interactiva; P-3 a P-5, con `claude -p`. Una ejecución por caso:

| Clave | Prueba | Señal |
|---|---|---|
| P-1 | P1 | Origen devuelto por `/nombre`; entradas del menú `/` y de `/skills` |
| P-2 | P2a y P2b | Origen devuelto por `/nombre`; orden del menú `/` |
| P-3 | P3a y P3b | Listas de agentes y skills del mensaje inicial de la sesión, y origen devuelto por cada vía |
| P-4 | P4a, P4b y P4c | Llamadas a tools del subagente y denegaciones de permiso del registro |
| P-5 | P5 | Lista de agentes del mensaje inicial, con y sin el agente de proyecto |

## 8. Sin respaldo en la documentación

La documentación consultada no resuelve este punto, así que no figura arriba como hecho. Su prueba está en `docs/plan-pruebas-precedencia.md`.

| Punto | Prueba |
|---|---|
| Si, ante una contradicción, el modelo sigue de hecho el CLAUDE.md más cercano | P6 |
