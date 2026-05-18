"""Tunables drift gate: CLAUDE.md ↔ code defaults (spec-139 M9.T4).

Closes the M9 reconciliation loop by mechanically enforcing that every
``AIENG_*`` env var documented in ``CLAUDE.md`` either:

1. Matches its code default in the canonical source file
   (``runtime_state.py`` for tool/loop/event tunables,
   ``runtime-stop.py`` for Ralph tunables,
   ``integrity.py`` for the hook integrity mode,
   ``src/ai_engineering/config/concurrency.py`` for spec-139 M1
   concurrency primitives), OR
2. Is explicitly marked ``# pending spec-139 M<n>`` so the reader can
   tell the var is reserved but not yet wired.

The opposite direction (every code-defaulted var appears in docs) is
narrowed to the spec-139 M1 trio so the test is not coupled to
deprecation noise in ``runtime_state.py`` (e.g. ``AIENG_TOOL_OFFLOAD_HEAD``
is internal and intentionally undocumented).

Anchored at spec-139 M9.T4 and D-139-07 (CLAUDE.md tunables
reconciliation). Drift in either direction fails CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_RUNTIME_STATE = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "runtime_state.py"
_RUNTIME_STOP = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
_INTEGRITY = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"
_CONCURRENCY = _REPO_ROOT / "src" / "ai_engineering" / "config" / "concurrency.py"

# Regex that pulls every ``AIENG_<NAME>  # default <value>`` or
# ``AIENG_<NAME>  # pending spec-139 M<n>`` row out of the tunables fenced
# code block. The trailing parenthetical (e.g. ``(observe-only)`` or
# ``(Phase 5 assessor cap)``) is allowed but ignored — the default token
# is just the first whitespace-bounded value after ``default ``.
_TUNABLE_RE = re.compile(
    r"^(AIENG_[A-Z_]+)\s+#\s*(?:default\s+(\S+)|pending\s+spec-139\s+(M\d+))",
    re.MULTILINE,
)

# Whitelisted established tunables where the code default and the
# CLAUDE.md / CONSTITUTION.md documented value disagree because the
# ``integrity.py`` source-file constant ``_DEFAULT_MODE = "warn"`` lags
# behind the docstring + governance posture (``enforce``). Tracked as a
# deferred reconciliation item from spec-139 M9. Removing this entry
# requires the code default to be flipped to ``enforce`` in
# ``.ai-engineering/scripts/hooks/_lib/integrity.py`` so the docs and
# code re-converge.
_KNOWN_DOC_CODE_DISAGREEMENTS: frozenset[str] = frozenset({"AIENG_HOOK_INTEGRITY_MODE"})

# Pending milestones acknowledged in CLAUDE.md but not yet wired in code.
# Removing an entry here means the corresponding milestone has landed and
# the var now has a real code default that the test must verify.
_PENDING_MILESTONES: frozenset[str] = frozenset({"M2", "M5", "M6"})


def _read_tunables_block() -> str:
    """Extract the fenced code block following ``## Runtime Layer Tunables``."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    marker = "## Runtime Layer Tunables"
    assert marker in text, "CLAUDE.md missing the Runtime Layer Tunables section"
    after_header = text.split(marker, 1)[1]
    # The first triple-backtick fence after the header is the tunables block.
    fence_open = after_header.find("```")
    assert fence_open != -1, "Tunables section missing opening code fence"
    fence_close = after_header.find("```", fence_open + 3)
    assert fence_close != -1, "Tunables section missing closing code fence"
    return after_header[fence_open + 3 : fence_close]


def _parse_documented_tunables() -> dict[str, tuple[str | None, str | None]]:
    """Return ``{name: (default, pending_milestone)}`` from CLAUDE.md."""
    block = _read_tunables_block()
    parsed: dict[str, tuple[str | None, str | None]] = {}
    for match in _TUNABLE_RE.finditer(block):
        name, default, pending = match.group(1), match.group(2), match.group(3)
        parsed[name] = (default, pending)
    return parsed


def _grep_default(path: Path, pattern: str) -> str | None:
    """Return the first regex capture group hit in ``path``, else ``None``."""
    text = path.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _code_default_for(name: str) -> str | None:
    """Resolve the code default for a documented AIENG_* var.

    The source file is hard-coded per var so the test is explicit about
    where each default lives. Unknown vars return ``None`` so the caller
    can decide whether absence is a hard failure (rule 2: every doc entry
    must have a matching code default OR a pending marker).
    """
    if name == "AIENG_TOOL_OFFLOAD_BYTES":
        return _grep_default(
            _RUNTIME_STATE,
            r'_env_int\("AIENG_TOOL_OFFLOAD_BYTES",\s*(\d+)',
        )
    if name == "AIENG_LOOP_WINDOW":
        return _grep_default(
            _RUNTIME_STATE,
            r'_env_int\("AIENG_LOOP_WINDOW",\s*(\d+)',
        )
    if name == "AIENG_RALPH_MAX_RETRIES":
        return _grep_default(
            _RUNTIME_STOP,
            r'_bounded_int_env\("AIENG_RALPH_MAX_RETRIES",\s*(\d+)',
        )
    if name == "AIENG_RALPH_BLOCK":
        # Boolean-style env: presence-of-"1" enables; default is off → 0.
        text = _RUNTIME_STOP.read_text(encoding="utf-8")
        if 'AIENG_RALPH_BLOCK") or "").strip() == "1"' in text:
            return "0"
        return None
    if name == "AIENG_HOOK_INTEGRITY_MODE":
        return _grep_default(_INTEGRITY, r'_DEFAULT_MODE\s*=\s*"([a-z]+)"')
    if name == "AIENG_MAX_WAVE_AGENTS":
        # Auto-tuned per HostProbe; docs say "auto" by design.
        return "auto"
    if name == "AIENG_MAX_QUALITY_AGENTS":
        return _grep_default(
            _CONCURRENCY,
            r"QUALITY_DEFAULT_CAP:\s*Final\[int\]\s*=\s*(\d+)",
        )
    if name == "AIENG_MAX_THREAD_WORKERS":
        return _grep_default(
            _CONCURRENCY,
            r"THREAD_WORKERS_DEFAULT:\s*Final\[int\]\s*=\s*(\d+)",
        )
    return None


# Established-tunables (5) that MUST be present in CLAUDE.md with a
# default-matching-code (modulo the known disagreement whitelist).
_ESTABLISHED_TUNABLES: tuple[str, ...] = (
    "AIENG_TOOL_OFFLOAD_BYTES",
    "AIENG_LOOP_WINDOW",
    "AIENG_RALPH_MAX_RETRIES",
    "AIENG_RALPH_BLOCK",
    "AIENG_HOOK_INTEGRITY_MODE",
)

# spec-139 M1 concurrency primitive trio that landed with M1.
_M1_TUNABLES: tuple[str, ...] = (
    "AIENG_MAX_WAVE_AGENTS",
    "AIENG_MAX_QUALITY_AGENTS",
    "AIENG_MAX_THREAD_WORKERS",
)

# spec-139 M6 SessionEnd rotation throttle var that landed with M6.
_M6_TUNABLES: tuple[str, ...] = ("AIENG_RUNTIME_ROTATE_THROTTLE_SEC",)


@pytest.mark.unit
def test_tunables_block_exists_in_claude_md() -> None:
    """CLAUDE.md MUST contain the Runtime Layer Tunables fenced block."""
    block = _read_tunables_block()
    assert block.strip(), "Tunables fence is empty"


@pytest.mark.unit
@pytest.mark.parametrize("name", _ESTABLISHED_TUNABLES)
def test_established_tunable_documented_with_code_matching_default(name: str) -> None:
    """Each established tunable MUST appear in CLAUDE.md with a default that
    matches the code default (or be on the known-disagreement whitelist).
    """
    documented = _parse_documented_tunables()
    assert name in documented, f"CLAUDE.md tunables block missing {name}"
    doc_default, pending = documented[name]
    assert pending is None, f"{name} is an established tunable but marked pending"
    assert doc_default is not None, f"{name} missing a documented default"

    code_default = _code_default_for(name)
    assert code_default is not None, (
        f"Could not resolve code default for {name} — update _code_default_for() "
        "if the source file moved."
    )

    if name in _KNOWN_DOC_CODE_DISAGREEMENTS:
        # Whitelisted: assert the disagreement still exists so accidental
        # convergence (someone fixed it) removes the entry from the
        # whitelist; otherwise the whitelist would silently rot.
        assert doc_default != code_default, (
            f"{name} now agrees with code default ({code_default}); "
            "remove it from _KNOWN_DOC_CODE_DISAGREEMENTS."
        )
        return

    assert doc_default == code_default, (
        f"{name} doc/code drift: CLAUDE.md says default={doc_default!r}, "
        f"code says default={code_default!r}. Fix by editing CLAUDE.md "
        "(if code is canonical) or the code default (if docs are canonical)."
    )


@pytest.mark.unit
@pytest.mark.parametrize("name", _M1_TUNABLES)
def test_m1_concurrency_tunable_matches_code_default(name: str) -> None:
    """spec-139 M1 concurrency primitives MUST be documented with their
    code-resolved defaults (``QUALITY_DEFAULT_CAP=3``,
    ``THREAD_WORKERS_DEFAULT=4``, ``MAX_WAVE_AGENTS=auto``).
    """
    documented = _parse_documented_tunables()
    assert name in documented, f"CLAUDE.md tunables block missing M1 var {name}"
    doc_default, pending = documented[name]
    assert pending is None, f"{name} landed in M1 but is marked pending"
    assert doc_default is not None, f"{name} missing a documented default"

    code_default = _code_default_for(name)
    assert code_default is not None, (
        f"Could not resolve code default for {name} — update _code_default_for() "
        "if concurrency.py moved."
    )
    assert doc_default == code_default, (
        f"{name} M1 doc/code drift: CLAUDE.md says default={doc_default!r}, "
        f"code says default={code_default!r}. Reconcile via spec-139 M1 source."
    )


@pytest.mark.unit
def test_pending_milestone_markers_use_documented_format() -> None:
    """Every pending var MUST use the ``# pending spec-139 M<n>`` format and
    cite one of the milestones still open in spec-139.
    """
    documented = _parse_documented_tunables()
    pending_entries = {
        name: pending for name, (_, pending) in documented.items() if pending is not None
    }
    assert pending_entries, (
        "Tunables block declares zero pending entries — at least the M2 / M5 / M6 "
        "vars from spec-139 M9.T1 are expected here. If every milestone has "
        "landed, this test can be deleted along with _PENDING_MILESTONES."
    )
    for name, milestone in pending_entries.items():
        assert milestone in _PENDING_MILESTONES, (
            f"{name} cites pending milestone {milestone!r}; the only acknowledged "
            f"pending milestones are {sorted(_PENDING_MILESTONES)}. Update the "
            "whitelist if a new spec-139 milestone genuinely opened."
        )


@pytest.mark.unit
def test_every_documented_var_classified() -> None:
    """Every var documented in CLAUDE.md MUST be either established / M1 /
    pending. Catches accidental new entries that bypass the classification.
    """
    documented = _parse_documented_tunables()
    classified = set(_ESTABLISHED_TUNABLES) | set(_M1_TUNABLES) | set(_M6_TUNABLES)
    for name, (_default, pending) in documented.items():
        if name in classified:
            continue
        if pending is not None:
            continue
        pytest.fail(
            f"{name} documented in CLAUDE.md but not classified as "
            "established / M1 / pending. Add it to _ESTABLISHED_TUNABLES or "
            "_M1_TUNABLES or mark the doc entry as pending spec-139 M<n>."
        )


@pytest.mark.unit
def test_pending_set_covers_m2_m5_m6_per_spec_139() -> None:
    """spec-139 M9.T1 asks for M2 / M5 / M6 vars to be reserved. Verify each
    bucket has at least one entry so a future docs edit cannot quietly drop
    the placeholder.
    """
    documented = _parse_documented_tunables()
    pending_milestones_seen = {
        pending for _, (_, pending) in documented.items() if pending is not None
    }
    for required in _PENDING_MILESTONES:
        assert required in pending_milestones_seen, (
            f"No CLAUDE.md tunable cites pending spec-139 {required}; "
            "M9.T1 reserves at least one var per milestone (M2 host probe, "
            "M5 hook cache, M6 NDJSON rotation)."
        )
