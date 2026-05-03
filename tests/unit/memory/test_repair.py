"""spec-118 T-2.6 -- repair.backfill_timestamps coverage."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.memory


def _seed_observations(project_root, lines):
    path = project_root / ".ai-engineering" / "state" / "instinct-observations.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(o, sort_keys=True) for o in lines) + "\n")
    return path


def test_no_file_returns_zero(memory_project):
    from memory import repair

    report = repair.backfill_timestamps(memory_project)
    assert report.total_lines == 0
    assert report.backfilled == 0


def test_already_valid_records_untouched(memory_project):
    from memory import repair

    valid = {"timestamp": "2026-04-01T12:00:00Z", "kind": "tool_complete", "tool": "Read"}
    _seed_observations(memory_project, [valid])
    report = repair.backfill_timestamps(memory_project)
    assert report.already_valid == 1
    assert report.backfilled == 0
    assert report.backup_path is None


def test_empty_timestamp_backfilled(memory_project):
    from memory import repair

    invalid = {"timestamp": "", "kind": "tool_complete", "tool": "Edit"}
    path = _seed_observations(memory_project, [invalid, invalid])
    report = repair.backfill_timestamps(memory_project)
    assert report.backfilled == 2
    assert report.already_valid == 0
    rebuilt = path.read_text(encoding="utf-8").strip().splitlines()
    for line in rebuilt:
        record = json.loads(line)
        assert record["timestamp"]
        assert record["timestamp"] != ""


def test_backup_written_only_when_backfilled(memory_project):
    from memory import repair

    invalid = {"timestamp": "", "kind": "tool_complete", "tool": "Bash"}
    _seed_observations(memory_project, [invalid])
    report = repair.backfill_timestamps(memory_project)
    assert report.backup_path is not None


def test_idempotent_second_run_no_backfill(memory_project):
    from memory import repair

    invalid = {"timestamp": "", "kind": "tool_complete", "tool": "Bash"}
    _seed_observations(memory_project, [invalid])
    repair.backfill_timestamps(memory_project)
    report2 = repair.backfill_timestamps(memory_project)
    assert report2.backfilled == 0
    assert report2.already_valid >= 1


def test_malformed_json_counted_not_crash(memory_project):
    from memory import repair

    path = memory_project / ".ai-engineering" / "state" / "instinct-observations.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json\n" + json.dumps({"timestamp": "", "tool": "x"}) + "\n")
    report = repair.backfill_timestamps(memory_project)
    assert report.malformed == 1
    assert report.backfilled == 1
