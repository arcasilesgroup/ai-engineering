---
name: ai-start
description: "Bootstraps a coding session: loads project context, activates session observation, displays a welcome dashboard with recent activity, board items, and available commands. Trigger for 'hello', 'lets start', 'good morning', 'whats the status', 'get me up to speed', 'I am back'. Also invokable mid-session to re-bootstrap. Not for human onboarding; use /ai-guide instead. Not for governance review; use /ai-governance instead."
effort: mid
argument-hint: 
model_tier: sonnet
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

### Step 1: Bootstrap (deterministic, ≤300ms, single call)

Run **exactly one command** — the literal argv form below — and parse the JSON dashboard:

```
uv run python .ai-engineering/scripts/session_bootstrap.py
```

The script is enrolled in the trusted-script lane (`hooks-manifest.json` `trustedArgvs`), so this single argv bypasses RTK rewriting + IOC re-evaluation. Do not modify the argv (no positional flags, no shell wrappers) — the lane is literal-match (D-131-12). Any other invocation form falls back to the full IOC path. (`uv run python` is required because the script imports `yaml` and `skill_scripts_lib`, both of which live in the project venv; plain `python3` will fail with `ModuleNotFoundError: yaml`.)

Fields returned:
- `branch`, `last_commit` (sha, subject)
- `active_spec` (id, state, title, tasks_total, tasks_done) or `null`
- `recent_events_7d` (int)
- `hooks_health` (string)

**Trust the JSON.** Do not re-derive any field with your own `git`, `yaml`, `sqlite`, or `gh` calls — that is the re-probe pattern that operator-pain #18b flags.

### Step 2: Display dashboard

Render the welcome dashboard as raw Markdown — NOT inside a code block. Markdown renders natively across Claude Code, claude.ai, GitHub Copilot, Codex, and Gemini CLI.

Use the JSON from Step 1 as the source of truth. Read `name` from `.ai-engineering/manifest.yml` ONCE for the project header — that single read is the only allowed manifest probe. Budget: ≤ 50 lines.

Template (output directly as Markdown, replacing placeholders; omit any line whose field is not present in the JSON):

````markdown
## ◈ [name]

> hooks: [hooks_health] · events 7d: [recent_events_7d]

---

### ▸ Active Work

- **Spec [active_spec.id]** — [active_spec.title] · `[active_spec.state]`
- **Plan** — [active_spec.tasks_done]/[active_spec.tasks_total] tasks complete

### ▸ Recent

- **[last_commit.sha]** [last_commit.subject]

---

`/ai-brainstorm` design · `/ai-debug` fix · `/ai-guide` explore · `/ai-commit` save
`/ai-review` review · `/ai-pr` ship · `/ai-test` verify · `/ai-cleanup` tidy
````

When `active_spec` is `null`, replace the Active Work block with `no active spec — run /ai-brainstorm`.

### Step 3: Optional — board + observation (after the dashboard renders)

After Step 2 prints the dashboard, you MAY run the following — both are fail-graceful and never block the dashboard:

- **Board status** (see Board Display section). Show `board unavailable` if the call errors; never block on it.
- **Observation activation**: invoke `/ai-observe` (fire-and-forget; the session continues whether observation initialises or not).

Skip Step 3 when the operator's first message after `/ai-start` is already a follow-up question — they read the dashboard, they want an answer, not more probes.

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
