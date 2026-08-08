"""Runs the repository's formatter over a file that was just written.

Telemetry, not a control: it blocks nothing and it opines about nothing. If it crashes
the edit still stands, and the decorator's name is the only documentation of that fact
anyone needs. 1,232 firings and zero failures in the estate — genuinely useful, and
still not a guard.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from _wrap import telemetry

FORMATTERS = {
    ".py": ["ruff", "format", "--quiet"],
    ".pyi": ["ruff", "format", "--quiet"],
    ".ts": ["prettier", "--write", "--log-level", "silent"],
    ".tsx": ["prettier", "--write", "--log-level", "silent"],
    ".js": ["prettier", "--write", "--log-level", "silent"],
    ".jsx": ["prettier", "--write", "--log-level", "silent"],
    ".json": ["prettier", "--write", "--log-level", "silent"],
    ".css": ["prettier", "--write", "--log-level", "silent"],
    ".md": ["prettier", "--write", "--log-level", "silent"],
    ".go": ["gofmt", "-w"],
    ".rs": ["rustfmt", "--edition", "2021"],
}


@telemetry("autoformat")
def run(payload: dict) -> None:
    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target:
        return
    path = Path(str(target))
    recipe = FORMATTERS.get(path.suffix)
    if not recipe or not path.is_file() or shutil.which(recipe[0]) is None:
        return
    subprocess.run([*recipe, str(path)], capture_output=True, timeout=10)
