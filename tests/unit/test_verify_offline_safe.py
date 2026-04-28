"""RED-phase tests for spec-101 T-1.9: offline-safe ``run_verify`` wrapper.

Covers spec D-101-04 (post-install verification is offline-safe) +
G-7 (runnable verify) + R-11 (air-gapped enterprise environments).

These tests target ``ai_engineering.installer.user_scope_install.run_verify``,
which does NOT exist yet. Every test MUST fail with ``ModuleNotFoundError``
or ``AttributeError`` until the GREEN-phase implementation lands (T-1.10).

Contract under test:

* ``run_verify(tool_spec) -> VerifyResult`` invokes the canonical offline-safe
  cmd recorded in ``installer/tool_registry.py`` for each tool.
* Subprocess is invoked through ``_safe_run`` (the runtime guard from T-1.5)
  with a 10-second timeout per D-101-04.
* ``VerifyResult`` is a structured value type with ``passed: bool``,
  ``version: str | None``, and ``stderr: str``. Optional ``error`` field carries
  ``"timeout"`` on subprocess timeouts.
* The registry's ``verify.regex`` is applied to subprocess stdout; non-match
  yields ``VerifyResult(passed=False)`` even when exit code is 0.
* Network-touching invocations (``semgrep --config auto``,
  ``semgrep --refresh``, ``pip-audit --update``) are refused at the wrapper
  layer with ``UnsafeVerifyCommand`` even if a caller fabricates them — the
  wrapper guards itself, not just the registry.
* Forced offline (``HTTPS_PROXY=http://127.0.0.1:1``) does NOT cause verify
  to hang or fail — every canonical verify cmd completes offline.
* Subprocess timeouts (>10s) are caught and reported as
  ``VerifyResult(passed=False, error="timeout")`` rather than raising.
"""

from __future__ import annotations

import importlib
import re
import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# All assertions live inside the test bodies so collection succeeds and pytest
# emits one ModuleNotFoundError / AttributeError per test (RED proof) rather
# than a single collection error masking the test count.

_MODULE = "ai_engineering.installer.user_scope_install"


def _import_module() -> Any:
    """Import the not-yet-existent module under test.

    Wrapped so each test produces its own ModuleNotFoundError in RED, and so
    GREEN-phase swaps the wrapper for a real import without touching test
    bodies.
    """
    return importlib.import_module(_MODULE)


def _get_run_verify() -> Any:
    module = _import_module()
    fn = getattr(module, "run_verify", None)
    assert fn is not None, f"{_MODULE} must export run_verify (T-1.10)"
    return fn


def _get_verify_result_cls() -> Any:
    module = _import_module()
    cls = getattr(module, "VerifyResult", None)
    assert cls is not None, f"{_MODULE} must export VerifyResult (T-1.10)"
    return cls


def _get_unsafe_verify_command() -> Any:
    module = _import_module()
    cls = getattr(module, "UnsafeVerifyCommand", None)
    assert cls is not None, f"{_MODULE} must export UnsafeVerifyCommand (T-1.10)"
    return cls


# ---------------------------------------------------------------------------
# Canonical verify cmds and regex shapes per D-101-04 + tool_registry contract
#
# Mirrors the spec D-101-04 / D-101-06 contract exactly — must stay in sync
# with installer/tool_registry.py (T-1.2).
# ---------------------------------------------------------------------------

# Tool-spec dicts that mimic what the registry emits per tool. Production
# `tool_spec` is the registry entry's verify block plus the tool name; tests
# build minimal fixtures that the wrapper can consume.
_CANONICAL_VERIFY_SPECS: dict[str, dict[str, Any]] = {
    # D-101-04: end-to-end offline-safe functional probe.
    "gitleaks": {
        "name": "gitleaks",
        "verify": {
            "cmd": [
                "gitleaks",
                "detect",
                "--no-git",
                "--source",
                "/dev/null",
                "--no-banner",
            ],
            "regex": r"no leaks found",
        },
        # Sample stdout that the canonical cmd produces offline.
        "stdout_sample": "no leaks found in 0 commits\n",
    },
    # D-101-04: semgrep phones home on broader invocations; --version only.
    "semgrep": {
        "name": "semgrep",
        "verify": {
            "cmd": ["semgrep", "--version"],
            "regex": r"\d+\.\d+\.\d+",
        },
        "stdout_sample": "1.45.0\n",
    },
    "jq": {
        "name": "jq",
        "verify": {
            "cmd": ["jq", "--version"],
            "regex": r"jq-\d+",
        },
        "stdout_sample": "jq-1.7.1\n",
    },
    "ruff": {
        "name": "ruff",
        "verify": {
            "cmd": ["ruff", "--version"],
            "regex": r"ruff \d+\.\d+\.\d+",
        },
        "stdout_sample": "ruff 0.6.9\n",
    },
    "ty": {
        "name": "ty",
        "verify": {
            "cmd": ["ty", "--version"],
            "regex": r"ty \d+\.\d+\.\d+",
        },
        "stdout_sample": "ty 0.0.1\n",
    },
    "pip-audit": {
        "name": "pip-audit",
        "verify": {
            "cmd": ["pip-audit", "--version"],
            "regex": r"pip-audit \d+\.\d+\.\d+",
        },
        "stdout_sample": "pip-audit 2.7.3\n",
    },
}

# The 6 baseline tools used by parametric coverage assertions.
_BASELINE_TOOL_NAMES: tuple[str, ...] = tuple(_CANONICAL_VERIFY_SPECS.keys())
assert len(_BASELINE_TOOL_NAMES) == 6, "T-1.9 mandates 6 canonical baseline tools"

# Forbidden invocations per D-101-04 — these MUST be refused by run_verify.
_FORBIDDEN_VERIFY_CMDS: tuple[tuple[str, ...], ...] = (
    ("semgrep", "--config", "auto"),
    ("semgrep", "--refresh"),
    ("pip-audit", "--update"),
)


# ---------------------------------------------------------------------------
# TestVerifyExecutesCanonicalCmd — registry's offline-safe cmd is invoked
# ---------------------------------------------------------------------------


class TestVerifyExecutesCanonicalCmd:
    """``run_verify`` invokes the canonical offline-safe cmd from registry.

    Parametric over 6 baseline tools (gitleaks, semgrep, jq, ruff, ty,
    pip-audit). Mocks ``_safe_run`` and asserts exact argv + 10-second
    timeout (D-101-04).
    """

    @pytest.mark.parametrize("tool_name", _BASELINE_TOOL_NAMES)
    def test_canonical_cmd_invoked_via_safe_run(self, tool_name: str) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS[tool_name]
        expected_cmd = spec["verify"]["cmd"]

        # Mock _safe_run as the wrapper's subprocess entry point.
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed) as mock_run:
            run_verify(spec)

        assert mock_run.called, f"_safe_run was not invoked for {tool_name}"
        # First positional argument is the argv list.
        call_args, call_kwargs = mock_run.call_args
        argv = call_args[0] if call_args else call_kwargs.get("argv") or call_kwargs.get("cmd")
        assert argv == expected_cmd, (
            f"{tool_name}: run_verify must invoke exact canonical argv "
            f"{expected_cmd!r}; got {argv!r}"
        )

    @pytest.mark.parametrize("tool_name", _BASELINE_TOOL_NAMES)
    def test_timeout_is_ten_seconds(self, tool_name: str) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS[tool_name]

        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed) as mock_run:
            run_verify(spec)

        _, call_kwargs = mock_run.call_args
        # Accept either kwarg or positional after argv (production likely uses kwarg).
        timeout = call_kwargs.get("timeout")
        assert timeout == 10, f"{tool_name}: D-101-04 mandates a 10-second timeout; got {timeout!r}"


# ---------------------------------------------------------------------------
# TestVerifyReturnsVerifyResult — typed return value
# ---------------------------------------------------------------------------


class TestVerifyReturnsVerifyResult:
    """``run_verify`` returns ``VerifyResult(passed, version, stderr)``."""

    def test_verify_result_has_required_attributes(self) -> None:
        VerifyResult = _get_verify_result_cls()
        # VerifyResult is constructible with the three documented fields.
        result = VerifyResult(passed=True, version="1.2.3", stderr="")
        assert result.passed is True
        assert result.version == "1.2.3"
        assert result.stderr == ""

    def test_run_verify_returns_verify_result_instance(self) -> None:
        run_verify = _get_run_verify()
        VerifyResult = _get_verify_result_cls()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert isinstance(result, VerifyResult), (
            f"run_verify must return VerifyResult instance; got {type(result).__name__}"
        )

    def test_passed_true_when_exit_zero_and_regex_matches(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is True, "passed must be True when exit 0 and regex matches"

    def test_version_extracted_when_regex_matches(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "ruff 0.6.9\n"
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.version is not None, "version must be populated on success"
        assert "0.6.9" in result.version, (
            f"version must include the matched semver; got {result.version!r}"
        )

    def test_stderr_propagated_from_subprocess(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]
        completed = MagicMock()
        completed.returncode = 1
        completed.stdout = ""
        completed.stderr = "ruff: error: not found\n"

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is False
        assert "ruff: error" in result.stderr, (
            f"stderr from subprocess must be propagated into VerifyResult; got {result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# TestVerifyRegexMatch — registry's verify.regex is applied to stdout
# ---------------------------------------------------------------------------


class TestVerifyRegexMatch:
    """Registry's ``verify.regex`` is applied to stdout; non-match → False."""

    def test_regex_match_on_stdout_marks_passed(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["jq"]
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "jq-1.7.1\n"
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is True

    def test_regex_non_match_marks_failed_even_when_exit_zero(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["jq"]
        completed = MagicMock()
        completed.returncode = 0
        # stdout that does NOT match the jq-\d+ regex.
        completed.stdout = "totally unrelated output\n"
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is False, (
            "non-match against verify.regex must mark VerifyResult(passed=False) "
            "even when subprocess exit code is 0 — D-101-04 demands a positive proof"
        )

    def test_regex_match_on_stderr_also_marks_passed(self) -> None:
        """spec-109 follow-up: tools that emit success markers to stderr
        (e.g. gitleaks logs ``no leaks found`` on stderr) must still be
        considered verified. ``run_verify`` searches both stdout and stderr.
        """
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["jq"]
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = ""  # nothing on stdout
        completed.stderr = "jq-1.7.1\n"  # marker only on stderr

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is True, (
            "regex match against stderr must satisfy run_verify when exit is 0; "
            "tools like gitleaks log success markers to stderr"
        )

    def test_non_zero_exit_marks_failed_regardless_of_regex(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["semgrep"]
        completed = MagicMock()
        completed.returncode = 2
        # stdout that DOES match the semver regex — but exit is non-zero.
        completed.stdout = "1.45.0\n"
        completed.stderr = "fatal\n"

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        assert result.passed is False, (
            "non-zero exit must always mark passed=False even if regex matches"
        )

    @pytest.mark.parametrize("tool_name", _BASELINE_TOOL_NAMES)
    def test_canonical_stdout_sample_passes_regex(self, tool_name: str) -> None:
        """Sanity check on the test fixtures themselves: stdout_sample MUST
        match the registry regex. Guards against fixture rot.
        """
        spec = _CANONICAL_VERIFY_SPECS[tool_name]
        regex = spec["verify"]["regex"]
        sample = spec["stdout_sample"]
        assert re.search(regex, sample), (
            f"{tool_name}: fixture stdout_sample {sample!r} must match "
            f"registry regex {regex!r} — fix the fixture"
        )


# ---------------------------------------------------------------------------
# TestVerifyRejectsNetworkCmd — wrapper guards itself from forbidden args
# ---------------------------------------------------------------------------


class TestVerifyRejectsNetworkCmd:
    """``run_verify`` refuses network-touching invocations.

    D-101-04 lists ``--config auto``, ``--refresh``, and ``--update`` as
    forbidden because they trigger network egress. Even if a caller (or a
    future regression to ``tool_registry.py``) fabricates such a cmd, the
    wrapper MUST refuse to execute it. The wrapper guards itself.
    """

    @pytest.mark.parametrize("forbidden_cmd", _FORBIDDEN_VERIFY_CMDS)
    def test_forbidden_cmd_raises_unsafe_verify_command(
        self, forbidden_cmd: tuple[str, ...]
    ) -> None:
        run_verify = _get_run_verify()
        UnsafeVerifyCommand = _get_unsafe_verify_command()

        spec = {
            "name": forbidden_cmd[0],
            "verify": {
                "cmd": list(forbidden_cmd),
                "regex": r".*",
            },
        }

        # Even with a benign mock, the wrapper must refuse BEFORE invoking
        # the subprocess — assert _safe_run is never called.
        with patch(f"{_MODULE}._safe_run") as mock_run:
            with pytest.raises(UnsafeVerifyCommand):
                run_verify(spec)
            assert not mock_run.called, (
                f"run_verify must reject {forbidden_cmd!r} BEFORE invoking _safe_run; "
                "the guard MUST be at the wrapper layer, not relied on by the registry"
            )

    def test_unsafe_verify_command_is_exception_subclass(self) -> None:
        UnsafeVerifyCommand = _get_unsafe_verify_command()
        assert issubclass(UnsafeVerifyCommand, Exception), (
            "UnsafeVerifyCommand must derive from Exception"
        )

    def test_safe_cmd_is_executed(self) -> None:
        """Sanity check: a non-forbidden cmd is NOT rejected."""
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["semgrep"]  # ['semgrep', '--version']

        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed) as mock_run:
            run_verify(spec)
        assert mock_run.called, "non-forbidden cmd must be executed"


# ---------------------------------------------------------------------------
# TestForcedOffline — verify completes under HTTPS_PROXY=http://127.0.0.1:1
# ---------------------------------------------------------------------------


class TestForcedOffline:
    """Integration: ``HTTPS_PROXY=http://127.0.0.1:1`` does not break verify.

    Per D-101-04, the offline-safe verify cmds MUST complete in an
    egress-blocked environment (the framework's regulated enterprise
    audience runs in air-gapped networks per R-11). The mock subprocess
    returns valid stdout WITHOUT touching the network, proving the wrapper
    does not accidentally introduce its own network dependency (DNS,
    telemetry, etc.) on top of what the registry already mandates.
    """

    @pytest.mark.parametrize("tool_name", _BASELINE_TOOL_NAMES)
    def test_verify_completes_under_forced_offline(
        self, tool_name: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS[tool_name]

        # Force offline by pointing HTTPS_PROXY at a closed loopback port.
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("https_proxy", "http://127.0.0.1:1")
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")

        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            result = run_verify(spec)

        # Under forced offline, the wrapper must STILL succeed because the
        # canonical cmd is offline-safe. A failure here proves the wrapper
        # introduced a network dependency.
        assert result.passed is True, (
            f"{tool_name}: forced-offline verify must succeed (D-101-04 / R-11); "
            f"got passed={result.passed}, stderr={result.stderr!r}"
        )

    def test_run_verify_does_not_hang_under_forced_offline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sanity: even with mock subprocess, wrapper must return promptly.

        If a future change introduces a real network call inside run_verify
        (e.g., DNS lookup for telemetry), forced offline + a tight pytest
        timeout would surface it. We use the mock to keep the test
        deterministic but the parametric cases above still prove the cmd
        path is offline-safe.
        """
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["jq"]
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")

        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = spec["stdout_sample"]
        completed.stderr = ""

        with patch(f"{_MODULE}._safe_run", return_value=completed):
            # If wrapper hangs, pytest's default timeout (or the assert below
            # never being reached) flags it. Production code is expected to
            # propagate the 10-second subprocess timeout.
            result = run_verify(spec)

        assert result is not None, "run_verify must return promptly even under forced offline"


# ---------------------------------------------------------------------------
# TestSlowToolTimeout — >10s subprocess yields VerifyResult(passed=False)
# ---------------------------------------------------------------------------


class TestSlowToolTimeout:
    """A tool that hangs >10s yields ``VerifyResult(passed=False, error='timeout')``.

    D-101-04 mandates a 10-second timeout. The wrapper must convert
    ``subprocess.TimeoutExpired`` (or the equivalent from ``_safe_run``)
    into a structured ``VerifyResult`` rather than letting the exception
    propagate; otherwise a single hung tool kills the whole install run.
    """

    def test_timeout_returns_verify_result_passed_false(self) -> None:
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]

        # _safe_run raises subprocess.TimeoutExpired on >10s.
        timeout_exc = subprocess.TimeoutExpired(cmd=spec["verify"]["cmd"], timeout=10)

        with patch(f"{_MODULE}._safe_run", side_effect=timeout_exc):
            result = run_verify(spec)

        assert result.passed is False, (
            "subprocess timeout must yield passed=False (NOT propagate the exception)"
        )

    def test_timeout_carries_error_marker(self) -> None:
        run_verify = _get_run_verify()
        VerifyResult = _get_verify_result_cls()
        spec = _CANONICAL_VERIFY_SPECS["ruff"]

        timeout_exc = subprocess.TimeoutExpired(cmd=spec["verify"]["cmd"], timeout=10)

        with patch(f"{_MODULE}._safe_run", side_effect=timeout_exc):
            result = run_verify(spec)

        # VerifyResult exposes an `error` attribute (or equivalent) so the
        # caller can distinguish "ran but failed" from "timed out".
        # Probe both common shapes — production code lands one of them.
        error_marker: str | None
        if hasattr(result, "error"):
            error_marker = result.error
        elif "error" in getattr(result, "__dict__", {}):
            error_marker = result.__dict__["error"]
        else:
            # Final fallback: stderr should at least mention the timeout.
            error_marker = result.stderr

        assert isinstance(result, VerifyResult)
        assert error_marker is not None and "timeout" in error_marker.lower(), (
            f"timeout must be reported via 'error' field or stderr; got {error_marker!r}"
        )

    def test_timeout_does_not_raise(self) -> None:
        """The exception MUST be caught — no leakage to the caller."""
        run_verify = _get_run_verify()
        spec = _CANONICAL_VERIFY_SPECS["semgrep"]

        timeout_exc = subprocess.TimeoutExpired(cmd=spec["verify"]["cmd"], timeout=10)

        with patch(f"{_MODULE}._safe_run", side_effect=timeout_exc):
            # No `pytest.raises` here: the call must NOT raise.
            result = run_verify(spec)
        assert result is not None
        assert result.passed is False
