# Autopilot Manifest: spec-097

## Split Strategy
By-layer: separated by infrastructure layer (GitHub settings, workflow architecture, version management, supply chain, release pipeline) with a final cleanup sub-spec that depends on all others.

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001 | GitHub Repository Hardening | planned | None | (no files — `gh api` only) |
| sub-002 | Workflow Architecture Split | planned | None | `ci.yml`, `ci-check.yml`, `ci-build.yml`, `release.yml`, `check_workflow_policy.py` |
| sub-003 | Version & Commit Modernization | planned | sub-002 | `pyproject.toml`, `__version__.py`, `__init__.py`, `commit_msg.py`, `version_bump.py`, `orchestrator.py`, `pr_description.py`, `ai-commit/SKILL.md`, `ai-pr/SKILL.md`, `ci-build.yml` |
| sub-004 | Supply Chain Security | planned | sub-002, sub-003 | `ci-build.yml` |
| sub-005 | Artifact-Driven Release Pipeline | planned | sub-003, sub-004 | `release.yml`, `CHANGELOG.md` |
| sub-006 | Cleanup & Decision Persistence | planned | sub-001, sub-002, sub-003, sub-004, sub-005 | `ci.yml`, `commit_msg.py`, `decision-store.json`, `CHANGELOG.md`, `README.md` |

## Coverage Traceability

| Spec Section | Sub-Spec(s) |
|-------------|-------------|
| D-097-01 (workflow decomposition) | sub-002 |
| D-097-02 (workflow_run trigger) | sub-002 |
| D-097-03 (conventional commits) | sub-003 |
| D-097-04 (artifact-driven releases) | sub-005 |
| D-097-05 (SLSA attestations) | sub-004 |
| D-097-06 (no-bump silence) | sub-003 |
| D-097-07 (90-day retention) | sub-002, sub-005 |
| D-097-08 (GitHub hardening) | sub-001 |
| D-097-09 (dry build) | sub-002 |
| D-097-10 (CHANGELOG validation) | sub-005 |
| D-097-11 (install-smoke separate) | sub-002 |
| D-097-12 (single version source) | sub-003 |
| Phase 6 cleanup | sub-006 |

## Deep Plan Summary
- Planned: 6 of 6 sub-specs
- Failed: 0 sub-specs
- Confidence distribution: 5 high, 1 high (sub-006 written by orchestrator after agent rate limit)

## Execution DAG

```
Wave 1 (parallel):              sub-001 (GitHub settings) || sub-002 (workflow split)
Wave 2 (serial, after Wave 1):  sub-003 (version + commits)
Wave 3 (serial, after Wave 2):  sub-004 (supply chain)
Wave 4 (serial, after Wave 3):  sub-005 (release pipeline)
Wave 5 (serial, after Wave 4):  sub-006 (cleanup)
```

### Dependency Edges
- sub-002 → sub-003 (imports: ci-build.yml)
- sub-002 → sub-004 (imports: ci-build.yml; file overlap: ci-build.yml, check_workflow_policy.py)
- sub-003 → sub-004 (imports: semantic-release tag/outputs; file overlap: ci-build.yml)
- sub-003 → sub-005 (imports: draft GitHub Releases; file overlap: via ci-build.yml chain)
- sub-004 → sub-005 (imports: SBOM/checksums; file overlap: check_workflow_policy.py)
- sub-005 → sub-006 (imports: release.yml complete; file overlap: CHANGELOG.md, release.yml)
- sub-003 → sub-006 (file overlap: commit_msg.py)
- sub-002 → sub-006 (file overlap: ci.yml)
- sub-001 → sub-006 (dependency: decision persistence)

### DAG Validation
- Acyclicity: PASSED (no cycles)
- Coverage: PASSED (all 6 sub-specs assigned to waves)
- Merges: 0 (no unresolvable file conflicts — all overlaps are sequential in the DAG)

### Key Change from Phase 1 DAG
Phase 1 estimated sub-003 and sub-004 could run in parallel (Wave 2). Deep planning revealed sub-004 depends on sub-003's semantic-release outputs AND both modify ci-build.yml. They must be sequential: sub-003 (Wave 2) → sub-004 (Wave 3). This increases total waves from 4 to 5.

## Totals
- Sub-specs: 6
- Tasks: 46 (6 + 9 + 12 + 6 + 7 + 6)
- Dependency chain depth: 5 waves
- File overlaps: 8 pairs
- Import chains: 9 edges
