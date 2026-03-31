---
id: sub-006
parent: spec-097
title: "Cleanup & Decision Persistence"
status: planning
files: [".github/workflows/ci.yml", "src/ai_engineering/policy/checks/commit_msg.py", ".ai-engineering/state/decision-store.json", "CHANGELOG.md", "README.md", ".github/workflows/release.yml"]
depends_on: ["sub-001", "sub-002", "sub-003", "sub-004", "sub-005"]
---

# Sub-Spec 006: Cleanup & Decision Persistence

## Scope

Delete deprecated `ci.yml`. Remove legacy `spec-NNN:` format acceptance from `commit_msg.py` (keep only conventional commits). Add decisions D-097-01 through D-097-12 to `decision-store.json`, marking DEC-012 and DEC-015 as superseded. Update CHANGELOG.md with spec-097 changes. Final verification: full test suite, lint, typecheck, policy check, secret scan. Covers spec-097 Phase 6.

## Exploration

### Existing Files

**`.github/workflows/ci.yml`** (759 lines) -- The monolith to delete. Contains 16 jobs: change-scope, lint, duplication, risk-acceptance, typecheck, test-unit (3x3 matrix), test-integration (3x1 matrix), test-e2e, sonarcloud, framework-smoke (3 OS), workflow-sanity, verify-gate-trailers, snyk-security, security, content-integrity, build, ci-result. By the time sub-006 executes, sub-002 will have created `ci-check.yml` and `ci-build.yml` as replacements, and this file will already be marked deprecated. Self-references internally at line 65 (paths-filter references `.github/workflows/ci.yml`).

**External references to `ci.yml` that must be updated:**
- `README.md` line 16: CI badge URL `actions/workflows/ci.yml/badge.svg` -- must update to `ci-check.yml`
- `.github/workflows/release.yml` line 37: `--workflow=ci.yml` in `gh run list` -- sub-005 (release redesign) should have already updated this; verify before sub-006 acts
- `CHANGELOG.md`: historical references (lines 123, 208, 324, 546) -- these are factual history, do NOT modify
- `.ai-engineering/specs/` files: spec references are documentation, not runtime -- do NOT modify
- `.codex/skills/ai-pipeline/handlers/generate.md` (and 3 other IDE mirrors): generic pipeline generation docs referencing `ci.yml` as example output name for customer projects -- this is NOT about this repo's own CI; these reference what the `/ai-pipeline` skill generates for user projects. Do NOT modify.

**`src/ai_engineering/policy/checks/commit_msg.py`** (57 lines) -- Current validation is already minimal: checks for empty message, empty first line, and 72-char first-line limit. There is NO legacy `spec-NNN:` format acceptance code present. The function `validate_commit_message()` does not check format prefixes at all. The spec says to "remove legacy spec-NNN: format acceptance" but this was either already removed by a prior sub-spec (sub-003 adding conventional commit validation) or was never in this file. If sub-003 added conventional commit validation with a transitional dual-format acceptance, then sub-006 removes the `spec-NNN:` branch. If sub-003 simply replaced the entire validator, sub-006's task is a no-op for this file. The implementation agent must check the state of this file AFTER sub-003 completes.

**`.ai-engineering/state/decision-store.json`** (491 lines) -- Contains 28 decisions (DEC-001 through DEC-028). Schema version 1.1. Each entry has: `id`, `title`, `description` (optional), `category`, `status`, `criticality`, `source`, `spec`, `created_at`, `expires_at`, `context_hash`, `acknowledged_by`, `decision`, `decidedAt`, `context`. Superseded entries have `superseded_by` field; superseding entries have `supersedes` field. Last ID is DEC-028. New entries will be DEC-029 through DEC-040 (12 decisions).

**DEC-012** (line 199-214) -- "Release zero-rebuild -- download CI artifacts". Status: `active`. To be marked `superseded` with `superseded_by: "DEC-032"` (D-097-04).

**DEC-015** (line 250-265) -- "Conventional commits with spec-NNN prefix". Status: `active`. To be marked `superseded` with `superseded_by: "DEC-031"` (D-097-03).

**`CHANGELOG.md`** -- Uses Keep a Changelog format with `## [Unreleased]` at top, then `### Added`, `### Changed`, `### Removed`, `### Fixed` subsections. Each entry is a bold title with spec reference followed by description. The spec-097 entry needs to summarize all 6 phases. Current `## [Unreleased]` already has entries from spec-095 and spec-096.

**`README.md`** -- Line 16 has CI badge pointing to `ci.yml`. Must update to `ci-check.yml` after deletion.

### Patterns to Follow

**Decision entry template** (from DEC-028, the most recent):
```json
{
  "id": "DEC-029",
  "title": "Short title",
  "category": "architecture|governance|delivery|tooling|security",
  "status": "active",
  "criticality": "high|medium|low",
  "source": "spec-097",
  "spec": "097",
  "created_at": "2026-03-31",
  "expires_at": "2027-03-31T00:00:00Z",
  "context_hash": "",
  "acknowledged_by": "plan",
  "decision": "Full decision text.",
  "decidedAt": "2026-03-31T00:00:00Z",
  "context": "same as category"
}
```

**Supersession pattern** (from DEC-002 -> DEC-019):
- On the OLD entry: add `"superseded_by": "DEC-NNN"`, change `"status": "superseded"`
- On the NEW entry: add `"supersedes": "DEC-NNN"`

**Decision ID mapping** (D-097-XX -> DEC-NNN):
| Spec Decision | DEC ID | Title |
|---|---|---|
| D-097-01 | DEC-029 | Workflow decomposition -- 6 independent YAML files |
| D-097-02 | DEC-030 | ci-build triggers via workflow_run on ci-check success |
| D-097-03 | DEC-031 | Conventional commits replace spec-NNN prefix (supersedes DEC-015) |
| D-097-04 | DEC-032 | Artifact-driven releases with workflow_dispatch (supersedes DEC-012) |
| D-097-05 | DEC-033 | SLSA Build attestations generated in the build job |
| D-097-06 | DEC-034 | Semantic-release only generates artifacts on version bump |
| D-097-07 | DEC-035 | 90-day artifact retention + permanent GitHub Releases |
| D-097-08 | DEC-036 | GitHub hardening -- required reviews, tag protection, environment restrictions |
| D-097-09 | DEC-037 | Dry build in ci-check for PR compilation validation |
| D-097-10 | DEC-038 | CHANGELOG validation in release workflow only |
| D-097-11 | DEC-039 | install-smoke.yml remains separate from ci-check |
| D-097-12 | DEC-040 | Single version source -- eliminate __version__.py |

### Dependencies Map

Sub-006 depends on ALL other sub-specs completing first:
- **sub-001** (GitHub Hardening): must complete so D-097-08 can reference actual applied settings
- **sub-002** (Workflow Split): must create `ci-check.yml` and `ci-build.yml` before `ci.yml` is safe to delete
- **sub-003** (Semantic Release): must complete so commit format transition is done and legacy format removal is safe
- **sub-004** (Supply Chain Security): must complete so D-097-05 references actual attestation implementation
- **sub-005** (Release Redesign): must complete so `release.yml` no longer references `ci.yml`

### Risks

1. **Deleting ci.yml while release.yml still references it** -- `release.yml` line 37 uses `--workflow=ci.yml` to find CI runs. Sub-005 should update this to the new workflow name, but if it did not, deleting ci.yml breaks the release workflow. The implementation agent MUST verify release.yml no longer references ci.yml before deletion.

2. **README badge URL becomes broken** -- The CI badge in README.md points to `ci.yml`. After deletion, the badge shows "not found". Must update to `ci-check.yml` in the same commit.

3. **Decision numbering conflicts** -- If another spec adds decisions between now and sub-006 execution, DEC-029+ could conflict. The implementation agent must read the current last DEC ID at execution time and number from there, NOT blindly use DEC-029.

4. **commit_msg.py state uncertainty** -- The current file has no legacy format code. Sub-003 may or may not have added transitional dual-format code that sub-006 needs to remove. The implementation agent must inspect the file state after sub-003 completes.

5. **Verification suite failures from prior sub-specs** -- Sub-006 runs final verification. If prior sub-specs introduced issues that were not caught, sub-006's verification will fail. This is not a sub-006 bug but a pipeline issue. Escalate if tests fail for reasons unrelated to sub-006 changes.

6. **Pipeline handler references to ci.yml are generic examples** -- The `/ai-pipeline` skill handlers in `.codex/`, `.claude/`, `.gemini/`, `.github/` reference `ci.yml` as a generic output filename for customer projects. These are NOT references to this repo's own CI and must NOT be modified.
