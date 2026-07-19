---
name: ai-brainstorm
description: "Forces rigorous design interrogation BEFORE any code: explores approaches, surfaces ambiguity, gathers evidence, produces an approved spec that becomes the contract for /ai-plan. Trigger for 'lets add X', 'how should we handle Y', 'whats the best approach', 'I am thinking about', 'what should we build for'. Not for existing approved specs; use /ai-plan instead. Not for execution; use /ai-build instead."
effort: mid
argument-hint: "[feature or problem description] [work item ID] | --consolidate-spec <slug>"
---

# Brainstorm

Design-interrogation skill: forces rigorous thinking BEFORE any code and produces an approved spec — the contract for `/ai-plan`.

## Workflow

Principle: §10.6 SDD — this skill produces the spec. **HARD GATE**: no implementation runs until the operator explicitly approves it.

- **-1. Live-slot guard** (D-167-05) — UNLESS `--consolidate-spec`, run `python .ai-engineering/scripts/spec_lifecycle.py slot_status` BEFORE any `spec.md` write (Step 6 and the Step 0b condensed path both write). If JSON reports `occupied: true` AND `state` ≠ `shipped`: surface `spec_id`/`slug`/`state` and ask the operator to consolidate first (`/ai-brainstorm --consolidate-spec <slug>`) or confirm the overwrite. On `occupied: false`, `shipped`, or any script error: proceed silently. Fail-open — advisory, never blocks interrogation.
- **0a. Fast-path `--consolidate-spec <slug>`** — read `.claude/skills/_shared/consolidate-spec.md` and run the shared handler (resolve record, append `_history.md` row via `spec_lifecycle.py mark_shipped`, clear `spec.md`/`plan.md` to placeholders). STOP after consolidation — no interrogation. Fail-open on missing script.
- **0b. Auto-spec gate** — follow `handlers/auto-spec-gate.md`. Classify the working-tree diff via `ai_engineering.brainstorm.auto_spec_gate.classify_diff` BEFORE interrogation. Any hard trigger OR any threshold exceeded → full interrogation (Step 1). Else → condensed-spec path: draft the minimum-viable spec from the diff, present for one-shot approval, STOP at Step 7. `manifest.brainstorm.auto_spec_gate.enabled: false` → no-op (fail-open to full interrogation).
- **0. Lifecycle bootstrap** (before evidence sweep) — `python .ai-engineering/scripts/spec_lifecycle.py start_new <slug> <title>` mints/refreshes the DRAFT record at `.ai-engineering/state/specs/<slug>.json`. Fail-open: non-zero exit logs and continues.
- **1. Work-item context** (only when a work-item ID is given, e.g. `AB#100` / `#45`):
  a. read `manifest.yml` `work_items` for active provider + team config;
  b. fetch item + hierarchy — GitHub `gh issue view <n> --json title,body,labels,milestone,assignees`; Azure `az boards work-item show --id <n> --expand relations -o json`;
  c. walk Feature → User Story → Tasks (parent/child relations);
  d. use all standard + custom fields the platform provides;
  e. pre-fill `refs` in the generated spec frontmatter;
  f. `/ai-board sync refinement <ref>` to move the item to refinement (fail-open).
- **2. Enhance input** — follow `handlers/prompt-enhance.md` to clarify and sharpen user input before interrogation.
- **3. Evidence sweep** — when current state spans multiple repo / governance surfaces, dispatch parallel read-only `ai-explore` passes first, summarize, then sharpen the next question or spec boundary.
- **4. Interrogate** — follow `handlers/interrogate.md` (see Questioning Rules).
- **5. Propose approaches** — 2-3 options with trade-offs (never one). Scope was settled at Step 0b; no post-interrogation file-count heuristic.
- **6. Draft spec** — write `.ai-engineering/specs/spec.md`, then run **Step 0.5 section pre-flight** (deterministic, BEFORE any LLM pass): `ai-eng spec verify --sections .ai-engineering/specs/spec.md` (spec-139 M7) scans the five required headers (`## Summary`, `## Goals`, `## Non-Goals`, `## Decisions`, `## Risks`) and emits JSON `valid` / `missing_sections` / `present_sections`. Exit 1 → patch missing headers, re-run. Only on `valid=true` proceed to LLM schema validation against `.ai-engineering/reference/spec-schema.md`.
- **7. Board sync (ready)** — if a work-item ID was given at Step 1, `/ai-board sync ready <ref>` (fail-open).
- **8. Review spec** — follow `handlers/spec-review.md` (max 3 iterations).
- **9. STOP — approval.** On operator approval, call `python .ai-engineering/scripts/spec_lifecycle.py approve <spec_id>` (`<spec_id>` from frontmatter `spec:`, fallback `slug:`) to transition DRAFT→APPROVED and mirror `status: approved` into `spec.md`. Fail-open (D-161-08): non-zero exit logs, does NOT block STOP. Present the approval ask with the 6-field value block (Bottom line / Why it matters / What's done / Risk / Next / Details) per `.ai-engineering/reference/value-lens.md` at the resolved audience level (default `full`) — the spec text stays a carve-out. Then present the approved spec; user runs `/ai-plan`.

## Questioning Rules

- ONE question at a time — never batch. Prefer multiple choice (A/B/C) over open-ended.
- Frame each question and option in plain terms (impact / effort / risk) per `value-lens.md` so a non-technical sponsor can answer.
- Challenge vague language — "improve", "optimize", "clean up" are not requirements.
- Push back on scope creep: "Is this in scope for v1?" Explore edge cases the user has not mentioned.
- Max 10 questions per session; if you need more, the problem is too big — split it.
- When input requires research to understand current state (audits, "is this working?", "how is X organized?"): gather data, present findings, THEN interrogate. Research precedes interrogation, it is not interrogation.

## Common Mistakes

- Writing implementation details in the spec — specs describe WHAT, not HOW.

## Integration

**Called by**: user, or `/ai-plan` when requirements are unclear. **Calls**: `handlers/auto-spec-gate.md` (Step 0b classifier via `ai_engineering.brainstorm.auto_spec_gate.classify_diff`), `handlers/prompt-enhance.md`, `handlers/interrogate.md`, `handlers/spec-review.md`, `/ai-board sync` (refinement + ready), `.ai-engineering/scripts/spec_lifecycle.py start_new` (fail-open bootstrap) + `approve` (Step 9 DRAFT→APPROVED, fail-open). **Transitions to**: `/ai-plan` (ONLY — never directly to `/ai-build`).

## Examples

User: "AB#456 says 'improve search performance' — what does that even mean?"

```
/ai-brainstorm AB#456
```

Pulls the work item, surfaces ambiguity, drives the user to specific measurable acceptance criteria, links the spec to the work item, and produces an approved spec at `.ai-engineering/specs/spec.md` with decisions recorded.

$ARGUMENTS
