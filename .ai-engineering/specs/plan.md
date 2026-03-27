# Plan: spec-080 Hook Simplification and Instinct Learning v1

## Pipeline: full
## Phases: 5
## Tasks: 18 (build: 16, verify: 1, guard: 1)

### Phase 1: Lock The Simplified Instinct Contract
**Gate**: The new instinct artifact set, retention rules, and observation minimization boundaries are defined by failing tests before hook rewiring begins.
- [x] T-1.1: Write failing state tests for `.ai-engineering/state/instinct-observations.ndjson`, `.ai-engineering/instincts/instincts.yml`, `.ai-engineering/instincts/context.md`, and `.ai-engineering/instincts/meta.json`, including project-local-only layout and 30-day retention behavior. (agent: build)
- [x] T-1.2: Implement shared state-path helpers, default metadata, and retention or bookkeeping utilities for the simplified instinct artifact set. (agent: build)
- [x] T-1.3: Write failing tests for sanitized pre-tool and post-tool observation capture that preserves enough signal for tool sequences, error recovery, and skill-agent preferences without transcripts, raw payloads, or secret leakage. (agent: build)
- [x] T-1.4: Implement the canonical `instinct-observe` writer and sanitization helpers so bounded observations append to `.ai-engineering/state/instinct-observations.ndjson` with automatic local retention enforcement. (agent: build)

### Phase 2: Achieve Retained Hook Parity And Naming Cleanup
**Gate**: Claude Code and GitHub Copilot both wire the retained capabilities automatically through canonical logic plus host adapters, with no `cost-tracker` or Copilot per-agent hook dependency.
- [x] T-2.1: Write failing hook config and template tests for automatic Claude and Copilot activation of `auto-format`, `strategic-compact`, `instinct-observe`, and `instinct-extract`, including Bash and PowerShell adapter coverage for Copilot. (agent: build)
- [x] T-2.2: Rename or restructure retained hook entrypoints into canonical Python logic plus Copilot adapters, and update Claude settings, Copilot hook manifests, and installer templates to reference the new names. (agent: build)
- [x] T-2.3: Implement missing Copilot adapters for `strategic-compact`, `instinct-observe`, and retained `auto-format` or `instinct-extract` parity in both `.sh` and `.ps1`, translating host payloads to the canonical shape. (agent: build)
- [x] T-2.4: Update the canonical `auto-format`, `strategic-compact`, and `instinct-extract` logic to use the new artifact model and host-independent session semantics while preserving fail-open behavior. (agent: build)
- [x] T-2.5: Remove or retire obsolete hook entrypoints and compatibility shims that exist only for legacy naming, incomplete parity, or superseded session behavior, while preserving macOS, Linux, and Windows support. (agent: build)

### Phase 3: Move Instinct Learning Into Onboard-Driven Consolidation
**Gate**: `onboard` owns the consolidation decision, processes only recent delta plus current store, and produces a bounded context file without daemons or ECC-style evolution features.
- [x] T-3.1: Write failing tests for the consolidation gate based on observation delta plus context age, and for bounded regeneration of `instincts.yml`, `context.md`, and `meta.json`. (agent: build)
- [x] T-3.2: Implement consolidation bookkeeping and gating logic around `.ai-engineering/instincts/meta.json`, including concrete delta and staleness thresholds resolved during planning. (agent: build)
- [x] T-3.3: Implement the simplified instinct consolidation flow so `onboard` consumes recent observations plus the current instinct store and emits a bounded `.ai-engineering/instincts/context.md` instead of per-instinct files or global scopes. (agent: build)
- [x] T-3.4: Update downstream session-start or context-loading flows to consume `.ai-engineering/instincts/context.md` rather than raw observation streams or the old instinct layouts. (agent: build)
- [x] T-3.5: Rewrite the `onboard` and `instinct` skill content and mirrors to describe the simplified review, normalize, and consolidate flow and remove outdated confidence, promotion, evolve, export/import, and global-scope behavior. (agent: build)

### Phase 4: Remove Unsupported Surface And Align Templates Or Docs
**Gate**: Standard install output no longer ships `cost-tracker`, stale Copilot per-agent guidance, or ECC-like instinct storage language, and all mirrors/templates stay in sync.
- [x] T-4.1: Write failing installer, template, and docs tests asserting removal of `cost-tracker`, removal of `chat.useCustomAgentHooks` dependency for retained capabilities, and absence of deprecated ECC-like paths such as `observations.jsonl` project/global instinct trees. (agent: build)
- [x] T-4.2: Remove `cost-tracker` scripts, hook wiring, and related references from the live repo and generated templates. (agent: build)
- [x] T-4.3: Update mirrored instructions, templates, solution-intent, and changelog language so the supported model is observation capture plus onboard consolidation plus bounded instinct context. (agent: build)

### Phase 5: Verify Acceptance And Reconcile Governance
**Gate**: Focused suites pass, cross-IDE hook automation is proven in installed fixtures, and the narrative surface is consistent with DEC-028 and the project identity.
- [x] T-5.1: Run focused unit and integration suites for hook state, retained hook flows, Copilot Bash/PowerShell adapters, installer templates, and instinct consolidation; fix regressions introduced by the redesign. (agent: build)
- [x] T-5.2: Verify spec-080 acceptance criteria end-to-end for standard install on Claude Code and GitHub Copilot, including automatic retained hooks, 30-day retention, bounded context generation, and no `cost-tracker`, daemon, or per-agent dependency. (agent: verify)
- [x] T-5.3: Review decision and documentation drift against DEC-028, project identity, and existing observability language, and confirm no supported surface still advertises the removed instinct model or Copilot per-agent hook dependency. (agent: guard)

## Notes

- TDD applies to artifact contracts, hook wiring, retention, and onboard consolidation: tests first, then implementation.
- Phase 2 depends on Phase 1 for the canonical observation contract and new artifact paths.
- Phase 3 depends on Phases 1 and 2 so `onboard` consolidates real data emitted consistently by Claude Code and GitHub Copilot.
- Phase 4 should not remove `cost-tracker` or legacy docs until the retained hook surface and consolidation flow exist from Phases 2 and 3.
- Phase 5 includes mirror/template verification because spec-080 changes dogfooded files and installer output at the same time.
