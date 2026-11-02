# PROPÓSITO: dejar `stdout` y `stderr` en UTF-8 en cuanto se importa cualquier
# parte del arnés, para que los módulos puedan imprimir ✓, ✗ o ·.
# POR QUÉ EXISTE: con la salida redirigida (Claude Code con `!`, una tubería, un
# archivo) Python en Windows codifica en cp1252 y `print("✓")` lanza
# UnicodeEncodeError a mitad de un módulo (visto en la prueba del narrador con
# `app1/05`). Así nadie necesita conocer `PYTHONUTF8` ni `PYTHONIOENCODING`.
# QUÉ NO HACE: no toca la variable de entorno ni la configuración global; solo
# reconfigura los dos flujos de este proceso. Si el flujo no admite
# `reconfigure` (p. ej. el que sustituye pytest al capturar), lo deja como está.
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
