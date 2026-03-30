# AI Run Provider Matrix

## Work Item Sources

| Source | Intake | Identity | Lifecycle Notes |
|--------|--------|----------|-----------------|
| GitHub Issues | `gh issue` / provider handlers | `#123` | Close on final PR only when hierarchy allows |
| Azure Boards | `az boards` / provider handlers | `AB#123` | Board state is explicit; closure may be PR-driven or sync-driven |
| Markdown | local parser | heading/checklist path | No remote lifecycle; local status only |

## Delivery Providers

| Provider | Delivery Surface | Notes |
|----------|------------------|-------|
| GitHub | `ai-pr` + `gh pr` | final PR body owns authoritative `Closes #N` refs |
| Azure Repos | `ai-pr` + `az repos pr` | may combine PR delivery with work-item transitions |

## Supported Pairings

| Work Items | Delivery | Valid |
|------------|----------|-------|
| GitHub | GitHub | yes |
| Azure Boards | GitHub | yes |
| Azure Boards | Azure Repos | yes |
| Markdown | GitHub | yes |
| Markdown | Azure Repos | yes |

## Hierarchy and Closure

Use `work_items.hierarchy` policy from `.ai-engineering/manifest.yml`.

- `feature` -> `never_close`
- `user_story` -> typically `close_on_pr`
- `task` -> typically `close_on_pr`
- `bug` / `issue` -> typically `close_on_pr`

Provider rules:

- GitHub:
  - closeable refs appear as `Closes #N` only on the final PR
  - mention-only refs appear as `Related: #N`
- Azure Boards:
  - closeable refs use `AB#N` plus provider transition rules
  - feature-level refs stay mention-only

## Existing Contracts To Reuse

- `src/ai_engineering/work_items/service.py`
- `src/ai_engineering/vcs/pr_description.py`
- `.claude/skills/ai-board-sync/SKILL.md`
- `.claude/skills/ai-pr/SKILL.md`
