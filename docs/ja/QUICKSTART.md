# クイックスタート

🌐 **言語:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [Português (Brasil)](../pt-BR/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [简体中文](../zh-CN/QUICKSTART.md) · 日本語

以下に示すコマンドと出力はすべて、このリポジトリのサンプルファイルを実行して得られたものです。パスはリポジトリのルートからの相対パスです。

## 1. インストール

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`phantom` スクリプトが `PATH` 上にない場合は、`python -m phantom …` でも同じことができます。)

## 2. ファイルを見てみる

[docs/examples/comments.py](../examples/comments.py) は通常の Python で、コメントの中に Phantom の命令が書かれています:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

Phantom のインポートも、デコレータも、ラッパーもありません。

## 3. 通常の Python は命令を無視する

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. 何も実行せずに検証する

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

壊れたファイル([docs/examples/invalid.py](../examples/invalid.py))は、位置とキャレット付きで、行順に拒否され、終了ステータスは 2 になります:

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

(要約行は最後に出力され、エラーは標準エラー出力に出力されます。)不明な命令が実行されることは決してありません。

## 5. インスペクト

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

機械可読な出力には `--json` を、疑わしい不可視文字にフラグを立てるには `--strict` を使います。インスペクトでファイルが実行されることはありません。

## 6. Phantom で実行する

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

`phantom run` はファイルを検証し、命令レイヤーを適用し、ホストをサブプロセスとして実行したうえで、ホストの出力に続けて診断情報を出力しました。終了ステータスはホストのものになります。ライフサイクルの全体像と、命令が行うこと・行わないことについては [RUNTIME.md](../RUNTIME.md) を参照してください。

## 7. フック

[docs/examples/events.py](../examples/events.py) は、組み込みのライフサイクルイベントに対して通常の関数を登録します:

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

## 8. その他のエンコーディング

[whitespace.py](../examples/whitespace.py)、[unicode.py](../examples/unicode.py)、[hybrid.py](../examples/hybrid.py) は、命令を不可視の形式で保持しています。これらは通常の Python でも Phantom でも実行できます:

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

実際に仕事で使う前に [ENCODINGS.md](../ENCODINGS.md) を読んでください。

## 9. 生成(任意、リモート)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

これにより、ファイルが設定済みのプロバイダーに送信されます(`pip install "phantom-lang[llm]"` と `GEMINI_API_KEY` が必要です)。詳細は [GENERATOR.md](../GENERATOR.md) を参照してください。

## 10. ロックダウンする

`--deny` を使ってランタイムのケイパビリティを制限したり、`--handlers-from` を使って許可するハンドラーのディレクトリを制限したりできます。

### ケイパビリティをブロックする

`cap.counters` のような特定のケイパビリティをブロックするには `--deny` を使います:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

出力:
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

拒否されたケイパビリティを持つファイルを実行しようとすると、ホストが起動する前に実行が停止します(終了コード 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

出力:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### イベントハンドラーを制限する

ハンドラーモジュールをインポートできる場所を制限するには `--handlers-from` を使います:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

出力:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

ハンドラーモジュールが指定されたディレクトリの外にある場合、ランタイムはそのインポートを拒否します:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

出力:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## 次のステップ

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
