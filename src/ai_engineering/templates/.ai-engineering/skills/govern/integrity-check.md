# Content Integrity

## Purpose

Validation skill that checks the integrity of all governance content in `.ai-engineering/`. Detects broken cross-references, mirror desync, counter mismatches, instruction file inconsistencies, and orphaned files. Designed to run after any governance content change and as a pre-merge gate.

## Trigger

- Command: agent invokes integrity-check skill after modifying governance content.
- Context: after creating, deleting, renaming, or moving any file in `.ai-engineering/`.
- Automatic: as part of verify-app agent behavior and session close actions.
- Pre-merge: before any PR that touches `.ai-engineering/` content.

## Procedure

### Category 1: File Existence

1. **Verify all referenced files exist** — scan all governance files for internal path references.
   - Parse all `.md` files in `.ai-engineering/` for paths matching `skills/`, `agents/`, `standards/`, `context/`.
   - For each referenced path, verify the file exists at `.ai-engineering/<path>`.
   - Report any references to non-existent files as BROKEN.

2. **Verify spec directory completeness** — for each spec directory in `context/specs/`:
   - Must contain at least: `spec.md`, `plan.md`, `tasks.md`.
   - Active spec (per `_active.md`) must NOT have `done.md` unless status is closed.
   - Completed specs should have `done.md`.

### Category 2: Mirror Sync

3. **Enumerate canonical/mirror pairs** — build the list of all files that must be mirrored.
   - Canonical root: `.ai-engineering/`
   - Mirror root: `src/ai_engineering/templates/.ai-engineering/`
   - Scope: `skills/**/*.md`, `agents/**/*.md`, `standards/framework/**/*.md`
   - Exclusions: `context/**`, `state/**`, `standards/team/**` (not mirrored).
   - Additional mirror pair: `.claude/commands/**` -> `src/ai_engineering/templates/project/.claude/commands/**` (slash command wrappers).

4. **Compare each pair** — verify byte-identical content.
   - Use file hash comparison (SHA-256).
   - Report any mismatches with both paths.
   - Report any canonical files missing their mirror.
   - Report any mirror files without a canonical source (orphaned mirrors).

### Category 3: Counter Accuracy

5. **Count skills in instruction files** — count the skill entries listed in `.github/copilot-instructions.md` under `## Skills`.
   - Count each `- \`.ai-engineering/skills/` line.
   - Verify count matches ALL 6 instruction files (must be identical).

6. **Count agents in instruction files** — count the agent entries listed under `## Agents`.
   - Count each `- \`.ai-engineering/agents/` line.
   - Verify count matches ALL 6 instruction files (must be identical).

7. **Verify product-contract counters** — compare instruction file counts against `product-contract.md`.
   - Active Objectives line must contain the correct skill and agent counts.
   - KPIs table `Agent coverage` row must match.
   - Report any mismatches.

### Category 4: Cross-Reference Integrity

8. **Verify skill references** — for each skill file, check that its `## References` section contains only valid paths.
   - Each referenced path must correspond to an existing file.
   - Referenced skills/agents must reciprocally reference this skill (bidirectional check).

9. **Verify agent references** — for each agent file, check `## Referenced Skills` and `## Referenced Standards`.
   - Each referenced skill must exist.
   - Each referenced standard must exist.
   - Referenced skills should reference the agent in their own `## References`.

### Category 5: Instruction File Consistency

10. **Verify all 6 instruction files are consistent** — compare skill and agent listings across all 6 files.
    - Extract the `## Skills` section from each file.
    - Extract the `## Agents` section from each file.
    - All 6 files must list identical skills and agents (same entries, same descriptions).
    - Report any file that differs from the others.

11. **Verify subsection structure** — each instruction file must have these subsections under `## Skills`:
    - `### Workflows` — workflow skills.
    - `### SWE Skills` — software engineering skills.
    - `### Lifecycle Skills` — framework lifecycle skills.
    - `### Quality Skills` — quality audit skills.
    - Report missing subsections.

### Category 6: Manifest Coherence

12. **Verify manifest.yml paths** — check that ownership model paths in `manifest.yml` match actual directory structure.
    - `framework_managed` globs must match existing directories.
    - `team_managed` globs must match existing directories.
    - `project_managed` globs must match existing directories.

13. **Verify _active.md consistency** — the active spec pointer must be valid.
    - The spec directory referenced in `_active.md` must exist.
    - The `spec.md` file must exist in that directory.
    - If `tasks.md` exists, frontmatter should be parseable.

## Output Contract

Structured report with 6 categories, each showing:

```
## Content Integrity Report

### Category 1: File Existence
- Status: PASS | FAIL
- Issues: [list of broken references]

### Category 2: Mirror Sync
- Status: PASS | FAIL
- Pairs checked: N
- Issues: [list of mismatches/orphans]

### Category 3: Counter Accuracy
- Status: PASS | FAIL
- Skills: N (instruction) vs M (product-contract)
- Agents: N (instruction) vs M (product-contract)

### Category 4: Cross-Reference Integrity
- Status: PASS | FAIL
- Issues: [list of broken/missing refs]

### Category 5: Instruction File Consistency
- Status: PASS | FAIL
- Issues: [list of inconsistencies]

### Category 6: Manifest Coherence
- Status: PASS | FAIL
- Issues: [list of mismatches]

### Overall: PASS | FAIL (N/6 categories passed)
```

## Governance Notes

- Content integrity validation is a governance requirement — it must run after any `.ai-engineering/` content change.
- This skill is the "test suite" for governance content — equivalent to unit tests for code.
- Results are informational, not blocking (content-first principle, D4/D7 from spec-003).
- Agents should self-invoke this skill at session close when governance content was modified.
- The verify-app agent includes content integrity as a behavior step.
- All 6 categories must PASS for a governance change to be considered complete.

## References

- `skills/govern/create-skill.md` — skill registration procedure (validates creation correctness).
- `skills/govern/create-agent.md` — agent registration procedure (validates creation correctness).
- `skills/govern/delete-skill.md` — skill removal procedure (validates deletion completeness).
- `skills/govern/delete-agent.md` — agent removal procedure (validates deletion completeness).
- `skills/govern/create-spec.md` — spec creation procedure (validates spec structure).
- `agents/verify-app.md` — agent that includes content integrity in verification.
- `standards/framework/core.md` — content integrity enforcement rules.
- `context/product/framework-contract.md` — template packaging and replication rule.
