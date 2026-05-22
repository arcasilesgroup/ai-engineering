"""Release authority drift tests for the governed release spine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# spec-152 W2.T13 hard-deleted ``.github/workflows/ci-build.yml``. The CI
# build now lives in ``ci-check.yml`` (the ``build-check`` job, ``uv build``
# only). Surfaces retargeted to ``ci-check.yml`` so the single-release-
# authority guarantee still covers a CI workflow, not a vanished file.
ACTIVE_RELEASE_SURFACES = (
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path(".github/workflows/ci-check.yml"),
    Path(".github/workflows/release.yml"),
    Path(".ai-engineering/reference/cli-reference.md"),
    Path("src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md"),
)

SEMANTIC_RELEASE_PATTERNS = (
    re.compile(r"python-semantic-release"),
    re.compile(r"\bsemantic-release\b"),
    re.compile(r"\bsemantic_release\b"),
    re.compile(r"\[tool\.semantic_release"),
)

# Writer signals that denote a CI workflow mutating release/version state and
# pushing it back. ``refs/heads/main`` (a read-only ``if: github.ref ==`` branch
# guard, used by the benign Snyk-monitor step in ci-check.yml) is intentionally
# excluded — it is a run condition, not a commit-back writer. The remaining
# patterns are the spec-100 commit-back writer fingerprint that the deleted
# ci-build.yml carried; the surviving build job must never reintroduce them.
CI_COMMIT_BACK_PATTERNS = (
    re.compile(r"Commit version bump back"),
    re.compile(r"chore\(release\): bump version"),
    re.compile(r"\bforce=true\b"),
    re.compile(r"src/ai_engineering/version/registry\.json"),
)


@dataclass(frozen=True)
class DriftFinding:
    path: Path
    line_number: int
    pattern: str
    line: str

    def render(self) -> str:
        location = f"{self.path}:{self.line_number}"
        return f"{location}: {self.pattern!r} in {self.line.strip()!r}"


def _find_matches(
    paths: tuple[Path, ...],
    patterns: tuple[re.Pattern[str], ...],
) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    for path in paths:
        text = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            findings.extend(
                DriftFinding(path, line_number, pattern.pattern, line)
                for pattern in patterns
                if pattern.search(line)
            )
    return findings


def test_active_release_surfaces_do_not_reference_semantic_release() -> None:
    """The governed release path must have one release authority."""
    findings = _find_matches(ACTIVE_RELEASE_SURFACES, SEMANTIC_RELEASE_PATTERNS)

    assert findings == [], "semantic-release drift found:\n" + "\n".join(
        finding.render() for finding in findings
    )


def test_ci_build_workflow_does_not_commit_release_state_back_to_main() -> None:
    """CI package builds must not mutate version state or write release commits.

    spec-152 W2.T13 deleted ``ci-build.yml``; the CI build moved to the
    ``build-check`` job in ``ci-check.yml`` (``uv build`` only, under a
    top-level ``permissions: contents: read``). The guarantee is unchanged:
    the surviving CI build path must not carry the spec-100 commit-back
    writer fingerprint.
    """
    findings = _find_matches(
        (Path(".github/workflows/ci-check.yml"),),
        CI_COMMIT_BACK_PATTERNS,
    )

    assert findings == [], "CI build release commit-back writer found:\n" + "\n".join(
        finding.render() for finding in findings
    )
