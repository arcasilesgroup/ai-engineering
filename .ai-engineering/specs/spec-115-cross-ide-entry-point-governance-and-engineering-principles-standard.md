---
spec: spec-115
title: Cross-IDE Entry-Point Governance and Engineering Principles Standard
status: approved
effort: medium
---

# Spec 115 - Cross-IDE Entry-Point Governance and Engineering Principles Standard

## Summary

ai-engineering currently preserves the intended workflow discipline and engineering philosophy only partially and across multiple surfaces. The same behavioral intent appears in different forms across `AGENTS.md`, `CONSTITUTION.md`, skills, contexts, and provider-specific overlays, while `GEMINI.md` still carries a larger legacy block that no longer matches the slim-overlay model adopted in spec-110. In parallel, engineering principles such as TDD, YAGNI, and clean architecture exist in isolated skills or language contexts rather than as one coherent framework-wide standard. This work defines a canonical governance model for cross-IDE entry points and a hybrid rule model for engineering principles so the framework stays consistent, auditable, and understandable without over-centralizing every guideline into one hard-rule file.

## Goals

- Define a single documented ownership and synchronization model for the root entry points `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, and the Codex surface that consumes root `AGENTS.md` so enabled IDEs are covered intentionally rather than by convention.
- Make drift in provider entry points deterministically detectable through sync and/or validation so a legacy-only block surviving in one IDE surface can no longer pass unnoticed.
- Establish a hybrid engineering-principles standard where spec-driven development (SDD), TDD, and proof-before-done remain hard governance rules, while YAGNI, DRY, KISS, SOLID, clean architecture, and clean code are enforced as operational standards through contexts, skills, and review criteria.
- Preserve the intent of the legacy orchestration guidance using current framework concepts such as `/ai-brainstorm`, `/ai-plan`, `/ai-dispatch`, `/ai-instinct`, generated mirrors, and AGENTS-first delegation rather than restoring outdated prose verbatim.
- Keep the resulting governance model multi-platform and explicit for Claude Code, Gemini CLI, GitHub Copilot, and Codex without requiring a wholesale rewrite of the framework runtime.

## Non-Goals

- Rewriting all framework governance into a single universal generator in this spec.
- Refactoring the full ai-engineering runtime or all existing skills to satisfy every design principle retroactively.
- Turning every engineering heuristic into a constitutional hard rule.
- Reintroducing `LESSONS.md` as the mandatory learning mechanism when the current model uses `ai-instinct` and related state.

## Decisions

### D-115-01: Treat cross-IDE entry points as a first-class governance surface

The framework will explicitly model the root entry points (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) and the Codex use of root `AGENTS.md` as a governed surface with defined ownership, generation/sync behavior, and validation expectations.

**Rationale**: The current repository already treats these files as framework-managed, but their canonical sources are mixed: `AGENTS.md` is generated, `CLAUDE.md` is root-authored and templated, `GEMINI.md` is rendered from a project template, and Copilot instructions are generated separately. Making this model explicit is necessary before the framework can claim true multi-IDE parity.

### D-115-02: Preserve intent, not legacy wording

The framework will preserve the behavioral intent of the removed legacy guidance, but it will express that intent in the current ai-engineering vocabulary and architecture instead of re-injecting the old block verbatim into every surface.

**Rationale**: Literal restoration would duplicate rules that spec-110 intentionally redistributed into `AGENTS.md`, `CONSTITUTION.md`, skills, and contexts. The problem is not the absence of legacy phrasing; it is the lack of one coherent and auditable mapping from intent to the current framework constructs.

### D-115-03: Use a hybrid principle model

Engineering principles will be split by enforcement strength. Spec-driven development, TDD, and verification-before-done remain hard rules in governance surfaces. YAGNI, DRY, KISS, SOLID, clean architecture, and clean code become framework-wide operational standards expressed through contexts, core skills, and review/verify criteria.

**Rationale**: Some principles are objective gates with clear failure conditions, while others are balancing heuristics that must guide design and review without turning every tradeoff into a constitutional violation. A hybrid model keeps governance strict where determinism is possible and pragmatic where engineering judgment is required.

### D-115-04: Codex is governed through AGENTS.md, not a separate CODEX.md

This work will treat the Codex surface as the root `AGENTS.md` contract unless a real platform-specific Codex entry point is introduced later by spec.

**Rationale**: The current repository has no root `CODEX.md`, and prior governance decisions already assume Codex uses `AGENTS.md` natively. Creating a parallel root surface without a platform need would increase drift and violate the simplification goal.

## Risks

- **Mixed-source drift remains underspecified**: if ownership boundaries between root files, templates, and generators stay ambiguous, the framework may still drift even after new wording is added. **Mitigation**: the spec must require one documented ownership model and deterministic checks for each enabled provider surface.
- **Principle overload**: adding too many principles at the same governance level can make the rules harder to follow and reduce adoption. **Mitigation**: keep the hybrid split explicit and limit hard rules to objectively enforceable behaviors.
- **Over-engineering the sync path**: solving a real GEMINI drift issue with a full generator rewrite would exceed the agreed scope. **Mitigation**: keep this spec focused on the canonical model, parity guarantees, and principle placement, not on a total governance-engine rewrite.

## References

- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: .github/copilot-instructions.md
- doc: .ai-engineering/manifest.yml
- doc: CONSTITUTION.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/contexts/architecture-patterns.md
- doc: .claude/skills/ai-plan/SKILL.md
- doc: .claude/skills/ai-code/SKILL.md
- doc: .claude/skills/ai-test/SKILL.md
- doc: .claude/skills/ai-review/SKILL.md
- doc: .claude/skills/ai-verify/SKILL.md
- doc: scripts/sync_command_mirrors.py
- doc: src/ai_engineering/installer/templates.py
- doc: src/ai_engineering/templates/project/GEMINI.md
- doc: src/ai_engineering/templates/project/CLAUDE.md
- doc: docs/anti-patterns.md
- doc: .ai-engineering/specs/spec-110-governance-v3-harvest.md

## Open Questions

- Should entry-point parity live inside the existing `sync_command_mirrors.py` pipeline, or should the framework split entry-point generation/validation into a separate governed mechanism while keeping one user-facing sync command?