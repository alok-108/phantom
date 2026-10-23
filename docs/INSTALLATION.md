# Phantom Installation Guide

This guide provides step-by-step instructions for installing and verifying the Phantom language toolchain across Windows, macOS, and Linux.

---

## System Requirements

- **Python:** Version **3.10**, **3.11**, **3.12**, or **3.13**.
- **Operating System:**
  - Windows 10 / 11 / Server 2019+ (x86_64, ARM64)
  - macOS 12+ (Apple Silicon or Intel)
  - Linux (Ubuntu 20.04+, Debian 11+, Fedora 38+, Arch, etc.)
- **Character Encoding:** UTF-8 locale support is required.

---

## Supported Python Versions Matrix

| Python Version | Status | Notes |
| :--- | :--- | :--- |
| **Python 3.9 and older** | :x: Unsupported | Lacks modern typing and standard library features required by Phantom IR. |
| **Python 3.10** | :white_check_mark: Supported | Minimum version; passes the CI test matrix. |
| **Python 3.11** | :white_check_mark: Supported | Passes the CI test matrix. |
| **Python 3.12** | :white_check_mark: Supported | Passes the CI test matrix. |
| **Python 3.13** | :white_check_mark: Supported | The version the test suite was run on. |

---

## Virtual Environment Setup (Recommended)

Always install Phantom within an isolated Python virtual environment to prevent package version conflicts.

### On macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### On Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(If script execution is disabled on Windows, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first.)*

### On Windows (Command Prompt)
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

---

## Installation Methods

### Option 1: Standard Installation from Source
To install Phantom into your active Python environment:
```bash
# from the repository root (https://github.com/hayagrivai-labs/phantom); no package is published on PyPI
pip install .
```

### Option 2: Editable Development Installation
If you plan to modify Phantom or contribute code:
```bash
pip install -e ".[dev]"
```
This installs `pytest`, `pytest-cov`, and `ruff` in addition to the core `phantom` package.

### Option 3: Installation with LLM Generator Support
The optional generator talks to a remote LLM provider (Google Gemini). Installing the extra sends nothing anywhere; code is sent only when you run `phantom generate` and consent. To install the dependency:
```bash
pip install -e ".[llm]"
```
Or install all dependencies (both developer tools and LLM packages):
```bash
pip install -e ".[all]"
```
This pulls in `google-genai>=1.0.0`.

---

## Verifying the Installation

### 1. Verify the CLI
Run the `phantom` CLI to confirm that the entry point is available on your `PATH`:
```bash
phantom --help
```
Expected output:
```text
usage: phantom [-h] [--version] {check,inspect,run,generate,diff,verify} ...

Phantom dual-layer programming language CLI
```

### 2. Verify Python Import and Version
Check the library version directly from Python:
```bash
python -c "import phantom; print(phantom.__version__)"
```
Expected output:
```text
0.1.1
```

---

## Platform-Specific Notes

### Windows
- **UTF-8 Console Output:** PowerShell and Windows Command Prompt default to legacy code pages (e.g., CP437 or CP1252) on older systems. To ensure accurate rendering of Unicode zero-width diagnostics, set the UTF-8 code page:
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  ```
  Or set the environment variable:
  ```powershell
  $env:PYTHONUTF8 = "1"
  ```
- **Line Endings:** Phantom's parser handles both Windows CRLF (`\r\n`) and Unix LF (`\n`) line endings transparently.

### macOS
- **System Python vs. Homebrew:** Avoid modifying the macOS system Python (`/usr/bin/python3`). We recommend using a modern Python installed via Homebrew (`brew install python@3.12`) or `pyenv`.

### Linux
- **Header Packages:** When compiling CPython or installing virtual environments on minimal server distros (e.g., Alpine or Ubuntu Server), ensure `python3-venv` and `python3-pip` are installed:
  ```bash
  sudo apt-get install python3-venv python3-pip
  ```

---

## Troubleshooting Installation Issues

- **Command Not Found: `phantom`:** Ensure your virtual environment is activated (`which phantom` or `where.exe phantom`). If not using a virtual environment, ensure your user script directory (e.g., `~/.local/bin` or `%APPDATA%\Python\Python31x\Scripts`) is in your system's `PATH`.
- **Hatchling Build Failure:** Phantom uses `hatchling` as its build backend. Ensure `pip` is updated to the latest version:
  ```bash
  pip install --upgrade pip
  ```

---

## Next Steps

Now that Phantom is installed, continue to the [Quick Start Guide](QUICKSTART.md) to write and execute your first dual-layer program!
