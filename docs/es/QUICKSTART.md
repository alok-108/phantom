  # Inicio Rápido

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

  [examples/comments.py](../examples/comments.py) es ordiriamente Python seguido por las instrucciones Phantom en los comentarios:

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

  ## Siguientes pasos

  [LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
