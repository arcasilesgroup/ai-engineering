---
name: ai-issue
description: "Creates a project work-item (issue / task / story) on the user's configured board: routes by manifest `work_items.provider` (GitHub Projects v2 or Azure DevOps), composes title + body + labels, attaches to the active board, and confirms a clickable link. Trigger for 'open an issue', 'file a bug', 'create a task', 'add this to the backlog', 'log a work item'. Not for upstream framework bugs (use /ai-engineering-issue); not for board configuration (use /ai-board discover); not for committing code (use /ai-commit)."
effort: cheap
model_tier: haiku
argument-hint: "<title> [--body <text>] [--labels a,b] [--dry-run]"
tags: [work-items, board, issue, github, azure_devops]
requires:
  bins:
    - gh
---


# Issue Creation

Discoverable wrapper around the project board: composes a work-item, routes by manifest provider, attaches to the configured GitHub Project (or Azure Boards area path), confirms the URL.

```
/ai-issue "<title>"                                # default body from session context
/ai-issue "<title>" --body "<text>"                # explicit body
/ai-issue "<title>" --labels bug,p1                # apply labels
/ai-issue "<title>" --dry-run                      # print the command, do not invoke
```

## Quick Start

1. Confirm the active provider in `.ai-engineering/manifest.yml` under `work_items.provider` — either `github` or `azure_devops`.
2. Confirm CLI auth: `gh auth status` for GitHub, `az account show` for Azure DevOps.
3. Invoke `/ai-issue "<title>"` — the skill composes title + body + labels and attaches to the configured board.

## Workflow

Principles applied: §10.1 KISS (thin wrapper over board plumbing; no rediscovery of provider state); §10.4 DRY (reuses `manifest.yml work_items` config rather than redefining provider routing per skill); §10.6 SDD (implements D-134-02 — discoverable issue surface promoted to first-class).

1. **Read configuration.** Open `.ai-engineering/manifest.yml` and locate the `work_items:` section. Required keys: `provider` (`github` or `azure_devops`). For GitHub also read `github_project.{owner,number}` and `github.team_label`. For Azure DevOps read `azure_devops.area_path` and `process_template`. If the section is absent or empty, refuse with a remediation line ("manifest missing `work_items` config — run `/ai-board discover` first") and exit non-zero.
2. **Preflight auth.** Run `gh auth status` (GitHub path) or `az account show` (Azure path). On non-zero exit, refuse with the remediation hint ("run `gh auth login`" / "run `az login`") and exit. Never proceed with an unauthenticated CLI.
3. **Compose title and body.** Title comes from `$ARGUMENTS` (or interactive prompt if absent). Body defaults to the session-context summary (recent commits, active spec, error logs) — overridable with `--body "<text>"`. Apply labels from `--labels` plus the configured `work_items.github.team_label`. Honour the `--dry-run` flag by printing the planned shell command without invoking.
4. **GitHub path.** Shell `gh issue create --title "<t>" --body "<b>" --label "<l1>,<l2>"`. Then attach to the project: `gh project item-add <number> --owner <owner> --url <issue-url>`. Capture the returned issue URL.
5. **Azure DevOps path.** Shell `az boards work-item create --title "<t>" --type "Task" --area "<area_path>" --description "<b>"`. Then set fields per `custom_fields` table in manifest. Capture the returned work-item ID + URL.
6. **Report outcome.** Print the issue URL (or work-item ID) and the configured board phase ("Backlog" by default — the state mapping comes from `work_items.state_mapping.refinement`).
7. **Audit.** Emit a `framework_event` with `kind: work_item_created`, `component: ai-issue`, `detail: {provider, issue_id, url}`. The event chains into the standard audit pipeline.

## Examples

### Example 1 — GitHub Projects v2 issue

User: "open an issue: pre-commit hook times out on macOS arm64"

```
/ai-issue "pre-commit hook times out on macOS arm64" --labels bug,p1
```

Skill reads `work_items.provider: github`, runs `gh auth status` (green), composes the body from recent session context, shells `gh issue create --title "..." --label "bug,p1,team:core"`, attaches to GitHub Project `arcasilesgroup/4`, prints the issue URL.

### Example 2 — Azure DevOps task with dry-run preview

User: "create a task to wire up the new spec gate, but show me the command first"

```
/ai-issue "wire up spec gate in /ai-brainstorm" --dry-run
```

Skill reads `work_items.provider: azure_devops`, prints the planned `az boards work-item create --title "..." --type "Task" --area "Project\TeamName"` invocation and exits without calling Azure.

## Quick Reference

| Goal | Command |
|------|---------|
| Create issue with session-context body | `/ai-issue "<title>"` |
| Provide explicit body | `/ai-issue "<title>" --body "<text>"` |
| Apply labels | `/ai-issue "<title>" --labels bug,p1` |
| Preview without invoking | `/ai-issue "<title>" --dry-run` |

## Common Mistakes

- Calling `/ai-issue` without running `/ai-board discover` first — the manifest needs `work_items.provider` populated before this skill can route.
- Bypassing the auth preflight — an unauthenticated `gh` / `az` will produce a partial / confusing failure; the skill refuses on purpose.
- Confusing this skill with `/ai-engineering-issue` — that one files upstream framework bugs and runs strict seven-vector redaction. `/ai-issue` is for **your project's** board.

## Integration

Called by: user directly. Reads: `.ai-engineering/manifest.yml` (`work_items` section). Writes: project board (GitHub Projects v2 item OR Azure Boards work item). Audited: `framework_event kind=work_item_created`. Pairs with: `/ai-board discover` (one-time provider configuration), `/ai-board sync` (lifecycle state transitions on existing items). See also: `/ai-engineering-issue` for upstream framework bug reports with strict redaction.

$ARGUMENTS
