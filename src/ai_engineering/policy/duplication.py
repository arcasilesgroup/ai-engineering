"""Lightweight duplication check used by pre-push gate.

Computes duplicated 8-line normalized windows across Python files and fails when
the duplicated-window ratio exceeds a threshold percentage.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path


def _normalized_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    result: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        result.append(line)
    return result


def _window_hashes(lines: list[str], width: int = 8) -> list[str]:
    if len(lines) < width:
        return []
    hashes: list[str] = []
    for i in range(0, len(lines) - width + 1):
        block = "\n".join(lines[i : i + width]).encode("utf-8")
        hashes.append(hashlib.sha256(block).hexdigest())
    return hashes


def _duplication_ratio(path: Path) -> tuple[float, int, int]:
    all_hashes: list[str] = []
    for py_file in sorted(path.rglob("*.py")):
        if py_file.name.startswith("test_"):
            continue
        all_hashes.extend(_window_hashes(_normalized_lines(py_file)))

    total = len(all_hashes)
    if total == 0:
        return 0.0, 0, 0

    counts = Counter(all_hashes)
    duplicate_instances = sum(count - 1 for count in counts.values() if count > 1)
    ratio = (duplicate_instances / total) * 100.0
    return ratio, duplicate_instances, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Check duplication ratio in Python source")
    parser.add_argument("--path", default="src/ai_engineering")
    parser.add_argument("--threshold", type=float, default=3.0)
    args = parser.parse_args()

    root = Path(args.path)
    ratio, duplicate_instances, total = _duplication_ratio(root)
    if ratio > args.threshold:
        print(
            "duplication-check failed: "
            f"{ratio:.2f}% duplicated windows ({duplicate_instances}/{total}) "
            f"> threshold {args.threshold:.2f}%"
        )
        return 1

    print(
        "duplication-check passed: "
        f"{ratio:.2f}% duplicated windows ({duplicate_instances}/{total}) "
        f"<= threshold {args.threshold:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
