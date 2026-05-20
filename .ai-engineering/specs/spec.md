---
spec: spec-146
title: Framework Simplification — Less is More
status: approved
effort: large
summary: Make ai-engineering smaller and safer by fixing update ownership reads first, reconciling persistence docs, pruning only evidence-proven dead surfaces, and documenting implemented tunables without broad state migrations.
source_brief: .ai-engineering/specs/drafts/framework-simplification-less-is-more-brief.md
pr: arcasilesgroup/ai-engineering#530
---
# Spec 146 - Framework Simplification — Less is More

## Summary

The framework has accumulated complexity in three connected places — `ai-eng update` still loads ownership from a removed JSON sidecar, persistence docs describe some state tables too broadly, and cleanup candidates span `.ai-engineering/` data files, tunables docs, and Python modules with uneven caller evidence. This spec chooses a conservative less-is-more path — fix the operator-visible ownership bug first, align the persistence contract table by table, then delete or inline only surfaces proven non-load-bearing by inventory, tests, and CHANGELOG-backed hard-delete documentation.

## Goals

- Fix `ai-eng update` so deny/team/operator ownership rows in `state.db.ownership_map` block create/update decisions, including the case where an operator deletes a denied file and update must leave it absent.
- Add tested ownership read helpers that expose both raw SQLite rows and the updater-ready `OwnershipMap` view, with a one-time legacy JSON fallback only when SQLite has no rows.
- Reconcile `docs/persistence-doctrine.md` and `src/ai_engineering/state/state_db.py` so each `state.db` table is classified as canonical lifecycle state, derived cache, or transitional/placeholder state.
- Keep `gate-findings.json` as the canonical gate/risk/verify artifact for this spec, and document `state.db.gate_findings` as non-primary placeholder/transitional state rather than migrating consumers now.
- Clean `.ai-engineering/` data surfaces by removing byte-identical duplicates, dead state artifacts, and duplicate learning files only after link, hook, and policy evidence proves the target store.
- Replace stale tunables documentation with implemented default-bearing entries, and reserve genuinely unimplemented host-preflight/budget-profile variables in one clearly labelled roadmap block or remove them.
- Run a caller inventory across `src/`, `tests/`, `tools/`, hooks, templates, docs, and specs before deleting or inlining Python modules.
- Preserve `trace_context.py`, `capabilities.py`, and other production-used state modules unless replacement tests prove observability and manifest-coherence behavior survives.
- Split or shrink oversized facades and registry modules only when it reduces behavior-free indirection without adding compatibility shims.
- Document every hard delete under `CHANGELOG.md` `Removed`, keep hot-path budgets green, and avoid deleting tests solely to make simplification appear successful.

## Non-Goals

- Do not create a new branch or PR for this work; it continues on the existing branch and PR named in the references.
- Do not re-litigate the canonical chain `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`.
- Do not change `CONSTITUTION.md` hard rules or introduce backwards-compatibility shims for approved deletes/renames.
- Do not migrate gate findings from JSON to SQLite or remove the placeholder table in this spec; that larger migration requires separate approval if chosen later.
- Do not delete production-used trace, capability, context, facade, or registry modules based on name/size alone.
- Do not remove `.ai-engineering/cache/gate/`; it is a bounded cache whose documentation may be corrected.
- Do not treat overlapping draft briefs as automatically superseded until this spec's final delivered scope is known.
- Do not rewrite append-only audit history or archived specs to make grep output cleaner.

## Decisions

### D-146-01 — Ship a conservative multi-wave simplification, not a deletion spree

Promote the consumed brief as one large, evidence-gated simplification spec with five waves — ownership update bug fix, persistence doctrine reconciliation, data-tree cleanup, tunables docs/code reconciliation, and caller-inventory module simplification.

**Rationale**: The brief shows one concrete operator-visible bug and several cleanup opportunities with different risk profiles. Shipping the bug fix first preserves operator data intent while later cleanup waits for inventories and tests instead of relying on intuition.

### D-146-02 — Ownership helpers expose both raw rows and updater-ready model

Add a raw `state_db.list_ownership_rows(project_root)`-style reader plus a high-level helper or mapper that reconstructs the updater's `OwnershipMap`; use the high-level path in `ai-eng update` and the raw path in diagnostics/tests.

**Rationale**: Raw rows keep the SQLite boundary inspectable and useful for doctor/diagnostic flows, while the updater should not duplicate row-to-policy mapping logic. Exposing both is still simpler than preserving the deleted JSON sidecar as the normal read path.

### D-146-03 — SQLite ownership is authoritative for update decisions

`_initialize_update_context` must load ownership from `state.db.ownership_map` before evaluating file changes; `ownership-map.json` is a one-time migration fallback only when SQLite has no rows and the sidecar exists.

**Rationale**: The installer already writes ownership rows to SQLite and removes the legacy sidecar. The updater's current sidecar read can therefore recreate files an operator intended to deny, so the canonical lifecycle store must drive update policy.

### D-146-04 — Keep `gate-findings.json` canonical in this spec

Retain `.ai-engineering/state/gate-findings.json` as the primary gate/risk/verify artifact for this spec. Classify `state.db.gate_findings` as non-primary placeholder/transitional state unless a later spec approves a full consumer migration.

**Rationale**: Multiple live paths and tests read/write the JSON artifact today. Migrating gate findings to SQLite is a cross-surface state migration, not necessary to fix ownership or remove obvious dead weight, and would make the simplification spec larger rather than simpler.

### D-146-05 — Gate cache receives documentation, not a new lifecycle

Document `.ai-engineering/cache/gate/` as a bounded ephemeral cache with existing age/count limits and reuse the current clear path if manual cleanup is needed.

**Rationale**: The brief verifies that the cache already has a TTL and entry cap. Adding a new cleanup subsystem or moving the cache to SQLite would solve a documentation problem with more machinery.

### D-146-06 — Data-tree cleanup is content-preserving and policy-aware

Delete `.ai-engineering/references/` only after links/tests use `.ai-engineering/security/iocs/`; remove dead state files only after grep proves no reader/writer; merge `.ai-engineering/team/lessons.md` into `.ai-engineering/LESSONS.md` before deleting the duplicate learning surface.

**Rationale**: The same-looking files have different policy semantics in the control plane. Less-is-more means one canonical store per datum, not silent loss of team-owned or append-only learning content.

### D-146-07 — Tunables docs distinguish implemented defaults from reserved roadmap variables

Update root and template rulebooks so implemented variables (`AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`, `AIENG_NDJSON_MAX_LINES`, `AIENG_NDJSON_MAX_BYTES`) show defaults and behavior, while truly unimplemented host-preflight/budget-profile names are either removed or isolated in one explicit reserved block.

**Rationale**: The current docs mark implemented variables as pending, which misleads operators. A small documentation reconciliation preserves the useful knobs and avoids inventing host-admission behavior that prior spec-145 learning already narrowed out.

### D-146-08 — Production-used state modules require replacement plans

Do not delete `trace_context.py`, `capabilities.py`, or `context_packs.py` unless caller inventory plus regression tests prove an equivalent replacement for observability and manifest-coherence behavior.

**Rationale**: These modules have production consumers. Removing them because they look like framework scaffolding would violate KISS by creating hidden breakage and follow-up repair work.

### D-146-09 — Dead/test-only modules can be hard-deleted after inventory

Allow deletion of low-risk candidates such as `agentsview.py`, `outbox.py`, `governance/policy_engine.py`, and `cli_ui_skill_ref.py` only after source, hook, template, doc, and test inventory proves there is no production dependency; update tests and CHANGELOG in the same wave.

**Rationale**: The Constitution forbids compatibility shims, so approved deletes must be direct and documented. The inventory gate prevents downstream-fork insurance and future-scale placeholders from surviving forever while still protecting real callers.

### D-146-10 — Facade flattening is staged by callsite, not dogma

Migrate `StateService` and `DurableStateRepository` callers to explicit helpers only where it removes behavior-free forwarding. Keep useful adapter boundaries until risk, gate, install, doctor, and update callsites have a tested replacement.

**Rationale**: Service classes are not inherently bad; pointless pass-through layers are. A callsite-by-callsite migration avoids an oversized PR and makes each layer removal prove its value.

### D-146-11 — Split oversized installer mechanisms without breaking imports

Split `src/ai_engineering/installer/mechanisms/__init__.py` into mechanism-specific modules or explicitly exempt it with rationale; keep a thin, stable re-export surface during internal migration only when required by existing imports.

**Rationale**: The current module centralizes many mechanism classes for registry use. Splitting improves navigability, but import stability during the same PR is acceptable as an internal migration step, not as a long-term compatibility shim.

### D-146-12 — Overlapping briefs remain related, not automatically superseded

Treat `harness-persistence-strategy`, `less-is-more-quality-engine`, `prune-contexts-docs-research-evals`, and `dx-excellence-refactor` as related context. Mark a draft superseded only after this spec's implementation fully absorbs that draft's scope.

**Rationale**: This spec intentionally narrows broad simplification pressure into evidence-backed waves. Prematurely closing adjacent drafts would hide unresolved work and violate the persistence doctrine's source-of-truth discipline.

## Risks

- **Ownership row mapping drift**: SQLite rows may not reconstruct `OwnershipMap` semantics exactly. Mitigation: add roundtrip unit tests for allow/deny/team/append-only rows and an integration test for the denied-missing-file update scenario.
- **Gate findings ambiguity persists**: Keeping JSON canonical leaves the SQLite placeholder visible. Mitigation: explicitly document the placeholder/non-primary status and add tests that gate/risk/verify continue to read the approved canonical artifact.
- **Cleanup deletes a hidden consumer**: Hooks, templates, or docs may reference candidates not visible from source imports. Mitigation: require a caller inventory that covers `src/`, `tests/`, `tools/`, `.ai-engineering/scripts/hooks/`, templates, docs, and specs before deletion.
- **Learning content is lost during merge**: `.ai-engineering/team/lessons.md` and `.ai-engineering/LESSONS.md` may contain overlapping but non-identical rules. Mitigation: content-preserving merge with duplicate detection before deleting either surface.
- **Tunables docs overcorrect**: Removing or relabelling a variable can break operator expectations. Mitigation: grep exact env names, update docs tests, and keep one explicit reserved block for intentionally future variables.
- **Facade flattening becomes too large**: Migrating every `StateService`/repository caller in one wave can exceed reviewable scope. Mitigation: plan callsite groups and stop before public API removal if the wave grows past the agreed review size.
- **Hot-path regression**: New SQLite readers could accidentally move into hooks. Mitigation: keep ownership reads in `ai-eng update`/doctor cold paths and run existing no-SQL-on-hot-path architecture tests.
- **PR scope confusion**: This spec lands on the existing branch/PR rather than a fresh one. Mitigation: references and handoff notes must name the active PR and distinguish this draft from already archived spec-144 artifacts.

## References

- doc: .ai-engineering/specs/drafts/framework-simplification-less-is-more-brief.md
- pr: arcasilesgroup/ai-engineering#530
- doc: CONSTITUTION.md (hard-delete/no-shim and SSOT rules)
- doc: docs/persistence-doctrine.md (four-tier persistence model)
- doc: .ai-engineering/reference/principles.md (§10.1 KISS, §10.2 YAGNI, §10.3 SOLID, §10.4 DRY, §10.7 Clean Code, §10.8 Hexagonal Architecture)
- doc: .ai-engineering/specs/archive/spec-138-harness-persistence-strategy.md (persistence doctrine predecessor)
- doc: .ai-engineering/specs/archive/spec-140-less-is-more-quality-engine.md (quality-surface simplification predecessor)
- doc: src/ai_engineering/updater/service.py (current update ownership load and file-change evaluation)
- doc: src/ai_engineering/state/state_db.py (SQLite lifecycle helpers and placeholder notes)
- doc: src/ai_engineering/policy/orchestrator.py (gate-findings JSON writer)
- doc: src/ai_engineering/verify/service.py (gate-findings JSON reader)
- doc: src/ai_engineering/cli_commands/risk_cmd.py (gate-findings JSON risk acceptance)
- doc: .ai-engineering/scripts/hooks/prompt-injection-guard.py (implemented hook-cache TTL tunable)
- doc: .ai-engineering/scripts/hooks/auto-format.py (implemented autoformat debounce tunable)
- doc: .ai-engineering/scripts/hooks/runtime-session-end.py (implemented NDJSON rotation tunables)

## Open Questions

None for spec approval. The six open choices in the consumed brief are resolved by D-146-02, D-146-04, D-146-05, D-146-08, D-146-07, and D-146-12 respectively; implementation may split waves if `/ai-plan` finds the caller-inventory or facade work too large for one PR.
