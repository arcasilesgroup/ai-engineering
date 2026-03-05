---
id: "037"
slug: "pr-workflow-hardening"
status: "in-progress"
created: "2026-03-05"
size: "L"
tags: ["governance", "pr", "workflow", "reliability"]
branch: "spec-037/pr-workflow-hardening"
pipeline: "full"
decisions: []
---

# Spec 037 — PR Workflow Hardening

## Problem

The governed PR flow is not consistently producing complete PR descriptions and has shown unstable behavior during create/edit operations. This creates governance drift between the documented PR contract and real execution outcomes, reducing auditability and reviewer confidence.

## Solution

Harden the PR workflow path by enforcing deterministic create-or-update behavior, robust multiline body handling, and strict parity between skill contract, command implementation, prompts, and validation tests.

## Scope

### In Scope

- Align `/ai:pr` contract and implementation for create vs update behavior.
- Ensure PR body generation/update is deterministic and preserves structured sections.
- Consolidate prompt surface to avoid conflicting PR execution semantics.
- Add regression coverage for PR create/edit/automerge paths.
- Improve observability of PR workflow outcomes for diagnostics.

### Out of Scope

- Re-architecting unrelated agent skills or command families.
- Changing release policy thresholds outside PR workflow needs.
- Broad refactors not required for PR contract parity.

## Acceptance Criteria

1. Existing-PR branch path uses append-only update semantics (does not overwrite body).
2. New-PR branch path reliably creates structured description (What/Why/How/Checklist).
3. PR workflow no longer depends on fragile inline multiline shell body payloads.
4. Prompt and command contract surfaces for PR are unified and non-conflicting.
5. Integration tests cover both create and update PR flows with deterministic assertions.
6. Governance validation (`ai-eng validate`) remains PASS after changes.

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| D-037-001 | Treat PR upsert as first-class deterministic behavior | Prevent body loss and contract drift |
| D-037-002 | Prefer file-backed body payloads over inline multiline body flags | Avoid shell quoting/heredoc instability |
