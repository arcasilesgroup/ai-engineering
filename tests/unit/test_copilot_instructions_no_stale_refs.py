"""Guard `.github/copilot-instructions.md` against stale tool-list references (T-5.5/T-5.8).

Spec-101 removed the hardcoded ``_PIP_INSTALLABLE`` and ``_REQUIRED_TOOLS``
literals from installer/tools.py and doctor/phases/tools.py. The Copilot
instructions doc must not mention either symbol or any of the legacy
hardcoded tool-list shapes -- otherwise contributors and the model both end
up with stale guidance about how tool resolution actually works.

This test enforces G-10 (automation): any reintroduction of the old
identifiers in the Copilot doc fails CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COPILOT_DOC = _REPO_ROOT / ".github" / "copilot-instructions.md"

# Symbols that MUST NOT appear in the Copilot instructions.
# - ``_PIP_INSTALLABLE`` was the old installer tools.py literal.
# - ``_REQUIRED_TOOLS`` was the old doctor/phases/tools.py literal.
# - ``ruff, ty, gitleaks, semgrep, pip-audit`` was the legacy hardcoded
#   tool-list shape that now lives in manifest.yml > required_tools.
_FORBIDDEN_SYMBOLS: tuple[str, ...] = (
    "_PIP_INSTALLABLE",
    "_REQUIRED_TOOLS",
)

# Hardcoded tool-list patterns that drift from the manifest source of truth.
# We accept normal prose mentions of individual tools, but reject the legacy
# joined list shape.
_FORBIDDEN_HARDCODED_LIST_PATTERNS: tuple[str, ...] = (
    'ruff", "ty", "gitleaks", "semgrep", "pip-audit"',
    "ruff, ty, gitleaks, semgrep, pip-audit",
    'ruff", "ty", "gitleaks", "pip-audit"',
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCopilotInstructionsNoStaleRefs:
    """The Copilot doc must not carry stale spec-101 references."""

    def test_doc_exists(self) -> None:
        assert _COPILOT_DOC.exists(), (
            f"Copilot instructions must exist at {_COPILOT_DOC}; "
            "regenerate via `uv run ai-eng sync` if missing."
        )

    @pytest.mark.parametrize("symbol", _FORBIDDEN_SYMBOLS)
    def test_no_legacy_symbol(self, symbol: str) -> None:
        """No occurrences of the legacy install/doctor literal names."""
        text = _COPILOT_DOC.read_text(encoding="utf-8")
        assert symbol not in text, (
            f"`.github/copilot-instructions.md` must not contain {symbol!r}. "
            f"This identifier was removed in spec-101 -- the Copilot doc must "
            "instead point at `manifest.yml > required_tools` (the single source "
            "of truth)."
        )

    @pytest.mark.parametrize("pattern", _FORBIDDEN_HARDCODED_LIST_PATTERNS)
    def test_no_hardcoded_tool_list(self, pattern: str) -> None:
        """No legacy `ruff/ty/gitleaks/semgrep/pip-audit` joined list."""
        text = _COPILOT_DOC.read_text(encoding="utf-8")
        assert pattern not in text, (
            "`.github/copilot-instructions.md` contains a hardcoded tool-list "
            f"pattern: {pattern!r}. Drop the literal list and reference "
            "`.ai-engineering/manifest.yml > required_tools` instead."
        )
