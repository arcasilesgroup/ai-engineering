# spec-126 Cleanup — History Backfill

**Discovery Date**: 2026-05-07
**Context**: Post-merge cleanup for spec-126 (PR #506). User requested full
backfill of unrecorded specs into `_history.md`.

## Action

Replace the current top of `_history.md` table with the rows below. They
slot above `| 125 |` (which is already present). Adds spec-126, 124, 123,
122, 121, 120 in chronological-descending order matching existing table
convention.

## Rows to insert (above row for spec-125)

```markdown
| 126 | Hook-side NDJSON Append Lock Parity (Windows multi-IDE concurrency fix) | done | 2026-05-07 | feat/spec-126-hook-ndjson-lock-parity |
| 124 | State JSON Fallback Deletion + Canonical Guard (wave 5 of 122 umbrella) | done | 2026-05-06 | feat/spec-122-framework-cleanup-phase-1 |
| 123 | specs/ Canonical Structure Migration + CONSTITUTION Article XIII | done | 2026-05-06 | feat/spec-122-framework-cleanup-phase-1 |
| 122 | Framework Cleanup Phase 1 — Hygiene + Config + Eval Cleanup + State-Plane Consolidation (sub-specs 122-a/b/d) | done | 2026-05-05 | feat/spec-122-framework-cleanup-phase-1 |
| 121 | Self-Improvement Loop + Hook Event Coverage Closure | done | 2026-05-04 | feat/spec-120-observability-modernization |
| 120 | Observability Modernization — Ralph Loop + PRISM Risk Accumulator + Runtime Layer | done | 2026-05-04 | feat/spec-120-observability-modernization |
```

## Provenance

Titles + dates derived from `git log --all --format="%cs %h %s"` filtered
per spec id. Branches resolved via `git log --all --format="%D"`. Verified
2026-05-07.

- **spec-120**: branch `feat/spec-120-observability-modernization`,
  representative commit "feat(spec-120): finish Ralph + PRISM (call sites,
  runtime-guard warn, mirror, docs)".
- **spec-121**: same branch, commit `a19053ad` "feat(spec-121): close
  self-improvement loop + hook event coverage".
- **spec-122**: branch `feat/spec-122-framework-cleanup-phase-1`,
  multi-wave umbrella with sub-specs `122-a` (Hygiene + Config + Delete
  Evals), `122-b` (state-plane consolidation), `122-d` (per spec-125
  D-122-27 reference). Representative commit `7210efe9` "docs(spec-122):
  autopilot integrity report + final manifest".
- **spec-123**: same branch, commit `eef76d0e` "feat(spec-123): wave 4 -
  specs/ canonical structure migration", commit `ab8faad1` "wave 5 -
  CONSTITUTION Article XIII + autopilot bug fix".
- **spec-124**: same branch, commit `1cb3cb0d` "feat(spec-124): wave 5 -
  delete migrated state JSON fallbacks + canonical guard".
- **spec-126**: branch `feat/spec-126-hook-ndjson-lock-parity`, PR #506,
  commit `5a28d40`.

## Cleanup sequence (post-merge of #506)

1. `gh pr view 506 --json state` → confirm `MERGED`.
2. `git checkout main && git pull`.
3. `git checkout -b chore/spec-126-cleanup-and-history-backfill`.
4. Insert the 6 rows above between header and the spec-125 row in
   `.ai-engineering/specs/_history.md`.
5. Replace `.ai-engineering/specs/spec.md` with placeholder:
   ```
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```
6. Replace `.ai-engineering/specs/plan.md` with placeholder:
   ```
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```
7. Stage, gitleaks, ruff (no Python touched), commit:
   `chore: clear spec state + backfill _history (specs 120-124, 126)`.
8. Push, open PR or fast-forward.

Optional: delete this note file in the same commit (it has served its
purpose as a checkpoint).
