"""Doctor runtime check: secrets_gate -- gitleaks/semgrep wiring probe.

Spec-124 D-124-09 / T-4.1: surfaces seven advisory checks that confirm
the secrets-gate defense-in-depth pipeline (gitleaks pre-commit +
semgrep pre-push) is wired end-to-end on the host.

Probes (each contributes a check entry to the doctor result):

1. ``gitleaks-binary``           -- ``shutil.which('gitleaks')`` returns a path.
2. ``gitleaks-version``          -- ``gitleaks version`` runs without error.
3. ``semgrep-binary``            -- ``shutil.which('semgrep')`` returns a path.
4. ``semgrep-config``            -- ``<root>/.semgrep.yml`` is a regular file.
5. ``gitleaks-config``           -- ``<root>/.gitleaks.toml`` and
   ``<root>/.gitleaksignore`` are regular files.
6. ``pre-commit-hook-installed`` -- ``<root>/.git/hooks/pre-commit`` exists
   and contains ``ai-eng gate pre-commit``.
7. ``pre-push-hook-installed``   -- same for ``pre-push`` and
   ``ai-eng gate pre-push``.

All probes are advisory (``WARN`` on failure) per the spec contract --
secrets-gate health monitoring should not block ``ai-eng doctor`` from
exiting clean when the rest of the framework is healthy. Failure
messages include actionable guidance (``brew install gitleaks``,
``ai-eng install`` etc).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

_GITLEAKS_CONFIG_FILENAME = ".gitleaks.toml"
_GITLEAKS_IGNORE_FILENAME = ".gitleaksignore"
_SEMGREP_CONFIG_FILENAME = ".semgrep.yml"
_PRE_COMMIT_HOOK = Path(".git") / "hooks" / "pre-commit"
_PRE_PUSH_HOOK = Path(".git") / "hooks" / "pre-push"
_PRE_COMMIT_MARKER = "ai-eng gate pre-commit"
_PRE_PUSH_MARKER = "ai-eng gate pre-push"


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all secrets-gate probes for the doctor runtime stage."""
    results: list[CheckResult] = []
    _check_gitleaks_binary(results)
    _check_gitleaks_version(results)
    _check_semgrep_binary(results)
    _check_semgrep_config(results, ctx.target)
    _check_gitleaks_config(results, ctx.target)
    _check_pre_commit_hook(results, ctx.target)
    _check_pre_push_hook(results, ctx.target)
    return results


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def _check_gitleaks_binary(results: list[CheckResult]) -> None:
    """Probe 1: ``gitleaks`` is on PATH."""
    path = shutil.which("gitleaks")
    if path is None:
        results.append(
            CheckResult(
                name="gitleaks-binary",
                status=CheckStatus.WARN,
                message=(
                    "gitleaks not on PATH; install via 'brew install gitleaks' "
                    "or 'ai-eng install' to wire the pre-commit secrets gate."
                ),
            )
        )
        return
    results.append(
        CheckResult(
            name="gitleaks-binary",
            status=CheckStatus.OK,
            message=f"gitleaks available at {path}",
        )
    )


def _check_gitleaks_version(results: list[CheckResult]) -> None:
    """Probe 2: ``gitleaks version`` runs without error."""
    binary_path = shutil.which("gitleaks")
    if binary_path is None:
        results.append(
            CheckResult(
                name="gitleaks-version",
                status=CheckStatus.WARN,
                message="gitleaks not on PATH; cannot probe version.",
            )
        )
        return
    raw = _gitleaks_version(binary_path)
    if raw is None:
        results.append(
            CheckResult(
                name="gitleaks-version",
                status=CheckStatus.WARN,
                message="gitleaks version output unparseable; cannot verify install.",
            )
        )
        return
    results.append(
        CheckResult(
            name="gitleaks-version",
            status=CheckStatus.OK,
            message=f"gitleaks version {raw}",
        )
    )


def _check_semgrep_binary(results: list[CheckResult]) -> None:
    """Probe 3: ``semgrep`` is on PATH."""
    path = shutil.which("semgrep")
    if path is None:
        results.append(
            CheckResult(
                name="semgrep-binary",
                status=CheckStatus.WARN,
                message=(
                    "semgrep not on PATH; install via 'brew install semgrep' or "
                    "'pipx install semgrep' to wire the pre-push security gate."
                ),
            )
        )
        return
    results.append(
        CheckResult(
            name="semgrep-binary",
            status=CheckStatus.OK,
            message=f"semgrep available at {path}",
        )
    )


def _check_semgrep_config(results: list[CheckResult], target: Path) -> None:
    """Probe 4: ``.semgrep.yml`` is present at the project root."""
    config_path = target / _SEMGREP_CONFIG_FILENAME
    if not config_path.is_file():
        results.append(
            CheckResult(
                name="semgrep-config",
                status=CheckStatus.WARN,
                message=(
                    f"{_SEMGREP_CONFIG_FILENAME} missing at project root; "
                    "pre-push semgrep gate cannot run without it."
                ),
            )
        )
        return
    results.append(
        CheckResult(
            name="semgrep-config",
            status=CheckStatus.OK,
            message=f"{_SEMGREP_CONFIG_FILENAME} present.",
        )
    )


def _check_gitleaks_config(results: list[CheckResult], target: Path) -> None:
    """Probe 5: ``.gitleaks.toml`` and ``.gitleaksignore`` are present."""
    config_path = target / _GITLEAKS_CONFIG_FILENAME
    ignore_path = target / _GITLEAKS_IGNORE_FILENAME
    missing: list[str] = []
    if not config_path.is_file():
        missing.append(_GITLEAKS_CONFIG_FILENAME)
    if not ignore_path.is_file():
        missing.append(_GITLEAKS_IGNORE_FILENAME)
    if missing:
        results.append(
            CheckResult(
                name="gitleaks-config",
                status=CheckStatus.WARN,
                message=(
                    f"gitleaks configuration missing: {', '.join(missing)}; "
                    "pre-commit gate falls back to default rules."
                ),
            )
        )
        return
    results.append(
        CheckResult(
            name="gitleaks-config",
            status=CheckStatus.OK,
            message=f"{_GITLEAKS_CONFIG_FILENAME} and {_GITLEAKS_IGNORE_FILENAME} present.",
        )
    )


def _check_pre_commit_hook(results: list[CheckResult], target: Path) -> None:
    """Probe 6: ``.git/hooks/pre-commit`` is wired to ``ai-eng gate pre-commit``."""
    hook_path = target / _PRE_COMMIT_HOOK
    _check_hook_marker(
        results,
        hook_path,
        marker=_PRE_COMMIT_MARKER,
        check_name="pre-commit-hook-installed",
        hint=(
            "pre-commit hook missing or not wired to 'ai-eng gate pre-commit'; "
            "run 'ai-eng install' to install it."
        ),
        ok_message="pre-commit hook wired to 'ai-eng gate pre-commit'.",
    )


def _check_pre_push_hook(results: list[CheckResult], target: Path) -> None:
    """Probe 7: ``.git/hooks/pre-push`` is wired to ``ai-eng gate pre-push``."""
    hook_path = target / _PRE_PUSH_HOOK
    _check_hook_marker(
        results,
        hook_path,
        marker=_PRE_PUSH_MARKER,
        check_name="pre-push-hook-installed",
        hint=(
            "pre-push hook missing or not wired to 'ai-eng gate pre-push'; "
            "run 'ai-eng install' to install it."
        ),
        ok_message="pre-push hook wired to 'ai-eng gate pre-push'.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_hook_marker(
    results: list[CheckResult],
    hook_path: Path,
    *,
    marker: str,
    check_name: str,
    hint: str,
    ok_message: str,
) -> None:
    """Verify a git hook exists and contains the expected ``ai-eng gate`` marker."""
    if not hook_path.is_file():
        results.append(
            CheckResult(
                name=check_name,
                status=CheckStatus.WARN,
                message=hint,
            )
        )
        return
    try:
        contents = hook_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        results.append(
            CheckResult(
                name=check_name,
                status=CheckStatus.WARN,
                message=f"hook unreadable: {exc}",
            )
        )
        return
    if marker not in contents:
        results.append(
            CheckResult(
                name=check_name,
                status=CheckStatus.WARN,
                message=hint,
            )
        )
        return
    results.append(
        CheckResult(
            name=check_name,
            status=CheckStatus.OK,
            message=ok_message,
        )
    )


def _gitleaks_version(binary_path: str) -> str | None:
    """Run ``gitleaks version`` and return the trimmed first non-empty line."""
    try:
        proc = subprocess.run(
            [binary_path, "version"],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None
