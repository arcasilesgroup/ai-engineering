# ai-engineering

Open-source AI governance framework for secure, practical software delivery.

## Status

- Contract baseline and CLI governance workflows are implemented.
- `.ai-engineering/` is the canonical governance root.

## Core Principles

- simple, efficient, practical, robust, secure.
- quality and security by default.
- lifecycle enforcement: Discovery -> Architecture -> Planning -> Implementation -> Review -> Verification -> Testing -> Iteration.
- strict local enforcement with no policy drift.

## Command Contract

- `/commit` -> stage + commit + push current branch
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; warns if branch is unpushed and proposes auto-push
- `/acho` -> stage + commit + push current branch
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `ai stack add/remove/list <stack>` -> manage stack templates with safe cleanup semantics
- `ai ide add/remove/list <ide>` -> manage IDE instruction templates with safe cleanup semantics

## Tooling Baseline

- package/runtime: `uv`
- lint/format: `ruff`
- type checking: `ty`
- dependency vulnerability checks: `pip-audit`
- mandatory security checks: `gitleaks`, `semgrep`

## Governance Docs

- Product vision: `.ai-engineering/context/product/vision.md`
- Architecture: `.ai-engineering/context/delivery/architecture.md`
- Planning: `.ai-engineering/context/delivery/planning.md`
- Backlog: `.ai-engineering/context/backlog/`

## License

MIT
