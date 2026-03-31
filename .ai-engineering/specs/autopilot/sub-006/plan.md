---
total: 6
completed: 0
---

# Plan: sub-006 Cleanup & Decision Persistence

```
exports: []
imports: [all sub-specs completed]
```

## Plan

### T-6.1: Delete deprecated ci.yml

Pre-check: verify `release.yml` does NOT reference `ci.yml` (sub-005 should have updated this). Verify `ci-check.yml` and `ci-build.yml` exist and are functional. Then delete `.github/workflows/ci.yml`.

**Files**: `.github/workflows/ci.yml` (DELETE)
**Done**: `ci.yml` does not exist. `ci-check.yml` and `ci-build.yml` are the active workflows. No workflow references `ci.yml`.

---

### T-6.2: Update README.md CI badge

Change CI badge URL from `actions/workflows/ci.yml/badge.svg` to `actions/workflows/ci-check.yml/badge.svg` on README.md line 16.

**Files**: `README.md`
**Done**: Badge URL points to `ci-check.yml`. Badge renders correctly on GitHub.

---

### T-6.3: Remove legacy commit format from commit_msg.py

If sub-003 added dual-format acceptance (conventional + legacy `spec-NNN:`), remove the `_LEGACY_SPEC_RE` pattern and its acceptance branch. Keep only conventional commit format validation.

**Files**: `src/ai_engineering/policy/checks/commit_msg.py`
**Done**: `validate_commit_message("spec-097: old format")` returns a warning/error. `validate_commit_message("feat(spec-097): new format")` returns `[]`. No `_LEGACY_SPEC_RE` in the file.

---

### T-6.4: Add decisions D-097-01 through D-097-12 to decision-store.json

Read current last DEC ID from `decision-store.json` (currently DEC-028). Add 12 new entries (DEC-029 through DEC-040) following the mapping from sub-006 spec.md. Mark DEC-012 (`superseded_by: "DEC-032"`) and DEC-015 (`superseded_by: "DEC-031"`) as superseded. Each new entry follows the v1.1 schema with `created_at: "2026-03-31"`, `expires_at: "2027-03-31T00:00:00Z"`, `source: "spec-097"`.

**Files**: `.ai-engineering/state/decision-store.json`
**Done**: 12 new entries (DEC-029 to DEC-040) present. DEC-012 status is `superseded` with `superseded_by: "DEC-032"`. DEC-015 status is `superseded` with `superseded_by: "DEC-031"`. JSON is valid. Total decisions: 40.

---

### T-6.5: Update CHANGELOG.md with spec-097 changes

Add a comprehensive entry under `## [Unreleased]` summarizing all 6 phases of spec-097. Use `### Changed` for the CI/CD redesign and `### Added` for new supply chain security features.

**Files**: `CHANGELOG.md`
**Done**: `## [Unreleased]` contains spec-097 entry covering: workflow split, conventional commits, semantic-release, SLSA attestations, SBOM, checksums, artifact-driven releases, GitHub hardening.

---

### T-6.6: Final verification suite

Run the complete verification suite to confirm everything works:
1. `uv run pytest` — all tests pass
2. `uv run ruff check` — no lint errors
3. `uv run ty check src/` — no type errors
4. `uv run python scripts/check_workflow_policy.py` — all workflows pass policy
5. `gitleaks protect --staged` — no secrets

**Files**: (none — verification only)
**Done**: All 5 verification commands exit with code 0. Zero failures across the board.

## Confidence

- **Level**: high
- **Assumptions**: All prior sub-specs (001-005) completed successfully. Decision numbering starts at DEC-029 (no other spec added decisions between now and execution).
- **Unknowns**: Exact state of commit_msg.py after sub-003 — may be a no-op if sub-003 didn't add legacy format acceptance.

## Self-Report
[EMPTY -- populated by Phase 4]
