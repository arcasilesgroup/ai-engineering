# Directory Schemas & Hexagonal Layer Map

Source-of-truth for the `src/ai_engineering/` layer membership used by
the `import-linter` direction contract in `pyproject.toml`
(`[tool.importlinter]`). Introduced by spec-132 sub-005 D-132-13.

## Layer map

| Directory / module                                | Layer        | Notes                                                  |
| ------------------------------------------------- | ------------ | ------------------------------------------------------ |
| `src/ai_engineering/core/`                        | core         | New hexagonal home (renderer, cli decorators today).   |
| `src/ai_engineering/governance/`                  | core         | Decision log, OPA runner, policy engine, bundle.       |
| `src/ai_engineering/state/`                       | core         | state.db, manifest, audit, capabilities, locking.      |
| `src/ai_engineering/policy/`                      | core         | Orchestrator, gate cache, watch residuals, checks.     |
| `src/ai_engineering/validator/`                   | core         | Validator categories, shared helpers.                  |
| `src/ai_engineering/cli_commands/`                | adapter      | Typer command callbacks (parse + delegate).            |
| `src/ai_engineering/installer/`                   | adapter      | Phase orchestration, templates, mechanisms.            |
| `src/ai_engineering/vcs/`                         | adapter      | gh / ado wiring.                                       |
| `src/ai_engineering/ide/`                         | adapter      | Claude / Copilot / Gemini / Codex surface wirings.     |
| `src/ai_engineering/updater/`                     | adapter      | Update preview/apply flow.                             |
| `src/ai_engineering/issues/`                      | adapter      | GitHub issue sync adapter (renamed from work_items).   |
| `src/ai_engineering/cli*.py` (flat top-level)     | transitional | `cli_envelope`, `cli_ui`, `cli_progress`, `cli_output`, `cli_factory`, `cli_preflight`, `cli.py`. Not classified yet. |
| `src/ai_engineering/{config,credentials,git,hooks,release,...}/` | transitional | Shared utilities pending classification. |

## Direction rule

`core` modules **MUST NOT** import from `adapter` modules. The reverse
direction is the natural shape of a hexagonal architecture: delivery
surfaces drive use-cases against the domain core. The contract is
enforced by `lint-imports` via `[tool.importlinter]` in
`pyproject.toml` and policed by
`tests/architecture/test_hexagonal.py`.

Transitional modules (the third group above) are deliberately NOT in
either layer today. They ride for free until a follow-up spec moves
them into the appropriate layer. New code SHOULD prefer the
explicit-layer modules over the transitional ones.

## Pilot relocations done in spec-132 sub-005

None. This sub-spec ships the DIRECTION enforcement only. Physical
relocation of the flat tree is deferred per the orchestrator
decision (see `## Deferred relocations` below).

Previously-shipped relocations that already live in `core/`:

- `core/cli/decorators.py` (sub-003) — `no_args_help` decorator.
- `core/output/renderer.py` (sub-002) — Renderer single-source-of-truth for CLI output.

## Baseline-pinned ignores

`pyproject.toml` `[[tool.importlinter.contracts]]` `ignore_imports`
records 4 pre-existing direction violations as of spec-132 sub-005
land time. The contract BLOCKS any NEW violation; the baseline rides
out until the follow-up relocation spec untangles each edge:

1. `ai_engineering.cli_ui -> ai_engineering.updater.service` — Renderer
   wraps `cli_ui` which itself calls `updater.show_status_after_install`.
2. `ai_engineering.updater.service -> ai_engineering.installer.templates`
   — updater inlines installer template helpers.
3. `ai_engineering.policy.checks.stack_runner -> ai_engineering.installer.launchers`
   — stack runner shells out to installer's OS launcher abstraction.
4. `ai_engineering.validator._shared -> ai_engineering.installer.templates`
   — validator resolves template paths during file-existence checks.

Each will invert (or be split via a port) in the follow-up spec.

## Deferred relocations

The following are explicitly OUT OF SCOPE for spec-132 sub-005 and
captured here as the backlog for a follow-up "mass relocation" spec:

- `git mv src/ai_engineering/governance` -> `src/ai_engineering/core/governance`.
- `git mv src/ai_engineering/state` -> `src/ai_engineering/core/state`.
- `git mv src/ai_engineering/policy` -> `src/ai_engineering/core/policy`.
- `git mv src/ai_engineering/validator` -> `src/ai_engineering/core/validator`.
- `git mv src/ai_engineering/cli_commands` -> `src/ai_engineering/adapters/cli`.
- `git mv src/ai_engineering/installer` -> `src/ai_engineering/adapters/installer`.
- `git mv src/ai_engineering/vcs` -> `src/ai_engineering/adapters/vcs`.
- `git mv src/ai_engineering/ide` -> `src/ai_engineering/adapters/ide`.
- `git mv src/ai_engineering/updater` -> `src/ai_engineering/adapters/updater`.
- `git mv src/ai_engineering/issues` -> `src/ai_engineering/adapters/issues`.
- Update ~200 import sites across `src/` and `tests/`.
- Update the four `[[tool.importlinter.contracts]].source_modules` /
  `forbidden_modules` lists to reflect the new physical layout.
- Classify the transitional top-level `cli*.py` modules.

The work is mechanical but voluminous; landing it in a single PR
alongside the spec-132 surface changes is too large to review.

## Spec lifecycle directory schema

`.ai-engineering/specs/` carries the active spec lifecycle workspace
plus the lifecycle artefacts a consumer never edits by hand. Introduced
by spec-132 sub-006 D-132-24. The canonical shape after a fresh
`ai-eng install` is:

```
.ai-engineering/specs/
├── spec.md               # active approved spec (current work)
├── plan.md               # patch-ready plan written by /ai-plan
├── current-summary.md    # one-paragraph synopsis of spec.md
├── history-summary.md    # rolling lifecycle summary
├── task-ledger.json      # plan task state (status/owner/timestamps)
├── evidence/             # /ai-build evidence drops (gitkeep on fresh)
│   └── .gitkeep
└── handoffs/             # cross-skill handoff notes (gitkeep on fresh)
    └── .gitkeep
```

Long-form historical artefacts live in two adjacent paths:

- `.ai-engineering/specs/archive/` is created lazily by
  `spec_lifecycle.py mark_shipped` when the first spec ships; it is NOT
  shipped by the installer.
- `.ai-engineering/specs/drafts/` is created lazily by
  `/ai-brainstorm` for unapproved briefs; it is NOT shipped by the
  installer.
- `_history.md` is owned by `/ai-cleanup` per spec-131 D-131-04. The
  validator downgrades its absence to WARN per spec-132 D-132-09; the
  installer does not ship a stub.

## State directory schema

`.ai-engineering/state/` carries the framework's append-only audit
chain and the SQLite projection used by `audit query`. Introduced by
spec-132 sub-006 D-132-24. The canonical shape after a fresh
`ai-eng install` is:

```
.ai-engineering/state/
├── state.db                          # SQLite single source of truth
├── framework-events.ndjson           # append-only audit stream
├── observation-events.ndjson         # observation telemetry stream
└── locks/
    └── framework-events.lock         # advisory file lock
```

Per spec-132 D-132-08, JSON sidecar files (`ownership-map.json`,
`decision-store.json`, `_OWNERSHIP`, `_DECISIONS`) are NEVER created by
a fresh install. The installer UPSERTs `ownership_map` and `decisions`
rows directly into `state.db` inside one transaction; the legacy JSON
shape is preserved only for backwards-compat reads in
`ai-eng audit index` against historical event streams. spec-132 D-132-07
adds a module-level dedup set in `state_db.py` so any stale-JSON warning
emits at most once per `state.db` lifetime.

Lazily-created entries (not present on fresh install, appear on first
use):

- `runtime/` — session checkpoints, ralph resume markers,
  skills-index cache. Gitignored.
- `gate-findings.json` — emitted by `ai-eng gate run` policy
  orchestrator (spec-104 baseline).
- `hooks-manifest.json` — sha256 pin file generated by hook integrity
  bootstrap when `AIENG_HOOK_INTEGRITY_MODE=enforce`.
- `framework-capabilities.json` — written by `setup` flows that probe
  for optional tooling (gh, ado, brew).
- `install-state.json` — written by installer when previously-installed
  bookkeeping is required (consumer upgrades).
