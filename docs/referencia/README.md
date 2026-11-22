# Referencia

Temas de Claude Code y del Agent SDK escritos para que sirvan fuera de este proyecto. Producto observado (no evaluable) salvo donde cada documento cita la Exam Guide v1.0: ninguno cambia una respuesta de examen.

## Qué entra aquí

- Un tema por carpeta, con todo lo que lo respalda (pruebas, código de ejemplo).
- Cada documento lleva fecha, versión de Claude Code o del SDK y fuentes con clave, y separa lo que dice la guía de lo que hace el producto, con los rótulos de los carriles de contenido.
- Los enlaces van entre archivos de la misma carpeta. Si un documento necesita algo del proyecto, lo cita por su ruta y como del proyecto de origen, sin darlo por supuesto.
- Lo que solo vale para esta implementación (cómo se aplica aquí, medidas de un módulo, decisiones) va a [`../hallazgos.md`](../hallazgos.md), que enlaza al tema.
- Un tema llega aquí cuando reúne varias entradas de `hallazgos.md` y le sirve a alguien sin el repositorio.

## Temas

| Carpeta | Tema | Viñetas relacionadas |
|---|---|---|
| [`precedencia/`](precedencia/) | Nombres repetidos entre agentes, skills y commands, y cómo se acumulan CLAUDE.md, hooks, permisos y settings | TS 1.5, 3.1, 3.2, 3.3 |
| [`hooks/`](hooks/) | Hooks `PreToolUse` y `PostToolUse`: ayuda rápida y escenarios con código | TS 1.5 |
