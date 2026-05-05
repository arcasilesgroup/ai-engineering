---
spec: spec-122-d
title: Framework Cleanup Phase 1-D — Meta-Cleanup (Docs + Scripts + Drift)
status: approved
effort: medium
---

# Spec 122-d — Meta-Cleanup (Docs + Scripts + Drift)

> Sub-spec of [spec-122 master](./spec-122-framework-cleanup-phase-1.md).
> Implements decisions D-122-24..28, D-122-31, D-122-29 (doc-test
> slice), D-122-35, D-122-37. **Depends on spec-122-a, spec-122-b, and
> spec-122-c** (docs reference final state; scripts split touches
> sync_command_mirrors which propagates the cleaned skill set).

## Summary

The framework's documentation, mirror-sync script, and CI guard surfaces
have drifted relative to the actual codebase: `CONSTITUTION.md` and the
project template still reference `/ai-implement` (a skill that does not
exist; current is `/ai-dispatch`); `.claude/settings.json` registers 11
hook events while CLAUDE.md and ADR-004 reference 8-10; `docs/` contains
a 32 KB `solution-intent.md` that pre-dates the Phase 1 cleanup; the
`scripts/sync_command_mirrors.py` propagator is an 82 KB single-file
monolith with ~50 functions/classes; a spec-106-era
`scripts/skill-audit.sh` (82 LOC) lingers without confirmed runtime
relevance; hot-path SLO budgets (pre-commit < 1 s p95, pre-push < 5 s
p95) are documented but not CI-enforced; `.gitignore` does not globally
ignore `.DS_Store` (multiple `.DS_Store` blobs already present in
`.codex/` and `docs/`); `CHANGELOG.md` (116 KB) lacks per-sub-spec
delivery entries.

This sub-spec is the meta-cleanup wave: nothing it changes affects
runtime correctness, but every change reduces user confusion and locks
the cleaned state in via CI guards.

## Goals

- `scripts/sync_command_mirrors.py` (82 KB monolith) split into
  `scripts/sync_mirrors/` modular package: `__main__.py` (CLI entry),
  `core.py` (discovery), `frontmatter.py` (YAML parsing),
  `manifest_sync.py`, plus per-IDE writers
  (`claude_target.py`, `codex_target.py`, `gemini_target.py`,
  `copilot_target.py`). Backwards-compat shim at
  `scripts/sync_command_mirrors.py` preserves all CI / skill
  invocation paths.
- `docs/` folder cleanup pass:
  - `.DS_Store` files deleted globally; `.gitignore` updated.
  - `solution-intent.md` (32 KB) rewritten to reflect post-Phase-1
    framework state.
  - `cli-reference.md` updated with new
    `ai-eng audit retention/rotate/compress/verify-chain/health/vacuum`
    subcommands.
  - `agentsview-source-contract.md`, `anti-patterns.md`,
    `ci-alpine-smoke.md`, `copilot-subagents.md` audited and refreshed
    if stale.
- `scripts/skill-audit.sh` evaluation: run once on the repo, compare
  output to `/ai-platform-audit --all`. If subset → DELETE the .sh
  script. If complement → KEEP and document in `manifest.yml
  required_tools` for survival.
- Hook canonical event count alignment: drop dead wirings, update
  CLAUDE.md / AGENTS.md / ADR-004 to the actual count after audit, add
  CI guard `tests/unit/hooks/test_canonical_events_count.py`.
- Hot-path SLO tests added in
  `tests/unit/hooks/test_hot_path_slo.py`: assert pre-commit < 1 s
  p95, pre-push < 5 s p95, individual hook invocation < 50 ms.
- Documentation drift audit:
  - Replace `/ai-implement` references in `CONSTITUTION.md` and
    `src/ai_engineering/templates/project/CONSTITUTION.md` with
    `/ai-dispatch`.
  - Cross-check skill listings in `AGENTS.md`, `CLAUDE.md`,
    `GEMINI.md`, `.github/copilot-instructions.md`, `README.md`
    against actual `.claude/skills/` directory listing.
  - Verify decision references in skill bodies (`spec-118`,
    `spec-119`, etc.) vs `_history.md` (specs deleted by Phase 1
    removed from skill instructions).
  - Repo-wide grep for skill names that no longer exist
    (`/ai-implement`, `/ai-eval-gate`, `/ai-eval`) and replace or
    remove.
  - Add CI guard `tests/unit/docs/test_skill_references_exist.py`
    asserting every `/ai-*` reference in markdown files corresponds
    to a skill in `.claude/skills/`.
- `.gitignore` global junk patterns added (`.DS_Store`, `Thumbs.db`,
  `desktop.ini`, editor swp files); `state.db*`, `state.db-wal`,
  `state.db-shm` ignored; pre-existing committed `.DS_Store` files
  purged from history.
- `CHANGELOG.md` populated with `[Unreleased]` entries per sub-spec
  (a / b / c / d), auto-generated from spec frontmatter + git diff
  stat by `/ai-pr`.
- Phase 1 test coverage gate: each sub-spec PR includes matching
  test coverage; `tests/integration/state/test_db_migration.py`,
  `tests/integration/governance/test_opa_eval.py`,
  `tests/integration/memory/test_engram_subprocess.py` are merge
  prerequisites.

## Non-Goals

- Rewriting `solution-intent.md` content beyond reflecting Phase 1
  changes (a separate spec may redo solution-intent from scratch
  for v2).
- Refactoring the `scripts/install.sh` install-time generators
  beyond what spec-122-b and spec-122-c require.
- Adding new hook events. The audit reduces or aligns existing
  wirings; new event creation is out of scope.
- Adding new docs files. The audit refreshes existing docs.
- Adding new skills or agents.

## Decisions

This sub-spec **imports** the following master decisions verbatim:

| ID | Decision title |
|---|---|
| D-122-24 | `scripts/sync_command_mirrors.py` split + audit |
| D-122-25 | `docs/` folder cleanup pass |
| D-122-26 | `scripts/skill-audit.sh` evaluation |
| D-122-27 | Hook canonical events count alignment |
| D-122-28 | Hot-path SLO test coverage |
| D-122-29 (doc-test slice) | Phase 1 test coverage for new artifacts |
| D-122-31 | Documentation drift audit + repair pass |
| D-122-35 | `.gitignore` audit + global junk patterns |
| D-122-37 | CHANGELOG.md entry per sub-spec delivery |
| D-122-40 | Spec path canonicalization — kill `specs/spec.md` doc drift |

## Acceptance Criteria

- `wc -c scripts/sync_command_mirrors.py` ≤ 2,000 (shim only).
- `find scripts/sync_mirrors -name '*.py' | wc -l` ≥ 7 (per-IDE
  writers + core + frontmatter + manifest_sync + main).
- `find . -name '.DS_Store' -not -path './.git/*'` returns empty.
- `grep '\.DS_Store' .gitignore` returns ≥ 1 match.
- `grep -rn '/ai-implement' --include='*.md'` returns empty (no stale
  references).
- `tests/unit/docs/test_skill_references_exist.py` asserts every
  markdown `/ai-*` reference resolves to a skill directory; passes.
- `tests/unit/hooks/test_canonical_events_count.py` passes; CLAUDE.md
  hook event count matches `.claude/settings.json` `len(.hooks)`.
- `tests/unit/hooks/test_hot_path_slo.py` passes; pre-commit p95 < 1 s
  measured over 50 invocations.
- `grep '\[Unreleased\]' CHANGELOG.md` shows entries for each
  sub-spec a / b / c / d.
- `cat docs/cli-reference.md | grep 'ai-eng audit retention'` shows
  the new command documented.
- Either `find scripts/skill-audit.sh` returns empty (deleted) or
  `grep skill-audit.sh manifest.yml` shows it documented in
  required_tools.
- `grep -rn 'specs/spec.md\|specs/plan.md\|specs/autopilot/' .claude/skills/ .gemini/skills/ .codex/skills/ .agents/skills/ 2>/dev/null`
  returns empty after canonicalization.
- `tests/unit/skills/test_spec_path_canonical.py` asserts no skill
  markdown references legacy `specs/spec.md` / `specs/plan.md` /
  `specs/autopilot/` paths.

## Decision Detail — D-122-40

Canonical active-spec path: `.ai-engineering/specs/spec.md` (matches
resolver default in `src/ai_engineering/state/work_plane.py:240`).
Numbered archive `.ai-engineering/specs/spec-NNN-name.md` lives in
same directory. Skill markdown referencing legacy `specs/spec.md`,
`specs/plan.md`, `specs/autopilot/manifest.md` rewritten to canonical
path. HX-02 moved resolver but skills not updated; caused user-visible
autopilot Step 0 failure on spec-122 invocation. Mechanical doc-only
fix across `.claude/skills/`, `.gemini/skills/`, `.codex/skills/`,
`.agents/skills/`. Adds CI guard preventing regression. Documents
dual surface (active buffer vs numbered archive).

## Risks

- **`sync_command_mirrors.py` shim breaking external tooling**:
  third-party CI workflows or skills may import the script directly.
  **Mitigation**: shim preserves the public CLI surface byte-for-byte;
  `tests/integration/sync/test_sync_compat.py` invokes the shim
  with all known argument combinations and asserts equivalent output
  vs the new package.
- **Skill listing audit missing IDE-only patterns**: a skill present in
  `.gemini/skills/` only (not yet synced to `.claude/`) could be
  flagged as drift incorrectly. **Mitigation**: audit walks all four
  IDE skill dirs and warns rather than fails; CI guard checks `.claude/`
  as the canonical source post-`sync_command_mirrors`.
- **CHANGELOG auto-generation diverging from manual edits**: the
  `/ai-pr` skill auto-generates the changelog block; manual edits
  may be overwritten on next PR. **Mitigation**: auto-generation
  appends below an `<!-- AUTO -->` marker; manual edits go above;
  the marker prevents collision.
- **Hot-path SLO test flakiness on CI runners**: cold cache + slow
  hardware can push pre-commit timing above 1 s p95. **Mitigation**:
  test runs 50 iterations, asserts p95 (not max); allows ±20%
  slack on CI runners (`os.getenv('CI')` flag); fails only if median
  > budget × 1.5.
- **`.DS_Store` purge from git history**: `git filter-repo` rewrites
  history; downstream forks must rebase. **Mitigation**: only purge
  `.DS_Store` from current working tree (`git rm --cached`); leave
  history untouched; `.gitignore` prevents re-adding. Full history
  rewrite is a separate decision if regulators demand it.
- **Solution-intent rewrite scope creep**: a 32 KB rewrite tempts
  unrelated changes. **Mitigation**: rewrite stays narrow to
  Phase-1-affected sections; structural / aesthetic changes filed as
  follow-up `spec-123-docs-restructure`.

## References

- doc: spec-122-framework-cleanup-phase-1.md (master)
- doc: spec-122-a-hygiene-and-evals-removal.md (dependency)
- doc: spec-122-b-engram-and-state-unify.md (dependency)
- doc: spec-122-c-opa-proper-switch.md (dependency)
- doc: scripts/sync_command_mirrors.py
- doc: scripts/skill-audit.sh
- doc: docs/solution-intent.md
- doc: docs/cli-reference.md
- doc: docs/anti-patterns.md
- doc: docs/ci-alpine-smoke.md
- doc: docs/copilot-subagents.md
- doc: docs/agentsview-source-contract.md
- doc: CHANGELOG.md
- doc: .gitignore
- doc: CONSTITUTION.md
- doc: src/ai_engineering/templates/project/CONSTITUTION.md
- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: .github/copilot-instructions.md
- doc: README.md
