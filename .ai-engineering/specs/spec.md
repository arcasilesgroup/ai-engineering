---
spec: spec-165
title: Observation Consolidation Nudge + Scheduled Sweep
status: in-progress
effort: medium
summary: Fix the un-triggered session-watch consolidation loop — a deterministic SessionStart nudge surfaces the pending-review backlog, and a new scheduled /ai-session-watch-sweep skill runs --review into a draft chore PR so corrections actually consolidate without manual prompting.
---

## Summary

The framework has two learning systems that share the `observations.yml`
corpus. **System A** (`instinct-extract.py`, a Stop hook) drains
`observation-events.ndjson` into the corpus automatically every session
end — it works (`meta.json lastExtractedAt` advances each run).
**System B** — `/ai-session-watch --review` — is the *only* path that
LLM-extracts the `corrections` section (user corrections to AI behavior),
enriches the hook-detected patterns, and files work items. System B is
**manual / on-demand** and has **no reliable trigger**: it is LLM-bound
(can't live in a <1s hot-path hook), `/ai-pr` lists it as a skippable
advisory step, and nothing fires it on a cadence. Result: the
highest-value signal — operator corrections — only consolidates when a
human remembers to type `/ai-session-watch --review` (last genuine corpus
change: 2026-06-02). This spec closes the System-B trigger gap with two
complementary mechanisms: a visibility **nudge** and a scheduled
**sweep**.

## Goals

- Make the pending-review backlog **visible**: a deterministic
  SessionStart nudge that says how stale the consolidation is.
- Make consolidation **reliably run** without manual prompting: a
  scheduled sweep that executes `--review` and lands the result in a
  draft chore PR for human review.
- Keep the hot path fast: the nudge is O(1) and adds no LLM call.
- Keep feature PRs clean: consolidation output never rides a feature PR
  (the scope concern that makes operators skip `--review` today).
- Leave System A (automatic instinct extraction) untouched — it already
  works; this spec only fixes System B.

## Non-Goals

- **No auto-cron creation.** The sweep skill never self-registers a
  schedule; the operator authorizes it via `/schedule weekly` (mirrors
  `/ai-simplify-sweep`).
- **No work-item auto-creation in the sweep.** Unattended issue filing is
  out (spam risk); interactive `--review` keeps its work-item step.
- **No change to System A** (`instinct-extract.py` Stop hook,
  `lastExtractedAt`, `deltaThreshold`).
- **No LLM call on the hot path.** The nudge is pure deterministic
  bookkeeping.
- **No sub-weekly cadence** (floods reviewers — same rule as
  `/ai-simplify-sweep`).
- **No new consolidation logic.** The sweep reuses the existing
  `/ai-session-watch --review`; it does not re-implement extraction.

## Decisions

### D-165-01 — Scope: both nudge and sweep

v1 ships the SessionStart nudge AND the scheduled sweep.

**Rationale**: They are complementary defense-in-depth. The sweep fixes
the root cause (no reliable trigger); the nudge fixes visibility so the
backlog stops being invisible between sweeps and so a human can act
sooner. Nudge-only leaves the root cause unfixed; sweep-only leaves the
backlog invisible. Both is the debug recommendation.

### D-165-02 — Sweep packaging: new `/ai-session-watch-sweep` skill

A thin scheduled wrapper skill mirroring `/ai-simplify-sweep` 1:1: invoke
`/ai-session-watch --review` (work-item creation suppressed per D-165-04),
run the pre-commit gate, open a **draft** chore PR, and exit clean with a
status event when there is nothing to consolidate (no empty PR). The
operator registers it via `/schedule weekly /ai-session-watch-sweep`; the
skill never self-creates cron.

**Rationale**: Reuses a proven, reviewed pattern (`/ai-simplify-sweep`)
rather than inventing scheduling. A separate skill keeps the autonomous
PR-opening concern out of the interactive review skill, and the draft PR
keeps consolidation out of feature branches (Goal: clean feature PRs).

### D-165-03 — Nudge: deterministic SessionStart, O(1) signal

The nudge emits a one-line `additionalContext` at SessionStart (same
channel as progressive-disclosure) when there are un-reviewed
observations. The staleness signal MUST be O(1) on the hot path — e.g.
compare `observation-events.ndjson` mtime against the new
`lastReviewedAt` marker — and MUST NOT scan the 7 MB / 16k-line event
stream. Wording is informational ("observations pending review since
<date> — run /ai-session-watch --review"), never blocking.

**Rationale**: SessionStart is automatic, once-per-session, and
well-timed (start of work). Hot-path discipline (<1s pre-commit budget,
deterministic plane) forbids both an LLM call and a full-file scan, so the
signal is a cheap timestamp/mtime comparison, not an exact recount.

### D-165-04 — Sweep suppresses work-item creation

The autonomous sweep runs `--review`'s extract → enrich → write steps
only; it does NOT file work items. Consolidated lessons land in the draft
PR; a human decides what becomes an issue. Interactive
`/ai-session-watch --review` is unchanged and keeps step 5.

**Rationale**: An unattended weekly run that auto-files issues would flood
the board with untriaged work items. The draft PR is already the human
review gate; work-item creation stays a human decision.

### D-165-05 — Add `lastReviewedAt` + `reviewDeltaThreshold` to meta.json

`observations/meta.json` gains `lastReviewedAt` (ISO timestamp, stamped on
completion by BOTH interactive `--review` and the sweep) and
`reviewDeltaThreshold` (default 10), distinct from System A's
`lastExtractedAt` / `deltaThreshold`. The nudge reads only these (plus the
NDJSON mtime) to decide whether to fire.

**Rationale**: System B needs its own checkpoint; reusing System A's
`lastExtractedAt` would couple the two independent loops and mis-report
staleness (extraction runs every session; review does not). A separate
key keeps the single-source-of-truth boundary between the two systems
clean.

### D-165-06 — System A is out of scope and unchanged

`instinct-extract.py` (Stop hook), `lastExtractedAt`, and `deltaThreshold`
are not modified. This spec only adds the System-B trigger + visibility.

**Rationale**: System A already runs reliably (evidence:
`lastExtractedAt` advances every session). Touching it would risk a
working hot-path hook for no benefit; the gap is exclusively System B.

## Risks

- **Hot-path budget on the nudge.** A naive implementation scanning the
  7 MB NDJSON on SessionStart would blow the budget. *Mitigation:* D-165-03
  mandates an O(1) mtime/timestamp signal; a perf test asserts no
  full-file read on the hot path.
- **Hook edit blast radius.** Editing a SessionStart hook breaks its
  `hooks-manifest.json` sha (integrity self-disable trap) and needs
  byte-parity with the template mirror. *Mitigation:* run
  `regenerate-hooks-manifest.py`, copy byte-identical to the
  `src/.../templates/` mirror, and add tests in both suites (the
  spec-159/161 parity lessons).
- **New skill surface fan-out.** A new skill must register in the manifest
  and regenerate 4 mirror surfaces with parity (`count_parity`,
  `surface_parity`, `template_skill_parity`). *Mitigation:* scaffold via
  the established skill pattern + `ai-eng dev sync`; CI parity guards
  catch drift.
- **Writer contention on `observations.yml`.** System A (Stop hook) and
  System B (`--review`/sweep) both write the corpus. *Mitigation:* the
  sweep reuses `--review` (no new writer); `lastReviewedAt` lives in the
  separate `meta.json`; rely on the existing locked-append path.
- **Scheduling not wired by default.** The sweep only runs if the operator
  registers the cron. *Mitigation:* documented `/schedule weekly`
  invocation in the skill (same as `/ai-simplify-sweep`); the nudge is the
  safety net when the schedule is absent.

## References

- doc: .claude/skills/ai-simplify-sweep/SKILL.md (the scheduled-wrapper + draft-PR pattern mirrored by D-165-02)
- doc: .claude/skills/ai-session-watch/SKILL.md (the --review consolidation this wraps)
- doc: .ai-engineering/scripts/hooks/_lib/instincts.py (System A corpus writer; INSTINCTS_REL / lastExtractedAt)
- doc: .ai-engineering/observations/meta.json (checkpoint store gaining lastReviewedAt + reviewDeltaThreshold)

## Open Questions

_None — all v1 decisions resolved._
