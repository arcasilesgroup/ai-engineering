"""Tests for ``plan_tasks.py`` — sub-plan checkbox / frontmatter sync.

Driven by the brainstorm finding that autopilot sub-plans drift between
their frontmatter (``total: N``, ``completed: M``) and the real checkbox
count in the body. The script is the canonical sync point for both
Phase 2 (deep-plan) and Phase 4 (implement) of ai-autopilot.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".ai-engineering" / "scripts" / "plan_tasks.py"
SCRIPT_DIR = SCRIPT.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import plan_tasks  # noqa: E402

# ---------------------------------------------------------------------------
# Domain — pure counting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_count_tasks_canonical_format() -> None:
    body = """## Plan

- [ ] T-1.1: First task
- [x] T-1.2: Second task
- [x] T-1.3: Third task
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 3
    assert counts.completed == 2


@pytest.mark.unit
def test_count_tasks_indented_subitems_not_counted() -> None:
    body = """## Plan

- [ ] T-1.1: First task
  - **Files**: foo.py
  - **Done**: condition
- [x] T-1.2: Second task
  - **Files**: bar.py
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 2
    assert counts.completed == 1


@pytest.mark.unit
def test_count_tasks_bullets_without_checkboxes_are_zero() -> None:
    body = """## Plan

- **T-2.1** — RED: write tests
- **T-2.2** — GREEN: implement
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 0
    assert counts.completed == 0


@pytest.mark.unit
def test_count_tasks_headers_only_are_zero() -> None:
    body = """## Plan

### Task 1 — TDD RED

### Task 2 — Module rename
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 0
    assert counts.completed == 0


@pytest.mark.unit
def test_count_tasks_empty_placeholder_body_is_zero() -> None:
    body = """## Plan
[EMPTY — populated by Phase 2]
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 0
    assert counts.completed == 0


@pytest.mark.unit
def test_count_tasks_x_is_case_insensitive() -> None:
    body = """- [X] T-1.1
- [x] T-1.2
- [ ] T-1.3
"""
    counts = plan_tasks.count_tasks(body)
    assert counts.total == 3
    assert counts.completed == 2


# ---------------------------------------------------------------------------
# Frontmatter parsing + rewrite
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_frontmatter_present() -> None:
    text = "---\ntotal: 14\ncompleted: 7\n---\n\nbody\n"
    fm, body = plan_tasks.parse_frontmatter(text)
    assert fm == {"total": "14", "completed": "7"}
    assert body == "\nbody\n"


@pytest.mark.unit
def test_parse_frontmatter_absent() -> None:
    text = "# Plan\n\nbody only\n"
    fm, body = plan_tasks.parse_frontmatter(text)
    assert fm == {}
    assert body == text


@pytest.mark.unit
def test_render_frontmatter_round_trip() -> None:
    rendered = plan_tasks.render_frontmatter({"total": 3, "completed": 2}, "\nbody\n")
    assert rendered.startswith("---\ntotal: 3\ncompleted: 2\n---\n")
    assert rendered.endswith("\nbody\n")


# ---------------------------------------------------------------------------
# sync — file-level integration
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.unit
def test_sync_updates_drifted_frontmatter(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 99
completed: 42
---

## Plan

- [ ] T-1.1: a
- [x] T-1.2: b
""",
    )
    changed = plan_tasks.sync(plan)
    assert changed is True
    text = plan.read_text(encoding="utf-8")
    assert text.startswith("---\ntotal: 2\ncompleted: 1\n---\n")


@pytest.mark.unit
def test_sync_is_idempotent_when_in_sync(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 2
completed: 1
---

- [ ] T-1.1: a
- [x] T-1.2: b
""",
    )
    changed = plan_tasks.sync(plan)
    assert changed is False


@pytest.mark.unit
def test_sync_inserts_frontmatter_when_missing(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """# Plan

- [ ] T-1.1: a
- [x] T-1.2: b
""",
    )
    changed = plan_tasks.sync(plan)
    assert changed is True
    text = plan.read_text(encoding="utf-8")
    assert text.startswith("---\ntotal: 2\ncompleted: 1\n---\n")


@pytest.mark.unit
def test_sync_rewrites_invented_frontmatter_with_no_checkboxes(tmp_path: Path) -> None:
    """sub-002 / sub-004 pattern: frontmatter invented, body has no checkboxes."""
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 14
completed: 0
---

## Plan

### Task 1 — RED
### Task 2 — GREEN
""",
    )
    changed = plan_tasks.sync(plan)
    assert changed is True
    text = plan.read_text(encoding="utf-8")
    assert text.startswith("---\ntotal: 0\ncompleted: 0\n---\n")


@pytest.mark.unit
def test_sync_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        plan_tasks.sync(tmp_path / "nope.md")


# ---------------------------------------------------------------------------
# validate — Phase 2 gate (>= 2 canonical checkbox tasks)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_passes_with_two_or_more_tasks(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 0
completed: 0
---

- [ ] T-1.1: a
- [ ] T-1.2: b
""",
    )
    ok, reason = plan_tasks.validate(plan)
    assert ok is True, reason


@pytest.mark.unit
def test_validate_fails_with_zero_tasks(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """## Plan
[EMPTY — populated by Phase 2]
""",
    )
    ok, reason = plan_tasks.validate(plan)
    assert ok is False
    assert "0" in reason or "no" in reason.lower() or "zero" in reason.lower()


@pytest.mark.unit
def test_validate_fails_with_one_task(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """- [ ] T-1.1: only one
""",
    )
    ok, _reason = plan_tasks.validate(plan)
    assert ok is False


@pytest.mark.unit
def test_validate_fails_on_bullet_only_format(tmp_path: Path) -> None:
    """sub-002 pattern: bullets without checkbox brackets fail the gate."""
    plan = _write(
        tmp_path / "plan.md",
        """## Plan

- **T-2.1** — RED: write tests
- **T-2.2** — GREEN: implement
""",
    )
    ok, reason = plan_tasks.validate(plan)
    assert ok is False
    assert "0" in reason or "checkbox" in reason.lower()


@pytest.mark.unit
def test_validate_syncs_as_side_effect(tmp_path: Path) -> None:
    """validate must sync frontmatter even when it passes — so completed counts stay honest."""
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 99
completed: 99
---

- [ ] T-1.1: a
- [x] T-1.2: b
""",
    )
    ok, _ = plan_tasks.validate(plan)
    assert ok is True
    text = plan.read_text(encoding="utf-8")
    assert text.startswith("---\ntotal: 2\ncompleted: 1\n---\n")


# ---------------------------------------------------------------------------
# CLI — exit codes
# ---------------------------------------------------------------------------


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
def test_cli_sync_exits_zero(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """---
total: 1
completed: 1
---

- [x] T-1.1: done
- [ ] T-1.2: not done
""",
    )
    result = _run(["sync", str(plan)])
    assert result.returncode == 0, result.stderr
    text = plan.read_text(encoding="utf-8")
    assert "total: 2" in text
    assert "completed: 1" in text


@pytest.mark.unit
def test_cli_validate_exits_zero_on_pass(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """- [ ] T-1.1: a
- [ ] T-1.2: b
""",
    )
    result = _run(["validate", str(plan)])
    assert result.returncode == 0, result.stderr


@pytest.mark.unit
def test_cli_validate_exits_nonzero_on_fail(tmp_path: Path) -> None:
    plan = _write(
        tmp_path / "plan.md",
        """## Plan
[EMPTY]
""",
    )
    result = _run(["validate", str(plan)])
    assert result.returncode != 0


@pytest.mark.unit
def test_cli_sync_exits_nonzero_on_missing_file(tmp_path: Path) -> None:
    result = _run(["sync", str(tmp_path / "missing.md")])
    assert result.returncode != 0


@pytest.mark.unit
def test_cli_no_subcommand_exits_nonzero() -> None:
    result = _run([])
    assert result.returncode != 0
