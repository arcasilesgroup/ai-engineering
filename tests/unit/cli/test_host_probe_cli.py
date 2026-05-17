"""Tests for ``ai-eng host probe`` (spec-139 M2.T3).

The CLI is a thin formatting layer over
:func:`ai_engineering.adapters.host.probe`. These tests focus on:

* JSON shape -- the payload always carries the seven canonical keys
  (``cores``, ``free_ram_gb``, ``ok_to_dispatch``, ``platform``,
  ``pressure_pct``, ``recommended_cap``, ``swap_used_pct``);
* ``--json`` pretty-prints (multi-line) versus the default one-liner;
* the CLI does NOT emit a ``host_capacity`` framework event (the
  operator is the caller, no skill dispatched per spec-139 M2.T4).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from ai_engineering.adapters.host import HostProbe

_EXPECTED_KEYS: frozenset[str] = frozenset(
    {
        "cores",
        "free_ram_gb",
        "ok_to_dispatch",
        "platform",
        "pressure_pct",
        "recommended_cap",
        "swap_used_pct",
    }
)


@pytest.fixture()
def app() -> typer.Typer:
    from ai_engineering.cli_factory import create_app

    return create_app()


@pytest.fixture()
def fake_probe() -> HostProbe:
    """A deterministic snapshot that clears every ``ok_to_dispatch`` guard."""
    return HostProbe(
        cores=8,
        free_ram_gb=16,
        pressure_pct=15,
        swap_used_pct=3,
        platform="linux",
    )


class TestHostProbeCli:
    def test_default_emits_oneline_json(self, app: typer.Typer, fake_probe: HostProbe) -> None:
        """Default output is a single-line JSON object with sorted keys."""
        with patch(
            "ai_engineering.cli_commands.host_cmd.host_probe",
            return_value=fake_probe,
        ):
            result = CliRunner().invoke(app, ["host", "probe"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert set(payload.keys()) == _EXPECTED_KEYS
        # Sorted keys → wire stability for downstream `jq` consumers.
        assert list(payload.keys()) == sorted(payload.keys())

    def test_payload_has_expected_field_values(
        self, app: typer.Typer, fake_probe: HostProbe
    ) -> None:
        """Each HostProbe field round-trips into the JSON payload unchanged."""
        with patch(
            "ai_engineering.cli_commands.host_cmd.host_probe",
            return_value=fake_probe,
        ):
            result = CliRunner().invoke(app, ["host", "probe"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["cores"] == 8
        assert payload["free_ram_gb"] == 16
        assert payload["pressure_pct"] == 15
        assert payload["swap_used_pct"] == 3
        assert payload["platform"] == "linux"
        assert payload["ok_to_dispatch"] is True
        # Auto-tune: min(16//4, 8//2, 6) = min(4, 4, 6) = 4 → still
        # clamped between WAVE_FLOOR (2) and WAVE_CEILING_AUTO (6).
        assert 2 <= payload["recommended_cap"] <= 6

    def test_json_flag_pretty_prints(self, app: typer.Typer, fake_probe: HostProbe) -> None:
        """``--json`` indents the payload for human inspection."""
        with patch(
            "ai_engineering.cli_commands.host_cmd.host_probe",
            return_value=fake_probe,
        ):
            result = CliRunner().invoke(app, ["host", "probe", "--json"])

        assert result.exit_code == 0, result.output
        # Pretty-printed → at least 2 lines (one per top-level key).
        body = result.output.strip()
        assert body.count("\n") >= 2
        # Still valid JSON.
        payload = json.loads(body)
        assert set(payload.keys()) == _EXPECTED_KEYS

    def test_ok_to_dispatch_false_when_pressure_high(self, app: typer.Typer) -> None:
        """A stressed host surfaces ``ok_to_dispatch: false`` in the JSON."""
        stressed = HostProbe(
            cores=8,
            free_ram_gb=16,
            pressure_pct=60,
            swap_used_pct=5,
            platform="darwin",
        )
        with patch(
            "ai_engineering.cli_commands.host_cmd.host_probe",
            return_value=stressed,
        ):
            result = CliRunner().invoke(app, ["host", "probe"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["ok_to_dispatch"] is False
        # Auto-tune collapses to 1 when pressure ≥ 50 (D-139-01).
        assert payload["recommended_cap"] == 1

    def test_low_ram_surfaces_floor_cap(self, app: typer.Typer) -> None:
        """1 GiB free host should produce ok_to_dispatch=False, cap=floor."""
        low_ram = HostProbe(
            cores=8,
            free_ram_gb=1,
            pressure_pct=20,
            swap_used_pct=0,
            platform="linux",
        )
        with patch(
            "ai_engineering.cli_commands.host_cmd.host_probe",
            return_value=low_ram,
        ):
            result = CliRunner().invoke(app, ["host", "probe"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["ok_to_dispatch"] is False
        # 1 GiB / 4 = 0 → clamped up to WAVE_FLOOR (2).
        assert payload["recommended_cap"] == 2

    def test_cli_does_not_emit_host_capacity_event(
        self,
        app: typer.Typer,
        fake_probe: HostProbe,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The CLI surface MUST NOT emit a ``host_capacity`` framework event.

        spec-139 M2.T4: the operator is the caller, no skill dispatched.
        Only skill-side callers (Phase 0 / step 0) emit. We assert the
        events file stays untouched by checking that the
        ``emit_host_capacity`` helper is not called during ``host probe``.
        """
        monkeypatch.chdir(tmp_path)
        with (
            patch(
                "ai_engineering.cli_commands.host_cmd.host_probe",
                return_value=fake_probe,
            ),
            patch("ai_engineering.state.observability.emit_host_capacity") as mock_emit,
        ):
            result = CliRunner().invoke(app, ["host", "probe"])

        assert result.exit_code == 0, result.output
        # The CLI must not have called the emit helper.
        mock_emit.assert_not_called()
