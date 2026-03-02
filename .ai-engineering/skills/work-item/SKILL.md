---
name: work-item
description: "Bidirectional work-item integration with Azure Boards and GitHub Issues/Projects — create, update, link, and sync work items with local specs."
metadata:
  version: 1.0.0
  tags: [work-items, azure-boards, github-issues, sync, integration]
  ai-engineering:
    scope: read-write
    token_estimate: 1200
    gating:
      anyBins: [gh, az]
---

# Work Item Integration

## Purpose

Bidirectional work-item integration between local spec lifecycle and external tracking systems (Azure Boards, GitHub Issues/Projects). Enables local specs to create/link work items, and external work items to trigger local spec creation.

## Trigger

- `ai:plan` pipeline step 5 (work-item sync after spec creation).
- User requests work-item creation or linking.
- Remote work item tagged "ready" needs local spec.
- Spec closure requires work-item state transition.

## Procedure

### Step 1 — Detect Platform

Read `manifest.yml` for configured work-item providers:

```yaml
work_items:
  enabled: true
  primary: "github-issues"  # or "azure-boards"
  sources:
    - type: "github-issues"
      labels_ready: ["ready", "agent-ready"]
    - type: "azure-boards"
      project: "platform"
      query_ready: "[System.Tags] CONTAINS 'agent-ready'"
```

Verify CLI tool availability:
- GitHub Issues: `gh` CLI authenticated
- Azure Boards: `az` CLI authenticated with `az boards` extension

### Step 2 — Determine Operation

Classify the requested operation:
- **create**: new work item from spec
- **link**: associate existing work item with spec
- **sync**: update work item state from spec status
- **read**: fetch work items matching criteria
- **transition**: move work item through states

### Step 3 — Create Work Item (from spec)

Extract from local spec:
- Title from `spec.md` heading
- Description from Problem + Solution sections
- Acceptance criteria from spec.md
- Phase breakdown from plan.md
- Task count from tasks.md

Create via platform CLI:

**GitHub Issues:**
```bash
gh issue create --title "<title>" --body "<body>" --label "spec-NNN"
```

**Azure Boards:**
```bash
az boards work-item create --type "User Story" --title "<title>" --description "<body>" --area "<area>"
```

### Step 4 — Link Work Item to Spec

Store bidirectional reference:
- In spec.md frontmatter: `work_item: "<platform>:<id>"`
- In work item: add comment linking to spec branch/path

### Step 5 — Sync State

Map spec status to work-item state:

| Spec Status | GitHub Issue | Azure Boards |
|-------------|-------------|--------------|
| in-progress | Open | Active |
| review | Open + "review" label | Resolved |
| done | Closed | Closed |

Auto-transition when:
- `tasks.md` completed = total → close work item
- `done.md` created → close work item
- PR merged → close work item

### Step 6 — Read Remote Items

Query for items matching criteria:

**GitHub:** `gh issue list --label "ready" --state open`
**Azure:** `az boards query --wiql "<query>"`

Return structured list: ID, title, state, labels, assignee, priority.

## Output Contract

- Work item created/updated with platform reference.
- Bidirectional link stored (spec ↔ work item).
- State transition applied.
- Sync report: items synced, transitions applied, conflicts detected.

## Governance Notes

- Work-item sync is advisory — human approves all transitions.
- Conflict resolution: local spec is source of truth; remote changes flagged for review.
- Never auto-close work items without spec closure evidence (done.md or PR merge).
- Platform credentials must not be stored in repo — use CLI auth or env vars.
