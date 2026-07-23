"""CLI census scanner (spec-199 T-1).

Scans installed CLIs: binary, version, origin, auth state, cost surface.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CliCandidate:
    """Single CLI candidate."""

    name: str
    binary_path: str
    version: str
    origin: str  # "homebrew", "npm", "pip", "cargo", "unknown"
    auth_state: str  # "authenticated", "unauthenticated", "unknown"
    cost_surface: str  # "free", "paid", "unknown"
    installed: bool = True


@dataclass(frozen=True)
class CliCensus:
    """Complete CLI census."""

    candidates: list[CliCandidate]
    total: int
    installed: int
    authenticated: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "total": self.total,
                "installed": self.installed,
                "authenticated": self.authenticated,
                "candidates": [
                    {
                        "name": c.name,
                        "binary_path": c.binary_path,
                        "version": c.version,
                        "origin": c.origin,
                        "auth_state": c.auth_state,
                        "cost_surface": c.cost_surface,
                    }
                    for c in self.candidates
                ],
            },
            indent=2,
            sort_keys=True,
        )


def scan_binary(name: str) -> CliCandidate | None:
    """Scan a single binary."""
    try:
        result = subprocess.run(
            ["which", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        binary_path = result.stdout.strip()

        # Get version
        version = "unknown"
        try:
            version_result = subprocess.run(
                [name, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if version_result.returncode == 0:
                version = version_result.stdout.strip().split("\n")[0][:50]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Determine origin
        origin = "unknown"
        if "/opt/homebrew/" in binary_path or "/usr/local/" in binary_path:
            origin = "homebrew"
        elif ".npm/" in binary_path or "node_modules" in binary_path:
            origin = "npm"
        elif ".local/" in binary_path and "pip" in binary_path:
            origin = "pip"

        return CliCandidate(
            name=name,
            binary_path=binary_path,
            version=version,
            origin=origin,
            auth_state="unknown",
            cost_surface="unknown",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def census_candidates(names: list[str]) -> CliCensus:
    """Run census on a list of candidate names."""
    candidates = []
    for name in names:
        candidate = scan_binary(name)
        if candidate:
            candidates.append(candidate)

    installed = sum(1 for c in candidates if c.installed)
    authenticated = sum(1 for c in candidates if c.auth_state == "authenticated")

    return CliCensus(
        candidates=candidates,
        total=len(candidates),
        installed=installed,
        authenticated=authenticated,
    )


# Default candidates to scan
DEFAULT_CANDIDATES = ["gh", "railway", "engram", "pencil", "pen"]
