# Phantom

🌐 **भाषाएँ:** [English](../../README.md) · हिन्दी

[![tests](https://github.com/hayagrivai-labs/phantom/actions/workflows/tests.yml/badge.svg)](https://github.com/hayagrivai-labs/phantom/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/hayagrivai-labs/phantom)](https://github.com/hayagrivai-labs/phantom/releases)
[![license: MIT](https://img.shields.io/github/license/hayagrivai-labs/phantom)](../../LICENSE)
[![python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](../COMPATIBILITY.md)
[![good first issues](https://img.shields.io/github/issues/hayagrivai-labs/phantom/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/hayagrivai-labs/phantom/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
[![discussions](https://img.shields.io/github/discussions/hayagrivai-labs/phantom)](https://github.com/hayagrivai-labs/phantom/discussions)

> **योगदानकर्ताओं का स्वागत है।** पहली बार आए हैं? [अच्छे शुरुआती मुद्दों](https://github.com/hayagrivai-labs/phantom/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) में से चुनें, [योगदानकर्ता मार्गदर्शिका](../CONTRIBUTOR_GUIDE.md) पढ़ें और [Discussions](https://github.com/hayagrivai-labs/phantom/discussions) में परिचय दें। नया instruction जोड़ने के लिए चार कोड बदलाव करने होते हैं। `mentor available` लेबल वाले मुद्दों पर मेंटेनर मदद उपलब्ध है। तैयार वातावरण के लिए [Codespace खोलें](https://codespaces.new/hayagrivai-labs/phantom)।

**Phantom** एक दो-स्तरीय प्रोग्रामिंग अवधारणा है: सामान्य Python स्रोत कोड के साथ comments (या whitespace / zero-width blocks) में एम्बेड की गई दूसरी, संरचित *instruction layer*। आपके कोड में Phantom imports, decorators या wrappers की आवश्यकता नहीं है।

> संस्करण **0.1.1** — शुरुआती रिलीज़। यह छोटा और परीक्षण किया हुआ है, और इसकी सीमाएँ स्पष्ट रूप से बताई गई हैं ([वर्तमान सीमाएँ](#वर्तमान-सीमाएँ) देखें)।

<p align="center">
  <img src="../assets/demo.svg" alt="टर्मिनल डेमो: Python Phantom लाइनों को अनदेखा करता है; phantom check उनकी जाँच करता है; phantom run उन्हें लागू करता है; phantom generate diff के रूप में सुझाव देता है" width="100%">
</p>

## क्यों?

वास्तविक Python कोड में अक्सर ऐसा अतिरिक्त ढाँचा भर जाता है जो मुख्य व्यावसायिक लॉजिक का हिस्सा नहीं होता: metrics calls, lifecycle hooks, provenance notes, decorators और tooling के लिए `import` lines। Phantom इसे अलग तरीके से व्यवस्थित करता है। आपकी फ़ाइल सामान्य Python ही रहती है। अतिरिक्त निर्देश पास की एक **दूसरी, typed और validated layer** में रहते हैं, जिसे tools और लोग पढ़, जाँच और लागू कर सकते हैं। LLM बदलाव को पूरे कोड के rewrite के बजाय **diff** के रूप में सुझा सकता है।

- **आपका कोड अपरिवर्तित रहता है।** `python app.py` इसे पहले की तरह चलाता है। Phantom इसे संपादित नहीं करता।
- **दूसरी layer की जाँच की जा सकती है।** इसमें formal grammar, `phantom check`, `phantom inspect` और invisible characters की सख्त जाँच है।
- **AI बदलाव सत्यापित किए जा सकते हैं।** `phantom generate` केवल नई lines जोड़ता है और तभी सुझाव स्वीकार करता है जब Python AST मूल के समान हो।
- **छोटा और स्पष्ट।** सात instructions, कोई runtime dependencies नहीं, और features को *Implemented / Experimental / Proposed* के रूप में चिह्नित किया गया है।

## 30 सेकंड में आज़माएँ

```bash
pip install "git+https://github.com/hayagrivai-labs/phantom.git"
printf 'print("Hello")\n#: phantom:0.1.0 diagnostic.note("it works")\n' > hello.py
phantom run hello.py
```

आपको पहले `Hello`, फिर Phantom diagnostic `it works` दिखना चाहिए। (अभी PyPI पर उपलब्ध नहीं है; [docs/RELEASING.md](../../docs/RELEASING.md) देखें।)

अगर Phantom उपयोगी या दिलचस्प लगे, तो star देने से दूसरों को इसे खोजने में मदद मिलेगी। योगदान देना चाहते हैं, तो [अच्छे शुरुआती मुद्दे](https://github.com/hayagrivai-labs/phantom/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) सबसे अच्छा शुरुआती रास्ता हैं।

## यह क्या है?

```python
def process_payment(amount: float) -> bool:
    return amount > 0

#: phantom:0.1.0 meta.author("Payments team")
#: phantom:0.1.0 counter.create("payments", 1000)
#: phantom:0.1.0 diagnostic.note("Payment module annotated")
```

- `python app.py` आपका कोड चलाता है; Phantom lines comments हैं और सामान्य Python में **execute नहीं होतीं**।
- `phantom run app.py` instruction layer को parse और validate करता है, उसे लागू करता है, फिर आपकी अपरिवर्तित फ़ाइल को subprocess के रूप में चलाता है।

Phantom Python को संशोधित नहीं करता, import hooks स्थापित नहीं करता और आपका environment नहीं बदलता। Execution model के लिए [docs/RUNTIME.md](../../docs/RUNTIME.md) देखें।

## सुविधाएँ

- सात instructions: events, सीमित counters, diagnostic notes और author/version metadata ([संदर्भ](../../docs/LANGUAGE_GUIDE.md))।
- Formal grammar ([SPECIFICATION.md](../../SPECIFICATION.md)) और typed, immutable IR।
- चार encodings: **comment** (अनुशंसित), whitespace, zero-width Unicode और hybrid ([ENCODINGS.md](../ENCODINGS.md))।
- Line/column diagnostics और SARIF export के साथ static validation।
- Invisible और bidirectional characters की सख्त जाँच (`--strict`)।
- सामान्य functions वाले lifecycle event handlers; प्रति-instruction capabilities।
- वैकल्पिक LLM-सहायता वाला generator, जो अलग candidate file सुझाता है ([GENERATOR.md](../../docs/GENERATOR.md))।
- कोई runtime dependencies नहीं। जब तक आप `generate` नहीं चलाते और सहमति नहीं देते, network का उपयोग नहीं होता।

## इंस्टॉल करें

Python ≥ 3.10।

```bash
pip install .                 # core
pip install -e ".[dev]"       # development (pytest, ruff)
pip install -e ".[llm]"       # optional: google-genai for `phantom generate`
```

[docs/INSTALLATION.md](../../docs/INSTALLATION.md) देखें।

## त्वरित शुरुआत

```bash
phantom check   docs/examples/comments.py     # validate, run nothing
phantom inspect docs/examples/comments.py     # show decoded instructions
phantom run     docs/examples/comments.py     # apply instructions, run the host
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (5 instruction(s), 0 warning(s))
Hello, World!

--- Phantom Diagnostics ---
[INFO] [docs/examples/comments.py:18:0 [comment]] Greeting counter initialised
```

पूरा walkthrough: [docs/QUICKSTART.md](QUICKSTART.md)।

## Commands

| Command | उद्देश्य | क्या आपका कोड चलाता है? |
| :--- | :--- | :--- |
| `phantom check FILE [--strict] [--format sarif]` | जाँच; त्रुटियों पर exit 2 | नहीं |
| `phantom inspect FILE [--json] [--strict]` | पहचाने गए instructions, स्थान और capabilities दिखाता है | नहीं |
| `phantom run FILE [-- ARGS]` | जाँच, instructions लागू, host चलाता है; host का status लौटाता है | **हाँ** |
| `phantom generate FILE --intent TEXT [--placement …] [--encoding …] [--output …] [--dry-run] [--allow-remote]` | Phantom instructions वाला candidate सुझाता है | नहीं (source provider को भेजता है) |
| `phantom diff ORIGINAL CANDIDATE` | Unified diff | नहीं |
| `phantom verify ORIGINAL CANDIDATE` | दोनों चलाकर stdout/stderr/exit code की तुलना | **हाँ** (दोनों) |

यदि `phantom` script आपके `PATH` पर नहीं है, तो `python -m phantom …` इसका समकक्ष है।

## Instructions

| Instruction | प्रभाव |
| :--- | :--- |
| `event.declare(name)` | event घोषित करता है |
| `event.on(event, handler)` | घोषित event के लिए `"module.function"` पंजीकृत करता है |
| `diagnostic.note(message)` | स्थान सहित note दर्ज करता है |
| `counter.create(name, limit)` | सीमित counter (`limit > 0`) बनाता है |
| `counter.increment(name)` | 1 जोड़ता है (limit पार होने पर error diagnostic दर्ज होता है) |
| `meta.author(name)` / `meta.version(version)` | provenance metadata |

Instructions के प्रभाव **initialisation के समय, host शुरू होने से पहले** लागू होते हैं, न कि उस line तक execution पहुँचने पर। केवल lifecycle events `phantom.pre_execute`, `phantom.post_execute` और `phantom.shutdown` fire होते हैं।

## LLM generator

`phantom generate` वास्तविक instruction registry से JSON plan माँगता है, उसे validate करता है, निर्देशों को स्वयं चुने स्थान पर नई lines के रूप में जोड़ता है और जाँचता है कि परिणाम valid Python, valid Phantom और मूल के **समान Python AST** वाला है। यह आपकी फ़ाइल को overwrite नहीं करता और candidate को चलाता नहीं है। Gemini provider का उपयोग करने पर source Google की service को भेजा जाता है; इसके लिए `--allow-remote` आवश्यक है। इस repository में live API के विरुद्ध provider integration नहीं चलाया गया है। विवरण और सीमाएँ: [docs/GENERATOR.md](../../docs/GENERATOR.md)।

## सुरक्षा संबंधी बातें

- Parsing, `check`, `inspect` और `diff` आपकी फ़ाइलों को execute या rewrite नहीं करते (tests से सत्यापित)।
- Instruction arguments literals होते हैं; decode की गई सामग्री `eval`/`exec`/shell को नहीं दी जाती।
- **`phantom run` फ़ाइल चलाता है और handler paths modules import करते हैं** — केवल भरोसेमंद फ़ाइलें चलाएँ। कोई sandbox नहीं है।
- Whitespace / zero-width encodings न तो secret हैं, न secure; उन्हें दिखाने के लिए `--strict` है।

[SECURITY.md](../../SECURITY.md) और [docs/THREAT_MODEL.md](../../docs/THREAT_MODEL.md) देखें।

## वर्तमान सीमाएँ

- केवल Python hosts; instructions host control flow में hook नहीं कर सकतीं।
- Custom events घोषित किए जा सकते हैं, लेकिन host code से fire नहीं किए जा सकते।
- Whitespace और zero-width encodings formatters तथा normalisation से प्रभावित हो सकते हैं।
- `verify` केवल एक run की तुलना करता है; यह equivalence का प्रमाण नहीं है।
- CI Python 3.10–3.13 पर Ubuntu और Windows में पास हुआ है; macOS का परीक्षण नहीं हुआ है।
- **Phantom C** (compiled languages के लिए dual-layer model और observer visibility का अध्ययन) दीर्घकालीन **research vision** है, implemented सुविधा नहीं: [docs/research/PHANTOM_C.md](../../docs/research/PHANTOM_C.md)। सभी features की स्थिति: [docs/RESEARCH_STATUS.md](../../docs/RESEARCH_STATUS.md)।

## Tests

```bash
pytest                                   # full suite
pytest --cov=phantom --cov-report=term-missing
ruff check src tests scripts
python scripts/verify_release.py         # release consistency gates
```

## योगदान करें

हर आकार के योगदान का स्वागत है: bug fixes, tests, docs, नए instructions, encodings, LLM providers और research experiments। [CONTRIBUTING.md](../../CONTRIBUTING.md) और चरण-दर-चरण [Contributor Guide](../CONTRIBUTOR_GUIDE.md) से शुरुआत करें (एक instruction जोड़ने के लिए चार code edits चाहिए)। विचारों को `good first issue`, `help wanted`, `mentor available` और `needs design` labels वाले GitHub issues में track किया जाता है। Pull request से पहले `ruff check src tests scripts`, `pytest` और `python scripts/verify_release.py` चलाएँ। प्रश्न और सुझाव [Discussions](https://github.com/hayagrivai-labs/phantom/discussions) में साझा करें; maintainers [MAINTAINERS.md](../../MAINTAINERS.md) में और design decisions [docs/adr/](../../docs/adr/) में हैं।

### योगदानकर्ता

<a href="https://github.com/hayagrivai-labs/phantom/graphs/contributors"><img src="https://contrib.rocks/image?repo=hayagrivai-labs/phantom" alt="योगदानकर्ता"></a>

जिनके pull request merge होते हैं, उन्हें release notes में धन्यवाद दिया जाता है।

## दस्तावेज़

[SPECIFICATION](../../SPECIFICATION.md) · [VISION](../../VISION.md) · [ROADMAP](../../ROADMAP.md) · [CHANGELOG](../../CHANGELOG.md) · [SECURITY](../../SECURITY.md) · [CONTRIBUTING](../../CONTRIBUTING.md)

Guides: [Contributor guide](../CONTRIBUTOR_GUIDE.md) · [Installation](../INSTALLATION.md) · [Quickstart](QUICKSTART.md) · [Language](../LANGUAGE_GUIDE.md) · [Encodings](../ENCODINGS.md) · [Runtime](../RUNTIME.md) · [Generator](../GENERATOR.md) · [Architecture](../ARCHITECTURE.md) · [Compatibility](../COMPATIBILITY.md) · [Troubleshooting](../TROUBLESHOOTING.md) · [FAQ](../FAQ.md) · [Threat model](../THREAT_MODEL.md) · [Research status](../RESEARCH_STATUS.md)

Research: [overview](../research/README.md) · [Phantom C](../research/PHANTOM_C.md) · [Observability](../research/OBSERVABILITY.md) · [Method](../research/EXPERIMENTAL_METHOD.md)

## लाइसेंस

MIT — [LICENSE](../../LICENSE) देखें।
