# Panduan Cepat

🌐 **Bahasa:** [English](../QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [Português (Brasil)](../pt-BR/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [简体中文](../zh-CN/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · Bahasa Indonesia

Setiap perintah dan keluaran di bawah ini dihasilkan dengan menjalankan file contoh repositori. Path bersifat relatif terhadap root repositori.

## 1. Instalasi

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` setara jika skrip `phantom` tidak ada di `PATH` Anda.)

## 2. Melihat sebuah file

[docs/examples/comments.py](../examples/comments.py) adalah Python biasa yang diikuti instruksi Phantom di dalam komentar:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

File ini tidak memiliki import Phantom, decorator, maupun wrapper.

## 3. Python biasa mengabaikan instruksi

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Validasi tanpa menjalankan apa pun

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

File yang rusak ([docs/examples/invalid.py](../examples/invalid.py)) akan ditolak dengan lokasi dan tanda caret, diurutkan menurut nomor baris, serta status keluar 2:

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

(Baris ringkasan dicetak paling akhir; error dikirim ke stderr.) Instruksi yang tidak dikenal tidak pernah dieksekusi.

## 5. Inspeksi

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

Gunakan `--json` untuk keluaran yang dapat dibaca mesin dan `--strict` untuk menandai karakter tak-tercetak yang mencurigakan. Inspeksi tidak pernah menjalankan file.

## 6. Menjalankan dengan Phantom

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

`phantom run` memvalidasi file, menerapkan lapisan instruksi, menjalankan host sebagai subproses, lalu mencetak keluaran host diikuti diagnostik. Status keluarnya adalah status host. Lihat [RUNTIME.md](../RUNTIME.md) untuk siklus hidup lengkap dan untuk apa yang dilakukan serta tidak dilakukan instruksi.

## 7. Hook

[docs/examples/events.py](../examples/events.py) mendaftarkan fungsi biasa untuk event siklus hidup bawaan:

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

## 8. Encoding lainnya

[whitespace.py](../examples/whitespace.py), [unicode.py](../examples/unicode.py) dan [hybrid.py](../examples/hybrid.py) membawa instruksinya dalam bentuk yang tidak terlihat. Ketiganya berjalan di Python biasa maupun di Phantom:

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

Baca [ENCODINGS.md](../ENCODINGS.md) sebelum menggunakannya untuk pekerjaan nyata.

## 9. Generate (opsional, remote)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

Perintah ini mengirim file ke provider yang dikonfigurasi (membutuhkan `pip install "phantom-lang[llm]"` dan `GEMINI_API_KEY`). Lihat [GENERATOR.md](../GENERATOR.md).

## 10. Mengunci kemampuan

Anda dapat membatasi kapabilitas runtime menggunakan `--deny` atau membatasi direktori handler yang diizinkan dengan `--handlers-from`.

### Memblokir kapabilitas

Gunakan `--deny` untuk memblokir kapabilitas tertentu, misalnya `cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Keluaran:
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

Mencoba mengeksekusi file dengan kapabilitas yang diblokir akan menghentikan eksekusi sebelum host dimulai (status keluar 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Keluaran:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Membatasi handler event

Gunakan `--handlers-from` untuk membatasi lokasi modul handler dapat di-import:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Keluaran:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

Jika modul handler berada di luar direktori yang ditentukan, runtime akan menolak import:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Keluaran:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Selanjutnya

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
