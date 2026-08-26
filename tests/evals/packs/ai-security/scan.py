"""The ai-security reporter: what the skill must find in a planted pack.

A deterministic stand-in for a well-calibrated skill: it flags hard-coded secrets
(tier 1) and insecure env-var defaults that ship a live value (tier 2). It does NOT fire
on the redaction placeholder (tier 3 — the trap): `REDACTED = 'secret://…'` is correct code
that merely pattern-matches a secret, and a skill that reports it loses precision.
"""

from __future__ import annotations

from pathlib import Path


def find_findings(root: Path) -> list[dict]:
    out: list[dict] = []
    for path in sorted((root / "src").glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if "REDACTED = 'secret://" in src:
            # The trap: correct code that looks like a secret. A well-calibrated skill
            # sees the placeholder and stays quiet.
            continue
        if "secret://" in src:
            out.append({"file": f"src/{path.name}", "finding": "hard-coded secret"})
        elif "getenv(" in src and "root-default" in src:
            out.append({"file": f"src/{path.name}", "finding": "insecure default"})
    return out
