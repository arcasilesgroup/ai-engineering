"""CLI entry point for canonical mirror synchronization.

Invoke with ``uv run python -m scripts.sync_mirrors [args]``.
"""

from __future__ import annotations

import sys

from scripts.sync_mirrors.core import main

if __name__ == "__main__":
    sys.exit(main())
