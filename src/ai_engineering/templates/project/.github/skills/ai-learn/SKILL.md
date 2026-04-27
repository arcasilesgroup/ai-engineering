---
name: ai-learn
description: Use when the AI keeps repeating the same mistakes, when you want the framework to learn from merged PR review feedback, or when enough corrections have accumulated to update standards. Trigger for 'the AI keeps doing X wrong', 'learn from this PR', 'what patterns did reviewers catch', 'update our standards from feedback'. Analyzes PRs, identifies missed checks, and writes lessons directly to LESSONS.md.
effort: medium
argument-hint: "single <pr>|batch"
mode: agent
tags: [meta, learning, continuous-improvement]
---



# Learn

## Purpose

Continuous improvement from delivery outcomes. Analyzes merged PRs to find where AI missed what human reviewers caught, identifies false positives, and writes lessons directly to `.ai-engineering/LESSONS.md`. The feedback loop that makes the framework smarter over time.

## Trigger

- Command: `/ai-learn single <pr>|batch`
- Context: after PR merge (single), periodic review (batch).

Step 0: read `.ai-engineering/LESSONS.md` for pre-existing patterns; load contexts per `.ai-engineering/contexts/stack-context.md`.

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

## Integration

- **See also**: `/ai-note` (save individual findings before synthesizing)
- **Correction capture is owned by `/ai-instinct`** -- when the AI makes repeated mistakes, run `/ai-instinct --review` to consolidate observations into the instinct store and generate improvement proposals.

$ARGUMENTS
