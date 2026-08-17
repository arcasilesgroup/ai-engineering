# ai-engineering

A governance framework for agents that write code. It installs in a minute, it fits in one
head, and everything it promises is checked by a command that exits non-zero.

```bash
uv tool install ai-engineering
ai-eng init
```

The second command asks before it touches anything, and every default destroys nothing.

## What it is

Twelve written procedures, six guards, and a command-line tool with ten verbs. `init`
places the procedures and registers the guards in the settings file each agent surface
already reads, so they are present in every project on your machine without a single file
landing in any of them. The package carries the record: it writes specs, plans, decisions
and dated risk acceptances as plain text in your repository, where reviewers read them in
a pull request.

## Every promise is a command

| The promise | Its command | What makes it fail |
|---|---|---|
| Deterministic — the same rules for every person and for CI | `ai-eng doctor` | The installed wheel is not what the repository pins, or a guard entry points at another install |
| Auditable — tamper-evident, survives losing the laptop | `ai-eng audit verify --anchors` | Any break in the chain, or a head anchored in git that is missing locally |
| Your data is yours | `ai-eng doctor --paths` | Any framework file outside `.ai/`, `specs/` and `docs/adr/` |
| No lock-in | delete `.ai/` | Nothing. `specs/` is markdown that outlives us. |

## What lands in your repository

Seven files: `AGENTS.md`, `CONSTITUTION.md`, `CLAUDE.md`, `justfile`,
`.github/workflows/check.yml`, `.ai/config.toml` and
`.ai/.gitignore` — plus your specs. No installer payload, no templates, no copied skills,
no per-IDE mirror trees. The guards stay inside the installed wheel and are pointed at
from the settings file each surface already reads.

## What actually blocks, and where

`ai-eng doctor` ends with one line per surface, and it is derived from the receipt, the
pin and the settings files on disk — never from a probe or a billed session.

- **No surface reads as blocking.** Not one has a receipted denial, so every surface
  that can deny reads **unproven** — including Claude Code, which is perfectly able
  to. CI does execute the dispatcher's deny path from the installed wheel, but nothing
  has yet executed one *through* a surface and written the receipt, and the distinction
  is the whole point. What is missing is the evidence, not the ability.
- **Codex CLI** installs and then sits **inert** until a human types `/hooks` to approve
  it. It is skipped silently until then, and nothing but a person can change that.
- **Cursor**, **VS Code Copilot** and **Copilot CLI** document a working deny, and none of
  them is proven here. They read **unproven**, not "covered".
- **pi**, **Zed** and anything else reading `AGENTS.md` get the instructions and the
  skills, and enforce nothing above the git layer.

Underneath all of that, the git hooks and your CI are the floor, and they do not depend on
any agent surface at all.

## Documentation

- `AGENTS.md` — the twelve rules, and how work happens in this repository.
- `CONSTITUTION.md` — what this project is, and what it never does.
- `SECURITY.md` — how to report something, and what this cannot protect you from.

Apache 2.0. See LICENSE.
