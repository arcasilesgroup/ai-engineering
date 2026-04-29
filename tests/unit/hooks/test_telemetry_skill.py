"""Tests for telemetry-skill.py skill name extraction (spec-112 T-1.1..T-1.3).

Covers G-1: regex extraction of `^/ai-([a-zA-Z0-9_-]+)` from `payload.prompt`,
including edge cases that emit `kind: skill_invoked_malformed` with
`detail.skill: null`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parents[3]
    / ".ai-engineering"
    / "scripts"
    / "hooks"
    / "telemetry-skill.py"
)


def _ndjson_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _read_events(project_root: Path) -> list[dict]:
    path = _ndjson_path(project_root)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def _run_hook(project_root: Path, prompt: str) -> int:
    payload = json.dumps({"prompt": prompt, "cwd": str(project_root)})
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    env["CLAUDE_HOOK_EVENT_NAME"] = "UserPromptSubmit"
    env["AIENG_HOOK_ENGINE"] = "claude_code"
    # Avoid CI noise muting violations for our deterministic tests
    env.pop("CI", None)
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    return result.returncode


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Minimal project root with .ai-engineering/state present."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# 10 valid prompt fixtures: each maps prompt -> expected detail.skill
# ---------------------------------------------------------------------------

VALID_PROMPTS: list[tuple[str, str]] = [
    ("/ai-brainstorm", "ai-brainstorm"),
    ("/ai-plan", "ai-plan"),
    ("/ai-brainstorm topic about telemetry", "ai-brainstorm"),
    ("/ai-research --depth=deep query body", "ai-research"),
    ("/ai-test\n", "ai-test"),
    ("/ai-debug some failing test", "ai-debug"),
    ("  /ai-commit", "ai-commit"),  # leading whitespace tolerated
    ("/ai-skill-evolve\n\nrest of body", "ai-skill-evolve"),  # hyphenated skill
    ("/ai-pr open it", "ai-pr"),
    ("/ai-Review camelCase folded", "ai-review"),  # lowercased
]


@pytest.mark.parametrize(("prompt", "expected"), VALID_PROMPTS)
def test_skill_name_extraction(project_root: Path, prompt: str, expected: str) -> None:
    """For valid prompts, telemetry-skill emits skill_invoked with detail.skill = expected."""
    rc = _run_hook(project_root, prompt)
    assert rc == 0, "telemetry-skill must always exit 0 (fail-open)"
    events = _read_events(project_root)
    skill_events = [e for e in events if e.get("kind") == "skill_invoked"]
    assert skill_events, f"no skill_invoked event emitted for prompt={prompt!r}; events={events}"
    last = skill_events[-1]
    assert last["detail"]["skill"] == expected, (
        f"skill mismatch for prompt={prompt!r}: got {last['detail']['skill']!r}, want {expected!r}"
    )
    # Bug guard: must NEVER emit hardcoded project name as skill (the historical bug).
    assert last["detail"]["skill"] != "ai-engineering"


# ---------------------------------------------------------------------------
# 2 edge case fixtures: empty prompt + prompt without /ai- prefix
# Both must emit `kind: skill_invoked_malformed` with `detail.skill: null`.
# ---------------------------------------------------------------------------


def test_empty_prompt_emits_malformed(project_root: Path) -> None:
    rc = _run_hook(project_root, "")
    assert rc == 0
    events = _read_events(project_root)
    malformed = [e for e in events if e.get("kind") == "skill_invoked_malformed"]
    assert malformed, f"empty prompt must emit skill_invoked_malformed; events={events}"
    assert malformed[-1]["detail"]["skill"] is None
    assert malformed[-1]["detail"].get("reason") == "empty_prompt"


def test_prompt_without_ai_prefix_emits_malformed(project_root: Path) -> None:
    rc = _run_hook(project_root, "hello world without slash command")
    assert rc == 0
    events = _read_events(project_root)
    malformed = [e for e in events if e.get("kind") == "skill_invoked_malformed"]
    assert malformed, f"non-/ai- prompt must emit skill_invoked_malformed; events={events}"
    assert malformed[-1]["detail"]["skill"] is None
    assert malformed[-1]["detail"].get("reason") == "no_ai_prefix"
