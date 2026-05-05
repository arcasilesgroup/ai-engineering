---
id: sub-004
parent: spec-122
title: "Meta-Cleanup (Docs + Scripts + Drift)"
status: planning
files:
  - scripts/sync_command_mirrors.py
  - scripts/sync_mirrors/__init__.py
  - scripts/sync_mirrors/__main__.py
  - scripts/sync_mirrors/core.py
  - scripts/sync_mirrors/frontmatter.py
  - scripts/sync_mirrors/manifest_sync.py
  - scripts/sync_mirrors/claude_target.py
  - scripts/sync_mirrors/codex_target.py
  - scripts/sync_mirrors/gemini_target.py
  - scripts/sync_mirrors/copilot_target.py
  - scripts/skill-audit.sh
  - docs/.DS_Store
  - docs/solution-intent.md
  - docs/cli-reference.md
  - docs/anti-patterns.md
  - docs/ci-alpine-smoke.md
  - docs/copilot-subagents.md
  - docs/agentsview-source-contract.md
  - .gitignore
  - CONSTITUTION.md
  - src/ai_engineering/templates/project/CONSTITUTION.md
  - AGENTS.md
  - CLAUDE.md
  - GEMINI.md
  - .github/copilot-instructions.md
  - README.md
  - CHANGELOG.md
  - .claude/settings.json
  - .ai-engineering/contexts/spec-schema.md
  - .ai-engineering/manifest.yml
  - .claude/skills/ai-brainstorm/SKILL.md
  - .claude/skills/ai-brainstorm/handlers/spec-review.md
  - .claude/skills/ai-mcp-sentinel/SKILL.md
  - .claude/skills/ai-commit/SKILL.md
  - .claude/skills/ai-autopilot/SKILL.md
  - .claude/skills/ai-autopilot/handlers/phase-decompose.md
  - .claude/skills/ai-autopilot/handlers/phase-deep-plan.md
  - .claude/skills/ai-autopilot/handlers/phase-orchestrate.md
  - .claude/skills/ai-autopilot/handlers/phase-implement.md
  - .claude/skills/ai-autopilot/handlers/phase-quality.md
  - .claude/skills/ai-autopilot/handlers/phase-deliver.md
  - .claude/skills/ai-dispatch/SKILL.md
  - .claude/skills/ai-dispatch/handlers/deliver.md
  - .claude/skills/ai-pr/SKILL.md
  - .claude/skills/ai-standup/SKILL.md
  - .claude/skills/ai-run/handlers/phase-item-plan.md
  - .claude/skills/_shared/execution-kernel.md
  - .claude/skills/ai-docs/handlers/solution-intent-init.md
  - .claude/skills/ai-docs/handlers/solution-intent-sync.md
  - .claude/skills/ai-start/SKILL.md
  - .claude/skills/ai-plan/SKILL.md
  - .claude/skills/ai-plan/handlers/design-routing.md
  - .gemini/skills/
  - .codex/skills/
  - tests/unit/skills/test_spec_path_canonical.py
  - tests/unit/hooks/test_canonical_events_count.py
  - tests/unit/hooks/test_hot_path_slo.py
  - tests/unit/docs/__init__.py
  - tests/unit/docs/test_skill_references_exist.py
  - tests/integration/sync/test_sync_compat.py
depends_on: [sub-001, sub-002, sub-003]
source_spec: .ai-engineering/specs/spec-122-d-meta-cleanup.md
---

# Sub-Spec 004: Meta-Cleanup (Docs + Scripts + Drift)

## Scope

Documentation, mirror-sync script, and CI guard meta-cleanup:
- Split `scripts/sync_command_mirrors.py` (2,032 LOC monolith) into `scripts/sync_mirrors/` package per IDE.
- `docs/` cleanup: delete `.DS_Store` globally, refresh `solution-intent.md`, update `cli-reference.md` with new audit subcommands, audit `agentsview-source-contract.md` / `anti-patterns.md` / `ci-alpine-smoke.md` / `copilot-subagents.md`.
- Evaluate `scripts/skill-audit.sh`: subset of `/ai-platform-audit` → DELETE; complement → KEEP + document in manifest.yml.
- Hook canonical event count alignment + CI guard.
- Hot-path SLO tests (pre-commit <1s p95, pre-push <5s p95).
- Documentation drift: replace `/ai-implement` → `/ai-dispatch`, cross-check skill listings, spec references, repo-wide grep for ghost skills.
- `.gitignore` global junk patterns + `state.db*` + `.DS_Store` purge from working tree.
- `CHANGELOG.md` per-sub-spec entries.
- **D-122-40: Spec path canonicalization** — rewrite skill markdown from
  legacy `specs/spec.md` to canonical `.ai-engineering/specs/spec.md` across
  `.claude/skills/`, `.gemini/skills/`, `.codex/skills/` (the `.agents/skills/`
  tree is empty/non-existent in this repo; D-122-40 covers the three IDE
  trees that exist). Add CI guard.

## Source

Full spec: `.ai-engineering/specs/spec-122-d-meta-cleanup.md`.

Decisions imported: D-122-24..28, D-122-31, D-122-29 (doc-test slice), D-122-35,
D-122-37, D-122-40.

## Exploration

### Existing Files

**Script split target (D-122-24)**
- `scripts/sync_command_mirrors.py` — 2,032 LOC; ~50 top-level
  defs spanning: skill discovery, frontmatter parsing
  (`_extract_frontmatter`, `_validate_skill_frontmatter`), per-IDE
  rendering (`render_gemini_md_placeholders`,
  `generate_copilot_instructions`), canonical/manifest validation
  (`validate_canonical`, `validate_manifest`), surface generation
  (`_generate_surface`), orphan handling (`_handle_orphans`), core
  write-or-check (`_check_or_write`). All in one file with mixed
  responsibilities. Imported as a module by 3+ skills (ai-skill-evolve,
  ai-pipeline) per master spec D-122-24.

**Skill-audit evaluation (D-122-26)**
- `scripts/skill-audit.sh` — 82 LOC; spec-106 D-106-04 advisory
  shell script. Loops `.claude/skills/ai-*/SKILL.md`, calls
  `uv run ai-eng skill eval` (CLI verb does NOT exist; falls back to
  `eval-failed-cli-missing` literal), writes `audit-report.json`.
  Always exits 0 (advisory). The eval CLI never landed; this is a
  no-op-with-pretty-output script. Dependency: `jq`.
  `manifest.yml required_tools` does not currently list it.

**Docs folder (D-122-25)**
- `docs/.DS_Store` (6 KB) — macOS junk, committed; DELETE.
- `docs/solution-intent.md` (776 LOC, 32.6 KB) — references
  pre-Phase-1 state (memory.db, evals/, custom Rego, etc.). REFRESH
  Phase-1-affected sections only (per Risks: avoid scope creep).
- `docs/cli-reference.md` (112 LOC, 5 KB) — current list ends at
  "Platform setup". Missing the `ai-eng audit
  retention/rotate/compress/verify-chain/health/vacuum` subcommands
  shipped by sub-002 (D-122-22). UPDATE.
- `docs/anti-patterns.md` (24 LOC) — small; AUDIT only.
- `docs/ci-alpine-smoke.md` (93 LOC) — verify alpine version is
  current.
- `docs/copilot-subagents.md` (136 LOC) — pre-spec-120; audit.
- `docs/agentsview-source-contract.md` (24 LOC) — short tool
  contract; verify post-spec-120 alignment.
- `docs/design.pen` — Pencil binary, KEEP, do not touch via Read.
- `docs/event-assets/`, `docs/presentations/` — KEEP.

**`.gitignore` (D-122-35)**
- Already ignores: `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.swp`,
  `*.swo`, `*~`, `.idea/`, `.vscode/`, `.ai-engineering/state/runtime/`,
  `.ai-engineering/state/audit-index.sqlite*`,
  `.ai-engineering/state/memory.db*`. **Does NOT yet ignore**:
  `**/.DS_Store` (subdir variant — current line is bare `.DS_Store`,
  which is sufficient via gitignore semantics, but adding `**/` is
  defensive), `state.db*`, `state.db-wal`, `state.db-shm` (sub-002
  artifacts). Pre-existing committed `.DS_Store` files: `docs/.DS_Store`
  (6 KB). One file, working-tree purge only (no history rewrite per
  Risks).

**Hook canonical event count (D-122-27)**
- `.claude/settings.json` registers **11 top-level event keys**:
  UserPromptSubmit (2 matchers), PreToolUse (4), PostToolUse (4),
  PostToolUseFailure (1), Stop (1), PreCompact (1), PostCompact (1),
  SessionStart (1), SubagentStop (1), Notification (1), SessionEnd (1).
  Total = 11 events. CLAUDE.md and AGENTS.md reference "8/10
  canonical events" in some places (master spec D-122-27 documents
  this drift). After audit: drop dead matchers, document the actual
  count, add CI guard.

**Hot-path SLO (D-122-28)**
- CLAUDE.md asserts pre-commit < 1 s p95, pre-push < 5 s p95,
  individual hook < 50 ms. No timing tests exist. Existing
  `tests/unit/hooks/` has 18 test files (test_hook_integrity.py,
  test_runtime_*, test_lib_*) — proven pattern: `pytest` +
  module-loaded-from-path via `importlib.util.spec_from_file_location`,
  with `REPO = Path(__file__).resolve().parents[3]`.

**Doc drift (D-122-31)**
- `/ai-implement` references in canonical docs: 2 occurrences
  (`CONSTITUTION.md:18`, `src/ai_engineering/templates/project/CONSTITUTION.md:18`).
  Replace with `/ai-dispatch`.
- `/ai-eval-gate`, `/ai-eval`: 0 occurrences in the audited canonical
  doc set (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`, `README.md`).
- Skill listings in canonical docs vs `.claude/skills/`: skill
  directory contains 53 `ai-*/` entries (verified by ls). Drift audit
  cross-checks each canonical doc's skill list against this set.
- `tests/unit/docs/` directory **does not exist**; create with
  `__init__.py` + `test_skill_references_exist.py`.

**CHANGELOG (D-122-37)**
- `CHANGELOG.md` (1,075 LOC, 116 KB) currently has `## [Unreleased]`
  block (line 8) describing 0.5.0 work. Pattern: `## [Unreleased]` →
  `### TL;DR` → `### Added/Changed/Removed (spec-NNN-x)`. Auto-gen
  by `/ai-pr` per master spec D-122-37; collision marker
  `<!-- AUTO -->` per Risks.

**D-122-40 spec path canonicalization (NEW DECISION)**
- Total occurrences across IDE skill trees: **240 lines** in **66
  unique files**. Per-IDE breakdown:
  - `.claude/skills/`: 22 files
  - `.gemini/skills/`: 22 files
  - `.codex/skills/`: 22 files
  - `.agents/skills/`: 0 files (tree does not exist in this repo)
- Affected skills (canonical via `.claude/`): ai-brainstorm,
  ai-mcp-sentinel, ai-commit, ai-autopilot (SKILL + 6 handlers),
  ai-dispatch (SKILL + handlers/deliver), ai-pr, ai-standup, ai-run
  (handlers/phase-item-plan), ai-docs (handlers/solution-intent-init,
  solution-intent-sync), ai-start, ai-plan (SKILL + handlers/design-routing),
  _shared/execution-kernel.
- Pattern targets:
  - `specs/spec.md` → `.ai-engineering/specs/spec.md`
  - `specs/plan.md` → `.ai-engineering/specs/plan.md`
  - `specs/autopilot/` → `.ai-engineering/specs/autopilot/`
  - `specs/_history.md` → `.ai-engineering/specs/_history.md` (if present)
- Already-correct paths (do not touch): instances already prefixed
  with `.ai-engineering/specs/` (e.g., ai-mcp-sentinel:82,
  ai-commit:29, ai-pr:69+81, ai-start:29-30, ai-plan multiple, etc.).
  Rewrite must be idempotent — re-prefixing must not double-prefix.
- `.ai-engineering/contexts/spec-schema.md` referenced from skills
  via the literal string `.ai-engineering/contexts/spec-schema.md`
  (already canonical) — no rewrite needed there; only the `specs/`
  prefix is in scope.

**Test pattern reference**
- `tests/unit/hooks/test_hook_integrity.py` — load module via
  `importlib.util.spec_from_file_location`, REPO via
  `Path(__file__).resolve().parents[3]`. Use this pattern for the
  three new test files.

### Patterns to Follow

**Script split**: Mirror Python package convention used elsewhere
in `scripts/` (e.g., `scripts/memory/` per master spec). Use
`scripts/sync_mirrors/__init__.py` to expose the public API for
backwards compat. The shim `scripts/sync_command_mirrors.py` becomes:

```python
#!/usr/bin/env python3
"""Backwards-compat shim. Real implementation in scripts/sync_mirrors/."""
from sync_mirrors.__main__ import main
if __name__ == "__main__":
    raise SystemExit(main())
```

Target: shim ≤ 2 KB. Public CLI surface preserved byte-for-byte
(argv parsing lives in `__main__.py`).

**Test scaffolding**: copy the `tests/unit/hooks/test_hook_integrity.py`
header pattern (`from __future__ import annotations`, `REPO =
Path(__file__).resolve().parents[3]`, pytest fixtures). For SLO
timing, use `time.perf_counter` + `statistics.quantiles` to compute
p95 over 50 iterations. CI slack via `os.getenv("CI")`.

**CHANGELOG entry shape** (per master spec D-122-37):

```markdown
## [Unreleased]

### Added (spec-122-d)
- ...
### Removed (spec-122-d)
- ...
### Changed (spec-122-d)
- ...
```

Below `<!-- AUTO -->` marker; manual edits go above.

**D-122-40 rewrite**: a single Python helper at
`scripts/sync_mirrors/spec_path_migrator.py` (or inline-script for
one-shot) walks the four IDE skill trees, applies regex rewrite
with idempotency guard (`(?<!\.ai-engineering/)specs/(spec|plan)\.md`
and similar for `autopilot/`). Idempotency proof: running it twice
yields no diff.

### Dependencies Map

**This sub-spec imports**:
- `sub-001` → final manifest.yml shape (after orphan cleanup), final
  CONSTITUTION.md (after slim), final `.ai-engineering/manifest.yml`
  (skill-audit may need to be added to `required_tools`).
- `sub-002` → `state.db*` filenames for `.gitignore`,
  `ai-eng audit retention/rotate/compress/verify-chain/health/vacuum`
  CLI verbs (for `cli-reference.md` update),
  `ai-eng install` command shape (for solution-intent.md refresh).
- `sub-003` → final OPA wiring (for solution-intent.md governance
  section), Rego policy filenames (for any docs cross-references).

**This sub-spec exports**:
- `scripts/sync_mirrors/` package — discovery + per-IDE writers.
- `scripts/sync_mirrors/__main__.py` — CLI entry replacing
  `sync_command_mirrors.py`.
- Refreshed canonical docs (`CONSTITUTION.md`, `AGENTS.md`,
  `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`,
  `README.md`).
- Refreshed `docs/solution-intent.md`, `docs/cli-reference.md`.
- `.gitignore` updated (sub-002 unblock for `state.db*`).
- 4 new CI guard tests (canonical events count, hot-path SLO, skill
  references exist, spec path canonical).
- `CHANGELOG.md` `[Unreleased]` block populated for a/b/c/d.

**External deps**: `jq` (already required by skill-audit.sh
evaluation step), `pytest` (existing), `time.perf_counter`,
`statistics`, `subprocess` (for hot-path SLO timing).

### Risks

- **Sync shim breaking external CI**: mirror-sync is invoked by
  ai-skill-evolve, ai-pipeline, and CI workflows. Shim must
  preserve `python scripts/sync_command_mirrors.py [args]`
  behaviour byte-for-byte. **Mitigation**: `tests/integration/sync/test_sync_compat.py`
  invokes the shim with all known argument combinations and asserts
  stdout/exit-code parity vs the new package.
- **Doc-drift CI guard false positives on `.gemini/` skills**: if a
  skill exists in `.gemini/` but not yet synced to `.claude/`, the
  guard could flag it. **Mitigation**: guard checks `.claude/` as
  canonical (post-`sync_command_mirrors`). Guard runs after the
  sync step in CI.
- **Hot-path SLO test flakiness on slow CI runners**: 50-iteration
  p95 may exceed 1s on cold cache. **Mitigation**: ±20% slack via
  `os.getenv("CI")`; assert p95 (not max); fail only if median >
  budget × 1.5.
- **Solution-intent rewrite scope creep**: 32 KB rewrite tempts
  unrelated changes. **Mitigation**: rewrite stays narrow to
  Phase-1-affected sections (memory layer → Engram delegation,
  custom Rego → OPA proper, evals/ → deletion, state migration);
  structural restructure deferred to spec-123.
- **D-122-40 idempotency**: re-running the rewrite must not
  double-prefix already-canonical paths. **Mitigation**:
  negative-lookbehind regex `(?<!\.ai-engineering/)specs/spec\.md`;
  pytest covers idempotency (run rewrite twice, assert second run
  yields zero diffs).
- **`.DS_Store` working-tree purge ≠ history**: `git rm --cached`
  removes from index but blob remains in history. Downstream forks
  that already cloned it still have the blob in their history.
  **Mitigation**: working-tree purge only (per master spec Risks);
  `.gitignore` prevents re-add; full `git filter-repo` deferred if
  regulators demand it.
- **CHANGELOG manual-edit collision**: `/ai-pr` auto-gen may
  overwrite manual edits. **Mitigation**: `<!-- AUTO -->` marker;
  auto-gen appends below; manual edits above. Auto-gen scope is
  spec-122-d only in this sub-spec; sub-001/002/003 entries land in
  their respective wave PRs (orchestrated by Phase 6 deliver).
- **Skill-audit.sh deletion path invalidation**: if `manifest.yml
  required_tools` references the .sh script downstream, deletion
  breaks the manifest contract. **Mitigation**: grep `manifest.yml`
  before deletion; if referenced, KEEP path is the survival path
  (per master spec D-122-26).

## Acceptance

See source spec. Summary:
- `wc -c scripts/sync_command_mirrors.py` ≤ 2,000 (shim only)
- `find scripts/sync_mirrors -name '*.py' | wc -l` ≥ 7
- `find . -name '.DS_Store' -not -path './.git/*'` → empty
- `grep -rn '/ai-implement' --include='*.md'` → empty
- `tests/unit/docs/test_skill_references_exist.py` passes
- `tests/unit/hooks/test_canonical_events_count.py` passes
- `tests/unit/hooks/test_hot_path_slo.py` passes (p95 < 1s)
- `grep '\[Unreleased\]' CHANGELOG.md` shows entries for a/b/c/d
- `cat docs/cli-reference.md | grep 'ai-eng audit retention'` matches
- `tests/unit/skills/test_spec_path_canonical.py` passes (no `specs/spec.md` in skills)
