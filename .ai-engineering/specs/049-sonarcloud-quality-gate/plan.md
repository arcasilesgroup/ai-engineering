---
spec: "049"
approach: "standard"
agents: [build, scan]
phases: 3
---

# Plan — Fix SonarCloud Quality Gate + No-Suppression Rule

## Architecture Decision

Fix false positives by making code provably safe to the taint analyzer rather than suppressing findings. Add governance rule to prevent future suppression shortcuts.

## Phase 1: No-Suppression Governance Rule

Add explicit prohibition to all instruction files and core standards.

**Files**:
- `CLAUDE.md` — add rule 9 to Absolute Prohibitions
- `AGENTS.md` — add no-suppression behavioral rule
- `.ai-engineering/standards/framework/core.md` — add to Non-Negotiables
- Template mirrors: `src/ai_engineering/templates/project/CLAUDE.md`, `src/ai_engineering/templates/project/AGENTS.md`, `src/ai_engineering/templates/.ai-engineering/standards/framework/core.md`

**Agent**: `ai-build`

## Phase 2: Fix SonarCloud Vulnerabilities

Fix 5 vulnerabilities by adding path/argument validation.

| File | Line | Rule | Fix |
|------|------|------|-----|
| `src/ai_engineering/cli_commands/spec_cmd.py` | 123 | S2083 | `resolve().relative_to()` containment |
| `src/ai_engineering/policy/checks/commit_msg.py` | 54 | S2083 | `.git` parent validation |
| `src/ai_engineering/release/changelog.py` | 75 | S2083 | Filename + containment validation |
| `src/ai_engineering/platforms/sonarlint.py` | 493 | S2083 | Suffix + containment validation |
| `src/ai_engineering/vcs/azure_devops.py` | 419 | S6350 | Argument type validation |

**Agent**: `ai-build`

## Phase 3: Validation + PR

- Run full test suite
- Run ruff, ty
- Run `ai-eng validate .` for content integrity
- Create PR targeting main

**Agent**: `ai-release`

## User Action (post-merge)

Review 4 security hotspots in SonarCloud UI as "Safe":
https://sonarcloud.io/project/security_hotspots?id=arcasilesgroup_ai-engineering&branch=main

| File | Line | Justification |
|------|------|---------------|
| `lib/parsing.py` | 33 | No nested quantifiers, anchored, bounded character classes |
| `maintenance/branch_cleanup.py` | 177 | Flat repetition, bounded by delimiters, git output |
| `vcs/pr_description.py` | 264 | Simple anchored pattern, no backtracking |
| `work_items/service.py` | 145 | Same pattern, structured markdown input |
