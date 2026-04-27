---
name: learn
description: Use to absorb history into LESSONS.md — analyze merged PRs and reviewer feedback, distill recurring patterns, and feed CLEAR-framework metrics. Different from /ai-note (single-shot user-driven); /ai-learn aggregates across PR history. Trigger for "learn from past PRs", "what patterns are reviewers flagging", "update lessons", "feed the instinct loop".
effort: max
tier: core
capabilities: [tool_use, structured_output]
---

# /ai-learn

Pattern aggregation across history. Reads merged PRs via `gh`, extracts
reviewer feedback, classifies it (style / correctness / architecture /
security / testing), distills recurring patterns into `LESSONS.md`, and
feeds CLEAR-framework metrics per ADR-0009.

> **Different from `/ai-note`** — `note` is single-shot, user-driven
> ("save this insight"). `learn` is bulk, observation-driven (mine the
> archive for patterns). Absorbs the legacy `instinct` skill.

## When to use

- Quarterly retrospective — "what are reviewers consistently flagging"
- After a wave of PR feedback — extract patterns before they fade
- New skill / agent onboarding — seed its `LESSONS.md` from history
- CLEAR-framework regression investigation — surface efficacy drift
- Pre-release polish — close known instinct gaps

## Process

1. **Scope window** — default last 90 days; `--since <date>` to widen.
2. **Pull merged PRs via `gh pr list --state merged --json …`** with
   review comments and inline comments.
3. **Classify each comment** — categories:
   - `style` — formatting, naming, idioms
   - `correctness` — logic bugs, missing edge cases
   - `architecture` — layer violations, port misuse
   - `security` — injection, secrets, OWASP findings
   - `testing` — coverage gaps, brittle mocks, RED missing
   - `process` — missing spec link, conventional-commit drift
4. **Cluster by pattern** — group comments that say the same thing in
   different words (LLM-judged similarity).
5. **Extract rule** — for each cluster, write a `LESSON: when X, do Y`
   line and a short rationale.
6. **Append to `.ai-engineering/LESSONS.md`** under the right category.
   Dedupe against existing lines.
7. **Emit CLEAR telemetry** — `learn.lesson_added` with category and
   reviewer count. Feeds Efficacy / Assurance dimensions.
8. **Surface the top 5** — present the most impactful new lessons
   to the user before persisting.

## Output format (LESSONS.md entry)

```
## <category>
- LESSON: <one-line rule>
  Source: 4 PR comments (#1284, #1305, #1311, #1340)
  Added: 2026-04-27
```

Entries are append-only. Older lessons are not deleted; superseded
lessons are marked `superseded-by: <new-lesson-id>`.

## Hard rules

- NEVER fabricate reviewer feedback — every cluster must cite real PR
  comment URLs.
- NEVER strip identifying detail to "anonymize"; PR refs are public.
- NEVER overwrite `LESSONS.md` — append-only, supersede-don't-delete.
- LESSONS entries must be actionable; "be careful with locks" is not a
  lesson, "always acquire locks in alphabetical order" is.
- Telemetry events must be emitted for every appended lesson.

## Common mistakes

- Mistaking volume for signal — 3 reviewers with the same gripe matters
  more than 1 reviewer with 50 nits
- Re-discovering existing lessons (always dedupe before appending)
- Skipping CLEAR emission — `/ai-eval` later misses the trend
- Categorizing "process" comments as "style" — different remediation
- Treating lessons as opinions rather than rules — write imperatives
- Forgetting the source URLs — future readers cannot audit
