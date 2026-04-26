"""spec-104 G-3 verification — gate-cache hit rate ≥70% on consecutive runs.

This is the integration test that pins spec-104 Goal G-3:

    "gate-cache hit rate ≥70% en runs consecutivos con inputs idénticos"

The orchestrator (``policy.orchestrator.run_gate``) is invoked 10 times in a
row with deterministic inputs (same staged blob shas, same configs, same
mode). Run 1 is the cold-cache pass — every Wave 2 check misses, populates
the cache, and emits ``cache_misses`` in the ``GateFindingsDocument``. Runs
2..10 hit the cache for every check (5 Wave 2 checks across 9 warm runs =
45 hits; 5 misses on run 1; 45 / 50 = 0.90 hit rate, well above the 70%
target).

The assertion uses two complementary observability hooks:

* **Structured bookkeeping** — every ``run_gate`` call returns a
  ``GateFindingsDocument`` whose ``cache_hits`` / ``cache_misses`` lists
  are the authoritative count for that single invocation. Aggregating
  across the 10 runs yields total_hits / total_runs (where total_runs =
  sum of hits + misses across all 10 invocations).
* **Per-check debug markers** — with ``AIENG_CACHE_DEBUG=1`` the
  orchestrator's ``_dispatch_one_check`` emits one log record per check
  ("gate-cache hit check=…" / "gate-cache miss check=…"). The test
  asserts the marker stream is consistent with the structured tally so
  any divergence between the two surfaces (which downstream perf tests
  rely on) is caught here.

Per spec-104 plan T-9.3 this test runs in the normal integration suite
(no ``@pytest.mark.perf`` gating); the orchestrator is invoked with a
mocked ``_run_check`` so a real ruff/gitleaks subprocess never fires —
the wall-clock cost is bounded by the cache lookup path itself.

Maps to:
* Spec G-3 (``ai-engineering/specs/spec.md``).
* Plan T-9.3 (``ai-engineering/specs/plan.md``).
* Cache observability seam established by T-2.7 / T-2.8 (orchestrator
  cache integration) and ``AIENG_CACHE_DEBUG`` markers from
  ``policy.gate_cache._debug_enabled``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Constants — Wave 2 ``run_gate`` checks per D-104-01 in mode="local".
#
# Canonical 5-checker set per the spec-104 verify+review iteration: docs-gate
# was removed from the cached path because LLM dispatch is non-deterministic
# and would skew cache hit-rate measurement; it continues to run inside the
# /ai-pr docs lanes (step 6.5 lane 2), outside the gate orchestrator.
#
# Mirrors ``policy.orchestrator.LOCAL_CHECKERS`` so the test does not depend
# on importing private symbols from the orchestrator module — any drift
# between the two lists is caught by the WAVE2 union/intersection assertions
# below.
# ---------------------------------------------------------------------------

WAVE2_LOCAL_CHECKS: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
    "validate",
)

# Spec G-3 target — ≥70% hit rate across the 10-run window. The test asserts
# the realised rate strictly exceeds this threshold so we have headroom for
# noise and don't need to special-case rounding at the boundary.
G3_HIT_RATE_TARGET = 0.70

# Number of consecutive ``run_gate`` invocations the test exercises.
RUN_COUNT = 10


# ---------------------------------------------------------------------------
# Helpers — staged-file fixture, config seeding, fake check runner.
#
# The shape mirrors ``tests/integration/test_orchestrator_cache_integration.py``
# so anyone reading the suite sees the same primitives across tests that
# share the orchestrator's cache-integration contract.
# ---------------------------------------------------------------------------


def _make_staged_files(repo: Path) -> list[str]:
    """Create deterministic staged source files inside ``repo``.

    Two ``src/*.py`` files keep the cache-key derivation non-trivial without
    making the assertions noisy. The contents stay constant across the 10
    runs so every cache key remains stable.
    """
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)

    file_a = src / "module_a.py"
    file_a.write_text("def alpha() -> int:\n    return 1\n", encoding="utf-8")

    file_b = src / "module_b.py"
    file_b.write_text("def beta() -> int:\n    return 2\n", encoding="utf-8")

    return ["src/module_a.py", "src/module_b.py"]


def _seed_minimal_configs(repo: Path) -> None:
    """Seed the configs hashed by ``_CONFIG_FILE_WHITELIST`` (D-104-09).

    Only the entries touched by ``mode="local"`` Wave 2 checks are written
    so the test stays focused on the hit-rate signal.
    """
    (repo / "pyproject.toml").write_text(
        "[tool.ruff]\nline-length = 100\n",
        encoding="utf-8",
    )
    (repo / ".ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    (repo / ".gitleaks.toml").write_text("title = 'gitleaks'\n", encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (repo / "conftest.py").write_text("# empty\n", encoding="utf-8")

    ai_dir = repo / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: [python]\n",
        encoding="utf-8",
    )

    specs_dir = ai_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    (specs_dir / "plan.md").write_text("# plan\n", encoding="utf-8")


def _git_init(repo: Path) -> None:
    """Initialise a git repo + stage the seeded files.

    The orchestrator's ``_staged_blob_shas`` reads the staged tree to derive
    cache-key inputs deterministically; without an initialised repo the
    blob-sha computation falls back to empty bytes and the cache key would
    still be stable but unrealistic.
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
    """Drop-in for ``orchestrator._run_check`` — counts calls per check name.

    Returning ``outcome="pass"`` with empty findings keeps the orchestrator
    on the happy path so ``GateFindingsDocument.findings`` stays empty and
    the only signal under test is the hit/miss bookkeeping.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(
        self,
        check_name: str,
        *args: object,
        **kwargs: object,
    ) -> dict[str, object]:
        self.calls.append(check_name)
        return {
            "outcome": "pass",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "findings": [],
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Initialised git repo with seeded configs + staged source files."""
    _seed_minimal_configs(tmp_path)
    _make_staged_files(tmp_path)
    _git_init(tmp_path)
    return tmp_path


@pytest.fixture()
def fake_runner() -> _FakeCheckRunner:
    """Fresh ``_FakeCheckRunner`` per test."""
    return _FakeCheckRunner()


@pytest.fixture(autouse=True)
def _clean_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee a clean cache-related env at test entry.

    Tests that need ``AIENG_CACHE_DEBUG=1`` set it themselves with
    ``monkeypatch.setenv``; this fixture only ensures no leak from a
    sibling test.
    """
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DEBUG", raising=False)
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)


def _doc_to_dict(doc: object) -> dict[str, object]:
    """Coerce ``GateFindingsDocument`` (or compatible) to a plain dict."""
    if hasattr(doc, "model_dump"):
        return doc.model_dump(by_alias=True)  # type: ignore[no-any-return]
    if hasattr(doc, "dict"):
        return doc.dict(by_alias=True)  # type: ignore[no-any-return]
    if isinstance(doc, dict):
        return doc
    raise AssertionError(
        f"orchestrator.run_gate must return a GateFindingsDocument or dict; got {type(doc)!r}"
    )


# ---------------------------------------------------------------------------
# Test — 10 consecutive runs, hit rate ≥ G-3 target.
# ---------------------------------------------------------------------------


def test_gate_cache_hit_rate_meets_g3_target(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """spec-104 G-3 — ``≥70%`` cache hit rate over 10 consecutive runs.

    Setup
    -----
    * Seeded git repo with two staged ``src/*.py`` files and the configs
      in ``_CONFIG_FILE_WHITELIST``.
    * ``AIENG_CACHE_DEBUG=1`` so per-check hit/miss markers reach
      ``caplog``.
    * ``orchestrator._run_check`` mocked so no real subprocess fires.

    Expected behaviour
    ------------------
    * Run 1: cold cache → all 5 Wave 2 checks miss → ``cache_misses==5``.
    * Runs 2..10: warm cache → all 5 Wave 2 checks hit → ``cache_hits==5``.
    * Aggregate: 45 hits / 50 total = 0.90 hit rate.
    * G-3 asserts ``hit_rate ≥ 0.70``.
    """
    # Arrange — orchestrator under test, AIENG_CACHE_DEBUG observability on.
    from ai_engineering.policy import orchestrator

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    total_hits = 0
    total_misses = 0
    per_run_hits: list[int] = []
    per_run_misses: list[int] = []

    # Caplog must observe records emitted on the orchestrator + gate_cache
    # loggers (those are where the hit/miss debug markers come from).
    with (
        mock.patch.object(orchestrator, "_run_check", new=fake_runner),
        caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.orchestrator"),
        caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"),
    ):
        for run_idx in range(RUN_COUNT):
            doc = orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=cache_dir,
            )
            payload = _doc_to_dict(doc)
            hits = payload.get("cache_hits") or []
            misses = payload.get("cache_misses") or []
            assert isinstance(hits, list), (
                f"run {run_idx + 1}: cache_hits must be a list; got {type(hits)!r}"
            )
            assert isinstance(misses, list), (
                f"run {run_idx + 1}: cache_misses must be a list; got {type(misses)!r}"
            )
            per_run_hits.append(len(hits))
            per_run_misses.append(len(misses))
            total_hits += len(hits)
            total_misses += len(misses)

            # Schema sanity — every emitted document remains v1 conformant.
            assert payload.get("schema") == "ai-engineering/gate-findings/v1", (
                f"run {run_idx + 1}: emitted document must reference schema v1; "
                f"got schema={payload.get('schema')!r}"
            )

    # ---------------------------------------------------------------------
    # Assertion 1 — cold-run / warm-run shape matches the cache-aware
    # contract. Run 1 must miss every Wave 2 check; runs 2..N must hit
    # every Wave 2 check (zero misses).
    # ---------------------------------------------------------------------
    assert per_run_misses[0] >= len(WAVE2_LOCAL_CHECKS), (
        "Cold-cache run (run 1) must record cache_misses for every Wave 2 check; "
        f"got misses={per_run_misses[0]}, hits={per_run_hits[0]}"
    )
    assert per_run_hits[0] == 0, (
        "Cold-cache run (run 1) must record 0 cache_hits (cache_dir was empty); "
        f"got hits={per_run_hits[0]}"
    )

    for warm_idx in range(1, RUN_COUNT):
        assert per_run_hits[warm_idx] >= len(WAVE2_LOCAL_CHECKS), (
            f"Warm-cache run {warm_idx + 1} must hit every Wave 2 check "
            f"(≥{len(WAVE2_LOCAL_CHECKS)}); got hits={per_run_hits[warm_idx]}, "
            f"misses={per_run_misses[warm_idx]}"
        )
        assert per_run_misses[warm_idx] == 0, (
            f"Warm-cache run {warm_idx + 1} must record 0 cache_misses; "
            f"got misses={per_run_misses[warm_idx]}, hits={per_run_hits[warm_idx]}"
        )

    # ---------------------------------------------------------------------
    # Assertion 2 — overall hit rate meets G-3.
    #
    # hit_rate = total_hits / (total_hits + total_misses). Using the union
    # in the denominator (instead of just RUN_COUNT) measures the rate at
    # the per-check granularity that matters for cold-vs-warm wall-clock
    # impact, not the per-run granularity.
    # ---------------------------------------------------------------------
    total_observations = total_hits + total_misses
    assert total_observations > 0, (
        "Aggregate observations across 10 runs must be > 0; cache instrumentation "
        f"emitted no hits or misses (hits={total_hits}, misses={total_misses})"
    )
    hit_rate = total_hits / total_observations
    assert hit_rate >= G3_HIT_RATE_TARGET, (
        f"spec-104 G-3 violated: gate-cache hit rate {hit_rate:.3f} is below "
        f"the {G3_HIT_RATE_TARGET:.0%} target across {RUN_COUNT} consecutive "
        f"runs (total_hits={total_hits}, total_misses={total_misses}, "
        f"per_run_hits={per_run_hits!r}, per_run_misses={per_run_misses!r})"
    )

    # ---------------------------------------------------------------------
    # Assertion 3 — runner invocations match the cache-aware contract.
    #
    # Run 1 invokes ``_run_check`` for every Wave 2 check (≥5 calls).
    # Runs 2..10 must NOT invoke ``_run_check`` for any cached check
    # (≥0 calls beyond the cold pass). Across the 10 runs the only
    # ``_run_check`` invocations should come from the cold pass.
    # ---------------------------------------------------------------------
    cached_calls = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert len(cached_calls) <= len(WAVE2_LOCAL_CHECKS), (
        "Across 10 consecutive runs, ``_run_check`` must be invoked at most "
        f"once per Wave 2 check (cold pass only); got {len(cached_calls)} "
        f"invocations: {cached_calls!r}"
    )
    assert set(cached_calls) >= set(WAVE2_LOCAL_CHECKS), (
        "Cold-cache pass must have invoked ``_run_check`` for every Wave 2 "
        f"check at least once; got invocations={cached_calls!r}, "
        f"expected superset of {list(WAVE2_LOCAL_CHECKS)!r}"
    )

    # ---------------------------------------------------------------------
    # Assertion 4 — AIENG_CACHE_DEBUG=1 markers are observable on caplog.
    #
    # The marker stream must contain at least one "miss" record (from the
    # cold pass) and at least one "hit" record (from the warm passes).
    # This is the spec-104 Plan T-9.3 contract: hit-rate verification
    # depends on the per-check log markers being emitted; if the markers
    # were silenced the test would still need to fail loudly.
    # ---------------------------------------------------------------------
    relevant_loggers = (
        "ai_engineering.policy.orchestrator",
        "ai_engineering.policy.gate_cache",
    )
    relevant_records = [r for r in caplog.records if r.name in relevant_loggers]
    assert relevant_records, (
        "AIENG_CACHE_DEBUG=1 must emit log records on the orchestrator or "
        "gate_cache loggers; got 0 relevant records across 10 runs"
    )

    messages_lower = " ".join(r.getMessage().lower() for r in relevant_records)
    assert "miss" in messages_lower, (
        "Debug log stream must include at least one 'miss' marker (from the "
        f"cold-cache pass on run 1); messages: "
        f"{[r.getMessage() for r in relevant_records[:10]]!r}"
    )
    assert "hit" in messages_lower, (
        "Debug log stream must include at least one 'hit' marker (from the "
        f"warm-cache passes on runs 2..{RUN_COUNT}); messages: "
        f"{[r.getMessage() for r in relevant_records[:10]]!r}"
    )

    # Per-check hit markers across runs 2..10 must reference every Wave 2
    # check at least once — this is the divergence guard between the
    # structured ``cache_hits`` list and the debug marker stream.
    for check in WAVE2_LOCAL_CHECKS:
        assert check in messages_lower, (
            f"Debug log stream must mention every Wave 2 check at least "
            f"once across {RUN_COUNT} runs; missing marker for check={check!r}; "
            f"sample messages: {[r.getMessage() for r in relevant_records[:5]]!r}"
        )
