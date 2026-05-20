---
spec: spec-147
title: Obvious by Default — fail-loud safety and legibility refactor
status: approved
effort: large
summary: "Make the obvious reading of every load-bearing ai-engineering surface the safe one: seal fail-open gates to fail loud, reconcile docs with code, de-collide skill triggers, make the quality-loop STOP deterministic, finish the decision-store SSOT migration, and enforce conventions via CI."
refs:
  - doc: .ai-engineering/specs/drafts/obvious-by-default-brief.md
---

# Spec 147 — Obvious by Default

## Summary

ai-engineering is governance-grade, but in several load-bearing places the *obvious reading* of a surface diverges from its *true behavior*, and the divergence is unsafe. The framework that preaches fail-loud ships `_DEFAULT_MODE = "warn"` for hook integrity (`.ai-engineering/scripts/hooks/_lib/integrity.py:40`), where three docs and the constant disagree; the no-suppression gate silently skips itself on `ImportError` (`src/ai_engineering/cli_commands/gate.py:138-140`); the secret scanner returns a clean verdict when its binary is broken (`src/ai_engineering/verify/service.py:307-313`); `CLAUDE.md:79-80` cites a manifest key (`agents.registry`) that does not exist; decisions are dual-written to `state.db` and a deprecated `decision-store.json` that is still fed to LLM sessions as authoritative; skill trigger phrases collide with no deterministic discriminator; and the bounded quality-loop STOP verdict depends on LLM judgment, so the same diff can be judged differently across runs. This spec applies poka-yoke (make the wrong reading impossible or immediately visible) across five independent waves: seal the fail-open gates, reconcile docs with code, give each task one obvious surface, make "done" deterministic, and enforce conventions in CI. It is an excellence refactor on a healthy base, not a rescue.

## Goals

- **G1 — No green gate on a broken tool.** With all `AIENG_*`/`AIE_*` env vars unset, no gate or hook exits 0 when its tool is absent, broken, or its input malformed (E-1..E-10). Hook integrity defaults to `enforce`; a drifted hook exits non-zero.
- **G2 — Every doc claim resolves to an on-disk fact.** CI asserts the documented agent/skill counts equal files on disk and that every behavior-changing `AIENG_*`/`AIE_*` env var read by a hook appears in the CLAUDE.md tunables table (E-11, E-12).
- **G3 — One canonical store per datum.** `decision-store.json` is fully migrated to `state.db` (all readers rewired, including the risk-acceptance gate reader) and deleted; the `gate-findings` transitional dual-store is reconciled to a single canonical store consistent with the persistence doctrine (E-13..E-15).
- **G4 — One obvious surface per task.** No skill trigger phrase routes ambiguously — a human can name the single skill for any phrase in the descriptions (verifiable form: no listed trigger phrase appears in more than one skill description); there is exactly one branch-cleanup implementation (E-16..E-23). The skill/agent surface count is unchanged (no folds, no new surfaces).
- **G5 — Deterministic "done".** The STOP verdict for an identical diff is reproducible: deterministic tool signals are the sole auto-STOP authority; every `/ai-verify` finding is tagged `method: deterministic|llm` (E-25, E-26).
- **G6 — Conventions enforced, not hoped.** CI enforces §10.x citation in skill Workflows, a documented naming-grammar rule, and DEC-binding on suppression entries; destructive CLI verbs default to dry-run/confirm (E-24, E-27..E-29).
- **G7 — Clean migration.** Every behavior flip and hard-rename is documented in CHANGELOG with zero backwards-compat shims (`CONSTITUTION.md:70-73`, `CLAUDE.md:110-112`).

## Non-Goals

- **No net-new skills or agents.** This is a safety/legibility refactor, not a feature wave.
- **No agent or skill registry.** The `.claude/agents/*.md` and `.claude/skills/*/SKILL.md` files on disk are the source of truth. The fix for E-11 corrects the doc to reference the directory and adds a CI file-count assertion — it does **not** introduce a manifest `agents.registry`/skill-registry key.
- **No skill folding, collapse, or deletion.** The surface count stays at its current value. Trigger collisions are resolved by sharpening descriptions and cross-referencing, never by merging skills (e.g., `ai-session-watch` is **not** folded into `ai-learn`).
- **No rewrite of the persistence doctrine.** Only its violations are in scope; the four-tier model itself is sound.
- **No performance / token-budget tuning** (covered by `framework-performance-hardening-brief.md`).
- **No mirror diet / token reduction** (covered by `skills-agents-excellence-v2-brief.md`).
- **No change to canonical-chain semantics.** Only the chain's legibility (off-chain visibility of `ai-spec-draft`) is touched.
- **E-30 (ai-advise/ai-guard identity) and E-31 (instinct-observe hot-path breadth) are deferred.** They are catalogued in the brief but unscheduled in its roadmap; out of scope for spec-147.

## Decisions

### D-147-01: One spec, five waves, autopilot ships per-wave PRs

spec-147 covers all five waves. `/ai-plan` decomposes it and routes to `/ai-autopilot`, which ships each wave as its own single-concern PR. Wave 1 (the CRITICAL fail-open holes) is sequenced first. Waves are independent and do not block each other except Wave 5's §10.x backfill, which lands before its enforcing CI test.

**Rationale**: The brief is one cohesive thesis whose waves already map to single-concern PRs (brief §4/§6). Autopilot's wave-shipping gives the blast-radius isolation of separate specs without the 5× brainstorm/plan overhead or the loss of the unifying contract. Wave 1 is the only active safety emergency, so it leads.

### D-147-02: Hard-flip hook integrity to `enforce` with a loud escape-hatch hint

Flip `_DEFAULT_MODE` to `"enforce"` (`integrity.py:40`); regenerate `.ai-engineering/state/hooks-manifest.json` in the same PR; the first drifted-hook run emits a loud, single-line hint naming the `AIENG_HOOK_INTEGRITY_MODE=warn` dev escape hatch and the `regenerate-hooks-manifest.py` command.

**Rationale**: The fail-loud thesis requires the *default* to be the safe one; three sources already document `enforce` as the default (`integrity.py:9`, `integrity.py:18-21`, `CLAUDE.md:183`). A one-release deprecation period is itself a fail-open compromise. The `warn` escape hatch already exists for fast-moving dev workflows, so the migration cost is bounded and self-service.

### D-147-03: Broken tool equals BLOCKER, never a clean verdict

`ImportError` on `no_suppression.cli` (`gate.py:138-140`) and `FileNotFoundError` / non-zero exit with empty stdout / `JSONDecodeError` on gitleaks (`verify/service.py:53-54`, `:307-313`) all raise a BLOCKER finding and exit non-zero, with a crisp error naming the missing tool and its install command.

**Rationale**: A gate that cannot run its check has not passed — it has failed to evaluate. Treating tool-absence as "clean" is the exact trap the mantra forbids. Naming the missing tool + install command honors Anthropic's "solve, don't punt" (turn the hard failure into an actionable one).

### D-147-04: Wire risk-acceptance TTL into the pre-push hot path

`gate_pre_push` calls the risk-acceptance check in strict mode so an expired DEC exits 1 (`gate.py:91-99`, `:118-127`, `:167-195`). The existing OPA TTL policy (`.ai-engineering/policies/risk_acceptance_ttl.rego:19-25`) is the reference for the deny condition.

**Rationale**: Expired risk acceptances currently only `warning()` and are never consulted in strict gate paths — an accepted-then-expired risk silently becomes a permanent hole. The policy logic is already correct; only its wiring is missing.

### D-147-05: Loud config errors; silent defaults reserved for genuinely-absent files

A malformed `manifest.yml` or state file exits 1 with a one-line named error rather than returning all-defaults (`config/loader.py:55-57`, `state/repository.py:48-50`). The stack-drift middleware narrows its bare `except Exception` to expected types (`cli_factory.py:237-245`). A *missing* file may still resolve to defaults; a *corrupt* one may not.

**Rationale**: A malformed config that is indistinguishable from a missing one means a typo silently disables governance. Distinguishing "absent" (legitimate default) from "broken" (must fail loud) is the predictability fix.

### D-147-06: Convert silent hook swallows to visible signals

Formatter failure (`auto-format.py:30-34`, `:242-249`), checkpoint/resume-state write failure (`runtime-stop.py:15-21`), and MCP-state persistence failure (`mcp-health.py:132-138`) emit a `hookSpecificOutput` warning instead of swallowing. `no-verify-guard.py` blocks (refuses) on an unparseable command rather than allowing it (`no-verify-guard.py:80-86`).

**Rationale**: The highest-frequency hooks currently swallow every error and exit 0, so a formatter that rewrites a file then fails to re-stage leaves an inconsistent tree with no signal, and an unparseable command bypasses the no-verify guard. Visible-but-non-blocking is the right default for formatters; fail-closed is the right default for a security guard parsing untrusted input.

### D-147-07: Correct the agent/skill count doc to point at the filesystem; CI counts files on disk

Rewrite `CLAUDE.md:79-80` (and the §12 surface-index counts) to stop claiming a `manifest.yml` `agents.registry` exists. The doc references the `.claude/agents/` and `.claude/skills/` directories as the source of truth and distinguishes the user-facing `ai-*` family from the internal review/verifier families. A CI test asserts the documented counts equal the files on disk. Because CLAUDE.md is canonical payload, the IDE mirrors (`AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.codex/`, `.gemini/`) are regenerated via `scripts/sync_mirrors/core.py` in the same PR so surface-parity CI stays green; the same regeneration applies to the SKILL.md description edits (D-147-11) and the CONSTITUTION.md edit (D-147-15).

**Rationale**: Operator decision — no registry is introduced. The filesystem is already the canonical surface; a manifest registry would be redundant structure that can itself drift. Making the doc point at the directory and pinning the count with a CI assertion makes the obvious reading true without inventing a new SoT.

### D-147-08: Document the escape-hatch env vars; CI greps hooks for completeness

Add the ≥8 behavior-changing `AIENG_*`/`AIE_*` env vars read by hooks (E-12) to the CLAUDE.md Runtime tunables table with defaults, including an explicit risk annotation on `AIE_MCP_HEALTH_FAIL_OPEN` (it converts the MCP health gate from blocking to pass-through). A CI test greps hook sources for `os.environ`/`getenv` reads of `AIENG_*`/`AIE_*` and asserts each appears in the table.

**Rationale**: An undocumented flag that disables a security gate is a silent trap; a security-relevant env var must be discoverable from the doc that claims to be the agent's source of truth. The CI grep makes the table self-maintaining.

### D-147-09: Finish the full decision-store migration to state.db and delete the JSON

Migrate all Decision view-model callers (the ~12 noted at `state/repository.py:157-163`) to read from `state.db`, including the risk-acceptance gate reader at `gate.py:169` (`_check_risk_inline` currently reads `decision-store.json`). Stop dual-writing in `save_decisions` (`state/repository.py:154-168`); remove `decision-store.json` from `_AUTHORITATIVE_CONTROL_PLANE` (`state/context_packs.py:32-36`) and from session context injection (`config/framework_defaults.py:21-25`); delete the JSON file. A CI caller-count ratchet guards the migration: the count of remaining JSON readers may only decrease, never increase.

**Rationale**: Operator decision — go deep and close E-13/E-14 completely rather than the surgical interim. `state.db` is already the documented canonical store; the JSON is both a dual-write (SSOT violation) and, worse, fed to LLM sessions as ground truth (predictability violation). The caller-count ratchet converts the migration risk into an incremental, CI-guarded sequence so no PR can regress it.

### D-147-10: Reconcile the gate-findings transitional dual-store to one canonical store

Resolve E-15 by aligning `gate-findings` to the persistence doctrine's declared primary (JSON, per `docs/persistence-doctrine.md:155-158`): either remove the non-primary SQLite seed/table (`state/migrations/0002_seed_from_json.py:221-227`, `state/control_plane.py:154-156`) if a caller audit shows no readers, or label the SQLite projection as a derived cache with a named rebuild command. The caller audit runs in `/ai-plan`.

**Rationale**: The doctrine already names JSON primary, yet a migration still seeds a SQLite table and control-plane code treats the JSON as residue — transitional pressure that violates single-SSOT-per-datum. Unlike decisions (where state.db is canonical), the doctrine here points the other way, so the fix is to make the doctrine's stated primary authoritative and either delete or explicitly label the other. The keep-vs-remove choice depends on a reader audit, deferred to planning (see Open Questions).

### D-147-11: De-collide skill triggers by assignment + cross-reference; no folds

Assign each contested trigger phrase to exactly one skill, with the others cross-referencing it (E-16..E-20): e.g., "write a blog post" → one of `ai-prose`/`ai-marketing`; "pre-release" → one of `ai-verify`/`ai-governance`/`ai-security`; "architecture" → one of `ai-explore`/`ai-explain`/`ai-onboard`; "scan for security issues" → one of `ai-verify`/`ai-security`; the `ai-code`/`ai-build` "implement" boundary stated explicitly. Make `ai-spec-draft` visible in the canonical chain as the optional pre-step (E-21). The three learning skills (`ai-learn`, `ai-session-watch`, `ai-skill-improve`) keep distinct ownership via sharpened descriptions (E-22). No skill is merged, folded, or deleted.

**Rationale**: Operator decision — preserve surface count and muscle memory; fix ambiguity, do not reorganize. Anthropic's rule applies: if a human cannot say which skill fires, neither can the agent. De-collision is a description edit with no behavior loss, only routing clarity. The precise phrase→skill assignments are a planning detail (`/ai-plan`).

### D-147-12: One branch-cleanup implementation (hard-rename)

Collapse the two overlapping entry points to a single implementation: `maintenance branch-cleanup` (`cli_factory.py:414`, `maintenance.py:123-149`) becomes a thin delegation to the richer `cleanup branches` path (`cli_factory.py:426`, `cleanup.py:219-300`). CHANGELOG documents the consolidation; no alias is retained beyond the documented delegation. An architecture test asserts a single implementation import.

**Rationale**: Two public entry points with two orchestration paths for one operation violate "one obvious way" and double the maintenance/divergence surface. Delegation (not duplication) is the DRY fix; hard-rename + CHANGELOG honors the no-shim rule.

### D-147-13: Deterministic layer is the sole auto-STOP authority; tag every finding by method

Split the bounded quality-loop STOP decision (E-25): deterministic tool signals (exit codes → BLOCKER/CRITICAL) are the only thing that auto-STOPs. The LLM acceptance layer (`verifier-acceptance`) escalates to the operator as advisory and operator-confirmable, but can neither silently pass nor silently auto-block. Every `/ai-verify` finding carries `method: deterministic|llm` in its output contract (E-26) so callers can threshold the two classes differently.

**Rationale**: Bazel-style hermeticity — the same diff must yield the same STOP verdict. LLM eligibility judgment in the STOP path makes shipping non-reproducible. The LLM signal is preserved (it still surfaces and can prompt an operator STOP) but is removed from the *automatic* gate authority. The `method` tag is a prerequisite: without it, callers cannot tell which findings are reproducible.

### D-147-14: CI-enforced §10.x citation in skill Workflows (backfill first)

Add a CI test (modeled on `tests/unit/hooks/test_canonical_events_count.py`) that fails if any skill's `## Workflow` section lacks a §10.x anchor. Backfill the skills that currently have a Workflow section without a citation before the test is switched on.

**Rationale**: The documented convention (`.ai-engineering/reference/principles.md:15-17`) currently holds in a small minority of skills. A convention enforced by hope is not a convention; a failing-first CI test is the poka-yoke. Backfill-before-enforce keeps the cutover green.

### D-147-15: Document and CI-enforce a naming-grammar rule; normalize outliers by hard-rename

Define a naming-grammar rule for skills (the surface currently mixes action-oriented and noun-oriented names with no cited discriminator, E-28), document it in `ai-scaffold` and CONSTITUTION.md, add a CI check, and normalize the outliers via hard-rename. The exact grammar/discriminator is settled in `/ai-plan` (see Open Questions).

**Rationale**: Names that do not predict behavior force readers to memorize exceptions (Clean Code violation). A documented, enforced grammar makes the name a reliable signal. The rule's precise wording is a HOW detail deferred to planning, but the decision to have one and enforce it is settled here.

### D-147-16: Dry-run-by-default for destructive CLI verbs

`cleanup branches` with no mode flag prints a plan and requires explicit confirmation rather than silently activating `merged = True` and deleting (`cleanup.py:257-260`, `:297-300`). A test asserts a no-flag invocation deletes nothing.

**Rationale**: A destructive default with opt-in `--dry-run` is the inverse of the pit-of-success; the safe action must be the default one. Confirm-before-destroy matches the framework's own care-with-irreversible-actions posture.

### D-147-17: Phased suppression DEC-binding — security rules hard now, the rest by expiry

Security-rule suppressions (`nosemgrep_hash`, `.ai-engineering/suppression-allowlist.yml:20-26`) are hard-required to carry a DEC immediately: a missing `dec_id` fails the allowlist load. The other 50+ `dec_id: ""` entries (`:64-641`) emit per-entry warnings on every gate run now and hard-block once their DECs are authored or the entries expire (2026-07-10). The DECs for any nosemgrep entries are authored in the same PR that enables the hard check.

**Rationale**: Operator decision — split the security-critical subset from the churny backlog. Hard-blocking all 50+ empty-`dec_id` entries at once would be a self-inflicted gate outage; warning-only on the security rules leaves the highest-stakes suppressions unbound for the whole window. Phasing binds the dangerous subset now and ratchets the rest to a dated deadline the allowlist already implies.

## Risks

- **Integrity `enforce` flip blocks dev sessions with drifted hooks** (Med likelihood / Med impact): ship with a loud first-run hint naming the `AIENG_HOOK_INTEGRITY_MODE=warn` escape hatch and the `regenerate-hooks-manifest.py` command; regenerate the manifest in the flip PR.
- **Broken-tool-blocks turns a missing binary into a hard CI failure** (High / Med): intended behavior, but every such failure must name the missing tool and its install command so the failure is actionable, not cryptic.
- **Full decision-store migration touches ~12 callers including the risk gate reader** (Med / High): land behind the CI caller-count ratchet (count may only decrease); migrate incrementally; replay the risk-gate behavior against expired/expiring-DEC fixtures before deleting the JSON. This is the highest-risk wave given the operator chose the full migration over the surgical interim.
- **Skill trigger reassignment breaks operator muscle memory** (Med / Low): CHANGELOG + cross-references; no behavior loss, only routing clarity. Lower than the brief's original estimate because no skills are folded.
- **STOP-determinism split changes which work auto-escalates** (Med / Med): replay-test the verdict on a corpus of past diffs before cutover to confirm the deterministic layer reproduces prior STOP decisions.
- **§10.x and naming backfill is churny** (High / Low): mechanical; land each backfill in one PR behind the CI test that defines its "done".
- **Suppression DEC-binding hard-check blocks the gate if a nosemgrep entry lacks a DEC** (Med / High): author the required DECs in the same PR that flips the security-rule check to hard; keep the non-security backlog on per-entry warnings until 2026-07-10.
- **gate-findings caller audit reveals readers that complicate the JSON-canonical choice** (Low / Med): the audit runs in `/ai-plan` and must fail loud (block the decision) if readership is ambiguous, rather than guessing.
- **Canonical-payload edits drift the IDE mirrors** (High / Low): editing CLAUDE.md, skill descriptions, or CONSTITUTION.md without regenerating the mirrors fails the surface-parity CI (`test_surface_parity.py`). Regenerate via `scripts/sync_mirrors/core.py` in the same PR as each canonical edit.

## References

- doc: .ai-engineering/specs/drafts/obvious-by-default-brief.md
- doc: .ai-engineering/specs/drafts/framework-performance-hardening-brief.md
- doc: .ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md
- doc: https://en.wikipedia.org/wiki/Poka-yoke
- doc: https://peps.python.org/pep-0020/
- doc: https://www.jamesshore.com/v2/blog/2004/fail-fast
- doc: https://www.anthropic.com/engineering/writing-tools-for-agents
- doc: https://bazel.build/basics/hermeticity

## Open Questions

- **gate-findings keep-vs-remove (D-147-10)**: does the SQLite seed/table have live readers? If yes, label it a derived cache with a rebuild command; if no, remove the seed/table. Resolved by a caller audit in `/ai-plan`.
- **Naming-grammar rule wording (D-147-15)**: what is the exact discriminator (e.g., imperative-action vs domain-noun) and which existing skills are the outliers to normalize? The decision to have and enforce a rule is settled; its precise text is authored in `/ai-plan` before the backfill.
