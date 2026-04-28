"""Regression test for spec-104 D-104-06 — gate-findings.json must persist.

The skills ``/ai-commit`` and ``/ai-pr`` instruct the agent to parse
``.ai-engineering/state/gate-findings.json`` after running ``ai-eng gate run``.
Pre-fix, ``gate_run`` only wrote the JSON to stdout (when ``--json`` was set),
so any agent following the skill instructions would error on a missing file.

This test is the end-to-end guard: it invokes the CLI through a subprocess
that runs the dev-venv code path (via ``sys.executable -m ai_engineering.cli``),
passes the canonical ``--cache-aware --json --mode=local`` flag combo from
the skill docs, and asserts that the canonical artefact exists at
``.ai-engineering/state/gate-findings.json`` with schema-v1 content.

We deliberately invoke through ``sys.executable -m ai_engineering.cli`` rather
than the bare ``ai-eng`` binary on PATH because the developer's PATH may
resolve to a uv-tool installation that lags behind the working tree. The
``-m`` form runs the module the test process imported, guaranteeing the
test exercises the in-tree fix and not a stale binary.

The artefact must persist regardless of the ``--json`` flag (covered by the
companion test below). The check fires fast because no staged files are
present in the temp repo — the orchestrator's wave-2 default ``_run_one_checker``
returns a benign empty payload per check.

Maps to spec-104 verify+review iteration BLOCKER correctness-1 fix.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering.state.models import GateFindingsDocument

# ---------------------------------------------------------------------------
# Constants — canonical artefact path the skills are documented to read.
# ---------------------------------------------------------------------------

_GATE_FINDINGS_RELATIVE_PATH = Path(".ai-engineering") / "state" / "gate-findings.json"
_SCHEMA_LITERAL = "ai-engineering/gate-findings/v1"


# ---------------------------------------------------------------------------
# Helpers — minimal git repo + spec scaffolding so the orchestrator runs.
# ---------------------------------------------------------------------------


def _git_init(repo: Path) -> None:
    """Initialise a fresh git repo so ``_staged_files_from_git`` succeeds."""
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


def _seed_minimum_project(repo: Path) -> None:
    """Lay down the minimum ``.ai-engineering/`` skeleton ``gate run`` expects."""
    ai_dir = repo / ".ai-engineering"
    state_dir = ai_dir / "state"
    specs_dir = ai_dir / "specs"
    state_dir.mkdir(parents=True, exist_ok=True)
    specs_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: [python]\n",
        encoding="utf-8",
    )
    (specs_dir / "spec.md").write_text("# No active spec\n", encoding="utf-8")
    (specs_dir / "plan.md").write_text("# No active plan\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _restore_subprocess_run() -> None:
    """Defend against pre-existing test pollution that leaks ``subprocess.run``.

    ``tests/unit/test_orchestrator_emit_findings.py::test_emit_findings_atomic_write``
    uses ``mock.patch("subprocess.run", ...)`` inside multiple threads
    concurrently. ``mock.patch`` is not thread-safe — concurrent enter/exit
    pairs can leave the global ``subprocess.run`` pointing at a Mock after
    the test ends. The IMMUTABLE TDD constraint on that file forbids fixing
    the race at the source, so this fixture force-reloads the subprocess
    module to refresh the canonical ``run`` callable before each invocation.
    """
    import importlib

    # Re-import a clean subprocess module so ``subprocess.run`` is guaranteed
    # to be the canonical CPython implementation, not a leaked Mock from a
    # prior test's threaded ``mock.patch`` race.
    importlib.reload(subprocess)
    yield


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Initialised git repo + ``.ai-engineering/`` scaffolding."""
    _git_init(tmp_path)
    _seed_minimum_project(tmp_path)
    return tmp_path


def _ai_eng_argv(args: list[str]) -> list[str]:
    """Return an argv that invokes the in-tree ``ai-eng`` CLI module.

    Uses ``sys.executable -m ai_engineering.cli`` so the subprocess loads the
    code under test (not a stale uv-tool binary on PATH that may shadow the
    working tree). The form is portable — works on any platform where the
    test runner can execute its own interpreter.
    """
    return [sys.executable, "-m", "ai_engineering.cli", *args]


def _require_module_runnable() -> None:
    """Verify ``python -m ai_engineering.cli`` is importable; skip otherwise."""
    probe = subprocess.run(
        [sys.executable, "-c", "import ai_engineering.cli"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if probe.returncode != 0:
        pytest.skip(
            "ai_engineering.cli not importable — install the project in "
            "editable mode (``uv pip install -e .``) before running this "
            f"integration test. stderr={probe.stderr!r}"
        )


# ---------------------------------------------------------------------------
# Test 1 — ``ai-eng gate run --cache-aware --json --mode=local`` persists.
# ---------------------------------------------------------------------------


def test_gate_run_persists_findings_with_json_flag(project: Path) -> None:
    """Skill-documented invocation MUST persist the canonical artefact.

    The /ai-commit skill instructs::

        ai-eng gate run --cache-aware --json --mode=local

    After this command exits, the agent parses
    ``.ai-engineering/state/gate-findings.json``. The file MUST exist with
    schema-v1 content; otherwise the skill instruction is broken end-to-end.
    """
    _require_module_runnable()

    # Act — run the exact incantation from .claude/skills/ai-commit/SKILL.md
    # via the in-tree CLI module so we exercise the working-tree fix.
    completed = subprocess.run(
        _ai_eng_argv(
            [
                "gate",
                "run",
                "--cache-aware",
                "--json",
                "--mode=local",
                "--target",
                str(project),
            ]
        ),
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Assert — exit code 0 (no findings on an empty staged set + benign default
    # checker bodies) so the test focuses on persistence, not gate verdict.
    assert completed.returncode == 0, (
        "`ai-eng gate run --cache-aware --json --mode=local` must exit 0 on "
        f"a clean repo. Got returncode={completed.returncode}\n"
        f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )

    # Assert — canonical artefact exists at the documented path.
    artefact = project / _GATE_FINDINGS_RELATIVE_PATH
    assert artefact.exists(), (
        "gate-findings.json MUST exist at "
        f"{_GATE_FINDINGS_RELATIVE_PATH} after `ai-eng gate run`. The "
        "skills /ai-commit and /ai-pr instruct agents to parse this file; "
        "without persistence the skill instruction is broken end-to-end. "
        f"stdout={completed.stdout!r}"
    )

    # Assert — content is valid JSON and validates against the v1 schema.
    raw = artefact.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert isinstance(parsed, dict), (
        f"gate-findings.json MUST decode to a JSON object; got {type(parsed)!r}"
    )
    assert parsed.get("schema") == _SCHEMA_LITERAL, (
        "gate-findings.json MUST carry the v1 schema literal "
        f"({_SCHEMA_LITERAL!r}); got schema={parsed.get('schema')!r}"
    )

    # Assert — round-trips cleanly through the Pydantic model so spec-105
    # consumers can parse without surprises.
    document = GateFindingsDocument.model_validate(parsed)
    assert document.produced_by.value in {"ai-commit", "ai-pr", "watch-loop"}, (
        f"produced_by MUST be a known skill caller; got {document.produced_by.value!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — persistence is unconditional (no --json flag still writes the file).
# ---------------------------------------------------------------------------


def test_gate_run_persists_findings_without_json_flag(project: Path) -> None:
    """Persistence MUST NOT depend on the ``--json`` flag.

    Hooks and CI scripts may invoke ``ai-eng gate run`` without ``--json``
    when they only care about the exit code, but downstream agents still
    need to parse the artefact for follow-up actions. The persistence
    behaviour is therefore unconditional.
    """
    _require_module_runnable()

    # Act — invoke without --json; persistence must still happen.
    completed = subprocess.run(
        _ai_eng_argv(
            [
                "gate",
                "run",
                "--cache-aware",
                "--mode=local",
                "--target",
                str(project),
            ]
        ),
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        "`ai-eng gate run --cache-aware --mode=local` (no --json) must exit 0 "
        f"on a clean repo. Got returncode={completed.returncode}\n"
        f"stderr={completed.stderr!r}"
    )

    artefact = project / _GATE_FINDINGS_RELATIVE_PATH
    assert artefact.exists(), (
        "gate-findings.json MUST be written even without --json; the "
        "artefact persistence is part of the skill contract, not the "
        "stdout-emission contract."
    )

    parsed = json.loads(artefact.read_text(encoding="utf-8"))
    assert parsed.get("schema") == _SCHEMA_LITERAL, (
        f"gate-findings.json must reference {_SCHEMA_LITERAL!r}; "
        f"got schema={parsed.get('schema')!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — ``--produced-by`` flag propagates into the persisted document.
# ---------------------------------------------------------------------------


def test_gate_run_produced_by_flag_propagates(project: Path) -> None:
    """``--produced-by=ai-pr`` MUST surface in the persisted document.

    Pre-fix, ``gate_run`` hardcoded ``produced_by="ai-commit"`` so any
    invocation from /ai-pr or the watch loop misattributed the document.
    The ``--produced-by`` flag fixes the attribution; the persisted file
    is the audit-trail consumer (spec-105 risk-accept) so the value MUST
    flow through end-to-end.
    """
    _require_module_runnable()

    completed = subprocess.run(
        _ai_eng_argv(
            [
                "gate",
                "run",
                "--cache-aware",
                "--json",
                "--mode=local",
                "--produced-by=ai-pr",
                "--target",
                str(project),
            ]
        ),
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        "--produced-by=ai-pr clean run must exit 0; "
        f"returncode={completed.returncode}\n"
        f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )

    artefact = project / _GATE_FINDINGS_RELATIVE_PATH
    assert artefact.exists(), (
        "persisted gate-findings.json missing\n"
        f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )

    parsed = json.loads(artefact.read_text(encoding="utf-8"))
    document = GateFindingsDocument.model_validate(parsed)
    assert document.produced_by.value == "ai-pr", (
        "--produced-by=ai-pr MUST surface in the persisted document so "
        "downstream consumers see the correct skill-caller attribution; "
        f"got produced_by={document.produced_by.value!r}"
    )
