"""md_mirror conformance — spec-131 S1 contract (sub-001 T-1.1).

The md_mirror checker (``tools/skill_lint/checks/md_mirror.py``) is the
deterministic enforcement surface for spec-131 D-131-03 (byte-equivalent
mirror strategy) and D-131-04 (CONSTITUTION rescoped to project-identity).

Five sub-checks per S1 acceptance:

1. **sha256 equivalence** — AGENTS.md, CLAUDE.md, and
   ``.github/copilot-instructions.md`` carry IDENTICAL canonical payload
   bytes after stripping the ``<!-- ide-extras:start -->…<!-- ide-extras:end -->``
   fence.
2. **no @AGENTS.md import** — no mirror file contains the literal
   ``@AGENTS.md`` import directive (a Claude-only quirk that broke
   parity).
3. **no retired Gemini artifacts** — spec-151 deletes `GEMINI.md` and `.gemini/`;
   the sweep refuses to find them.
4. **no .codex/AGENTS.md orphan** — Codex reads root AGENTS.md natively;
   an in-repo ``.codex/AGENTS.md`` would shadow the canonical surface.
5. **CONSTITUTION.md is clean** — after D-131-04 migration, the
   project-identity CONSTITUTION must NOT contain any header from
   ``FORBIDDEN_CONSTITUTION_HEADERS`` (those are AI-behaviour headers
   that migrated into CANONICAL.md).

This file is the TDD RED partner of T-1.9. **DO NOT MODIFY THIS FILE
during T-1.9 GREEN.** The checker implementation must change to satisfy
these assertions.
"""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures: synthetic repo layout for unit isolation.
# ---------------------------------------------------------------------------

# spec-134 sub-005 mirror diet: the canonical payload no longer
# carries §10/§14/§15/§16 prose; those sections moved to ``docs/``.
# The fixture below mirrors that contract — synthetic body holds
# bootstrap + pointer rows only. Tests that assert "verbatim heading
# returned" mutate `_CANONICAL_PAYLOAD` in-flight to reintroduce the
# offending heading.
_CANONICAL_PAYLOAD = textwrap.dedent(
    """\
    # Header

    ## 0. Bootstrap

    Read CANONICAL.md.

    ## 10. Engineering Principles (pointer)

    See `.ai-engineering/reference/principles.md` for §10.1 KISS … §10.8 Hexagonal.
    """
)


def _write_mirror(repo: Path, rel: str, payload: str, extras: str = "") -> Path:
    """Write a mirror file with canonical payload + IDE-extras fence.

    Mirrors reality: every output of ``assemble_mirror_payload`` (in
    ``scripts/sync_mirrors/core.py``) carries a fence at end-of-file —
    AGENTS.md carries an empty fence placeholder; CLAUDE /
    Copilot carry filled fences. The fence position is canonical so
    sha256 equivalence holds after fence-strip.
    """
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if extras:
        fence = "<!-- ide-extras:start -->\n" + extras + "\n<!-- ide-extras:end -->"
    else:
        fence = "<!-- ide-extras:start -->\n<!-- ide-extras:end -->"
    content = payload + fence + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _build_fixture(repo: Path, *, with_extras: bool = True) -> None:
    """Lay out a synthetic three-mirror tree with matching canonical payload."""
    _write_mirror(repo, "AGENTS.md", _CANONICAL_PAYLOAD)
    _write_mirror(
        repo,
        "CLAUDE.md",
        _CANONICAL_PAYLOAD,
        extras="Claude-specific hot-path bullets." if with_extras else "",
    )
    _write_mirror(
        repo,
        ".github/copilot-instructions.md",
        _CANONICAL_PAYLOAD,
        extras="Copilot hooks wiring table." if with_extras else "",
    )
    # Project-identity CONSTITUTION: only allowed headers.
    (repo / "CONSTITUTION.md").write_text(
        textwrap.dedent(
            """\
            # CONSTITUTION

            ## Mission

            Ship safe software fast.

            ## Stakeholders

            - team A
            - team B

            ## Prohibitions

            - No secrets in source.
            """
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Check 1 — sha256 equivalence across the three root mirrors (with fence strip).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sha256_equivalence_passes_with_matching_payload(tmp_path: Path) -> None:
    """OK when all three root mirrors share the same canonical payload."""
    _build_fixture(tmp_path)
    from skill_lint.checks.md_mirror import check_sha256_equivalence

    result = check_sha256_equivalence(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_sha256_equivalence_passes_when_extras_differ(tmp_path: Path) -> None:
    """OK when payload matches but ide-extras blocks differ (R-1.1 mitigation)."""
    _build_fixture(tmp_path, with_extras=True)
    from skill_lint.checks.md_mirror import check_sha256_equivalence

    result = check_sha256_equivalence(tmp_path)
    assert result.severity == "OK", (
        f"ide-extras fence must be stripped before hashing; got {result.reason}"
    )


@pytest.mark.unit
def test_sha256_equivalence_fails_when_payload_drifts(tmp_path: Path) -> None:
    """CRITICAL when a mirror's canonical payload differs from the others."""
    _build_fixture(tmp_path)
    # Mutate the AGENTS.md canonical payload.
    drifted = _CANONICAL_PAYLOAD.replace("Read CANONICAL.md.", "Read AGENTS.md.")
    (tmp_path / "AGENTS.md").write_text(drifted, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_sha256_equivalence

    result = check_sha256_equivalence(tmp_path)
    assert result.severity == "CRITICAL", result.reason


# ---------------------------------------------------------------------------
# Check 2 — no @AGENTS.md import directive in any mirror.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_agents_import_passes_for_clean_mirrors(tmp_path: Path) -> None:
    """OK when no mirror contains the @AGENTS.md import directive."""
    _build_fixture(tmp_path)
    from skill_lint.checks.md_mirror import check_no_agents_import

    result = check_no_agents_import(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_no_agents_import_fails_when_directive_present(tmp_path: Path) -> None:
    """CRITICAL when CLAUDE.md contains @AGENTS.md import."""
    _build_fixture(tmp_path)
    polluted = _CANONICAL_PAYLOAD + "\n@AGENTS.md\n"
    (tmp_path / "CLAUDE.md").write_text(polluted, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_no_agents_import

    result = check_no_agents_import(tmp_path)
    assert result.severity == "CRITICAL", result.reason


# ---------------------------------------------------------------------------
# Check 3 — no retired Gemini artifacts on disk.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_gemini_artifacts_pass_when_absent(tmp_path: Path) -> None:
    """OK when GEMINI.md and .gemini do not exist."""
    _build_fixture(tmp_path)
    from skill_lint.checks.md_mirror import check_no_gemini_orphan

    result = check_no_gemini_orphan(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_no_gemini_artifacts_fail_when_present(tmp_path: Path) -> None:
    """CRITICAL when retired Gemini artifacts exist."""
    _build_fixture(tmp_path)
    orphan = tmp_path / ".gemini" / "settings.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("{}\n", encoding="utf-8")
    from skill_lint.checks.md_mirror import check_no_gemini_orphan

    result = check_no_gemini_orphan(tmp_path)
    assert result.severity == "CRITICAL", result.reason


# ---------------------------------------------------------------------------
# Check 4 — no .codex/AGENTS.md orphan on disk.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_codex_orphan_passes_when_absent(tmp_path: Path) -> None:
    """OK when .codex/AGENTS.md does not exist (Codex reads root)."""
    _build_fixture(tmp_path)
    from skill_lint.checks.md_mirror import check_no_codex_orphan

    result = check_no_codex_orphan(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_no_codex_orphan_fails_when_present(tmp_path: Path) -> None:
    """CRITICAL when .codex/AGENTS.md exists (would shadow root)."""
    _build_fixture(tmp_path)
    orphan = tmp_path / ".codex" / "AGENTS.md"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("stale codex overlay\n", encoding="utf-8")
    from skill_lint.checks.md_mirror import check_no_codex_orphan

    result = check_no_codex_orphan(tmp_path)
    assert result.severity == "CRITICAL", result.reason


# ---------------------------------------------------------------------------
# Check 5 — CONSTITUTION.md does NOT contain forbidden AI-behaviour headers.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constitution_clean_passes_for_project_identity(tmp_path: Path) -> None:
    """OK when CONSTITUTION.md only contains project-identity headers."""
    _build_fixture(tmp_path)
    from skill_lint.checks.md_mirror import check_constitution_clean

    result = check_constitution_clean(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
@pytest.mark.parametrize(
    "forbidden_header",
    [
        "Simplicity First",
        "Plan-Mode Default",
        "Surgical Changes",
        "Goal-Driven Execution",
        "Subagent Strategy",
        "Self-Improvement Loop",
        "Demand Elegance",
        "Autonomous Bug Fixing",
        "KISS",
        "YAGNI",
        "SOLID",
        "DRY",
        "TDD",
        "SDD",
        "Clean Code",
        "Hexagonal Architecture",
        "Think Before Coding",
    ],
)
def test_constitution_clean_fails_for_each_forbidden_header(
    tmp_path: Path, forbidden_header: str
) -> None:
    """CRITICAL when CONSTITUTION.md contains any AI-behaviour header."""
    _build_fixture(tmp_path)
    polluted = textwrap.dedent(
        f"""\
        # CONSTITUTION

        ## Mission

        Ship safe software fast.

        ## {forbidden_header}

        Migrated AI-behaviour content (shouldn't be here).
        """
    )
    (tmp_path / "CONSTITUTION.md").write_text(polluted, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_constitution_clean

    result = check_constitution_clean(tmp_path)
    assert result.severity == "CRITICAL", result.reason
    assert forbidden_header in result.reason, (
        f"reason must surface offending header {forbidden_header!r}; got {result.reason!r}"
    )


# ---------------------------------------------------------------------------
# Forbidden-header constant exposure (consumed by tooling beyond this lint).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_forbidden_constitution_headers_constant_is_complete() -> None:
    """The exported tuple must cover every header asserted parametrically above."""
    from skill_lint.checks.md_mirror import FORBIDDEN_CONSTITUTION_HEADERS

    expected = {
        "Simplicity First",
        "Plan-Mode Default",
        "Surgical Changes",
        "Goal-Driven Execution",
        "Subagent Strategy",
        "Self-Improvement Loop",
        "Demand Elegance",
        "Autonomous Bug Fixing",
        "KISS",
        "YAGNI",
        "SOLID",
        "DRY",
        "TDD",
        "SDD",
        "Clean Code",
        "Hexagonal Architecture",
        "Think Before Coding",
    }
    assert expected.issubset(set(FORBIDDEN_CONSTITUTION_HEADERS)), (
        f"missing headers: {expected - set(FORBIDDEN_CONSTITUTION_HEADERS)}"
    )


# ---------------------------------------------------------------------------
# Driver — check_md_mirror_consistency aggregates the five sub-checks.
# ---------------------------------------------------------------------------


def _build_docs_targets(repo: Path) -> None:
    """Write the three sub-005 `docs/` destinations into the fixture root.

    The sub-005 driver requires the three ``.ai-engineering/reference/``
    targets (``principles.md``, ``mirror-authoring.md``,
    ``surface-axioms.md``) to exist on disk; their contents are not
    inspected by the lint
    sub-checks (they are content-existence guards only). Test
    fixtures therefore write stub files; integration tests
    (``test_canonical_mirror_parity.py``) cover content shape.
    """
    reference = repo / ".ai-engineering" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    (reference / "principles.md").write_text("# stub principles\n", encoding="utf-8")
    (reference / "mirror-authoring.md").write_text("# stub mirror authoring\n", encoding="utf-8")
    (reference / "surface-axioms.md").write_text("# stub surface axioms\n", encoding="utf-8")


@pytest.mark.unit
def test_driver_aggregates_all_subchecks(tmp_path: Path) -> None:
    """check_md_mirror_consistency returns ≥7 RubricResult records (sub-005)."""
    _build_fixture(tmp_path)
    _build_docs_targets(tmp_path)
    from skill_lint.checks.md_mirror import check_md_mirror_consistency

    results = check_md_mirror_consistency(tmp_path)
    assert len(results) >= 7, f"expected ≥7 sub-check results, got {len(results)}"
    severities = {r.severity for r in results}
    assert severities == {"OK"}, f"all sub-checks should pass on clean fixture, got {severities}"


@pytest.mark.unit
def test_driver_flags_drift(tmp_path: Path) -> None:
    """Driver surfaces CRITICAL when sha256 equivalence breaks."""
    _build_fixture(tmp_path)
    _build_docs_targets(tmp_path)
    drifted = _CANONICAL_PAYLOAD.replace("Read CANONICAL.md.", "DRIFT.")
    (tmp_path / "AGENTS.md").write_text(drifted, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_md_mirror_consistency

    results = check_md_mirror_consistency(tmp_path)
    criticals = [r for r in results if r.severity == "CRITICAL"]
    assert criticals, f"expected ≥1 CRITICAL result on drift, got {[r.severity for r in results]}"


# ---------------------------------------------------------------------------
# Check 6 — no extracted §10/§14/§15/§16 section headings in any mirror.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_extracted_sections_passes_on_clean_mirrors(tmp_path: Path) -> None:
    """OK when no mirror carries the verbatim extracted section headings."""
    _build_fixture(tmp_path)
    _build_docs_targets(tmp_path)
    from skill_lint.checks.md_mirror import check_no_extracted_sections_in_mirrors

    result = check_no_extracted_sections_in_mirrors(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_no_extracted_sections_fails_when_section_10_returns(tmp_path: Path) -> None:
    """CRITICAL when CLAUDE.md regains the verbatim `## 10. Engineering Principles`."""
    _build_fixture(tmp_path)
    _build_docs_targets(tmp_path)
    polluted = _CANONICAL_PAYLOAD + "\n## 10. Engineering Principles\n\nverbatim prose\n"
    (tmp_path / "CLAUDE.md").write_text(polluted, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_no_extracted_sections_in_mirrors

    result = check_no_extracted_sections_in_mirrors(tmp_path)
    assert result.severity == "CRITICAL", result.reason
    assert "CLAUDE.md" in result.reason, (
        f"reason must surface the offending mirror; got {result.reason!r}"
    )


@pytest.mark.unit
def test_no_extracted_sections_allows_pointer_stub_with_suffix(tmp_path: Path) -> None:
    """OK when a mirror carries a pointer stub (heading with `(pointer)` suffix)."""
    _build_fixture(tmp_path)
    _build_docs_targets(tmp_path)
    pointer = _CANONICAL_PAYLOAD + (
        "\n## 10. Engineering Principles (pointer)\n\nsee .ai-engineering/reference/principles.md\n"
    )
    (tmp_path / "CLAUDE.md").write_text(pointer, encoding="utf-8")
    from skill_lint.checks.md_mirror import check_no_extracted_sections_in_mirrors

    result = check_no_extracted_sections_in_mirrors(tmp_path)
    assert result.severity == "OK", (
        f"pointer stub with distinct suffix should pass; got {result.reason!r}"
    )


# ---------------------------------------------------------------------------
# Check 7 — three sub-005 docs/ targets exist on disk.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_docs_targets_present_passes_when_files_exist(tmp_path: Path) -> None:
    """OK when all three docs/ destinations exist."""
    _build_docs_targets(tmp_path)
    from skill_lint.checks.md_mirror import check_docs_targets_exist

    result = check_docs_targets_exist(tmp_path)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_docs_targets_present_fails_when_principles_missing(tmp_path: Path) -> None:
    """CRITICAL when .ai-engineering/reference/principles.md is absent."""
    _build_docs_targets(tmp_path)
    (tmp_path / ".ai-engineering" / "reference" / "principles.md").unlink()
    from skill_lint.checks.md_mirror import check_docs_targets_exist

    result = check_docs_targets_exist(tmp_path)
    assert result.severity == "CRITICAL", result.reason
    assert ".ai-engineering/reference/principles.md" in result.reason, (
        f"reason must surface the missing target; got {result.reason!r}"
    )


# ---------------------------------------------------------------------------
# Live-surface smoke test (live repo HEAD).
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_live_repo_canonical_payload_matches(project_root: Path) -> None:
    """After T-1.7 lands, the repo-root three mirrors must hash-equivalent.

    This test guards against post-merge drift: any future hand-edit of
    AGENTS / CLAUDE / copilot-instructions that breaks parity
    will fail here.
    """
    from skill_lint.checks.md_mirror import check_sha256_equivalence

    result = check_sha256_equivalence(project_root)
    assert result.severity == "OK", result.reason


# ---------------------------------------------------------------------------
# Hashing helper exposed for downstream parity tests.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_strip_ide_extras_returns_bytes_excluding_fence() -> None:
    """The fence-strip helper must remove the entire fenced block."""
    from skill_lint.checks.md_mirror import strip_ide_extras

    text = (
        "canonical body\n"
        "<!-- ide-extras:start -->\n"
        "EXTRAS_THAT_SHOULD_NOT_HASH\n"
        "<!-- ide-extras:end -->\n"
        "trailing content\n"
    )
    stripped = strip_ide_extras(text)
    assert "EXTRAS_THAT_SHOULD_NOT_HASH" not in stripped, (
        f"fence body must be removed; got {stripped!r}"
    )
    # The canonical body and trailing content must survive.
    assert "canonical body" in stripped
    assert "trailing content" in stripped
    # Hash should be deterministic.
    h1 = hashlib.sha256(strip_ide_extras(text).encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(strip_ide_extras(text + "  ").encode("utf-8")).hexdigest()
    # Trailing whitespace difference still affects hash (no normalization).
    _ = h1, h2  # documentary; the equality is not asserted (deterministic w.r.t. input).
