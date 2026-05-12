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
