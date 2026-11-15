"""Allow running phantom as: python -m phantom"""

from __future__ import annotations

import sys

from phantom.cli import main

if __name__ == "__main__":
    sys.exit(main())
