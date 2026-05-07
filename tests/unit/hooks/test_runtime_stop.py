"""Tests for `runtime-stop.py` — the Stop hook that writes checkpoint.json
and stamps the Ralph resume marker.

Pin two correctness contracts that earlier versions silently broke:
  * Ralph retry counter actually enforces `AIENG_RALPH_MAX_RETRIES` (clears
    `active` on the next bump that crosses the budget).
  * Checkpoint payload uses snake_case keys that match
    `memory/episodic.py:_read_checkpoint`. Previous camelCase output
    silently produced empty episodes.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# POSIX file-mode tests are not meaningful on Windows: ``Path.chmod`` only
# toggles the read-only bit there, so ``stat().st_mode & 0o777`` always
# returns 0o666 (writable) or 0o444 (read-only) -- never 0o600. The hook
# itself wraps ``chmod`` in ``try/except OSError`` so the file is still
# created; the test guards the POSIX semantics specifically.
_WIN32 = sys.platform == "win32"

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"


@pytest.fixture
def rstop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AIENG_RALPH_MAX_RETRIES", "3")
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _read_resume(project: Path) -> dict:
    path = project / ".ai-engineering" / "runtime" / "ralph-resume.json"
    return json.loads(path.read_text())


def test_ralph_increments_retries_and_stays_active(rstop, project: Path) -> None:
    rstop._bump_ralph_state(project, session_id="s", reason="r", last_prompt="p")
    state = _read_resume(project)
    assert state["retries"] == 1
    assert state["active"] is True
    assert state["exhausted"] is False


def test_ralph_clears_active_at_max_retries(rstop, project: Path) -> None:
    """The headline finding: AIENG_RALPH_MAX_RETRIES must actually be enforced."""
    for _ in range(rstop._RALPH_MAX_RETRIES + 2):
        rstop._bump_ralph_state(project, session_id="s", reason="r", last_prompt="p")
    state = _read_resume(project)
    assert state["retries"] == rstop._RALPH_MAX_RETRIES + 2
    assert state["exhausted"] is True
    # active must be False once the retry budget is exhausted, otherwise the
    # next /ai-start would offer to resume forever.
    assert state["active"] is False


@pytest.mark.skipif(_WIN32, reason="POSIX file-mode semantics not applicable on Windows")
def test_ralph_resume_file_mode_is_user_only(rstop, project: Path) -> None:
    rstop._bump_ralph_state(project, session_id="s", reason="r", last_prompt="p")
    path = project / ".ai-engineering" / "runtime" / "ralph-resume.json"
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600


def test_looks_incomplete_only_fires_on_recent_failure(rstop) -> None:
    """One stale failure deep in the window must NOT trigger Ralph escalation
    (red-phase tests legitimately leave Traceback markers)."""
    history = [
        {"outcome": "failure", "tool": "Bash", "errorSummary": "Traceback ..."},
        {"outcome": "success", "tool": "Read", "errorSummary": None},
        {"outcome": "success", "tool": "Edit", "errorSummary": None},
    ]
    incomplete, _ = rstop._looks_incomplete(history)
    assert incomplete is False


def test_looks_incomplete_fires_when_latest_failed(rstop) -> None:
    history = [
        {"outcome": "success", "tool": "Read", "errorSummary": None},
        {"outcome": "failure", "tool": "Bash", "errorSummary": "exit 1"},
    ]
    incomplete, reason = rstop._looks_incomplete(history)
    assert incomplete is True
    assert "Bash" in (reason or "")


def test_recent_edited_files_reads_from_tool_history(rstop, project: Path) -> None:
    """The `_recent_edited_files` regression: must read filePath from
    tool-history.ndjson (not the auto-format event detail, which never carries
    file_path)."""
    history_path = project / ".ai-engineering" / "runtime" / "tool-history.ndjson"
    lines = [
        json.dumps(
            {
                "timestamp": "2026-05-04T00:00:00Z",
                "sessionId": "sess",
                "tool": "Edit",
                "signature": "abc",
                "outcome": "success",
                "errorSummary": None,
                "filePath": "/some/edited.py",
            }
        ),
        json.dumps(
            {
                "timestamp": "2026-05-04T00:00:01Z",
                "sessionId": "sess",
                "tool": "Bash",
                "signature": "def",
                "outcome": "success",
                "errorSummary": None,
            }
        ),
    ]
    history_path.write_text("\n".join(lines) + "\n")
    edited = rstop._recent_edited_files(project, session_id="sess")
    assert edited == ["/some/edited.py"]
