# Configuration

`ai-eng init` writes `.ai-engineering/config.toml` with each key commented and set to its
default. You edit it by hand; the chain reads it and never writes it.

| Table | What it sets |
|---|---|
| `[surfaces]` | the agents this repository is governed on (`ai-eng config` rewrites only this key) |
| `[ci]` | the CI provider |
| `[guards]` | the loop thresholds, the command-scope policy and your own injection rules |
| `[gc]` | what `ai-eng doctor --gc` keeps, and how long receipts live |
| `[git]`, `[work]`, `[notices]` | commented out: worktree folder, lane limits, update notice |

The **command-scope policy** is four octal digits: system, external, network and workspace.
Each digit adds read (4), write (2) and execute (1). The default, `4667`, allows system
reads, external and network reads and writes, and everything in the workspace.

A change an agent proposes to these files is applied by a person, outside the agent session:
`self-protect` denies the agent's own write.

## Surfaces

A surface is an agent host: an IDE or a CLI. `ai-eng` writes one set of definitions,
enables them per surface you choose, and mirrors the skills into every host's skill folder,
so the same guard judges the same call whichever host sent it.
[`src/surfaces/surfaces.json`](../src/surfaces/surfaces.json) records what each host supports.

| Tier | Meaning | Surfaces |
|---|---|---|
| core | deny, plus a rewritten command where the host allows it | `claude-code`, `oh-my-pi`, `opencode`, `cursor`, `pi` |
| experimental | works, less proven | `codex` |
| best-effort | the host limits the outcome | `copilot-cli` |
| skills-only | skills, no interception | `zed`, `agy` |

`ai-eng config --add <id>` and `ai-eng config --remove <id>` turn a surface on or off and
regenerate its files (`agy` and `zed` are declared but refused: see the matrix). `ai-eng
doctor` reports, per surface, whether its hook file is where that host reads it, and whether
the surface is **enforced** (synchronous pre-tool deny) or **advisory** (observation only).
The [capability matrix](surface-capability-matrix.md) is the measured truth for what
each host can and cannot enforce; [Global carriers](global-carriers.md) explains how
the carrier files are installed and removed.
