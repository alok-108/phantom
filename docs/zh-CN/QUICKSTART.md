# 简体中文版

🌐 **语言:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [Português (Brasil)](../pt-BR/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · 简体中文

以下的每条命令与输出均通过本仓库中示例代码构建。其路径均相对于仓库根目录。

## 1. Install

```bash
python --version            # 3.10及以上版本
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(如果`phantom`不在`PATH`中，`python -m phantom …`与之是等价的。)

## 2. Look at a file

[docs/examples/comments.py](../examples/comments.py)是原始的Python代码，其后是注释中的Phantom指令。

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

代码中不包含Phantom导入，也不包含装饰器或包装器。

## 3. Plain Python ignores the instructions

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Validate without running anything

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

损坏的文件([docs/examples/invalid.py](../examples/invalid.py))将会被拒绝执行，并给出错误位置与插入符，按行顺序显示，且退出状态为 2：

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

(概要将会打印在最后一行，错误信息输出至stderr。)未知指令将永远不会被执行。

## 5. Inspect

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

用`--json`产出机器可读的输出，并用`--strict`标记可疑的不可见字符。检查过程绝不运行该文件。

## 6. Run with Phantom

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

`phantom run`将校验文件，应用其指令层，并将宿主作为子进程运行，随后先输出宿主输出，再输出诊断信息。其退出状态即为宿主的退出状态。有关完整生命周期以及指令的作用范围与边界，请参见 [RUNTIME.md](../RUNTIME.md)。

## 7. Hooks

[docs/examples/events.py](../examples/events.py) 为内置生命周期事件注册了普通函数：

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

## 8. Other encodings

[whitespace.py](../examples/whitespace.py)、[unicode.py](../examples/unicode.py) 和 [hybrid.py](../examples/hybrid.py) 以不可见形式承载其指令。它们既可在普通 Python 下运行，也可在 Phantom 下运行：

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

请在将他们应用到实际工作前，阅读[ENCODINGS.md](../ENCODINGS.md) 。

## 9. Generate (optional, remote)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

这将发送文件到配置好的服务提供商(需要`pip install "phantom-lang[llm]"`并且配置`GEMINI_API_KEY`)。 参见 [GENERATOR.md](../GENERATOR.md)。

## 10. Locking things down
你可以借助`--deny`限制运行时能力，或借助`--handlers-from`限定程序允许的处理目录。

### Blocking Capabilities
利用`--deny`阻止特殊的能力，例如`cap.counters`：

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

输出：
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

当尝试执行能力已被拒绝的文件时，进程将在宿主机启动前中止执行（退出码 2）：

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

输出：
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Restricting Event Handlers
使用 `--handlers-from` 限定处理程序模块的可导入来源：

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

输出：
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

如果处理程序模块位于指定目录之外，则运行时会拒绝该导入：

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

输出：
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Next

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
