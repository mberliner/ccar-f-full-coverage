<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Revisado por una instancia independiente (3.9, 2026-11-14) y corregido en 3.10 (2026-11-15).
-->
# E2 · Claude Code en el equipo de la mesa de ayuda

> **Escenario:** E2
> **Dominios principales:** D3 · D5
> **Preguntas:** 10
> **Tiempo orientativo:** 20 minutos

## Contexto

El equipo que mantiene la aplicación de la mesa de ayuda (un backend en Python con varios paquetes, cuyas pruebas `test_*.py` están repartidas por muchas carpetas junto al código que prueban, y un frontend en React) usa Claude Code a diario para generar código, refactorizar, depurar y documentar. Hasta ahora cada persona lo configuraba a su manera; el equipo quiere integrarlo en su flujo de trabajo con un `CLAUDE.md` bien organizado, comandos y skills propios, y un criterio común para decidir cuándo planificar antes de tocar el código y cuándo cambiarlo directamente. En las próximas semanas tiene previstas tareas de todos los tamaños, desde arreglos de una línea hasta la migración de una biblioteca que usa medio backend.

## Restricciones compartidas

- R1: lo que vale para todo el equipo se versiona en el repositorio; lo personal no debe cambiar lo que reciben los demás.
- R2: el contexto de la sesión principal se reserva para el trabajo en curso: lo que no hace falta siempre no se carga siempre.
- R3: antes de un cambio que toque muchos archivos o admita varios enfoques se acuerda el enfoque; los arreglos acotados no esperan.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 3.1 | una respuesta |
| 2 | TS 3.1 | una respuesta |
| 3 | TS 3.3 | una respuesta |
| 4 | TS 3.2 | multiple-response |
| 5 | TS 3.2 | una respuesta |
| 6 | TS 3.4 | multiple-response |
| 7 | TS 5.4 | una respuesta |
| 8 | TS 3.5 | una respuesta |
| 9 | TS 3.5 | multiple-response |
| 10 | TS 5.4 | una respuesta |

## Preguntas

### Pregunta 1 (TS 3.1 · una respuesta)

El `CLAUDE.md` raíz ha crecido hasta varios cientos de líneas con las normas de la API, de las migraciones de base de datos y del frontend, y cada paquete solo necesita parte de ellas. Quienes mantienen cada paquete saben qué normas le aplican. ¿Qué organización respeta R1 y R2?

- A. Mover las normas de cada paquete al `~/.claude/CLAUDE.md` de quien lo mantiene.
- B. Dejar el `CLAUDE.md` raíz como está y pedir en él que se ignore lo que no aplique.
- C. Convertir cada archivo de normas en una skill que cada persona invoque si se acuerda.
- D. Que el `CLAUDE.md` de cada paquete importe con `@` solo las normas que le aplican.

<details>
<summary>Respuesta</summary>

**D.** La sintaxis `@import` mantiene el `CLAUDE.md` modular, y quien mantiene cada paquete elige qué archivos de normas incluye en el suyo (TS 3.1-K3, TS 3.1-S2); el archivo del paquete se versiona y llega a todo el equipo. A deja las normas en el nivel de usuario, que no se comparte por el control de versiones (TS 3.1-K2) y rompe R1. B sigue cargando todo en cada sesión, en contra de R2. C convierte normas que deben aplicarse siempre en algo que depende de invocarlo: las skills son para flujos a demanda y `CLAUDE.md` para las normas que se cargan siempre (TS 3.2-S5).
</details>

### Pregunta 2 (TS 3.1 · una respuesta)

Una desarrolladora observa que Claude Code respeta la convención de nombres del equipo en sus sesiones, pero no en las de un compañero que trabaja sobre el mismo repositorio. ¿Cuál es el primer paso para diagnosticar la diferencia?

- A. Ejecutar `/memory` en las dos sesiones y comparar qué archivos de memoria se cargan.
- B. Pedir a Claude, en cada sesión, que resuma de memoria las normas que está siguiendo.
- C. Copiar la convención en el `~/.claude/CLAUDE.md` del compañero que no la recibe.
- D. Repetir la convención en mayúsculas en el `CLAUDE.md` raíz para que pese más.

<details>
<summary>Respuesta</summary>

**A.** `/memory` muestra qué archivos de memoria están cargados y es la forma de diagnosticar un comportamiento que cambia entre sesiones (TS 3.1-S4); una causa típica es que la convención esté en el nivel de usuario de una persona y no en el del proyecto (TS 3.1-S1). B no dice qué archivos se cargaron, solo lo que el modelo cuenta. C tapa el síntoma en una sola máquina con configuración personal, que no se comparte (TS 3.1-K2) y rompe R1. D cambia el texto sin averiguar si el archivo llega a cargarse.
</details>

### Pregunta 3 (TS 3.3 · una respuesta)

El equipo quiere que Claude Code siga unas convenciones de pruebas del backend cada vez que edite un archivo `test_*.py`, que hay en decenas de carpetas distintas, sin cargarlas cuando trabaja en el frontend. ¿Dónde las escribe?

- A. En un `CLAUDE.md` dentro de cada carpeta que hoy contiene pruebas del backend.
- B. En un archivo de `.claude/rules/` con `paths: ["**/test_*.py"]` en su frontmatter.
- C. En una sección «Pruebas» del `CLAUDE.md` raíz, que se carga en todas las sesiones.
- D. En un comando `/pruebas` de `.claude/commands/` que cada persona lance antes.

<details>
<summary>Respuesta</summary>

**B.** Una regla de `.claude/rules/` con un campo `paths` de patrones glob se activa solo al editar archivos que coinciden, sea cual sea su carpeta (TS 3.3-K1, TS 3.3-K2, TS 3.3-S2). A es la alternativa que la guía descarta para convenciones repartidas por todo el código: obliga a mantener un archivo por carpeta (TS 3.3-K3, TS 3.3-S3). C carga las normas también al trabajar en el frontend, en contra de R2. D depende de que cada persona se acuerde de invocarlo y no se activa por el archivo que se edita.
</details>

### Pregunta 4 (TS 3.2 · multiple-response)

El equipo versiona en `.claude/skills/analizar-paquete/` una skill que recorre un paquete del backend y produce un análisis muy largo. Quiere que ese análisis no llene la conversación principal (R2) y que, si alguien la invoca sin decir qué paquete, se le indique que falta. **Selecciona dos** cambios en el frontmatter del `SKILL.md`. Evalúa cada opción por separado.

- A. Añadir `context: fork` para que la skill se ejecute en un subagente aislado.
- B. Añadir `argument-hint` para indicar el paquete cuando se invoca sin argumento.
- C. Añadir `allowed-tools` con solo escritura para que la salida no llegue a la sesión.
- D. Añadir `paths` con el patrón de los paquetes para que se cargue solo al editarlos.

<details>
<summary>Respuesta</summary>

**A y B.** Cada uno cubre uno de los dos objetivos del enunciado.

- **A** Correcta. `context: fork` ejecuta la skill en un contexto de subagente aislado y evita que una salida extensa, como un análisis de código, contamine la conversación principal (TS 3.2-K3, TS 3.2-S2).
- **B** Correcta. `argument-hint` sirve para pedir a quien invoca la skill sin argumentos el parámetro que necesita (TS 3.2-S4).
- **C** Incorrecta. `allowed-tools` restringe qué tools puede usar la skill mientras se ejecuta, por ejemplo para evitar acciones destructivas (TS 3.2-S3); no aísla su salida ni pide el argumento.
- **D** Incorrecta. `paths` es el campo de las reglas de `.claude/rules/` para cargarlas según el archivo que se edita (TS 3.3-K1), no una opción del frontmatter de una skill de las que nombra la guía (TS 3.2-K2). Y aunque lo fuera, no consigue ninguno de los dos objetivos: decidir cuándo se carga algo no aísla la salida del análisis ni pide el paquete que falta.
</details>

### Pregunta 5 (TS 3.2 · una respuesta)

El equipo comparte la skill `/notas-version`, que redacta las notas de cada entrega. Un desarrollador quiere una versión con otro tono solo para su uso, sin cambiar lo que reciben sus compañeros (R1). ¿Qué hace?

- A. Edita el `SKILL.md` del proyecto con su tono y avisa al equipo del cambio.
- B. Crea en `~/.claude/skills/` una skill con el mismo nombre que la del proyecto.
- C. Crea en `~/.claude/skills/` una variante con otro nombre, solo para su uso.
- D. Añade al `CLAUDE.md` del proyecto una nota con el tono que él prefiere.

<details>
<summary>Respuesta</summary>

**C.** La personalización personal se hace con variantes en `~/.claude/skills/` y con otro nombre, para no afectar a los compañeros (TS 3.2-K4). A cambia la skill compartida, que se versiona y llega a todo el equipo (TS 3.2-K1), así que rompe R1. B se aparta de esa práctica: la guía describe la variante personal con un nombre distinto del de la skill del equipo. D mete una preferencia personal en un archivo compartido que se carga en las sesiones de todos.
</details>

### Pregunta 6 (TS 3.4 · multiple-response)

El equipo repasa las tareas de la semana para decidir cuáles empiezan en plan mode, según R3. **Selecciona dos** tareas para las que la guía recomienda plan mode. Evalúa cada opción por separado.

- A. Migrar el cliente HTTP a otra biblioteca, un cambio que afecta a unos 50 archivos.
- B. Corregir un fallo de un solo archivo con una traza que señala la línea exacta.
- C. Elegir entre dos formas de integrar la cola de avisos, con infraestructura distinta.
- D. Añadir una validación de fecha a la función que crea los tickets de soporte.

<details>
<summary>Respuesta</summary>

**A y C.** Las dos tienen implicaciones de arquitectura; las otras dos son cambios acotados.

- **A** Correcta. Una migración de biblioteca que toca decenas de archivos es el caso típico de plan mode (TS 3.4-K1, TS 3.4-S1).
- **B** Incorrecta. Un arreglo en un solo archivo con una traza clara es un cambio de alcance definido: ejecución directa (TS 3.4-S2).
- **C** Correcta. Elegir entre enfoques de integración con requisitos de infraestructura distintos admite varios enfoques válidos y es una decisión de arquitectura (TS 3.4-K1, TS 3.4-S1).
- **D** Incorrecta. Añadir una validación a una función es el ejemplo de cambio simple y bien acotado para ejecución directa (TS 3.4-K2, TS 3.4-S2).
</details>

### Pregunta 7 (TS 5.4 · una respuesta)

Al preparar la migración del cliente HTTP, la sesión principal se va llenando con listados largos de búsqueda en el código, y aún quedan varias fases de exploración. ¿Qué enfoque mantiene la sesión principal útil, según R2?

- A. Leer en la sesión principal todos los archivos que usan el cliente antes de seguir.
- B. Copiar los listados de búsqueda al `CLAUDE.md` para tenerlos a mano en adelante.
- C. Pedir que vuelque en la conversación todos los resultados, sin resumir ninguno.
- D. Encargar a subagentes preguntas concretas y dejar a la principal la coordinación.

<details>
<summary>Respuesta</summary>

**D.** Delegar en subagentes preguntas concretas (por ejemplo, «encuentra todos los archivos que usan el cliente») aísla la salida verbosa de la exploración mientras la sesión principal conserva la visión de conjunto (TS 5.4-K3, TS 5.4-S1); entre fases se resumen los hallazgos y se pasan al siguiente subagente (TS 5.4-S3). A y C hacen justo lo contrario: llenan el contexto principal con salida de exploración. B carga esos listados en todas las sesiones futuras, en contra de R2.
</details>

### Pregunta 8 (TS 3.5 · una respuesta)

El equipo pide a Claude Code una función que convierta las referencias antiguas de tickets al formato nuevo. Lo describe en prosa, y cada vez la conversión sale distinta en los casos menos habituales. ¿Qué cambio es el más eficaz?

- A. Reescribir la descripción en prosa con más detalle y en un tono más enérgico.
- B. Repetir la petición hasta que el resultado salga bien y quedarse con ese.
- C. Dar dos o tres ejemplos concretos de referencia antigua y su forma esperada.
- D. Pedir a Claude que explique la regla con sus palabras antes de cada conversión.

<details>
<summary>Respuesta</summary>

**C.** Cuando una descripción en prosa se interpreta de forma inconsistente, los ejemplos concretos de entrada y salida son la forma más eficaz de comunicar la transformación esperada (TS 3.5-K1, TS 3.5-S1). A insiste en la prosa, que es lo que ya falla. B no cambia nada de lo que recibe el modelo y deja el resultado al azar. D no aporta información nueva sobre la transformación que se espera.
</details>

### Pregunta 9 (TS 3.5 · multiple-response)

Tras una refactorización del cálculo de prioridad de los tickets quedan tres problemas: el redondeo de la puntuación y el orden de los umbrales se afectan entre sí (arreglar uno cambia el resultado del otro), y además hay una errata independiente en un mensaje de registro. **Selecciona dos** formas de pedir los arreglos. Evalúa cada opción por separado.

- A. Explicar en un único mensaje detallado los dos problemas que se influyen entre sí.
- B. Corregir por separado los dos que interactúan, uno en cada mensaje sucesivo.
- C. Tratar aparte, en su propia iteración, la errata del mensaje de registro.
- D. Juntar los tres en un mensaje, porque siempre conviene dar todos los fallos a la vez.

<details>
<summary>Respuesta</summary>

**A y C.** Los problemas que interactúan van juntos; los independientes, por separado.

- **A** Correcta. Cuando los arreglos interactúan, se describen todos en un solo mensaje detallado (TS 3.5-K4, TS 3.5-S5).
- **B** Incorrecta. Arreglarlos por turnos ignora que cada arreglo cambia el resultado del otro, que es justo el caso en que la guía pide un único mensaje (TS 3.5-S5).
- **C** Correcta. Un problema independiente se puede resolver con iteración secuencial (TS 3.5-K4, TS 3.5-S5).
- **D** Incorrecta. La guía distingue entre problemas que interactúan y problemas independientes (TS 3.5-K4); «siempre a la vez» no es su criterio.
</details>

### Pregunta 10 (TS 5.4 · una respuesta)

En una sesión larga de depuración, Claude Code empieza a dar respuestas que no cuadran con lo que encontró al principio y habla de «patrones típicos» en lugar de las clases concretas que había localizado en el backend. ¿Qué práctica contrarresta mejor este problema?

- A. Mantener un archivo de notas con los hallazgos clave y remitir a él en cada pregunta.
- B. Seguir en la misma sesión y repetir la pregunta hasta que cite las clases correctas.
- C. Empezar una sesión nueva sin nada de lo anterior y volver a explorar todo el código.
- D. Pegar otra vez en la conversación el contenido completo de los archivos ya leídos.

<details>
<summary>Respuesta</summary>

**A.** Las respuestas inconsistentes y las referencias a «patrones típicos» son la señal de degradación del contexto en sesiones largas (TS 5.4-K1), y un archivo de notas (*scratchpad*) con los hallazgos clave, al que se remite en las preguntas siguientes, es lo que la guía propone para contrarrestarla (TS 5.4-K2, TS 5.4-S2). B no cambia la causa. C pierde los hallazgos ya hechos y obliga a repetir la exploración. D llena aún más el contexto, que es lo que lo degrada.
</details>
