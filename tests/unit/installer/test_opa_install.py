"""Tests for the OPA tool registry entry (spec-122 Phase C, T-3.4).

Verifies that ``TOOL_REGISTRY["opa"]`` declares the install fallback chain
agreed in the plan:

* darwin: ``BrewMechanism("opa")`` -> ``GitHubReleaseBinaryMechanism(...)``
* linux:  ``GitHubReleaseBinaryMechanism(...)``
* win32:  ``WingetMechanism(...)`` -> ``ScoopMechanism(...)`` ->
  ``GitHubReleaseBinaryMechanism(...)``

The ``verify`` block uses ``opa version`` (not ``--version``; OPA's CLI
exposes ``opa version`` as a subcommand) and the canonical semver regex.
No subprocesses are invoked — tests inspect the registry data structure
only.
"""

from __future__ import annotations

import re

from ai_engineering.installer.mechanisms import (
    BrewMechanism,
    GitHubReleaseBinaryMechanism,
    ScoopMechanism,
    WingetMechanism,
)
from ai_engineering.installer.tool_registry import TOOL_REGISTRY


def test_opa_entry_exists() -> None:
    assert "opa" in TOOL_REGISTRY, "TOOL_REGISTRY must declare an 'opa' entry"
    entry = TOOL_REGISTRY["opa"]
    for key in ("darwin", "linux", "win32", "verify"):
        assert key in entry, f"opa entry must expose '{key}'"


def test_opa_darwin_chain_brew_then_github() -> None:
    chain = TOOL_REGISTRY["opa"]["darwin"]
    assert len(chain) == 2, "darwin chain must be brew → GitHub release"
    assert isinstance(chain[0], BrewMechanism)
    assert chain[0].formula == "opa"
    assert isinstance(chain[1], GitHubReleaseBinaryMechanism)
    assert chain[1].repo == "open-policy-agent/opa"
    assert chain[1].binary == "opa"


def test_opa_linux_chain_github_only() -> None:
    chain = TOOL_REGISTRY["opa"]["linux"]
    assert len(chain) == 1, "linux chain must be GitHub release only"
    assert isinstance(chain[0], GitHubReleaseBinaryMechanism)
    assert chain[0].repo == "open-policy-agent/opa"
    assert chain[0].binary == "opa"


def test_opa_win32_chain_winget_scoop_github() -> None:
    chain = TOOL_REGISTRY["opa"]["win32"]
    assert len(chain) == 3, "win32 chain must be winget → scoop → GitHub release"
    assert isinstance(chain[0], WingetMechanism)
    assert chain[0].package_id == "OpenPolicyAgent.OPA"
    assert isinstance(chain[1], ScoopMechanism)
    assert chain[1].package == "opa"
    assert isinstance(chain[2], GitHubReleaseBinaryMechanism)
    assert chain[2].repo == "open-policy-agent/opa"
    assert chain[2].binary == "opa.exe"


def test_opa_verify_block_shape() -> None:
    verify = TOOL_REGISTRY["opa"]["verify"]
    assert verify["cmd"] == ["opa", "version"], (
        "OPA exposes its version via the `opa version` subcommand, not `--version`"
    )
    pattern = re.compile(verify["regex"])
    # Sample first line of `opa version` output: "Version: 1.16.1".
    assert pattern.search("Version: 1.16.1") is not None
    assert pattern.search("Version: 0.70.0") is not None
    assert pattern.search("Version: 1.0.0-rc.1") is not None
