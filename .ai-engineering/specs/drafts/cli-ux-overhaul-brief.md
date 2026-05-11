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
| B2 | `ai-eng install` **hangs** after answering `y` to "Install Engram for memory persistence?". | **Decision: remove Engram from installer entirely.** Engram is a third-party product (Gentleman-Programming/Engram), not an `ai-engineering` dependency. Bundling third-party installs into our CLI creates an unwanted dependency surface: brew formula drift, subprocess timeout/deadlock bugs, version skew, and failure modes outside our control. Original root cause (kept for reference): `src/ai_engineering/installer/engram.py:153`, `:348`; `src/ai_engineering/cli_commands/core.py:304`, `:794` — no `timeout=`, `capture_output` deadlock, wrong brew formula, missing spinner, bare exception swallow. | **Strip Engram from the installer.** (a) Delete `src/ai_engineering/installer/engram.py` and the `--engram`/`--no-engram` flags from `cli_commands/core.py`. (b) Remove the install-time prompt. (c) Remove `engram` references from `manifest.yml`, `AGENTS.md` Step 0, and any phase orchestration. (d) Add a standalone doc page (`docs/integrations/engram.md`) with the official Engram install commands per OS and the `engram setup claude_code` step — clearly marked as **optional, third-party, not maintained by `ai-engineering`**. (e) `ai-eng doctor` may *detect* Engram if present and report status, but never installs or prompts. Acceptance: zero subprocess calls to brew/winget from our installer; zero hang risk; CLAUDE.md "Optional: Engram" section rewritten as "see external doc". |
| B3 | Two `CONSTITUTION.md` files (root + `.ai-engineering/`) — reported many times, still ships. | **Refined.** Four copies actually exist: (i) root `CONSTITUTION.md` (277 lines, source-repo governance law, NOT shipped, correct); (ii) `.ai-engineering/CONSTITUTION.md` (113 lines, **divergent stub, no architectural role**); (iii) `src/ai_engineering/templates/project/CONSTITUTION.md` (229 lines, project-charter template); (iv) `src/ai_engineering/templates/.ai-engineering/CONSTITUTION.md` (79 lines, minimal stub). Installer ships the project-charter template to BOTH consumer root AND consumer `.ai-engineering/` per `templates.py:171-184` — that is the duplication users see. | **Delete source-repo `.ai-engineering/CONSTITUTION.md` (113-line stub)** — redundant. Decide installer policy: ship project-charter template to ONE consumer location only (likely root), not both. Add CI invariant test: exactly one `CONSTITUTION.md` per consumer install. **DEPENDS ON `dx-excellence-refactor-brief.md` M2** — that brief redefines `CONSTITUTION.md` shape: project-specific identity (mission, stakeholders, vocabulary, prohibitions, compliance gates, anti-goals, boundaries, escalation, language, lifecycle phase), AI-behaviour content migrated to AGENTS.md mirror. **The new template installer ships MUST follow that shape, not the legacy 229-line stub.** Sequencing: DX M2 lands first (defines new template), then CLI B3 wires installer to ship the new template once. |
| B4 | Fresh install fails `ai-eng validate`: missing `_history.md`, broken `ai-governance` cross-refs to `src/ai_engineering/governance/opa_runner.py`, `decision_log.py`, `policy/checks/opa_gate.py`, `doctor/runtime/opa_health.py`, `ai-mcp-sentinel` → `IOCS_ATTRIBUTION.md`. | **Refuted in part — validator bug.** Files (1)-(4) **all exist** in source repo (`opa_runner.py`, `decision_log.py`, `policy/checks/opa_gate.py`, `doctor/runtime/opa_health.py`). Bug is in `src/ai_engineering/validator/categories/file_existence.py:_reference_exists()`: it scans `.claude/skills/*.md` and resolves `src/...` paths from consumer-project root, where `src/` does not exist by design (it is the source-repo's implementation tree, not a consumer artifact). **Confirmed real misses**: `IOCS_ATTRIBUTION.md` is genuinely missing from `src/ai_engineering/templates/.ai-engineering/references/` (only `iocs.json` ships); `_history.md` is absent because validator at `validator/categories/file_existence.py:228-256` `_record_spec_buffer_result` HARD-FAILs without a fresh-install exemption (file is a progressive artifact). | **Three patches:** (i) validator `_should_skip_reference_path()` skips `src/ai_engineering/...` in SKILL.md (those are LLM impl notes, not consumer files); (ii) add `IOCS_ATTRIBUTION.md` to `src/ai_engineering/templates/.ai-engineering/references/`; (iii) **prefer:** downgrade missing `_history.md` to WARN when `spec.md` + `plan.md` present. **DEPENDS ON `dx-excellence-refactor-brief.md` M4** — that brief assigns `_history.md` rotation to `/ai-cleanup` (consolidated spec deletion → append `_history.md`, leave slot ready). **Do NOT ship an empty stub from the installer**; defer creation to `/ai-cleanup` first invocation. Acceptance: fresh install passes `ai-eng check` (was: `validate`) + `ai-eng verify governance` ≥ 95. |
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
| B15 | `AGENTS.md` ships even when only Claude Code + Copilot are selected. Unclear who consumes it. | AGENTS.md is the cross-IDE SSOT per CLAUDE.md, but installer should explain or skip. | **RESOLVED by `dx-excellence-refactor-brief.md` §2.3 + M2.** AGENTS.md is one of **four canonical mirrors** (AGENTS / CLAUDE / GEMINI / `.github/copilot-instructions.md`) — all carry **identical content** regardless of IDE selection. Installer ships ALL FOUR every install (no IDE-conditional shipping). Sync enforced by `tools/skill_lint/md_mirror.py` (sha256 equivalence). Installer banner explains: "These four files are mirror copies; each IDE reads its native path." |
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
- B2: Strip Engram from installer; document as optional external integration.
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
| Engram removal (B2) | **Delete:** `src/ai_engineering/installer/engram.py`, engram phase from `installer/phases/`, `--engram`/`--no-engram` flags in `cli_commands/core.py`, engram refs in `manifest.yml` + `AGENTS.md` Step 0. **Add:** `docs/integrations/engram.md` (standalone, marked third-party). **Update:** CLAUDE.md "Optional: Engram" section → external-doc pointer. |
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
3. ~~AGENTS.md ship policy.~~ **Resolved (B15) by `dx-excellence-refactor-brief.md` §2.3:** AGENTS.md is one of four canonical mirrors, always shipped, identical content across all four IDE-native paths.
4. ~~Engram: opt-in default vs prompt? Timeout value?~~ **Resolved (B2):** Engram is **removed** from the installer. Documented as optional third-party integration in `docs/integrations/engram.md`. No prompt, no subprocess, no dependency.
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

## 9. Cross-Brief Coordination — Dependencies on `dx-excellence-refactor-brief.md`

Both briefs target PR #506. CLI brief execution **must consume DX brief outputs** in the following areas. Order-of-operations: when in doubt, **DX brief lands first** because it changes the contracts (mirrors, naming rules, `/ai-cleanup` lifecycle) that CLI brief surfaces consume.

### 9.1 Hard dependencies (DX brief MUST land before CLI brief touches the area)

| CLI brief item | DX brief dependency | Why |
|---|---|---|
| **B3** (CONSTITUTION.md installer policy) | DX brief **M2** (`/ai-constitution` redefined → project-specific shape: mission, stakeholders, vocabulary, prohibitions, compliance gates, anti-goals, boundaries, escalation, language, lifecycle phase) | The template the installer ships must follow the new shape. Wiring installer to ship the legacy 229-line stub would lock-in the wrong content. |
| **B4** (`_history.md` validator failure) | DX brief **M4** (`/ai-cleanup` adds explicit `_history.md` rotation step) | `/ai-cleanup` becomes the lifecycle owner of `_history.md`. Installer must NOT ship a stub — defer to `/ai-cleanup` first run. CLI fix becomes "downgrade missing → WARN" only. |
| **B15** (AGENTS.md ship policy) | DX brief **§2.3 / M2** (four canonical mirrors with identical content, sync via `tools/skill_lint/md_mirror.py`) | Resolves the open question. AGENTS.md ships always, identical to CLAUDE.md / GEMINI.md / `.github/copilot-instructions.md`. |
| **M4 Surface Consolidation** (rename `validate→check`, `work-item→issue`, collapse `stack/ide/provider→config`, etc.) | DX brief **M1** (5-rule naming convention with `tools/skill_lint/naming.py`) | All new command names must satisfy R1 (`ai-` prefix where applicable), R3 (paired lifecycle verbs `start/end`, `enable/disable`), R4 (kebab-case slugs), R5 (`.sh`/`.ps1` parity for any new scripts). CLI rename table must be checked against the lint *before* M4 ships. |
| **B6** (move `sync` to `dev sync`) | DX brief **M6** (trusted-script lane in hook manifest) | If `dev sync` invokes `python scripts/sync_command_mirrors.py`, the script should run in the trusted-script lane to bypass RTK rewriting and IOC re-evaluation in sub-agent contexts. |

### 9.2 Soft alignments (CLI brief should reference DX brief decisions; no blocking dependency)

| Topic | Alignment |
|---|---|
| Installer onboarding (3 yes/no → 2 yes/no) | DX brief §2.7 frame 1 says install asks "telemetry, engram, IDE". With Engram removed (CLI B2), the prompt set is now **2 yes/no** (telemetry, IDE). Both briefs should reflect this. Suggest patching DX brief §2.7 to drop `engram` from the frame-1 prompt list. |
| Renderer / output contract (CLI §2.3 + M2) | DX brief §2.4 introduces deterministic preprocessor JSON output for skills (`scripts/start_collect.py` etc.). Renderer should accept a "JSON-passthrough" rendering mode for skills that consume `collect-context` JSON, so CLI commands and skill dashboards share the same output substrate. Not a blocker — a future-proofing note. |
| `commit` top-level command (CLI §8.3 final tree) | DX brief §2.2 + M4 says `/ai-commit` is **off-chain, standalone, WIP-only**. CLI brief's `commit` top-level survives untouched, but help text should label it "WIP / standalone — not part of the canonical chain (use `pr` instead)". |
| `workflow` deletion (CLI §8.3 locked decision) | DX brief §1 row 1-2 + M4 align: chain stops mentioning `/ai-commit`-then-`/ai-pr`; `workflow.py` shim becomes redundant. CLI brief deletion is consistent. |
| `/ai-ide-audit` extension (DX M2) | CLI brief does not own this, but DX brief adds Antigravity to the audit matrix. After DX M2 lands, CLI's `ai-eng doctor` may want to surface Antigravity detection results too (defer to a follow-up). |

### 9.3 Bidirectional updates needed

These items require edits to **both** briefs to stay coherent:

1. **DX brief §2.7 frame 1** — drop `engram` from "asks 3 yes/no (telemetry, engram, IDE)". After CLI B2 (Engram removed), it is `2 yes/no (telemetry, IDE)`.
2. **DX brief §2.4.1 last bullet** — "Engram tool prefix doc mismatch" remains a hook/docs concern (not installer). Keep DX M6 fix; the CLI brief no longer interacts with this surface.
3. **CLI brief §6 open decisions** — items 3 and 4 are now cross-marked resolved (this edit).

### 9.4 Sequencing recommendation for PR #506

Given both briefs ride PR #506, the suggested commit order minimises rework:

1. **DX M1** (naming + parity lint) — establishes the rules CLI M4 must satisfy.
2. **DX M2** (Markdown canon + `/ai-constitution` refactor + new template) — establishes the CONSTITUTION.md template CLI B3 ships.
3. **CLI M1** (P0 bug fixes B1, B2, B3, B4, B5, B13, B16) — depends on DX M2's new template for B3; depends on DX M4's `_history.md` lifecycle for B4.
4. **DX M3** (preprocessor layer + `/ai-start` canary) — independent of CLI work; can run in parallel with CLI M1.
5. **DX M4** (single canonical chain + `/ai-cleanup` `_history.md` rotation + per-task gate trim) — needed before CLI M4 ships, as CLI M4 will rename `commit` semantics.
6. **CLI M2/M3** (Renderer + help-first discipline) — independent; can run in parallel.
7. **CLI M4** (surface consolidation + renames) — gated on DX M1 (naming lint) + DX M4 (chain semantics).
8. **DX M5/M6/M7** + **CLI M5/M6** — parallel hardening passes.

If sequencing slips, fall back to "DX brief in earlier commits, CLI brief in later commits within the same PR."

---

## 10. References

- This brief: `.ai-engineering/specs/drafts/cli-ux-overhaul-brief.md`
- Source feedback: live CLI session transcript captured in this prompt (P0/P1 items annotated in §2).
- Governance: `.ai-engineering/CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`.
- UX context to consult: `.ai-engineering/contexts/cli-ux.md` (referenced by user; verify it exists, otherwise create as part of M2).
- Related skills: `/ai-design`, `/ai-debug`, `/ai-explore`, `/ai-support`, `/ai-prompt` (this), `/ai-brainstorm`, `/ai-plan`.

---

**Next action:** invoke `/ai-brainstorm` against this brief to lock decisions in §6, then `/ai-plan` to produce `plan.md` with the M0–M6 task DAG.
