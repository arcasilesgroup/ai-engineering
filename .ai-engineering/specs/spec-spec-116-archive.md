---
spec: spec-116
title: Framework Knowledge Consolidation, Canonical Placement, and Governance Cleanup
status: approved
effort: large
---

# Spec 116 - Framework Knowledge Consolidation, Canonical Placement, and Governance Cleanup

## Summary

ai-engineering now has enough accumulated guidance across `LESSONS.md`, `instincts.yml`, `proposals.md`, `decision-store.json`, skills, agents, contexts, and root IDE overlays that the main problem is no longer missing knowledge but misplaced knowledge. Durable, repeatable framework behavior still lives partly in soft-memory artifacts and prose-only overlays, which makes it hard to validate mechanically, easy to leave stale, and risky to clean up without losing important rules. This work defines a governed consolidation pass that promotes repeatable behavior into the correct canonical home (`SKILL.md`, agent docs, `manifest.yml`, contexts, or root entry points), leaves heuristic discovery and audit backlog content in the learning artifacts, formalizes only real decisions and active risks in `decision-store.json`, and then removes stale or redundant artifacts once their signal is preserved elsewhere.

## Goals

- Define an explicit canonical-placement matrix for framework knowledge so the team can decide whether a rule belongs in a skill, an agent, a context, `manifest.yml`, a root entry-point file, or a governance artifact without case-by-case guesswork.
- Enrich `manifest.yml` with machine-readable metadata for the framework surfaces that currently exist only as prose, such as handler dependencies, profile semantics, decision references, and mirror ownership where that metadata can be validated automatically.
- Promote the highest-value repeatable patterns from `LESSONS.md`, `instincts.yml`, and `proposals.md` into the canonical skills, agents, and entry points that actually govern runtime behavior.
- Audit `decision-store.json` so it contains only formal decisions, live governance constraints, and active/accepted risks, while stale, superseded, or already-remediated entries are clarified, archived, or removed from the active surface.
- Clean up redundant or stale learning/governance artifacts only after their important signal has been preserved in the correct canonical surface.
- End with deterministic validation proving that mirrors, references, manifests, and canonical docs stay coherent after the consolidation.

## Non-Goals

- Rewriting the full framework runtime, agent system, or installer architecture.
- Turning every heuristic, instinct, or review preference into a constitutional hard rule.
- Deleting skills, agents, or governance artifacts based only on telemetry or audit impressions without verifying the underlying data source first.
- Introducing new root IDE surfaces such as a dedicated `CODEX.md` when the current governance model already routes Codex through existing entry points.
- Replacing the current sync system with a full universal documentation generator in this spec.

## Decisions

### D-116-01: Adopt a canonical placement matrix for framework knowledge

The framework will define one explicit placement model for each class of knowledge: user-facing operational contracts live in canonical `SKILL.md` files; agent-specific orchestration behavior lives in agent docs; machine-readable metadata lives in `manifest.yml` only when validators can consume it; cross-IDE governance rules live in `AGENTS.md` or the appropriate root entry-point overlay; contexts hold reusable framework guidance; `LESSONS.md`, `instincts.yml`, and `proposals.md` remain discovery and refinement surfaces rather than the final runtime contract.

**Rationale**: The current repository contains the same rule in multiple forms because the destination decision is implicit. Making placement explicit is the prerequisite for both safe cleanup and deterministic validation.

### D-116-02: `manifest.yml` will hold structured metadata, not freeform operational prose

This spec will enrich `manifest.yml` only with metadata that downstream tooling can validate or consume directly, such as handler registries, profile/mode semantics, decision references, provider/mirror ownership, and similar structured declarations. Behavioral explanations and human-facing process guidance will stay in skills, agents, contexts, or entry-point documents.

**Rationale**: The manifest is the configuration source of truth, but turning it into a prose dump would make it harder to validate and easier to drift. The goal is stronger determinism, not a new dumping ground.

### D-116-03: Learning artifacts are a promotion funnel, not the canonical runtime surface

`LESSONS.md`, `instincts.yml`, and `proposals.md` will remain the place where the framework captures discoveries, corrections, and candidate improvements. A pattern only graduates out of those files when it is repeatable, broadly applicable, and better enforced in a canonical surface.

**Rationale**: Not every correction deserves permanent codification. Keeping the learning artifacts as a funnel preserves experimentation while preventing important recurring rules from getting trapped in soft memory.

### D-116-04: `decision-store.json` is reserved for formal decisions and live governance risk

The decision store will contain formal architectural/governance decisions, accepted or active risks, and other audit-grade records that need lifecycle metadata. Tactical heuristics, style preferences, and solved implementation notes will not be promoted there. Existing stale, superseded, or remediated entries must be made explicit rather than left ambiguous.

**Rationale**: The decision store loses value if it becomes a second `LESSONS.md`. It must stay narrow enough to support audits, expiry checks, and real governance review.

### D-116-05: Cleanup happens only after promotion and verification

No learning or governance artifact will be deleted, slimmed, or de-emphasized until the useful signal it carries has been promoted to the correct canonical surface and the resulting mirrors and validators remain green.

**Rationale**: The failure mode here is “clean but dumber.” Promotion-first cleanup keeps the framework simpler without silently discarding operating knowledge.

## Risks

- **Over-promotion risk**: if too many tactical lessons are codified as permanent framework behavior, the framework will become rigid and noisy. **Mitigation**: apply the placement matrix strictly and require a repeatability/value test before promotion.
- **Manifest bloat**: adding too much metadata to `manifest.yml` could make it harder to maintain and easier to misuse. **Mitigation**: only add machine-readable fields with a validator or consuming tool behind them.
- **Historical-loss risk**: cleanup of stale proposals or decisions could remove useful context for future archaeology. **Mitigation**: preserve promoted signal in canonical files and keep archival/history pointers where needed.
- **Mirror/validator drift**: moving rules across skills, contexts, and entry points can desynchronize mirrors or cross-reference validation. **Mitigation**: include sync and validation as explicit acceptance criteria for the spec.

## References

- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/LESSONS.md
- doc: .ai-engineering/instincts/instincts.yml
- doc: .ai-engineering/instincts/proposals.md
- doc: .ai-engineering/state/decision-store.json
- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: .github/copilot-instructions.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/contexts/mcp-integrations.md
- doc: .claude/skills/ai-brainstorm/SKILL.md
- doc: .claude/skills/ai-plan/SKILL.md
- doc: .claude/skills/ai-pr/SKILL.md
- doc: .claude/skills/ai-review/SKILL.md
- doc: .claude/skills/ai-verify/SKILL.md
- doc: .claude/skills/ai-autopilot/SKILL.md
- doc: scripts/sync_command_mirrors.py
- doc: .ai-engineering/specs/spec-115-cross-ide-entry-point-governance-and-engineering-principles-standard.md
- doc: .ai-engineering/specs/spec-096-manifest-source-of-truth.md
- doc: .ai-engineering/specs/spec-090-instincts-lessons-consolidation.md

## Open Questions

- Should handler/profile metadata be authored directly in `manifest.yml`, generated into it from canonical skill metadata, or managed as a separate generated section with manifest-level ownership?
- Which currently active decision-store entries should remain active after codification into skills or entry points, and which should be archived as completed cleanup outcomes?
