# Docs Audit

## Purpose

Audits all governance documentation for location correctness, writing quality, structural consistency, signal-to-noise ratio, and stale content. Covers Markdown, YAML, and JSON files across `.ai-engineering/`, instruction files, and spec/backlog artifacts. Produces a health score with specific rewrite recommendations and compaction opportunities.

## Trigger

- Command: agent invokes docs-audit skill or user requests documentation review.
- Context: weekly maintenance cycle, pre-release documentation review, governance audit, content compaction pass.

## Procedure

### Phase 1: Inventory

1. **Enumerate all documentation** — build a complete inventory of governance docs.
   - `.ai-engineering/**/*.md` — all governance Markdown files.
   - `.ai-engineering/**/*.yml` / `*.yaml` — configuration files.
   - `.ai-engineering/**/*.json` — state and config files.
   - Root instruction files: `CLAUDE.md`, `AGENTS.md`, `codex.md`, `.github/copilot-instructions.md`.
   - Record file path, size, last modified date, ownership level.

2. **Classify by ownership** — tag each file with its ownership level.
   - Framework-managed, team-managed, project-managed, system-managed.
   - Flag any files outside the ownership model.

### Phase 2: Location Correctness

3. **Verify file placement** — confirm each file is in the correct directory per ownership rules.
   - Skills in `skills/<category>/`.
   - Agents in `agents/`.
   - Standards in `standards/framework/` or `standards/team/`.
   - Context in `context/`.
   - State in `state/`.
   - Report misplaced files with recommended location.

4. **Verify naming conventions** — check kebab-case, correct extensions, no orphan files.
   - All `.md` files use kebab-case naming.
   - No files with spaces or special characters.
   - No empty files (except intentional placeholders).

### Phase 3: Writing Quality

5. **Assess clarity** — evaluate each document for clarity and precision.
   - Purpose section present and concise (1-3 sentences).
   - Procedure steps are actionable (verb-first imperatives).
   - No vague language ("might", "possibly", "various").
   - Technical terms used consistently.

6. **Assess actionability** — verify documents drive behavior, not just describe.
   - Skills: every step produces a verifiable output.
   - Agents: behavior steps are sequentially executable.
   - Standards: rules are testable (can determine PASS/FAIL).

7. **Detect stale content** — identify outdated references and obsolete information.
   - References to deleted files or renamed artifacts.
   - Version numbers that don't match current release.
   - Dates older than 90 days without recent validation.
   - Spec references to completed/archived specs without context.

### Phase 4: Structural Consistency

8. **Verify template compliance** — check that skills and agents follow their templates.
   - Skills: Purpose, Trigger, Procedure, Output Contract, Governance Notes, References.
   - Agents: Identity, Capabilities, Activation, Behavior, Referenced Skills, Referenced Standards, Output Contract, Boundaries.
   - Report missing or incorrectly named sections.

9. **Audit spec/backlog structure** — verify delivery artifact organization.
   - Each spec directory: `spec.md`, `plan.md`, `tasks.md` (minimum).
   - Completed specs: `done.md` present.
   - `_active.md` pointer valid and current.
   - Tasks files: frontmatter parseable, checkboxes present.

### Phase 5: Signal-to-Noise

10. **Measure content efficiency** — assess signal-to-noise ratio.
    - Detect duplicate content across files (same paragraph in multiple locations).
    - Identify verbose sections that could be compressed without information loss.
    - Flag boilerplate that adds no governance value.
    - Calculate approximate signal-to-noise ratio per category.

11. **Identify compaction opportunities** — recommend specific consolidations.
    - Files that could be merged (overlapping purpose).
    - Sections that could be shortened (verbose explanations of simple concepts).
    - Cross-references that could replace duplicated content.

### Phase 6: Report

12. **Produce documentation health report** — structured findings with scores.
    - Per-category scores (location, quality, structure, efficiency).
    - Specific findings with file paths and line references.
    - Before/after recommendations for top-priority rewrites.
    - Overall health score.

## Output Contract

```
## Documentation Health Report

### Summary
- Files audited: N
- Health score: N/100
- Critical findings: N
- Compaction opportunities: N

### Location Correctness
- Status: PASS | FAIL
- Misplaced files: [list]

### Writing Quality
- Score: N/100
- Clarity issues: [list with file:line references]
- Stale content: [list]

### Structural Consistency
- Status: PASS | FAIL
- Template violations: [list]
- Spec structure issues: [list]

### Content Efficiency
- Signal-to-noise: HIGH | MEDIUM | LOW
- Duplications: [list of duplicate content pairs]
- Compaction targets: [list with estimated reduction %]

### Top Recommendations
1. [Highest-priority rewrite with before/after]
2. [Second priority]
3. [Third priority]
```

## Governance Notes

- Documentation quality directly impacts AI agent effectiveness — low-quality docs produce low-quality behavior.
- This skill covers the documentation audit gap not addressed by `integrity-check` (which validates structure, not quality).
- Run as part of the weekly maintenance cycle for ongoing content health.
- Compaction recommendations require human approval before execution.
- Spec/backlog structure validation ensures delivery lifecycle artifacts are navigable.

## References

- `skills/govern/integrity-check.md` — structural validation (complementary).
- `skills/docs/writer.md` — documentation generation standards.
- `skills/docs/explain.md` — clarity standards for explanations.
- `skills/govern/create-skill.md` — skill template structure.
- `skills/govern/create-agent.md` — agent template structure.
- `skills/quality/release-gate.md` — release readiness (documentation is a gate dimension).
- `agents/platform-auditor.md` — orchestrator that invokes this skill.
- `standards/framework/core.md` — ownership model and content rules.
