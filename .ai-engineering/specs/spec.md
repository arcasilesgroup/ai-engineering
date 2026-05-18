---
spec: spec-000
title: No active spec
status: done
effort: trivial
summary: Idle placeholder for the canonical spec slot after delivered specs are archived or moved to history.
---

## Summary

There is no active implementation spec in the canonical working slot.
Start a new spec with `/ai-brainstorm` before implementation work.

## Goals

- Keep `.ai-engineering/specs/spec.md` structurally valid while idle.
- Make the inactive state explicit for humans and automation.

## Non-Goals

- Do not describe completed implementation work in this idle placeholder.

## Decisions

- **D-000-01 — Use a lint-clean idle placeholder.** The canonical spec slot remains valid markdown with required schema sections even when no spec is active.
  *Rationale*: Integration gates self-validate the canonical spec path, so the idle state must remain machine-parseable.

## Risks

- A reader may mistake this placeholder for active work; the summary and title explicitly state that no active spec exists.
