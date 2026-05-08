---
name: ai-learn
description: Extracts lessons from merged PR review feedback by analyzing what reviewers caught, identifying missed checks, and writing entries directly to LESSONS.md. Trigger for 'the AI keeps doing X wrong', 'learn from this PR', 'what patterns did reviewers catch', 'update our standards from feedback'. Not for in-session observation; use /ai-instinct instead. Not for skill-level rewrites; use /ai-skill-evolve instead.
effort: medium
argument-hint: "single [pr]|batch"
mode: agent
tags: [meta, learning, continuous-improvement]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-learn/SKILL.md
edit_policy: generated-do-not-edit
---



# Learn

## Purpose

Continuous improvement from delivery outcomes. Analyzes merged PRs to find where AI missed what human reviewers caught, identifies false positives, and writes lessons directly to `.ai-engineering/LESSONS.md`. The feedback loop that makes the framework smarter over time.

## Trigger

- Command: `/ai-learn single <pr>|batch`
- Context: after PR merge (single), periodic review (batch).

Step 0: read `.ai-engineering/LESSONS.md` for pre-existing patterns; load contexts per `.ai-engineering/contexts/stack-context.md`.

## Workflow

Two modes: `single <pr>` (analyze one PR) and `batch` (analyze all merged PRs since last lesson update). Both follow the same loop:

1. Read PR review comments + code-change diff.
2. For each comment, classify the lesson category (Pattern Categories below).
3. Check for duplicates against existing LESSONS.md entries.
4. Append new lessons with category + evidence link.
5. When enough lessons accumulate per category, optionally draft an AGENTS.md proposal.

## Modes

### single <pr> -- Analyze one merged PR

1. **Fetch PR data** -- `gh pr view <pr> --json body,reviews,comments,files,additions,deletions`.
2. **Collect AI findings** -- read the AI-generated PR description, guard advisories, and verify results from the PR.
3. **Collect human feedback** -- extract all review comments, requested changes, and approval notes.
4. **Cross-reference** -- compare AI findings with human feedback:

   | Category | Description |
   |----------|-------------|
   | **AI miss** | Human reviewer found an issue AI did not flag |
   | **False positive** | AI flagged something human reviewer dismissed or overrode |
   | **AI hit** | AI flagged an issue human reviewer agreed with |
   | **Novel insight** | Human added context AI could not have known |

5. **Write lesson** -- for each actionable pattern found (AI miss, false positive, or novel insight), append a lesson entry to `.ai-engineering/LESSONS.md`:

   ```markdown
   ### [Pattern name derived from PR analysis]

   **Context**: [What happened in PR #NNN — the specific review feedback]
   **Learning**: [The pattern or rule extracted from the feedback]
   **Rule**: [Actionable instruction for future sessions]
   ```

   Only write lessons for patterns that are repeatable and actionable. Skip one-off issues specific to a single PR.

### batch -- Process unanalyzed merged PRs

1. **Read tracking marker** -- check `.ai-engineering/LESSONS.md` YAML frontmatter for `lastAnalyzedAt` field. If absent, this is the first batch run.
2. **Find unanalyzed PRs** -- `git log --merges --since=<lastAnalyzedAt> --format="%H %s"`. Extract PR numbers from merge commit messages. If `git log --merges` yields no results (e.g., squash-merge workflow), fall back to `gh pr list --state merged --json number,mergedAt` filtered by `lastAnalyzedAt`.
3. **Process each** -- run single-mode analysis for each unanalyzed PR.
4. **Update marker** -- set `lastAnalyzedAt: <current ISO date>` in LESSONS.md frontmatter (add frontmatter if absent).
5. **Summary** -- report total PRs analyzed, lessons written, and emerging patterns.

## Pattern Categories

| Pattern | Example | Action |
|---------|---------|--------|
| Missed check | AI never flags missing error handling in async code | Write lesson with Rule for future sessions |
| Over-flagging | AI flags every single-letter variable in list comprehensions | Write lesson noting the exception |
| Missing context | Reviewers always explain why a specific pattern is used in this codebase | Write lesson adding the context |
| Style drift | Reviewers consistently request a style AI does not enforce | Write lesson with the style rule |

## Quick Reference

```
/ai-learn single 123         # analyze PR #123, write lessons to LESSONS.md
/ai-learn batch               # process all unanalyzed merged PRs
```

## Storage

- All lessons written to: `.ai-engineering/LESSONS.md`
- Batch tracking: `lastAnalyzedAt` field in LESSONS.md YAML frontmatter
- Format: Markdown with Context/Learning/Rule sections (same as manually-written lessons)

## AGENTS.md proposal mode (spec-121)

Single-PR analysis writes to LESSONS.md. Procedural memory (AGENTS.md, CONSTITUTION.md) is the durable layer agents read on every session — when a category of lessons crosses threshold, it should be reinforced *there*, not buried in LESSONS.md.

After every batch run (or at the end of a single run), perform a category sweep:

1. Group all lessons in `.ai-engineering/LESSONS.md` by Pattern Category (Missed check / Over-flagging / Missing context / Style drift / custom).
2. For any category whose count is **≥ 5** AND that has **not** already been reflected in AGENTS.md (grep AGENTS.md for the category name or a representative phrase), draft a proposal block.
3. Append the proposal to `.ai-engineering/state/agents-proposals.md` (create if absent). **Never** edit AGENTS.md directly — same constraint as `/ai-dream` (D-118-04). Humans review and merge proposals manually via PR.

Proposal block format:

```markdown
## Proposal — <ISO date> — <Category name>

**Trigger**: <N> lessons in category "<Category>" since <oldest>; AGENTS.md does not yet codify this rule.

**Suggested AGENTS.md addition** (under section `## Hard rules` or appropriate):

> <single-sentence imperative rule derived from the lessons>

**Evidence** (lesson titles, PR refs):
- <lesson 1>
- <lesson 2>
- ...

**Action**: open a PR adding the rule above to AGENTS.md if accepted.
```

Emit a `framework_operation` event with `operation=agents_proposal_drafted`, `category=<name>`, `lesson_count=<N>` so the audit chain records each proposal cycle.

## Examples

### Example 1 — extract lessons from a single merged PR

User: "learn from PR #128"

```
/ai-learn single 128
```

Reads PR #128 review comments, classifies each into pattern categories, appends new entries to LESSONS.md, deduplicates against existing entries.

### Example 2 — batch analysis of recent merges

User: "synthesize lessons from everything merged this sprint"

```
/ai-learn batch
```

Walks merged PRs since last lesson update, applies the loop per PR, drafts AGENTS.md proposals when categories accumulate enough evidence.

## Integration

Called by: user directly, post-merge automation. Reads: `gh pr view`, `LESSONS.md`. Writes: `LESSONS.md` (append-only). See also: `/ai-note` (individual findings), `/ai-instinct` (in-session corrections), `/ai-skill-evolve` (acts on accumulated lessons).

$ARGUMENTS
