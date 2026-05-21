---
execution_route:
  version: 1
  spec: spec-147
  executor: autopilot
  automation: autopilot
  concern_count: 5
  estimated_files: 45
  reason: "Five independent concerns (waves) spanning hooks, gate/verify services, config/state, skill+agent surface, CLI, and docs; ~45 files; the decision-store migration alone touches 17 caller call-sites. Multi-concern + large → autopilot wave-shipping (D-147-01)."
  safe_next_command: "/ai-autopilot"
status: draft
pipeline: full
spec: spec-147
title: Plan — Obvious by Default (fail-loud safety and legibility refactor)
---

# Plan — spec-147 Obvious by Default

## Summary

Decompose spec-147 into five independent waves, each shipped by `/ai-autopilot` as its own single-concern PR. Wave 1 (seal the fail-open gates) is sequenced first because it is the only active safety emergency. Each wave is TDD-paired (a RED test asserting the fail-loud/poka-yoke behavior precedes every GREEN implementation). Planning-phase exploration resolved both spec Open Questions and surfaced three task-shaping refinements (17 not 12 decision-store callers; gate-findings SQLite table is reader-less; the quality-loop STOP is already deterministic except one condition) — recorded below so autopilot's per-wave deep-planning starts from real ground truth.

## Pipeline classification

`full` — new cross-cutting refactor, >5 files, five concerns. Executor route: `autopilot` (see frontmatter). `/ai-plan` does not execute; operator approves this plan, then runs `/ai-autopilot`.

## Design routing

N/A — no user-facing UI surface. All changes are Python services, stdlib hooks, CLI behavior, CI tests, skill/doc markdown, and mirror regeneration. No `/ai-design` dispatch.

## Architecture

Pattern: **ad-hoc multi-wave remediation** (no single canonical pattern; each wave has its own shape). Hexagonal hardening (§10.8) is the spine of Waves 1 and 4: a tool/port adapter that cannot run must raise into the port, never return a clean result. Waves 2/3/5 are poka-yoke CI guards + SSOT consolidation + surface de-collision.

Module boundaries touched:

- **Hooks** (`.ai-engineering/scripts/hooks/`) — Waves 1, 2. stdlib-only sealed contract; `sqlite3` IS stdlib, so hooks MAY read `state.db` directly.
- **Gate / verify services** (`src/ai_engineering/cli_commands/gate.py`, `src/ai_engineering/verify/service.py`, `src/ai_engineering/policy/`) — Waves 1, 4.
- **Config / state** (`src/ai_engineering/config/`, `src/ai_engineering/state/`, `installer/`, `policy/checks/risk.py`) — Waves 1, 2.
- **Skill + agent surface + docs** (`.claude/skills/`, `CLAUDE.md`, `CONSTITUTION.md`) — Waves 2, 3, 5. Canonical-payload edits require `python scripts/sync_command_mirrors.py` to regenerate mirrors; byte-drift is caught by `validate_content_integrity` (via `verify_governance`), not `test_surface_parity.py` (which enforces the No-Twin Axiom).
- **CLI** (`src/ai_engineering/cli_commands/cleanup.py`, `maintenance.py`) — Waves 3, 5.

## Wave DAG (ordering)

```
Wave 1 (safety)  ──►  [ships first, independent PR]
Wave 2 (docs+SSOT) ─┐
Wave 3 (one way)   ─┤  independent of each other; any order after Wave 1
Wave 4 (determinism)┤  (no hard cross-wave blockers)
Wave 5 (poka-yoke) ─┘  internal dep: §10.x backfill (T-5.1) precedes its CI test (T-5.2)
```

No wave hard-blocks another. Each wave is its own PR, so each regenerates mirrors independently (no concurrent-regen conflict). Recommended sequence: 1 → 2 → 3 → 4 → 5 (safety first, then the highest-risk migration while attention is fresh).

## Resolved Open Questions (from spec §Open Questions)

- **OQ1 gate-findings (D-147-10)** → RESOLVED by caller audit: no production code reads the `gate_findings` SQLite table (only `tests/integration/state/test_db_migration.py:133`). Decision: **remove the SQLite seed + table; keep `gate-findings.json` canonical** (matches doctrine). Update the one migration test.
- **OQ2 naming-grammar (D-147-15)** → CANDIDATE for operator confirm in Wave 5: codify the *already-universal* grammar — `ai-` prefix + lowercase-kebab + (imperative-verb | domain-noun); all 53 skills already satisfy it, so **zero renames expected**. CI locks it for new skills. Confirm in T-5.3 before any rename.

---

## Phase 1 — Wave 1: Seal the fail-open gates (D-147-02..06)

Concern: no gate or hook exits 0 when its tool is absent/broken/malformed. Agent: build (code), with verify gates. Highest priority.

- [ ] T-1.1 — RED: assert hook integrity default is `enforce`
  - Agent: build
  - Files: `tests/unit/hooks/test_integrity_default.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — author a test modeled on `tests/unit/hooks/test_canonical_events_count.py` (plain `assert`, `parents[N]` anchor) asserting `integrity._DEFAULT_MODE == "enforce"` and that a drifted-script run with no env var exits non-zero.
  - Gate: test fails against current `warn` default.

- [ ] T-1.2 — GREEN: flip `_DEFAULT_MODE` to `enforce`; regenerate manifest; loud hint
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/integrity.py:40`, `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: §10.8 Hexagonal (adapter fails into the port), §10.6 SDD
  - Patch (deterministic):
    ```diff
    --- a/.ai-engineering/scripts/hooks/_lib/integrity.py
    +++ b/.ai-engineering/scripts/hooks/_lib/integrity.py
    @@
    -_DEFAULT_MODE = "warn"
    +_DEFAULT_MODE = "enforce"
    ```
    Then run `python scripts/regenerate-hooks-manifest.py`. Add a one-line first-run hint (prose edit) in the mismatch path naming `AIENG_HOOK_INTEGRITY_MODE=warn` + the regenerate command.
  - Gate: T-1.1 passes; drifted-hook run exits non-zero with the hint.

- [ ] T-1.3 — RED: `no_suppression` ImportError → BLOCKER, non-zero exit
  - Agent: build
  - Files: `tests/unit/test_gates.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — monkeypatch the import to raise `ImportError`; assert `_run_no_suppression` raises `typer.Exit(code=1)` (not a clean return). Model on existing `test_gates.py` patterns.
  - Gate: fails against current `warning(...skipping...); return`.

- [ ] T-1.4 — GREEN: broken no_suppression module blocks
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/gate.py:136-140`
  - Principles applied: §10.8 Hexagonal, §10.1 KISS
  - Patch (deterministic): omit — judgment: replace the `except ImportError: warning(...); return` with a BLOCKER finding + `raise typer.Exit(code=1)`, error text naming the missing module and its install path. Honor "solve don't punt".
  - Gate: T-1.3 passes.

- [ ] T-1.5 — RED: gitleaks missing/crash/empty/bad-JSON → BLOCKER
  - Agent: build
  - Files: `tests/unit/test_verify_service.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — extend the `FakeSubprocess` fixture (`test_verify_service.py:34-71`); add cases: binary missing (`shutil.which`→None per `test_secrets_gate.py:64-73`), `returncode!=0`+empty stdout, malformed JSON. Each asserts a `FindingSeverity.BLOCKER` secrets finding, not a clean verdict.
  - Gate: fails against current early-return/JSONDecodeError-swallow.

- [ ] T-1.6 — GREEN: verify service treats broken gitleaks as BLOCKER
  - Agent: build
  - Files: `src/ai_engineering/verify/service.py:53-54,307-313`
  - Principles applied: §10.8 Hexagonal, §10.4 DRY
  - Patch (deterministic): omit — judgment: guard `FileNotFoundError`, distinguish crash (non-zero+empty) from clean, and convert swallowed `JSONDecodeError` into a BLOCKER. Error names gitleaks + install command.
  - Gate: T-1.5 passes.

- [ ] T-1.7 — RED: expired risk-acceptance DEC blocks `gate pre-push`
  - Agent: build
  - Files: `tests/unit/test_gates.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — fixture with an expired DEC; assert `gate_pre_push` exits 1. Reference deny logic at `.ai-engineering/policies/risk_acceptance_ttl.rego:19-25`.
  - Gate: fails against current warn-only path.

- [ ] T-1.8 — GREEN: wire risk TTL into pre-push hot path
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/gate.py:91-99,118-127,167-195`
  - Principles applied: §10.8 Hexagonal, §10.6 SDD
  - Patch (deterministic): omit — judgment: call `_check_risk_inline(root, strict=True)` from `gate_pre_push`; expired → exit 1. Keep <5s hot-path budget (state.db read, no LLM).
  - Gate: T-1.7 passes; pre-push budget unbroken.

- [ ] T-1.9 — RED: malformed manifest/state exits 1 with a named error
  - Agent: build
  - Files: `tests/unit/test_config_loader.py`, `tests/unit/state/test_repository.py` (extend or new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — corrupt-YAML fixture; assert non-zero exit + a one-line named error; assert a *missing* file still returns defaults (the contrast case).
  - Gate: fails against current silent-defaults-on-parse-error.

- [ ] T-1.10 — GREEN: distinguish absent (default) vs corrupt (fail loud)
  - Agent: build
  - Files: `src/ai_engineering/config/loader.py:55-57`, `src/ai_engineering/state/repository.py:48-50`, `src/ai_engineering/cli_factory.py:237-245`
  - Principles applied: §10.8 Hexagonal, §10.1 KISS
  - Patch (deterministic): omit — judgment: raise/exit on parse error, keep defaults only for genuine `FileNotFoundError`; narrow the stack-drift `except Exception` to expected types.
  - Gate: T-1.9 passes.

- [ ] T-1.11 — RED: hook silent-swallow fault injection
  - Agent: build
  - Files: `tests/unit/hooks/test_hook_failloud.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — inject formatter failure (`auto-format.py`), checkpoint-write failure (`runtime-stop.py`), MCP-state failure (`mcp-health.py`) → assert a `hookSpecificOutput` warning is emitted; feed an unparseable command to `no-verify-guard.py` → assert it blocks (refuses), not allows.
  - Gate: fails against current swallow/allow behavior.

- [ ] T-1.12 — GREEN: convert silent swallows to visible signals
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/auto-format.py:30-34,242-249`, `runtime-stop.py:15-21`, `mcp-health.py:132-138`, `no-verify-guard.py:80-86`
  - Principles applied: §10.8 Hexagonal, §10.7 Clean Code
  - Patch (deterministic): omit — formatters/state writes emit `hookSpecificOutput` warning (visible, non-blocking); no-verify-guard fails closed on parse error (security boundary). Regenerate hooks-manifest after edits.
  - Gate: T-1.11 passes; hot-path budgets intact.
  - **Wave-1 acceptance**: with all `AIENG_*`/`AIE_*` unset, no gate/hook exits 0 on absent/broken/malformed tool or input (G1).

---

## Phase 2 — Wave 2: Reconcile docs with code + finish SSOT (D-147-07..10)

> **Wave 2 split (2026-05-21).** 2a (doc reconciliation, D-147-07/08) is **DONE + shipped** on PR #532. The SSOT half (2b: decision-store migration to state.db, D-147-09/10) is **SUPERSEDED by spec-148 (Files-only persistence)** — route reversed to retire `state.db` and make files the SoT. The 2b tasks below are retained for history but are NOT executed under spec-147; see `spec-148-files-only-persistence-plan.md`.

Concern: every doc claim resolves to an on-disk fact; one canonical store per datum. Highest-risk wave (17-caller decision-store migration). Agent: build.

### 2a — Doc reconciliation

- [ ] T-2.1 — RED: documented agent/skill counts == files on disk
  - Agent: build
  - Files: `tests/architecture/test_surface_counts.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — glob `.claude/skills/*/SKILL.md` (expect 53) and `.claude/agents/*.md` (expect 19; 9 `ai-*`), assert against the counts stated in CLAUDE.md (regex-extracted) and `manifest.yml` totals. Model on `test_canonical_events_count.py` locked-constant style.
  - Gate: fails against current `agents.registry` claim / count mismatch.

- [ ] T-2.2 — GREEN: correct CLAUDE.md to reference the directory (no registry)
  - Agent: build
  - Files: `CLAUDE.md:79-80` + §12 surface-index; then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): omit — judgment: remove the `agents.registry` claim; point at `.claude/agents/`+`.claude/skills/`; distinguish 9 user-facing `ai-*` from the review/verifier families. Regenerate mirrors.
  - Gate: T-2.1 passes; `sync_command_mirrors --check` clean.

- [ ] T-2.3 — RED: every hook-read `AIENG_*`/`AIE_*` env var is documented
  - Agent: build
  - Files: `tests/architecture/test_env_var_docs.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — glob hook scripts, `re.findall` `os.environ.get`/`os.getenv` for `AIENG_`/`AIE_` reads, assert each appears in the CLAUDE.md Runtime tunables table. (Exploration found undocumented: `AIENG_INSTINCT_BATCH_DISABLED`, `AIENG_RISK_ACCUMULATOR_DISABLED`, `AIENG_RALPH_DISABLED`, `AIE_MCP_HEALTH_FAIL_OPEN`, `AIE_MCP_URL/CMD/RECONNECT_*`, et al.)
  - Gate: fails listing the undocumented vars.

- [ ] T-2.4 — GREEN: document the escape-hatch env vars + risk annotation
  - Agent: build
  - Files: `CLAUDE.md` (Runtime tunables table); then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — add each var with default; annotate `AIE_MCP_HEALTH_FAIL_OPEN` as converting the MCP health gate from blocking to pass-through. Regenerate mirrors.
  - Gate: T-2.3 passes.

### 2b — decision-store.json full migration (17 callers → state.db, then delete)

- [ ] T-2.5 — Hooks read state.db via stdlib sqlite3 (RED+GREEN)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/mcp-health.py:166-212`, `prompt-injection-guard.py:534-629`; tests under `tests/unit/hooks/`
  - Principles applied: §10.8 Hexagonal, §10.5 TDD
  - Patch (deterministic): omit — judgment: add a stdlib `sqlite3` reader (sealed-contract-safe) for the `decisions` table; RED test asserts hooks resolve decisions from state.db with no JSON present.
  - Gate: hooks pass with `decision-store.json` absent.

- [ ] T-2.6 — Migrate direct-JSON readers to the repository/state.db
  - Agent: build
  - Files: `src/ai_engineering/policy/checks/risk.py:15`, `commands/workflows.py:655`, `maintenance/report.py:400-408`
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Patch (deterministic): omit — judgment: replace direct `read_json_model(ds_path, DecisionStore)` with `DurableStateRepository.load_decisions()`. RED tests per caller first.
  - Gate: each caller reads from state.db; JSON-read removed.

- [ ] T-2.7 — Migrate the audit-chain verifiers (delicate)
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/audit_cmd.py:129,182`, `doctor/phases/state.py:290-300`
  - Principles applied: §10.8 Hexagonal, §10.6 SDD
  - Patch (deterministic): omit — judgment: these hash-chain-verify the JSON as an append-only audit artifact. Re-point verification at the canonical audit source (tier-1 NDJSON / state.db projection) per `docs/persistence-doctrine.md`. RED test replays a known chain. **FLAG: most regression-prone task — keep isolated in its own commit.**
  - Gate: audit-chain verification passes against the canonical source; no JSON dependency.

- [ ] T-2.8 — Stop dual-write; drop JSON from the control plane
  - Agent: build
  - Files: `src/ai_engineering/state/repository.py:154-168`, `state/context_packs.py:35`, `config/framework_defaults.py:25`
  - Principles applied: §10.4 DRY (single SSOT), §10.2 YAGNI
  - Patch (deterministic): omit — judgment: remove the `write_json_model(decision_store_path,...)` mirror from `save_decisions`; remove `decision-store.json` from `_AUTHORITATIVE_CONTROL_PLANE` and from session-context injection.
  - Gate: writes go only to state.db; sessions no longer ingest the JSON.

- [ ] T-2.9 — CI caller-count ratchet
  - Agent: build
  - Files: `tests/architecture/test_decision_store_ratchet.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — grep src/+hooks for `decision-store.json`/`decision_store_path` reads; assert the count ≤ a locked ceiling that only decreases. Guards every PR against regression mid-migration.
  - Gate: count monotonically decreases; never increases.

- [ ] T-2.10 — Delete decision-store.json + residue
  - Agent: build
  - Files: `src/ai_engineering/state/state_db.py:72` (`_DEPRECATED_JSON_FALLBACKS`), `state/observability.py:602`, `validator/categories/manifest_coherence.py:52`, installer cleanup (already `unlink(missing_ok=True)`)
  - Principles applied: §10.2 YAGNI, §10.4 DRY
  - Patch (deterministic): omit — remove the JSON from fallback/observability/coherence path maps; confirm the installer cleanup unlink remains. CHANGELOG hard-delete entry.
  - Gate: repo-wide grep shows zero JSON readers; T-2.9 ceiling at 0.

### 2c — gate-findings reconciliation (OQ1 resolved)

- [ ] T-2.11 — Remove the reader-less gate_findings SQLite seed/table
  - Agent: build
  - Files: `src/ai_engineering/state/migrations/0002_seed_from_json.py:96-128,227`, `state/control_plane.py:154-156`, `tests/integration/state/test_db_migration.py:133`, `docs/persistence-doctrine.md:155-158`
  - Principles applied: §10.4 DRY (single SSOT), §10.2 YAGNI
  - Patch (deterministic): omit — judgment: drop `_seed_gate_findings`; remove the `gate_findings` table (or document as removed); update the migration test; align the doctrine to JSON-canonical with no transitional SQLite pressure.
  - Gate: doctrine + code agree; JSON is the single store; migration test green.
  - **Wave-2 acceptance**: G2 (doc claims CI-asserted) + G3 (one canonical store per datum).

---

## Phase 3 — Wave 3: One obvious way (D-147-11, D-147-12)

Concern: no ambiguous trigger; one branch-cleanup. No skill folds/deletes (surface count stays). Agent: build.

- [ ] T-3.1 — De-collide contested trigger phrases
  - Agent: build
  - Files: `.claude/skills/{ai-prose,ai-marketing,ai-verify,ai-governance,ai-security,ai-explore,ai-explain,ai-onboard,ai-code,ai-build}/SKILL.md` descriptions; then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.3 SOLID (single-responsibility trigger), §10.7 Clean Code
  - Patch (deterministic): omit — assign each contested phrase ("write a blog post", "pre-release", "architecture", "scan for security issues", "implement it"/"implement this") to exactly one skill; others cross-reference. No merges.
  - Gate: no listed trigger phrase appears in >1 description (verifiable form of G4); mirrors clean.

- [ ] T-3.2 — Surface ai-spec-draft in the canonical chain; clarify ai-code vs ai-build
  - Agent: build
  - Files: `CLAUDE.md` §11 chain; `.claude/skills/ai-spec-draft/SKILL.md`, `ai-code`/`ai-build` descriptions; then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — note ai-spec-draft as the optional pre-step; state the code-subcomponent vs implementation-gateway boundary explicitly. Regenerate mirrors.
  - Gate: chain doc shows the pre-step; mirrors clean.

- [ ] T-3.3 — RED: single branch-cleanup implementation
  - Agent: build
  - Files: `tests/architecture/test_branch_cleanup_single_impl.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert exactly one implementation import path for branch cleanup.
  - Gate: fails against the two current paths.

- [ ] T-3.4 — GREEN: delegate maintenance branch-cleanup to cleanup branches
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/maintenance.py:123-149` (delegate), `cli_factory.py:414`, CHANGELOG
  - Principles applied: §10.4 DRY, §10.1 KISS
  - Patch (deterministic): omit — judgment: make `maintenance branch-cleanup` a thin delegation to `cleanup branches`; CHANGELOG documents the consolidation (no shim alias).
  - Gate: T-3.3 passes.
  - **Wave-3 acceptance**: G4 (one obvious surface; surface count unchanged).

---

## Phase 4 — Wave 4: Deterministic "done" (D-147-13) — NARROWED

Concern: reproducible STOP + method-tagged findings. Exploration confirmed the count-threshold STOP is already deterministic; only `quality.md` Step 2d condition 4 is LLM-judged. Agent: build.

- [ ] T-4.1 — RED: every verify Finding carries `method: deterministic|llm`
  - Agent: build
  - Files: `tests/unit/test_verify_service.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert each finding exposes `method` ∈ {deterministic, llm}; deterministic for tool runners, llm for `verifier-acceptance`.
  - Gate: fails (no field today).

- [ ] T-4.2 — GREEN: add `method` to the Finding model + verify contract
  - Agent: build
  - Files: `src/ai_engineering/verify/` Finding model + assembly; `.claude/skills/ai-verify/SKILL.md:64-70` output contract; then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): omit — tag tool-runner findings `deterministic`, `verifier-acceptance` findings `llm`; document the field in the contract.
  - Gate: T-4.1 passes; mirrors clean.

- [ ] T-4.3 — Make the one LLM STOP element deterministic/advisory (RED+GREEN)
  - Agent: build
  - Files: `.claude/skills/ai-build/handlers/quality.md:124-141` (Step 2d condition 4); replay test under `tests/`
  - Principles applied: §10.6 SDD, §10.5 TDD
  - Patch (deterministic): omit — judgment: condition 4 ("requires product decision/architecture redesign/destructive migration") becomes a deterministic signal OR is reclassified as advisory-only (cannot silently auto-block or auto-pass). RED replay test: same diff → same STOP verdict across runs.
  - Gate: identical-diff replay is reproducible.
  - **Wave-4 acceptance**: G5 (reproducible STOP; method-tagged findings).

---

## Phase 5 — Wave 5: Poka-yoke the conventions (D-147-14..17)

Concern: CI enforces §10.x citation, naming grammar, suppression DEC-binding; destructive verbs default to dry-run. Agent: build.

- [ ] T-5.1 — Backfill §10.x into Workflow-without-citation skills
  - Agent: build
  - Files: the ~22 `.claude/skills/*/SKILL.md` with a `## Workflow` lacking a `§10.x` anchor; then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — add the most relevant `§10.x` anchor to each Workflow. Mechanical but per-file judgment on which anchor.
  - Gate: every Workflow section cites §10.x.

- [ ] T-5.2 — RED+GREEN: CI test "Workflow ⇒ §10.x"
  - Agent: build
  - Files: `tests/architecture/test_workflow_principle_citation.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — for each SKILL.md, if a `## Workflow` section exists, assert it contains `§10.\d`. Model on `test_canonical_events_count.py`. Runs after T-5.1 (intra-wave dep).
  - Gate: green post-backfill; fails if any Workflow drops its citation.

- [ ] T-5.3 — Codify + CI-lock the naming grammar (confirm zero renames)
  - Agent: build
  - Files: `.claude/skills/ai-scaffold/SKILL.md`, `CONSTITUTION.md`, `tests/architecture/test_skill_naming_grammar.py` (new); then `python scripts/sync_command_mirrors.py`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — document the candidate rule (`ai-` + lowercase-kebab + verb|noun); CI asserts all skill dirs match. Confirm with operator that no renames are needed before touching any skill dir (OQ2).
  - Gate: all 53 skills satisfy the locked grammar; zero renames.

- [ ] T-5.4 — RED: `cleanup branches` no-flag deletes nothing
  - Agent: build
  - Files: `tests/unit/test_cleanup.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — invoke with no mode flag; assert no deletion, a plan is printed, confirmation required.
  - Gate: fails against current `merged=True` default.

- [ ] T-5.5 — GREEN: dry-run-by-default for destructive CLI verbs
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/cleanup.py:257-260,297-300`
  - Principles applied: §10.7 Clean Code (pit of success)
  - Patch (deterministic): omit — judgment: no-flag prints plan + requires confirm; deletion is opt-in.
  - Gate: T-5.4 passes.

- [ ] T-5.6 — RED: nosemgrep suppression without dec_id fails allowlist load
  - Agent: build
  - Files: `tests/unit/test_suppression_allowlist.py` (or existing no_suppression tests)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — a `nosemgrep_hash` entry with `dec_id: ""` → load raises/blocks; a non-security entry with empty dec_id → warning only (not block, until 2026-07-10).
  - Gate: fails against current accept-empty behavior.

- [ ] T-5.7 — GREEN: phased suppression DEC-binding
  - Agent: build
  - Files: `.ai-engineering/suppression-allowlist.yml:20-26,64-641`, allowlist loader, `src/ai_engineering/no_suppression/`
  - Principles applied: §10.8 Hexagonal (fail into the port), §10.6 SDD
  - Patch (deterministic): omit — hard-require DEC on `nosemgrep_hash` (author the DECs for current nosemgrep entries in this PR); per-entry warning for the other 50+ empty `dec_id` until expiry 2026-07-10.
  - Gate: T-5.6 passes; gate not globally blocked by the non-security backlog.
  - **Wave-5 acceptance**: G6 (conventions CI-enforced; destructive verbs dry-run-by-default).

---

## Cross-cutting gates (every wave)

- CHANGELOG documents each behavior flip + hard-rename; zero backwards-compat shims (G7; `CONSTITUTION.md:70-73`).
- Any canonical-payload edit (CLAUDE.md / SKILL.md / CONSTITUTION.md) runs `python scripts/sync_command_mirrors.py`; `--check` is clean before PR.
- Hot-path budgets preserved (pre-commit <1s, pre-push <5s) for Wave-1 gate changes.
- `regenerate-hooks-manifest.py` run after any hook-script edit (Waves 1, 2).

## Self-review (Clean Code §10.7) — 2 iterations

- **Iter 1** — Found Wave 4 over-scoped (spec implied a STOP rewrite; exploration shows STOP is already deterministic). Narrowed Phase 4 to the `method` tag + the single LLM condition. Resolved.
- **Iter 1** — Found the decision-store migration under-scoped at 12 callers; corrected to 17 with the hook (stdlib sqlite3) + audit-chain sub-classes split into distinct tasks (T-2.5..T-2.10). Resolved.
- **Iter 2** — Verified TDD pairing (every GREEN has a preceding RED), agent assignments are all `build` (code-write; verify/guard run as gates inside autopilot's Phase 5), and no task exceeds single-concern. Confirmed the two spec Open Questions are resolved/answered above. No remaining concerns.

## Next

Operator approves this plan, then runs **`/ai-autopilot`** (executor route: autopilot — 5 concerns, ~45 files). Autopilot deep-plans each wave into a sub-spec, builds the DAG, implements in waves, runs the bounded fail-loud quality loop, and delivers per-wave PRs (Wave 1 first).
