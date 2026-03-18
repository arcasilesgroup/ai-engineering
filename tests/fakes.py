"""Central fake registry for TDD-ready tests.

Provides reusable in-memory implementations that replace mocks across
the test suite. Each fake implements the same interface as the production
code, making tests behavior-focused instead of implementation-coupled.

Design principles:
- Implement the same Protocol/interface as production code
- Add test helpers as separate methods (not part of Protocol)
- Make behavior configurable (set_error, set_response, etc.)
- Keep simple enough that fakes don't need their own tests
"""

from __future__ import annotations

import subprocess
import typing
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus

# ── FakeCommandRunner ─────────────────────────────────────────────────────


class FakeCommandRunner:
    """Configurable fake for subprocess.run — replaces _run() in services.

    Usage:
        fake = FakeCommandRunner()
        fake.set_response("ruff", returncode=1, stdout='[{"message": "lint"}]')
        monkeypatch.setattr("module._run", fake)
    """

    def __init__(self) -> None:
        self._responses: dict[str, subprocess.CompletedProcess[str]] = {}
        self.call_log: list[list[str]] = []

    def set_response(
        self,
        cmd_contains: str,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self._responses[cmd_contains] = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def __call__(
        self,
        cmd: list[str],
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        self.call_log.append(cmd)
        cmd_str = " ".join(cmd)
        for key, response in self._responses.items():
            if key in cmd_str:
                return response
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ── FakeCheckResults ──────────────────────────────────────────────────────


class FakeCheckResults:
    """Pre-built CheckResult lists for doctor test injection.

    Usage:
        results = FakeCheckResults.all_passing()
        results = FakeCheckResults.with_failure("hooks", "Hook file missing")
    """

    _CHECK_NAMES: typing.ClassVar[list[str]] = [
        "layout",
        "state_files",
        "tools",
        "venv",
        "hooks",
    ]

    @classmethod
    def all_passing(cls) -> list[CheckResult]:
        return [
            CheckResult(name=name, status=CheckStatus.OK, message=f"{name}: ok")
            for name in cls._CHECK_NAMES
        ]

    @classmethod
    def with_failure(cls, check_name: str, message: str = "") -> list[CheckResult]:
        results = []
        for name in cls._CHECK_NAMES:
            if name == check_name:
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.FAIL,
                        message=message or f"{name}: failed",
                    )
                )
            else:
                results.append(CheckResult(name=name, status=CheckStatus.OK, message=f"{name}: ok"))
        return results

    @classmethod
    def with_warning(cls, check_name: str, message: str = "") -> list[CheckResult]:
        results = []
        for name in cls._CHECK_NAMES:
            if name == check_name:
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.WARN,
                        message=message or f"{name}: warning",
                    )
                )
            else:
                results.append(CheckResult(name=name, status=CheckStatus.OK, message=f"{name}: ok"))
        return results


# ── FakeFileSystem ────────────────────────────────────────────────────────


@dataclass
class FakeFileSystem:
    """In-memory filesystem for tests that need Path.exists/read_text.

    Usage:
        fs = FakeFileSystem()
        fs.add_file("config.yml", "key: value")
        assert fs.exists(Path("config.yml"))
    """

    _files: dict[str, str] = field(default_factory=dict)

    def add_file(self, path: str, content: str = "") -> None:
        self._files[path] = content

    def exists(self, path: Path) -> bool:
        return str(path) in self._files

    def read_text(self, path: Path) -> str:
        key = str(path)
        if key not in self._files:
            raise FileNotFoundError(f"Fake file not found: {path}")
        return self._files[key]
