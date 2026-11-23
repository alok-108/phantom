# Hướng dẫn nhanh (Quick Start)

🌐 **Ngôn ngữ:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [Português (Brasil)](../pt-BR/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [简体中文](../zh-CN/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md) · Tiếng Việt

Mọi câu lệnh và kết quả đầu ra dưới đây đều được tạo từ việc chạy các tệp ví dụ trong kho lưu trữ. Các đường dẫn được tính từ thư mục gốc của kho lưu trữ.

## 1. Cài đặt

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` có tác dụng tương đương nếu lệnh `phantom` chưa nằm trong `PATH` của bạn.)

## 2. Xem một tệp mẫu

[docs/examples/comments.py](../examples/comments.py) là một tệp Python bình thường kèm theo các chỉ thị Phantom trong phần chú thích:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

Tệp này không hề `import` Phantom, không có decorator và cũng không có wrapper nào.

## 3. Python thuần bỏ qua các chỉ thị

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Kiểm tra hợp lệ mà không chạy mã

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

Một tệp lỗi ([docs/examples/invalid.py](../examples/invalid.py)) sẽ bị từ chối kèm vị trí và dấu mũ chỉ lỗi theo thứ tự dòng, với mã thoát 2:

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

(Dòng tóm tắt được in ở cuối; các lỗi được ghi ra `stderr`.) Những chỉ thị không xác định sẽ không bao giờ được thực thi.

## 5. Kiểm tra chi tiết (Inspect)

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
      Kind:         metadata-only
  ...
```

Dùng `--json` để xuất định dạng máy đọc được và `--strict` để cảnh báo các ký tự ẩn đáng ngờ. Lệnh inspect không bao giờ thực thi tệp.

## 6. Chạy với Phantom

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

`phantom run` kiểm tra tệp, áp dụng lớp chỉ thị, chạy chương trình gốc trong một tiến trình con, rồi in đầu ra của chương trình cùng phần chẩn đoán. Mã thoát là mã thoát của chương trình gốc. Xem [RUNTIME.md](../RUNTIME.md) để biết toàn bộ vòng đời và những gì chỉ thị làm hoặc không làm.

## 7. Hooks

[docs/examples/events.py](../examples/events.py) đăng ký các hàm Python thông thường cho những sự kiện vòng đời tích hợp sẵn:

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

## 8. Các kiểu mã hóa khác

[whitespace.py](../examples/whitespace.py), [unicode.py](../examples/unicode.py) và [hybrid.py](../examples/hybrid.py) lưu chỉ thị dưới dạng ẩn. Chúng chạy được cả dưới Python thuần lẫn dưới Phantom:

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

Hãy đọc [ENCODINGS.md](../ENCODINGS.md) trước khi sử dụng chúng trong công việc thực tế.

## 9. Sinh chỉ thị (tùy chọn, từ xa)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Lệnh này gửi tệp lên nhà cung cấp đã cấu hình (cần `pip install "phantom-lang[llm]"` và `GEMINI_API_KEY`). Xem [GENERATOR.md](../GENERATOR.md).

## 10. Siết chặt quyền thực thi

Bạn có thể giới hạn quyền năng (capabilities) lúc chạy bằng `--deny` hoặc giới hạn thư mục chứa handler được phép bằng `--handlers-from`.

### Chặn quyền năng (Capabilities)

Dùng `--deny` để chặn các quyền năng cụ thể, chẳng hạn `cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Output:
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
      Kind:         executable
      Policy:       BLOCKED (denied: cap.counters)
  [2] counter.increment
      Arguments:    string='cap.counters'
      Source:       docs/examples/policy.py:11:0
      Encoding:     comment
      Capabilities: cap.counters
      Kind:         executable
      Policy:       BLOCKED (denied: cap.counters)
  [3] event.on
      Arguments:    string='phantom.pre_execute', string='hooks.on_start'
      Source:       docs/examples/policy.py:12:0
      Encoding:     comment
      Capabilities: cap.events
      Kind:         executable
```

Thử chạy tệp với quyền năng bị từ chối sẽ dừng thực thi trước khi chương trình gốc bắt đầu (mã thoát 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Giới hạn Event Handlers

Dùng `--handlers-from` để giới hạn thư mục nơi các module handler được phép import:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Nếu module handler nằm ngoài thư mục được chỉ định, runtime sẽ từ chối import:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Tiếp theo

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
