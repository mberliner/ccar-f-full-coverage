---
paths: ["**/test_*.py"]
---
<!--
CONCEPTO [TS 3.3-K3, S2, S3]: un glob por tipo de archivo frente a CLAUDE.md por carpeta.
QUÉ DICE LA GUÍA: cuando una convención aplica a archivos dispersos por el
repositorio (p. ej. todos los tests), una regla con un glob por tipo de archivo
la cubre esté donde esté el archivo; un CLAUDE.md por subdirectorio obligaría a
repetirla en cada carpeta.
POR QUÉ IMPORTA: aquí hay tests en tests/ y los habrá junto a los servidores MCP
de cada app; una sola regla los cubre a todos.
ANTI-PATRÓN: copiar las convenciones de testing en un CLAUDE.md de cada carpeta
que contenga tests.
INTRODUCE: TS 3.3-K3, TS 3.3-S2, TS 3.3-S3
-->
# Tests

- **Sin modelo:** los tests nunca llaman al modelo. Lo que depende de su reacción se observa ejecutando el módulo, no en `pytest`.
- **Hooks y tools del SDK:** se prueban con `harness/offline.py`: `run_hook` para los callbacks y `call_tool` para los handlers con `@tool`.
- **Datos:** se cargan de `datos/sinteticos/` o se construyen en el propio test. Nunca se editan a mano los archivos generados.
- **Cabecera:** cada archivo de test empieza con una línea que dice qué prueba y que es «Sin modelo».
- **Fallos esperados:** se marcan con `xfail(strict=True)`, para que pytest avise cuando la marca sobre.
- **Tests primero:** el test del comportamiento esperado y de los casos borde se escribe antes que el código que lo cumple.
