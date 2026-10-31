# Démarrage rapide

🌐 **Langues :** [English](QUICKSTART.md) · [हिन्दी](hi/QUICKSTART.md) · [Deutsch](de/QUICKSTART.md) · [Español](es/QUICKSTART.md) · [Português (Brasil)](pt-BR/QUICKSTART.md) · Français

Toutes les commandes et tous les résultats ci-dessous ont été produits en exécutant les fichiers d'exemple du dépôt. Les chemins sont relatifs à la racine du dépôt.

## 1. Installation

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` est équivalent si le script `phantom` n'est pas sur votre `PATH`.)

## 2. Examiner un fichier

[docs/examples/comments.py](examples/comments.py) est du Python ordinaire suivi d'instructions Phantom dans des commentaires :

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

Il n'a ni import Phantom, ni décorateur, ni enveloppe.

## 3. Le Python ordinaire ignore les instructions

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Valider sans rien exécuter

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

Un fichier défectueux ([docs/examples/invalid.py](examples/invalid.py)) est rejeté avec l'emplacement et un accent circonflexe, dans l'ordre des lignes, et le code de sortie 2 :

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

(La ligne de résumé est imprimée en dernier ; les erreurs vont vers stderr.) Les instructions inconnues ne sont jamais exécutées.

## 5. Inspecter

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

Utilisez `--json` pour une sortie lisible par machine et `--strict` pour signaler les caractères invisibles suspects. L'inspection n'exécute jamais le fichier.

## 6. Exécuter avec Phantom

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

`phantom run` a validé le fichier, appliqué la couche d'instructions, exécuté l'hôte comme sous-processus, puis affiché la sortie de l'hôte suivie des diagnostics. Son code de sortie est celui de l'hôte. Voir [RUNTIME.md](RUNTIME.md) pour le cycle de vie complet et pour ce que les instructions font et ne font pas.

## 7. Crochets (hooks)

[docs/examples/events.py](examples/events.py) enregistre des fonctions ordinaires pour les événements de cycle de vie intégrés :

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

## 8. Autres encodages

[whitespace.py](examples/whitespace.py), [unicode.py](examples/unicode.py) et [hybrid.py](examples/hybrid.py) portent leurs instructions sous forme invisible. Ils s'exécutent sous Python ordinaire et sous Phantom :

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

Lisez [ENCODINGS.md](ENCODINGS.md) avant de les utiliser pour un vrai travail.

## 9. Générer (facultatif, à distance)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Cela envoie le fichier au fournisseur configuré (nécessite `pip install "phantom-lang[llm]"` et `GEMINI_API_KEY`). Voir [GENERATOR.md](GENERATOR.md).

## 10. Verrouiller les choses

Vous pouvez restreindre les capacités d'exécution avec `--deny` ou limiter les répertoires de gestionnaires autorisés avec `--handlers-from`.

### Bloquer des capacités

Utilisez `--deny` pour bloquer des capacités précises, comme `cap.counters` :

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Sortie :
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

Tenter d'exécuter le fichier avec des capacités refusées arrêtera l'exécution avant le démarrage de l'hôte (code de sortie 2) :

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Sortie :
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Restreindre les gestionnaires d'événements

Utilisez `--handlers-from` pour restreindre l'endroit d'où les modules de gestionnaires peuvent être importés :

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Sortie :
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Si le module de gestionnaire se trouve en dehors du répertoire indiqué, l'exécution rejette l'import :

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Sortie :
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Suite

[LANGUAGE_GUIDE.md](LANGUAGE_GUIDE.md) · [ENCODINGS.md](ENCODINGS.md) · [RUNTIME.md](RUNTIME.md) · [GENERATOR.md](GENERATOR.md)
