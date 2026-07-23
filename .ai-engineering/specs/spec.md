---
spec: spec-194
slug: deterministic-context-safety-harness
title: "Deterministic Context and Safety Harness"
status: draft
effort: large
summary: "Read-only baseline collector that measures root-instruction bytes/tokens, mandatory reads, discovered catalog metadata, duplicate identities, hook injection cost, automatic writes and reachable MCP residue; produces redacted receipts; gates all six follow-on specs."
stack: python
---

# spec-194 — Deterministic Context and Safety Harness

## Summary

Before any context, MCP, surface or integration migration, ai-engineering needs a values-free harness that reports the actual host-visible prompt cost, discovery collisions, hook injection, automatic writes, MCP residue and command-output bounds. The harness supports preview, apply and verify workflows but makes no policy decision itself. A change is accepted only when the harness proves its claimed token, safety and compatibility effect on a clean host.

This is the **prerequisite for all five follow-on specs** (195–199). No mutation to roots, MCPs, surfaces, bootstrap, commands or packs may proceed without a passing baseline from this harness.

## Goals

- Produce a stable JSON schema (`ContextSafetyReport`) covering: root bytes/tokens, mandatory reads, unique and duplicate visible IDs, command metadata cost, hook injection, automatic writes, MCP operational residue and bounded output.
- Implement read-only collectors for roots, instructions, skills, commands, hooks, MCP configuration classes and output samples.
- Add clean fixtures for every enabled host plus an `UNVERIFIED` fixture mode that cannot claim support.
- Add compare/receipt output and tests for determinism, redaction, caps and false-negative-resistant duplicate detection.
- Reports contain no secret value, home path, credential key material or raw environment value.
- Same fixture and inputs produce byte-identical normalized JSON.
- Each enabled surface has a fixture result or an explicit `UNVERIFIED` result; no inferred pass.
- A baseline/compare regression fails on a budget or duplicate regression and leaves the target unchanged.
- The harness is a required pre/post gate for the five follow-on briefs.

## Non-Goals

- Do not remove MCPs, change root prose, generate commands, author CLI skills, rotate credentials, or change user-owned configuration. Those are separate specs that consume this evidence.
- Do not build a new control plane, daemon, registry or LLM intent router.
- Do not introduce a compatibility shim for old audit scripts.
- Do not mutate any target configuration during baseline or verify.

## Decisions

### D-194-01 — Pure domain collector with adapter pattern

The harness uses a pure domain collector that receives a repository root, declared host adapter and explicit fixture inputs, then emits a redacted `ContextSafetyReport`. Adapters own host-specific probes; the domain owns normalization, duplicate detection, budgets and verdicts. The command layer offers only `baseline`, `verify` and `compare` with deterministic JSON and concise human output.

**Rationale**: §10.8 Hexagonal Architecture isolates host differences in adapters. §10.1 KISS: one normalized report instead of host-specific ad-hoc audits.

### D-194-02 — Fixtures are disposable synthetic directories

Fixtures are disposable directories with synthetic safe configurations; the harness never scans or serializes credential values. Each enabled surface must have a passing fixture or an explicit `UNVERIFIED` result.

**Rationale**: §10.5 TDD: fixtures pin each classifier and redaction edge. No host can claim support without evidence.

### D-194-03 — Budget and redaction are versioned and documented

Budgets (token ceilings, output caps, duplicate thresholds) live in a versioned configuration file. Redaction rules are explicit and tested. Reports are capped at 8 KiB or 200 lines.

**Rationale**: §10.6 SDD: no remediation begins without evidence. Versioned budgets allow progressive tightening.

### D-194-04 — Harness is read-only and file-based

The harness is read-only, file-based and command-driven. It never writes to target configurations, never caches state between runs, and never invokes LLMs. It may read only what is necessary for its probes.

**Rationale**: Risk mitigation: harness becomes a new control plane. Keeping it deterministic and stateless prevents scope creep.

## Risks

- **Metadata estimate differs from real prompt input**: medium likelihood, high impact. Mitigation: require clean-host probes where available; label estimates explicitly.
- **Scanner reads a secret**: low likelihood, critical impact. Mitigation: parse structure only; redact before persistence; test known secret-shaped fixtures.
- **Harness becomes a new control plane**: medium likelihood, medium impact. Mitigation: keep it read-only, file-based and command-driven.
- **Fixture claims unsupported host behavior**: medium likelihood, high impact. Mitigation: `UNVERIFIED` is terminal for that adapter; no inferred pass.

## References

- brief: `.ai-engineering/specs/drafts/deterministic-context-safety-harness-brief.md`
- audit: `.ai-engineering/runtime/audits/cli-first-context-audit-2026-07-23.md`
- existing tests: `tests/architecture/test_surface_parity.py`, `tests/perf/test_skill_lint_budget.py`
- gate policy: `.ai-engineering/reference/gate-policy.md`
- generator: `scripts/sync_mirrors/core.py`
- template: `src/ai_engineering/templates/project/CANONICAL.md`

## Acceptance

- [ ] Schema and budget file are versioned and documented.
- [ ] Structure-only parsing and redaction tests pass.
- [ ] All enabled-surface fixtures emit pass, fail or `UNVERIFIED` deterministically.
- [ ] Compare output is capped and receipt-bound.
- [ ] Existing parity and skill-budget tests still pass.
- [ ] No target configuration is mutated by baseline or verify.
