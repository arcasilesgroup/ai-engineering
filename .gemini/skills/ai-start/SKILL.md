---
name: ai-start
description: Use at the start of every coding session to load project context, activate instinct observation, and display a welcome dashboard with recent activity, active work status, board items, and available commands. Trigger for 'hello', 'let's start', 'good morning', 'what's the status', 'get me up to speed', 'I'm back', or any session-opening message. Also invokable mid-session to re-bootstrap. Not for human onboarding — use /ai-guide for that.
effort: medium
argument-hint: 
---


# Start

## Purpose

Session welcome dashboard. Loads project context, activates instinct observation, and shows everything needed to begin working. Users run this because the dashboard is useful — context loading is a built-in benefit.

## Process

### Step 1: Load context

Read `session.context_files` from `.ai-engineering/manifest.yml` to discover which files to load. If `manifest.yml` is missing or `session.context_files` is not defined, skip context loading and note in the dashboard: 'manifest not found — run `/ai-constitution` to initialize'. Read each file. Count meaningful data for the summary line (e.g., number of lessons, number of decisions, active risks).

### Step 2: Activate instinct

Run `/ai-instinct` to enter observation mode for this session.

### Step 3: Gather status

Collect these in parallel:

- **Active spec**: read `.ai-engineering/specs/spec.md` frontmatter — extract title and status. Spec frontmatter is YAML between `---` delimiters. Extract `title` and `status` fields. If file missing or empty: `no active spec`.
- **Plan progress**: read `.ai-engineering/specs/plan.md` — count checked `[x]` vs total `[ ]` tasks. If missing: `no active plan`.
- **Recent activity**: run `git log --oneline -5` and generate a 3-5 line human-readable summary. Not the raw log — explain what happened in plain language.
- **Board status**: follow the Board Display section below.
- **Instinct proposals**: read `.ai-engineering/instincts/proposals.md` — if it has content beyond the header, count proposals.

### Step 4: Display dashboard

Render the welcome dashboard as raw Markdown — NOT inside a code block. Markdown renders natively across Claude Code, claude.ai, GitHub Copilot, Codex, and Gemini CLI.

Read `name` from `.ai-engineering/manifest.yml` for the project header. Budget: ≤ 50 lines.

Template (output directly as Markdown, replacing placeholders):

````markdown
## ◈ [name]

> LESSONS (N) · CONSTITUTION · manifest (N skills, N agents) · decisions (N active, N risks)
> instinct · observation mode active

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
- or: not configured — run `/ai-board-discover`

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

If `work_items` section missing from manifest: show `not configured — run /ai-board-discover`.
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

## Integration

- **Called by**: user directly, IDE instruction files (FIRST ACTION mandate)
- **Calls**: `/ai-instinct` (observation mode)
- **Suggests**: `/ai-board-discover` (board not configured), `/ai-brainstorm` (no active spec)
