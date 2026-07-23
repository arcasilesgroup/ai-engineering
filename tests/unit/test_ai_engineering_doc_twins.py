"""Byte-parity + sync-drift guard for the ``.ai-engineering`` doc twins.

spec-187 follow-up (doc-twin root fix). The installer ships the
``.ai-engineering/{reference,runbooks}/**.md`` docs to consumers verbatim via
the template tree at ``src/ai_engineering/templates/.ai-engineering/**``. Before
Surface 11 of the mirror sync, no propagation path existed, so a canonical edit
silently drifted the packaged twin — caught only by full-suite parity tests and
hand-``cp``'d every wave. ``ai-eng dev sync`` now regenerates these twins.

These tests assert the invariant from both ends:

* every canonical doc is byte-identical to its install-template twin (steady
  state that ``dev sync`` maintains), and
* a hand-drifted twin is caught by ``sync_all(check_only=True)`` (so CI's
  ``--check`` gate fails loudly rather than shipping stale content).

The allowlist mirrors ``scripts.sync_mirrors.core._DOC_TWIN_SUBTREES`` — only
``reference/`` and ``runbooks/`` are verbatim mirrors; sibling trees such as
``overrides/``, ``specs/``, and ``LESSONS.md`` are intentionally divergent
(generic starter template / placeholder / project state) and are NOT synced.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL = _ROOT / ".ai-engineering"
_TWIN = _ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering"

# Kept in lockstep with scripts.sync_mirrors.core._DOC_TWIN_SUBTREES.
_DOC_TWIN_SUBTREES = ("reference", "runbooks")


def _norm(path: Path) -> bytes:
    """CRLF-normalized bytes so Windows checkouts do not spuriously differ."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def _canonical_docs() -> list[Path]:
    docs: list[Path] = []
    for subtree in _DOC_TWIN_SUBTREES:
        docs.extend(sorted((_CANONICAL / subtree).rglob("*.md")))
    return docs


def test_allowlist_matches_sync_source() -> None:
    """This test's allowlist must equal the sync's, or coverage silently drifts."""
    from scripts.sync_mirrors.core import _DOC_TWIN_SUBTREES as sync_subtrees

    assert tuple(sync_subtrees) == _DOC_TWIN_SUBTREES


def test_doc_twins_byte_identical() -> None:
    """Every canonical reference/runbooks doc equals its install-template twin.

    This is the steady state ``ai-eng dev sync`` maintains; a mismatch means a
    canonical edit never reached the twin (re-run ``ai-eng dev sync``).
    """
    docs = _canonical_docs()
    assert docs, "no canonical docs discovered — allowlist or tree is wrong"

    mismatches: list[str] = []
    for canonical in docs:
        rel = canonical.relative_to(_CANONICAL)
        twin = _TWIN / rel
        if not twin.is_file():
            mismatches.append(f"MISSING twin: {rel}")
        elif _norm(canonical) != _norm(twin):
            mismatches.append(f"DRIFT: {rel}")

    assert not mismatches, (
        "doc-twin drift between .ai-engineering/ and the installer template at "
        "src/ai_engineering/templates/.ai-engineering/ — run `ai-eng dev sync`:\n  "
        + "\n  ".join(mismatches)
    )


def test_no_orphan_doc_twins() -> None:
    """No install-template twin exists without a canonical source.

    Guards the reverse direction: a deleted/renamed canonical doc must not leave
    a stale twin shipping in the wheel (Surface 11 orphan cleanup enforces this).
    """
    orphans: list[str] = []
    for subtree in _DOC_TWIN_SUBTREES:
        for twin in sorted((_TWIN / subtree).rglob("*.md")):
            rel = twin.relative_to(_TWIN)
            if not (_CANONICAL / rel).is_file():
                orphans.append(str(rel))
    assert not orphans, (
        "orphan doc twin(s) with no canonical source — run `ai-eng dev sync`:\n  "
        + "\n  ".join(orphans)
    )


def test_drift_caught_by_sync_check(template_hooks_lock) -> None:
    """A hand-drifted twin makes ``sync_all(check_only=True)`` return 1.

    Holds the shared template mutex so the drift window never overlaps another
    worker asserting the global sync surface clean (see conftest fixture).
    """
    from scripts.sync_mirrors import sync_all

    twin = _TWIN / "reference" / "value-lens.md"
    assert twin.is_file(), "fixture twin missing — pick another allowlisted doc"
    original = twin.read_bytes()

    with template_hooks_lock():
        assert sync_all(check_only=True) == 0, "baseline sync surface is not clean"
        try:
            twin.write_bytes(original + b"\n<!-- doc-twin drift probe -->\n")
            assert sync_all(check_only=True) == 1, "sync --check did not flag the drifted doc twin"
        finally:
            twin.write_bytes(original)
        assert sync_all(check_only=True) == 0, "restore did not return the surface to clean"
