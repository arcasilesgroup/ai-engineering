# Asset Follow-up — spec-144

## Status

[PENDING] Design asset count drift is deferred from the README rewrite and branch-cleanup rename delivery.

## Context

Spec-144 updates Markdown onboarding and skill naming. It does not edit `docs/design.pen` or `docs/untitled.pen`; those files are visual design sources and remain out of scope for this PR.

## Follow-up Payload

Title: Refresh stale design-asset counts after spec-144 README rewrite

Scope:

- Review stale count references captured for `docs/design.pen:15131`.
- Review stale count references captured for `docs/untitled.pen:482`.
- Update the design sources only through the design-asset workflow.

Acceptance:

- The asset counts match the current skill/surface inventory.
- No Markdown README or skill rename work is bundled into the asset update.
- The follow-up references spec-144 as the source of the deferral.

## Blocked Reason

Provider-backed issue creation was not required for local delivery evidence in this run; this file is the fallback payload for a later `/ai-issue` handoff.
