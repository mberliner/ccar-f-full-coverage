<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Pendiente de revisión por una instancia distinta de la que lo escribió (paquete 3.9 del plan de mejoras).
-->
# E4 · Asistente para explorar un sistema heredado

> **Escenario:** E4
> **Dominios principales:** D1 · D2 · D3
> **Preguntas:** 8
> **Tiempo orientativo:** 16 minutos

## Contexto

Un equipo de plataforma hereda el sistema de facturación de otra área: varios cientos de archivos, pocas pruebas y nadie que conozca el código. Construye con el Claude Agent SDK un asistente que ayuda a sus ingenieros a orientarse en ese código, explicar flujos antiguos, generar código repetitivo y automatizar tareas rutinarias. El asistente usa las tools integradas (Read, Write, Edit, Bash, Grep, Glob) y se conecta a servidores MCP: uno del gestor de incidencias que ya usa la empresa y otro propio con el catálogo de esquemas de la base de datos. El mismo equipo trabaja a diario con Claude Code sobre el repositorio, y quiere que la configuración compartida llegue igual a todos sus miembros.

## Restricciones compartidas

- R1: ninguna credencial se guarda en el repositorio; la configuración compartida sí se versiona.
- R2: lo que vale para todo el equipo llega por el repositorio, no por la configuración de cada persona.
- R3: el contexto de la conversación principal es limitado y no debe llenarse con salidas largas de exploración.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 2.5 | una respuesta |
| 2 | TS 2.5 | una respuesta |
| 3 | TS 2.4 | multiple-response |
| 4 | TS 2.4 | una respuesta |
| 5 | TS 3.1 | una respuesta |
| 6 | TS 3.2 | multiple-response |
| 7 | TS 3.4 | una respuesta |
| 8 | TS 1.7 | una respuesta |

## Preguntas

### Pregunta 1 (TS 2.5 · una respuesta)

Una ingeniera pide al asistente que localice todos los sitios del código que llaman a la función `calcular_recargo` antes de cambiar su firma. ¿Qué tool integrada es la adecuada para empezar?

- A. Glob, con un patrón que encuentre los archivos cuyo nombre contenga «recargo».
- B. Grep, buscando el nombre de la función en el contenido de todo el código.
- C. Read sobre cada archivo del repositorio, para revisar las llamadas una a una.
- D. Bash, listando los directorios del proyecto para deducir dónde se usa.

<details>
<summary>Respuesta</summary>

**B.** Buscar quién llama a una función es buscar en el contenido de los archivos, que es para lo que sirve Grep (TS 2.5-K1, TS 2.5-S1). A busca por nombre de archivo (TS 2.5-K2), y un archivo que llama a la función no tiene por qué llamarse así. C lee todo de entrada en lugar de construir la comprensión poco a poco desde los puntos de entrada (TS 2.5-S4). D no mira el contenido.
</details>

### Pregunta 2 (TS 2.5 · una respuesta)

El asistente intenta cambiar una línea de configuración con Edit, pero el texto que usa como ancla aparece varias veces en el mismo archivo y la edición falla. ¿Qué debería hacer para completar el cambio de forma fiable?

- A. Repetir Edit con la misma ancla hasta que acierte con la aparición buscada.
- B. Abandonar el cambio y pedir a la ingeniera que lo haga ella a mano.
- C. Usar Grep para contar las apariciones y elegir la primera de ellas.
- D. Leer el archivo completo con Read y escribirlo modificado con Write.

<details>
<summary>Respuesta</summary>

**D.** Cuando Edit no encuentra un texto único, la alternativa fiable es cargar el archivo con Read y escribirlo entero con Write (TS 2.5-K4, TS 2.5-S3). A repite una operación que fallará igual, porque el ancla sigue sin ser única. B renuncia a una alternativa que existe. C no resuelve el fallo de Edit: contar apariciones no hace única el ancla.
</details>

### Pregunta 3 (TS 2.4 · multiple-response)

El equipo quiere que todos sus miembros tengan el servidor MCP del gestor de incidencias, y nota que el asistente prefiere Grep sobre los archivos exportados antes que la tool del servidor, que devuelve las incidencias con su historial completo. **Selecciona dos** cambios que lo resuelven respetando R1 y R2.

- A. Declarar el servidor en el `.mcp.json` del proyecto, con el token como `${INCIDENCIAS_TOKEN}`.
- B. Declarar el servidor en el `~/.claude.json` de cada ingeniero, con su token escrito allí.
- C. Escribir el token en claro en el `.mcp.json` del proyecto para que nadie tenga que configurarlo.
- D. Ampliar la descripción de la tool MCP con lo que sabe hacer y lo que devuelve.

<details>
<summary>Respuesta</summary>

**A y D.** Lo compartido va en el `.mcp.json` del proyecto con expansión de variables, y el agente deja de preferir Grep cuando la descripción de la tool MCP explica su capacidad y su salida.

- **A** Correcta: el ámbito de proyecto es el de las herramientas compartidas, y la expansión de variables evita versionar el secreto (TS 2.4-K1, TS 2.4-K2, TS 2.4-S1).
- **B** Incorrecta: el ámbito de usuario es para servidores personales o de prueba (TS 2.4-S2), y no llega al equipo por el repositorio, contra R2.
- **C** Incorrecta: versiona la credencial, contra R1; la expansión de variables existe justo para evitarlo (TS 2.4-K2).
- **D** Correcta: una descripción detallada de capacidades y salida evita que el agente prefiera una tool integrada como Grep a una tool MCP más capaz (TS 2.4-S3).
</details>

### Pregunta 4 (TS 2.4 · una respuesta)

En cada sesión, el asistente hace una docena de llamadas exploratorias al servidor propio solo para averiguar qué tablas y esquemas existen antes de responder. ¿Qué cambio en el servidor reduce esas llamadas?

- A. Fusionar todas las tools del servidor en una sola con un parámetro de acción.
- B. Subir el límite de turnos del asistente para que termine la exploración.
- C. Exponer el catálogo de esquemas como recurso MCP visible para el agente.
- D. Quitar el servidor propio y leer los esquemas con Read desde el disco.

<details>
<summary>Respuesta</summary>

**C.** Los recursos MCP sirven para exponer catálogos de contenido, como esquemas de base de datos, y dar al agente visibilidad de lo que hay sin llamadas exploratorias (TS 2.4-K4, TS 2.4-S5). A cambia la forma de las tools, no la visibilidad del catálogo. B deja que siga explorando, solo que durante más tiempo. D renuncia al servidor del equipo y obliga a buscar los archivos a mano.
</details>

### Pregunta 5 (TS 3.1 · una respuesta)

Un ingeniero recién llegado ve que Claude Code no sigue en sus sesiones la convención de nombres del módulo de facturación, que sus compañeros sí obtienen. Esa convención la escribió hace meses la jefa del equipo. ¿Qué es lo primero que conviene comprobar?

- A. Si la convención está en el `~/.claude/CLAUDE.md` de la jefa y no en el del proyecto.
- B. Si el recién llegado usa una versión de Claude Code distinta de la del resto.
- C. Si la convención es demasiado larga y debe resumirse en una sola línea.
- D. Si el recién llegado ha abierto la sesión desde la raíz del repositorio clonado.

<details>
<summary>Respuesta</summary>

**A.** Las instrucciones de nivel de usuario solo se aplican a esa persona y no se comparten por el control de versiones (TS 3.1-K2); diagnosticar que una persona nueva no recibe instrucciones porque están en el nivel de usuario y no en el de proyecto es el caso que describe la guía (TS 3.1-S1). Con `/memory` se ve qué archivos de memoria se cargan (TS 3.1-S4). B y C no explican que solo falle a una persona. D no explica por qué los compañeros sí la obtienen con el mismo repositorio.
</details>

### Pregunta 6 (TS 3.2 · multiple-response)

El equipo crea una skill del proyecto, `analizar-modulo`, que recorre un módulo heredado y produce un análisis muy largo. Quiere que no llene la conversación principal (R3) y que, si alguien la invoca sin decir qué módulo, se le pida. **Selecciona dos** ajustes del frontmatter de su `SKILL.md`.

- A. `allowed-tools` limitado a Write, para que la skill pueda guardar su análisis en disco.
- B. `context: fork`, para que el análisis se haga en un contexto de subagente aislado.
- C. `argument-hint`, para que pida el módulo a quien la invoque sin argumentos.
- D. Mover la skill a `~/.claude/skills/` de cada ingeniero, para aislar su contexto.

<details>
<summary>Respuesta</summary>

**B y C.** `context: fork` aísla la salida larga y `argument-hint` pide el parámetro que falta.

- **B** Correcta: `context: fork` ejecuta la skill en un subagente aislado y evita que su salida contamine la conversación principal, lo indicado para análisis de código verbosos (TS 3.2-K3, TS 3.2-S2).
- **C** Correcta: `argument-hint` sirve para pedir los parámetros necesarios cuando se invoca la skill sin argumentos (TS 3.2-S4).
- **A** Incorrecta: `allowed-tools` restringe las tools durante la skill (TS 3.2-S3), pero dejar solo Write le impide leer el módulo que tiene que analizar, y no aísla el contexto.
- **D** Incorrecta: `~/.claude/skills/` es para variantes personales (TS 3.2-K4); la skill dejaría de compartirse con el equipo, contra R2, y la ubicación no aísla el contexto.
</details>

### Pregunta 7 (TS 3.4 · una respuesta)

Hay que sustituir la biblioteca de fechas del sistema heredado por otra, un cambio que toca unos 60 archivos y admite dos estrategias de migración con distinto coste. ¿Cómo conviene abordarlo con Claude Code?

- A. Ejecución directa, archivo por archivo, corrigiendo según aparezcan los fallos.
- B. Ejecución directa en un único paso que reescriba los 60 archivos a la vez.
- C. Plan mode para investigar y elegir estrategia, y después ejecución directa.
- D. Plan mode durante toda la migración, sin pasar nunca a ejecución directa.

<details>
<summary>Respuesta</summary>

**C.** Un cambio que afecta a muchos archivos y admite varios enfoques válidos es el caso de plan mode (TS 3.4-K1, TS 3.4-S1), y la guía recomienda combinarlo: plan mode para investigar y diseñar, ejecución directa para aplicar lo planificado (TS 3.4-S4). A y B usan ejecución directa, que la guía reserva para cambios simples y acotados (TS 3.4-K2), y arriesgan rehacer trabajo. D no pasa nunca a implementar lo planificado.
</details>

### Pregunta 8 (TS 1.7 · una respuesta)

Un ingeniero dejó ayer una sesión con nombre, `facturacion-flujos`, analizando el cálculo de impuestos. Esta mañana un compañero cambió dos de los archivos analizados; el resto del análisis sigue siendo válido. ¿Cómo debería continuar?

- A. Empezar una sesión nueva sin contexto y repetir toda la exploración desde cero.
- B. Reanudar con `--resume facturacion-flujos` e indicar qué dos archivos cambiaron.
- C. Reanudar con `--resume facturacion-flujos` y seguir sin mencionar los cambios.
- D. Bifurcar la sesión con `fork_session` y seguir en la rama sin decir qué cambió.

<details>
<summary>Respuesta</summary>

**B.** Reanudar es lo indicado cuando el contexto previo sigue siendo válido en su mayor parte (TS 1.7-S3), y hay que informar a la sesión reanudada de los archivos concretos que cambiaron para que los vuelva a analizar sin repetir toda la exploración (TS 1.7-K3, TS 1.7-S4). A tira un análisis que sigue valiendo. C deja al agente trabajando con resultados desfasados de esos dos archivos. D sirve para explorar enfoques divergentes desde una base común (TS 1.7-K2), no para actualizar un análisis, y tampoco avisa de los cambios.
</details>
