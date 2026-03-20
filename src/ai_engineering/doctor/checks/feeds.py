"""Enterprise artifact feed diagnostic checks.

Validates private feed configuration in ``pyproject.toml``, detects lock-file
leaks to pypi.org, checks lock freshness, and verifies keyring availability
for credential retrieval.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport


def check_feeds(target: Path, report: DoctorReport) -> None:
    """Run all feed-related diagnostic checks against *target* project."""
    pyproject_path = target / "pyproject.toml"
    if not pyproject_path.exists():
        return

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    indexes: list[dict[str, object]] = data.get("tool", {}).get("uv", {}).get("index", [])
    if not indexes:
        return

    # Classify feeds.
    private_feeds: list[dict[str, object]] = []
    pypi_feeds: list[dict[str, object]] = []
    for entry in indexes:
        url = str(entry.get("url", ""))
        if "pypi.org" in url:
            pypi_feeds.append(entry)
        else:
            private_feeds.append(entry)

    # --- feed-mixed-sources (checked first, early return) --------------------
    if private_feeds and pypi_feeds:
        report.checks.append(
            CheckResult(
                name="feed-mixed-sources",
                status=CheckStatus.WARN,
                message="Both private and pypi.org feeds configured; "
                "packages may resolve from unexpected sources",
            )
        )
        return

    # All remaining checks apply only when private feeds are configured.
    if not private_feeds:
        return

    lock_path = target / "uv.lock"
    lock_exists = lock_path.exists()

    # --- feed-lock-leak ------------------------------------------------------
    _check_lock_leak(lock_path, lock_exists, report)

    # --- feed-lock-freshness -------------------------------------------------
    _check_lock_freshness(pyproject_path, lock_path, lock_exists, report)

    # --- feed-keyring --------------------------------------------------------
    _check_keyring(private_feeds, report)


# -- Private helpers ----------------------------------------------------------


def _check_lock_leak(
    lock_path: Path,
    lock_exists: bool,
    report: DoctorReport,
) -> None:
    """Detect pypi.org references leaking into a private-only lock file."""
    if not lock_exists:
        report.checks.append(
            CheckResult(
                name="feed-lock-leak",
                status=CheckStatus.OK,
                message="Lock file absent; skipped leak check",
            )
        )
        return

    lock_text = lock_path.read_text()
    if "pypi.org/simple" in lock_text:
        report.checks.append(
            CheckResult(
                name="feed-lock-leak",
                status=CheckStatus.FAIL,
                message="uv.lock contains pypi.org references "
                "despite private-only feed configuration",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="feed-lock-leak",
                status=CheckStatus.OK,
                message="No pypi.org leak detected in uv.lock",
            )
        )


def _check_lock_freshness(
    pyproject_path: Path,
    lock_path: Path,
    lock_exists: bool,
    report: DoctorReport,
) -> None:
    """Verify that uv.lock is at least as recent as pyproject.toml."""
    if not lock_exists:
        report.checks.append(
            CheckResult(
                name="feed-lock-freshness",
                status=CheckStatus.WARN,
                message="uv.lock not found; run `uv lock` to generate it",
            )
        )
        return

    lock_mtime = lock_path.stat().st_mtime
    pyproject_mtime = pyproject_path.stat().st_mtime

    if lock_mtime >= pyproject_mtime:
        report.checks.append(
            CheckResult(
                name="feed-lock-freshness",
                status=CheckStatus.OK,
                message="uv.lock is up to date with pyproject.toml",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="feed-lock-freshness",
                status=CheckStatus.WARN,
                message="uv.lock is stale (older than pyproject.toml); run `uv lock` to refresh",
            )
        )


def _check_keyring(
    private_feeds: list[dict[str, object]],
    report: DoctorReport,
) -> None:
    """Verify keyring CLI availability and credential access for private feeds."""
    # Skip in CI environments.
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        report.checks.append(
            CheckResult(
                name="feed-keyring",
                status=CheckStatus.OK,
                message="CI detected; skip keyring check",
            )
        )
        return

    # Check keyring binary on PATH.
    if shutil.which("keyring") is None:
        report.checks.append(
            CheckResult(
                name="feed-keyring",
                status=CheckStatus.FAIL,
                message="keyring CLI not found on PATH; install via `uv tool install keyring`",
            )
        )
        return

    # Check keyring backend.
    try:
        subprocess.run(
            ["keyring", "--list-backends"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        report.checks.append(
            CheckResult(
                name="feed-keyring",
                status=CheckStatus.WARN,
                message="Keyring backend unavailable; "
                "configure a backend (e.g. keyring-azartifacts)",
            )
        )
        return

    # Check credential for first private feed.
    feed_url = str(private_feeds[0].get("url", ""))
    result = subprocess.run(
        ["keyring", "get", feed_url, ""],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        report.checks.append(
            CheckResult(
                name="feed-keyring",
                status=CheckStatus.WARN,
                message=f"No credential found for {feed_url}; "
                "run `keyring set` or configure artifact credential provider",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="feed-keyring",
                status=CheckStatus.OK,
                message="Keyring credential available for private feed",
            )
        )
