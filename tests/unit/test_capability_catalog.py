"""Tests for the capability catalog generator (spec-153 W5, T-21).

The generator (``scripts/gen_capability_catalog.py``) reads the canonical
skill (``.claude/skills/ai-*/SKILL.md``) and agent (``.claude/agents/ai-*.md``)
frontmatter and renders a deterministic markdown catalog wrapped in
``<!-- catalog:start -->`` / ``<!-- catalog:end -->`` markers. It is a derived,
rebuildable cache (SSOT remains the skill/agent files); ``apply_to`` performs an
idempotent in-place replacement of the marker block, and the drift check fails
when the rendered counts diverge from the canonical registry / on-disk truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ai_engineering.config.framework_defaults import DEFAULT_SKILLS_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPO_ROOT / "scripts" / "gen_capability_catalog.py"

CATALOG_START = "<!-- catalog:start -->"
CATALOG_END = "<!-- catalog:end -->"

# The number of user-facing agents is a fixed contract: the glob ``ai-*.md``
# under ``.claude/agents/`` excludes the internal review-*/reviewer-*/verifier-*
# families. See CLAUDE.md §12 ("Agents (9)").
EXPECTED_AGENT_COUNT = 9


def _load_generator():
    """Import ``scripts/gen_capability_catalog.py`` as a module.

    Imported by path because ``scripts/`` is not an installed package; this is
    the same standalone-dev-script contract the generator ships under.
    """
    spec = importlib.util.spec_from_file_location("gen_capability_catalog", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    if not GENERATOR_PATH.is_file():
        pytest.fail(
            f"generator absent: {GENERATOR_PATH} — implement T-22 "
            "(scripts/gen_capability_catalog.py)"
        )
    return _load_generator()


def test_render_section_is_marker_wrapped(gen) -> None:
    """The rendered section is delimited by the catalog markers."""
    section = gen.render_section(REPO_ROOT)
    assert section.startswith(CATALOG_START)
    assert section.rstrip().endswith(CATALOG_END)
    # Markers appear exactly once each (no nesting / duplication).
    assert section.count(CATALOG_START) == 1
    assert section.count(CATALOG_END) == 1


def test_render_section_includes_known_skill_and_description(gen) -> None:
    """A known skill name and a substring of its description are rendered."""
    section = gen.render_section(REPO_ROOT)
    # ai-build is a stable canonical skill; its description mentions the
    # implementation gateway role.
    assert "ai-build" in section
    assert "implementation gateway" in section.lower()


def test_render_section_includes_known_agent(gen) -> None:
    """A known agent name is rendered in the catalog."""
    section = gen.render_section(REPO_ROOT)
    assert "ai-explore" in section


def test_render_section_counts_match_canonical_truth(gen) -> None:
    """Rendered skill/agent counts equal the registry / on-disk agent truth."""
    skill_count, agent_count = gen.count_capabilities(REPO_ROOT)
    assert skill_count == len(DEFAULT_SKILLS_REGISTRY)
    assert agent_count == EXPECTED_AGENT_COUNT


def test_render_section_is_deterministic(gen) -> None:
    """Two renders of the same source produce identical bytes (sorted output)."""
    first = gen.render_section(REPO_ROOT)
    second = gen.render_section(REPO_ROOT)
    assert first == second


def test_apply_to_creates_block_then_idempotent(gen, tmp_path: Path) -> None:
    """apply_to replaces only the marker block and is byte-idempotent."""
    target = tmp_path / "README.md"
    before = "# Title\n\nIntro paragraph.\n\n"
    after = "\n## Trailing section\n\nKept verbatim.\n"
    sentinel = "ZZZ_STALE_BLOCK_SENTINEL_ZZZ"
    target.write_text(
        f"{before}{CATALOG_START}\n{sentinel}\n{CATALOG_END}{after}", encoding="utf-8"
    )

    gen.apply_to(target, REPO_ROOT)
    first = target.read_text(encoding="utf-8")

    # Content outside the markers is untouched.
    assert first.startswith(before)
    assert first.endswith(after)
    # The stale block content is gone; real content is in.
    assert sentinel not in first
    assert "ai-build" in first

    # Running twice yields identical bytes.
    gen.apply_to(target, REPO_ROOT)
    second = target.read_text(encoding="utf-8")
    assert first == second


def test_apply_to_without_markers_raises(gen, tmp_path: Path) -> None:
    """apply_to raises a clear error when the target has no marker block.

    The caller (dev sync / install) uses this signal to fail open until
    Wave 6 adds the markers to the README.
    """
    target = tmp_path / "README.md"
    target.write_text("# No markers here\n", encoding="utf-8")
    with pytest.raises(gen.MarkersNotFoundError):
        gen.apply_to(target, REPO_ROOT)


def test_check_passes_for_freshly_applied_block(gen, tmp_path: Path) -> None:
    """check() returns True (no drift) immediately after apply_to."""
    target = tmp_path / "README.md"
    target.write_text(f"head\n{CATALOG_START}\nx\n{CATALOG_END}\ntail\n", encoding="utf-8")
    gen.apply_to(target, REPO_ROOT)
    assert gen.check(target, REPO_ROOT) is True


def test_check_fails_when_block_is_stale(gen, tmp_path: Path) -> None:
    """check() returns False when the on-disk block diverges from a fresh render."""
    target = tmp_path / "README.md"
    target.write_text(
        f"head\n{CATALOG_START}\nstale-and-wrong\n{CATALOG_END}\ntail\n",
        encoding="utf-8",
    )
    assert gen.check(target, REPO_ROOT) is False


def test_drift_check_fails_on_count_divergence(gen, tmp_path: Path, monkeypatch) -> None:
    """The drift check fails when rendered counts diverge from registry truth.

    Simulated by pointing the generator at a skills root with a different
    skill set than the canonical registry: the count helper must report the
    on-disk number, which then mismatches len(DEFAULT_SKILLS_REGISTRY).
    """
    fake_root = tmp_path / "fake_repo"
    skills_dir = fake_root / ".claude" / "skills"
    agents_dir = fake_root / ".claude" / "agents"
    skills_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)

    # Only two skills on disk — fewer than the 53-entry registry.
    for name in ("ai-foo", "ai-bar"):
        d = skills_dir / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f'---\nname: {name}\ndescription: "Fake {name}."\n---\n# {name}\n',
            encoding="utf-8",
        )
    (agents_dir / "ai-foo.md").write_text(
        '---\nname: ai-foo\ndescription: "Fake agent."\n---\n# foo\n',
        encoding="utf-8",
    )

    skill_count, agent_count = gen.count_capabilities(fake_root)
    assert skill_count == 2
    assert agent_count == 1
    # The drift gate compares to canonical truth → mismatch.
    assert skill_count != len(DEFAULT_SKILLS_REGISTRY)
    assert agent_count != EXPECTED_AGENT_COUNT


class TestCatalogBridge:
    """In-package bridge consumed by `ai-eng dev sync` + install/update (T-23).

    These tests pin the fail-open / drift contract the CLI relies on without
    spinning up a full CLI runner.
    """

    def _fake_root_with_markers(self, tmp_path: Path, body: str) -> Path:
        """Build a fake project root linking the real generator + sources."""
        root = tmp_path / "proj"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "gen_capability_catalog.py").symlink_to(GENERATOR_PATH)
        (root / ".claude").symlink_to(REPO_ROOT / ".claude")
        (root / ".ai-engineering").mkdir()
        (root / ".ai-engineering" / "README.md").write_text(
            f"# Manual\n\nIntro.\n\n{CATALOG_START}\n{body}\n{CATALOG_END}\n\nFooter.\n",
            encoding="utf-8",
        )
        return root

    def test_apply_then_check_in_sync(self, tmp_path: Path) -> None:
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
            check_capability_catalog,
        )

        root = self._fake_root_with_markers(tmp_path, "stale")
        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.APPLIED
        assert applied.ok
        checked = check_capability_catalog(root)
        assert checked.status is CatalogStatus.IN_SYNC
        assert checked.ok

    def _template_twin(self, root: Path) -> Path:
        return root / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "README.md"

    def test_apply_regenerates_template_twin(self, tmp_path: Path) -> None:
        """A default apply writes BOTH the live manual and its install-template twin.

        spec-187 W4 root-cause fix: before, `ai-eng dev sync` regenerated only
        the live `.ai-engineering/README.md`, so the twin at
        `src/ai_engineering/templates/.ai-engineering/README.md` drifted every
        regen and had to be manually `cp`-ed. The generator now writes both,
        byte-identical.
        """
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
        )

        root = self._fake_root_with_markers(tmp_path, "stale-live")
        twin = self._template_twin(root)
        twin.parent.mkdir(parents=True)
        twin.write_text(
            f"# Twin\n\nIntro.\n\n{CATALOG_START}\nstale-twin\n{CATALOG_END}\n\nFooter.\n",
            encoding="utf-8",
        )

        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.APPLIED

        live_text = (root / ".ai-engineering" / "README.md").read_text(encoding="utf-8")
        twin_text = twin.read_text(encoding="utf-8")
        # Twin was regenerated (stale sentinel gone, real content in).
        assert "stale-twin" not in twin_text
        assert "ai-build" in twin_text
        # Both catalog blocks are byte-identical (parity guarantee).
        live_block = live_text.split(CATALOG_START, 1)[1].split(CATALOG_END, 1)[0]
        twin_block = twin_text.split(CATALOG_START, 1)[1].split(CATALOG_END, 1)[0]
        assert live_block == twin_block

    def test_check_detects_twin_drift(self, tmp_path: Path) -> None:
        """`dev sync --check` fails when only the install-template twin drifts."""
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
            check_capability_catalog,
        )

        root = self._fake_root_with_markers(tmp_path, "stale-live")
        twin = self._template_twin(root)
        twin.parent.mkdir(parents=True)
        twin.write_text(
            f"# Twin\n\nIntro.\n\n{CATALOG_START}\nstale-twin\n{CATALOG_END}\n\nFooter.\n",
            encoding="utf-8",
        )
        # Regenerate both, then corrupt ONLY the twin block.
        apply_capability_catalog(root)
        good = twin.read_text(encoding="utf-8")
        twin.write_text(good.replace("ai-build", "ai-build-CORRUPTED", 1), encoding="utf-8")

        checked = check_capability_catalog(root)
        assert checked.status is CatalogStatus.DRIFT
        assert checked.ok is False

    def test_check_detects_drift(self, tmp_path: Path) -> None:
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            check_capability_catalog,
        )

        # Marker block is present but never regenerated → drift.
        root = self._fake_root_with_markers(tmp_path, "definitely-not-the-real-catalog")
        checked = check_capability_catalog(root)
        assert checked.status is CatalogStatus.DRIFT
        assert checked.ok is False  # this is what fails `dev sync --check`

    def test_fail_open_when_no_markers(self, tmp_path: Path) -> None:
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
            check_capability_catalog,
        )

        root = tmp_path / "proj"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "gen_capability_catalog.py").symlink_to(GENERATOR_PATH)
        (root / ".claude").symlink_to(REPO_ROOT / ".claude")
        (root / ".ai-engineering").mkdir()
        (root / ".ai-engineering" / "README.md").write_text(
            "# Manual\n\nNo markers yet (Wave 6 adds them).\n", encoding="utf-8"
        )
        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.SKIPPED_NO_MARKERS
        assert applied.ok  # fail-open: apply does not error
        checked = check_capability_catalog(root)
        assert checked.status is CatalogStatus.SKIPPED_NO_MARKERS
        assert checked.ok  # fail-open: keeps `dev sync --check` green pre-Wave-6

    def test_skips_when_generator_absent(self, tmp_path: Path) -> None:
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
        )

        # Consumer project: README exists with markers but no generator script.
        root = tmp_path / "consumer"
        (root / ".ai-engineering").mkdir(parents=True)
        (root / ".ai-engineering" / "README.md").write_text(
            f"{CATALOG_START}\nx\n{CATALOG_END}\n", encoding="utf-8"
        )
        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.SKIPPED_NO_GENERATOR
        assert applied.ok

    def test_skips_when_target_absent(self, tmp_path: Path) -> None:
        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
        )

        root = tmp_path / "proj"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "gen_capability_catalog.py").symlink_to(GENERATOR_PATH)
        (root / ".claude").symlink_to(REPO_ROOT / ".claude")
        # No .ai-engineering/README.md at all.
        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.SKIPPED_NO_TARGET
        assert applied.ok

    def test_skips_when_spec_cannot_load(self, tmp_path: Path, monkeypatch) -> None:
        """Generator file present but importlib yields no spec → treated as absent.

        Covers the defensive ``spec is None`` branch in ``_load_generator`` so the
        no-suppression rule holds without a ``# pragma: no cover`` marker.
        """
        import importlib.util as _ilu

        from ai_engineering.installer.capability_catalog import (
            CatalogStatus,
            apply_capability_catalog,
        )

        root = self._fake_root_with_markers(tmp_path, "stale")
        monkeypatch.setattr(_ilu, "spec_from_file_location", lambda *a, **k: None)
        applied = apply_capability_catalog(root)
        assert applied.status is CatalogStatus.SKIPPED_NO_GENERATOR
        assert applied.ok
