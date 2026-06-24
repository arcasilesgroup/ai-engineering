---
title: "Plan — spec-175 ai-research Tier-3 NotebookLM CLI migration"
spec: spec-175
slug: tier3-notebooklm-cli-migration
status: approved
pipeline: full
execution_route:
  version: 1
  spec: spec-175
  executor: build
  automation: build
  concern_count: 1
  estimated_files: 6
  reason: "Single concern (Tier-3 provider model: MCP -> notebooklm-py CLI) but a behavior change with a large lockstep helper + test rewrite (helper 20.8K, tier3 test 36.5K, resilience test couples Tier-3), handler/SKILL docs, tunable doc edits, and mirror propagation. Judgment-heavy -> mid-tier dispatch."
  safe_next_command: "/ai-build"
safe_next_command: "/ai-build"
---

# Plan — spec-175: Tier-3 NotebookLM CLI migration

## Architecture

Pattern: `ad-hoc` rewrite of the Tier-3 launch+harvest functions and their
lockstep tests; the `Tier3Result` output shape and naming helpers
(`topic_slug`/`hash6`/`notebook_title`/`should_launch_tier3`) are UNCHANGED, so
the synthesize handler (consumes `sources_discovered`) is untouched (Non-Goal).

Provider model change in `tests/integration/_ai_research_tier3_helper.py`:

- **Capability gate:** inject a `doctor_probe() -> bool` (runs `notebooklm
  doctor`, exit 0 = available) replacing `_notebooklm_available(nlm_list)`.
- **`tier3_launch(query, *, timestamp_iso, doctor_probe, create_notebook,
  add_research, reuse_notebook=None, deep_timeout_sec)`:** probe doctor →
  degrade if unavailable; resolve notebook (reuse or `create_notebook(title)`);
  `add_research(notebook_id, query, deep_timeout_sec)` launches the DETACHED
  CLI job `notebooklm source add-research "<q>" -n <id> --from web --mode deep
  --import-all --timeout <deep_timeout_sec> --json` and returns a job handle.
  Returns `{notebook_id, job, degraded, warnings}`.
- **`tier3_harvest(launch, *, wait_for_job, read_result, wait_budget_sec,
  ask=None)`:** `wait_for_job(job, timeout=wait_budget_sec) -> status`
  ("completed"|"failed"|"timeout"|"auth_required") — a BLOCKING bounded wait on
  the detached job that REPLACES the poll-loop + capped back-off entirely
  (D-175-02 native wait; retires the D-172-05 re-poll and the
  `POLL_INTERVAL_SEC` cadence). On completed → `read_result(notebook_id)`
  parses the `--json` report + imported sources; on timeout → degrade + preserve
  `notebook_id` (detached job keeps running + importing; `--reuse-notebook`
  recovers); auth_required → degrade with login warning.
- **Removed:** `poll_status`, `clock`, `sleep`, `_DEFAULT_POLL_INTERVAL_SEC`,
  `_POLL_INTERVAL_CAP_SEC`, the `_with_retry` MCP wrap (CLI `--timeout` owns the
  deadline), and the `nlm_*` callable types.

`--json` output (confirmed on the CLI) means structured parsing, not text
scraping — the spec's parsing-brittleness risk is mitigated.

## Phases

### Phase 1 — RED: rewrite the lockstep tests to the CLI model

- [x] T-1 — Rewrite `test_ai_research_tier3.py` for the CLI launch+harvest contract
  - Agent: build
  - Files: `tests/integration/test_ai_research_tier3.py`
  - Principles applied: §10.5 TDD (RED before GREEN), §10.7 Clean Code
  - Patch (deterministic): N/A — judgment rewrite. Concretely:
    - Replace `nlm_list/nlm_create_notebook/nlm_research/nlm_ask` mocks with
      `doctor_probe`, `create_notebook`, `add_research` (returns a fake job),
      `wait_for_job`, `read_result` fakes.
    - DELETE the MCP re-poll / back-off / status-streaming tests (D-175-02
      native wait removes them). Replace with: detached-launch builds the
      `source add-research --mode deep --import-all --timeout <N> --json` args;
      `wait_for_job` returns completed → report+imported sources fused;
      `wait_for_job` returns timeout → degraded + `notebook_id` preserved (job
      NOT killed); `doctor` non-zero → launch degraded, zero create/research.
    - Add an import-all assertion: the launched args include `--import-all` and
      `--timeout <deep_timeout_sec>`.
    - Keep: naming-helper tests (`topic_slug`/`hash6`/`notebook_title`) and
      `should_launch_tier3`.
  - Gate: `pytest tests/integration/test_ai_research_tier3.py` FAILS against the
    current MCP helper (RED proven).

- [x] T-2 — Update the Tier-3 cases in `test_ai_research_resilience.py`
  - Agent: build
  - Files: `tests/integration/test_ai_research_resilience.py:159,303` (the `notebooklm_auth_expired` + `notebooklm_absent` cases) and the import block (L30-31)
  - Principles applied: §10.5 TDD, §10.4 DRY (shared availability semantics)
  - Patch (deterministic): N/A — judgment. Re-express the two Tier-3 degrade
    cases against `doctor_probe` (auth-expired / absent → degrade, zero CLI
    mutation) instead of the `nlm_list` probe. Tier-1/Tier-3-NotebookLM
    fail-soft contract preserved.
  - Gate: file imports + the two cases reference the new CLI-shaped signature.

### Phase 2 — GREEN: rewrite the helper to the CLI model

- [x] T-3 — Rewrite `tier3_launch` + `tier3_harvest` in the lockstep helper
  - Agent: build
  - Files: `tests/integration/_ai_research_tier3_helper.py:140-507`
  - Principles applied: §10.1 KISS (native wait deletes the whole poll loop), §10.3 SOLID (injected deps, single concern), §10.5 TDD (make T-1/T-2 green)
  - Patch (deterministic): N/A — judgment rewrite per the Architecture API. Keep
    `Tier3Result`, naming helpers, `should_launch_tier3`. Swap MCP callables for
    the CLI-shaped injectables; replace the poll loop with `wait_for_job`;
    update the module docstring + `_UNAVAILABLE_WARNING` (drop the
    `notebooklm-skill` MCP login string → `notebooklm login` / `notebooklm
    doctor`). Build the `add_research` args incl. `--import-all`, `--mode deep`,
    `--from web`, `--timeout <deep_timeout_sec>`, `--json`.
  - Gate: `pytest tests/integration/test_ai_research_tier3.py tests/integration/test_ai_research_resilience.py` GREEN.

### Phase 3 — Docs: handler + SKILL describe the CLI model

- [x] T-4 — Rewrite `tier3-notebooklm.md` to the CLI launch/harvest
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/tier3-notebooklm.md`
  - Principles applied: §10.6 SDD (handler ↔ helper 1:1), §10.7 Clean Code
  - Patch (deterministic): N/A — prose. Backend → `notebooklm-py` CLI; launch =
    `source add-research --from web --mode deep --import-all --timeout <N>
    --json` detached; harvest = bounded `wait_for_job` (no re-poll); capability
    = `notebooklm doctor`; supersede D-172-05/08; document the import-all step.
  - Gate: no `mcp__notebooklm__nlm_*` / `nlm_research` / re-poll language remains
    in `tier3-notebooklm.md`; matches the helper.

- [x] T-5 — Update `SKILL.md` Tier-3 lines
  - Agent: build
  - Files: `.claude/skills/ai-research/SKILL.md:16,42,48,50,124`
  - Principles applied: §10.6 SDD, §10.4 DRY (canonical edited once; mirrors generated)
  - Patch (deterministic): N/A — prose. Tier-3 harvest step (L42), default-on
    probe (L48 → `notebooklm doctor`), `--reuse-notebook` (L50/124 → CLI `-n`),
    capability line (L16). Citation / 3-directions contract untouched.
  - Gate: SKILL.md Tier-3 text says CLI + import-all + doctor; no MCP `nlm_*`
    framing remains.

### Phase 4 — Tunables

- [x] T-6 — Add DEEP_TIMEOUT_SEC, retire POLL_INTERVAL_SEC (canonical source, NOT CLAUDE.md)
  - Agent: build
  - Files: the CLAUDE.md tunables source — `CANONICAL.md` or `scripts/sync_mirrors` `_CLAUDE_EXTRAS` (CLAUDE.md is generated; never hand-edit it); plus `.ai-engineering/manifest.yml` if the tunables are mirrored there
  - Principles applied: §10.4 DRY (single source → dev sync mirrors)
  - Patch (deterministic): N/A — locate the source first. Add
    `AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC` (default 1800; CLI `--timeout`); retire
    `AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC` (native wait — no poll loop); keep
    `AIENG_RESEARCH_NLM_WAIT_SEC` (harvest budget).
  - Gate: edits in the canonical source; `CLAUDE.md` regenerated by T-7 (not hand-edited).

### Phase 5 — Propagate mirrors

- [x] T-7 — Regenerate mirror + template surfaces via dev sync
  - Agent: build
  - Files: `.codex/`, `.opencode/`, `.github/`, `.agents/`, `src/ai_engineering/templates/project/...` (ai-research SKILL.md + tier3 handler), `CLAUDE.md` (regenerated)
  - Principles applied: §10.4 DRY, §10.6 SDD (mirror/template + CANONICAL→CLAUDE parity)
  - Patch (deterministic): N/A — run the generator:
    ```
    ai-eng dev sync
    ```
  - Gate: `dev sync` clean; CLAUDE.md tunables block shows DEEP_TIMEOUT_SEC and
    no POLL_INTERVAL_SEC; every ai-research mirror + template twin carries the
    CLI wording.

### Phase 6 — Verify

- [x] T-8 — Full Tier-3 + parity verification
  - Agent: verify
  - Files: `tests/integration/test_ai_research_tier3.py`, `test_ai_research_resilience.py`, `test_ai_research_skill_present.py` (read-only)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Gate: `pytest tests/integration/test_ai_research_tier3.py tests/integration/test_ai_research_resilience.py tests/integration/test_ai_research_skill_present.py` all green; `ai-eng gate run --mode=local` 0 findings; no handler↔helper drift; no stale MCP `nlm_*` references in the ai-research surface.

## Gate Criteria (plan-level)

- Tier-3 drives the `notebooklm-py` CLI (no `mcp__notebooklm__nlm_*`); deep
  research launches detached with `--import-all --mode deep --timeout <N>
  --json`; harvest is a bounded `wait_for_job` (no poll loop).
- Capability gate via `notebooklm doctor`; fail-soft degrade + `--reuse-notebook`
  preserved.
- Lockstep parity: `tier3-notebooklm.md` == `_ai_research_tier3_helper.py`.
- Tunables: `DEEP_TIMEOUT_SEC` added, `POLL_INTERVAL_SEC` retired, via the
  canonical source (CLAUDE.md regenerated, never hand-edited).
- All ai-research integration tests green; gate clean; mirrors regenerated.
- Non-Goals held: Tier 0/1/2, citation/3-directions contract, and the
  synthesize handler untouched.

## Quality Outcome

T-1..T-8 complete; one bounded quality-remediation pass consumed, then terminal reassessment PASS.

- **Implementation:** lockstep helper + tier3/resilience tests (RED→GREEN), handler + SKILL docs, tunable migration (`POLL_INTERVAL_SEC` → `DEEP_TIMEOUT_SEC` in `runtime_state.py` + template twin + `_CLAUDE_EXTRAS` + parity gate; hooks-manifest regenerated, sha verified MATCH), mirrors via `dev sync`.
- **Review (ai-review + adversarial validator):** verdict sound/ships-ready. One HIGH (harvest read-path fell through to `read_result` for non-terminal status — dead `_STATUS_COMPLETED`), 2 medium, 2 low.
- **Remediation (one bounded pass):** HIGH fixed — explicit `status != _STATUS_COMPLETED` degrade guard + parametrized test; M1 `build_add_research_cmd` pins the `--import-all`/`--mode deep` token sequence; M2 alias-parser coverage; L1 `notebook_title` inside try; L2 handler ceiling note.
- **Terminal reassessment:** no remaining blocker/critical/high. Tests 35 (trio) + 27 (tunables) + 47 (parity) green. `ai-eng gate run --mode=local` → 0 findings. Ruff clean. No suppressions.
- **Excluded from delivery:** `observations.yml` (pre-existing, owns PR #597). **Included:** the parked spec-174 (`specs/parked/` + approved `spec-174.json`) to preserve that design durably.

## Notes

- `--json` on the CLI de-risks output parsing (structured, not text).
- Tunable migration touched real code (`runtime_state.py` `_env_int` + parity gate), not doc-only as the plan first assumed — the build agent corrected this.
- spec-174 (Tier-2 fan-out) stays parked at
  `.ai-engineering/specs/parked/spec-174-tier2-fanout/`; restore after spec-175 ships.
