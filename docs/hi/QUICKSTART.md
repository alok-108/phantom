# त्वरित शुरुआत

नीचे दिए गए प्रत्येक command और output को repository की example files चलाकर प्राप्त किया गया है। Paths repository root के सापेक्ष हैं।

## 1. इंस्टॉल करें

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

यदि `phantom` script आपके `PATH` पर नहीं है, तो `python -m phantom …` इसका समकक्ष है।

## 2. फ़ाइल देखें

[docs/examples/comments.py](../examples/comments.py) सामान्य Python है, जिसके बाद comments में Phantom instructions हैं:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

इसमें Phantom import, decorator या wrapper नहीं है।

## 3. सामान्य Python instructions को अनदेखा करता है

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. कुछ चलाए बिना validate करें

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

टूटी हुई फ़ाइल ([docs/examples/invalid.py](../examples/invalid.py)) को location और caret के साथ, line क्रम में अस्वीकार किया जाता है; exit status 2 होता है:

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

(Summary line सबसे अंत में छपती है; errors stderr पर जाते हैं। Unknown instructions कभी execute नहीं होते।)

## 5. Inspect करें

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

Machine-readable output के लिए `--json` और संदिग्ध invisible characters को flag करने के लिए `--strict` इस्तेमाल करें। Inspection फ़ाइल को execute नहीं करता।

## 6. Phantom के साथ चलाएँ

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

`phantom run` ने फ़ाइल validate की, instruction layer लागू की, host को subprocess के रूप में चलाया, फिर host output और diagnostics छापे। इसका exit status host के बराबर होता है। पूरे lifecycle और instructions क्या करते हैं तथा क्या नहीं, इसके लिए [RUNTIME.md](../RUNTIME.md) देखें।

## 7. Hooks

[docs/examples/events.py](../examples/events.py) built-in lifecycle events के लिए सामान्य functions register करता है:

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

## 8. अन्य encodings

`whitespace.py`, `unicode.py` और `hybrid.py` अपने instructions को invisible रूप में रखते हैं। वे सामान्य Python और Phantom दोनों के साथ चलते हैं:

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

वास्तविक काम में इनका उपयोग करने से पहले [ENCODINGS.md](../ENCODINGS.md) पढ़ें।

## 9. Generate करें (वैकल्पिक, remote)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

यह फ़ाइल को configured provider को भेजता है (इसके लिए `pip install "phantom-lang[llm]"` और `GEMINI_API_KEY` चाहिए)। [GENERATOR.md](../GENERATOR.md) देखें।

## आगे पढ़ें

[LANGUAGE_GUIDE.md](../LANGUAGE_GUIDE.md) · [ENCODINGS.md](../ENCODINGS.md) · [RUNTIME.md](../RUNTIME.md) · [GENERATOR.md](../GENERATOR.md)
