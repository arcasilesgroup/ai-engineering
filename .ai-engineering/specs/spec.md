---
spec: spec-134
slug: skills-agents-excellence-v2
title: Skills + Agents Excellence Refactor v2
status: approved
effort: large
branch: spec-128/context-overrides-refactor
pr: arcasilesgroup/ai-engineering#509
target_dispatch: /ai-autopilot
source_brief: .ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md
chains_after: spec-133
---

# Skills + Agents Excellence Refactor v2

## Summary

The current framework is operational, but the operator-facing surface still asks too much insider knowledge from a first-time user. Work-item creation has no discoverable skill, upstream bug reporting lacks a safe redaction path, `/ai-build` has no unattended single-concern mode, `/ai-brainstorm` still spends time interrogating obviously trivial changes, and the mirror payload duplicates too much governance prose for too little UX value. The skill and agent roster also remains harder to read than it should be because orphan first-class agents are undiscoverable and several names are opaque or misleading. This spec closes those cohesion gaps in one governed pass on `spec-128/context-overrides-refactor` / PR #509 by adding the missing user-facing skills, introducing a pre-interrogation auto-spec gate, trimming mirror duplication into `docs/`, hard-renaming the ambiguous surfaces in one wave, and centralizing strict upstream redaction. One governing constraint is explicit: the repository instructions mention a `decisions` table, but [.ai-engineering/state/state.db](/Users/soydachi/repos/arcasilesgroup/ai-engineering/.ai-engineering/state/state.db) is currently empty, so this work must rely on the live JSON sidecars under `.ai-engineering/state/specs/` instead of a non-existent DB contract.

## Goals

1. Add discoverable issue/reporting surfaces: `/ai-issue`, `/ai-engineering-issue`, and `/ai-spec-draft`, with mirror propagation and acceptance tests.
2. Surface the orphan first-class agents as slash skills: `/ai-advise` for advisory governance review and `/ai-simplify` for direct simplification work.
3. Add an opt-in `/ai-build --no-hitl` path for single-concern approved plans that runs unattended, fails loud on blockers, emits audit evidence, and never auto-retries.
4. Add an auto-spec gate to `/ai-brainstorm` before interrogation, with manifest-driven thresholds, hard triggers, and a condensed-spec path for trivial changes.
5. Reduce mirror bootstrap weight by moving duplicated principles, mirror-authoring rules, and surface axioms into `docs/`, leaving the canonical mirrors thin enough to keep `CLAUDE.md` at or below 200 lines while preserving mirror-equivalence and IDE extras.
6. Execute one hard-rename wave for ambiguous skill and agent names, including internal family alignment for verifier and review lifecycle helpers.
7. Standardize all new and touched skills on the skill-authoring contract, including bodies at or below 500 lines and `evals/evals.json` coverage for objectively verifiable skills.
8. Centralize upstream-report sanitization in `_shared/redactor.py` with strict seven-vector redaction and mandatory human confirmation before submission.
9. Add or update architecture and unit tests for skill-agent cohesion, naming clarity, skill contract compliance, brainstorm auto-spec behavior, build no-HITL behavior, and redaction coverage, including new coverage for `tests/architecture/test_skill_agent_cohesion.py` and `tests/unit/skills/test_brainstorm_auto_spec_gate.py`.
10. Update `CHANGELOG.md` with added, changed, removed, and breaking-change entries for the new surfaces, mirror diet, and hard renames.

## Non-Goals

- Do not fuse or redesign the creative roster (`ai-animation`, `ai-visual`, `ai-design`, `ai-media`, `ai-video-editing`, `ai-slides`) in this spec.
- Do not retrofit the full repository with eval corpora; only new or touched skills must adopt the contract now.
- Do not add backwards-compatibility shims, alias commands, or compatibility files for renamed skills, agents, or flags.
- Do not make `/ai-build --no-hitl` the default behavior in this spec.
- Do not depend on a DB-backed decisions store until the repository actually ships one.

## Decisions

### D-134-01 — The work lands as one cohesive spec executed through `/ai-autopilot`

**Decision**: Keep the UX, naming, mirror, and workflow changes in a single large spec on `spec-128/context-overrides-refactor` / PR #509, with `/ai-autopilot` as the target dispatch.

**Rationale**: The problem being solved is cohesion. Splitting naming, workflow, and discoverability into separate specs would leave the surface inconsistent across releases and make the approval story harder to follow.

### D-134-02 — Issue creation and upstream bug filing become first-class skills

**Decision**: Add `/ai-issue` for project board work-item creation and `/ai-engineering-issue` for upstream framework bug reports. These may reuse existing board/provider plumbing internally, but the user-facing entry points remain dedicated skills.

**Rationale**: The gap is discoverability and safe workflow, not raw provider capability. Dedicated skills communicate destination and confidentiality clearly.

### D-134-03 — `/ai-build --no-hitl` is opt-in

**Decision**: Add `--no-hitl` to `/ai-build` for single-concern approved plans. Default `/ai-build` behavior remains human-in-the-loop.

**Rationale**: This closes the unattended single-concern gap without silently changing current operator expectations. It also keeps the blast radius smaller while the new contract proves itself.

### D-134-04 — `/ai-brainstorm` runs the spec gate before interrogation

**Decision**: Move the trivial-vs-spec decision to the front of the brainstorm workflow, using manifest-configured thresholds (`files`, `loc`, `cross_module`) plus hard triggers (`public_api`, `state_or_schema`, `new_dependency`, `security_surface`) and a condensed-spec path for trivial work.

**Rationale**: The current post-interrogation file-count heuristic spends effort too late and misses real governance triggers. The gate should save operator time without weakening review discipline.

### D-134-05 — Mirror diet is implemented by docs extraction

**Decision**: Move duplicated principles, mirror authoring rules, and surface axioms into `docs/` as the canonical home, leaving mirrors as thin entry documents plus IDE-specific extras.

**Rationale**: The waste is duplication, not the content itself. Extraction preserves the rules while materially reducing bootstrap cost and drift surface.

### D-134-06 — Naming refactor ships as one hard-rename wave

**Decision**: Execute the recommended rename set in one wave, including ambiguous skills such as `ai-gtm`, `ai-eval`, `ai-guide`, `ai-observe`, `ai-create`, `ai-cleanup`, `ai-write`, `ai-prompt`, `ai-guard`, plus family alignment for `verify-deterministic`, `reviewer-context`, and `reviewer-validator`.

**Rationale**: Partial renames create a mixed vocabulary that is harder to learn and document than the current state. The constitution already prefers hard renames over compatibility shims.

### D-134-07 — Orphan first-class agents must gain slash-skill surfaces

**Decision**: Surface the advisory and simplification agents as user-facing skills (`/ai-advise`, `/ai-simplify`) rather than keeping them as hidden implementation details or folding them into broader skills.

**Rationale**: First-time discovery happens through the `/ai-` roster. A first-class agent without a discoverable entry is a cohesion bug.

### D-134-08 — Touched skills adopt the skill-authoring contract; unchanged skills do not block this spec

**Decision**: All new and touched skills must comply with the skill-authoring contract, including bounded body size and evals where outputs are objectively verifiable. Unchanged skills are deferred.

**Rationale**: This delivers immediate quality leverage without turning the work into a repo-wide retrofit.

### D-134-09 — Upstream-report redaction becomes a shared strict service

**Decision**: Create `_shared/redactor.py` as the single redaction service. Upstream reporting uses strict mode with seven vectors; existing observability flows may reuse normal mode.

**Rationale**: Duplicating secret and PII regex logic across reporting surfaces is both a DRY failure and a security risk.

### D-134-10 — This spec must not depend on the documented `decisions` table

**Decision**: Treat `.ai-engineering/state/specs/*.json` as the live lifecycle source of truth for this work until the repository actually ships a DB-backed decisions contract.

**Rationale**: The repository instructions and the live filesystem diverge today. Shipping against a documented but non-existent table would make the workflow brittle from day one.

## Risks

- Hard renames will break user muscle memory and any out-of-repo references. Mitigation: update generated surfaces and `CHANGELOG.md` in the same wave; do not ship shims.
- Mirror extraction may break parity or lint assumptions. Mitigation: land the docs move together with mirror-equivalence and lint updates.
- `--no-hitl` could hide failures if the audit contract is incomplete. Mitigation: block with exit 78, emit audit rows and gate findings, and prohibit auto-retry.
- Auto-spec gating could under-classify regulated work. Mitigation: keep hard triggers absolute and provide a stricter regulated-mode knob.
- Redaction misses could leak private context upstream. Mitigation: strict seven-vector redaction plus mandatory human confirmation of the rendered issue body.
- The empty `state.db` / missing decisions-table mismatch could confuse future tooling. Mitigation: document the mismatch in this spec and keep the implementation sidecar-based until the DB contract is real.

## References

- pr: arcasilesgroup/ai-engineering#509
- doc: .ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md
- doc: .ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md
- doc: .ai-engineering/specs/spec.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: CONSTITUTION.md
- doc: AGENTS.md
- doc: .github/skills/ai-brainstorm/SKILL.md

## Open Questions

- Suppression drift closeout: should this spec resolve the `# noqa` / `pragma: no cover` drift by explicit-name refactors only, or should it require a separate operator-approved `/ai-constitution amend` carve-out for the sanctioned architectural cases?
