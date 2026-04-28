"""RED skeleton for spec-107 G-8 (Phase 4) — Sentinel runtime IOC matching.

Spec-107 D-107-06 extends `.ai-engineering/scripts/hooks/prompt-injection-guard.py`
with a `load_iocs()` loader and a 3-valued evaluator that matches payload
content against four IOC categories vendored from claude-mcp-sentinel:

- ``sensitive_paths`` — path patterns like ``~/.ssh``, ``~/.aws/credentials``
- ``sensitive_env_vars`` — env var names like ``AWS_SECRET_ACCESS_KEY``
- ``malicious_domains`` — known C2 / data-exfil endpoints
- ``shell_patterns`` — dangerous shell idioms like ``curl ... | bash``

Decision protocol:
- No IOC match → ``allow``.
- IOC match without active risk-acceptance → ``deny`` (default-deny stance).
- IOC match WITH active risk-acceptance → ``warn`` (allow execution + log
  audit event for compliance trace). Covered separately in
  ``test_sentinel_risk_accept.py`` (G-9).

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 4 lands the GREEN implementation. They are the
acceptance contract for T-4.1 / T-4.4 / T-4.5 / T-4.6 / T-4.7 /
T-4.8 / T-4.9 / T-4.10.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
IOCS_PATH = REPO_ROOT / ".ai-engineering" / "references" / "iocs.json"
ATTRIBUTION_PATH = REPO_ROOT / ".ai-engineering" / "references" / "IOCS_ATTRIBUTION.md"
HOOK_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"


@pytest.mark.spec_107_red
def test_iocs_catalog_vendored() -> None:
    """G-8 prerequisite: `references/iocs.json` ships vendored from upstream."""
    assert IOCS_PATH.is_file(), (
        f"IOC catalog missing: {IOCS_PATH} — Phase 4 T-4.1 must vendor "
        "iocs.json verbatim from claude-mcp-sentinel"
    )


@pytest.mark.spec_107_red
def test_iocs_attribution_documented() -> None:
    """G-8 prerequisite: vendored catalog needs IOCS_ATTRIBUTION.md provenance."""
    assert ATTRIBUTION_PATH.is_file(), (
        f"attribution missing: {ATTRIBUTION_PATH} — Phase 4 T-4.2 must "
        "document upstream URL, vendor commit hash, and license terms"
    )


@pytest.mark.spec_107_red
def test_iocs_schema_four_categories() -> None:
    """G-8 prerequisite: vendored catalog preserves the 4-category schema."""
    import json

    assert IOCS_PATH.is_file(), "preconditions: iocs.json must exist first"
    payload = json.loads(IOCS_PATH.read_text(encoding="utf-8"))
    expected_categories = {
        "sensitive_paths",
        "sensitive_env_vars",
        "malicious_domains",
        "shell_patterns",
    }
    found = {key for key in payload if key in expected_categories}
    missing = expected_categories - found
    assert not missing, (
        f"vendored iocs.json missing categories: {sorted(missing)}; "
        "spec-107 D-107-05 requires verbatim 4-category schema preserved"
    )


@pytest.mark.spec_107_red
def test_hook_exposes_load_iocs_fail_open() -> None:
    """G-8: hook ships `load_iocs()` that fails open on missing/corrupt file."""
    assert HOOK_PATH.is_file(), f"hook missing: {HOOK_PATH}"
    text = HOOK_PATH.read_text(encoding="utf-8")
    assert "def load_iocs(" in text, (
        "prompt-injection-guard.py missing `load_iocs()` — Phase 4 T-4.4 "
        "must add the loader with fail-open semantics (return {} on miss)"
    )


@pytest.mark.spec_107_red
def test_hook_evaluates_against_iocs_three_valued() -> None:
    """G-8: hook ships an evaluator returning ``allow|deny|warn``."""
    assert HOOK_PATH.is_file()
    text = HOOK_PATH.read_text(encoding="utf-8")
    # The function name is the spec-mandated `evaluate_against_iocs`; the
    # evaluator must return one of three string verdicts.
    assert "evaluate_against_iocs" in text, (
        "prompt-injection-guard.py missing `evaluate_against_iocs()` — "
        "Phase 4 T-4.5 / T-4.6 must add the matcher returning allow|deny|warn"
    )
    for verdict in ("allow", "deny", "warn"):
        assert verdict in text, (
            f"hook does not reference `{verdict}` verdict; D-107-06 requires "
            "all three decision values"
        )


@pytest.mark.spec_107_red
def test_hook_canonical_finding_id_format() -> None:
    """G-8: hook computes canonical `sentinel-<category>-<pattern>` finding-id."""
    assert HOOK_PATH.is_file()
    text = HOOK_PATH.read_text(encoding="utf-8")
    assert "sentinel-" in text, (
        "prompt-injection-guard.py missing canonical finding_id format — "
        'Phase 4 T-4.7 must compute `f"sentinel-{category}-{pattern}"` for '
        "risk-accept lookups"
    )


@pytest.mark.spec_107_red
def test_hook_template_byte_equivalent() -> None:
    """G-8: install template hook stays byte-equivalent to canonical."""
    template_path = (
        REPO_ROOT
        / "src"
        / "ai_engineering"
        / "templates"
        / ".ai-engineering"
        / "scripts"
        / "hooks"
        / "prompt-injection-guard.py"
    )
    assert template_path.is_file(), (
        f"template hook missing: {template_path} — Phase 4 T-4.8 must "
        "mirror the canonical hook into the install template"
    )
    canonical_text = HOOK_PATH.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")
    assert canonical_text == template_text, (
        "template hook drifted from canonical; spec-107 requires byte-equiv "
        "between .ai-engineering/scripts/hooks/ and templates/.ai-engineering/scripts/hooks/"
    )
