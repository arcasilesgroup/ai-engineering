"""Test guard for D-133-02: no `ai-eng guide` mentions in user-facing CLI strings.

Companion to ``test_d133_02_guide_deleted.py``. That guard checks the CLI
registry; this one scans the production source tree for residual textual
references that would point a shell operator at a command that no longer
exists. Together they close the loop on D-133-02 (`ai-eng guide` hard-deleted
in favour of the `/ai-onboard` skill).

Scope: every ``.py`` file under ``src/ai_engineering/`` must be free of
the literal substring ``ai-eng guide``. Any such occurrence — whether in
a string literal, an f-string, or a comment — fails the guard. Test files
and historical specs are intentionally excluded.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src" / "ai_engineering"
_FORBIDDEN = "ai-eng guide"


def test_no_ai_eng_guide_references_in_src() -> None:
    """No `.py` file under ``src/ai_engineering/`` may mention `ai-eng guide`."""
    offenders: list[tuple[Path, int, str]] = []
    for path in _SRC_ROOT.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _FORBIDDEN not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN in line:
                offenders.append((path.relative_to(_REPO_ROOT), lineno, line.strip()))

    assert not offenders, (
        "D-133-02 violated — `ai-eng guide` referenced in production source. "
        "The command was hard-deleted; point users at /ai-onboard (in your AI surface) "
        "or the install-state.json branch_policy.manual_guide field instead. "
        "Offending sites:\n" + "\n".join(f"  {p}:{ln}: {snippet}" for p, ln, snippet in offenders)
    )
