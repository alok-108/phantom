# Inicio Rápido

🌐 **Idiomas:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · Spanish

Todos los comandos y resultados que aparecen a continuación se obtuvieron ejecutando los archivos de ejemplo del repositorio. Las rutas son relativas a la raíz del repositorio.

## 1. Instalación

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` es lo equivalente a si el ejecutable `phantom` no estuviera en tu ruta `PATH`.)

## 2. Examinar el archivo

[examples/comments.py](../examples/comments.py) es ordinariamente Python seguido por las instrucciones Phantom en los comentarios:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

No tiene ningun import Phantom, ni decorador ni wrapper.

## 3. Python estándar ignora las instrucciones

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Validar sin ejecutar nada

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

Un archivo incorrecto ([docs/examples/invalid.py](../examples/invalid.py)) es rechazado mostrando su ubicación y un indicador de la posición, siguiendo el orden de las lineas, y con un código de salida 2:

```bash
phantom check docs/examples/invalid.py
```

```text
error: Counter limit must be > 0, got 0
  --> docs/examples/invalid.py:5:1
  5 | #: phantom:0.1.0 counter.create("retries", 0)
    | ^
error: Handler registered for undeclared event 'never.declared'
  --> docs/examples/invalid.py:6:1
  6 | #: phantom:0.1.0 event.on("never.declared", "handlers.go")
    | ^
error: Unknown instruction identifier: 'system.exec'
  --> docs/examples/invalid.py:7:1
  7 | #: phantom:0.1.0 system.exec("calc")
    | ^
3 error(s), 0 warning(s)
```

(La línea de resumen es mostrada al final; Los errores se envían a stderr.) Las instrucciones desconocidas nunca son ejecutadas.

## 5. Inspeccionar

```bash
phantom inspect docs/examples/comments.py
```

```text
File: docs/examples/comments.py
Spec Version: 0.1.0
Total Instructions: 5

Instructions:
  [1] meta.author
      Arguments:    string='Ada Lovelace'
      Source:       docs/examples/comments.py:14:0
      Encoding:     comment
      Capabilities: cap.metadata
  ...
```

Utiliza `--json` para obtener una salida legible por máquina y `--strict` para detectar caracteres invisibles sospechosos. La inspección nunca ejecuta un archivo.

## 6. Ejecutar con Phantom

```bash
phantom run docs/examples/comments.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (5 instruction(s), 0 warning(s))
Hello, World!

--- Phantom Diagnostics ---
[INFO] [docs/examples/comments.py:18:0 [comment]] Greeting counter initialised
```

`phantom run` validó el archivo, aplicó la capa de instrucciones, ejecutó el programa anfitrión como un subproceso y, después, mostró la salida del programa anfitrión seguida de los diagnósticos.
Su código de salida es el mismo que el del programa anfitrión. Consulta [RUNTIME.md](../RUNTIME.md) para conocer el ciclo de vida completo y saber qué hacen y qué no hacen las instrucciones.

## 7. Hooks (ganchos)

[docs/examples/events.py](../examples/events.py) registra funciones normales de Python para los eventos integrados del ciclo de vida:

```bash
phantom run docs/examples/events.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (2 instruction(s), 0 warning(s))
[hook] about to run events.py
[hook] finished with exit code 0
Doing the work.
```

## 8. Otras codificaciones

Los archivos [whitespace.py](../examples/whitespace.py), [unicode.py](../examples/unicode.py) y [hybrid.py](../examples/hybrid.py) contienen sus instrucciones en formatos invisibles. Se ejecutan tanto Python estándar como con Phantom:

```bash
phantom run docs/examples/whitespace.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (1 instruction(s), 0 warning(s))
Executing core Python logic!

--- Phantom Diagnostics ---
[INFO] [docs/examples/whitespace.py:11:0 [whitespace]] hidden in whitespace
```

Lee [ENCODINGS.md](../ENCODINGS.md) antes de utilizar estas codificaciones en proyectos reales.

## 9. Generar (opcional, remoto)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Este comando envía el archivo al proveedor configurado. (Requiere instalar `pip install "phantom-lang[llm]"` y disponer de una variable `GEMINI_API_KEY`). Consulta [GENERATOR.md](../GENERATOR.md).

## 10. Restringir las capacidades y los permisos
Puedes restringir las capacidades disponibles durante la ejecución mediante `--deny` o limitar los directorios desde los que se permite importar módulos de controladores de eventos mediante `--handlers-from`.

### Bloquear capacidades
Usa `--deny` para bloquear capacidades especificas, como `cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Salida:
```text
File: docs/examples/policy.py
Spec Version: 0.1.0
Total Instructions: 3

Instructions:
  [1] counter.create
      Arguments:    string='cap.counters', integer=10
      Source:       docs/examples/policy.py:10:0
      Encoding:     comment
      Capabilities: cap.counters
      Policy:       BLOCKED (denied: cap.counters)
  [2] counter.increment
      Arguments:    string='cap.counters'
      Source:       docs/examples/policy.py:11:0
      Encoding:     comment
      Capabilities: cap.counters
      Policy:       BLOCKED (denied: cap.counters)
  [3] event.on
      Arguments:    string='phantom.pre_execute', string='hooks.on_start'
      Source:       docs/examples/policy.py:12:0
      Encoding:     comment
      Capabilities: cap.events
```

Si intentas ejecutar el archivo con capacidades denegadas, se detendrá la ejecución antes de que se inicie el programa anfitrión. (exit código de salida 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Salida:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Restringir los controladores de eventos
Utiliza `--handlers-from` para restringir los directorios desde los que se pueden importar módulos de controladores de eventos:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Salida:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Si el módulo del controlador se encuentra fuera del directorio especificado, el entorno de ejecución rechazará la importación:
```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Salida:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

  ## Siguientes pasos

  [LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
