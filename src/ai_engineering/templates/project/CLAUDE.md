# CLAUDE.md

Project instructions are canonical in `.ai-engineering/`.

## Required References

- `.ai-engineering/context/product/framework-contract.md`
- `.ai-engineering/standards/framework/core.md`
- `.ai-engineering/standards/framework/stacks/python.md`
- `.ai-engineering/standards/team/core.md`
- `.ai-engineering/context/delivery/planning.md`
- `.ai-engineering/context/backlog/tasks.md`

## Command Contract

- `/commit` -> stage + commit + push
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; if declined, continue with selected mode
- `/acho` -> stage + commit + push
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Non-Negotiables

- mandatory local gates cannot be bypassed,
- no direct commits to protected branches,
- update safety must preserve team/project-owned content.
