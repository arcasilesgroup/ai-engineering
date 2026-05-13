"""Color-field schema compliance across mirror surfaces.

Background — each surface validates the ``color:`` YAML frontmatter
field differently. Empirical schemas (researched 2026-05-12):

- Claude Code: enum of 8 names (red, blue, green, yellow, purple,
  orange, pink, cyan). Hex silently dropped. Canonical truth.
- OpenCode: hex ``^#[0-9a-fA-F]{6}$`` OR semantic tokens
  (primary, secondary, accent, success, warning, error, info).
  Zod-strict — fails fast on invalid (root of probando/ bug).
- Gemini / Copilot / Cursor / Antigravity: ``color`` field not
  documented in their schemas. Strip to avoid future strict-mode
  breakage (defensive: same Zod-tightening risk as OpenCode).
- Codex: ``color`` field undocumented in spec but accepts names
  empirically. Passthrough.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TPL = REPO / "src" / "ai_engineering" / "templates" / "project"

_OPENCODE_VALID_TOKENS = {
    "primary",
    "secondary",
    "accent",
    "success",
    "warning",
    "error",
    "info",
}
_CLAUDE_VALID_NAMES = {
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "orange",
    "pink",
    "cyan",
}


def _extract_color(path: Path) -> str | None:
    """Return value of ``color:`` line in YAML frontmatter, or None."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("color:"):
            return line.split(":", 1)[1].strip()
        if line.strip() == "---" and not line.startswith("color"):
            continue
    return None


def _iter_agent_files(surface_dir: Path, suffix: str = ".md") -> list[Path]:
    if not surface_dir.is_dir():
        return []
    return sorted(p for p in surface_dir.glob(f"ai-*{suffix}") if p.is_file())


# ── OpenCode: color must be hex or semantic token ─────────────────────────


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".opencode" / "agents"))
def test_opencode_color_is_valid_token_or_hex(agent_path: Path) -> None:
    value = _extract_color(agent_path)
    assert value is not None, f"{agent_path.name}: missing color"
    is_hex = value.startswith("#") and len(value) == 7
    is_token = value in _OPENCODE_VALID_TOKENS
    assert is_hex or is_token, (
        f"{agent_path.name}: color={value!r} is neither hex nor "
        f"OpenCode semantic token ({sorted(_OPENCODE_VALID_TOKENS)})"
    )


# ── Gemini / Cursor / Antigravity / Copilot: color field stripped ─────────


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".gemini" / "agents"))
def test_gemini_color_stripped(agent_path: Path) -> None:
    assert _extract_color(agent_path) is None, (
        f"{agent_path.name}: color field must be stripped from Gemini mirror"
    )


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".cursor" / "agents", suffix=".mdc"))
def test_cursor_color_stripped(agent_path: Path) -> None:
    assert _extract_color(agent_path) is None, (
        f"{agent_path.name}: color field must be stripped from Cursor mirror"
    )


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".agent" / "agents"))
def test_antigravity_color_stripped(agent_path: Path) -> None:
    assert _extract_color(agent_path) is None, (
        f"{agent_path.name}: color field must be stripped from Antigravity mirror"
    )


def _iter_copilot_agent_files() -> list[Path]:
    d = TPL / "agents"  # spec-128: .github/agents lands under templates/project/agents
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.agent.md") if p.is_file())


@pytest.mark.parametrize("agent_path", _iter_copilot_agent_files())
def test_copilot_color_stripped(agent_path: Path) -> None:
    assert _extract_color(agent_path) is None, (
        f"{agent_path.name}: color field must be stripped from Copilot mirror"
    )


# ── Claude (canonical) + Codex (passthrough): names preserved ─────────────


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".claude" / "agents"))
def test_claude_color_is_valid_name(agent_path: Path) -> None:
    value = _extract_color(agent_path)
    if value is None:
        return  # specialist agents may carry no color — tolerable
    assert value in _CLAUDE_VALID_NAMES, (
        f"{agent_path.name}: color={value!r} not in Claude's 8-name enum"
    )


@pytest.mark.parametrize("agent_path", _iter_agent_files(TPL / ".codex" / "agents"))
def test_codex_color_passthrough(agent_path: Path) -> None:
    value = _extract_color(agent_path)
    assert value is not None, f"{agent_path.name}: codex must passthrough color"
    assert value in _CLAUDE_VALID_NAMES, (
        f"{agent_path.name}: codex color={value!r} not in canonical enum"
    )
