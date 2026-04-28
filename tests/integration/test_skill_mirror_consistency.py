"""RED skeleton for spec-105 Phase 7 -- skill mirror consistency.

Covers G-9: ``ai-eng sync --check`` PASS post-changes; espejos en
``.github/``, ``.codex/``, ``.gemini/`` regenerated consistent with
updated SKILL.md content (T-7.5..T-7.8 skill updates + T-7.13 sync).

Status: RED -- mirror regeneration lands in Phase 7 T-7.13 once the
skill SKILL.md edits + docs updates are in place. Marker
``pytest.mark.spec_105_red`` excludes from default CI run; will be
unmarked in Phase 7 T-7.17.
"""

from __future__ import annotations

import subprocess


def test_ai_eng_sync_check_returns_zero_post_phase_7() -> None:
    """G-9 -- ai-eng sync --check exits 0 after skill updates + sync run."""
    result = subprocess.run(
        ["uv", "run", "ai-eng", "sync", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"ai-eng sync --check failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
