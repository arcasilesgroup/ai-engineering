---
id: "035"
slug: "feature-gap-wiring"
status: "in-progress"
created: "2026-03-04"
size: "S"
tags: ["feature-gap", "wiring", "dead-code-functional", "scan", "governance"]
branch: "spec-035/feature-gap-wiring"
pipeline: "standard"
decisions: []
---

# Spec 035 — Extend feature-gap with wiring detection

## Problem

The `feature-gap` skill currently detects gaps between specifications and code (what should exist and doesn't). There is an uncovered case: **code that is implemented but not connected** — functions, modules, or exports that exist in the codebase but are not wired to any entry point, route, or consumer. This is "functional dead code": not unreachable branches, but complete implementations that nobody calls.

Without wiring detection, fully implemented features can sit disconnected indefinitely, creating maintenance burden and false confidence that features are "done."

## Solution

Extend the existing `feature-gap` skill (rather than creating a new skill) to detect wiring gaps. This keeps the 34-skill count stable and expands the scan agent's coverage without structural changes.

Changes:

1. **`skills/feature-gap/SKILL.md`** — Update metadata (description, tags), add procedure step 5.5 (wiring gap detection), update Purpose, add Wiring Matrix to output.
2. **`agents/scan.md`** — Update the feature-gap mode description and threshold table to reflect wiring coverage.

No other changes required — the scan agent already references feature-gap, the command routing is in place, and the output contract structure is preserved.

## Scope

### In Scope

- Update `skills/feature-gap/SKILL.md`: metadata, purpose, procedure step 5.5, output section.
- Update `agents/scan.md`: mode table description, threshold table entry.
- Validation: verify updated documents are coherent and pass integrity checks.

### Out of Scope

- Python CLI changes (no deterministic wiring detection tooling in this spec).
- New skill or agent creation.
- Changes to other scan modes.
- Automated static analysis tooling for wiring detection.

## Acceptance Criteria

1. `skills/feature-gap/SKILL.md` metadata includes `wiring` and `dead-code-functional` tags.
2. `skills/feature-gap/SKILL.md` description mentions "wiring gaps (implemented but disconnected code)."
3. `skills/feature-gap/SKILL.md` Purpose section covers both spec-vs-code gaps AND implementation-vs-integration gaps.
4. Procedure step 5.5 exists between "Detect dead specs" (step 5) and "Report" (step 6), covering: exported but never imported, endpoints not registered, handlers not subscribed, modules without importers, CLI commands not registered.
5. Output section includes a Wiring Matrix table with columns: Implementation, Type, Expected Consumer, Connected, Status.
6. `agents/scan.md` mode table for `feature-gap` mentions "wiring gaps (disconnected implementations)."
7. `agents/scan.md` threshold table for `feature-gap` includes ">5 unwired exports" as a critical threshold.
8. `ai-eng validate` passes without integrity errors after changes.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Extend feature-gap instead of new skill | Keeps 34-skill count stable; wiring is a natural extension of gap analysis |
| D2 | New category name: "Disconnected" | Distinct from "Missing" (spec gap) — signals implemented-but-unwired |
| D3 | Step numbering as 5.5 (not renumbering) | Minimal diff, preserves existing step references |
