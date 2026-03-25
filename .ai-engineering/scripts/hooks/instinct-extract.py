#!/usr/bin/env python3
"""Stop hook: extract behavioral instincts from tool usage observations.

Reads observations.jsonl for the current project, detects usage patterns
(tool frequency, sequence pairs, error recovery), and writes instinct
YAML files for future sessions.

Async, timeout 30s, fail-open: exit 0 always.
"""

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import (
    append_audit_event,
    get_audit_log,
    get_project_root,
    is_debug_mode,
    read_stdin,
)

_INSTINCTS_BASE = Path.home() / ".ai-engineering" / "instincts"
_MIN_OBSERVATIONS = 50
_MIN_TOOL_FREQUENCY = 5
_MIN_SEQUENCE_PAIRS = 3


def _get_project_hash() -> str:
    """SHA256 of git remote URL (first 8 chars), fallback to cwd hash."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            digest = hashlib.sha256(result.stdout.strip().encode()).hexdigest()[:8]
            return digest
    except Exception:
        pass
    digest = hashlib.sha256(os.getcwd().encode()).hexdigest()[:8]
    return digest


def _get_project_dir(project_hash: str) -> Path:
    return _INSTINCTS_BASE / "projects" / project_hash


def _read_observations(project_dir: Path) -> list[dict]:
    """Read all observations from observations.jsonl."""
    obs_file = project_dir / "observations.jsonl"
    if not obs_file.exists():
        return []
    observations = []
    try:
        with open(obs_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        observations.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return observations


def _get_new_observation_count(project_dir: Path, total_count: int) -> int:
    """Count observations since last extraction."""
    marker_file = project_dir / ".last-extract"
    if not marker_file.exists():
        return total_count
    try:
        with open(marker_file, encoding="utf-8") as f:
            last_count = int(f.read().strip())
        return max(0, total_count - last_count)
    except (ValueError, OSError):
        return total_count


def _update_marker(project_dir: Path, total_count: int) -> None:
    """Update the .last-extract marker with current observation count."""
    marker_file = project_dir / ".last-extract"
    try:
        with open(marker_file, "w", encoding="utf-8") as f:
            f.write(str(total_count))
    except Exception:
        pass


def _detect_tool_frequency(observations: list[dict]) -> list[dict]:
    """Detect tools used >= _MIN_TOOL_FREQUENCY times."""
    tool_counts: Counter[str] = Counter()
    for obs in observations:
        tool = obs.get("tool", "")
        if tool:
            tool_counts[tool] += 1

    frequent = []
    for tool, count in tool_counts.most_common():
        if count >= _MIN_TOOL_FREQUENCY:
            frequent.append({"tool": tool, "count": count})
    return frequent


def _detect_sequence_pairs(observations: list[dict]) -> list[dict]:
    """Detect consecutive tool A -> B pairs appearing >= _MIN_SEQUENCE_PAIRS times."""
    pair_counts: Counter[tuple[str, str]] = Counter()
    prev_tool = ""
    for obs in observations:
        tool = obs.get("tool", "")
        if not tool:
            continue
        if prev_tool and obs.get("type") == "tool_start":
            pair_counts[(prev_tool, tool)] += 1
        if obs.get("type") == "tool_complete":
            prev_tool = tool
        elif obs.get("type") == "tool_start":
            prev_tool = ""

    pairs = []
    for (tool_a, tool_b), count in pair_counts.most_common():
        if count >= _MIN_SEQUENCE_PAIRS:
            pairs.append({"from": tool_a, "to": tool_b, "count": count})
    return pairs


def _detect_error_recovery(observations: list[dict]) -> list[dict]:
    """Detect tool_complete with error followed by a fix attempt."""
    recoveries = []
    for i, obs in enumerate(observations):
        if obs.get("type") != "tool_complete":
            continue
        output = obs.get("output", "")
        if not isinstance(output, str):
            output = str(output)
        has_error = any(
            keyword in output.lower()
            for keyword in ("error", "exception", "failed", "traceback", "errno")
        )
        if not has_error:
            continue
        if i + 1 < len(observations):
            next_obs = observations[i + 1]
            if next_obs.get("type") == "tool_start":
                recoveries.append(
                    {
                        "failed_tool": obs.get("tool", ""),
                        "recovery_tool": next_obs.get("tool", ""),
                        "error_snippet": output[:200],
                    }
                )
    return recoveries


def _generate_instinct_yaml(
    instinct_type: str,
    data: list[dict],
    project_hash: str,
) -> str:
    """Generate a YAML instinct file content."""
    instinct_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"id: {instinct_type}-{instinct_id}",
        f"type: {instinct_type}",
        f"project: {project_hash}",
        f"extractedAt: {timestamp}",
        "source: observation-mining",
        "data:",
    ]

    for item in data:
        lines.append("  - ")
        for key, value in item.items():
            safe_value = str(value).replace("\n", " ").replace('"', "'")
            if len(safe_value) > 200:
                safe_value = safe_value[:200] + "..."
            lines.append(f'    {key}: "{safe_value}"')

    return "\n".join(lines) + "\n"


def _write_instinct(project_hash: str, instinct_type: str, content: str) -> Path:
    """Write an instinct YAML file."""
    instinct_dir = _get_project_dir(project_hash) / "instincts" / "personal"
    instinct_dir.mkdir(parents=True, exist_ok=True)

    instinct_id = str(uuid.uuid4())[:8]
    filename = f"{instinct_type}-{instinct_id}.yaml"
    instinct_path = instinct_dir / filename

    try:
        with open(instinct_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

    return instinct_path


def main() -> None:
    _ = read_stdin()

    min_observations = _MIN_OBSERVATIONS
    env_min = os.environ.get("AIE_INSTINCT_MIN_OBSERVATIONS")
    if env_min:
        with contextlib.suppress(ValueError):
            min_observations = int(env_min)

    project_hash = _get_project_hash()
    project_dir = _get_project_dir(project_hash)

    observations = _read_observations(project_dir)
    total_count = len(observations)

    new_count = _get_new_observation_count(project_dir, total_count)
    if new_count < min_observations:
        return

    extracted_types = []

    tool_freq = _detect_tool_frequency(observations)
    if tool_freq:
        content = _generate_instinct_yaml("tool_frequency", tool_freq, project_hash)
        _write_instinct(project_hash, "tool_frequency", content)
        extracted_types.append("tool_frequency")

    seq_pairs = _detect_sequence_pairs(observations)
    if seq_pairs:
        content = _generate_instinct_yaml("sequence_pairs", seq_pairs, project_hash)
        _write_instinct(project_hash, "sequence_pairs", content)
        extracted_types.append("sequence_pairs")

    error_recovery = _detect_error_recovery(observations)
    if error_recovery:
        content = _generate_instinct_yaml("error_recovery", error_recovery, project_hash)
        _write_instinct(project_hash, "error_recovery", content)
        extracted_types.append("error_recovery")

    if extracted_types:
        project_root = get_project_root()
        audit_log = get_audit_log(project_root)
        append_audit_event(
            audit_log,
            {
                "event": "instinct_extracted",
                "actor": "ai",
                "detail": {
                    "project_hash": project_hash,
                    "instinct_types": extracted_types,
                    "observation_count": total_count,
                    "new_observations": new_count,
                },
            },
            project_root=project_root,
        )

    _update_marker(project_dir, total_count)

    if is_debug_mode():
        project_root = get_project_root()
        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(
                    f"[{timestamp}] instinct-extract: project={project_hash} "
                    f"new={new_count} types={extracted_types}\n"
                )
        except Exception:
            pass


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
