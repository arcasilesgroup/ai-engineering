---
name: ai-start
description: "Bootstraps a coding session: loads project context, activates session observation, displays a welcome dashboard with recent activity, board items, and available commands. Trigger for 'hello', 'lets start', 'good morning', 'whats the status', 'get me up to speed', 'I am back'. Also invokable mid-session to re-bootstrap. Not for human onboarding; use /ai-guide instead. Not for governance review; use /ai-governance instead."
effort: medium
argument-hint: 
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-start/SKILL.md
edit_policy: generated-do-not-edit
---


# Start

## Purpose

Session welcome dashboard. Loads project context, activates session observation, and shows everything needed to begin working. Users run this because the dashboard is useful — context loading is a built-in benefit.
This skill is invoked as an IDE slash command (`/ai-start`). It is not an `ai-eng start` terminal command, and no CLI fallback should be inferred unless the CLI docs explicitly define one.

## Process

### Step 1: Bootstrap (deterministic, <300ms)

Run `python3 .ai-engineering/scripts/session_bootstrap.py` and parse the JSON dashboard. Fields: `branch`, `last_commit`, `active_spec` (id/state/title/tasks_total/tasks_done), `recent_events_7d`, `hooks_health`. Use these directly — no LLM data shuffle.

### Step 2: Load context

Read `session.context_files` from `.ai-engineering/manifest.yml`. If `manifest.yml` is missing or `session.context_files` is not defined, skip and note in the dashboard: 'manifest not found — run `/ai-constitution` to initialize'.

### Step 3: Activate observation

Run `/ai-observe` to enter observation mode for this session.

### Step 4: Gather supplementary status (LLM-only where genuinely needed)

- **Recent activity narrative**: run `git log --oneline -5` and generate a 3-line human-readable summary. Plain language, not raw log.
- **Board status**: follow the Board Display section below.

### Step 5: Display dashboard

Render the welcome dashboard as raw Markdown — NOT inside a code block. Markdown renders natively across Claude Code, claude.ai, GitHub Copilot, Codex, and Gemini CLI.

Read `name` from `.ai-engineering/manifest.yml` for the project header. Budget: ≤ 50 lines.

Template (output directly as Markdown, replacing placeholders):

````markdown
## ◈ [name]

> LESSONS (N) · CONSTITUTION · manifest (N skills, N agents) · decisions (N active, N risks)
> observation mode active

---

### ▸ Active Work

- **Spec NNN** — [title] · `status`
- **Plan** — N/M tasks complete | no active plan

### ▸ Recent

- [LLM summary line] (#NNN)
- [LLM summary line] (#NNN)
- [3-5 bullets from last 5 commits]

### ▸ Board · [provider] [project]

- N items — Status1: N · Status2: N
- or: not configured — run `/ai-board discover`

---

`/ai-brainstorm` design · `/ai-debug` fix · `/ai-guide` explore · `/ai-commit` save
`/ai-review` review · `/ai-pr` ship · `/ai-test` verify · `/ai-cleanup` tidy
````

Formatting rules:
- Use `·` (middle dot U+00B7) as inline separator
- Status values in inline code backticks: `approved`, `in_progress`, `draft`
- Plan complete: append ✓ after count
- PR references in parentheses: (#NNN)
- No active spec: `no active spec — run /ai-brainstorm`
- Board unavailable: `board unavailable` — never block the dashboard
- Proposals (if any): add `### ▸ Proposals` section with count and titles (≤ 3 lines)

## Board Display

1. Read `work_items.provider` from manifest. This is the ONLY field that determines which provider to use.
2. Branch on the value:

**IF `work_items.provider` is `github`**:
- If `work_items.github_project.number` is set: read `work_items.github_project.owner` from manifest for the `--owner` flag. `gh project item-list <number> --owner <github_project.owner> --format json --limit 10`
- Else: `gh issue list --limit 10 --json number,title,state,labels`

**ELSE IF `work_items.provider` is `azure_devops`**:
- Read `work_items.azure_devops.area_path` from manifest.
- `az boards query --wiql "SELECT [System.Id],[System.Title],[System.State] FROM WorkItems WHERE [System.AreaPath] UNDER '<area_path>' ORDER BY [System.ChangedDate] DESC" --top 10 -o json`

**ELSE**: show `board provider unknown — check work_items.provider in manifest`.

Show count grouped by status. Keep it to 1-3 lines.

If `work_items` section missing from manifest: show `not configured — run /ai-board discover`.
If API call fails: show `board unavailable` and continue. Never block the dashboard.

## Context Budget

| Section | Max lines |
|---------|-----------|
| Header + context | 4 |
| Active work | 4 |
| Recent activity | 7 |
| Board | 3 |
| Quick actions | 2 |
| Proposals (if any) | 3 |
| **Total** | **≤ 50** |

## Examples

### Example 1 — morning bootstrap

User: "good morning, where did I leave off?"

```
/ai-start
```

Loads context, activates instinct, prints the dashboard: recent activity, active spec, board status, suggested next command.

### Example 2 — mid-session re-bootstrap after `/clear`

User: "I cleared context — get me back up to speed"

```
/ai-start
```

Re-loads project context without rebuilding the conversation; shorter dashboard since recent activity is limited to commits since last bootstrap.

## Integration

Called by: user directly, IDE instruction files (FIRST ACTION mandate). Calls: `/ai-observe` (observation mode). Suggests: `/ai-board discover` (board not configured), `/ai-brainstorm` (no active spec). See also: `/ai-guide` (human onboarding), `/ai-cleanup` (pre-start hygiene).
