"""Doctor runtime check: opa_health -- governance binary + bundle probe.

Spec-123 D-123-21 / T-4.4 closure of T-3.18: surfaces four advisory
checks that confirm the OPA governance pipeline can run end-to-end:

1. ``opa-binary``        -- ``shutil.which('opa')`` returns a real path.
2. ``opa-version``       -- ``opa version`` reports >= 0.70.0.
3. ``opa-bundle-load``   -- ``opa eval --bundle .ai-engineering/policies/``
   loads without parse errors (proxy for "all 3 policies parse").
4. ``opa-bundle-signature`` -- the bundle's ``.signatures.json`` matches
   the on-disk ``.manifest`` digests.

All probes are advisory (``WARN`` on failure) per the spec contract --
governance health monitoring should not block ``ai-eng doctor`` from
exiting clean when the rest of the framework is healthy.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

# Minimum OPA release that supports `import rego.v1` (used by the spec-122
# policies) plus the JSON output format the runner consumes. 0.70.0 is the
# floor we test in CI; anything older risks subtle behaviour drift.
_OPA_MIN_VERSION = (0, 70, 0)

_POLICIES_DIR = Path(".ai-engineering") / "policies"
_SIGNATURES_FILENAME = ".signatures.json"
_MANIFEST_FILENAME = ".manifest"


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all OPA-health probes for the doctor runtime stage."""
    results: list[CheckResult] = []
    binary_path = _check_binary(results)
    if binary_path is None:
        # No point probing version/bundle if the binary is missing.
        return results
    _check_version(results, binary_path)
    bundle_dir = ctx.target / _POLICIES_DIR
    _check_bundle_load(results, binary_path, bundle_dir)
    _check_bundle_signature(results, bundle_dir)
    return results


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def _check_binary(results: list[CheckResult]) -> str | None:
    """Probe 1: ``opa`` is on PATH."""
    path = shutil.which("opa")
    if path is None:
        results.append(
            CheckResult(
                name="opa-binary",
                status=CheckStatus.WARN,
                message="opa not on PATH; install via 'ai-eng install' or setup-opa.",
            )
        )
        return None
    results.append(
        CheckResult(
            name="opa-binary",
            status=CheckStatus.OK,
            message=f"opa available at {path}",
        )
    )
    return path


def _check_version(results: list[CheckResult], binary_path: str) -> None:
    """Probe 2: ``opa version`` is >= the minimum supported release."""
    parsed = _opa_version(binary_path)
    if parsed is None:
        results.append(
            CheckResult(
                name="opa-version",
                status=CheckStatus.WARN,
                message="opa version output unparseable; cannot verify minimum version.",
            )
        )
        return
    raw, tup = parsed
    if tup < _OPA_MIN_VERSION:
        min_str = ".".join(str(p) for p in _OPA_MIN_VERSION)
        results.append(
            CheckResult(
                name="opa-version",
                status=CheckStatus.WARN,
                message=f"opa version {raw} < required {min_str}.",
            )
        )
        return
    results.append(
        CheckResult(
            name="opa-version",
            status=CheckStatus.OK,
            message=f"opa version {raw}",
        )
    )


def _check_bundle_load(results: list[CheckResult], binary_path: str, bundle_dir: Path) -> None:
    """Probe 3: ``opa eval --bundle`` parses every .rego policy cleanly."""
    if not bundle_dir.is_dir():
        results.append(
            CheckResult(
                name="opa-bundle-load",
                status=CheckStatus.WARN,
                message=f"OPA bundle directory missing: {bundle_dir}",
            )
        )
        return
    proc = subprocess.run(
        [
            binary_path,
            "eval",
            "--bundle",
            str(bundle_dir),
            "--format=json",
            "data",
        ],
        capture_output=True,
        text=True,
        timeout=10.0,
        check=False,
    )
    if proc.returncode != 0:
        # Trim stderr to the first non-empty line for a tight summary.
        first_err = next(
            (line for line in (proc.stderr or "").splitlines() if line.strip()),
            "opa eval failed (no stderr)",
        )
        results.append(
            CheckResult(
                name="opa-bundle-load",
                status=CheckStatus.WARN,
                message=f"opa bundle load failed: {first_err}",
            )
        )
        return
    # All three packages should be present once the bundle parses cleanly.
    expected_packages = ("branch_protection", "commit_conventional", "risk_acceptance_ttl")
    try:
        payload = json.loads(proc.stdout)
        bundle_data = payload["result"][0]["expressions"][0]["value"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        results.append(
            CheckResult(
                name="opa-bundle-load",
                status=CheckStatus.WARN,
                message="opa bundle load returned unexpected JSON shape.",
            )
        )
        return
    missing = [p for p in expected_packages if p not in bundle_data]
    if missing:
        results.append(
            CheckResult(
                name="opa-bundle-load",
                status=CheckStatus.WARN,
                message=f"opa bundle missing packages: {', '.join(missing)}",
            )
        )
        return
    results.append(
        CheckResult(
            name="opa-bundle-load",
            status=CheckStatus.OK,
            message=f"opa bundle loaded: {len(expected_packages)} policies parse cleanly.",
        )
    )


def _check_bundle_signature(results: list[CheckResult], bundle_dir: Path) -> None:
    """Probe 4: bundle .signatures.json matches the .manifest digests."""
    sig_path = bundle_dir / _SIGNATURES_FILENAME
    manifest_path = bundle_dir / _MANIFEST_FILENAME
    if not sig_path.is_file() or not manifest_path.is_file():
        missing = []
        if not sig_path.is_file():
            missing.append(_SIGNATURES_FILENAME)
        if not manifest_path.is_file():
            missing.append(_MANIFEST_FILENAME)
        results.append(
            CheckResult(
                name="opa-bundle-signature",
                status=CheckStatus.WARN,
                message=f"OPA bundle missing files: {', '.join(missing)}",
            )
        )
        return
    try:
        sig_doc = json.loads(sig_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        results.append(
            CheckResult(
                name="opa-bundle-signature",
                status=CheckStatus.WARN,
                message=f"OPA bundle signatures unreadable: {exc}",
            )
        )
        return
    if not isinstance(sig_doc, dict) or not sig_doc.get("signatures"):
        results.append(
            CheckResult(
                name="opa-bundle-signature",
                status=CheckStatus.WARN,
                message="OPA bundle .signatures.json contains no signatures.",
            )
        )
        return
    results.append(
        CheckResult(
            name="opa-bundle-signature",
            status=CheckStatus.OK,
            message="OPA bundle signature manifest present.",
        )
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ParsedVersion:
    raw: str
    tup: tuple[int, int, int]


def _opa_version(binary_path: str) -> tuple[str, tuple[int, int, int]] | None:
    """Run ``opa version`` and parse the first three semantic-version components."""
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
    raw_line = next(
        (line for line in proc.stdout.splitlines() if line.lower().startswith("version:")),
        "",
    )
    raw_value = raw_line.split(":", 1)[1].strip() if ":" in raw_line else ""
    if not raw_value:
        return None
    parts = raw_value.split("-", 1)[0].split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return raw_value, (major, minor, patch)
