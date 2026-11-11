# Mini plan: pruebas P1 y P2 en sesión interactiva

Producto observado (no evaluable). Encargo autónomo para una sesión interactiva de Claude Code abierta en un directorio de laboratorio. Desarrolla las pruebas P1 y P2 de `docs/plan-pruebas-precedencia.md`. Ningún resultado cambia una respuesta de examen.

## 1. Objetivo

Averiguar qué definición ejecuta `/nombre` en Claude Code cuando hay dos con el mismo nombre en estos tres casos, que la documentación oficial no resuelve:

| Caso | En `~/.claude/` (usuario) | En `<lab>/.claude/` (proyecto) |
|---|---|---|
| P1 | command | command |
| P2a | command | skill |
| P2b | skill | command |

Lo que ya se sabe por la documentación: entre dos skills, la personal gana a la de proyecto; entre una skill y un command, gana la skill. No dice qué pasa entre dos commands (P1) ni cuál de las dos reglas manda cuando se cruzan (P2a es el caso que las distingue).

## 2. Reparto de tareas

- **El modelo** crea y borra los archivos de cada caso y, al final, redacta el informe con lo que la persona le dicte.
- **La persona** observa: los menús (`/`, `/skills`, `/doctor`) no los ve el modelo. Cada observación se hace en una **sesión nueva** abierta en `<lab>` en otra terminal, para que las definiciones se carguen de cero.

El modelo no debe deducir el resultado por su cuenta ni ejecutar él los commands: espera a lo que la persona pegue.

## 3. Reglas

- `<lab>` es un directorio desechable con `git init`, fuera de cualquier repositorio real. Si no lo es, parar y avisar.
- En `~/.claude/` solo se crean y se borran rutas cuyo nombre empieza por `zz-prec-`. No se toca ningún otro archivo de `~/.claude/`, ni `settings.json`, ni plugins.
- Antes de empezar, anotar si `~/.claude/commands/` existe. Si no existía, se borra al final solo si está vacío (`rmdir`, nunca un borrado recursivo).
- Un caso cada vez: se borran los archivos del caso anterior antes de crear los del siguiente.
- Las sesiones de observación se abren con `claude --model claude-opus-5-5`, sin `--setting-sources` ni `--bare`: hace falta el nivel de usuario activo.
- En las sesiones de observación no aceptar ningún permiso con «no volver a preguntar» ni cambiar estados en `/skills` (solo mirar). Ambas acciones escriben `settings.local.json` y pueden añadir una línea al archivo global de exclusiones de git.
- Anotar la salida de `claude --version`.

## 4. Archivos de cada caso

Los commands son un archivo `.md`; las skills, un directorio con `SKILL.md`. Todos con este contenido, cambiando la descripción y el origen:

```markdown
---
description: <caso> <nivel> <tipo>
---
Responde solo con: ORIGEN=<nivel>-<tipo>
```

| Caso | Archivo | `description` | `ORIGEN` |
|---|---|---|---|
| P1 | `~/.claude/commands/zz-prec-p1.md` | `P1 usuario command` | `usuario-command` |
| P1 | `<lab>/.claude/commands/zz-prec-p1.md` | `P1 proyecto command` | `proyecto-command` |
| P2a | `~/.claude/commands/zz-prec-p2.md` | `P2a usuario command` | `usuario-command` |
| P2a | `<lab>/.claude/skills/zz-prec-p2/SKILL.md` | `P2a proyecto skill` | `proyecto-skill` |
| P2b | `~/.claude/skills/zz-prec-p2/SKILL.md` | `P2b usuario skill` | `usuario-skill` |
| P2b | `<lab>/.claude/commands/zz-prec-p2.md` | `P2b proyecto command` | `proyecto-command` |

## 5. Pasos por caso

Para P1, luego P2a y luego P2b:

1. **Modelo:** borra los archivos `zz-prec-*` del caso anterior, crea los dos del caso y lista lo creado.
2. **Persona**, en una sesión nueva en `<lab>`:
   1. Escribe `/zz-prec-p1` (o `/zz-prec-p2`) **sin enviar**: cuántas entradas ofrece el menú y con qué descripción cada una.
   2. `/skills`: qué entrada aparece con ese nombre y bajo qué origen o grupo.
   3. `/doctor`: si avisa de un nombre duplicado, y el texto del aviso.
   4. Envía `/zz-prec-p1` (o `/zz-prec-p2`): qué `ORIGEN=` devuelve.
3. **Persona:** pega las cuatro observaciones en la sesión del modelo.
4. **Modelo:** las registra tal cual en la tabla de la sección 6, sin interpretarlas todavía.

## 6. Informe

Al acabar los tres casos, el modelo entrega este bloque relleno, listo para copiar:

```markdown
Versión: <salida de claude --version>
Fecha: <AAAA-MM-DD>
Modelo: Opus 5.5

| Caso | Menú `/` (entradas y descripción) | `/skills` (entrada y origen) | `/doctor` | ORIGEN devuelto |
|---|---|---|---|---|
| P1 | | | | |
| P2a | | | | |
| P2b | | | | |

Lectura:
- P1: gana <usuario | proyecto | se listan los dos>.
- P2: <la skill gana en los dos casos (manda el tipo) | gana el nivel personal en los dos (manda el nivel) | otro>.
Incidencias: <permisos pedidos, avisos, cualquier cosa inesperada, o «ninguna»>.
```

La lectura solo afirma lo que las observaciones muestran. Si el menú y el `ORIGEN` no coinciden, se dice y no se elige uno.

## 7. Limpieza

1. **Modelo:** borra `~/.claude/commands/zz-prec-p1.md`, `~/.claude/commands/zz-prec-p2.md` y `~/.claude/skills/zz-prec-p2/` (este último contiene solo `SKILL.md`: borrar el archivo y luego el directorio vacío).
2. **Modelo:** si `~/.claude/commands/` no existía al empezar y ha quedado vacío, lo borra con `rmdir`.
3. **Modelo:** lista `~/.claude/commands/` y `~/.claude/skills/` y confirma que no queda nada que empiece por `zz-prec-`.
4. **Persona:** en una sesión nueva, `/skills` no muestra ningún `zz-prec-`.
5. `<lab>` se puede borrar entero cuando el informe esté copiado.

Los resultados se anotan después en la tabla de `docs/plan-pruebas-precedencia.md` y pasan como hechos a `docs/precedencia-y-nombres.md`.
