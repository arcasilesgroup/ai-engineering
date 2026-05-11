"""Parity test — `simplify-sweep.sh` and `simplify-sweep.ps1` emit byte-equivalent NDJSON.

Pairing: TDD RED partner of plan T-6.5
(`.ai-engineering/scripts/scheduled/simplify-sweep.ps1`).
**DO NOT MODIFY THIS FILE during T-6.5 GREEN.**

Three scenarios are parametrised:

1. `missing-ai-eng` — no `ai-eng` shim on PATH; both wrappers emit
   `outcome="skipped"` with `detail={"reason":"ai-eng_not_on_path"}`.
2. `present-success` — stub `ai-eng` shim exits 0; both wrappers emit
   `outcome="success"` with `detail={"mode":"conservative","pr":"deferred_to_skill"}`.
3. `present-failure` — stub `ai-eng` shim exits 1; both wrappers emit
   `outcome="failure"` with `detail={"mode":"conservative"}`.

The `timestamp` field is normalised to a fixed string before
comparison so wall-clock skew does not break the assert.

`pwsh` absence is treated as a skip (Windows CI carries it; macOS/Linux
runners may not). The POSIX leg always runs and the parity assertion
is performed only when both legs are exercised.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SH_PATH = _REPO_ROOT / ".ai-engineering" / "scripts" / "scheduled" / "simplify-sweep.sh"
_PS1_PATH = _REPO_ROOT / ".ai-engineering" / "scripts" / "scheduled" / "simplify-sweep.ps1"


def _read_emitted_line(events_file: Path) -> dict:
    """Parse the last NDJSON line from `events_file`.

    Returns a dict with `timestamp` normalised to a fixed string so two
    invocations from different wall-clock moments compare equal.
    """
    text = events_file.read_text(encoding="utf-8").strip()
    assert text, f"no events emitted to {events_file}"
    last_line = text.splitlines()[-1]
    payload = json.loads(last_line)
    payload["timestamp"] = "<normalized>"
    return payload


def _make_stub_ai_eng(bin_dir: Path, exit_code: int) -> None:
    """Place an `ai-eng` shim at `bin_dir/ai-eng` returning `exit_code`."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "ai-eng"
    shim.write_text(
        f"#!/usr/bin/env sh\nexit {exit_code}\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)


def _scenario_to_setup(scenario: str, tmp_path: Path) -> tuple[Path, str]:
    """Build the PATH for `scenario`. Returns `(events_file, modified_PATH)`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    events_dir = tmp_path / ".ai-engineering" / "state"
    events_dir.mkdir(parents=True, exist_ok=True)
    events_file = events_dir / "framework-events.ndjson"

    base_path = os.environ.get("PATH", "")
    # Strip any path that contains an existing `ai-eng` shim so the
    # missing-scenario actually misses.
    if scenario == "missing-ai-eng":
        cleaned_segments = []
        for seg in base_path.split(os.pathsep):
            if not seg:
                continue
            if (Path(seg) / "ai-eng").exists():
                continue
            cleaned_segments.append(seg)
        modified_path = os.pathsep.join(cleaned_segments)
    elif scenario == "present-success":
        _make_stub_ai_eng(bin_dir, 0)
        modified_path = os.pathsep.join([str(bin_dir), base_path])
    elif scenario == "present-failure":
        _make_stub_ai_eng(bin_dir, 1)
        modified_path = os.pathsep.join([str(bin_dir), base_path])
    else:
        raise ValueError(f"unknown scenario {scenario!r}")

    return events_file, modified_path


def _invoke(
    interpreter: list[str],
    script: Path,
    tmp_path: Path,
    modified_path: str,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PATH"] = modified_path
    env["AIENG_PROJECT_ROOT"] = str(tmp_path)
    return subprocess.run(
        interpreter + [str(script)],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


@pytest.mark.parametrize(
    "scenario",
    ["missing-ai-eng", "present-success", "present-failure"],
)
def test_sh_ps1_parity(tmp_path: Path, scenario: str) -> None:
    assert _SH_PATH.is_file(), f"expected canonical {_SH_PATH}"
    if not _PS1_PATH.is_file():
        pytest.fail(
            f"T-6.5 not landed yet — {_PS1_PATH} missing. "
            f"This is the RED state — implement the .ps1 to GREEN."
        )

    if shutil.which("pwsh") is None:
        pytest.skip("pwsh not available — parity test gated on Windows CI job")

    # POSIX leg.
    sh_events_file, sh_path = _scenario_to_setup(scenario, tmp_path / "sh")
    sh_result = _invoke(["bash"], _SH_PATH, tmp_path / "sh", sh_path)
    assert sh_result.returncode == 0, (
        f"sh wrapper must exit 0 (got {sh_result.returncode}):\nstdout={sh_result.stdout}\n"
        f"stderr={sh_result.stderr}"
    )
    sh_payload = _read_emitted_line(sh_events_file)

    # PowerShell leg.
    ps1_events_file, ps1_path = _scenario_to_setup(scenario, tmp_path / "ps1")
    ps1_result = _invoke(["pwsh", "-NoProfile", "-File"], _PS1_PATH, tmp_path / "ps1", ps1_path)
    assert ps1_result.returncode == 0, (
        f"ps1 wrapper must exit 0 (got {ps1_result.returncode}):\nstdout={ps1_result.stdout}\n"
        f"stderr={ps1_result.stderr}"
    )
    ps1_payload = _read_emitted_line(ps1_events_file)

    # Byte-equivalent payload across both runtimes (after timestamp
    # normalisation).
    assert sh_payload == ps1_payload, (
        f"{scenario}: sh and ps1 payloads differ.\nsh={sh_payload}\nps1={ps1_payload}"
    )

    # Scenario-specific outcome contract.
    expected_outcomes = {
        "missing-ai-eng": ("skipped", {"reason": "ai-eng_not_on_path"}),
        "present-success": (
            "success",
            {"mode": "conservative", "pr": "deferred_to_skill"},
        ),
        "present-failure": ("failure", {"mode": "conservative"}),
    }
    expected_outcome, expected_detail = expected_outcomes[scenario]
    assert sh_payload["outcome"] == expected_outcome, sh_payload
    assert sh_payload["detail"] == expected_detail, sh_payload
    # Constant envelope fields.
    assert sh_payload["component"] == "scheduled.simplify-sweep"
    assert sh_payload["kind"] == "framework_operation"
    assert sh_payload["operation"] == "simplify_sweep_scheduled_run"
    assert sh_payload["schemaVersion"] == "1.0"
    assert sh_payload["source"] == "scheduled"
    assert sh_payload["engine"] == "cron"
    assert sh_payload["project"] == "ai-engineering"


def test_sh_wrapper_runs_even_without_pwsh(tmp_path: Path) -> None:
    """The POSIX leg always runs (no `pwsh` dependency).

    Pins the contract that the `.sh` half is the canonical baseline —
    the parity test skips above only the cross-runtime comparison
    when `pwsh` is absent.
    """
    events_file, modified_path = _scenario_to_setup("missing-ai-eng", tmp_path)
    result = _invoke(["bash"], _SH_PATH, tmp_path, modified_path)
    assert result.returncode == 0, result.stderr
    payload = _read_emitted_line(events_file)
    assert payload["outcome"] == "skipped"
    assert payload["detail"] == {"reason": "ai-eng_not_on_path"}
