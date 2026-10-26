# Início rápido

Todos os comandos e resultados abaixo foram obtidos executando os arquivos de exemplo do repositório. Os caminhos são relativos à raiz do repositório.

## 1. Instalação

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` é equivalente caso o script `phantom` não esteja disponível no `PATH`.)

## 2. Examine um arquivo

[docs/examples/comments.py](../examples/comments.py) é um arquivo Python comum, seguido por instruções do Phantom em comentários:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

Ele não possui importação do Phantom, decorador ou wrapper.

## 3. O Python puro ignora as instruções

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Valide sem executar nada

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

Um arquivo com erros ([docs/examples/invalid.py](../examples/invalid.py)) é rejeitado com a localização do erro e um acento circunflexo (`^`), na ordem das linhas, e código de saída 2:

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

A linha de resumo é exibida por último; os erros são enviados para `stderr`. Instruções desconhecidas nunca são executadas.

## 5. Inspecione

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

Use `--json` para obter uma saída legível por máquinas e `--strict` para sinalizar caracteres invisíveis suspeitos. A inspeção nunca executa o arquivo.

## 6. Execute com o Phantom

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

O comando `phantom run` validou o arquivo, aplicou a camada de instruções, executou o programa hospedeiro como um subprocesso e, em seguida, exibiu a saída do programa seguida pelos diagnósticos. O código de saída é o mesmo do programa hospedeiro.

Consulte [RUNTIME.md](../RUNTIME.md) para conhecer o ciclo de vida completo e entender o que as instruções fazem — e o que não fazem.

## 7. Hooks

[docs/examples/events.py](../examples/events.py) registra funções comuns para os eventos integrados do ciclo de vida:

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

## 8. Outras codificações

Os arquivos [whitespace.py](../examples/whitespace.py), [unicode.py](../examples/unicode.py) e [hybrid.py](../examples/hybrid.py) armazenam suas instruções em formatos invisíveis. Eles funcionam tanto com o Python puro quanto com o Phantom:

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

Leia [ENCODINGS.md](../ENCODINGS.md) antes de utilizá-los em projetos reais.

## 9. Gere instruções (opcional, remoto)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Esse comando envia o arquivo ao provedor configurado. É necessário instalar `pip install "phantom-lang[llm]"` e configurar a variável `GEMINI_API_KEY`.

Consulte [GENERATOR.md](../GENERATOR.md).

## 10. Restrinja as permissões

Você pode restringir os recursos disponíveis durante a execução usando `--deny` ou limitar os diretórios de handlers permitidos usando `--handlers-from`.

### Bloqueando recursos

Use `--deny` para bloquear recursos específicos, como `cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Saída:

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

Tentar executar o arquivo com recursos bloqueados interromperá a execução antes do início do programa hospedeiro (código de saída 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Saída:

```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Restringindo os handlers de eventos

Use `--handlers-from` para restringir os locais de onde os módulos de handlers podem ser importados:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Saída:

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Se o módulo do handler estiver fora do diretório especificado, o runtime rejeitará a importação:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Saída:

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Próximos passos

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
