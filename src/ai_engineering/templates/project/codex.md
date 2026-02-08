# Codex Project Instructions

Use `.ai-engineering/` as the only governance and context source.

## Read First

- `.ai-engineering/context/product/framework-contract.md`
- `.ai-engineering/standards/framework/core.md`
- `.ai-engineering/context/backlog/tasks.md`

## Command Behavior

- `/commit` and `/acho` push current branch after governed checks.
- `/pr --only` warns on unpushed branch and proposes auto-push, then continues by selected mode.

## Security and Quality

- run local mandatory checks,
- fix failures locally,
- avoid bypass flags.
