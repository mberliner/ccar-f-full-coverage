# D3 · Claude Code: configuración y flujos de trabajo

El dominio 3 trata de cómo se configura y se usa Claude Code, así que no tiene módulos ejecutables: el material es **la propia configuración de este repositorio**. Este README tiene cuatro partes:

1. **Ruta por los archivos reales:** las 27 viñetas que ya viven en un archivo de configuración.
2. **Guion de lo que no cabe en un archivo:** las 13 viñetas que se introducen aquí y dos comparaciones que el examen suele plantear.
3. **Práctica propia:** la haces tú, en tu sesión.
4. **Tres preguntas tipo examen.**

La TS 3.6 (CI/CD) no está en esta sección: llega con la entrega 3 (ver `CONCEPTOS.md`).

En todo el README, «la guía» es la Exam Guide v1.0. Lo que hace el producto actual y la guía no dice va marcado como **EN PRODUCCIÓN (no evaluable)**. En el examen manda la guía.

---

## 1 · Ruta por los archivos reales

<!-- USA: TS 3.1-K1, TS 3.1-K2, TS 3.1-K3, TS 3.1-K4, TS 3.1-S2, TS 3.1-S3, TS 3.2-K1, TS 3.2-K2, TS 3.2-K3, TS 3.2-S1, TS 3.2-S2, TS 3.2-S3, TS 3.2-S4, TS 3.3-K1, TS 3.3-K2, TS 3.3-K3, TS 3.3-S1, TS 3.3-S2, TS 3.3-S3, TS 3.4-K1, TS 3.4-K2, TS 3.4-K3, TS 3.4-K4, TS 3.4-S1, TS 3.4-S2, TS 3.4-S3, TS 3.4-S4 -->

Cada fila es una viñeta con su marcador `INTRODUCE` en el archivo indicado. Abre el archivo: el comentario de cabecera explica la viñeta y el resto del archivo es el ejemplo. La tabla sale de cruzar las filas `d3` de `CONCEPTOS.md` con los marcadores del repositorio; para comprobar que sigue alineada:

```bash
grep -rn "INTRODUCE" CLAUDE.md .claude docs d3_claude_code | grep "TS 3\."
uv run pytest -q tests/test_una_vez.py
```

| Viñeta | Archivo con el marcador | Qué mirar |
| :--- | :--- | :--- |
| TS 3.1-K1 | `CLAUDE.md` | Los tres niveles: el `CLAUDE.md` raíz es el de proyecto; cada `app*/CLAUDE.md` es de directorio y solo dice lo propio de esa app; el de usuario no se usa |
| TS 3.1-K2 | `CLAUDE.md` | «Nada del proyecto va en `~/.claude/CLAUDE.md`»: lo que se pone ahí no viaja por git |
| TS 3.1-K3 | `CLAUDE.md` | Las dos líneas `@docs/…` del final, que traen los estándares de código y de flujo |
| TS 3.1-S2 | `CLAUDE.md` | El `@import` es selectivo: solo los dos estándares comunes; lo de cada tipo de archivo no se importa, va en reglas |
| TS 3.1-K4 | `.claude/rules/apps-comentarios.md` | Una regla por tema en `.claude/rules/` en vez de un `CLAUDE.md` que lo acumule todo |
| TS 3.1-S3 | `.claude/rules/apps-comentarios.md` | Las convenciones de los módulos de app, sacadas del `CLAUDE.md` raíz a un archivo propio |
| TS 3.2-K1 | `.claude/commands/nuevo-modulo.md` | Comando de proyecto, versionado; uno en `~/.claude/commands/` solo lo tendría su autor |
| TS 3.2-S1 | `.claude/commands/nuevo-modulo.md` | El flujo de crear un módulo (tests primero, cabecera, `CONCEPTOS.md`) como comando del equipo |
| TS 3.2-K2 | `.claude/skills/verificar-concepto/SKILL.md` | El frontmatter: `context: fork`, `allowed-tools` y `argument-hint` |
| TS 3.2-K3 | `.claude/skills/verificar-concepto/SKILL.md` | `context: fork`: la skill corre en un subagente y a la conversación solo vuelve el informe |
| TS 3.2-S2 | `.claude/skills/verificar-concepto/SKILL.md` | Por qué fork aquí: recorrer el repositorio genera mucha salida que no debe quedarse en tu contexto |
| TS 3.2-S3 | `.claude/skills/verificar-concepto/SKILL.md` | `allowed-tools: Read, Grep, Glob`: una verificación no escribe |
| TS 3.2-S4 | `.claude/skills/verificar-concepto/SKILL.md` | `argument-hint: "<TS x.y-Kn\|Sn>"` y, en el cuerpo, la comprobación de `$ARGUMENTS` (ver nota de producto abajo) |
| TS 3.3-K1 | `.claude/rules/apps-comentarios.md` | El frontmatter YAML `paths: ["app*/**/*.py"]` |
| TS 3.3-K2 | `.claude/rules/apps-comentarios.md` | Solo entra en contexto al trabajar con un `.py` de una app; editando un README no se carga |
| TS 3.3-S1 | `.claude/rules/apps-comentarios.md` | Cómo se escribe una regla condicional: frontmatter con globs y, debajo, las convenciones |
| TS 3.3-K3 | `.claude/rules/tests.md` | Un glob por tipo de archivo frente a un `CLAUDE.md` en cada carpeta con tests |
| TS 3.3-S2 | `.claude/rules/tests.md` | `paths: ["**/test_*.py"]`: vale para `tests/` y para cualquier test futuro, esté donde esté |
| TS 3.3-S3 | `.claude/rules/tests.md` | La elección razonada: los tests están dispersos, así que regla por ruta y no `CLAUDE.md` por subdirectorio |
| TS 3.4-K1 | `docs/estandares-flujo.md` | «Plan mode»: diseñar cada app y los cambios multi-archivo o con varios enfoques |
| TS 3.4-K2 | `docs/estandares-flujo.md` | «Ejecución directa»: un módulo ya diseñado o un arreglo con causa clara |
| TS 3.4-K3 | `docs/estandares-flujo.md` | Plan mode como fase de exploración y diseño antes de tocar archivos |
| TS 3.4-K4 | `docs/estandares-flujo.md` | El subagente `Explore` para el descubrimiento verboso |
| TS 3.4-S1 | `docs/estandares-flujo.md` | Cuándo elegir plan mode: un cambio en el arnés o en la capa meta que afecte a todos los módulos |
| TS 3.4-S2 | `docs/estandares-flujo.md` | Cuándo elegir ejecución directa: «un test que falla con su traza» |
| TS 3.4-S3 | `docs/estandares-flujo.md` | `Explore` para recorrer la guía o buscar una viñeta en todo el repositorio, devolviendo un resumen |
| TS 3.4-S4 | `docs/estandares-flujo.md` | «Combinación habitual»: plan mode para investigar y diseñar, ejecución directa para implementar |

Los `app*/CLAUDE.md` llevan un `USA` de TS 3.1-K1 y TS 3.1-K3: son el ejemplo vivo del nivel de directorio.

---

## 2 · Guion de lo que no cabe en un archivo

Las 13 viñetas de esta parte describen diagnósticos, decisiones o formas de trabajar. No hay un archivo que las «contenga», así que se introducen aquí, cada una con un caso de este proyecto.

### 2.1 Diagnosticar la jerarquía de `CLAUDE.md`

<!-- INTRODUCE: TS 3.1-S1 -->

**Qué dice la guía (TS 3.1-S1):** un fallo típico de jerarquía es que una persona nueva no recibe unas instrucciones porque estaban en el nivel de usuario y no en el de proyecto. Diagnosticarlo es preguntarse en qué nivel vive la instrucción y quién lo carga.

**Caso de este proyecto:** si una regla del proyecto se escribe en `~/.claude/CLAUDE.md`, la sesión que la escribió la cumple y parece que funciona. Pero no llega a nadie más, y tampoco a **tu propia sesión** abierta con otro directorio de configuración (`CLAUDE_CONFIG_DIR`, por ejemplo una cuenta personal y otra de empresa): para Claude Code son dos «usuarios» distintos. Por eso `docs/estandares-flujo.md` (sección «Directivas») prohíbe guardar directivas del proyecto en la memoria automática o en la configuración de usuario. El síntoma («a mí me funciona y a ti no») es el mismo que el del compañero nuevo de la guía.

Lo inverso también ocurre: los `CLAUDE.md` de directorios **padre** del clon se cargan aunque no sean del proyecto. Aquí se excluyen con `claudeMdExcludes` (ver `CLAUDE.md`, «Contexto heredado»), porque contaminarían las pruebas.

**Por qué importa (inferencia propia):** un fallo de jerarquía no da error: la instrucción simplemente no llega, y quien lo sufre ve un asistente que «no cumple» sin ninguna pista. Preguntarse en qué nivel vive la instrucción y quién lo carga evita buscar el fallo en su redacción, que es la dirección equivocada.

**Anti-patrón / trampa del examen:** el diagnóstico equivocado es reescribir la instrucción, o pedir a la persona afectada que copie el `~/.claude/CLAUDE.md` de otra: el problema es de nivel y no de texto, y la copia sigue sin viajar por git. La corrección coherente con la guía (TS 3.1-K2: lo de usuario no se comparte por control de versiones) es subir la instrucción al nivel de proyecto. En un examen, la opción que arregla el síntoma sin cambiar el nivel es la trampa.

### 2.2 Comprobar qué memoria está cargada: `/memory`

<!-- INTRODUCE: TS 3.1-S4 -->

**Qué dice la guía (TS 3.1-S4):** `/memory` es el comando para ver qué archivos de memoria están cargados y diagnosticar por qué dos sesiones se comportan distinto.

**Caso de este proyecto:** es la primera comprobación de §11.5 del roadmap y la de «Contexto heredado» de `CLAUDE.md`: en `/memory` deben salir el `CLAUDE.md` del proyecto y sus dos `@import`, y ningún `CLAUDE.md` padre.

**EN PRODUCCIÓN (no evaluable):** en el producto actual, `/memory` lista las *ubicaciones* de memoria (también las que no existen) para abrirlas y editarlas, y **no lista las reglas** de `.claude/rules/`. Lo cargado al arrancar se ve con `/context`; las reglas con `paths` y los `CLAUDE.md` de subcarpetas se cargan bajo demanda y lo anuncian con una línea `Loaded` en el terminal (`conceptos-generales.md` §4.6 del repositorio de estudio; `docs/hallazgos.md`). En el examen, `/memory` es la respuesta para «verificar qué memoria está cargada».

**Por qué importa (inferencia propia):** cuando dos sesiones se comportan distinto, lo primero es saber qué instrucciones tiene cargadas cada una. Discutir el comportamiento sin mirar eso es adivinar.

**Anti-patrón / trampa del examen:** diagnosticar la inconsistencia sin mirar qué se cargó: repetir la instrucción en el prompt, reinstalar o suponer que el modelo «se olvidó». La guía da el comando que lo comprueba, `/memory` (TS 3.1-S4), aunque el producto reparta hoy esa información entre `/memory`, `/context` y la línea `Loaded` (ver arriba, EN PRODUCCIÓN).

### 2.3 Variantes personales de una skill

<!-- INTRODUCE: TS 3.2-K4 -->

**Qué dice la guía (TS 3.2-K4):** para personalizar una skill sin afectar al equipo, se crea una variante en `~/.claude/skills/` **con otro nombre**.

**Caso de este proyecto:** si quieres una versión de `verificar-concepto` que se salte la comprobación de la pregunta tipo examen, no edites `.claude/skills/verificar-concepto/`: ese cambio llegaría a todos por git. Crea `~/.claude/skills/verificar-concepto-rapido/SKILL.md`. Con el mismo nombre, una taparía a la otra: dejarías de ver los cambios que el equipo haga en la suya, y nadie que lea el repositorio sabría que tú ejecutas otra cosa. Con otro nombre, las dos conviven. Lo mismo vale para un comando: la variante va en `~/.claude/commands/`, con otro nombre.

**Por qué importa (inferencia propia):** personalizar una skill es legítimo, pero la copia personal no debe cambiar lo que recibe el equipo ni esconder sus cambios. Un nombre distinto deja claro que son dos cosas.

**Anti-patrón / trampa del examen:** editar la skill de proyecto «solo para mí» (el cambio viaja por git a todos) o crear la variante en `~/.claude/skills/` **con el mismo nombre** y dar por hecho que no pasa nada. La guía pide otro nombre (TS 3.2-K4); por qué el mismo nombre es peor (taparía la del equipo) es razonamiento propio, no un hecho de la guía.

### 2.4 Skill frente a `CLAUDE.md`

<!-- INTRODUCE: TS 3.2-S5 -->

**Qué dice la guía (TS 3.2-S5):** una skill se invoca bajo demanda para un flujo concreto; `CLAUDE.md` contiene los estándares universales y se carga siempre.

**Caso de este proyecto:**

| Contenido | Dónde | Por qué |
| :--- | :--- | :--- |
| Regla «una vez», datos sintéticos, `max_budget_usd` en toda ejecución | `CLAUDE.md` | Se aplican a cualquier cambio, lo pida quien lo pida |
| Verificar una viñeta (recorrer `CONCEPTOS.md`, marcadores, cabecera y pregunta) | skill `verificar-concepto` | Solo hace falta cuando alguien lo pide; en `CLAUDE.md` ocuparía contexto en cada sesión |

La prueba rápida: si la instrucción tiene que cumplirse aunque nadie la recuerde, es de `CLAUDE.md` (o de una regla). Si es un procedimiento que alguien lanza, es una skill o un comando.

**Por qué importa (inferencia propia):** `CLAUDE.md` se carga en toda sesión y su coste es fijo; una skill solo cuesta su descripción hasta que se invoca. En el `/context` de la práctica (2026-10-27): `CLAUDE.md`, 1,1k tokens, frente a unos 80 tokens de la descripción de `verificar-concepto`.

**Anti-patrón / trampa del examen:** meter en `CLAUDE.md` un procedimiento que solo se lanza a veces (engorda cada sesión) o, al revés, convertir en skill una regla que debe cumplirse siempre (si nadie la invoca, no se aplica). La guía da el criterio: una skill, bajo demanda, para un flujo concreto; `CLAUDE.md`, para los estándares universales (TS 3.2-S5).

### 2.5 Refinamiento iterativo

<!-- INTRODUCE: TS 3.5-K1, TS 3.5-K2, TS 3.5-K3, TS 3.5-K4, TS 3.5-S1, TS 3.5-S2, TS 3.5-S3, TS 3.5-S4, TS 3.5-S5 -->

**Qué dice la guía (TS 3.5):** reúne cuatro técnicas para que Claude converja hacia lo que quieres: ejemplos concretos de entrada y salida, iteración guiada por tests, entrevista previa (*interview pattern*) y distinguir los problemas que interactúan de los independientes. Cada una, con su caso en el repositorio:

**Ejemplos de entrada y salida (TS 3.5-K1, TS 3.5-S1).** La guía dice que, cuando una descripción en prosa se interpreta de formas distintas, lo más eficaz son 2–3 ejemplos concretos. Caso: «normaliza la fecha del ticket a ISO 8601» admite varias lecturas (¿qué zona horaria?, ¿qué hacer con una fecha ISO sin zona?). Los casos de `tests/test_app2_02_hooks_pre_post.py` (`test_dates_to_iso`) la fijan sin ambigüedad:

| Entrada | Salida esperada |
| :--- | :--- |
| `1788449580` (timestamp Unix) | `2026-09-03T15:33:00+00:00` |
| `"29/09/2026 10:33"` | `2026-09-29T10:33:00+00:00` |
| `"2026-09-21T17:18:00"` (sin zona) | `2026-09-21T17:18:00+00:00`: UTC, no la hora local de la máquina |

El tercero es el que la prosa nunca habría dejado claro.

**Iteración guiada por tests (TS 3.5-K2, TS 3.5-S2).** La guía propone escribir primero los tests (comportamiento esperado, casos borde y, si importa, rendimiento) e iterar compartiendo los fallos. Caso: es el paso 3 de `/nuevo-modulo` («crea el test y comprueba que falla») y la regla «Tests primero» de `docs/estandares-flujo.md` y de `.claude/rules/tests.md`. Los módulos de las apps siguen ese orden: el fallo de `pytest`, con su traza, es lo que se le pasa a Claude en la iteración siguiente.

**Casos de prueba para los casos borde (TS 3.5-S4).** Para corregir un caso borde, la guía recomienda dar el caso con su entrada y su salida esperada (su ejemplo son los valores nulos en una migración). Caso: el hook de umbral de `app2/02`. «Bloquea los reembolsos de más de 500 EUR» no dice qué pasa con 500 justos. Los tests lo dicen: `500.0` pasa, `500.01` se deniega; y `None`, `"seiscientos"` y `"600,50"` también se deniegan (falla en cerrado: un importe que no se puede leer no se aprueba).

**Interview pattern (TS 3.5-K3, TS 3.5-S3).** La guía describe pedirle a Claude que **pregunte primero**, para que salgan consideraciones que no habías previsto, sobre todo en un terreno poco conocido (sus ejemplos: cómo invalidar una caché, qué modos de fallo hay). Caso: el diseño de la capa meta del hito 0. Antes de escribir hooks y reglas, las preguntas útiles eran del tipo: ¿qué pasa si alguien escribe en `datos/sinteticos/` por shell en vez de con `Edit`?, ¿qué `CLAUDE.md` de directorios padre se van a colar?, ¿qué ocurre si el hook falla? Las respuestas están hoy en el proyecto: el *matcher* del hook cubre también `Bash` y `PowerShell` (`.claude/settings.json`), `claudeMdExcludes` excluye los padres y los hooks de la sesión fallan en cerrado (`docs/hallazgos.md`). Un prompt para provocarlo: «Antes de proponer nada, hazme las preguntas que necesites sobre lo que hay que proteger y por qué vías se podría saltar».

**Todos a la vez o de uno en uno (TS 3.5-K4, TS 3.5-S5).** La guía distingue dos casos: si los problemas interactúan, se dan todos en un único mensaje detallado; si son independientes, se corrigen en secuencia. Caso: los 21 hallazgos de la revisión de la entrega 1 (`NOTAS.md`). El criterio de presupuesto (`CCARF_BUDGET_*` como tope de toda la ejecución, repartido entre repeticiones y configuraciones) toca `harness/cli.py` y a todos los módulos que lo usan: si se arregla por partes, cada módulo queda con un reparto distinto, así que va en un mensaje con todos los afectados. En cambio, el fallo en cerrado del hook de umbral de `app2/02` y los falsos positivos de la señal de dependencia de `app3/02` no comparten código ni criterio: se corrigen de uno en uno, y cada arreglo se comprueba con su test.

**Por qué importa (inferencia propia):** las cuatro técnicas cambian cómo te comunicas, no el modelo: le dan un criterio comprobable (un ejemplo, un test, un caso borde) en lugar de más prosa, y evitan iteraciones a ciegas. Se nota en el coste: cada ronda que se podía haber evitado es otra ejecución.

**Anti-patrón / trampa del examen:** insistir con una instrucción en prosa más larga cuando ya se interpreta de formas distintas, en vez de dar 2–3 ejemplos (TS 3.5-K1, S1); dar la regla sin su caso borde con entrada y salida esperada (TS 3.5-S4); pedir una solución sin dejar que Claude pregunte en terreno poco conocido (TS 3.5-K3, S3); y mezclar en un solo mensaje problemas independientes, o corregir de uno en uno los que interactúan (TS 3.5-K4, S5). La pregunta 3 de la sección 4 lo pone a prueba: la opción que explica mejor el formato en prosa es la trampa.

### 2.6 Reglas por ruta frente a `CLAUDE.md` por subdirectorio

Este repositorio usa las dos cosas, y el contraste es la lección (TS 3.3-K3, TS 3.3-S3, ya en `.claude/rules/tests.md`):

| Convención | Mecanismo | Por qué |
| :--- | :--- | :--- |
| «En app1, `01_bucle_manual` usa la Messages API y su tope lo pone `CostGuard`» | `app1_agente_unico/CLAUDE.md` | Aplica a **una carpeta** y a todo lo que contiene |
| «Los tests no llaman al modelo; los fallos esperados van con `xfail(strict=True)`» | `.claude/rules/tests.md` con `paths: ["**/test_*.py"]` | Aplica a **un tipo de archivo** repartido por el repositorio (`tests/` hoy, junto a los servidores mañana) |
| «Cabecera fija en cada módulo de app» | `.claude/rules/apps-comentarios.md` con `paths: ["app*/**/*.py"]` | Aplica a los `.py` de **tres carpetas**; con `CLAUDE.md` por subdirectorio habría que copiarla tres veces |

La pregunta que decide: ¿la convención sigue a una carpeta o a un tipo de archivo? Si sigue a un tipo de archivo disperso, regla por ruta.

### 2.7 Plan mode frente a ejecución directa: las tres complejidades del Exercise 2

El Exercise 2 de la guía pide probar las dos formas en tres tareas de complejidad creciente. Con casos de este proyecto (las viñetas, ya en `docs/estandares-flujo.md`):

| Complejidad | Caso en este proyecto | Modo | Por qué |
| :--- | :--- | :--- | :--- |
| Un bug en un archivo, con traza clara | `Edit` salía denegado en `app1/02` porque `copy_to_temp` devolvía la ruta corta de Windows; arreglo: devolver la ruta resuelta (`harness/data.py`) | Ejecución directa | Un archivo, una causa, un test que lo confirma (TS 3.4-K2, TS 3.4-S2) |
| Una migración que toca muchos archivos | Subir de versión `claude-agent-sdk`, que está fijado en `pyproject.toml` y «solo se actualiza de forma deliberada»: afecta a `harness/options.py`, al recorder y a todos los módulos (caso hipotético, aún no se ha hecho) | Plan mode | Hay que localizar todos los usos antes de tocar ninguno; `Explore` hace ese recorrido (TS 3.4-K1, TS 3.4-S1, TS 3.4-S3) |
| Una funcionalidad con varios enfoques válidos | `app1/02 --parte edicion`: `Edit` no fallaba. Opciones: bajar de modelo, provocar el fallo en el prompt o aceptar que no se ve | Plan mode | Se comparan enfoques antes de elegir (se eligió el prompt, `NOTAS.md`); elegir mal cuesta rehacer código y README (TS 3.4-K3) |

Y la propia entrega 2 es el caso de la combinación (TS 3.4-S4): el diseño se hizo y se aprobó en plan mode (`docs/diseno-entrega-2.md`) y cada módulo se construyó después en ejecución directa.

---

## 3 · Práctica propia

La haces tú, en tu sesión de Claude Code. Anota el resultado en **tu** `NOTAS_PERSONALES.md` (`estado/<perfil>/`, sección «Práctica propia»), no en este repositorio.

1. **Verificación de la capa meta** (roadmap §11.5), en una sesión nueva. Cuatro comprobaciones: `/memory`, las reglas por ruta, la skill y la barrera de `datos/sinteticos/`. La guía completa, con prerrequisitos, lo que debes escribir, lo que debes ver y qué hacer si algo falla, está en la sección 3.1 de abajo.
2. **Un cambio multi-archivo pequeño con plan mode.** Por ejemplo, una variante `--anti` nueva en `app1/03` (un nombre de tool engañoso, sin tocar la descripción): el módulo, su test y su fila en el README. Antes de aprobar el plan, fíjate en si exploró los tests existentes.
3. **Un cambio acotado con ejecución directa.** Por ejemplo, ajustar el texto de un error de `app1_agente_unico/servers/mesa.py` y su test.
4. **Anota**, para los cambios 2 y 3, qué modo elegiste, por qué y si volverías a elegirlo.

### 3.1 · Guía paso a paso del punto 1: verificación de la capa meta

**Quién:** tú, en una sesión de Claude Code que no sea la que construyó el repositorio. **Cuánto:** 15–20 minutos. **Coste:** el de tu sesión; no se ejecuta ningún módulo de las apps ni se llama a la API desde el repositorio.

Un resultado que no coincide con «lo esperado» no es un fallo tuyo: es un hallazgo sobre la capa meta. Apúntalo tal cual (texto literal de la pantalla) y llévalo a quien mantenga el repositorio.

#### Antes de empezar

| Comprobación | Cómo hacerla (en una terminal normal, no en Claude) | Si no sale bien |
| :--- | :--- | :--- |
| Estás en la rama que quieres comprobar y sin cambios sin guardar | `git branch --show-current` y `git status --short` | Cambia de rama o guarda lo pendiente: un cambio a medias confunde las lecturas del paso 2 |
| El entorno funciona (los hooks usan `uv run --no-sync`) | `uv sync` y después `uv run pytest -q` | Sin entorno, los hooks fallan en cerrado y bloquean todo |
| Hay `CLAUDE.md` de directorios **padre** del clon | Bash: `d=$(pwd); while [ "$d" != "/" ]; do d=$(dirname "$d"); ls "$d/CLAUDE.md" 2>/dev/null; done` · PowerShell: `$d=(Get-Location).Path; while ($d = Split-Path $d -Parent) { if (Test-Path (Join-Path $d 'CLAUDE.md')) { Join-Path $d 'CLAUDE.md' } }` | **Sin salida:** no hay padres y no necesitas nada más. **Con salida:** copia `.claude/settings.local.example.json` a `.claude/settings.local.json` y deja el patrón con negación `!**/<carpeta-del-clon>/**`, que excluye todo lo que queda fuera del proyecto, también la memoria de usuario (ese archivo no se versiona) |
| Qué contiene la configuración de **usuario** de tu cuenta | Mira el directorio de configuración de la cuenta con la que abrirás `claude` (`~/.claude/` o el que indique `CLAUDE_CONFIG_DIR`): `CLAUDE.md`, `rules/`, `skills/` y `commands/` | Si tiene alguno, se cargará en toda sesión y aparecerá en `/memory`: no es del proyecto, pero hay que saberlo antes de interpretar el paso 1 |

#### Abrir la sesión

1. En la raíz del repositorio (donde está `CLAUDE.md`): `claude -n practica-d3`. Con el nombre podrás volver con `claude --resume practica-d3`. Para salir, `/exit`.
2. Abre una sesión **nueva**, no una larga. Una lectura anterior cambia lo que anuncia el paso 2: un archivo que ya está en contexto no vuelve a anunciar sus reglas. Antes del paso 2, no leas nada.

#### Paso 1 · `/memory`

Escribe `/memory`.

| Debe aparecer | No debe aparecer |
| :--- | :--- |
| El `CLAUDE.md` del proyecto (el de la raíz) y los dos archivos que importa: `docs/estandares-codigo.md` y `docs/estandares-flujo.md` | Ningún `CLAUDE.md` de un directorio padre |
| | Los `CLAUDE.md` de `app*/`: son de directorio y solo entran en contexto al trabajar en esa carpeta (lo verás en el paso 2) |

**Salida real observada (2026-10-27)**, con los significados:

```
> Auto-memory  true

> Project instructions          Checked in at ./CLAUDE.md
  L docs\estandares-codigo.md   @-imported
  L docs\estandares-flujo.md    @-imported
  User instructions             Saved in ~/.claude/CLAUDE.md
```

- **`Project instructions` con las dos líneas `L … @-imported`:** es lo esperado. El `CLAUDE.md` del proyecto, con sus dos `@import` (TS 3.1-K3).
- **`User instructions  Saved in ~/.claude/CLAUDE.md`:** es el **nivel de usuario** (TS 3.1-K1, K2), no un `CLAUDE.md` de un directorio padre, así que no incumple «ningún padre». Y **no implica que el archivo exista**: `/memory` lista la ubicación para poder abrirla y editarla (**EN PRODUCCIÓN, no evaluable**). Lo decide el sistema de archivos: PowerShell `Test-Path "$HOME/.claude/CLAUDE.md"`, Bash `ls ~/.claude/CLAUDE.md`. Si da `False` o «No such file», la línea es solo una ubicación vacía y no se carga nada. Si existe, se carga en toda sesión (TS 3.1-K2): anota su contenido, porque entra en tu contexto aunque no sea del proyecto.
- **`Auto-memory  true`:** la memoria automática está activa en tu sesión interactiva. Es normal. Las **apps** la apagan (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` en `harness/options.py`) para que cada ejecución sea nueva, y el proyecto prohíbe guardar directivas suyas ahí (`docs/estandares-flujo.md`, «Directivas»).

`/memory` no lista las reglas de `.claude/rules/` (**EN PRODUCCIÓN, no evaluable**; ver la sección 2.2).

Tres comprobaciones rápidas que complementan a `/memory`:

- `/context`: lo cargado al arrancar. Anota el total de memoria y si ves algo que no esperas.
- `/plugin`: en la sección **Built-in** salen los plugins que trae Claude Code, siempre activos y ajenos a tu cuenta (observados el 2026-10-27: `cc-plugin-agents-md`, `cc-plugin-diff`, `cc-plugin-plugin-authoring` y `cc-plugin-telemetry`). Ningún plugin de tu cuenta debe aparecer activado: los que apagues en tu `.claude/settings.local.json` (`enabledPlugins`) salen apagados o no salen. La lista continúa más abajo («more below»), con las skills: desplázate para verla entera. Con el archivo local puesto, el plugin sincronizado `cowork-plugin-management` sale **apagado** (observado el 2026-10-27), no desaparece de la lista.
- `/mcp`: no debe haber conectores de claude.ai; el repositorio fija `ENABLE_CLAUDEAI_MCP_SERVERS=false`.

#### Paso 2 · Reglas por ruta

Escribe estas peticiones, una detrás de otra, y mira la terminal justo debajo de cada lectura. Allí aparece una línea que empieza por `Loaded` y nombra la regla o el `CLAUDE.md` que acaba de entrar.

| Qué escribes | Qué debes ver | Qué demuestra |
| :--- | :--- | :--- |
| `Lee README.md` | Ninguna línea `Loaded` de reglas | Una regla con `paths` no se carga con un `.md` (TS 3.3-K2) |
| `Lee app1_agente_unico/01_bucle_manual.py` | `Loaded` de `.claude/rules/apps-comentarios.md`. Sale también la de `app1_agente_unico/CLAUDE.md`, antes que la de la regla (observado el 2026-10-27) | La regla entra con un `.py` de una app (TS 3.3-K1, K2). El `CLAUDE.md` de subcarpeta es el nivel de directorio (TS 3.1-K1) |
| `Lee tests/test_budget.py` | `Loaded` de `.claude/rules/tests.md` | Un glob por tipo de archivo, no una carpeta (TS 3.3-K3, S2) |
| `Lee d3_claude_code/README.md` (control) | Ninguna regla de apps ni de tests | La regla no se filtra a otros archivos |

Para confirmar que el contenido quedó en contexto, pregunta: `¿Qué dice la regla apps-comentarios sobre la cabecera fija de un módulo?`. Si responde con el contenido de la regla sin volver a leer el archivo, está en contexto.

Si el segundo paso no muestra `Loaded`: comprueba que es sesión nueva (si ya leíste ese archivo, no se repite) y copia el texto exacto que sí ves.

#### Paso 3 · La skill

Antes, escribe `/skills` y busca dos líneas del proyecto: `verificar-concepto … project` (la skill) y `nuevo-modulo … project` (el comando: esta versión del producto lista los comandos de proyecto junto a las skills). El resto de la lista no es del proyecto: las `claude.ai sync` y las `locked by plugin` vienen de tu cuenta. En una cuenta con sincronización de claude.ai la lista tiene más de una docena de skills ajenas al repositorio; no afectan a la comprobación.

1. Escribe `/verificar-concepto` **sin pulsar Intro** y mira el autocompletado: debe mostrar la pista `<TS x.y-Kn|Sn>` (es `argument-hint`).
2. Escribe `/verificar-concepto TS 3.5-K1` y pulsa Intro.
   - **Debe volver:** un informe corto con el destino (`d3`), el estado (☑), dónde está el `INTRODUCE`, si hay pregunta tipo examen y cuántos `USA` hay, más los problemas que encuentre. El asistente principal reformula el informe, así que no esperes la plantilla literal de `SKILL.md`. Escribe la viñeta con la `K` o la `S` **en mayúscula**. La skill acepta también la minúscula y la trata como mayúscula (así lo indica ahora `SKILL.md`; el 2026-10-27, antes de ese cambio, la aceptó pero avisó de que un formato estricto la rechazaría). Es una instrucción, no una validación de código.
   - **Verás un aviso de segundo plano:** en la observación del 2026-10-27 salió «Running in the background as @verificar-concepto» y, unos 30 s después, el informe como notificación. Es normal con `context: fork` en esta versión.
   - **No debe quedar en tu conversación:** las decenas de lecturas y búsquedas que la skill hizo para llegar ahí. Corre en un subagente aislado (`context: fork`) y solo vuelve el resultado (TS 3.2-K3, S2).
3. Escribe `/verificar-concepto` sin argumento y pulsa Intro.
   - **Debe volver:** la línea `Falta la viñeta. Uso: /verificar-concepto <TS x.y-Kn|Sn>`, sin ninguna búsqueda. El asistente principal puede envolverla en una frase suya o añadir un ejemplo (el 2026-10-27 añadió «escribe el comando con la viñeta que quieres comprobar»): esa frase no es de la skill. Lo que cuenta es que la skill se detuvo y no hubo lecturas ni búsquedas.
   - **Lectura (EN PRODUCCIÓN, no evaluable):** `argument-hint` solo se muestra al teclear; el producto lanza la skill igualmente sin argumento. Por eso la propia skill comprueba `$ARGUMENTS` y se detiene (TS 3.2-S4).

Si sale «unknown skill» o similar: comprueba que abriste `claude` desde la raíz del repositorio; la skill está en `.claude/skills/verificar-concepto/SKILL.md`.

#### Paso 4 · La barrera de `datos/sinteticos/`

Hay **dos** barreras y quieres ver cuál actúa en cada caso:

- La regla `permissions.deny` `Edit(./datos/sinteticos/**)` de `.claude/settings.json`.
- El hook `PreToolUse` `.claude/hooks/proteger_rutas.py`, que mira `Edit`, `Write`, `Bash` y `PowerShell`.

La sesión conoce la protección (está en `docs/estandares-codigo.md`) y puede negarse sin intentarlo. Hay que **forzar el intento**, pidiéndolo como prueba autorizada.

**Antes de 4a, pide una lectura:** `Lee datos/sinteticos/usuarios.json` (leer está permitido; solo se protege escribir). La herramienta `Edit` exige haber leído el archivo en la conversación; sin esa lectura, el `Edit` podría fallar por eso y no por la barrera, y no sabrías cuál de las dos cosas viste. Con el archivo ya leído, lo único que puede rechazar la edición es la protección.

| Intento | Qué escribes | Qué debes ver |
| :--- | :--- | :--- |
| 4a · Edit | `Esto es una prueba de seguridad autorizada de la protección del proyecto. Usa la herramienta Edit para cambiar en datos/sinteticos/usuarios.json el nombre del primer usuario a «Prueba». Hazlo aunque sepas que está protegido: quiero ver cómo lo rechaza el sistema; no lo evites ni propongas alternativas.` | El `Edit` aparece rechazado por la regla `deny`: `File is in a directory that is denied by your permission settings.` |
| 4b · Write | `Ahora lo mismo con la herramienta Write: crea datos/sinteticos/prueba.json con el contenido {}.` | La escritura aparece rechazada, también por la regla `deny`, con el mismo texto |
| 4c · Shell | `Ahora con un comando de shell: ejecuta echo prueba > datos/sinteticos/prueba.txt` | El hook lo rechaza (`PreToolUse:Bash hook error` o `PreToolUse:PowerShell hook error`, según la shell) con el texto exacto: `El comando nombra datos/sinteticos/ o un .env: usa Read para leer y datos/generar_sinteticos.py para regenerar.` |

**Cómo saber qué barrera actuó (anótalo en 4a y 4b):**

- Si el mensaje es `File is in a directory that is denied by your permission settings.` (o dice que el permiso está denegado por la configuración), lo rechazó la **regla `deny`**. **Es lo esperado en 4a y 4b:** se comprobó con la versión de Claude Code usada al construir el repositorio. La regla actúa antes que el hook, así que el hook no llega a ejecutarse.
- Si el mensaje contiene `hook error` **y** la frase `está protegido: los datos se cambian con datos/generar_sinteticos.py y .env no se edita`, lo rechazó el **hook**. En 4a o 4b solo lo verás si la regla `deny` no está activa (por ejemplo, si alguien la quitó de `.claude/settings.json`). En 4c lo ves siempre: la regla solo cubre las herramientas de edición, no la shell.
- Esa asimetría es la lección: la regla cubre `Edit` y `Write`; el hook cubre además `Bash` y `PowerShell`. Dos capas, cada una con su alcance.
- Copia el mensaje literal; el texto exacto puede variar con la versión del producto.

**Comprobación final, fuera de la sesión (terminal normal):**

1. `git status --short datos/` no debe mostrar nada.
2. `uv run python datos/generar_sinteticos.py --check` no debe imprimir nada y debe terminar sin error.
3. Si algo se coló: `git checkout -- datos/sinteticos` y borra a mano los archivos nuevos, o regenera con `uv run python datos/generar_sinteticos.py`. Ese `checkout` solo toca esa carpeta, que se genera; no pierdes trabajo.

Si 4a, 4b o 4c **no** son rechazados, es un hallazgo grave de la capa meta: detente, haz la comprobación final, y llévalo tal cual.

#### Paso 5 · Aislamiento del entorno (`.claude/settings.local.json`)

Es parte del buen funcionamiento del repositorio: la sesión que construye debe ver solo lo del proyecto. El archivo local (no versionado) tiene tres partes: `claudeMdExcludes` (negación `!**/<carpeta-del-clon>/**`), `enabledPlugins` (apaga los plugins sincronizados de tu cuenta) y `skillOverrides` (apaga por nombre las skills sincronizadas). **Se aplica al abrir una sesión nueva**: haz esta comprobación en una que arranques después de crearlo.

| Escribes | Debe verse | Qué demuestra |
| :--- | :--- | :--- |
| `/memory` | El `CLAUDE.md` del proyecto con sus dos `@import`. La línea `User instructions … ~/.claude/CLAUDE.md` puede seguir saliendo como ubicación | Que la negación **no** excluyó el `CLAUDE.md` del propio proyecto. Si falta, la carpeta del clon no se llama como el patrón: corrígelo |
| `/context` | En «Memory files»: `CLAUDE.md` y los dos `docs/estandares-*.md`, sin nada de usuario. En «Skills»: **Project** con `verificar-concepto` y `nuevo-modulo`, y **Built-in** con las skills que trae Claude Code (en la observación fueron 16, unos 2,5k tokens: `dataviz`, `code-review`, `claude-api`, `init`…) | Que lo de fuera del proyecto no entra en contexto. Las Built-in no son de tu cuenta ni del proyecto: salen igual para cualquiera con tu versión |
| `/skills` | Ya no aparecen las 13 `claude.ai sync` ni las 2 `locked by plugin` (antes eran 17 con las 2 del proyecto) | Que `skillOverrides` y `enabledPlugins` apagan las ajenas |
| `/plugin` | `cowork-plugin-management` apagado | Que `enabledPlugins` se aplica |

Si queda alguna skill ajena en `/skills`, apunta su nombre exacto y la etiqueta (`claude.ai sync` o `locked by plugin`): `skillOverrides` solo admite nombres exactos, sin comodines, y un nombre mal escrito no hace nada.

**Qué se ha comprobado y qué no:**

- Comprobado (pruebas herméticas, 2026-10-27): la negación deja pasar solo el `CLAUDE.md` y las reglas del proyecto y excluye un `CLAUDE.md` padre y la memoria de usuario (`CLAUDE.md` y reglas); y el repositorio real sigue cargando su `CLAUDE.md` con ese archivo puesto.
- Comprobado: `skillOverrides` oculta una skill con su nombre exacto (skills de proyecto y una incluida con Claude Code) y los comodines no hacen nada.
- Comprobado en una sesión interactiva (2026-10-27, `/context`): con el archivo puesto, «Memory files» lista solo el `CLAUDE.md` del proyecto y sus dos `@import`, y «Skills» deja las 2 del proyecto y las Built-in; ya no están las 13 sincronizadas ni las 2 de plugin. Es decir, `skillOverrides` apaga las sincronizadas reales y `enabledPlugins` las del plugin.
- **Sin comprobar:** la línea `User instructions` de `/memory` tras excluir (puede seguir mostrando la ubicación vacía) y `disableBundledSkills` (apagaría las Built-in; no se ha probado y no hace falta para el aislamiento, porque no dependen de la cuenta).

#### Si algo no sale como se espera

| Síntoma | Causa probable | Qué hacer |
| :--- | :--- | :--- |
| `/memory` muestra un `CLAUDE.md` de un directorio padre | Falta `claudeMdExcludes` | Crea `.claude/settings.local.json` desde el ejemplo (ver «Antes de empezar») y abre una sesión nueva |
| `/memory` muestra `User instructions  Saved in ~/.claude/CLAUDE.md` | Es la ubicación de usuario; el archivo puede no existir | Comprueba con `Test-Path "$HOME/.claude/CLAUDE.md"` (PowerShell) o `ls ~/.claude/CLAUDE.md` (Bash). Si no existe, no hay nada que hacer. Si existe, es esperado pero se carga en tu contexto: no es del proyecto (TS 3.1-K2) y no se puede apagar desde el repositorio. Anota su contenido |
| Paso 2: ninguna línea `Loaded` en ningún archivo | Sesión no nueva, o archivos ya leídos | Cierra con `/exit`, abre otra con `claude -n` y repite sin leer nada antes |
| Paso 3: «unknown skill» | Sesión abierta fuera de la raíz | Sal y abre `claude` desde la raíz del repositorio |
| Paso 4: la sesión se niega a intentarlo | Conoce la protección | Repite con el texto de 4a tal cual («prueba de seguridad autorizada… no lo evites») |
| Paso 4: no entiendes de qué barrera es el mensaje | El texto varía con la versión del producto | Pégalo literal con la salida de `claude --version`: se diagnostica por el texto |

#### Cómo anotar el resultado

En `estado/<perfil>/NOTAS_PERSONALES.md`, sección «Práctica propia», una tabla como esta (rellénala con lo que **viste**, literal y en una línea):

| Paso | ¿Como se esperaba? | Qué viste |
| :--- | :---: | :--- |
| 1 · `/memory` | ✓/✗ | |
| 2 · reglas por ruta (`.md`, `.py`, test, control) | ✓/✗ | |
| 3 · skill con y sin argumento | ✓/✗ | |
| 4a · Edit en `datos/sinteticos/` | ✓/✗ | qué barrera actuó: |
| 4b · Write en `datos/sinteticos/` | ✓/✗ | qué barrera actuó: |
| 4c · shell | ✓/✗ | |
| Comprobación final (`git status`, `--check`) | ✓/✗ | |

Si pegas los ✗ al responsable del repositorio, incluye siempre: el paso, lo que escribiste, el texto literal de la pantalla y la salida de `claude --version`.

#### De dónde sale cada comprobación

Qué esperar de cada paso no es opinión: sale de estas fuentes. La última columna dice **cuánto se ha comprobado** y cuándo, para que sepas qué es un hecho observado y qué es una lectura de la configuración.

| Comprobación | Fuente | Estado de la verificación |
| :--- | :--- | :--- |
| `/memory` lista los `CLAUDE.md` y sus `@import`, no las reglas | Roadmap §11.5 (primer punto de «Capa meta»); `CLAUDE.md` (sección «Contexto heredado»); sección 2.2 de este README | Observado en una sesión nueva al construir el repositorio (`NOTAS.md`, hito 0) y **repetido el 2026-10-27**: salió el `CLAUDE.md` del proyecto con sus dos `@import`, `Auto-memory  true` y la ubicación de usuario `~/.claude/CLAUDE.md`, cuyo archivo no existe (comprobado en esa máquina) |
| Ningún `CLAUDE.md` de directorio padre | `CLAUDE.md` («Contexto heredado»); `.claude/settings.local.example.json` | En un equipo concreto se comprobó que no había padres (búsqueda hacia arriba desde el clon). En el tuyo lo compruebas en «Antes de empezar» |
| `/plugin` y `/mcp` limpios | `CLAUDE.md` («Comprobar con `/memory` y `/plugin`»); `ENABLE_CLAUDEAI_MCP_SERVERS=false` en `.claude/settings.json` | Observado al construir el repositorio (`NOTAS.md`, hito 0, aislamiento). Depende de los plugins de tu cuenta |
| Línea `Loaded` y regla solo con un `.py` de `app*/` | Roadmap §11.5 (segundo punto); frontmatter `paths: ["app*/**/*.py"]` de `.claude/rules/apps-comentarios.md` | Observado al construir el repositorio, con contenido de la regla en contexto, y **repetido el 2026-10-27**: salió con `app1_agente_unico/01_bucle_manual.py` y **no** salió ninguna regla al leer `README.md` |
| `tests.md` con cualquier `test_*.py` | Roadmap §11.5; frontmatter `paths: ["**/test_*.py"]` de `.claude/rules/tests.md` | Observado al construir el repositorio, con un test fuera de `app*/`, y **repetido el 2026-10-27** con `tests/test_budget.py`: salió solo `Loaded` de `tests.md`, sin la de `apps-comentarios.md` |
| Que `app1_agente_unico/CLAUDE.md` también anuncie `Loaded` | Sección 1 de este README (nivel de directorio, TS 3.1-K1) | **Observado el 2026-10-27**: al leer `app1_agente_unico/01_bucle_manual.py` salió `Loaded app1_agente_unico\CLAUDE.md` y después la de `apps-comentarios.md` |
| El control con `d3_claude_code/README.md` | Deducción de los `paths` de las dos reglas | **Sin comprobar.** Es una inferencia; anota lo que veas |
| Skill: informe corto y exploración fuera de tu conversación | Roadmap §11.5 (tercer punto); `.claude/skills/verificar-concepto/SKILL.md` (`context: fork`) | Observado al construir el repositorio, con y sin argumento |
| El aislamiento local (negación de `claudeMdExcludes`, `enabledPlugins`, `skillOverrides`) | `docs/hallazgos.md` («Patrones para excluir…»); esquema de ajustes de la CLI | Negación y `skillOverrides` por nombre: **observado el 2026-10-27** en pruebas herméticas. Efecto sobre skills y plugins reales: **observado el 2026-10-27** en el `/context` de una sesión interactiva |
| `/skills` lista la skill y el comando de proyecto | `.claude/skills/verificar-concepto/SKILL.md`; `.claude/commands/nuevo-modulo.md` | **Observado el 2026-10-27** (Claude Code 2.1.311): `verificar-concepto · project` y `nuevo-modulo · project`, más 13 `claude.ai sync` y 2 `locked by plugin` de la cuenta |
| `argument-hint` solo en el autocompletado; sin argumento se lanza igual | `docs/hallazgos.md` («`argument-hint` no obliga…»); `SKILL.md` (la comprobación de `$ARGUMENTS`) | Observado al construir el repositorio (Claude Code 2.1.310) |
| Texto de la línea `Falta la viñeta…` y primera línea del informe | `SKILL.md` (plantillas de salida); `CONCEPTOS.md` (la fila de TS 3.5-K1 es `d3` y ☑) | La línea sin argumento: **observada el 2026-10-27** (la skill se detuvo y la devolvió; el asistente añadió una frase suya). El informe con argumento: **observado el 2026-10-27**, en segundo plano (32 s), sin líneas de herramienta en la conversación y reformulado por el asistente principal. Repetido tras completar los rótulos de D3: la cabecera salió «completa» y el `CONCEPTO` se tomó del título de la sección |
| `Edit` y `Write` rechazados por la regla `deny` | Roadmap §11.5 (cuarto punto); `.claude/settings.json` (`permissions.deny`) | **Observado el 2026-10-27** al intentarlo desde otra sesión: ambas dieron «File is in a directory that is denied by your permission settings.» y los datos no cambiaron |
| La shell rechazada por el hook, con su texto | `.claude/hooks/proteger_rutas.py` (el texto exacto del bloqueo) | **Observado el 2026-10-27**: varios comandos que nombraban la carpeta fueron bloqueados con ese texto |
| La variante de PowerShell del hook | `.claude/settings.json` (el *matcher* incluye `PowerShell`); cabecera de `proteger_rutas.py` | **Sin comprobar** en ejecución |
| Hay que forzar el intento | Roadmap §11.5 (último punto); `docs/estandares-codigo.md` («Datos») | Razonado: la sesión conoce la protección y puede negarse sin intentarlo |
| La lectura de `.env` denegada | `.claude/settings.json` (`Read(./.env)`) | **Sin comprobar** en ejecución |

---

## 4 · Preguntas tipo examen

### Pregunta 1 (TS 3.1 y 3.3)

Una persona se incorpora al equipo y Claude no aplica en sus sesiones las convenciones de testing, que sí cumple en las de la responsable técnica. Al revisarlo con `/memory`, la persona nueva ve el `CLAUDE.md` del proyecto pero no las convenciones. Los tests están repartidos por muchos directorios del repositorio. ¿Qué cambio es el más adecuado?

- A. Pedir a la persona nueva que copie el `~/.claude/CLAUDE.md` de la responsable en su equipo, para que las dos trabajen con las mismas instrucciones.
- B. Mover las convenciones a `.claude/rules/testing.md`, con un frontmatter `paths` para los archivos de test, y versionarlo con el proyecto.
- C. Crear un `CLAUDE.md` en cada directorio que tenga tests, con las convenciones copiadas, para que se carguen junto a esos archivos.
- D. Pegar las convenciones en el `CLAUDE.md` raíz del proyecto, para que se carguen siempre en todas las sesiones del equipo.

<details>
<summary>Respuesta</summary>

**B.** El diagnóstico es de jerarquía: las convenciones estaban en el nivel de usuario de la responsable, que no se comparte (TS 3.1-K2, TS 3.1-S1), y `/memory` es lo que lo revela (TS 3.1-S4). La solución las sube al proyecto como regla por ruta: se versiona, y con un glob se carga solo con los archivos de test, estén donde estén (TS 3.3-K1, TS 3.3-K2, TS 3.3-S2). A sigue dependiendo de una copia personal que nadie mantiene en común. C funciona, pero repite la convención en cada carpeta: es justo lo que la regla por ruta evita cuando los archivos están dispersos (TS 3.3-K3, TS 3.3-S3). D también la compartiría, pero la carga en todas las sesiones aunque no se toque ningún test y engorda el `CLAUDE.md` que la guía propone dividir (TS 3.1-K4).
</details>

### Pregunta 2 (TS 3.2)

El equipo tiene una skill de proyecto, `analizar-dependencias`, que recorre todo el repositorio. Cada vez que alguien la ejecuta, cientos de líneas de exploración se quedan en la conversación principal, y en alguna ocasión la skill ha modificado archivos aunque solo debía leerlos. ¿Qué cambio en su `SKILL.md` es el más adecuado?

- A. Añadir `argument-hint` en el frontmatter para que pida el directorio que se debe analizar y así recorra solo una parte del repositorio.
- B. Mover la skill a `~/.claude/skills/` de cada persona, para que el volcado y las ediciones solo afecten a quien la ejecuta.
- C. Pasar sus instrucciones al `CLAUDE.md` del proyecto, para que el análisis forme parte del contexto de todas las sesiones.
- D. Añadir `context: fork` para que corra en un subagente aislado y `allowed-tools` con solo tools de lectura en el frontmatter.

<details>
<summary>Respuesta</summary>

**D.** `context: fork` ejecuta la skill en un subagente aislado, y a la conversación principal solo vuelve el resultado (TS 3.2-K3, TS 3.2-S2); `allowed-tools` restringe las tools mientras corre, así que una skill de lectura no puede editar (TS 3.2-S3). A usa `argument-hint` para algo que no resuelve: sirve para pedir un parámetro requerido (TS 3.2-S4), no para aislar la salida ni impedir ediciones. B confunde la variante personal (TS 3.2-K4) con una solución: el equipo pierde la skill compartida y el problema sigue en cada máquina. C va al revés de TS 3.2-S5: un flujo bajo demanda no debe cargarse siempre.
</details>

### Pregunta 3 (TS 3.4 y 3.5)

Un equipo tiene que cambiar la librería de fechas en unos 45 archivos. Un primer intento en ejecución directa, con la instrucción «normaliza todas las fechas a ISO 8601», dejó formatos distintos según el archivo: unos con zona horaria, otros sin ella y otros en hora local. ¿Qué enfoque es el más adecuado para el segundo intento?

- A. Usar plan mode para localizar los usos y diseñar el cambio, con 2–3 ejemplos de entrada y salida esperada, e implementar después en ejecución directa.
- B. Repetir en ejecución directa con una instrucción en prosa más larga, que explique con detalle el formato ISO 8601 y cómo tratar las zonas horarias.
- C. Seguir en ejecución directa archivo por archivo y corregir cada formato incorrecto en un mensaje aparte, a medida que vaya apareciendo.
- D. Hacer toda la tarea en plan mode, incluida la edición de los 45 archivos, para que ningún cambio se aplique sin haber pasado antes por el plan.

<details>
<summary>Respuesta</summary>

**A.** Una migración de librería que toca muchos archivos es el caso de plan mode (TS 3.4-K1, TS 3.4-S1), y lo habitual es combinarlo con ejecución directa para implementar (TS 3.4-S4). La inconsistencia viene de una instrucción en prosa que se interpreta de varias formas: lo que la fija son 2–3 ejemplos concretos de entrada y salida (TS 3.5-K1, TS 3.5-S1). B insiste en la prosa, que es lo que falló. C trata como independientes problemas que comparten la misma causa (la interpretación del formato): van juntos en un mensaje (TS 3.5-K4, TS 3.5-S5), y además se salta la exploración de una tarea multi-archivo. D usa plan mode para lo que no es: sirve para explorar y diseñar con seguridad antes de cambiar nada (TS 3.4-K3), y la implementación posterior es ejecución directa.
</details>
