# CLI UX & Architecture Overhaul — Brief for Spec / Plan

> **Status:** Draft brief, ready for `/ai-brainstorm` → `/ai-plan` decomposition.
> **Branch:** `feat/spec-126-hook-ndjson-lock-parity` (current).
> **PR:** [#506](https://github.com/.../pull/506) — this work lands as part of the active PR; no new branch.
> **Audience:** ai-engineering implementation agents (build, plan, review, verify).
> **North Star:** First-time user runs `ai-eng install` on an empty repo and never feels confused, never sees noise, never hits a hidden failure mode. Every command shows what it is doing, why, and what changed.

---

## 1. Vision (Final Picture — Keep Visible Through Every Commit)

A staff-principal CI architect (200-engineer org) and a designer would say:

> "The CLI is **self-describing, observable, idempotent, and honest**. Naming reveals intent. Output reveals action. Errors reveal recovery. No legacy duplication. No silent state drift. No commands that exist only for internal maintenance. Architecture is hexagonal: domain (governance, state, sync) is decoupled from delivery (CLI, hooks, IDE adapters)."

Concretely, after this work:

1. `ai-eng <noun>` with no args **always prints help**, never errors with `Missing argument`.
2. Every mutating command shows a **before / action / after** diff: *Installing X*, *Updating Y*, *Removing Z*, *Moved A → B*.
3. Every command surface is **one of three types**, clearly tagged:
   - **Lifecycle** (install, update, doctor, gate, release) — public, user-facing.
   - **Inspection** (status, list, show) — read-only, safe.
   - **Maintenance** (sync, validate-mirrors) — hidden behind `ai-eng dev *` or removed from the public surface.
4. There is **exactly ONE** validation command, **ONE** quality command, **ONE** state truth (state.db). No `audit` vs `verify` vs `validate` confusion.
5. Freshly installed project has **zero warnings, zero failures**, full sync.
6. Naming follows: `ai-eng <noun> <verb>` (resource-action), short, pronounceable, no jargon (`spec activate --specs-dir <path>` becomes `ai-eng spec start <path>`).

---

## 2. Raw Feedback — Categorized & Triaged

### 2.1 P0 — Bugs & Broken Promises (must fix in PR-506)

| # | Symptom | Root cause hypothesis | Acceptance |
|---|---------|----------------------|------------|
| B1 | "stale state JSON fallback" warning printed **34×** during `install`, repeats on every `doctor`, `update`, `guide`, `vcs status`, `work-item sync`. | **Confirmed.** Emitter `_warn_on_deprecated_fallbacks` at `src/ai_engineering/state/state_db.py:172-194`, called unconditionally from `connect()` line 168 on every non-read-only connect. Install does **17 connect() calls × 2 stale files = 34**. **No dedup exists.** Worse: installer **self-creates** the files it warns about at `src/ai_engineering/installer/phases/state.py:117-121` via `write_json_model` for `_OWNERSHIP` + `_DECISIONS`. | Two-part fix: **(a)** dedup set `_warned_fallbacks: set[Path]` at `state_db.py:~63` checked inside loop at line 183; **(b)** stop writing JSON in `installer/phases/state.py:117-121`, UPSERT to `ownership_map` + `decisions` tables in state.db instead. Tests to update: `tests/unit/state/test_state_db_fallback_warning.py:46-78`, `tests/unit/specs/test_state_canonical.py:107-121`, `tests/unit/installer/test_phases.py:314-327`. Acceptance: zero spurious warnings on fresh install. |
| B2 | `ai-eng install` **hangs** after answering `y` to "Install Engram for memory persistence?". | **Confirmed root cause** (`src/ai_engineering/installer/engram.py:153`, `:348`; `src/ai_engineering/cli_commands/core.py:304`, `:794`): (1) `subprocess.run()` has **no `timeout=`**; (2) `capture_output=True` creates pipe-buffer deadlock when brew output is large and unread; (3) **wrong brew formula** — code does `brew install engram` but the real formula is `brew install --cask gentleman-programming/tap/engram`; (4) `step_progress` exits before subprocess starts, no spinner during the actual hang; (5) bare `except Exception` at `core.py:794` silently swallows failures. | Add `timeout=180`, drop `capture_output` for streaming or use `Popen` w/ readers, fix the brew formula, wrap in spinner during subprocess, narrow exception, fail-open w/ "skipped: <reason> — continue without memory". |
| B3 | Two `CONSTITUTION.md` files (root + `.ai-engineering/`) — reported many times, still ships. | **Refined.** Four copies actually exist: (i) root `CONSTITUTION.md` (277 lines, source-repo governance law, NOT shipped, correct); (ii) `.ai-engineering/CONSTITUTION.md` (113 lines, **divergent stub, no architectural role**); (iii) `src/ai_engineering/templates/project/CONSTITUTION.md` (229 lines, project-charter template); (iv) `src/ai_engineering/templates/.ai-engineering/CONSTITUTION.md` (79 lines, minimal stub). Installer ships the project-charter template to BOTH consumer root AND consumer `.ai-engineering/` per `templates.py:171-184` — that is the duplication users see. | **Delete source-repo `.ai-engineering/CONSTITUTION.md` (113-line stub)** — redundant. Decide installer policy: ship project-charter template to ONE consumer location only (likely root), not both. Add CI invariant test: exactly one `CONSTITUTION.md` per consumer install. |
| B4 | Fresh install fails `ai-eng validate`: missing `_history.md`, broken `ai-governance` cross-refs to `src/ai_engineering/governance/opa_runner.py`, `decision_log.py`, `policy/checks/opa_gate.py`, `doctor/runtime/opa_health.py`, `ai-mcp-sentinel` → `IOCS_ATTRIBUTION.md`. | **Refuted in part — validator bug.** Files (1)-(4) **all exist** in source repo (`opa_runner.py`, `decision_log.py`, `policy/checks/opa_gate.py`, `doctor/runtime/opa_health.py`). Bug is in `src/ai_engineering/validator/categories/file_existence.py:_reference_exists()`: it scans `.claude/skills/*.md` and resolves `src/...` paths from consumer-project root, where `src/` does not exist by design (it is the source-repo's implementation tree, not a consumer artifact). **Confirmed real misses**: `IOCS_ATTRIBUTION.md` is genuinely missing from `src/ai_engineering/templates/.ai-engineering/references/` (only `iocs.json` ships); `_history.md` is absent because validator at `validator/categories/file_existence.py:228-256` `_record_spec_buffer_result` HARD-FAILs without a fresh-install exemption (file is a progressive artifact). | **Three patches:** (i) validator `_should_skip_reference_path()` skips `src/ai_engineering/...` in SKILL.md (those are LLM impl notes, not consumer files); (ii) add `IOCS_ATTRIBUTION.md` to `src/ai_engineering/templates/.ai-engineering/references/`; (iii) either ship empty `_history.md` stub in template tree or downgrade missing `_history.md` to WARN when `spec.md` + `plan.md` present. Acceptance: fresh install passes `ai-eng check` (was: `validate`) + `ai-eng verify governance` ≥ 95. |
| B5 | `ai-eng update` immediately after `install` reports **2 files updated** (`AGENTS.md`, `.github/skills/ai-eval/SKILL.md`). | Installer ships stale templates or update detection is wrong. | After `install`, `update --check` reports 0 changes. |
| B6 | `ai-eng sync` (without `--check`) errors `Sync script not found: scripts/sync_command_mirrors.py` in consumer projects. | Command is **internal-only** (source-repo maintenance), exposed by accident. | Either removed from consumer-facing CLI **or** moved to `ai-eng dev sync` and hidden from `--help` in non-source-repo mode. |
| B7 | `ai-eng work-item sync` fails with `'spec-126' label not found` and stale-state warnings; unclear value. | Either auto-create the label or fail-soft with clear remediation. | Either: (a) auto-create missing labels with `--create-labels` opt-in, or (b) print clear `→ run 'gh label create spec-126'` next-step. |
| B8 | `set-primary` does not exist as top-level command (only `ai-eng vcs set-primary`); user typed expected discoverability. | Naming inconsistency. | Either flatten or document; subcommand discoverability must be obvious from `ai-eng --help`. |
| B9 | `ai-eng gate cache` errors `requires --status or --clear` instead of printing help. | Same anti-pattern as `verify` / `release` / `stack remove` / `ide add` / `provider add`. | **Universal rule:** any subcommand invoked with no required args → print help and exit 0, never error. |
| B10 | `ai-eng risk-check` / `ai-eng list` / `ai-eng set-primary` look like they should be top-level (typed by user) but are buried. | Discoverability. | Top-level `--help` lists all reachable verbs; helpful "did-you-mean" suggestions for typos. |
| B11 | `ai-eng spec activate` requires `--specs-dir` flag — feels backwards. | Should accept positional arg matching how user thinks. | `ai-eng spec start <path>` (or default to currently selected spec from manifest). |
| B12 | `ai-eng spec verify` says `Frontmatter completed=? total=?` then `Drift detected` then `Auto-fixed: total=17, completed=17` — confusing tri-state output. | Output mixes diagnostic and action without separation. | `BEFORE: 17/17 ✓` `AFTER: 17/17 ✓` `→ no drift`. If drift: `DRIFT: total ?→17, completed ?→17` `FIXED ✓`. |
| B13 | `.ai-engineering/contexts/team` still ships even though deprecated in last iteration. | Installer manifest stale. | Removed from installer; `ai-eng update` cleans existing installs (orphan flag in update preview). |
| B14 | `.ai-engineering/specs` and `.ai-engineering/state` directory contents do not match latest spec definitions. | Unknown — needs explore. | Acceptance: documented schema for each dir, golden-file test that fresh install matches schema. |
| B15 | `AGENTS.md` ships even when only Claude Code + Copilot are selected. Unclear who consumes it. | AGENTS.md is the cross-IDE SSOT per CLAUDE.md, but installer should explain or skip. | Either: AGENTS.md is **always** the canonical doc (and installer banner says so), or installer only ships AGENTS.md when ≥2 IDEs selected. Decision required. |
| B16 | `.gitleaks.toml` and `.semgrep.yml` in consumer project — sync with current branch state? | **Confirmed divergent in source repo.** `.gitleaks.toml`: template (`src/ai_engineering/templates/project/.gitleaks.toml`, 35 lines, stricter, has Article XII §4 comment) vs source-repo live `.gitleaks.toml` (31 lines, trimmed). `.semgrep.yml`: template more current (added `hardcoded-password`, `subprocess-shell-true`, CWE/OWASP metadata) vs source-repo live (older). Installer ships template (correct), but source-repo's own configs are stale — its own gates run against weaker rules. | **Decide policy:** either source repo dogfoods its own template (sync source-repo `.gitleaks.toml` + `.semgrep.yml` to match templates), or templates are intentionally stricter for consumers (document why). Add CI test: source-repo configs must match templates unless explicit `# AIENG_DOGFOOD_DRIFT_OK: <reason>` marker. AGENTS.md note: shipped for copilot/gemini/codex (deduplicated), NOT for claude-code (CLAUDE.md is equivalent) — that part is correct by design. |

### 2.2 P1 — Surface / Naming / Discoverability

The user named these explicitly:

- **`ide`, `stack`, `provider`, `vcs` subcommands feel redundant with `install --reconfigure`** (KISS violation). Proposal: collapse to a single `ai-eng config` (or `ai-eng reconfigure`) interactive flow that wraps the install wizard. Keep `list` / `status` for inspection.
- **`audit` vs `verify` vs `validate` overlap** and none feels reliable. Unify to:
  - `ai-eng check` — single user-facing health command (replaces `validate`); fast, no LLM.
  - `ai-eng verify [--profile <p>]` — deep verification with specialists; profile is the only flag (default `normal`, `full` available).
  - `ai-eng audit` — pure read-only telemetry / SQLite query surface (already documented in CLAUDE.md). Keep.
  - `ai-eng doctor` — runtime + tools health (keep, but it must NOT print state warnings repeatedly).
- **`gate` vs `risk-check` overlap.** `risk-check` is a `gate` subcommand only — make that obvious in help, don't expose top-level alias confusion.
- **`work-item`** — name is awkward; rename to `ai-eng issue sync` (closer to GitHub/ADO mental model) OR fold into `ai-eng board sync` if board is the term used elsewhere (it is — see `ai-board-sync` skill).
- **`workflow`** subcommand suspected legacy — needs an explicit decision: keep (with documented purpose) or delete.

### 2.3 P1 — Output / UX Quality (the "show what it's doing" requirement)

Every command must implement the same **narrative output contract**:

```
{ ai } engineering · v0.4.0

→ <action verb> <object>          # e.g. "Installing Engram", "Updating AGENTS.md"
  ├ <substep 1>                   # spinner or ✓
  ├ <substep 2>
  └ <substep N>

✓ <result summary>                # "Installed Engram v0.3.2 in 12s"
  Changed:  <count> file(s)
  Created:  <count>
  Removed:  <count>
  Moved:    <count>
  Skipped:  <count>

Next steps:
  → <suggested command>
```

- **Verbs are explicit**: Installing / Updating / Removing / Moving / Creating / Verifying. Never silent.
- **Diff summary is mandatory** for any mutating command.
- **Long-running steps** show progress (Engram, package downloads, semgrep scans).
- **Errors quote exact tool output** and provide a *Next steps* recovery line.
- **Interactive selection** (like `install` already does for stacks/IDEs/providers) is the default for any command that takes a closed-set TEXT argument. CLI flags remain available for non-interactive use.
- **No bare `--help` exit on no args** is acceptable in 2026 — print help and exit 0.

### 2.4 P2 — Architecture Hygiene

The user wants the seal of: **KISS, YAGNI, DRY, SOLID, SDD, TDD, Clean Code, Hexagonal/Clean Architecture.** Concrete asks derivable from the feedback:

1. **One source of truth for state**: state.db. Delete the JSON fallback code path (or guard it behind a one-time migration that runs in `install` / `update` and never logs after migration).
2. **One source of truth for governance docs**: single `CONSTITUTION.md` location. Add invariant test.
3. **Domain / adapter split (hexagonal)**:
   - `core/` — governance rules, state mutations, spec lifecycle. No I/O.
   - `adapters/cli/` — Typer commands, output formatters, prompts.
   - `adapters/installer/` — phase orchestration, file copy, manifest sync.
   - `adapters/vcs/` — gh, ado.
   - `adapters/ide/` — claude, copilot, gemini, codex.
4. **Output formatting is one module** (single Renderer with `info/action/diff/error/next` methods) — DRY across every command.
5. **Public vs internal CLI surface** is enforced by a `cli_visibility: public|internal` attribute on every Typer command; internal commands hidden unless `AIENG_DEV=1`.
6. **TDD** for every change: golden snapshot tests for help output, install transcript, update diff. CI fails if `ai-eng install` on a synthetic empty repo emits ANY warning.
7. **YAGNI**: candidates for deletion (subject to decision in spec phase) — `stack`, `ide`, `provider`, `vcs` mutating verbs (replace with `config reconfigure`); `workflow` if legacy; top-level `sync` for non-source repos.

---

## 3. Roadmap & Milestones

All milestones land on `feat/spec-126-hook-ndjson-lock-parity` and ride PR #506. Each milestone is a coherent commit boundary with passing gates.

### M0 — Discovery & Spec Lock (no code)
- `/ai-brainstorm` from this brief → spec.md.
- `/ai-plan` → plan.md with task DAG.
- Decisions logged for: (a) `audit/verify/validate/check` final naming, (b) `stack/ide/provider/vcs` collapse, (c) `workflow` keep/delete, (d) `AGENTS.md` policy, (e) `work-item` rename.
- **Exit:** Approved spec + plan, all P0 items have an owner task, golden tests defined.

### M1 — Stop the Bleeding (P0 bugs, no surface change)
- B1: Single-shot state warner + auto-cleanup of orphan JSON files in `state` phase.
- B2: Engram install with timeout + progress + fail-open.
- B3: Single CONSTITUTION.md + invariant test.
- B4: Fix every broken cross-reference in `ai-governance` & `ai-mcp-sentinel` SKILLs.
- B5: `update --check` returns 0 changes immediately after `install` (golden test).
- B13: Drop `contexts/team` from installer + cleanup orphan in `update`.
- B16: Golden-file parity for `.gitleaks.toml`, `.semgrep.yml`.
- **Exit:** `ai-eng install && ai-eng doctor && ai-eng validate` on empty dir → ALL PASS, ZERO warnings, ZERO failures.

### M2 — Output Contract (DRY renderer)
- Build single `Renderer` (`core/output/`) with `step / action / diff / error / next` methods.
- Every command emits via Renderer. Remove ad-hoc `print` calls.
- Add `--quiet`, `--json` (already partial), `--verbose`.
- Golden snapshot tests for `install`, `update`, `doctor`, `gate`, `verify`, `validate` transcripts.
- B12: spec verify uses BEFORE/AFTER/DIFF format.
- **Exit:** Every public command shows "what it is doing" + diff summary + next steps. No silent operations.

### M3 — Help-First Discipline (no `Missing argument` ever)
- Universal Typer wrapper: a command/subcommand invoked with no required args prints help and exits 0.
- B6, B9, B10, B11: applied across `verify`, `release`, `stack remove`, `ide add/remove`, `provider add`, `gate cache`, `spec activate`.
- Top-level `--help` shows full tree; "did-you-mean" hint for unknown commands.
- **Exit:** Empty-arg invocation always exits 0 and shows help; usability tested via golden help snapshots.

### M4 — Surface Consolidation (P1 naming)
- Collapse `stack`, `ide`, `provider`, `vcs` *mutation* verbs into `ai-eng config` (interactive reconfigure flow). Keep `*-list` / `*-status` for inspection or fold into `ai-eng status`.
- Unify `validate` → `check` (with deprecation alias `validate` → `check` for one release).
- Move `sync` (mirror sync) to `ai-eng dev sync`, hidden when not in source repo.
- Decide and execute: `work-item` rename (likely `issue` or `board`), `workflow` keep/delete.
- Top-level `--help` reduced to: `install / update / status / doctor / check / verify / audit / gate / commit / pr / release / spec / config / dev`.
- **Exit:** New surface documented in AGENTS.md; old verbs print deprecation warning + next-command suggestion for one release.

### M5 — Hexagonal Refactor (architecture seal)
- Extract `core/` (no I/O), `adapters/cli/`, `adapters/installer/`, `adapters/vcs/`, `adapters/ide/`.
- Output Renderer becomes `core/output/`; CLI only wires.
- All Typer command modules become thin: parse args → call core use-case → render.
- Add architecture test (import-linter or custom) blocking core → adapter dependencies.
- **Exit:** Architecture diagram in `docs/architecture.md`; import-linter green; all existing tests pass.

### M6 — Hardening & Verify Loop
- Run `/ai-verify --full` until governance + architecture + feature ≥ 95.
- Run `/ai-review` 3× (full specialist roster) until clean.
- Manual usability test: human runs `ai-eng install` on a fresh dir, narrates confusion. Zero confusion ⇒ done.
- **Exit:** PR #506 ready for merge.

---

## 4. What Changes — Concrete File-Level Targets

(Initial map — `/ai-explore` will refine during M0.)

| Concern | Files (representative) |
|---------|------------------------|
| State warner spam (B1) | `src/ai_engineering/state/observability.py`, `src/ai_engineering/installer/phases/state.py`, every `*Store` consumer |
| Engram hang (B2) | `src/ai_engineering/installer/phases/engram.py` (or wherever the prompt lives), subprocess wrapper |
| Duplicate CONSTITUTION (B3) | Root `CONSTITUTION.md`, `.ai-engineering/CONSTITUTION.md`, installer manifest |
| Cross-ref breaks (B4) | `.claude/skills/ai-governance/SKILL.md`, `.claude/skills/ai-mcp-sentinel/SKILL.md`, `.ai-engineering/references/IOCS_ATTRIBUTION.md` |
| Update-after-install (B5) | Installer template payloads for `AGENTS.md`, `.github/skills/ai-eval/SKILL.md` |
| Internal-only `sync` (B6) | `src/ai_engineering/cli/commands/sync.py`, `scripts/sync_command_mirrors.py` |
| work-item labels (B7) | `src/ai_engineering/work_item/*` |
| Help-on-empty (B9, B10, B11, etc.) | Typer base in `src/ai_engineering/cli/__init__.py` (or equivalent app factory) |
| spec activate UX (B11) | `src/ai_engineering/cli/commands/spec.py` |
| spec verify output (B12) | same |
| Surface collapse (M4) | `cli/commands/stack.py`, `ide.py`, `provider.py`, `vcs.py`, `config.py` (new) |
| Renderer (M2) | `src/ai_engineering/output/renderer.py` (new) |
| Hexagonal split (M5) | Repo-wide |

---

## 5. Definition of Done (project-level)

- [ ] `ai-eng install` on empty dir: 0 warnings, 0 errors, no hangs, ≤ 30s wall-clock.
- [ ] Immediately after install: `update --check` = 0, `doctor` = ALL PASS, `validate`/`check` = ALL PASS, `verify` (default profile) ≥ 95.
- [ ] No subcommand ever exits with `Missing argument`. Help is always 0.
- [ ] Single CONSTITUTION.md. CI invariant.
- [ ] Single `state.db`. JSON fallback removed or one-shot migrated silently.
- [ ] Renderer used by every public command.
- [ ] Surface map in AGENTS.md ≤ 14 top-level verbs.
- [ ] Architecture: import-linter passes; core/ has zero adapter imports.
- [ ] Golden snapshot tests for install / update / doctor / check / verify transcripts.
- [ ] `/ai-review --full` and `/ai-verify --full` clean (≥ 95).

---

## 6. Open Decisions for `/ai-brainstorm`

1. Final names: `check` vs `validate`? `issue` vs `board` vs `work-item`? `config` vs `reconfigure`?
2. Keep `workflow`? If yes, what does it do?
3. AGENTS.md ship policy.
4. Engram: opt-in default vs prompt? Timeout value?
5. Deprecation policy: how many releases keep aliases?

---

## 7. Implementation Constraints (non-negotiable)

- **Branch:** stay on `feat/spec-126-hook-ndjson-lock-parity`. No new branch.
- **PR:** #506. Squash optional but commit-by-milestone preferred for reviewability.
- **Hot path budgets** (from CLAUDE.md): pre-commit < 1s, pre-push < 5s. Renderer / wrappers must not regress this.
- **TDD:** every milestone lands with new tests RED → GREEN.
- **No backwards-compat shims** beyond one release of deprecation aliases (per M4).
- **No new dependencies** without architecture review.

---

## 8. Evidence Appendix (grounded by parallel deep-pass)

### 8.1 CLI surface inventory (Agent 2)

Entry: `src/ai_engineering/cli.py` → `cli_factory.py:create_app()` line 188. Root app `no_args_is_help=False` w/ custom `_app_callback` showing logo+help on bare invocation. Sub-apps **with** `no_args_is_help=True` already: `stack`, `ide`, `gate`, `skill`, `maint`, `provider`, `vcs`, `setup`, `decision`, `audit`, `retention` (nested under `audit`), `risk`, `spec`, `work_item`, `workflow`, `internal` (hidden).

**Confirmed NO-ARG-FAILS** (typer.Argument w/ no default): `verify MODE`, `release VERSION`, `stack add STACK`, `stack remove STACK`, `ide add IDE`, `ide remove IDE`, `gate commit-msg MSG_FILE`, `provider add PROVIDER`, `spec activate --specs-dir` (required option, same anti-pattern). M3 wraps these in a single `@no_args_help` decorator applied at registration.

### 8.2 Renderer contract (Agent 5 — proposed module `src/ai_engineering/output/renderer.py`)

```python
class Renderer:
    def __init__(self, command: str, *, json: bool, quiet: bool) -> None: ...
    @classmethod
    def from_app(cls, command: str) -> "Renderer": ...
    def header(self, title: str | None = None) -> None: ...
    def step(self, description: str) -> None: ...
    def action(self, verb: Verb, object_: str, detail: str | None = None) -> None: ...
    @contextmanager
    def progress(self, total: int, desc: str) -> Iterator[StepTracker]: ...
    def record(self, kind: ChangeKind, path: str, *, from_: str | None = None) -> None: ...
    def diff_summary(self,
        created=(), updated=(), removed=(), moved=(), skipped=()) -> None: ...
    def error(self, msg: str, *, code: str = "ERROR", fix: str | None = None,
              next_actions: list[NextAction] = ()) -> NoReturn: ...
    def next(self, actions: list[NextAction]) -> None: ...
    def ok(self, summary: str, *, result: dict | None = None) -> None: ...
```

**Verb taxonomy (closed Literal):** `Installing` (info-blue), `Updating` (info-blue), `Removing` (error-red), `Moving` (warning-yellow), `Creating` (success-green), `Verifying` (brand-teal), `Skipping` (muted-dim), `Restoring` (warning-yellow). Other verbs rejected at type-check time.

**Mode behavior:**
| Method | Human (default) | JSON | Quiet |
|---|---|---|---|
| `header/step/action/progress` | Rich w/ verb color | no-op | no-op |
| `record/diff_summary` | tree summary | accumulate to `result["changes"]` | summary only |
| `next` | `→ <action>` block | append to envelope `next_actions` | suppressed |
| `ok` | success line | `emit_success(...)` once | success line |
| `error` | red error + fix + next | `emit_error(...)` exit 1 | red error |

Wraps existing `cli_envelope.py`, `cli_ui.py`, `cli_progress.py`, `cli_output.py` — does **not** replace them. After M2 commands stop calling those directly; deprecate `cli_ui.success/warning/error/info/kv/status_line/result_header/suggest_next` w/ one-release alias, remove in M5.

### 8.3 Final command tree (Agent 5 — locked target for M4)

```
ai-eng
├── install            Set up framework in this repo (interactive)
├── update             Apply available framework updates
├── status             Show framework + project state at a glance
├── doctor             Health diagnostics: tools, hooks, runtime
├── check              Content-integrity validation (was: validate)
├── verify [profile]   Deep scored verification w/ specialists
├── audit              Read-only telemetry + SQLite query
├── config             Reconfigure stacks/IDEs/providers/VCS interactively
├── gate               Hot-path gates: pre-commit, commit-msg, pre-push, risk-check
├── spec               Spec lifecycle: start, verify, list, show
├── issue              Sync specs to GitHub Issues / ADO Boards (was: work-item)
├── release            Cut a release w/ changelog + tag
├── setup              Configure platform credentials (gh, sonar, ado)
├── decision           Architectural decisions: list, record, expire-check
├── risk               Risk register: accept, renew, resolve, list, show
├── guide              Print AGENTS.md / onboarding guide
├── version            Print framework version
└── dev                Source-repo maintenance (hidden in consumer projects)
    └── sync           Regenerate IDE command mirrors
```

**Migration table (one-release deprecation alias unless noted):**

| Old | New | Alias |
|---|---|---|
| `validate` | `check` | yes |
| `stack {add,remove,list}` | `config` (interactive) / `config stack list` | yes |
| `ide {add,remove,list}` | `config` / `config ide list` | yes |
| `provider {add,remove,list}` | `config` / `config provider list` | yes |
| `vcs {status,set-primary}` | `config vcs {status,set-primary}` | yes |
| `work-item sync` | `issue sync` | yes |
| `sync [--check]` | `dev sync [--check]` | hidden, no alias |
| `workflow {commit,pr,pr-only}` | **removed**; use `release --pr` or `/ai-pr` skill | yes |
| typed `set-primary`, `risk-check`, `list` top-level | did-you-mean → real path | n/a |

**Locked decisions** (resolves §6 open questions):
- `config` over `reconfigure` (shorter, matches `git config`).
- `check` over `validate` (brief mandate).
- `issue` over `board` (GitHub primary mental model on PR #506; `board` implies UI nav).
- `workflow` **deleted** — `workflow.py` is a 112-line shim duplicating `gate all` + `release`; verbs map to `release --pr` / `--commit-only` or `/ai-pr` / `/ai-commit` skills.

### 8.4 Investigation source files (full reports offloaded by runtime-guard)

- State-warner trace: `.ai-engineering/runtime/tool-outputs/2026-05-07T190653Z-e89fb8c888f4416eb7d58f0b171b1fb7.txt`
- Renderer + Naming proposal: same offload bundle (Agent 5 result).
- All citations above are file:line from the live source tree on `feat/spec-126-hook-ndjson-lock-parity`.

---

## 9. References

- This brief: `.ai-engineering/specs/drafts/cli-ux-overhaul-brief.md`
- Source feedback: live CLI session transcript captured in this prompt (P0/P1 items annotated in §2).
- Governance: `.ai-engineering/CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`.
- UX context to consult: `.ai-engineering/contexts/cli-ux.md` (referenced by user; verify it exists, otherwise create as part of M2).
- Related skills: `/ai-design`, `/ai-debug`, `/ai-explore`, `/ai-support`, `/ai-prompt` (this), `/ai-brainstorm`, `/ai-plan`.

---

**Next action:** invoke `/ai-brainstorm` against this brief to lock decisions in §6, then `/ai-plan` to produce `plan.md` with the M0–M6 task DAG.
