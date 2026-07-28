"""The surface support tiers are a contract, not prose (spec-201 D-201-03).

`manifest.yml` enables six surfaces. Before this spec nothing stated what
"enabled" bought you, and nothing checked that a surface documented as guarded
actually had a hook plane. That is the same blindness that let two Codex
bypasses ship undetected: every gate asserted on strings, none on behaviour.

These tests assert three things:
1. Every enabled surface appears exactly once in the `gate-policy.md` tier table.
2. Every GUARDED surface has a real, non-empty hook config on disk whose commands
   name guard scripts that EXIST — plus, for the two guards that are cheap to
   drive, that the plane actually denies.
3. Every CONTENT-ONLY surface has no such config, so the table cannot quietly
   understate a surface either.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_POLICY = REPO_ROOT / ".ai-engineering" / "reference" / "gate-policy.md"
MANIFEST = REPO_ROOT / ".ai-engineering" / "manifest.yml"
HOOKS_DIR = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"

_TIER_HEADING = "## Surface support tiers"
_ROW_RE = re.compile(r"^\|\s*`([a-z-]+)`\s*\|\s*(GUARDED|CONTENT-ONLY)([^|]*)\|(.*)$")

# Where each surface's hook plane lives, and where its command strings name the
# guard scripts. For OpenCode the plugin entry is a thin re-export, so the guard
# names live in the canonical bridge it points at.
_HOOK_CONFIGS: dict[str, tuple[Path, tuple[Path, ...]]] = {
    "claude-code": (REPO_ROOT / ".claude" / "settings.json", ()),
    "codex": (REPO_ROOT / ".codex" / "hooks.json", ()),
    "cursor": (REPO_ROOT / ".cursor" / "hooks.json", (HOOKS_DIR / "cursor-hook-bridge.py",)),
    "github-copilot": (REPO_ROOT / ".github" / "hooks" / "hooks.json", ()),
    "opencode": (
        REPO_ROOT / ".opencode" / "plugin" / "ai-engineering.ts",
        (HOOKS_DIR / "opencode-hook-bridge.ts",),
    ),
}

_SCRIPT_RE = re.compile(r"([\w.-]+\.(?:py|sh))")


def _tier_table() -> dict[str, tuple[str, str]]:
    """Return `{surface: (tier, caveat_plus_row_text)}` from the tier section."""
    body = GATE_POLICY.read_text(encoding="utf-8")
    assert _TIER_HEADING in body, f"{GATE_POLICY} has no '{_TIER_HEADING}' section"
    section = body.split(_TIER_HEADING, 1)[1]
    section = section.split("\n## ", 1)[0]

    rows: dict[str, tuple[str, str]] = {}
    for line in section.splitlines():
        match = _ROW_RE.match(line.strip())
        if not match:
            continue
        surface, tier, caveat, rest = match.groups()
        assert surface not in rows, f"{surface} appears more than once in the tier table"
        rows[surface] = (tier, caveat + rest)
    return rows


def _enabled_surfaces() -> list[str]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return list(data["surfaces"]["enabled"])


def test_every_enabled_surface_has_exactly_one_tier_row() -> None:
    table = _tier_table()
    enabled = _enabled_surfaces()

    assert sorted(table) == sorted(enabled), (
        f"tier table {sorted(table)} != manifest surfaces.enabled {sorted(enabled)}"
    )


def test_guarded_surfaces_have_a_live_hook_plane() -> None:
    """A GUARDED row must be backed by a config naming guards that exist."""
    guard_scripts = {p.name for p in HOOKS_DIR.glob("*.py")} | {
        p.name for p in HOOKS_DIR.glob("*.sh")
    }

    for surface, (tier, _row) in _tier_table().items():
        if tier != "GUARDED":
            continue
        assert surface in _HOOK_CONFIGS, f"{surface} is GUARDED with no known hook config"
        config, extra_sources = _HOOK_CONFIGS[surface]
        assert config.is_file(), f"{surface} is GUARDED but {config} does not exist"
        text = config.read_text(encoding="utf-8")
        assert text.strip(), f"{surface}: {config} is empty"

        for extra in extra_sources:
            assert extra.is_file(), f"{surface}: {config} points at missing {extra}"
            assert extra.name in text, f"{surface}: {config} does not reference {extra.name}"
            text += extra.read_text(encoding="utf-8")

        named = {s for s in _SCRIPT_RE.findall(text) if s in guard_scripts}
        assert named, (
            f"{surface}: no command in {config} names a guard script that exists under {HOOKS_DIR}"
        )


def test_content_only_surfaces_have_no_hook_plane() -> None:
    """A CONTENT-ONLY row must not quietly own an enforcement plane."""
    for surface, (tier, _row) in _tier_table().items():
        if tier != "CONTENT-ONLY":
            continue
        config = _HOOK_CONFIGS.get(surface)
        assert config is None or not config[0].exists(), (
            f"{surface} is documented CONTENT-ONLY but ships {config[0]} — the table "
            "understates the surface"
        )


def test_best_effort_surfaces_carry_the_caveat() -> None:
    """OpenCode and Copilot must not read as equivalent to Claude Code."""
    table = _tier_table()

    for surface in ("opencode", "github-copilot"):
        tier, row = table[surface]
        assert tier == "GUARDED"
        assert "best-effort" in row.lower(), (
            f"{surface} is GUARDED without the best-effort caveat — that is an "
            "overclaim on a security boundary"
        )


def test_residual_gaps_are_named_in_words() -> None:
    """The section states what it does NOT close, not just what it does."""
    body = GATE_POLICY.read_text(encoding="utf-8")
    section = body.split(_TIER_HEADING, 1)[1].split("\n## ", 1)[0]

    for phrase in ("unsigned", "INCLUDE_SUFFIXES", "operator-verified"):
        assert phrase in section, f"tier section must name the residual gap: {phrase}"


def test_codex_config_wires_both_previously_bypassed_guards() -> None:
    """The two documented Codex bypasses stay closed."""
    config = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entries in config["hooks"].values()
        for group in entries
        for hook in group.get("hooks", [])
    ]

    for guard in ("no-verify-guard.py", "injection-read-guard.py"):
        assert any(cmd.endswith(guard) for cmd in commands), (
            f"{guard} is absent from .codex/hooks.json — the bypass is reopened"
        )


def test_copilot_deny_plane_actually_denies() -> None:
    """Executable proof for the Copilot GUARDED row."""
    script = HOOKS_DIR / "copilot-deny.sh"
    assert script.is_file()
    if not _has_jq():
        pytest.skip("jq absent: copilot-deny.sh is fail-open without it (best-effort tier)")

    payload = json.dumps(
        {"toolName": "bash", "toolArgs": {"command": "git commit --no-verify -m x"}}
    )
    result = subprocess.run(
        ["bash", str(script)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["permissionDecision"] == "deny"
    assert body["permissionDecisionReason"]


def _has_jq() -> bool:
    import shutil

    return shutil.which("jq") is not None
