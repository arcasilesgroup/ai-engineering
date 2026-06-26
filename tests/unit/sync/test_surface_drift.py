"""Fail-loud surface-drift guard for sync_mirrors (spec-159 T-2 / D-159-08).

The framework keeps a canonical authoring copy of every installable surface
at the repo root and a packaged install-template copy under
``src/ai_engineering/templates/``. ``scripts/sync_mirrors/core.py`` is the
generation pipeline that must keep template == canonical.

Before spec-159 three surface classes drifted *invisibly* because the
pipeline had no sync step (or generated the wrong content) for them:

1. ``.ai-engineering/scripts/hooks/**/*.py`` (incl. ``_lib/``) had no sync
   step at all -- 16 files perpetually drifted (D-159-04).
2. ``generate_specialist_agent`` injected provenance frontmatter into the
   ``.claude/agents/*`` install template that the canonical source lacks,
   guaranteeing a permanent byte mismatch (D-159-05).

This module asserts byte-parity for those framework-managed surfaces *and*
that ``sync_all(check_only=True)`` reports clean. It is the fail-loud signal:
any future surface edit that is not propagated into the install template
turns this red, naming ``python scripts/sync_mirrors/core.py`` as the remedy.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_REMEDY = "run: python scripts/sync_mirrors/core.py"


def test_sync_all_check_mode_reports_clean(template_hooks_lock) -> None:
    """``sync_all(check_only=True)`` must exit 0 -- no tracked drift."""
    from scripts.sync_command_mirrors import sync_all

    with template_hooks_lock():  # serialize vs test_orphan_* probe writes
        exit_code = sync_all(check_only=True)
    assert exit_code == 0, f"Mirror drift detected -- {_REMEDY}"


def test_hook_scripts_template_matches_canonical() -> None:
    """Every canonical hook ``.py`` (incl. ``_lib/``) is byte-identical in template."""
    from scripts.sync_command_mirrors import ROOT

    canonical_root = ROOT / ".ai-engineering" / "scripts" / "hooks"
    template_root = (
        ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts" / "hooks"
    )

    drifted: list[str] = []
    for src_file in sorted(canonical_root.rglob("*.py")):
        if "__pycache__" in src_file.parts:
            continue
        relative = src_file.relative_to(canonical_root)
        tpl_file = template_root / relative
        if not tpl_file.exists():
            drifted.append(f"MISSING: {relative}")
            continue
        if src_file.read_bytes() != tpl_file.read_bytes():
            drifted.append(f"DRIFT: {relative}")

    assert not drifted, (
        f"Hook-script install templates drifted from canonical ({_REMEDY}):\n" + "\n".join(drifted)
    )


def test_specialist_agent_claude_template_carries_provenance() -> None:
    """``.claude/agents/*`` install templates are GENERATED mirrors with provenance.

    spec-159 D-159-05 (corrected): the specialist ``.claude`` *install template*
    carries governed provenance frontmatter (canonical body + provenance),
    enforced by ``validator/_check_claude_specialist_agents_mirror``. Only the
    authored canonical ``.claude/agents/<name>.md`` source is provenance-free.
    An earlier draft wrote the template verbatim; that violated the mirror-sync
    governance contract and was reverted. Each template must match
    ``generate_specialist_agent`` output byte-for-byte.
    """
    from scripts.sync_command_mirrors import (
        TPL_CLAUDE_AGENTS,
        discover_specialist_agents,
        generate_specialist_agent,
    )

    drifted: list[str] = []
    for specialist_path in discover_specialist_agents():
        tpl_file = TPL_CLAUDE_AGENTS / specialist_path.name
        if not tpl_file.exists():
            drifted.append(f"MISSING: {specialist_path.name}")
            continue
        expected = generate_specialist_agent(specialist_path)
        if tpl_file.read_text(encoding="utf-8") != expected:
            drifted.append(f"DRIFT: {specialist_path.name}")
        # Canonical authoring source stays provenance-free.
        if "mirror_family: specialist-agents" in specialist_path.read_text(encoding="utf-8"):
            drifted.append(f"CANONICAL-HAS-PROVENANCE: {specialist_path.name}")

    assert not drifted, (
        f"Specialist-agent .claude install templates desynced from the generated "
        f"provenance form ({_REMEDY}):\n" + "\n".join(drifted)
    )


def test_orphan_py_in_template_hooks_is_flagged_but_launchers_are_safe(
    template_hooks_lock,
) -> None:
    """spec-159 D-159-04: orphan cleanup of the template hooks subtree is
    scoped to ``*.py`` ONLY.

    (a) A stray ``.py`` that the sync step does not own is reported as an
        orphan by ``--check``.
    (b) ``.sh``/``.ps1`` launchers living in the same tree are NEVER orphan
        candidates -- they are a separate packaging concern and must survive.
    """
    from scripts.sync_command_mirrors import TPL_HOOK_SCRIPTS, sync_all
    from scripts.sync_mirrors.core import _handle_orphans

    TPL_HOOK_SCRIPTS.mkdir(parents=True, exist_ok=True)
    stray_py = TPL_HOOK_SCRIPTS / "spec159_stray_orphan_probe.py"
    stray_sh = TPL_HOOK_SCRIPTS / "spec159_stray_launcher_probe.sh"
    stray_ps1 = TPL_HOOK_SCRIPTS / "spec159_stray_launcher_probe.ps1"
    created = [stray_py, stray_sh, stray_ps1]
    # Hold the cross-process mutex for the whole probes-on-disk window so a
    # parallel worker running test_template_parity cannot read the shared
    # template hooks dir mid-write (spec-181 follow-up: parallel-isolation race).
    _lock = template_hooks_lock()
    _lock.__enter__()
    try:
        stray_py.write_text("# stray\n", encoding="utf-8")
        stray_sh.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        stray_ps1.write_text("# launcher\n", encoding="utf-8")

        # Build the full generated set the way a real sync does, then run
        # orphan detection in check-only mode (non-destructive).
        from scripts.sync_mirrors import core as _core

        # Populate `generated` exactly as Surface 10 does so the legitimate
        # synced `.py` files are NOT mis-reported as orphans.
        generated: set[Path] = set()
        canonical_root = _core.ROOT / ".ai-engineering" / "scripts" / "hooks"
        for src_file in canonical_root.rglob("*.py"):
            if "__pycache__" in src_file.parts:
                continue
            generated.add(TPL_HOOK_SCRIPTS / src_file.relative_to(canonical_root))

        diffs = _handle_orphans(generated, check_only=True, verbose=False)

        # (a) the stray `.py` is flagged as an orphan.
        py_rel = stray_py.relative_to(_core.ROOT)
        assert any(f"ORPHAN: {py_rel}" == d for d in diffs), (
            f"stray template hook .py was not reported as orphan; diffs={diffs}"
        )

        # (b) the `.sh`/`.ps1` launchers are NOT orphan candidates.
        sh_rel = stray_sh.relative_to(_core.ROOT)
        ps1_rel = stray_ps1.relative_to(_core.ROOT)
        assert not any(str(sh_rel) in d for d in diffs), (
            f".sh launcher must never be an orphan candidate; diffs={diffs}"
        )
        assert not any(str(ps1_rel) in d for d in diffs), (
            f".ps1 launcher must never be an orphan candidate; diffs={diffs}"
        )

        # The launchers must still exist on disk after a check-mode pass.
        assert stray_sh.exists() and stray_ps1.exists()

        # Belt-and-suspenders: a full check-mode sync_all flags the stray `.py`
        # (proves it is wired into the surface registry, not just the helper).
        assert sync_all(check_only=True) == 1
        assert stray_sh.exists() and stray_ps1.exists()
    finally:
        for probe in created:
            if probe.exists():
                probe.unlink()
        _lock.__exit__(None, None, None)
