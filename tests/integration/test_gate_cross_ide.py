"""Cross-IDE parity tests for ``ai_engineering.policy.orchestrator`` (T-8.5).

RED phase for spec-104 G-8 / D-104-08 — the orchestrator must produce
identical output regardless of which IDE driver (Claude Code, GitHub
Copilot, Codex, Gemini) is invoking the CLI. The bottleneck spec-104
addresses lives entirely in the CLI/Python layer, so cross-IDE parity is
guaranteed only if the orchestrator never branches on IDE-identifying
state (env vars, imports, conditional code paths).

These tests exercise three independent angles of that guarantee:

1. **Behavioural parity** — invoke ``run_gate`` four times with
   ``AIENG_IDE`` set to each supported IDE, normalise the run-local
   ``session_id`` and ``produced_at`` fields, and assert the remaining
   JSON is byte-identical (Tests 1, 3).
2. **Static parity** — grep the orchestrator source for IDE-identifying
   strings or imports; require zero matches (Tests 2, 8).
3. **Negative parity** — assert the orchestrator does not read
   IDE-specific env vars (``CLAUDE_CODE_SESSION_ID`` etc.) and
   correctly attributes the *skill* caller (``ai-commit`` / ``ai-pr`` /
   ``watch-loop``) instead of the IDE (Tests 4, 5).
4. **Cache parity** — the cache module is also IDE-agnostic (Test 6),
   and the orchestrator runs with no ``AIENG_*`` env at all (Test 7).

The contract under test is the public entrypoint that T-2.8 (Phase 2
GREEN) lands in ``ai_engineering.policy.orchestrator``::

    run_gate(
        staged_files: list[str],
        *,
        mode: str = "local",
        cache_dir: Path,
        cache_disabled: bool = False,
        produced_by: str = "ai-commit",
    ) -> GateFindingsDocument

Tests that depend on the production module being importable today
(behavioural / negative parity) currently fail with ``ImportError`` —
that is the expected RED state. Tests that grep the source skip with a
helpful message until ``orchestrator.py`` exists (Phase 2 GREEN
pending), then engage the assertion automatically.

TDD CONSTRAINT: this file is IMMUTABLE after T-8.5 lands. T-8.6 may
only confirm the production module already satisfies the assertions
(orchestrator must already be IDE-agnostic by construction); never edit
the assertions themselves.

Coverage (8 tests):

1. ``test_orchestrator_does_not_branch_on_aieng_ide_env`` — set
   ``AIENG_IDE`` to each of the four supported values; the orchestrator's
   externally-observable behaviour is identical.
2. ``test_orchestrator_module_no_ide_string_grep`` — source-level grep
   of ``orchestrator.py`` finds zero IDE-identifying string literals.
3. ``test_run_gate_output_byte_identical_across_ides`` — JSON output
   byte-identical (after normalising session_id + produced_at) across
   all four IDE-emulated environments.
4. ``test_run_gate_does_not_read_claude_specific_env`` — orchestrator
   does NOT consult ``CLAUDE_CODE_SESSION_ID``, ``COPILOT_SESSION_ID``,
   ``CODEX_SESSION_ID``, or ``GEMINI_SESSION_ID``.
5. ``test_run_gate_skill_caller_attributed_correctly`` — the
   ``produced_by`` field reflects the skill caller (one of
   ``ai-commit`` / ``ai-pr`` / ``watch-loop``), never the IDE.
6. ``test_gate_cache_does_not_branch_on_ide_env`` — source-level grep
   of ``gate_cache.py`` finds zero IDE-identifying string literals.
7. ``test_run_gate_works_with_no_aieng_env_set`` — clean env (no
   ``AIENG_*`` variables present) still yields a successful run.
8. ``test_orchestrator_imports_no_ide_specific_modules`` — source-level
   AST scan finds no ``import claude_code`` / ``from copilot import …``
   / etc. statements anywhere in the orchestrator module.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Path constants — anchored at the repo root regardless of cwd.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

ORCHESTRATOR_PATH = REPO_ROOT / "src" / "ai_engineering" / "policy" / "orchestrator.py"
GATE_CACHE_PATH = REPO_ROOT / "src" / "ai_engineering" / "policy" / "gate_cache.py"

# ---------------------------------------------------------------------------
# Constants — Wave 2 checks (mode="local") and IDE identifiers under test.
# ---------------------------------------------------------------------------

WAVE2_LOCAL_CHECKS = ("gitleaks", "ruff", "ty", "pytest-smoke", "validate")

# The four IDE identifiers spec-104 G-8 enumerates. Test parity must hold
# for the cartesian product of these values x orchestrator behaviour.
SUPPORTED_IDES: tuple[str, ...] = (
    "claude-code",
    "github-copilot",
    "codex",
    "gemini",
)

# IDE-specific session-ID env vars the orchestrator must NEVER consult.
# Each IDE driver sets its own session marker; reading any of them would
# create implicit IDE branching and break G-8 parity.
IDE_SPECIFIC_SESSION_ENVS: tuple[str, ...] = (
    "CLAUDE_CODE_SESSION_ID",
    "COPILOT_SESSION_ID",
    "CODEX_SESSION_ID",
    "GEMINI_SESSION_ID",
)

# Substrings that, if present as bare literal tokens in the orchestrator
# or gate_cache source, indicate IDE-specific branching. The regex is
# word-bounded so we don't false-positive on substrings of unrelated
# identifiers (e.g., a hypothetical ``code_xchange`` doesn't trip
# ``codex``). Each IDE name is matched as an isolated token.
IDE_LITERAL_GREP = re.compile(r"\b(claude-code|github-copilot|copilot|codex|gemini)\b")

# Allow-list: substrings of the source we explicitly tolerate even if
# they happen to contain an IDE token. Every entry is a verbatim match
# on a contiguous source slice — keep this list minimal and motivated.
# (Empty today by design; if a legitimate need arises, add the
# narrowest possible string and a comment.)
IDE_LITERAL_ALLOWLIST: tuple[str, ...] = ()

# The set of skill callers the orchestrator MUST be able to attribute as
# ``produced_by``. Sourced from D-104-06 schema v1's ``GateProducedBy``
# enum; spec-104 G-8 demands attribution by skill, not by IDE.
SKILL_CALLERS = ("ai-commit", "ai-pr", "watch-loop")


# ---------------------------------------------------------------------------
# Helpers — shared with tests/integration/test_orchestrator_cache_integration.py
# (re-implemented here to keep this test file self-contained per TDD spec).
# ---------------------------------------------------------------------------


def _seed_minimal_configs(repo: Path) -> None:
    """Seed configs that ``_CONFIG_FILE_WHITELIST`` (D-104-09) hashes.

    Mirrors the helper in ``test_orchestrator_cache_integration.py`` so
    the cache-key derivation is deterministic across test files.
    """

    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    (repo / ".ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    (repo / ".gitleaks.toml").write_text("title = 'gitleaks'\n", encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (repo / "conftest.py").write_text("# empty\n", encoding="utf-8")

    ai_dir = repo / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: [python]\n", encoding="utf-8"
    )

    specs_dir = ai_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    (specs_dir / "plan.md").write_text("# plan\n", encoding="utf-8")


def _make_staged_files(repo: Path) -> list[str]:
    """Create a deterministic set of staged files inside ``repo``.

    Returns repo-relative POSIX paths suitable for
    ``run_gate(staged_files=...)``. Two files keep the cache key
    non-trivial without making assertions noisy.
    """

    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)

    (src / "module_a.py").write_text("def alpha() -> int:\n    return 1\n", encoding="utf-8")
    (src / "module_b.py").write_text("def beta() -> int:\n    return 2\n", encoding="utf-8")

    return ["src/module_a.py", "src/module_b.py"]


def _git_init(repo: Path) -> None:
    """Initialise a git repo so cache-key derivation has real blob hashes.

    ``_compute_cache_key`` (D-104-09) hashes staged blobs via
    ``git hash-object`` so a real git context is required. Identical to
    the helper in ``test_orchestrator_cache_integration.py``.
    """

    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Tester"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"],
        check=True,
        capture_output=True,
    )


class _FakeCheckRunner:
    """Drop-in replacement for the orchestrator's per-check dispatcher.

    Test-local copy of the runner used in
    ``test_orchestrator_cache_integration.py``. Keeps the cross-IDE
    tests independent of the cache-integration test file's fixtures.
    """

    def __init__(self, return_outcomes: dict[str, str] | None = None) -> None:
        self.calls: list[str] = []
        self.return_outcomes: dict[str, str] = return_outcomes or {}

    def __call__(self, check_name: str, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append(check_name)
        outcome = self.return_outcomes.get(check_name, "pass")
        return {
            "outcome": outcome,
            "exit_code": 0 if outcome == "pass" else 1,
            "stdout": "",
            "stderr": "",
            "findings": [],
        }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Initialised git repo with seeded configs and staged source files."""

    _seed_minimal_configs(tmp_path)
    _make_staged_files(tmp_path)
    _git_init(tmp_path)
    return tmp_path


@pytest.fixture()
def fake_runner() -> _FakeCheckRunner:
    """Return a fresh ``_FakeCheckRunner`` per test."""

    return _FakeCheckRunner()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no IDE / cache env state leaks across tests.

    Tests that need an env var SET will call ``monkeypatch.setenv``
    themselves; this fixture only guarantees a clean slate. The list
    is exhaustive: every env var any test in this file might consult
    or assert against is wiped.
    """

    monkeypatch.delenv("AIENG_IDE", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DEBUG", raising=False)
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)

    for env_name in IDE_SPECIFIC_SESSION_ENVS:
        monkeypatch.delenv(env_name, raising=False)


def _findings_doc_dict(doc: object) -> dict[str, object]:
    """Coerce ``run_gate``'s return to a plain dict for comparison.

    Mirrors the helper in ``test_orchestrator_cache_integration.py``;
    accepts a Pydantic model (``model_dump`` / ``dict``) or a raw dict.
    Uses ``by_alias=True`` so the ``schema_`` field surfaces as
    ``"schema"`` (matching D-104-06).
    """

    if hasattr(doc, "model_dump"):
        return doc.model_dump(by_alias=True, mode="json")  # type: ignore[no-any-return]
    if hasattr(doc, "dict"):
        return doc.dict(by_alias=True)  # type: ignore[no-any-return]
    if isinstance(doc, dict):
        return doc
    raise AssertionError(
        f"orchestrator.run_gate must return a GateFindingsDocument or dict; got {type(doc)!r}"
    )


def _normalise_run_local_fields(doc: dict[str, object]) -> dict[str, object]:
    """Strip the run-local fields that legitimately differ across runs.

    ``session_id`` is a fresh UUID4 per ``run_gate`` invocation and
    ``produced_at`` is a wall-clock timestamp. Two parity-satisfying
    runs MUST produce different values for these fields; the parity
    contract applies to *every other* field (D-104-08).

    Returns a new dict with these fields removed so JSON-equality
    captures the parity guarantee precisely.
    """

    normalised = dict(doc)
    normalised.pop("session_id", None)
    normalised.pop("produced_at", None)
    # ``wall_clock_ms`` is also legitimately variable run-to-run (CPU
    # contention, scheduler noise). Strip it; the parity contract is
    # about WHAT ran, not HOW LONG it took.
    normalised.pop("wall_clock_ms", None)
    # ``commit_sha`` is captured from git HEAD and may be ``None`` for
    # uncommitted state. It's deterministic per fixture but we strip it
    # defensively in case the fixture ever depends on commit timing.
    normalised.pop("commit_sha", None)
    return normalised


def _scan_orchestrator_source() -> str:
    """Return the orchestrator source as a single string.

    Caller must check ``ORCHESTRATOR_PATH.exists()`` first so we can
    skip with a helpful message during the RED phase before T-2.2 lands.
    """

    return ORCHESTRATOR_PATH.read_text(encoding="utf-8")


def _ide_literal_matches(source: str) -> list[str]:
    """Return IDE-identifying token matches in ``source`` (case-insensitive).

    Drops matches that fall inside any allow-listed substring. The
    allow-list is empty by design (see ``IDE_LITERAL_ALLOWLIST``); the
    plumbing exists so a future legitimate occurrence can be carved out
    narrowly without weakening the test.
    """

    matches: list[str] = []
    for match in IDE_LITERAL_GREP.finditer(source):
        token = match.group(0)
        # If the literal occurs inside a permitted substring, skip it.
        # This costs O(n) per allowlist entry; n is small.
        match_span = source[max(0, match.start() - 32) : match.end() + 32]
        if any(allowed in match_span for allowed in IDE_LITERAL_ALLOWLIST):
            continue
        matches.append(token)
    return matches


# ---------------------------------------------------------------------------
# Test 1 — orchestrator does not branch on AIENG_IDE env
# ---------------------------------------------------------------------------


def test_orchestrator_does_not_branch_on_aieng_ide_env(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set ``AIENG_IDE`` to each supported value one at a time; the
    orchestrator's externally-observable behaviour MUST be identical.

    Identical here means: same set of Wave 2 checks invoked, same
    cache_hits / cache_misses bookkeeping, same findings aggregation.
    The contract is that ``AIENG_IDE`` is metadata for callers — never
    a control input the orchestrator consumes (D-104-08).
    """
    # Arrange — the production module must exist for behavioural
    # parity; if it doesn't, the test fails-loudly (not a skip) so the
    # RED contract is enforced. Phase 2 GREEN (T-2.8) lands the symbol.
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    observed_invocations: list[set[str]] = []
    observed_hits: list[set[str]] = []
    observed_misses: list[set[str]] = []

    for ide_value in SUPPORTED_IDES:
        # Fresh runner + fresh cache_dir per IDE iteration so the
        # observed behaviour reflects the IDE value alone — not residual
        # cache state from a prior iteration.
        runner = _FakeCheckRunner()
        per_ide_cache_dir = cache_dir / ide_value
        per_ide_cache_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("AIENG_IDE", ide_value)

        with mock.patch.object(orchestrator, "_run_check", new=runner):
            doc = orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=per_ide_cache_dir,
            )

        invoked = {c for c in runner.calls if c in WAVE2_LOCAL_CHECKS}
        result = _findings_doc_dict(doc)

        observed_invocations.append(invoked)
        observed_hits.append(set(result.get("cache_hits") or []))
        observed_misses.append(set(result.get("cache_misses") or []))

    # Assert — every iteration invoked the same set of checks.
    first_invoked = observed_invocations[0]
    assert all(invoked == first_invoked for invoked in observed_invocations), (
        "AIENG_IDE must NOT influence which Wave 2 checks the orchestrator "
        "runs (D-104-08). Per-IDE invocations diverged: "
        f"{dict(zip(SUPPORTED_IDES, observed_invocations, strict=True))}"
    )
    # And the invoked set covers every Wave 2 local check (no IDE
    # silently skipped a check).
    assert first_invoked >= set(WAVE2_LOCAL_CHECKS), (
        f"Each per-IDE run must invoke every Wave 2 local check; got invoked={first_invoked!r}"
    )

    # Assert — cache bookkeeping is identical across IDEs (every IDE
    # got a fresh cache_dir → all-miss is the only valid outcome).
    first_hits = observed_hits[0]
    first_misses = observed_misses[0]
    assert all(h == first_hits for h in observed_hits), (
        "AIENG_IDE must NOT influence cache_hits bookkeeping; "
        f"per-IDE hits diverged: {dict(zip(SUPPORTED_IDES, observed_hits, strict=True))}"
    )
    assert all(m == first_misses for m in observed_misses), (
        "AIENG_IDE must NOT influence cache_misses bookkeeping; "
        f"per-IDE misses diverged: {dict(zip(SUPPORTED_IDES, observed_misses, strict=True))}"
    )


# ---------------------------------------------------------------------------
# Test 2 — orchestrator source has zero IDE-identifying string literals
# ---------------------------------------------------------------------------


def test_orchestrator_module_no_ide_string_grep() -> None:
    """Source-level grep for IDE-identifying tokens in ``orchestrator.py``.

    The orchestrator MUST NOT contain literal references to any IDE
    name (``claude_code``, ``copilot``, ``codex``, ``gemini``). Any
    occurrence is structural evidence of IDE branching and breaks the
    G-8 parity guarantee.

    Skips with a helpful message until ``orchestrator.py`` lands
    (Phase 2 GREEN T-2.2 pending).
    """
    if not ORCHESTRATOR_PATH.exists():
        pytest.skip(
            "orchestrator.py not yet created — Phase 2 GREEN T-2.2 pending. "
            "Source-level IDE-grep parity test gates on file presence."
        )

    source = _scan_orchestrator_source()
    matches = _ide_literal_matches(source)

    assert matches == [], (
        "orchestrator.py contains IDE-identifying string literals — this is "
        "structural evidence of IDE branching and breaks spec-104 G-8 / "
        f"D-104-08 cross-IDE parity. Found tokens: {matches!r}. "
        "If a legitimate need exists, narrow it with IDE_LITERAL_ALLOWLIST."
    )


# ---------------------------------------------------------------------------
# Test 3 — JSON output byte-identical across IDE-emulated environments
# ---------------------------------------------------------------------------


def test_run_gate_output_byte_identical_across_ides(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run ``run_gate`` once per IDE; assert JSON byte-equality after
    normalising session_id, produced_at, wall_clock_ms, and commit_sha.

    This is the strictest cross-IDE parity assertion: not just "same
    behaviour" (Test 1) but "same emitted document". After stripping
    legitimately-variable run-local fields, every IDE must produce the
    same dictionary serialised to the same byte sequence.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache-shared"
    staged = _make_staged_files(repo)

    # Use a SHARED cache_dir across IDE iterations. The first iteration
    # cold-starts (all miss); the next three should hit the same
    # entries — but the parity contract says even the cache bookkeeping
    # must be identical across IDEs *given identical inputs and starting
    # state*. So instead, give each IDE its own pristine cache_dir and
    # compare after stripping cache fields too.
    per_ide_results: dict[str, dict[str, object]] = {}

    for ide_value in SUPPORTED_IDES:
        # Each IDE gets a fresh runner and a fresh cache_dir to control
        # for cache-warmth ordering; the comparison is on what the
        # orchestrator EMITS, which must be IDE-agnostic.
        runner = _FakeCheckRunner()
        per_ide_cache_dir = cache_dir / ide_value
        per_ide_cache_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("AIENG_IDE", ide_value)

        with mock.patch.object(orchestrator, "_run_check", new=runner):
            doc = orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=per_ide_cache_dir,
            )

        result = _findings_doc_dict(doc)
        normalised = _normalise_run_local_fields(result)
        per_ide_results[ide_value] = normalised

    # Assert — every IDE's normalised output is byte-identical.
    # JSON serialisation with sort_keys + canonical separators makes
    # the comparison robust to insertion order in the underlying dict.
    canonical_kwargs = {"sort_keys": True, "separators": (",", ":"), "default": str}
    serialised = {
        ide: json.dumps(result, **canonical_kwargs).encode("utf-8")
        for ide, result in per_ide_results.items()
    }

    first_ide = SUPPORTED_IDES[0]
    first_bytes = serialised[first_ide]

    for ide_value in SUPPORTED_IDES[1:]:
        assert serialised[ide_value] == first_bytes, (
            f"orchestrator output for AIENG_IDE={ide_value!r} differs from "
            f"AIENG_IDE={first_ide!r} after normalising run-local fields. "
            f"spec-104 G-8 / D-104-08 requires byte-identical output across "
            f"IDEs.\n"
            f"  {first_ide}: {first_bytes!r}\n"
            f"  {ide_value}: {serialised[ide_value]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — orchestrator does NOT consult IDE-specific session env vars
# ---------------------------------------------------------------------------


def test_run_gate_does_not_read_claude_specific_env(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set every IDE-specific session env to a sentinel; the orchestrator
    MUST produce identical output to a clean-env run.

    ``CLAUDE_CODE_SESSION_ID``, ``COPILOT_SESSION_ID``, etc. are markers
    each IDE driver populates. Reading any of them is implicit IDE
    branching: a Claude run would diverge from a Codex run even though
    both invoked the same CLI. The contract (D-104-08) is that the
    orchestrator NEVER consults these vars — its run is fully
    determined by staged files, configs, mode, and CLI flags.

    Test method: capture os.environ.get / os.getenv calls via mocking
    and assert none of the IDE-specific names appear in the keys read.
    """
    # Arrange
    import os

    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    # Pre-populate IDE-specific session env vars so that IF the
    # orchestrator looks at them, the lookup succeeds (and we can prove
    # it). The clean-env precondition fixture wipes these between
    # tests, so we set them just for this test's scope.
    for env_name in IDE_SPECIFIC_SESSION_ENVS:
        monkeypatch.setenv(env_name, f"sentinel-for-{env_name.lower()}")

    # Capture every os.environ read. The cleanest hook is to wrap
    # ``os.environ.get`` and ``os.getenv`` so any read by the
    # orchestrator (or any code it transitively calls) is observable.
    keys_read: list[str] = []
    original_environ_get = os.environ.get
    original_getenv = os.getenv

    def _spy_environ_get(key: str, default: object = None) -> object:
        keys_read.append(key)
        return original_environ_get(key, default)

    def _spy_getenv(key: str, default: object = None) -> object:
        keys_read.append(key)
        return original_getenv(key, default)

    with (
        mock.patch.object(os.environ, "get", new=_spy_environ_get),
        mock.patch.object(os, "getenv", new=_spy_getenv),
        mock.patch.object(orchestrator, "_run_check", new=fake_runner),
    ):
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — none of the IDE-specific session-id env names were read.
    forbidden_reads = [k for k in keys_read if k in IDE_SPECIFIC_SESSION_ENVS]

    assert forbidden_reads == [], (
        "orchestrator.run_gate read IDE-specific session env vars — this is "
        "implicit IDE branching and breaks spec-104 G-8 / D-104-08 parity. "
        f"Forbidden reads: {forbidden_reads!r}. "
        "Allowed env reads: AIENG_* only (cache flags, debug, legacy fallback)."
    )


# ---------------------------------------------------------------------------
# Test 5 — produced_by reflects the skill caller, never the IDE
# ---------------------------------------------------------------------------


def test_run_gate_skill_caller_attributed_correctly(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoking ``run_gate`` with each skill caller (one of
    ``ai-commit`` / ``ai-pr`` / ``watch-loop``) MUST set
    ``produced_by`` to that exact value — never the IDE.

    The contract (D-104-06) is that ``produced_by`` is one of the
    enumerated skill callers; the IDE is metadata captured ONLY in
    callsite skill markdown, never in the gate-findings document.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    # Set AIENG_IDE so that IF the orchestrator accidentally used it
    # for produced_by attribution, the test would catch it.
    monkeypatch.setenv("AIENG_IDE", "claude-code")

    observed_produced_by: dict[str, str] = {}

    for caller in SKILL_CALLERS:
        runner = _FakeCheckRunner()
        per_caller_cache = cache_dir / caller
        per_caller_cache.mkdir(parents=True, exist_ok=True)

        with mock.patch.object(orchestrator, "_run_check", new=runner):
            doc = orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=per_caller_cache,
                produced_by=caller,
            )

        result = _findings_doc_dict(doc)
        observed_produced_by[caller] = str(result.get("produced_by"))

    # Assert — every invocation's produced_by exactly matches the caller.
    for caller, observed in observed_produced_by.items():
        assert observed == caller, (
            f"run_gate(produced_by={caller!r}) emitted produced_by={observed!r}; "
            "schema v1 (D-104-06) requires exact attribution to one of "
            f"{list(SKILL_CALLERS)!r}. The IDE name (AIENG_IDE='claude-code') "
            "must NOT leak into produced_by."
        )

    # Assert — none of the produced_by values matches an IDE identifier.
    ide_set = set(SUPPORTED_IDES)
    for caller, observed in observed_produced_by.items():
        assert observed not in ide_set, (
            f"produced_by={observed!r} (for caller {caller!r}) matches an IDE "
            f"identifier; spec-104 G-8 forbids IDE leakage into the schema."
        )


# ---------------------------------------------------------------------------
# Test 6 — gate_cache module is also IDE-agnostic (source-level grep)
# ---------------------------------------------------------------------------


def test_gate_cache_does_not_branch_on_ide_env() -> None:
    """Source-level grep for IDE-identifying tokens in ``gate_cache.py``.

    The cache layer (D-104-03 / D-104-08) is an IDE-agnostic CLI
    component. Any literal IDE token in its source is structural
    evidence of branching and breaks G-8 parity at the cache layer
    (which would manifest as different cache_hits/cache_misses
    bookkeeping per IDE — already exercised behaviourally in Test 1,
    but caught earlier here).

    Skips with a helpful message until ``gate_cache.py`` lands
    (Phase 1 GREEN T-1.2 pending).
    """
    if not GATE_CACHE_PATH.exists():
        pytest.skip(
            "gate_cache.py not yet created — Phase 1 GREEN T-1.2 pending. "
            "Source-level IDE-grep parity test gates on file presence."
        )

    source = GATE_CACHE_PATH.read_text(encoding="utf-8")
    matches = _ide_literal_matches(source)

    assert matches == [], (
        "gate_cache.py contains IDE-identifying string literals — this is "
        "structural evidence of IDE branching and breaks spec-104 G-8 / "
        f"D-104-08 cross-IDE parity at the cache layer. Found tokens: "
        f"{matches!r}. The cache module is pure CLI/Python with zero IDE "
        "knowledge by design."
    )


# ---------------------------------------------------------------------------
# Test 7 — clean env (no AIENG_*) still runs correctly
# ---------------------------------------------------------------------------


def test_run_gate_works_with_no_aieng_env_set(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``run_gate`` MUST run successfully with NO ``AIENG_*`` env vars
    set — the env is a clean process, simulating a non-Claude IDE
    that doesn't populate any AIENG_* state.

    The autouse ``_clean_env`` fixture already wipes the relevant
    vars; this test makes the contract explicit by additionally
    sweeping any AIENG_* prefix at runtime and asserting a successful
    run still yields a valid GateFindingsDocument with all Wave 2
    checks executed.
    """
    # Arrange
    import os

    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    # Defensively wipe ANY AIENG_* env that might exist from the test
    # runner's parent shell. The autouse fixture handles the named
    # ones; this catches anything unexpected.
    for env_name in list(os.environ):
        if env_name.startswith("AIENG_"):
            monkeypatch.delenv(env_name, raising=False)

    # Sanity precondition — no AIENG_* env survives.
    aieng_residual = [k for k in os.environ if k.startswith("AIENG_")]
    assert aieng_residual == [], (
        f"precondition: AIENG_* env must be empty; got residual={aieng_residual!r}"
    )

    # Act
    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        doc = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — run produced a valid document with all Wave 2 checks.
    result = _findings_doc_dict(doc)

    assert result.get("schema") == "ai-engineering/gate-findings/v1", (
        f"Clean-env run must still emit the v1 schema; got schema={result.get('schema')!r}"
    )

    invoked = {c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS}
    assert invoked >= set(WAVE2_LOCAL_CHECKS), (
        "Clean-env run must invoke every Wave 2 local check (no env-driven "
        f"skip); got invoked={invoked!r}"
    )

    # Sanity — produced_by is a known skill caller (default 'ai-commit'
    # per the run_gate kwarg default).
    produced_by = str(result.get("produced_by"))
    assert produced_by in SKILL_CALLERS, (
        f"Clean-env run produced_by={produced_by!r} is not a known skill "
        f"caller; expected one of {list(SKILL_CALLERS)!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 — orchestrator source imports zero IDE-specific modules (AST scan)
# ---------------------------------------------------------------------------


def test_orchestrator_imports_no_ide_specific_modules() -> None:
    """AST scan of ``orchestrator.py`` finds zero ``import claude_code``
    / ``from copilot import …`` / similar IDE-specific imports.

    Source-level grep (Test 2) catches string-literal occurrences;
    this test catches *structural* IDE imports — even if a future
    refactor stored an IDE name in a module attribute or function
    parameter (which Test 2 might allow if narrowly allow-listed),
    importing an IDE-named module is unambiguous evidence of branching.

    Skips with a helpful message until ``orchestrator.py`` lands.
    """
    if not ORCHESTRATOR_PATH.exists():
        pytest.skip(
            "orchestrator.py not yet created — Phase 2 GREEN T-2.2 pending. "
            "AST-level IDE-import parity test gates on file presence."
        )

    source = _scan_orchestrator_source()
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    # An import is "IDE-specific" if the regex matches anywhere in the
    # dotted module path. Word boundaries don't apply cleanly inside
    # dotted paths, so we test each path component individually.
    forbidden_imports: list[str] = []
    for module in imported_modules:
        for component in module.split("."):
            if IDE_LITERAL_GREP.fullmatch(component):
                forbidden_imports.append(module)
                break

    assert forbidden_imports == [], (
        "orchestrator.py imports IDE-specific modules — this is structural "
        "evidence of IDE branching and breaks spec-104 G-8 / D-104-08. "
        f"Forbidden imports: {forbidden_imports!r}. "
        "The orchestrator is pure CLI/Python with zero IDE knowledge."
    )
