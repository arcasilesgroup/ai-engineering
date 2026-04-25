"""Failing tests for `prereqs.sdk` per-stack SDK probes (spec-101 T-1.17 — RED phase).

Covers (per plan T-1.17 + spec.md D-101-14):
- Parametric sweep across the 9 SDK-required stacks (java, kotlin, swift, dart,
  csharp, go, rust, php, cpp). Each case asserts `probe_sdk(stack)` returns a
  `ProbeResult` carrying status + version derived from a mocked subprocess.
- Probe-only invariant: `prereqs/sdk.py` MAY ONLY invoke probe argv shapes from a
  fixed allowlist; no install/download/upgrade/curl/setup/init verbs allowed.

Probe matrix (spec.md L313-323):
| stack  | probe                                               |
|--------|-----------------------------------------------------|
| java   | `java -version`             (parse JDK >= 21)        |
| kotlin | `java -version`             (shares JDK probe)       |
| swift  | `swift --version`           (darwin only)            |
| dart   | `dart --version`                                     |
| csharp | `dotnet --version`          (parse >= 9)             |
| go     | `go version`                                         |
| rust   | `rustc --version`                                    |
| php    | `php --version`             (parse >= 8.2)           |
| cpp    | `clang --version` OR `gcc --version`                 |

These tests MUST FAIL initially: `ai_engineering.prereqs.sdk` does not exist
until T-1.18 GREEN lands, so collection raises `ModuleNotFoundError`.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

import pytest

# This import intentionally fails until T-1.18 lands. Pytest collection raises
# ModuleNotFoundError, which is the RED-phase signal.
from ai_engineering.prereqs.sdk import (  # type: ignore[import-not-found]
    ProbeResult,
    probe_sdk,
)

# ---------------------------------------------------------------------------
# Parametric test cases — one per SDK-required stack (must equal 9).
# ---------------------------------------------------------------------------

# Each case: (stack_id, probe_argv, mocked_stdout, mocked_stderr,
#            expected_argv_prefix, expected_min_version_substr)
#
# Note: `java -version` writes to stderr (JDK convention); other probes write
# to stdout. The mocked subprocess returns the value on the matching stream.
_test_cases: list[tuple[str, list[str], str, str, list[str], str]] = [
    (
        "java",
        ["java", "-version"],
        "",
        'openjdk version "21.0.2" 2024-01-16\n',
        ["java", "-version"],
        "21",
    ),
    (
        "kotlin",
        ["java", "-version"],  # kotlin shares the JDK probe
        "",
        'openjdk version "21.0.2" 2024-01-16\n',
        ["java", "-version"],
        "21",
    ),
    (
        "swift",
        ["swift", "--version"],
        "Apple Swift version 5.9.2 (swiftlang-5.9.2.2.56 clang-1500.1.0.2.5)\n",
        "",
        ["swift", "--version"],
        "5.9",
    ),
    (
        "dart",
        ["dart", "--version"],
        "Dart SDK version: 3.2.5 (stable)\n",
        "",
        ["dart", "--version"],
        "3.2",
    ),
    (
        "csharp",
        ["dotnet", "--version"],
        "9.0.100\n",
        "",
        ["dotnet", "--version"],
        "9",
    ),
    (
        "go",
        ["go", "version"],
        "go version go1.22.0 darwin/arm64\n",
        "",
        ["go", "version"],
        "1.22",
    ),
    (
        "rust",
        ["rustc", "--version"],
        "rustc 1.75.0 (82e1608df 2023-12-21)\n",
        "",
        ["rustc", "--version"],
        "1.75",
    ),
    (
        "php",
        ["php", "--version"],
        "PHP 8.3.1 (cli) (built: Dec 21 2023 12:00:00) (NTS)\n",
        "",
        ["php", "--version"],
        "8.3",
    ),
    (
        "cpp",
        ["clang", "--version"],
        "Apple clang version 15.0.0 (clang-1500.3.9.4)\n",
        "",
        ["clang", "--version"],
        "15",
    ),
]

# Sanity gate — fails at module load time if a stack is silently dropped.
assert len(_test_cases) == 9, f"expected exactly 9 SDK-required probe cases, got {len(_test_cases)}"

# Probe argv shapes that prereqs/sdk.py is allowed to invoke. Anything else
# (especially install/download verbs) MUST be rejected by the allowlist test.
_PROBE_ARGV_ALLOWLIST: tuple[tuple[str, ...], ...] = (
    ("java", "-version"),
    ("dotnet", "--version"),
    ("go", "version"),
    ("rustc", "--version"),
    ("php", "--version"),
    ("clang", "--version"),
    ("gcc", "--version"),  # cpp fallback
    ("dart", "--version"),
    ("swift", "--version"),
)

# Words that, if present anywhere in a probe argv, indicate the module has
# crossed into NG-11 / install-shaped territory.
_FORBIDDEN_ARGV_WORDS: tuple[str, ...] = (
    "install",
    "add",
    "download",
    "curl",
    "update",
    "upgrade",
    "setup",
    "init",
)


# ---------------------------------------------------------------------------
# Subprocess interception helpers
# ---------------------------------------------------------------------------


def _make_subprocess_stub(
    captured: list[Sequence[str]],
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build a `subprocess.run` replacement that records argv and returns canned output."""

    def _run(
        cmd: Sequence[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        return subprocess.CompletedProcess(
            args=list(cmd),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return _run


def _patch_run(
    monkeypatch: pytest.MonkeyPatch,
    fn: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    """Patch subprocess.run on both the global module and the prereqs module."""
    import ai_engineering.prereqs.sdk as sdk_module

    monkeypatch.setattr(subprocess, "run", fn, raising=False)
    monkeypatch.setattr(sdk_module.subprocess, "run", fn, raising=False)


# ---------------------------------------------------------------------------
# Per-stack parametric probe tests
# ---------------------------------------------------------------------------


class TestPerStackProbe:
    """Parametric sweep — one case per SDK-required stack (9 total)."""

    @pytest.mark.parametrize(
        ("stack", "expected_argv", "stdout", "stderr", "_argv_prefix", "version_substr"),
        [
            pytest.param(stack, argv, sout, serr, prefix, vsubstr, id=stack)
            for (stack, argv, sout, serr, prefix, vsubstr) in _test_cases
        ],
    )
    def test_probe_returns_result_for_stack(
        self,
        stack: str,
        expected_argv: list[str],
        stdout: str,
        stderr: str,
        _argv_prefix: list[str],
        version_substr: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`probe_sdk(stack)` returns a ProbeResult with status + parsed version."""
        # Skip swift on non-darwin per spec.md (D-101-13 — swift is darwin-only).
        if stack == "swift" and sys.platform != "darwin":
            pytest.skip("swift probe is darwin-only per D-101-13")

        # Arrange — capture argv and stub subprocess.run.
        captured: list[Sequence[str]] = []
        stub = _make_subprocess_stub(captured, stdout=stdout, stderr=stderr, returncode=0)
        _patch_run(monkeypatch, stub)

        # Act
        result = probe_sdk(stack)

        # Assert — return type contract.
        assert isinstance(result, ProbeResult), (
            f"probe_sdk({stack!r}) returned {type(result).__name__}, expected ProbeResult"
        )

        # Status field exists and is truthy/recognized.
        assert hasattr(result, "status"), "ProbeResult missing `status` attribute"
        assert result.status, f"probe_sdk({stack!r}) returned empty status"

        # Version field exists and reflects the mocked output.
        assert hasattr(result, "version"), "ProbeResult missing `version` attribute"
        assert result.version is not None, (
            f"probe_sdk({stack!r}) returned version=None despite successful probe"
        )
        assert version_substr in str(result.version), (
            f"probe_sdk({stack!r}): expected version containing {version_substr!r}, "
            f"got {result.version!r}"
        )

        # Subprocess was actually invoked with the expected argv shape.
        assert captured, f"probe_sdk({stack!r}) did not invoke subprocess"
        assert captured[0] == expected_argv, (
            f"probe_sdk({stack!r}): expected argv {expected_argv!r}, got {captured[0]!r}"
        )

    def test_module_load_assertion_holds(self) -> None:
        """`len(_test_cases) == 9` — guards against silent omission."""
        # Assert
        assert len(_test_cases) == 9, (
            f"expected exactly 9 SDK-required probe cases, got {len(_test_cases)}"
        )

        # And every canonical stack is represented.
        stacks = {case[0] for case in _test_cases}
        assert stacks == {
            "java",
            "kotlin",
            "swift",
            "dart",
            "csharp",
            "go",
            "rust",
            "php",
            "cpp",
        }, f"unexpected stack set: {sorted(stacks)}"


# ---------------------------------------------------------------------------
# Probe-only allowlist — D-101-14 invariant
# ---------------------------------------------------------------------------


class TestProbeOnlyAllowlist:
    """`prereqs/sdk.py` MUST only invoke argv shapes from the probe allowlist."""

    def _exercise_all_probes(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> list[Sequence[str]]:
        """Run every probe with a subprocess stub and return the captured argv calls."""
        captured: list[Sequence[str]] = []
        stub = _make_subprocess_stub(captured, stdout="", stderr="", returncode=0)
        _patch_run(monkeypatch, stub)

        for stack, _argv, _sout, _serr, _prefix, _vsubstr in _test_cases:
            if stack == "swift" and sys.platform != "darwin":
                continue
            with contextlib.suppress(Exception):
                # Probe failure is fine here — we are auditing the argv shapes only.
                probe_sdk(stack)

        return captured

    def test_required_argv_shapes_are_invoked(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each canonical probe argv shape MUST appear in the captured calls."""
        # Act
        captured = self._exercise_all_probes(monkeypatch)
        seen: set[tuple[str, ...]] = {tuple(call) for call in captured}

        # Assert — required argvs appear (gcc is a fallback, not required to be invoked).
        required: tuple[tuple[str, ...], ...] = (
            ("java", "-version"),
            ("dotnet", "--version"),
            ("go", "version"),
            ("rustc", "--version"),
            ("php", "--version"),
            ("clang", "--version"),
            ("dart", "--version"),
        )
        if sys.platform == "darwin":
            required = (*required, ("swift", "--version"))

        for argv in required:
            assert argv in seen, (
                f"expected probe argv {argv!r} to be invoked; captured calls: {sorted(seen)!r}"
            )

    def test_every_invocation_matches_allowlist(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No probe argv may fall outside the fixed allowlist."""
        # Act
        captured = self._exercise_all_probes(monkeypatch)

        # Assert — every captured argv is in the allowlist.
        for call in captured:
            tuple_call = tuple(call)
            assert tuple_call in _PROBE_ARGV_ALLOWLIST, (
                f"prereqs/sdk.py invoked unallowed argv {tuple_call!r}; "
                f"allowlist is {_PROBE_ARGV_ALLOWLIST!r}"
            )

    def test_no_install_shaped_argv_words(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No argv may contain install/upgrade/download/curl/setup/init/add/update."""
        # Act
        captured = self._exercise_all_probes(monkeypatch)

        # Assert — each forbidden word is absent from every argv token.
        for call in captured:
            tokens_lower = [str(tok).lower() for tok in call]
            for forbidden in _FORBIDDEN_ARGV_WORDS:
                assert forbidden not in tokens_lower, (
                    f"prereqs/sdk.py invoked install-shaped argv {list(call)!r} "
                    f"(forbidden token {forbidden!r}); D-101-14 probe-only invariant violated"
                )

    def test_minimum_argv_count_matches_required_stacks(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """At least one subprocess call per non-skipped stack is recorded."""
        # Act
        captured = self._exercise_all_probes(monkeypatch)

        # Assert — 9 stacks total, swift skipped on non-darwin.
        expected_min = 9 if sys.platform == "darwin" else 8
        assert len(captured) >= expected_min, (
            f"expected at least {expected_min} probe invocations across stacks, "
            f"got {len(captured)}: {captured!r}"
        )
