---
title: "Global Hook Surface Resilience — Hooks Must Not Crash in Uninitialized Repos"
status: draft
audience: framework-dev
branch: feat/global-hook-surface-resilience
length_estimate: M
authoring_style: brief
principles_required: ["§10.1", "§10.8"]
delivery_mode: standard
mantra: "A global hook surface degrades; it never exit-127s."
---

# Global Hook Surface Resilience — Hooks Must Not Crash in Uninitialized Repos

> Sibling brief to `global-install-work-plane-brief.md`. That brief fixes
> work-plane resolution (where specs/state live). THIS brief fixes the IDE hook
> surface so a global install does not crash Claude Code in repos that have no
> local `.ai-engineering/`. A strategy judge-panel found this is the real
> "global install doesn't work" symptom — distinct from the work-plane
> collision, and worse, because it fires on every hook event.

## 1. Vision

After a global install, opening Claude Code in ANY directory — initialized or
not — produces zero hook crashes. Hooks that need a local `.ai-engineering/`
degrade cleanly (no-op or resolve against the global brain) instead of failing
with `exit 127`. The IDE surface (skills, agents, hooks) is usable machine-wide;
the absence of a per-repo work-plane is a quiet, recoverable state, not a fatal
one.

## 2. Scope Boundary

**In scope**

- The global `~/.claude/settings.json` hook wiring and the
  `.claude/hooks -> .ai-engineering/scripts/hooks` symlink contract.
- The hook bootstrap path (`run-hook.sh`) tolerating an absent
  `.ai-engineering/` tree (resolve against the global brain, or no-op).
- A definition of "the brain hook tree" location that exists machine-wide.

**Explicitly NOT in scope**

- Work-plane / specs / state resolution — owned by
  `global-install-work-plane-brief.md`.
- Skill/agent markdown Step-0 degradation (LLM instructions, not executable
  crashes) — tracked as a follow-up note, not a code fix.

## 3. Diagnostic Snapshot

The IDE surface structurally HARD-DEPENDS on a co-located `.ai-engineering/`
tree; a global `~/.claude` cannot stand alone.

- `.claude/hooks` is a symlink to `../.ai-engineering/scripts/hooks`
  (`.claude/hooks`). When `.ai-engineering/` is absent the target is dead and
  every hook lookup through it fails at the OS level before any Python runs.
- The global `~/.claude/settings.json` wires 20 hook commands as
  `bash "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh"
  "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<name>.py"` with no
  fallback and no `continueOnError`. In a repo without `.ai-engineering/`,
  `$CLAUDE_PROJECT_DIR` resolves to that repo, the script path does not exist,
  and `bash` exits 127 on every event (SessionStart, UserPromptSubmit,
  PreToolUse, PostToolUse, Stop, SubagentStop, Notification, SessionEnd,
  PreCompact, PostCompact).
- `run-hook.sh` has a `_resolve_root()` walk-up
  (`.ai-engineering/scripts/hooks/_lib/run-hook.sh:23`), but it is unreachable:
  `bash` cannot open `run-hook.sh` itself when `.ai-engineering/` is missing, so
  the fallback never executes.
- Once a hook DOES run, the inner layer is already resilient: integrity
  pass-opens when the manifest is absent
  (`.ai-engineering/scripts/hooks/_lib/integrity.py:88`), and emitters
  auto-create `state/` with `mkdir(parents=True, exist_ok=True)`
  (`.ai-engineering/scripts/hooks/_lib/hook-common.py:224`). The defect is
  purely the boot path: reaching `run-hook.sh` at all.

## 4. Architecture

The fix lives at the wiring + boot boundary, not inside the hooks.

1. **Brain hook tree has a machine-wide home.** Under a global install, the hook
   scripts live at `~/.ai-engineering/scripts/hooks/` (already true). The wiring
   must point hooks at a tree that exists regardless of cwd.
2. **Resolve the hook tree with a fallback chain** in the wiring (or a tiny
   stable shim): prefer `$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/` when
   present, else `$HOME/.ai-engineering/scripts/hooks/` (the global brain), else
   no-op exit 0. A missing local tree degrades to the global brain; a missing
   global brain degrades to a clean no-op — never `exit 127`.
3. **Guard the runner.** The `bash` entry must test the script path and exit 0
   (not 127) when absent, so a malformed environment never propagates a failure
   into the IDE. `continueOnError`-equivalent behavior by construction.
4. **Symlink contract.** Either keep `.claude/hooks` pointing at the resolved
   brain tree, or stop relying on the symlink for the global surface and let the
   wiring resolve the path directly.

## 5. Evidence Catalog

| Claim | Evidence |
|-------|----------|
| Dead symlink when brain absent | `.claude/hooks` -> `../.ai-engineering/scripts/hooks` |
| 20 hook commands hard-code the local path | `~/.claude/settings.json` (hook block) |
| Project settings carry the same wiring | `.claude/settings.json` (hook block) |
| Unreachable walk-up fallback | `.ai-engineering/scripts/hooks/_lib/run-hook.sh:23` |
| Integrity pass-opens on missing manifest | `.ai-engineering/scripts/hooks/_lib/integrity.py:88` |
| Emitters self-create state dir | `.ai-engineering/scripts/hooks/_lib/hook-common.py:224` |

## 6. Roadmap

- **M1 — Runner guard.** `run-hook.sh` invocation tests the target and exits 0
  when absent. Gate: a synthetic repo with no `.ai-engineering/` produces zero
  non-zero hook exits across all 11 events.
- **M2 — Brain fallback in wiring.** Hook path resolves
  project-local -> global-brain -> no-op. Gate: hooks fire from the global brain
  in an uninitialized repo; integrity still pass-opens.
- **M3 — Symlink/contract cleanup.** Resolve or retire the `.claude/hooks`
  symlink for the global surface. Gate: no dead-symlink lookups.

## 7. Definition of Done

- Opening Claude Code in a repo with no `.ai-engineering/` (global install
  present) yields zero hook crashes across all 11 events.
- Hooks needing the brain resolve it from `$HOME/.ai-engineering`; with no brain
  at all, hooks no-op exit 0.
- Hot-path budget unchanged (`<1s` session-start / per-hook): the fallback is
  one path test, no walk-up on the common path.

## 8. Quality Stamps

- **§10.1 KISS** — fix at the wiring boundary; do not rewrite the hooks.
- **§10.8 Hexagonal** — the hook runner is the port; its inputs (script path,
  brain root) are resolved once and injected.
- Contracts honored: hot-path SLOs; D-112-04 (hooks stay stdlib-only — this
  brief touches wiring, not hook bodies).

## 9. Open Decisions

1. Resolve the hook tree in the `bash` command string vs a tiny committed shim
   that does the project->global->noop resolution.
2. Whether the global `~/.claude/settings.json` should reference
   `$HOME/.ai-engineering` directly (decoupling from `$CLAUDE_PROJECT_DIR`) or
   keep `$CLAUDE_PROJECT_DIR` with a fallback.
3. Whether to keep `.claude/hooks` as a symlink at all for the global surface.
4. Behavior when the global brain's hook bytes fail the integrity pin in a
   foreign repo (pass-open vs no-op).

## 10. Migration

No data migration. Wiring change only; documented in CHANGELOG. The
`~/.claude/settings.json` hook block is regenerated by the installer, so the
fix ships through a reinstall/update with no shim (CONSTITUTION.md §3).

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fallback to global brain runs stale hook bytes in a foreign repo | Medium | Medium | integrity pin pass-opens or no-ops; document precedence |
| Silencing exit 127 hides a genuinely broken local install | Low | Medium | doctor surfaces "hooks resolving from global brain, no local tree" advisory |
| Path-test guard adds hot-path cost | Low | Low | single `test -f`; no walk-up on the common path |
| `$CLAUDE_PROJECT_DIR` unset in some IDE contexts | Medium | Medium | default to `$HOME/.ai-engineering` brain when the env var is empty |

## 12. References

- Claude Code hooks + settings.json wiring: docs.claude.com/claude-code (hooks).
- git hooks core.hooksPath (global vs per-repo hook resolution):
  git-scm.com/docs/githooks.
- pre-commit global hook env vs per-repo install: pre-commit.com.

## 13. Glossary

- **Brain hook tree** — `~/.ai-engineering/scripts/hooks/`, the machine-wide hook
  scripts a global install lays down.
- **Boot path** — getting `bash` to open `run-hook.sh` at all; the defect is
  here, before any Python or integrity check.
- **Degrade** — resolve against the global brain, or no-op exit 0 — never
  `exit 127`.

## 14. Acceptance

- [ ] Zero non-zero hook exits in an uninitialized repo (global install present),
      all 11 events.
- [ ] Hooks resolve the brain tree project-local -> `$HOME` -> no-op.
- [ ] Dead `.claude/hooks` symlink no longer causes a lookup failure.
- [ ] Hot-path SLO unchanged; runner guard is one path test.
- [ ] Installer regenerates the corrected `~/.claude/settings.json` wiring;
      CHANGELOG entry; no shim.
