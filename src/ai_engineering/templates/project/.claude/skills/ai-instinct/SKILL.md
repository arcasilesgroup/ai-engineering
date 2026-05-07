---
name: ai-instinct
description: "Activate at session start to silently observe corrections, recoveries, and workflow patterns. Run with --review before commits or PRs to consolidate observations into project instincts. Trigger for 'start observing', 'learn from this session', 'consolidate instincts', 'review what you learned', 'instinct review'. Listening mode is passive -- review mode extracts, enriches, and writes."
effort: medium
argument-hint: "[--review]"
tags: [meta, learning, continuous-improvement]
---

# ai-instinct

Project-local instinct learning for `ai-engineering`. Two modes: passive observation during a session, and active consolidation on demand. No daemons, no background workers -- the LLM itself is the observer.

## Artifact Set

| Artifact                                             | Purpose                                                         |
| ---------------------------------------------------- | --------------------------------------------------------------- |
| `.ai-engineering/state/instinct-observations.ndjson` | Append-only observation stream from hooks. Retain last 30 days. |
| `.ai-engineering/instincts/instincts.yml`            | Canonical project-local instinct store (v2 schema).             |
| `.ai-engineering/instincts/meta.json`                | Checkpoints and thresholds for consolidation.                   |
| `.ai-engineering/instincts/proposals.md`             | Actionable proposals generated when thresholds are met.         |

## Supported Families (v2)

The canonical store supports only these sections:

- `corrections` -- user corrections to AI behavior (LLM-extracted during --review)
- `recoveries` -- error recovery patterns (hook-detected + LLM-enriched)
- `workflows` -- skill invocation sequences (hook-detected + LLM-enriched)

Anything outside those families is out of scope.

## Commands

### `/ai-instinct` (listening mode)

Enter passive observation mode for the session. Output ONLY this single line, then go silent:

> instinct is observing the session...

Do nothing else. Do not read files. Do not produce analysis. The LLM passively observes corrections, error recoveries, and workflow patterns as the session continues. Observations are consolidated only when `--review` is invoked.

### `/ai-instinct --review` (consolidation)

5-step consolidation (extract → enrich → write → evaluate → create work items). Run this before `/ai-commit` or `/ai-pr` to capture learnings.

#### Step 1: EXTRACT

Review the current conversation for:

- **Corrections**: moments where the user corrected AI behavior, rejected an approach, or redirected a decision.
- **Recoveries**: errors encountered and how they were resolved.
- **Workflows**: skill invocation sequences and tool usage patterns.

For each observation, identify:

- `relatedSkill` -- which skill was active (e.g., `ai-code`, `ai-test`)
- `diagnostic` -- the error message or correction signal
- `skillIssue` -- what the skill got wrong or could improve

#### Step 2: ENRICH

1. Read `.ai-engineering/state/instinct-observations.ndjson` for hook-detected recoveries.
2. Read `.ai-engineering/state/framework-events.ndjson` for `skill_invoked` events to detect workflow patterns.
3. For each extracted observation, add semantic fields:
   - `trigger` -- what condition causes this pattern (e.g., "user says 'no, do X instead'")
   - `action` -- what the AI should do differently (e.g., "prefer X over Y in this context")

#### Step 3: WRITE

Upsert entries into `.ai-engineering/instincts/instincts.yml` using the v2 schema. Each family entry shares: `pattern`, `trigger`, `action`, `relatedSkill`, `confidence` (0.0-1.0), `evidenceCount`, `domain` (project|stack|team), `lastSeen` (ISO 8601). `corrections` and `recoveries` add `diagnostic` + `skillIssue`.

```yaml
schemaVersion: "2.0"
corrections:
  - pattern: "<description>"
    trigger: "<what triggers this>"
    action: "<what to do>"
    relatedSkill: "<skill-name>"
    diagnostic: "<error or correction signal>"
    skillIssue: "<what the skill got wrong>"
    confidence: 0.7
    evidenceCount: 3
    domain: "project"
    lastSeen: "2026-04-27T00:00:00Z"
recoveries:
  - pattern: "<description>"
    # ...same fields; trigger/action/diagnostic describe error pattern + recovery steps + error message
workflows:
  - pattern: "<description>"
    # ...same fields except diagnostic/skillIssue; trigger/action describe the sequence
```

Merge rules:

- If an existing entry matches the same pattern (fuzzy match on trigger + action), increment `evidenceCount` and update `lastSeen`. Match if the trigger and action describe the same behavioral pattern using different wording. When in doubt, increment the existing entry rather than creating a duplicate.
- Apply confidence scoring: `confidence_for_count(evidenceCount)` yields 0.3/0.5/0.7/0.85 at thresholds 1/2/3/5+.
- Drop entries with confidence below 0.2 (decay threshold).
- Update `.ai-engineering/instincts/meta.json` with new checkpoint.

#### Step 4: EVALUATE

Cross-reference the updated instincts with project knowledge to produce actionable proposals:

1. Read `.ai-engineering/LESSONS.md` to check for already-captured patterns.
2. Read project context: `CONSTITUTION.md`, `.ai-engineering/manifest.yml`, and the target artifact (e.g., `.claude/skills/ai-<skill>/SKILL.md` or `.claude/agents/ai-<agent>.md`) to understand the improvement surface. If only `.ai-engineering/CONSTITUTION.md` exists, use it as a compatibility fallback.
3. Filter instincts: only those with `confidence >= 0.7` AND `evidenceCount >= 3` qualify as proposals.
4. For each qualifying instinct, check if the pattern is already captured in LESSONS.md -- if so, skip.
5. Append a new `PROP-NNN` entry to `.ai-engineering/instincts/proposals.md`:

```markdown
## PROP-NNN: <title>

- **Status**: proposed
- **Source**: <family> instinct, confidence <N>, evidence <N>
- **Pattern**: <what was observed>
- **Diagnostic**: <error message or correction signal from the instinct>
- **Proposed fix**: <specific change: update SKILL.md procedure, add LESSONS.md entry, adjust manifest config, etc.>
- **Target**: LESSONS.md | SKILL.md (<which skill>) | agent.md (<which agent>) | manifest.yml | hook (<which hook>)
- **LESSONS.md cross-ref**: <"none" or the matching lesson heading if partial overlap exists>
```

Number proposals sequentially (PROP-001, PROP-002, ...). Check existing entries in proposals.md before assigning the next number.

#### Step 5: CREATE WORK ITEMS

If `.ai-engineering/manifest.yml` has a `work_items` section, create trackable work items for each new proposal. Follow the same fail-open protocol as `ai-board-sync`: never block the calling workflow.

1. Read `work_items.provider` from `.ai-engineering/manifest.yml`.
2. **Check for duplicates** before creating:
   - **GitHub**: `gh issue list --label "ai-engineering,instinct" --state open --json title`
   - **Azure DevOps**: `az boards query --wiql "SELECT [System.Title] FROM WorkItems WHERE [System.Tags] CONTAINS 'instinct' AND [System.State] <> 'Closed'" -o json`
   - If a work item with a matching title already exists, skip and note "duplicate" in the output.
3. Create the work item:
   - **GitHub** (`work_items.provider: github`): `gh issue create --title "instinct: [target] - [diagnostic]" --body "<proposal body>" --label "ai-engineering,instinct"`
   - **Azure DevOps** (`work_items.provider: azure_devops`): `az boards work-item create --title "instinct: [target] - [diagnostic]" --description "<proposal body>" --type "Task"`
4. Update the proposal entry in `.ai-engineering/instincts/proposals.md`: set `Status` to `work-item-created` and append `- **Work item**: <ref>` (e.g., `#45` or `AB#100`).
5. If no `work_items` section in manifest, skip silently.
6. Fail-open: if CLI is not authenticated, project is not found, or command fails -- log a warning with remediation hint (e.g., `gh auth login`) but do not block the review.

## Review-Mode Output

Structured summary: observations extracted (count per family), entries upserted (new vs. updated), proposals generated (count, titles), work items created (count, links). If no meaningful observations: "No consolidation needed -- session had no corrections, recoveries, or notable workflow patterns."

## Boundaries

- Project-local only. No global instinct scope.
- One canonical `instincts.yml`, not one file per instinct.
- Never store transcripts, prompts, responses, or raw tool payloads.
- Do not create instincts outside `.ai-engineering/instincts/`.
- Do not invent unsupported pattern types beyond corrections/recoveries/workflows.
- Do not claim the system supports promotion, evolution, or global libraries.

$ARGUMENTS
