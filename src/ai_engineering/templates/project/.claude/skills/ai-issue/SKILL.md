---
name: ai-issue
description: "Creates a project work-item (issue / task / story) on the user's configured board: routes by manifest `work_items.provider` (GitHub Projects v2 or Azure DevOps), composes title + body + labels, attaches to the active board, and confirms a clickable link. Trigger for 'open an issue', 'file a bug', 'create a task', 'add this to the backlog', 'log a work item'. Not for upstream framework bugs (use /ai-engineering-issue); not for board configuration (use /ai-board discover); not for committing code (use /ai-commit)."
effort: cheap
argument-hint: "<title> [--body <text>] [--labels a,b] [--dry-run]"
tags: [work-items, board, issue, github, azure_devops]
requires:
  bins:
    - gh
---


# Issue Creation

Thin wrapper over the project board: composes a work-item, routes by manifest provider, attaches to the configured GitHub Project (or Azure Boards area path), confirms the URL.

```
/ai-issue "<title>"                    # body from session context
/ai-issue "<title>" --body "<text>"    # explicit body
/ai-issue "<title>" --labels bug,p1    # apply labels
/ai-issue "<title>" --dry-run          # print the command, do not invoke
```

## Workflow

Principles: §10.1 KISS (thin wrapper, no provider rediscovery); §10.4 DRY (reuses `manifest.yml work_items` routing); §10.6 SDD (D-134-02 — discoverable issue surface).

1. **Read config.** Open `manifest.yml` `work_items:`. Required: `provider` (`github`|`azure_devops`). GitHub also: `github_project.{owner,number}`, `github.team_label`. Azure also: `azure_devops.area_path`, `process_template`. If absent/empty, refuse: "manifest missing `work_items` config — run `/ai-board discover` first" and exit non-zero.
2. **Preflight auth.** `gh auth status` (GitHub) or `az account show` (Azure). On non-zero, refuse with the fix hint (`gh auth login` / `az login`) and exit. Never proceed unauthenticated.
3. **Compose.** Title from `$ARGUMENTS` (else prompt). Body defaults to session-context summary (recent commits, active spec, error logs); override with `--body`. Labels = `--labels` + configured `work_items.github.team_label`. Honour `--dry-run` (print planned command, do not invoke).
4. **GitHub path.** `gh issue create --title <t> --body <b> --label <l1,l2>`, then `gh project item-add <number> --owner <owner> --url <issue-url>`. Capture URL.
5. **Azure path.** `az boards work-item create --title <t> --type Task --area <area_path> --description <b>`, then set fields per manifest `custom_fields`. Capture ID + URL.
6. **Report.** Print the issue URL (or work-item ID) and board phase ("Backlog" by default, from `work_items.state_mapping.refinement`).
7. **Audit.** Emit `framework_event kind=work_item_created`, `component: ai-issue`, `detail: {provider, issue_id, url}`.

## Examples

User: "open an issue: pre-commit hook times out on macOS arm64"

```
/ai-issue "pre-commit hook times out on macOS arm64" --labels bug,p1
```

Reads `work_items.provider: github`, runs `gh auth status` (green), composes the body from session context, shells `gh issue create --label "bug,p1,team:core"`, attaches to the GitHub Project, prints the URL.

## Integration

Called by user. Reads `.ai-engineering/manifest.yml` (`work_items`). Writes the project board (GitHub Projects v2 item OR Azure Boards work item). Audits `framework_event kind=work_item_created`. Pairs with `/ai-board discover` (one-time provider config) + `/ai-board sync` (lifecycle state transitions). See also `/ai-engineering-issue` (upstream framework bugs, strict redaction — distinct from **your** project's board).

$ARGUMENTS
