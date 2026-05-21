"""Tunables drift gate: CLAUDE.md ↔ code defaults (spec-139 M9.T4).

Closes the M9 reconciliation loop by mechanically enforcing that every
``AIENG_*`` env var documented in ``CLAUDE.md`` either:

1. Matches its code default in the canonical source file
   (``runtime_state.py`` for tool/loop/event tunables,
   ``runtime-stop.py`` for Ralph tunables,
   ``integrity.py`` for the hook integrity mode,
   ``src/ai_engineering/config/concurrency.py`` for spec-139 M1
   concurrency primitives, hook scripts for M5, and SessionEnd hooks
   for M6), OR
2. Is explicitly marked ``# reserved spec-139 M<n>`` so the reader can
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
_TEMPLATE_CLAUDE_MD = _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "CLAUDE.md"
_RUNTIME_STATE = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "runtime_state.py"
_RUNTIME_STOP = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
_INTEGRITY = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"
_CONCURRENCY = _REPO_ROOT / "src" / "ai_engineering" / "config" / "concurrency.py"
_PROMPT_INJECTION_GUARD = (
    _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"
)
_AUTO_FORMAT = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "auto-format.py"
_RUNTIME_ROTATE_THROTTLED = (
    _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "runtime-rotate-throttled.py"
)
_RUNTIME_SESSION_END = (
    _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "runtime-session-end.py"
)

# Regex that pulls every ``AIENG_<NAME>  # default <value>`` or
# ``AIENG_<NAME>  # reserved spec-139 M<n>`` row out of the tunables fenced
# code block. The trailing parenthetical (e.g. ``(observe-only)`` or
# ``(Phase 5 assessor cap)``) is allowed but ignored — the default token
# is just the first whitespace-bounded value after ``default ``.
_TUNABLE_RE = re.compile(
    r"^(AIENG_[A-Z_]+)\s+#\s*"
    r"(?:default\s+(\S+)|(?:(pending|reserved)\s+spec-139\s+(M\d+)))",
    re.MULTILINE,
)

# Whitelisted established tunables where the code default and the
# CLAUDE.md / CONSTITUTION.md documented value intentionally disagree.
# spec-147 G1 flipped ``integrity.py`` ``_DEFAULT_MODE`` from ``warn`` to
# ``enforce`` so it now matches the docs — the former
# ``AIENG_HOOK_INTEGRITY_MODE`` entry was removed once they re-converged.
# Add an entry here only for a deliberate, documented divergence; the
# test below asserts each entry's disagreement still holds so the
# whitelist cannot silently rot.
_KNOWN_DOC_CODE_DISAGREEMENTS: frozenset[str] = frozenset()

# Reserved milestones acknowledged in CLAUDE.md but not yet wired in code.
# Removing an entry here means the corresponding milestone has landed and
# the var now has a real code default that the test must verify.
_RESERVED_MILESTONES: frozenset[str] = frozenset({"M2", "M5"})
_RESERVED_TUNABLES: frozenset[str] = frozenset(
    {
        "AIENG_HOST_PREFLIGHT_DISABLED",
        "AIENG_HOST_PREFLIGHT_MIN_FREE_MB",
        "AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT",
        "AIENG_HOOK_BUDGET_PROFILE",
    }
)


def _read_tunables_block(doc_path: Path = _CLAUDE_MD) -> str:
    """Extract the fenced code block following ``## Runtime Layer Tunables``."""
    text = doc_path.read_text(encoding="utf-8")
    marker = "## Runtime Layer Tunables"
    assert marker in text, f"{doc_path} missing the Runtime Layer Tunables section"
    after_header = text.split(marker, 1)[1]
    # The first triple-backtick fence after the header is the tunables block.
    fence_open = after_header.find("```")
    assert fence_open != -1, "Tunables section missing opening code fence"
    fence_close = after_header.find("```", fence_open + 3)
    assert fence_close != -1, "Tunables section missing closing code fence"
    return after_header[fence_open + 3 : fence_close]


def _parse_documented_tunables(
    doc_path: Path = _CLAUDE_MD,
) -> dict[str, tuple[str | None, str | None, str | None]]:
    """Return ``{name: (default, marker_kind, marker_milestone)}``."""
    block = _read_tunables_block(doc_path)
    parsed: dict[str, tuple[str | None, str | None, str | None]] = {}
    for match in _TUNABLE_RE.finditer(block):
        name = match.group(1)
        default = match.group(2)
        marker_kind = match.group(3)
        marker_milestone = match.group(4)
        parsed[name] = (default, marker_kind, marker_milestone)
    return parsed


def _grep_default(path: Path, pattern: str) -> str | None:
    """Return the first regex capture group hit in ``path``, else ``None``."""
    text = path.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _normalized_int_literal(raw: str | None) -> str | None:
    """Normalize a Python integer literal token for doc-default comparison."""
    return raw.replace("_", "") if raw is not None else None


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
    if name == "AIENG_RUNTIME_ROTATE_THROTTLE_SEC":
        return _grep_default(
            _RUNTIME_ROTATE_THROTTLED,
            r"_DEFAULT_THROTTLE_SEC\s*=\s*(\d+)",
        )
    if name == "AIENG_HOOK_CACHE_TTL_SEC":
        code_default = _grep_default(
            _PROMPT_INJECTION_GUARD,
            r"if not raw:\s+return\s+(\d+)(?:\.0)?",
        )
        return code_default
    if name == "AIENG_AUTOFORMAT_DEBOUNCE_SEC":
        return _grep_default(
            _AUTO_FORMAT,
            r"_AUTOFORMAT_DEBOUNCE_DEFAULT_SEC\s*=\s*(\d+\.\d+)",
        )
    if name == "AIENG_NDJSON_MAX_LINES":
        return _normalized_int_literal(
            _grep_default(
                _RUNTIME_SESSION_END,
                r"_NDJSON_MAX_LINES_DEFAULT\s*=\s*([0-9_]+)",
            )
        )
    if name == "AIENG_NDJSON_MAX_BYTES":
        expression = _grep_default(
            _RUNTIME_SESSION_END,
            r"_NDJSON_MAX_BYTES_DEFAULT\s*=\s*([0-9_]+\s*\*\s*[0-9_]+\s*\*\s*[0-9_]+)",
        )
        if expression is None:
            return None
        factors = [int(factor.strip().replace("_", "")) for factor in expression.split("*")]
        product = 1
        for factor in factors:
            product *= factor
        return str(product)
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

# spec-139 M5/M6 tunables that are implemented in hook/runtime code and
# therefore MUST be default-bearing docs entries, never reserved/pending.
_PROMOTED_M5_M6_TUNABLES: tuple[str, ...] = (
    "AIENG_HOOK_CACHE_TTL_SEC",
    "AIENG_AUTOFORMAT_DEBOUNCE_SEC",
    "AIENG_NDJSON_MAX_LINES",
    "AIENG_NDJSON_MAX_BYTES",
)

_CANONICAL_TUNABLE_DOCS: tuple[Path, ...] = (_CLAUDE_MD, _TEMPLATE_CLAUDE_MD)


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
    doc_default, marker_kind, _milestone = documented[name]
    assert marker_kind is None, f"{name} is an established tunable but marked {marker_kind}"
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
    doc_default, marker_kind, _milestone = documented[name]
    assert marker_kind is None, f"{name} landed in M1 but is marked {marker_kind}"
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
@pytest.mark.parametrize("doc_path", _CANONICAL_TUNABLE_DOCS)
@pytest.mark.parametrize("name", _PROMOTED_M5_M6_TUNABLES)
def test_promoted_m5_m6_tunable_documented_with_code_matching_default(
    doc_path: Path,
    name: str,
) -> None:
    """Implemented spec-139 M5/M6 vars MUST show real defaults in rulebooks."""
    documented = _parse_documented_tunables(doc_path)
    assert name in documented, f"{doc_path} tunables block missing {name}"
    doc_default, marker_kind, _milestone = documented[name]
    assert marker_kind is None, f"{name} is implemented but marked {marker_kind} in {doc_path}"
    assert doc_default is not None, f"{name} missing a documented default in {doc_path}"

    code_default = _code_default_for(name)
    assert code_default is not None, (
        f"Could not resolve code default for {name} — update _code_default_for() "
        "if the hook/runtime source moved."
    )
    assert doc_default == code_default, (
        f"{name} doc/code drift in {doc_path}: docs say default={doc_default!r}, "
        f"code says default={code_default!r}."
    )


@pytest.mark.unit
@pytest.mark.parametrize("doc_path", _CANONICAL_TUNABLE_DOCS)
def test_tunables_block_uses_reserved_not_pending_markers(doc_path: Path) -> None:
    """Tunables docs use default-bearing entries or explicit reserved rows."""
    block = _read_tunables_block(doc_path)
    assert "pending spec-139" not in block, (
        f"{doc_path} still uses pending markers; implemented vars need defaults "
        "and future-only vars should use reserved markers."
    )


@pytest.mark.unit
def test_reserved_milestone_markers_use_documented_format() -> None:
    """Every reserved var MUST use the ``# reserved spec-139 M<n>`` format and
    cite one of the roadmap milestones still open in spec-139.
    """
    documented = _parse_documented_tunables()
    reserved_entries = {
        name: milestone
        for name, (_default, marker_kind, milestone) in documented.items()
        if marker_kind is not None
    }
    assert reserved_entries, (
        "Tunables block declares zero reserved entries — keep the genuinely future "
        "host-preflight/budget-profile vars in one reserved block, or delete this "
        "test if D-146-07 removes them entirely."
    )
    for name, milestone in reserved_entries.items():
        assert name in _RESERVED_TUNABLES, f"{name} is not an approved reserved roadmap tunable"
        assert milestone in _RESERVED_MILESTONES, (
            f"{name} cites reserved milestone {milestone!r}; the only acknowledged "
            f"reserved milestones are {sorted(_RESERVED_MILESTONES)}. Update the "
            "whitelist if a new spec-139 roadmap milestone genuinely opened."
        )


@pytest.mark.unit
def test_every_documented_var_classified() -> None:
    """Every var documented in CLAUDE.md MUST be either established / M1 /
    M5-M6 / reserved. Catches accidental entries that bypass classification.
    """
    documented = _parse_documented_tunables()
    classified = (
        set(_ESTABLISHED_TUNABLES)
        | set(_M1_TUNABLES)
        | set(_M6_TUNABLES)
        | set(_PROMOTED_M5_M6_TUNABLES)
        | set(_RESERVED_TUNABLES)
    )
    for name, (_default, marker_kind, _milestone) in documented.items():
        if name in classified:
            continue
        if marker_kind is not None:
            continue
        pytest.fail(
            f"{name} documented in CLAUDE.md but not classified as "
            "established / M1 / M5-M6 / reserved. Add it to the matching "
            "classification or mark the doc entry as reserved spec-139 M<n>."
        )


@pytest.mark.unit
def test_reserved_set_covers_future_m2_m5_only_per_spec_146() -> None:
    """D-146-07 keeps only future host-preflight/budget-profile vars reserved."""
    documented = _parse_documented_tunables()
    reserved_entries = {
        name: milestone
        for name, (_default, marker_kind, milestone) in documented.items()
        if marker_kind == "reserved"
    }
    assert set(reserved_entries) == _RESERVED_TUNABLES
    assert set(reserved_entries.values()) == _RESERVED_MILESTONES


@pytest.mark.unit
def test_m6_runtime_rotate_tunable_matches_code_default() -> None:
    """M6 runtime rotation throttle is documented with its wrapper default."""
    documented = _parse_documented_tunables()
    for name in _M6_TUNABLES:
        assert name in documented, f"CLAUDE.md tunables block missing M6 var {name}"
        doc_default, marker_kind, _milestone = documented[name]
        assert marker_kind is None, f"{name} landed in M6 but is marked {marker_kind}"
        assert doc_default is not None, f"{name} missing a documented default"
        code_default = _code_default_for(name)
        assert code_default is not None, (
            f"Could not resolve code default for {name} — update _code_default_for() "
            "if runtime-rotate-throttled.py moved."
        )
        assert doc_default == code_default, (
            f"{name} M6 doc/code drift: CLAUDE.md says default={doc_default!r}, "
            f"code says default={code_default!r}."
        )
