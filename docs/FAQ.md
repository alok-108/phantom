# FAQ

**Do I need to import anything in my Python code?**
No. The host file contains no Phantom imports, decorators or wrappers. The instruction layer is comments (or whitespace/zero-width blocks).

**Does `python app.py` run the Phantom instructions?**
No. Stock Python treats them as comments/blank lines and runs only your code. The instructions take effect only through `phantom run app.py`. Phantom does not install import hooks, `sitecustomize` or any interpreter setting, and there is no mechanism in v0.1.0 to make plain `python` act on them.

**Does my code change when I use Phantom?**
`phantom run` launches your unmodified file as a subprocess. Phantom never edits it. `phantom generate` writes a *separate* candidate file only when you pass `--output`.

**Is the instruction layer executed where it is written?**
No. It is applied once, at initialisation, before the host starts. See [RUNTIME.md](RUNTIME.md).

**What can the instructions actually do?**
Declare events, register handlers for the three lifecycle events (`pre_execute`, `post_execute`, `shutdown`), keep bounded counters, record diagnostic notes, and record author/version metadata. It is deliberately small.

**Can Phantom hook into a specific function or line of my program?**
Not in v0.1.0.

**Why does `event.on` need a dotted path?**
Handlers are plain Python functions identified by `module.function`, imported when the event fires. That import executes the module's top-level code, so only run files you trust.

**Which encoding should I use?**
Comment encoding. Whitespace and zero-width encodings exist as supported formats but are fragile under formatters and normalisation; see [ENCODINGS.md](ENCODINGS.md).

**Is zero-width encoding secure or secret?**
No. It is not encryption and not access control. Reviewers can decode it with `phantom inspect`, and `phantom check --strict` flags unexpected invisible characters. Do not use encoding to protect secrets.

**Can Phantom hide code from antivirus tools or from administrators?**
That is not a goal and nothing here is designed or claimed to do so. See [research/PHANTOM_C.md](research/PHANTOM_C.md) for how the project treats visibility as a research question and why evasion is out of scope.

**What is Phantom C?**
A long-term *research vision* about dual-layer sources for compiled languages and about who can observe what. It is not implemented. See [research/PHANTOM_C.md](research/PHANTOM_C.md) and [RESEARCH_STATUS.md](RESEARCH_STATUS.md).

**Do I need an LLM or an API key?**
No. Parsing, validation, inspection and execution work offline. Only `phantom generate` uses a provider.

**Does `generate` send my code somewhere?**
Yes, to the configured remote provider (Gemini), which processes whatever you submit. It does so only after explicit consent (`--allow-remote` or an interactive `y`).

**Will the generated candidate behave identically to my program?**
The generator can only *insert* lines and checks that the Python AST is unchanged, which is strong evidence the host code is untouched. `phantom verify` additionally compares one run's output. Neither is a guarantee about all inputs or environments. The candidate may of course add Phantom effects you asked for.

**Does Phantom work with Python 3.9 or older?** No (`>= 3.10`).

**Why a subprocess for the host?**
Isolation of runtime state, precise capture of exit code and output, and a timeout. The trade-off is that Phantom cannot observe inside the host.
