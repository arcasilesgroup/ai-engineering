"""spec-140 W2.T6 (D-140-06) — replacement for the help-snapshot ceremony.

The 66 help-snapshot files at ``tests/golden/cli/help_snapshots/`` were a
maintenance tax (every option rewording, every Rich box-character drift,
every Typer minor bump caused a snapshot regen). The signal the snapshot
suite carried is binary: "every top-level command is still wired into the
Typer app". This single assertion captures that signal at <50ms and
without any golden-file churn.

The redundant test surface deleted by W2.T6:

* ``tests/integration/cli/test_help_snapshots.py`` — 128-LOC parametrised
  snapshot driver.
* ``tests/golden/cli/help_snapshots/`` — 66 golden text files.
* ``tests/integration/sync/test_canonical_mirror_parity.py`` — mirror
  payload sha256 + idempotency contract (kept at
  ``tests/conformance/test_md_mirror.py``).
"""

from __future__ import annotations

from typer.testing import CliRunner

from ai_engineering.cli import app

# Canonical top-level commands the Typer factory MUST surface. Drift in
# either direction (deletion of a command, hiding it accidentally,
# accidental rename) flips this assertion.
_REQUIRED_TOP_LEVEL_COMMANDS = (
    "install",
    "doctor",
    "verify",
    "audit",
    "spec",
    "decision",
    "risk",
    "config",
    "gate",
)


def test_top_level_commands_present() -> None:
    """`ai-eng --help` lists every required top-level command."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, (
        f"`ai-eng --help` exited {result.exit_code}; stdout=\n{result.stdout}"
    )
    for command in _REQUIRED_TOP_LEVEL_COMMANDS:
        assert command in result.stdout, f"missing top-level command: {command}"
