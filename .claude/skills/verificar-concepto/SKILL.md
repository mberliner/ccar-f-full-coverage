---
name: verificar-concepto
description: Verifica en el repositorio una viñeta del examen (TS x.y-Kn/Sn) — destino en CONCEPTOS.md, marcador INTRODUCE único y en su sitio, cabecera completa, usos posteriores y pregunta tipo examen — y devuelve un informe breve.
argument-hint: "<TS x.y-Kn|Sn>"
context: fork
allowed-tools: Read, Grep, Glob
# CONCEPTO [TS 3.2-K2, K3, S2, S3, S4]: skill de proyecto con frontmatter.
# QUÉ DICE LA GUÍA: las skills de .claude/skills/ admiten `context: fork` (se
# ejecutan en un subagente aislado y solo vuelve el resultado), `allowed-tools`
# (restringe las tools mientras corre) y `argument-hint` (pide el parámetro si
# se invoca sin él).
# POR QUÉ IMPORTA: recorrer el repositorio produce mucha salida; con fork, la
# conversación principal solo recibe el informe. Una verificación no debe
# escribir, así que solo tiene tools de lectura.
# ANTI-PATRÓN: ejecutar la exploración verbosa en la conversación principal, o
# dar a la skill todas las tools «por si acaso».
# INTRODUCE: TS 3.2-K2, TS 3.2-K3, TS 3.2-S2, TS 3.2-S3, TS 3.2-S4
---

Verifica la viñeta `$ARGUMENTS` en este repositorio. No modifiques ningún archivo.

1. En `CONCEPTOS.md`, localiza la fila de la viñeta y anota su destino (`appN/NN_concepto` o `d3`) y su estado (☐/☑).
2. Busca con Grep el marcador `INTRODUCE:` que contenga el identificador exacto, excluyendo `CONCEPTOS.md`, `NOTAS.md`, `FALLOS.md` y `tests/`. Debe haber como mucho uno, y estar en el destino:
   - si el destino es un módulo, en su archivo;
   - si es `d3`, en `d3_claude_code/`, `.claude/`, `docs/`, `CLAUDE.md` o en el `CLAUDE.md` de una app.
3. Si hay marcador, comprueba que su archivo tiene la cabecera completa:
   - `CONCEPTO` · `QUÉ DICE LA GUÍA` · `POR QUÉ IMPORTA` · `ANTI-PATRÓN`;
   - si es un módulo de app, que el `README.md` de la app tiene la pregunta tipo examen con la respuesta en `<details>`.
4. Lista los marcadores `USA:` con ese identificador. Ninguno debe aparecer si la viñeta sigue ☐.

Devuelve solo este informe, sin volcar el contenido de los archivos:

```
Viñeta: <id> · destino: <destino> · estado: <☐|☑>
INTRODUCE: <ruta o «ninguno»> → <correcto | problema>
Cabecera: <completa | falta X>
Pregunta tipo examen: <sí | no | no aplica>
USA: <n> (<rutas>)
Problemas: <lista o «ninguno»>
```
