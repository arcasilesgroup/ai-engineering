---
id: "037"
slug: "spec-as-gate"
status: "in-progress"
created: "2026-03-06"
size: "M"
tags: ["cross-ide", "planning", "cli", "governance"]
branch: "feat/037-spec-as-gate"
pipeline: "standard"
decisions: []
---

# Spec 037 — Spec-as-Gate: Cross-IDE Plan/Execute Separation

## Problem

LLMs lack real "modes." Textual instructions like `PLAN-B1` ("do not execute during planning") are soft constraints that fail when conversation context accumulates execution momentum — the model predicts the next logical step is *doing*, not *planning*.

Additionally, native IDE plan modes (Claude Code, Copilot ask mode, Codex suggest mode) are binary: fully read-only or full access. This creates a catch-22:

- **Plan mode ON**: LLM cannot write spec files to disk.
- **Plan mode OFF**: LLM may leak from planning into execution.

No current mechanism provides "scoped writes" (specs/plans only) during planning.

## Solution

Replace dependency on IDE plan modes with an **artifact-as-gate** pattern inspired by GSD, Spec Kit, and BMAD Method:

1. **`/ai:plan`** — LLM analyzes and produces spec as **structured text in the conversation** (not file writes). Then calls `ai-eng spec save` (deterministic CLI) to persist. Then STOPS.
2. **User reviews** the spec (in chat or on disk). Iterates if needed.
3. **`/ai:execute`** — LLM reads spec from disk (source of truth) and implements.

The gate between plan and execute is the **user typing `/ai:execute`** — a hard stop no LLM can bypass.

### Design Principles

- **Artefact is the boundary** (from GSD/Spec Kit): the spec file on disk is the contract between planning and execution.
- **CLI is the gatekeeper**: `ai-eng spec save` is deterministic — no AI tokens, no drift.
- **User is the transition**: explicit human action between phases.
- **IDE-agnostic**: works identically in Claude Code, Copilot, Cursor, OpenCode, Codex.

## Scope

### In Scope

- New CLI command `ai-eng spec save` that reads structured spec from stdin and persists to disk.
- Update `agents/plan.md` to produce spec as text + call CLI instead of writing files directly.
- Update `skills/spec/SKILL.md` to document CLI-driven path.
- Cross-IDE configuration: `.github/copilot-instructions.md`, `.cursor/rules/ai-engineering.mdc`.
- Documentation for other IDEs (OpenCode, Codex, etc.).

### Out of Scope

- PreToolCall hooks for enforcement (future enhancement, not needed with this approach).
- Changes to `/ai:execute` agent (already reads spec from disk).
- IDE plugin development.
- Removing existing manual spec creation flow (remains as alternative).

## Acceptance Criteria

1. `ai-eng spec save` reads a spec from stdin, validates structure, creates branch + spec files + commit.
2. `ai-eng spec save` rejects malformed input with clear error messages.
3. `agents/plan.md` produces spec as conversation text, calls `ai-eng spec save`, then STOPS.
4. `.github/copilot-instructions.md` exists and references the framework's plan/execute flow.
5. `.cursor/rules/ai-engineering.mdc` exists and references the framework's plan/execute flow.
6. End-to-end: `/ai:plan` produces spec -> `ai-eng spec save` persists -> `/ai:execute` reads and works.
7. No IDE plan mode is required at any point in the workflow.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-037-1 | CLI persists specs, not LLM | Eliminates execution leak — LLM produces text, CLI writes files |
| D-037-2 | No IDE plan mode dependency | Binary modes (read-only/full) don't support scoped writes |
| D-037-3 | Spec from stdin (pipe) | Universal across shells/IDEs; fallback `--file` for edge cases |
| D-037-4 | Existing manual spec flow preserved | `ai-eng spec save` is preferred path, manual remains for direct `/ai:spec` |
