---
spec: spec-196
slug: lean-bootstrap-and-observation
title: "Lean Bootstrap, Session Ticket, and Opt-In Observation"
status: draft
effort: large
summary: "Root budget ≤2 KiB/≤500 tokens, no mandatory reads, deterministic session ticket, zero happy-path context injection, opt-in deduplicated observation."
stack: python
---

# spec-196 — Lean Bootstrap, Session Ticket, and Opt-In Observation

## Summary

A new session receives only a compact root rulebook: identity, irreversible-action gates, canonical lifecycle commands and a pointer to a deterministic task ticket. Long doctrine, memory and framework context are fetched only after an explicit `/ai-*` workflow needs them. Healthy sessions write nothing automatically; learning is a deliberate, deduplicated cold-path operation.

Depends on spec-194 (harness) for baseline measurement. Independent of spec-195 (MCP removal).

## Goals

- Each generated root is at most 2 KiB or 500 estimated tokens and has no "read every session" directive.
- A session ticket is deterministic, bounded and task-specific; it loads no full reference unless an invoked workflow requests it.
- Normal hooks add zero model-visible context and make no tracked learning/work-item write.
- Observation review is explicit, deduplicated and confirmation-gated.
- Review routing uses changed path/risk with a deliberate full-review override.
- Normal/list/error output obeys 8 KiB/200, 4 KiB/100 and 2 KiB/50 limits respectively.

## Non-Goals

- Third-party MCP deletion (spec-195).
- Host command/skill roots (spec-197).
- New CLI packs (spec-198/199).
- A semantic router.
- Changes to project-domain instructions owned by consumers.

## Decisions

### D-196-01 — Session ticket replaces mandatory reads

A deterministic `session ticket` generated from task type, changed paths, active approved artifact, stack and risk replaces implicit document reads. The ticket contains bounded pointers and only the minimum digest needed to choose a workflow.

**Rationale**: Mandatory reads force every session to pay for context before task work begins.

### D-196-02 — Hooks emit zero model context on happy path

Normal successful actions emit no `additionalContext` and no tracked write. Hook scripts may collect privacy-safe technical receipts, but the model sees nothing unless an error occurs.

**Rationale**: Progressive-disclosure injection adds ~252 tokens per prompt across 238 prompts.

### D-196-03 — Observation is opt-in cold-path

Learning changes to an operator-invoked sweep that performs deterministic deduplication and requires explicit confirmation before any tracked write or work-item creation.

**Rationale**: Always-on observation creates noise and unexpected file mutations.

### D-196-04 — Hard-delete mandatory-read wording

Delete mandatory-read wording rather than adding compatibility prose. No long-root compatibility mode.

**Rationale**: §10.1 KISS — remove bootstrap rather than inventing another layer.

## Risks

- **Lean root omits an irreversible gate**: low likelihood, critical impact. Mitigation: enumerate gates, test them, retain only those in root.
- **Ticket is too generic to guide work**: medium likelihood, medium impact. Mitigation: require path/risk evidence and measure task success.
- **Removing prompt hooks weakens security**: medium likelihood, high impact. Mitigation: keep deterministic enforcement at CLI/hook/CI boundaries; remove prose injection only.
- **Learning signal is lost**: medium likelihood, low impact. Mitigation: explicit sweep with receipts and deduplication.

## References

- brief: `.ai-engineering/specs/drafts/lean-bootstrap-and-observation-brief.md`
- template: `src/ai_engineering/templates/project/CANONICAL.md`
- hooks: `.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py`
- session-watch: `.claude/skills/ai-session-watch/SKILL.md`

## Acceptance

- [ ] Root size/token gates pass on all generated mirrors.
- [ ] No generated root mandates session-wide document reads.
- [ ] Ticket tests prove bounded and task-relevant output.
- [ ] Normal hooks emit no `additionalContext` and no tracked write.
- [ ] Observation is explicit, deduplicated and confirmation-gated.
- [ ] Output and review-selection tests pass.
