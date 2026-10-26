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

### 2.2 Comprobar qué memoria está cargada: `/memory`

<!-- INTRODUCE: TS 3.1-S4 -->

**Qué dice la guía (TS 3.1-S4):** `/memory` es el comando para ver qué archivos de memoria están cargados y diagnosticar por qué dos sesiones se comportan distinto.

**Caso de este proyecto:** es la primera comprobación de §11.5 del roadmap y la de «Contexto heredado» de `CLAUDE.md`: en `/memory` deben salir el `CLAUDE.md` del proyecto y sus dos `@import`, y ningún `CLAUDE.md` padre.

**EN PRODUCCIÓN (no evaluable):** en el producto actual, `/memory` lista las *ubicaciones* de memoria (también las que no existen) para abrirlas y editarlas, y **no lista las reglas** de `.claude/rules/`. Lo cargado al arrancar se ve con `/context`; las reglas con `paths` y los `CLAUDE.md` de subcarpetas se cargan bajo demanda y lo anuncian con una línea `Loaded` en el terminal (`conceptos-generales.md` §4.6 del repositorio de estudio; `docs/hallazgos.md`). En el examen, `/memory` es la respuesta para «verificar qué memoria está cargada».

### 2.3 Variantes personales de una skill

<!-- INTRODUCE: TS 3.2-K4 -->

**Qué dice la guía (TS 3.2-K4):** para personalizar una skill sin afectar al equipo, se crea una variante en `~/.claude/skills/` **con otro nombre**.

**Caso de este proyecto:** si quieres una versión de `verificar-concepto` que se salte la comprobación de la pregunta tipo examen, no edites `.claude/skills/verificar-concepto/`: ese cambio llegaría a todos por git. Crea `~/.claude/skills/verificar-concepto-rapido/SKILL.md`. Con el mismo nombre, una taparía a la otra: dejarías de ver los cambios que el equipo haga en la suya, y nadie que lea el repositorio sabría que tú ejecutas otra cosa. Con otro nombre, las dos conviven. Lo mismo vale para un comando: la variante va en `~/.claude/commands/`, con otro nombre.

### 2.4 Skill frente a `CLAUDE.md`

<!-- INTRODUCE: TS 3.2-S5 -->

**Qué dice la guía (TS 3.2-S5):** una skill se invoca bajo demanda para un flujo concreto; `CLAUDE.md` contiene los estándares universales y se carga siempre.

**Caso de este proyecto:**

| Contenido | Dónde | Por qué |
| :--- | :--- | :--- |
| Regla «una vez», datos sintéticos, `max_budget_usd` en toda ejecución | `CLAUDE.md` | Se aplican a cualquier cambio, lo pida quien lo pida |
| Verificar una viñeta (recorrer `CONCEPTOS.md`, marcadores, cabecera y pregunta) | skill `verificar-concepto` | Solo hace falta cuando alguien lo pide; en `CLAUDE.md` ocuparía contexto en cada sesión |

La prueba rápida: si la instrucción tiene que cumplirse aunque nadie la recuerde, es de `CLAUDE.md` (o de una regla). Si es un procedimiento que alguien lanza, es una skill o un comando.

### 2.5 Refinamiento iterativo

<!-- INTRODUCE: TS 3.5-K1, TS 3.5-K2, TS 3.5-K3, TS 3.5-K4, TS 3.5-S1, TS 3.5-S2, TS 3.5-S3, TS 3.5-S4, TS 3.5-S5 -->

La TS 3.5 reúne cuatro técnicas para que Claude converja hacia lo que quieres. Cada una con su caso en el repositorio:

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

1. **Verificación de la capa meta** (roadmap §11.5), en una sesión nueva:
   - `/memory`: ¿qué `CLAUDE.md` e `@import` aparecen? ¿Se cuela algún `CLAUDE.md` padre?
   - Lee un `.md` y después un `.py` de `app1_agente_unico/`. ¿Cuándo aparece la línea `Loaded` de `apps-comentarios.md`? Lee un test de `tests/`: ¿se carga `tests.md`?
   - `/verificar-concepto TS 3.5-K1` y `/verificar-concepto` sin argumento: ¿qué vuelve a tu conversación?
   - Pide editar un archivo de `datos/sinteticos/` **forzando el intento** (si la sesión ya sabe que está protegido, lo esquiva y la barrera no llega a actuar). ¿Qué lo rechaza: la regla `deny` o el hook?
2. **Un cambio multi-archivo pequeño con plan mode.** Por ejemplo, una variante `--anti` nueva en `app1/03` (un nombre de tool engañoso, sin tocar la descripción): el módulo, su test y su fila en el README. Antes de aprobar el plan, fíjate en si exploró los tests existentes.
3. **Un cambio acotado con ejecución directa.** Por ejemplo, ajustar el texto de un error de `app1_agente_unico/servers/mesa.py` y su test.
4. **Anota**, para los cambios 2 y 3, qué modo elegiste, por qué y si volverías a elegirlo.

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
