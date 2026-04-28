"""Assert that sha256_pinned=True implies expected_sha256 is non-empty.

This test prevents future regressions where a registry entry sets
sha256_pinned=True without supplying the actual pin (silently failing
ALL installs of that tool because _PIN_REQUIRED=True correctly raises).
"""

from __future__ import annotations

from ai_engineering.installer.mechanisms import GitHubReleaseBinaryMechanism
from ai_engineering.installer.tool_registry import TOOL_REGISTRY


def test_sha256_pinned_implies_expected_sha256_present() -> None:
    """Every pinned GitHubReleaseBinaryMechanism MUST carry a non-empty pin.

    Iterates every per-OS entry in TOOL_REGISTRY and asserts the invariant
    holds for every GitHubReleaseBinaryMechanism instance. The ``verify``
    block is skipped because it is metadata, not a mechanism list.
    """
    violations: list[tuple[str, str, GitHubReleaseBinaryMechanism]] = []
    for tool_name, os_map in TOOL_REGISTRY.items():
        for os_key, mechanisms in os_map.items():
            if os_key == "verify":
                continue
            if not isinstance(mechanisms, list):
                continue
            for mech in mechanisms:
                if (
                    isinstance(mech, GitHubReleaseBinaryMechanism)
                    and mech.sha256_pinned
                    and not (mech.expected_sha256 or "").strip()
                ):
                    violations.append((tool_name, os_key, mech))
    assert not violations, (
        "GitHubReleaseBinaryMechanism with sha256_pinned=True must provide "
        f"expected_sha256. Violations: {violations}"
    )
