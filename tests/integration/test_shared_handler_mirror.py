"""Phase 1 GREEN: shared handlers propagate to all IDE mirrors (spec-106 R-1).

R-1 mitigation: ``_shared/execution-kernel.md`` MUST exist in every IDE
mirror surface (.codex/, .gemini/, .github/) so cross-IDE consumers see the
same canonical kernel that the .claude/ orchestrators delegate to.

Mirror sync applies ``translate_refs()`` per-target IDE so canonical
``.claude/`` paths inside the kernel body get rewritten to the IDE-specific
scheme. Byte-for-byte equality is therefore NOT the right invariant; instead
we assert that each mirror equals ``translate_refs(canonical, target_ide)``,
which is what spec-106 D-106-08 guarantees.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL = REPO_ROOT / ".claude" / "skills" / "_shared" / "execution-kernel.md"
MIRROR_TARGETS = (
    (REPO_ROOT / ".codex" / "skills" / "_shared" / "execution-kernel.md", "codex"),
    (REPO_ROOT / ".gemini" / "skills" / "_shared" / "execution-kernel.md", "gemini"),
    (REPO_ROOT / ".github" / "skills" / "_shared" / "execution-kernel.md", "copilot"),
)
INSTALL_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / "project"
    / ".claude"
    / "skills"
    / "_shared"
    / "execution-kernel.md"
)


def test_canonical_kernel_exists() -> None:
    """Pre-condition for mirror checks: canonical source must exist."""
    assert CANONICAL.exists(), f"missing canonical source: {CANONICAL}"


@pytest.mark.parametrize("mirror_path,target_ide", MIRROR_TARGETS)
def test_mirror_matches_translated_canonical(mirror_path: Path, target_ide: str) -> None:
    """Each IDE mirror equals translate_refs(canonical, ide).

    Mirror sync rewrites ``.claude/`` references inside the kernel body to
    the IDE-specific path scheme so cross-IDE links stay valid. Byte-equality
    against the canonical source is wrong; equality against the translated
    canonical is the correct invariant.
    """
    from scripts.sync_command_mirrors import translate_refs

    assert mirror_path.exists(), (
        f"missing mirror for IDE '{target_ide}': {mirror_path}. "
        f"Run `uv run ai-eng sync` to regenerate IDE mirrors."
    )

    expected = translate_refs(CANONICAL.read_text(encoding="utf-8"), target_ide)
    actual = mirror_path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Mirror drift for {mirror_path.relative_to(REPO_ROOT)} "
        f"(target={target_ide}). Expected ref-translated canonical content."
    )


def test_install_template_byte_equivalent_to_canonical() -> None:
    """The .claude/ install template carries the canonical kernel as-is.

    Templates copied into a fresh project install must be byte-equivalent to
    the canonical source so install-time and dev-time consumers see the same
    content. No ref translation is applied -- both surfaces use the same
    ``.claude/`` path scheme.
    """
    assert INSTALL_TEMPLATE.exists(), (
        f"missing install template mirror: {INSTALL_TEMPLATE}. "
        f"Run `uv run ai-eng sync` to regenerate."
    )
    assert INSTALL_TEMPLATE.read_bytes() == CANONICAL.read_bytes(), (
        "Install template kernel must be byte-equivalent to canonical source"
    )
