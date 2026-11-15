"""Build the README demo (docs/assets/demo.svg) and the social preview image.

The demo is rendered from the *real* output of the commands below, so it cannot drift from what
Phantom actually prints. Run from anywhere:

    python scripts/build_assets.py

The PNG needs Pillow (`pip install pillow`); the SVG needs nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"

DEMO = [
    ("python docs/examples/comments.py", [sys.executable, "docs/examples/comments.py"], None),
    ("phantom check docs/examples/comments.py", ["-m", "phantom", "check", "docs/examples/comments.py"], None),
    ("phantom run docs/examples/comments.py", ["-m", "phantom", "run", "docs/examples/comments.py"], None),
    (
        "phantom generate docs/examples/generation/program.py --intent annotate \\\n"
        "    --plan-file docs/examples/generation/plan.json --dry-run",
        [
            "-m", "phantom", "generate", "docs/examples/generation/program.py",
            "--intent", "annotate", "--plan-file", "docs/examples/generation/plan.json",
            "--dry-run",
        ],
        10,
    ),
]


def run(argv: list[str]) -> str:
    cmd = argv if argv[0] == sys.executable else [sys.executable, *argv]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
    done = subprocess.run(
        cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, timeout=60,
    )
    return (done.stdout + done.stderr).rstrip("\n")


def build_svg() -> None:
    lines: list[tuple[str, str]] = []  # (kind, text)
    for shown, argv, max_lines in DEMO:
        for i, part in enumerate(shown.split("\n")):
            lines.append(("cmd", ("$ " if i == 0 else "") + part))
        out = run(argv).splitlines()
        if max_lines is not None and len(out) > max_lines:
            out = out[:max_lines] + ["..."]
        lines.extend(("out", ln) for ln in out)
        lines.append(("out", ""))
    while lines and lines[-1][1] == "":
        lines.pop()

    char_w, line_h, pad_x, top = 8.4, 20, 24, 56
    width = int(max(len(t) for _, t in lines) * char_w + pad_x * 2)
    width = max(width, 720)
    height = top + len(lines) * line_h + 24

    rows = []
    for n, (kind, text) in enumerate(lines):
        y = top + (n + 1) * line_h - 6
        cls = "cmd" if kind == "cmd" else ("add" if text.startswith("+") and not text.startswith("+++")
                                           else "out")
        if kind == "cmd" and text.startswith("$ "):
            rows.append(
                f'<text x="{pad_x}" y="{y}" class="out"><tspan class="prompt">$ </tspan>'
                f'<tspan class="cmd">{escape(text[2:])}</tspan></text>'
            )
        else:
            rows.append(f'<text x="{pad_x}" y="{y}" class="{cls}" xml:space="preserve">{escape(text)}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Phantom terminal demo">
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace; font-size: 14px; white-space: pre; }}
    .out {{ fill: #c9d1d9; }}
    .cmd {{ fill: #ffffff; font-weight: 600; }}
    .prompt {{ fill: #3fb950; }}
    .add {{ fill: #3fb950; }}
  </style>
  <rect width="{width}" height="{height}" rx="10" fill="#0d1117"/>
  <rect width="{width}" height="36" rx="10" fill="#161b22"/>
  <rect y="26" width="{width}" height="10" fill="#161b22"/>
  <circle cx="22" cy="18" r="6" fill="#ff5f56"/><circle cx="42" cy="18" r="6" fill="#ffbd2e"/><circle cx="62" cy="18" r="6" fill="#27c93f"/>
  <text x="{width // 2}" y="23" text-anchor="middle" class="out" style="font-size:13px">phantom: ordinary Python + a second layer</text>
  {chr(10).join(rows)}
</svg>
"""
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "demo.svg").write_text(svg, encoding="utf-8", newline="\n")
    print("wrote docs/assets/demo.svg")


def _font(candidates: list[str], size: int):
    from PIL import ImageFont

    for name in candidates:
        for base in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"):
            path = Path(base) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def build_social_preview() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed; skipping social preview")
        return
    w, h = 1280, 640
    img = Image.new("RGB", (w, h), "#0d1117")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, h], fill="#7057ff")
    title = _font(["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 112)
    sub = _font(["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"], 40)
    mono = _font(["consola.ttf", "DejaVuSansMono.ttf", "Courier New.ttf"], 30)
    small = _font(["segoeui.ttf", "DejaVuSans.ttf"], 30)
    d.text((80, 70), "Phantom", font=title, fill="#ffffff")
    d.text((84, 215), "A second, structured layer for your Python code.", font=sub, fill="#c9d1d9")
    d.text((84, 270), "No imports. No decorators. Fully inspectable.", font=sub, fill="#8b949e")
    d.rounded_rectangle([84, 360, 1196, 540], radius=14, fill="#161b22", outline="#30363d")
    code = [
        ("def process_payment(amount):", "#c9d1d9"),
        ("    return amount > 0", "#c9d1d9"),
        ('#: phantom:0.1.0 counter.create("payments", 1000)', "#3fb950"),
        ('#: phantom:0.1.0 diagnostic.note("annotated")', "#3fb950"),
    ]
    for i, (text, color) in enumerate(code):
        d.text((116, 380 + i * 38), text, font=mono, fill=color)
    d.text((84, 570), "github.com/hayagrivai-labs/phantom   -   contributors welcome", font=small, fill="#8b949e")
    ASSETS.mkdir(parents=True, exist_ok=True)
    img.save(ASSETS / "social-preview.png", optimize=True)
    print("wrote docs/assets/social-preview.png")


if __name__ == "__main__":
    build_svg()
    build_social_preview()
