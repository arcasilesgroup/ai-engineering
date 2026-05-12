---
title: "CLI UX & Cross-IDE Re-architecture — Surface as First-Class Primitive"
status: draft
audience: /ai-brainstorm
chains_after: spec-132 (CLI UX overhaul) — same PR aggregate (#509)
branch: spec-128/context-overrides-refactor
pr: 509
length_estimate: "~1500 lines (deep brief, evidence-anchored)"
authoring_style: "Staff Principal Architect — long-horizon, hexagonal, fail-loud"
principles_required: [KISS, YAGNI, DRY, SOLID, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Single-branch / same-PR / hard-rename / no-shim"
---

# CLI UX & Cross-IDE Re-architecture Brief

> **READ FIRST.** This brief is the contract for `/ai-brainstorm`. It is
> the result of a full evidence-anchored audit (4 parallel `ai-explore`
> dispatches + 1 `/ai-prompt` synthesis pass on 2026-05-12). Every claim
> below cites `file:line`. No hedging, no decoration. The North Star is
> at §2 — every sub-decision must serve it. If a future plan-step
> drifts away from §2, the plan is wrong.
>
> **Scope.** This refactor lives on branch
> `spec-128/context-overrides-refactor` and joins the active **PR #509**
> aggregate (spec-128 + spec-129 + spec-131 + spec-132). No new PR,
> no new branch. Hard renames. No backwards-compat shims (per
> CONSTITUTION + hard-rule §13.3).
>
> **Authoring sigils.** KISS · YAGNI · DRY · SOLID · SDD · TDD ·
> clean-code · hexagonal. Every milestone in §6 cites at least one
> §10.x anchor from `CLAUDE.md`.

---

## 1. Executive Summary (one screen)

ai-engineering installs but **breaks on first skill use** across all 4
official IDEs. The wizard asks 4 questions, two of which are
**conceptually broken** ("AI Providers" vs "IDE integrations" pretend
to be orthogonal — they are not). Antigravity is documented as
"advisory" yet listed in `_KNOWN_IDES`, and OpenCode (a real,
multi-LLM IDE we want to support) has **zero presence** in the
codebase. The CLI exposes overlapping verbs (`ai-eng verify` vs
`/ai-verify`; `ai-eng maintenance branch-cleanup` vs `/ai-cleanup`).
Skills and agents share names (`ai-build` skill + agent) without an
explicit disambiguation contract. 9 root scripts are **referenced by
skills but never deployed** by the installer.

The cure is a **conceptual reframe**: collapse "AI Provider" and
"IDE Integration" into a single first-class domain primitive — the
**Surface** — and rebuild the installer, manifest, wizard, and
mirror-sync around that primitive. Hexagonal layering becomes
enforceable. The wizard collapses to **one or two questions**.
Antigravity and OpenCode become first-class Surfaces. Hard renames
clean up naming smells. Final state is a cohesive, single-mental-model
framework where a new user understands "I pick my Surface(s); the
framework wires the rest."

**Cost.** Estimated 6 milestones, ~30-50 file moves, ~15 new files,
~10 deletions. Single TDD pass (RED → GREEN → REFACTOR per task).
One Phase-5 fail-loud quality loop on the full changeset per D-131-05.

---

## 2. North Star — Final Picture

After this refactor, on a fresh machine, a new engineer types:

```bash
$ ai-eng install
✓ detected: python, github, cwd is empty
? Which IDE Surface(s) do you use? (space to toggle, enter to confirm)
  ❯ ◉ Claude Code     ◯ Codex (OpenAI)   ◯ Gemini CLI
    ◯ GitHub Copilot  ◯ Cursor           ◯ Antigravity
    ◯ OpenCode
✓ installing Surface(s): claude-code
✓ deployed 47 skills, 9 agents, 11 hook events, 9 framework scripts
✓ wired hooks for Claude Code (settings.json)
✓ ready — try `/ai-start` to see the dashboard
```

**Properties of the final state**:

1. **Single primitive — Surface**. No more "AI provider" vs "IDE
   integration" split. A Surface is the unit a user installs. It
   bundles: instruction-file contract, tree-dir, hook-engine, runtime
   capabilities. The user picks Surfaces, not "providers."
2. **One conceptual question.** "Which Surfaces?" — that's the only
   wizard prompt that does not have a deterministic default. Stack is
   auto-detected silently (no question). VCS is auto-detected silently
   (no question, default `github`). IDE-vs-AI-provider as separate
   concepts is **deleted**.
3. **Seven Surfaces supported**: Claude Code, Codex, Gemini CLI, GitHub
   Copilot, Cursor, Antigravity, OpenCode. Each has a complete
   provisioner adapter (file map + tree map + hooks engine + audit
   probe — `hooks_engine` is `None` for the three mirror-only
   Surfaces).
4. **Skills work first try.** All 9 root framework scripts ship in the
   template tree. Every skill that calls
   `uv run python .ai-engineering/scripts/<x>.py` succeeds on a fresh
   install of any Surface — verified by a `pristine-install` smoke
   test across all 6 Surfaces.
5. **Naming is self-describing.** `/ai-gtm`, `/ai-board`, `/ai-eval`,
   `/ai-note`, `/ai-observe`, `/ai-learn`, `/ai-prompt`, `/ai-standup`
   are hard-renamed to verbose, unambiguous slugs. `verify-deterministic`
   agent is renamed to `verifier-deterministic` (pattern parity).
6. **Hex contract is real**. The 4 baseline violations in
   `pyproject.toml:249-265 ignore_imports` are eliminated. The
   adapter↔core boundary is physically enforced. Manifest reads
   route through a `ManifestPort`. CLI adapters do **zero**
   filesystem mutation directly.
7. **Mirrors stay in sync, automatically.** A single
   `scripts/sync_mirrors/core.py` run produces byte-identical Surface
   trees with one Surface-specific extras fence per IDE. Drift is a
   CI failure. `.github/` mirror gap (missing
   `ai-analyze-permissions`) is closed.
8. **One commit per milestone**. SDD. Conventional Commits. Spec
   decisions get IDs `D-<spec>-<NN>` and ship to the decisions table.

If a /ai-plan task does not move us toward this picture, the task is
wrong.

---

## 3. Evidence Catalog — Bugs by ID

Each bug below carries: ID, severity, file:line(s), one-line root
cause, fix sketch. The /ai-plan author MUST keep this list in scope.

### B1 — Root Scripts Orphaned in Templates (CRITICAL, 6 IDEs)

| Script | Live (.ai-engineering/scripts/) | In templates | Skill caller |
|---|---|---|---|
| `session_bootstrap.py` | YES | **NO** | `ai-start` (SKILL.md:30) |
| `spec_lifecycle.py` | YES | **NO** | `ai-brainstorm` (L33,L81), `ai-pr` (L69), `ai-cleanup` (L67,L90,L124,L154) |
| `commit_compose.py` | YES | **NO** | `ai-commit` (L63) |
| `branch_slug.py` | YES | **NO** | `ai-commit` (L28), `ai-pr` (L33) |
| `doc_gate.py` | YES | **NO** | `ai-commit` (L63) |
| `pr_body_compose.py` | YES | **NO** | `ai-pr` (L85) |
| `runtime_rotate.py` | YES | **NO** | `ai-cleanup` (L77,L154) |
| `regenerate-hooks-manifest.py` | YES | **NO** | (installer + dev only) |
| `plan_tasks.py` | YES | **NO** | **orphaned — 0 skill refs** |

**Root cause**: `src/ai_engineering/installer/phases/hooks.py:76-87`
sources only `governance_root/scripts/hooks/` — the root `.py` files
in `.ai-engineering/scripts/` are never copied to the template tree
and never deployed. Result: `/ai-start`, `/ai-commit`, `/ai-pr`,
`/ai-cleanup`, `/ai-brainstorm` all `FileNotFoundError` on first call
in a consumer repo (any Surface).

**Fix sketch (option A — preferred)**: Add scripts to
`src/ai_engineering/templates/.ai-engineering/scripts/` (root + subdirs
`skills/`, `scheduled/`). Extend the installer with a new phase
`ScriptsPhase` (or absorb into governance phase) that deploys the full
`scripts/` tree, not only `hooks/`. Keep `plan_tasks.py` only if a
skill consumer is identified — otherwise **delete** it (YAGNI).

**Why not option B (move to CLI native)**: Would break the
"trusted-script argv lane" D-131-12 contract (hash-pinned scripts
under `hooks-manifest.json`). Templates approach preserves that.

### B2 — Antigravity Not Installable (HIGH)

- `src/ai_engineering/installer/operations.py:15` declares
  `antigravity` in `_KNOWN_IDES` but no provider entry exists in
  `_PROVIDER_FILE_MAPS` (`templates.py:36-51`) or
  `_PROVIDER_TREE_MAPS` (`templates.py:189-205`).
- No `.antigravity/` template directory in
  `src/ai_engineering/templates/project/`.
- `R-131-08` declares Antigravity audit "advisory" because there is
  no stable CLI version probe.
- `capability-matrix.md:25-43` says Antigravity v1.20.3+ reads
  `GEMINI.md` (priority 1) then `AGENTS.md` (fallback). No native
  hook engine.

**Fix sketch**: Add Antigravity as a **mirror-only Surface**. Provider
entry deploys `GEMINI.md` + `AGENTS.md` + (optionally) `.antigravity/`
docs-only tree if Antigravity reads anything from it. **No hook
engine** — document explicitly that hooks are not supported until
Antigravity exposes a deterministic CLI. Mark Surface capability =
`{instruction: yes, tree: docs-only, hooks: no, audit: advisory}`.

### B3 — OpenCode Has Zero Codebase Presence (HIGH)

- `grep -ri opencode .` → 0 hits across templates, manifest, autodetect,
  capability matrix, sync scripts.
- OpenCode (`opencode.ai`, SST-stack) is a multi-LLM terminal IDE.
  Reads `AGENTS.md` and `.opencode/` for prompts/config. No
  deterministic hook engine documented.

**Fix sketch**: Add OpenCode as a **mirror-only Surface** (same shape
as Antigravity initially): provisioner deploys `AGENTS.md` + a minimal
`.opencode/` directory carrying prompts + agent docs. No hook engine
until OpenCode exposes one. Add to `_PROVIDER_POPULARITY`,
`capability-matrix.md`, `evidence-collection.md`, and ai-ide-audit
arg-hint.

### B3b — Cursor Not a Surface (HIGH)

- `cursor` is in `_KNOWN_IDES` (`operations.py:15`) and
  `_IDE_POPULARITY` (`autodetect.py:53`) but has **no provider entry**
  in `_PROVIDER_FILE_MAPS`/`_PROVIDER_TREE_MAPS`. Same shape as B2.
- Cursor (`cursor.com`) since 2025 reads `AGENTS.md` natively (per
  Cursor docs) and `.cursor/rules/*.mdc` for granular project rules.
  Legacy `.cursorrules` single-file is deprecated; use `.cursor/rules/`.
- MCP server config via `.cursor/mcp.json`. No deterministic
  pre/post-tool hook engine in the framework's sense.

**Fix sketch**: Add Cursor as a **mirror-with-rules Surface**:
provisioner deploys `AGENTS.md` + `.cursor/rules/*.mdc` (rules
translated from canonical CLAUDE.md payload + per-skill headers, one
`.mdc` per skill or per topic) + `.cursor/mcp.json` (optional;
deferred unless operator wants ship-day MCP wiring). Hook engine
`None`. Audit capability `advisory`. Add to `_PROVIDER_POPULARITY`,
`capability-matrix.md`, `evidence-collection.md`, ai-ide-audit
arg-hint, and to `_SURFACE_REGISTRY` (M2).

### B4 — Manifest Schema Conflates AI Provider vs IDE (CRITICAL)

- `src/ai_engineering/config/manifest.py:28` defines
  `ProvidersConfig.ides: list[str] = ["claude-code"]`. Wrong type —
  `claude-code` is the AI-Surface ID, not an IDE ID.
- `manifest.yml:15-23` carries TWO orthogonal lists:
  `providers.ides: [terminal, vscode]` and
  `ai_providers.enabled: [claude-code, github-copilot, gemini-cli, codex]`.
  In reality, **a user installs Claude Code (the integrated tool)** —
  they do not pick "claude-code AI provider" + "terminal IDE"
  separately. The split is artificial.
- Wizard `wizard.py:113-145` asks 4 questions across these two axes
  → operator confusion (operator feedback: "esas preguntas están mal
  de principio a fin").

**Fix sketch**: Collapse `providers.ides` + `ai_providers.enabled` →
single `surfaces.enabled: list[str]` carrying Surface IDs from a
closed enum: `{claude-code, codex, gemini-cli, github-copilot,
antigravity, opencode}`. Drop `ai_providers.primary` — there is no
"primary" concept once each Surface is self-contained. Drop the
"IDE integration" notion entirely from the manifest (the user's
underlying editor — VS Code, JetBrains — is not framework-relevant;
the framework only cares about which AI Surface is installed). Hard
schema migration; no shim.

### B5 — Wizard UX Defects (HIGH)

`wizard.py:113-145` asks 4 questions. Defects per question:

| # | Prompt | Defect |
|---|---|---|
| 1 | "Select technology stacks:" | On empty/new repo the user doesn't know yet; on existing repo auto-detect already nailed it. UI overhead. (Operator feedback verbatim.) |
| 2 | "Select AI providers:" | Conceptually wrong (see B4). |
| 3 | "Select IDE integrations:" | Conceptually wrong (see B4). |
| 4 | "Select VCS provider:" | Auto-detect from remote already works; default `github` covers 99% — should be silent unless override. |

**Fix sketch**: Collapse wizard to **one question**: "Which Surface(s)
do you use?" (multi-select). Stack and VCS become **silent
auto-detect**, overridable via `--stack` / `--vcs` CLI flags. If
**all** Surfaces are passed via `--surface`, the wizard is fully
non-interactive (and `--non-interactive` continues to work as a guard).

### B6 — `plan_tasks.py` Orphaned (LOW)

`.ai-engineering/scripts/plan_tasks.py` exists but **zero SKILL.md
references it**. YAGNI: delete it.

### B7 — `/ai-explore` Slash Command Broken (MEDIUM)

`CLAUDE.md` (Token Efficiency section) refers users to `/ai-explore`
for deep codebase research, but no
`.claude/skills/ai-explore/SKILL.md` exists. Only the agent does.
A new user typing `/ai-explore` finds nothing.

**Fix sketch**: Either (a) create `ai-explore` skill as a thin wrapper
that dispatches the agent — clearer mental model for new users; or
(b) update CLAUDE.md to say "dispatch the `ai-explore` agent" and
delete the slash reference. **Pick (a)** for UX consistency: users
discover commands by typing `/ai-` and reading hints; agents are not
discoverable that way.

### B8 — ~~`verify-deterministic` Naming Break~~ (DEFERRED out of scope)

**Decision (operator-locked 2026-05-12)**: Agent naming reform is a
separate concern from CLI verbs. Deferred to the same follow-up spec
as B14. `verify-deterministic` stays as-is for this PR.

### B9 — `ai-eng verify` vs `/ai-verify` Same Name, Different Scope (HIGH UX)

`cli_factory.py:260` registers `ai-eng verify` for the deterministic
gate. `/ai-verify` skill orchestrates the full 4-specialist verification
(deterministic + LLM judgment). Same verb, **incompatible scope**. New
user typing `ai-eng verify --help` gets a tool listing; typing
`/ai-verify` gets a verification orchestrator. **Disambiguate by
renaming** the CLI verb to `ai-eng gate verify` or `ai-eng check`
(merge into existing `ai-eng check`).

### B10 — `ai-eng maintenance branch-cleanup` Duplicates `/ai-cleanup` (HIGH UX)

`cli_factory.py:322` and skill `ai-cleanup` overlap. Same goal, two
entry points. Decide canonical and **delete** the other:

- **Recommend**: keep `/ai-cleanup` skill (carries spec-lifecycle
  awareness, runtime rotation, branch pruning in one cohesive flow).
- **Delete**: `ai-eng maintenance branch-cleanup` (or reduce it to an
  internal helper invoked by the skill — not user-facing).

### B11 — `ai-eng guide` Duplicates `/ai-guide` (LOW UX)

`cli_factory.py:263` exposes `ai-eng guide` as a query command;
`/ai-guide` is an interactive onboarding skill. Different shapes
sharing a name.

**Decision (operator-locked 2026-05-12)**: **DELETE** `ai-eng guide`
entirely. No rename, no backward-compat shim. `/ai-guide` is the
canonical entry point for onboarding/architecture tours. Hard removal
per CONSTITUTION + hard-rule §13.3.

### B12 — `ai-analyze-permissions` Is Claude-Only (MEDIUM, classification fix)

`.github/skills/` has 46 SKILL.md vs `.claude/skills/` 47. Originally
classified as drift; **operator-clarified 2026-05-12**: this is **by
design** — `ai-analyze-permissions` audits Claude Code
`settings.local.json` and has no analogue in Codex, Gemini CLI,
GitHub Copilot, Cursor, Antigravity, or OpenCode.

**Fix sketch**:
1. Codify the filter explicitly in `scripts/sync_mirrors/core.py` —
   add an allowlist/blocklist mechanism keyed by Surface ID:
   `SKILL_SURFACE_RESTRICTIONS = {"ai-analyze-permissions":
   {"claude-code"}}`. Skip mirror copy when target Surface is not in
   the set.
2. Update the skill's SKILL.md frontmatter with a
   `applies_to_surfaces: [claude-code]` field so the restriction is
   self-documented at source (not buried in the sync script).
3. Update `tools/skill_lint/checks/md_mirror.py` to **exclude**
   restricted skills from sha256 parity checks (so mirror count
   asymmetry no longer fails CI).
4. Update `tests/mirrors/test_skill_count_parity.py` (if exists) to
   expect: `count(.claude/) == 47`, `count(.codex/) == count(.gemini/)
   == count(.github/) == count(.cursor/rules/) == count(.opencode/)
   == count(.antigravity/) == 46` (each = 47 minus the
   claude-only restricted set).
5. Document the pattern in `CLAUDE.md` §14 (Strict Content Contracts)
   under a new bullet: "Per-Surface skill restrictions are declared
   in SKILL.md frontmatter via `applies_to_surfaces`; sync_mirrors
   skips restricted entries."

### B13 — Hexagonal Contract Violations (HIGH)

4 baseline violations whitelisted in `pyproject.toml:249-265
ignore_imports`:

1. `cli_ui -> updater.service`
2. `updater.service -> installer.templates`
3. `policy.checks.stack_runner -> installer.launchers`
4. `validator._shared -> installer.templates`

Plus 6 in-band violations in CLI adapters:
- `core.py:366-381` — `sqlite3.connect(db_path)` inside CLI callback
  (`_is_reinstall`).
- `core.py:344` — raw `print(json.dumps(...))` bypassing UI layer.
- `core.py:519-557` — `typer.echo` + `typer.prompt` + business logic
  + `typer.Exit` interleaved (`_confirm_fresh_reinstall`,
  `_confirm_reconfigure`, `_confirm_repair`).
- `spec_cmd.py:133` — `click.echo(ctx.get_help())` direct.
- `spec_cmd.py:84` — `plan_path.write_text(...)` filesystem write
  inside CLI helper.
- `audit_cmd.py:38` — `import sqlite3` at module level; raw
  `conn.execute()` SQL throughout.

**Fix sketch**: Introduce ports in the domain layer:
- `ManifestPort` (read manifest values without importing
  `state.manifest`).
- `OutputPort` (CLI writes go through one interface; rich-console
  adapter implements it).
- `ConfirmPort` (interactive confirms abstracted).
- `AuditStorePort` (audit query layer abstracted; sqlite3 adapter
  lives in `infrastructure/`).

CLI adapters take a port at construction and call `.read(...)` /
`.emit(...)` / `.confirm(...)`. The 4 whitelisted violations are
removed; the in-band violations are unwound by the same port
introduction. Architecture test (`tests/architecture/test_hexagonal.py`)
should run with **empty** `ignore_imports`.

### B14 — ~~Naming Smells~~ (DEFERRED out of scope)

**Decision (operator-locked 2026-05-12)**: Skill + agent naming reform
is **out of scope** for this spec. CLI verb renames/deletions (B9,
B10, B11) stay in scope — those are a different surface with
different blast radius. Skill + agent renames are a separate concern
deferred to a follow-up spec.

Original cohesion-audit list (preserved for the deferred spec):
`ai-gtm`, `ai-board`, `ai-eval`, `ai-note`, `ai-simplify-sweep`,
`ai-observe`, `ai-learn`, `ai-prompt`, `ai-standup`,
`verify-deterministic` (agent). Out of scope here.

### B15 — `--stack` Flag UX Mismatch (LOW)

`core.py:103` accepts `--stack/-s` repeatable. Wizard prompt
overrides it (B5 fix). After B5, `--stack` becomes the **only**
non-auto-detect path. Document it explicitly in `ai-eng install
--help`.

---

## 4. Architectural Vision — Surface as First-Class Primitive

A **Surface** is the framework's only IDE/AI domain primitive. It has
five capabilities, declared once per Surface:

```python
# src/ai_engineering/domain/surface.py  (NEW)
@dataclass(frozen=True)
class Surface:
    id: str                          # "claude-code", "antigravity", ...
    display_name: str                # "Claude Code", "Antigravity"
    instruction_files: tuple[InstructionFile, ...]   # CLAUDE.md, AGENTS.md, ...
    tree_dir: Path | None            # .claude/, .codex/, .gemini/, .github/, .opencode/, None
    hook_engine: HookEngine | None   # "claude", "codex", "gemini", "copilot", None
    audit_capability: AuditLevel     # "deterministic" | "advisory" | "none"
    autodetect_marker: Marker | None # dir or file that signals presence
```

```python
# src/ai_engineering/domain/ports.py  (NEW)
class ManifestPort(Protocol):
    def read_surfaces(self) -> tuple[Surface, ...]: ...
    def read_stacks(self) -> tuple[Stack, ...]: ...
    def read_vcs(self) -> Vcs: ...

class SurfaceProvisionerPort(Protocol):
    def deploy(self, surface: Surface, target: Path) -> DeployReport: ...
    def reconfigure(self, surface: Surface, target: Path) -> ReconfigureReport: ...

class OutputPort(Protocol):
    def emit(self, payload: OutputEvent) -> None: ...
    def prompt(self, question: PromptSpec) -> PromptAnswer: ...

class AuditStorePort(Protocol):
    def list_decisions(self, where: DecisionFilter) -> tuple[Decision, ...]: ...
```

**Layering** (all moves are hard, no shim):

```
src/ai_engineering/
  domain/              # NEW — pure
    surface.py         # Surface, AuditLevel, HookEngine enums
    manifest_value.py  # value objects
    ports.py           # ManifestPort, ProvisionerPort, OutputPort, AuditStorePort
  application/         # NEW — use cases
    install_surfaces.py
    reconfigure_surface.py
    audit_surfaces.py
  adapters/            # was cli_commands/, installer/, vcs/, ide/, etc.
    cli/               # Typer adapter; depends only on OutputPort + use cases
    installer/         # provisioner adapters per Surface
    storage/           # sqlite + manifest adapter; implements AuditStorePort + ManifestPort
    hooks/             # hook engines (claude, codex, gemini, copilot)
```

**Dependency direction**: `cli` → `application` → `domain` ← `storage`
← `installer`. Import-linter contract drops the 4 baseline ignores;
`tests/architecture/test_hexagonal.py` passes with empty whitelist.

---

## 5. Conceptual Reframe Table

| Old concept | Status | Replaced by | Rationale |
|---|---|---|---|
| AI Provider | DELETED | Surface | Conflated with IDE; "claude-code AI provider" was never separable from "Claude Code IDE" |
| IDE Integration | DELETED | Surface | `terminal` is not an IDE; `vscode` and `jetbrains` are user editors orthogonal to framework wiring |
| `providers.ides: list` | DELETED | — | Carries `terminal/vscode/jetbrains` — none of which the framework wires |
| `ai_providers.enabled` | RENAMED | `surfaces.enabled` | Single list of Surface IDs |
| `ai_providers.primary` | DELETED | — | YAGNI; no consumer of "primary AI" |
| `providers.vcs` | KEPT | `vcs.detected` | Auto-detect from git remote; user override via `--vcs` flag |
| `providers.stacks` | KEPT | `stacks.detected` | Auto-detect from marker files; user override via `--stack` flag. Stack concept stays (real consumers: doctor, policy, tools). |
| 4 wizard prompts | COLLAPSED | 1 wizard prompt: "Which Surface(s)?" | KISS + YAGNI |

---

## 6. Roadmap — 6 Milestones

Each milestone is an atomic commit shipped to PR #509. TDD per task.
Principles cited per milestone.

### M1 — Templates: Deploy Root Framework Scripts (B1)

**Apply**: §10.5 (TDD), §10.6 (SDD)
**Why**: Skills break on first call in any consumer repo. Highest
ROI fix.

**Tasks**:
1. RED — write
   `tests/unit/installer/test_phases_scripts_deploy.py` asserting
   that after `phases.run`, the target `.ai-engineering/scripts/`
   contains all 8 root scripts (no `plan_tasks.py`).
2. GREEN — copy
   `session_bootstrap.py, spec_lifecycle.py, commit_compose.py,
   branch_slug.py, doc_gate.py, pr_body_compose.py, runtime_rotate.py,
   regenerate-hooks-manifest.py` into
   `src/ai_engineering/templates/.ai-engineering/scripts/`.
3. Update `installer/phases/hooks.py` (or new `phases/scripts.py`) to
   deploy the full `scripts/` tree, not only `hooks/`.
4. Add a `pristine-install smoke test` for each Surface — calls
   `/ai-start`'s exact argv and asserts exit 0.
5. **DELETE** `plan_tasks.py` (orphaned, B6).
6. REFACTOR — extract shared template-copy helper if extraction
   reveals a duplicate.

**Acceptance**:
- `pytest tests/unit/installer/test_phases_scripts_deploy.py` green.
- Manual: `ai-eng install` into `/tmp/probando` and run
  `uv run python .ai-engineering/scripts/session_bootstrap.py
  --format=markdown` → exit 0.

### M2 — Domain Layer: Surface Primitive + Ports (B4, B13)

**Apply**: §10.3 (SOLID/DIP), §10.8 (Hex)
**Why**: Foundation for every downstream rename and adapter rewrite.

**Tasks**:
1. RED — write
   `tests/unit/domain/test_surface.py` asserting Surface equality,
   capability flags, autodetect-marker shape, immutability.
2. RED — write
   `tests/unit/domain/test_ports.py` asserting port protocols (just
   `isinstance(impl, Protocol)` round-trips).
3. GREEN — create `src/ai_engineering/domain/{surface,ports,
   manifest_value}.py`.
4. Encode the 6 official Surfaces as a `_SURFACE_REGISTRY` constant in
   `domain/surface.py`. Each entry: id, display_name, instruction
   files, tree_dir, hook_engine, audit_capability, autodetect_marker.
5. REFACTOR — no infrastructure imports in domain (import-linter
   enforced).

**Acceptance**:
- `lint-imports` passes with the new `domain` package added to
  `core` group.
- New domain package has 0 transitive imports of `installer`, `state`,
  `cli_commands`.

### M3 — Adapters: Surface Provisioner per Surface (B2, B3, B3b, B12)

**Apply**: §10.1 (KISS), §10.4 (DRY), §10.8 (Hex)
**Why**: Antigravity + OpenCode + Cursor become first-class; the
per-IDE file_map / tree_map duplication in `templates.py:36-205`
collapses into one generic provisioner driven by the Surface registry.

**Tasks**:
1. RED — `tests/unit/adapters/installer/test_surface_provisioner.py`
   asserts each of 7 Surfaces deploys its declared instruction files
   and tree dir into the target, with no dest collisions.
2. RED — `tests/unit/adapters/installer/test_antigravity_surface.py`
   asserts GEMINI.md + AGENTS.md deploy; tree_dir is optional
   (docs-only); hook_engine is None.
3. RED — `tests/unit/adapters/installer/test_opencode_surface.py`
   asserts AGENTS.md + `.opencode/` deploy; hook_engine is None.
4. RED — `tests/unit/adapters/installer/test_cursor_surface.py`
   asserts AGENTS.md + `.cursor/rules/*.mdc` deploy; legacy
   `.cursorrules` NOT written; hook_engine is None;
   audit_capability is advisory.
5. GREEN — implement `SurfaceProvisioner` adapter that reads
   `Surface` and copies files; replace `_PROVIDER_FILE_MAPS` and
   `_PROVIDER_TREE_MAPS` (delete them) with a registry-driven loop.
6. Add `.antigravity/` (docs-only), `.opencode/`, and `.cursor/rules/`
   template trees under `src/ai_engineering/templates/project/`. The
   `.cursor/rules/` tree carries one `.mdc` per canonical CLAUDE.md
   topic (§10 principles, hot-path discipline, hooks summary) plus
   one `.mdc` per skill (regenerated from `.claude/skills/<name>/
   SKILL.md` by `scripts/sync_mirrors/core.py`).
7. Update `capability-matrix.md`, `evidence-collection.md`,
   `ai-ide-audit/SKILL.md` `argument-hint` to include
   `antigravity|opencode|cursor`.
8. Codify per-Surface skill restrictions (B12). Add
   `applies_to_surfaces: [claude-code]` to
   `.claude/skills/ai-analyze-permissions/SKILL.md` frontmatter.
   Extend `scripts/sync_mirrors/core.py` with restriction-aware
   filtering. Update `tools/skill_lint/checks/md_mirror.py` + mirror
   parity tests to expect 46 on non-Claude Surfaces.

**Acceptance**:
- 7 Surfaces installable standalone — verified by smoke matrix
  (`tests/integration/installer/test_install_per_surface.py`).
- `.claude/skills/` count = 47 (canonical, includes
  `ai-analyze-permissions`).
- `.codex/`, `.gemini/`, `.github/`, `.cursor/rules/`, `.opencode/`,
  `.antigravity/` skill counts = 46 (each = 47 minus Claude-only
  restricted set).
- `.cursor/rules/` carries the 46 cross-Surface skills as `.mdc`
  files plus canonical CLAUDE.md-derived topic rules.

### M4 — Wizard + CLI: Collapse to Surface (B5, B9, B10, B11, B15)

**Apply**: §10.1 (KISS), §10.2 (YAGNI), §10.7 (Clean Code)
**Why**: User-facing UX is the highest-leverage daily-pain surface.

**Tasks**:
1. Delete `wizard.py` prompts for stack, providers, ides separately.
   Replace with **single multi-select** "Which Surface(s) do you
   use?" populated from `Surface._SURFACE_REGISTRY`. Pre-selected
   from autodetect.
2. Stack auto-detect remains silent; `--stack` flag preserved as
   override. VCS auto-detect remains silent; `--vcs` flag preserved.
3. Delete `--ide` and `--provider` flags from `install_cmd`
   (`core.py:103-110`). Add `--surface/-S` (repeatable) replacing
   both. Hard rename.
4. Rename `ai-eng verify` → `ai-eng gate verify` (or merge into
   `ai-eng check`). Decision deferred to /ai-brainstorm.
5. Delete `ai-eng maintenance branch-cleanup` (B10); `/ai-cleanup`
   becomes the only entry point.
6. **Delete** `ai-eng guide` command (B11). No replacement,
   no shim. Remove registration from `cli_factory.py:263` and the
   handler file. `/ai-guide` skill is the only entry point.
7. Update help-text + golden snapshots
   (`tests/unit/cli/test_help_snapshots.py` or equivalent).

**Acceptance**:
- New wizard golden snapshot: 1 question, not 4.
- `ai-eng install --surface claude-code --non-interactive` works
  end-to-end into a temp dir.
- `ai-eng install --help` shows `--surface/-S`, NOT `--provider/-p` or
  `--ide/-i`.

### M5 — Manifest Schema Migration (B4)

**Apply**: §10.4 (DRY), §10.6 (SDD), §13.3 (no shim)
**Why**: Removes the conceptual root cause of B4 + B5.

**Tasks**:
1. RED —
   `tests/unit/config/test_manifest_surface_schema.py` asserts new
   `surfaces.enabled` field round-trips.
2. GREEN — `src/ai_engineering/config/manifest.py`:
   - Add `SurfacesConfig(enabled: list[str])`.
   - Delete `AiProvidersConfig` entirely.
   - Delete `ProvidersConfig.ides` field.
   - Keep `ProvidersConfig.stacks` and `ProvidersConfig.vcs`.
3. Migrate the framework's own `.ai-engineering/manifest.yml` to new
   schema (hard rewrite).
4. Update `validator/categories/required_tools.py:R-15` to operate on
   `stacks` directly (unchanged behavior).
5. Update OPA bundle + decision-store schema for `surfaces.enabled`
   (D-129-xx) where it references manifest provider keys.
6. CHANGELOG entry documenting the hard break.

**Acceptance**:
- `ai-eng doctor` on the framework repo itself shows zero
  manifest-related findings.
- `cat .ai-engineering/manifest.yml` shows `surfaces.enabled: [...]`,
  no `ai_providers`, no `providers.ides`.

### M6 — Naming Reform + Hex Cleanup (B8, B14, B13)

**Apply**: §10.7 (Clean Code), §10.8 (Hex)
**Why**: Closes naming smells and brings the hex contract to
zero-whitelist.

**Tasks**:
1. Hard rename 10 names per B14 table. For each:
   - Move `.claude/skills/<old>/` → `.claude/skills/<new>/`.
   - Update `SKILL.md` `name:` frontmatter.
   - Update all cross-references in other skills, agents, CLAUDE.md,
     CONSTITUTION.md, manifest counters, decision-store entries.
   - `scripts/sync_command_mirrors.py` propagates to .codex/.gemini/.github/.
   - Add entry to CHANGELOG breaking-changes section.
2. Verifier-deterministic agent rename (B8).
3. Create `ai-explore` skill (B7) — thin wrapper that dispatches the
   agent.
4. Eliminate 4 hex baseline violations in
   `pyproject.toml:249-265 ignore_imports`:
   - `cli_ui -> updater.service`: route updater through OutputPort.
   - `updater.service -> installer.templates`: extract a
     `TemplateRegistryPort`.
   - `policy.checks.stack_runner -> installer.launchers`: extract
     `LauncherPort`.
   - `validator._shared -> installer.templates`: same `TemplateRegistryPort`.
5. Eliminate 6 in-band CLI hex violations (B13).
6. RED — re-run `tests/architecture/test_hexagonal.py` with empty
   `ignore_imports`; assert exit 0.

**Acceptance**:
- 47-skill / 9-agent count unchanged (the renames are 1:1).
- `pyproject.toml` `ignore_imports` block is empty (or contains only
  explicitly documented externally-enforced exceptions).
- `python scripts/sync_command_mirrors.py --check` exits 0.

---

## 7. Naming Convention Reform — Full Rename Map

| Old skill | New skill | Old agent | New agent |
|---|---|---|---|
| `ai-gtm` | `ai-go-to-market` | — | — |
| `ai-board` | `ai-project-board` | — | — |
| `ai-eval` | `ai-reliability-eval` | — | — |
| `ai-note` | `ai-discovery-notes` | — | — |
| `ai-simplify-sweep` | `ai-simplify-scheduled` | — | — |
| `ai-observe` | `ai-session-observe` | — | — |
| `ai-learn` | `ai-learn-from-reviews` | — | — |
| `ai-prompt` | `ai-prompt-optimize` | — | — |
| `ai-standup` | `ai-standup-report` | — | — |
| — | — | `verify-deterministic` | `verifier-deterministic` |

CLI verb renames:
| Old | New | Reason |
|---|---|---|
| `ai-eng verify` | `ai-eng gate verify` | Disambiguate from `/ai-verify` skill |
| `ai-eng maintenance branch-cleanup` | (DELETED — use `/ai-cleanup`) | Duplicate |
| `ai-eng guide` | (DELETED — use `/ai-guide` skill) | Duplicate; operator-locked deletion 2026-05-12 |
| `--provider/-p`, `--ide/-i` (install) | `--surface/-S` | Conceptual collapse |

---

## 8. Principles Application Matrix

| Principle | Applied in | Anti-pattern eliminated |
|---|---|---|
| **KISS (§10.1)** | M4 (1 wizard prompt), M6 (hex zero-whitelist) | 4-question wizard, 4 ignore_imports |
| **YAGNI (§10.2)** | M1 (delete `plan_tasks.py`), M5 (delete `ai_providers.primary`) | Dead code |
| **DRY (§10.4)** | M3 (one provisioner driven by registry; no more per-IDE file_map dicts) | `_PROVIDER_FILE_MAPS` + `_PROVIDER_TREE_MAPS` duplication |
| **SOLID (§10.3)** | M2 (ports + protocols), M6 (port-based decoupling) | Direct sqlite3 / typer / print in CLI |
| **TDD (§10.5)** | Every milestone RED-first | After-the-fact coverage |
| **SDD (§10.6)** | Brief→spec→plan→build; D-<spec>-<NN> decisions for each break | Drive-by changes |
| **Clean Code (§10.7)** | M4 + M6 (renames, function-size in CLI confirm helpers) | 30+ line callbacks mixing I/O + business |
| **Hexagonal (§10.8)** | M2 + M3 + M6 (domain/application/adapters split; ports) | adapter→adapter direct imports, hex contract whitelist |

---

## 9. Risk Register & Rollback Strategy

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Manifest schema break orphans existing `.ai-engineering/manifest.yml` in consumer repos | Medium | High | Document in CHANGELOG; `ai-eng install --reconfigure` re-runs wizard against new schema. **No shim** — hard break per spec-128 §13.3. Operator on PR #509 is the only consumer until release. |
| Hard renames break downstream tooling (Engram lookups, decision IDs) | Medium | Medium | Update decision-store entries in same commit as rename. Add CHANGELOG-breaking section. Sync mirrors run idempotently as part of acceptance. |
| Antigravity/OpenCode/Cursor provisioners might be wrong without external CLI probes | High | Low | Document each as advisory (`audit_capability: advisory`). No hook engine. R-131-08 carries forward as R-133-XX. |
| Cursor `.cursor/rules/*.mdc` format may evolve before ship | Medium | Low | Pin to current `.mdc` schema (front-matter + body); regenerate from skills on every sync; operator can opt out via `--surface` exclusion. |
| Sub-agent dispatch in `/ai-review` and `/ai-verify` references old `verify-deterministic` name | High | Low | Grep-and-replace covers all references in the rename commit; tests assert dispatch round-trip. |
| Hex extraction inadvertently breaks installer hot-path (the 4 whitelisted edges may be load-bearing) | Medium | Medium | M6 is the **last** milestone — the 5 prior have green tests; hex extraction only refactors layout, not behavior. Per-milestone `pytest` gate. |

Rollback: any milestone is a single commit. `git revert` per-commit
is the rollback unit. No data migrations beyond the manifest hard
schema break (M5) which is operator-acknowledged.

---

## 10. Test Strategy

Per principle §10.5 TDD: every code-bearing task starts with a failing
test.

**New test packages**:
- `tests/unit/domain/test_surface.py`
- `tests/unit/domain/test_ports.py`
- `tests/unit/adapters/installer/test_surface_provisioner.py`
- `tests/unit/adapters/installer/test_antigravity_surface.py`
- `tests/unit/adapters/installer/test_opencode_surface.py`
- `tests/unit/config/test_manifest_surface_schema.py`
- `tests/integration/installer/test_install_per_surface.py` (6-Surface
  smoke matrix)
- `tests/unit/installer/test_phases_scripts_deploy.py`

**Updated**:
- `tests/architecture/test_hexagonal.py` — strip `ignore_imports`
  whitelist.
- `tests/unit/installer/test_wizard.py` — wizard golden snapshot:
  1 question.
- `tests/unit/cli/test_help_snapshots.py` — `--surface`, no
  `--provider`, no `--ide`.
- `tests/mirrors/test_skill_count_parity.py` (if exists) — `.github/`
  matches `.claude/`.

**Acceptance gate per milestone**: `uv run pytest tests/` 100% green,
`lint-imports` 0 violations, `ruff check .` 0 errors,
`python scripts/sync_command_mirrors.py --check` idempotent,
`python -m spec_lint --check .ai-engineering/specs/spec.md` BLOCKERS=0.

Final spec-level gate: full `pytest tests/` plus a manual
`ai-eng install` into a clean tmp dir per Surface, calling
`/ai-start` and confirming exit 0.

---

## 11. Out of Scope (documented to prevent scope creep)

- **No new skills.** No new agents. (Except: `ai-explore` SKILL.md to
  fix B7 — that's a B-fix, not a new capability.)
- **No new hook events.** The 11 canonical events stay.
- **No spec-129 / spec-131 / spec-132 retrofit**. Those shipped; this
  spec extends, doesn't rewrite.
- **No physical layer relocation beyond what M2-M6 require.**
  Aggressive folder rearrangement is deferred to a follow-up spec
  (`spec-128/context-overrides-refactor` already shipped most of the
  contexts/overrides moves).
- **No support for JetBrains-as-Surface, terminal-as-Surface, Aider,
  Continue, etc.** Those are user editors without an instruction
  surface the framework can drive. Add them only when an operator
  request lands. (Cursor is supported as of this spec — see B3b
  + M3.)
- **No backwards-compat shims** for the manifest schema break (M5).
  Hard break, CHANGELOG documented.

---

## 12. Open Questions for `/ai-brainstorm`

`/ai-brainstorm` MUST interrogate the operator on these before
producing spec.md:

1. **`ai-eng verify` rename**: collapse into existing `ai-eng check`,
   or move under `ai-eng gate verify`? Operator preference + downstream
   doc impact.
2. ~~**`ai-eng guide` rename**~~ — **RESOLVED 2026-05-12**: command
   DELETED entirely; `/ai-guide` skill is canonical. No question.
3. **Stack concept (Level A vs B from feedback)**: Level A (delete
   wizard prompt only, keep concept) is recommended in §6 M4. Confirm
   operator does not want Level B (delete concept entirely).
4. **`/ai-cleanup` vs `ai-eng maintenance`**: confirm `/ai-cleanup`
   wins (recommended). If operator wants `ai-eng maintenance` retained
   for scriptability, both stay but with a clear seam (skill = UX,
   CLI = scripting).
5. **OpenCode `.opencode/` tree contents**: confirm operator wants
   AGENTS.md + skills/agents docs only (no executable hook engine),
   matching Antigravity's mirror-only Surface shape.
6. **Cursor `.cursor/rules/` granularity**: confirm one `.mdc` per
   skill (regenerated from `.claude/skills/<name>/SKILL.md`) plus
   topic-level rules from canonical CLAUDE.md. Alternative: a single
   `.mdc` carrying the full canonical payload + per-skill anchors —
   simpler but loses Cursor's per-rule selective application. Default
   recommended: granular (one-per-skill).
7. **Cursor MCP wiring (`.cursor/mcp.json`)**: deploy on ship day, or
   defer to follow-up? Default recommended: defer (out-of-scope unless
   operator wants it explicitly).
8. **`ai-explore` skill (B7)**: confirm (a) thin-wrapper skill
   approach over (b) CLAUDE.md doc fix.
9. **Naming reform**: confirm the 10 renames in §7. Operator has veto
   per name — surface preferences before the spec locks in.

---

## 13. Definition of Done (spec-level)

- All 16 bugs in §3 (B1-B15 + B3b) closed with file:line evidence
  in PR body.
- All 6 milestones in §6 shipped as atomic commits to branch
  `spec-128/context-overrides-refactor` (joining PR #509).
- New domain + application + adapter layout in place; import-linter
  whitelist empty.
- Manifest schema migrated; framework's own `.ai-engineering/
  manifest.yml` rewritten.
- All 7 Surfaces install standalone — verified by integration smoke
  test.
- Mirror counts per Surface: `.claude/` = 47 canonical; `.codex/`,
  `.gemini/`, `.github/`, `.cursor/rules/`, `.opencode/`,
  `.antigravity/` = 46 each (47 minus Claude-only
  `ai-analyze-permissions`). Restriction declared via
  `applies_to_surfaces` SKILL.md frontmatter (B12).
- 47-skill + 9-agent count preserved on `.claude/` canonical (renames
  are 1:1; no count change).
- CHANGELOG entry documenting:
  - manifest schema break (M5)
  - 10 hard renames (M6)
  - 3 CLI verb renames + 2 CLI verb deletions (M4)
  - new Surface registry (M2)
- Phase-5 fail-loud quality loop green on the full PR #509 changeset
  (D-131-05 contract).
- Decision-store rows `D-<spec>-01..NN` written for each binding
  decision.

---

## 14. Naming Anchor (for /ai-brainstorm spec.md)

Suggested spec.md frontmatter:

```yaml
---
spec_id: spec-133            # /ai-brainstorm picks next number
title: "Surface Primitive Re-architecture (CLI UX + Cross-IDE)"
status: approved             # after operator review
effort: high
chains_after: spec-132
branch: spec-128/context-overrides-refactor
pr: 509
---
```

---

*End of brief.* Hand this file to `/ai-brainstorm`. The brainstorm
phase MUST cover §12 questions before locking spec.md.
