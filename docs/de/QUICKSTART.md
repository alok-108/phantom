# Schnellstart

🌐 **Sprachen:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · Deutsch

Jeder Befehl und jede Ausgabe unten stammt aus den Beispiel-Dateien des
Repositories. Pfade sind relativ zum Repository-Root.

## 1. Installation

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` ist gleichwertig, wenn das `phantom`-Skript nicht in
Ihrem `PATH` liegt.)

## 2. Eine Datei ansehen

[docs/examples/comments.py](../examples/comments.py) ist gewöhnliches Python,
gefolgt von Phantom-Anweisungen in Kommentaren:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

Es gibt keinen Phantom-Import, keinen Decorator und keinen Wrapper.

## 3. Gewöhnliches Python ignoriert die Anweisungen

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Validieren ohne etwas auszuführen

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

Eine fehlerhafte Datei ([docs/examples/invalid.py](../examples/invalid.py))
wird mit Ort und Caret, in Zeilenreihenfolge, abgelehnt; Exit-Status 2:

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

(Die Zusammenfassung erscheint zuletzt; Fehler gehen nach stderr.) Unbekannte
Anweisungen werden nie ausgeführt.

## 5. Inspizieren

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

Mit `--json` erhalten Sie maschinenlesbare Ausgabe; mit `--strict` werden
verdächtige unsichtbare Zeichen gemeldet. Die Inspektion führt die Datei nie
aus.

## 6. Mit Phantom ausführen

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

`phantom run` hat die Datei validiert, die Anweisungs-Schicht angewendet, den
Host als Subprozess gestartet und danach die Host-Ausgabe gefolgt von den
Diagnosen ausgegeben. Der Exit-Status ist der des Hosts. Den vollständigen
Lebenszyklus und was die Anweisungen tun und nicht tun, beschreibt
[RUNTIME.md](../RUNTIME.md).

## 7. Hooks

[docs/examples/events.py](../examples/events.py) registriert gewöhnliche
Funktionen für die eingebauten Lifecycle-Events:

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

## 8. Andere Kodierungen

[whitespace.py](../examples/whitespace.py), [unicode.py](../examples/unicode.py)
und [hybrid.py](../examples/hybrid.py) tragen ihre Anweisungen in unsichtbarer
Form. Sie laufen unter gewöhnlichem Python und unter Phantom:

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

Lesen Sie [ENCODINGS.md](../ENCODINGS.md), bevor Sie sie produktiv einsetzen.

## 9. Generate (optional, remote)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Das sendet die Datei an den konfigurierten Anbieter (benötigt
`pip install "phantom-lang[llm]"` und `GEMINI_API_KEY`). Siehe
[GENERATOR.md](../GENERATOR.md).

## 10. Absichern

Sie können Laufzeit-Fähigkeiten mit `--deny` einschränken oder erlaubte
Handler-Verzeichnisse mit `--handlers-from` begrenzen.

### Fähigkeiten blockieren

Mit `--deny` blockieren Sie bestimmte Capabilities, zum Beispiel
`cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Ausgabe:
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

Ein Lauf mit verweigerten Capabilities bricht ab, bevor der Host startet
(Exit-Code 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Ausgabe:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Event-Handler einschränken

Mit `--handlers-from` legen Sie fest, aus welchen Verzeichnissen
Handler-Module importiert werden dürfen:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Ausgabe:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Liegt das Handler-Modul außerhalb des angegebenen Verzeichnisses, lehnt die
Runtime den Import ab:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Ausgabe:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Weiter

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) ·
[RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
