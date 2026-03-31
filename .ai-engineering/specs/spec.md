---
spec: spec-095
title: "ai-eng install: auto-infer mode, single tree UX"
status: done
effort: medium
---

# Spec 095 — ai-eng install: auto-infer mode, single tree UX

## Summary

`ai-eng install` on an existing installation presents 4 options (fresh/repair/reconfigure/cancel) that the user must choose between without understanding the internal file-write semantics. After choosing, the same 4-step wizard always runs regardless of mode. The UX is confusing, redundant, and violates the principle of not asking users to make decisions the system can infer. The tree display in `ai-eng update` compounds this by rendering multiple separate trees (one per outcome bucket) with verbose 3-line metadata per file, including unchanged files.

## Goals

- [ ] Remove the 4-option menu (`render_reinstall_options`) from reinstall flow
- [ ] Auto-infer the minimal correct action: detect missing files (→ create), outdated files (→ update), removed providers (→ clean up), unchanged files (→ skip)
- [ ] Show a single grouped mini-tree with per-file state before confirmation:
  ```
  .claude/
  ├── skills/ai-start/SKILL.md       new
  └── skills/ai-guide/SKILL.md       updated
  .ai-engineering/
  └── contexts/stack.md              updated
  .github/                           removed (provider disabled)
  ```
- [ ] Confirm with `Proceed? [Y/n]` — no mode selection needed
- [ ] After apply: show a post-tree ONLY with failures (if any). If all ok, one-liner: "Done. 3 created, 2 updated, 1 removed."
- [ ] `--fresh` flag: show same mini-tree with all files as `overwrite`, require typed confirmation "Type 'fresh' to confirm:"
- [ ] `--reconfigure` flag: launch wizard, then show mini-tree with diff (new files from added providers, removed files from dropped providers), confirm before applying
- [ ] First install (no `.ai-engineering/`): keep current flow — autodetect + wizard + tree + confirm
- [ ] Wizard ONLY runs on: first install OR `--reconfigure`. Never on default reinstall.
- [ ] Read manifest.yml to determine current config (providers, stacks, IDEs) instead of re-asking
- [ ] Eliminate double-render in interactive mode (preview tree + result tree → preview tree + one-liner/failure-only tree)
- [ ] Update tree displays a single unified view grouped by directory with per-file state color indicators

## Non-Goals

- Changing the 6-phase install pipeline internals (governance, ide_config, state, hooks, tools phases stay as-is)
- Modifying InstallMode enum semantics (the modes still exist internally, just auto-selected)
- Redesigning the wizard itself (prompts, autodetect logic)
- Fixing validate/verify manifest.yml compliance (spec-C, separate)
- Maturing superficial verify checks (spec-D, separate)
- Changing `ai-eng update` logic beyond tree display (the update diffing engine stays)

## Decisions

**D-095-01**: Eliminate explicit mode selection menu; auto-infer from filesystem state.
*Rationale*: Users shouldn't need to understand file-write semantics (overwrite vs create-only vs delete-removed). The system knows what's missing, outdated, and orphaned — it should act on that knowledge. `brew upgrade`, `apt upgrade`, `rustup update` all follow this pattern.

**D-095-02**: `--fresh` as explicit flag, not menu option.
*Rationale*: Fresh is destructive and rare. Destructive operations should require intentional invocation (`--fresh`) and explicit typed confirmation, not a menu pick that's one keystroke from a non-destructive option.

**D-095-03**: `--reconfigure` as explicit flag that triggers the wizard.
*Rationale*: Changing providers/stacks is a deliberate config change, not the default reinstall intent. Separating it into a flag makes the default path zero-decision while preserving full control. The wizard runs ONLY here and on first install.

**D-095-04**: Single unified tree grouped by directory with per-file state colors.
*Rationale*: Multiple trees per outcome bucket fragment the user's mental model. One tree with inline state indicators (new/updated/removed/unchanged/overwrite) gives a complete picture at a glance. Colors: green=new/created, yellow=updated, red=removed, dim/gray=unchanged, bold red=overwrite (--fresh).

**D-095-05**: Post-apply output: failures-only tree or one-liner.
*Rationale*: After confirmation, the user already saw the preview tree. Repeating it with "applied" labels is noise. Show only what went wrong (failure tree) or confirm success in one line.

**D-095-06**: First install keeps current autodetect + wizard flow.
*Rationale*: No manifest.yml exists yet, so auto-infer has nothing to read. Autodetect provides sensible defaults, wizard lets the user confirm/adjust, then tree shows what will be created. This flow works well already.

**D-095-07**: `--reconfigure` shows diff-tree (added + removed) before applying.
*Rationale*: Provider/stack changes can delete files (e.g., switching from .claude to .codex removes all .claude/ skill mirrors). The user must see what will be removed before confirming. The tree shows both additions (green) and removals (red).

## Risks

**R1: Auto-infer misclassifies a file state (e.g., marks a user-modified file as "outdated").**
*Mitigation*: Classification uses the existing ownership map (`state/ownership-map.json`) and content hashing. Team-owned files (`contexts/team/`) are never touched. Framework-managed files compare against template hashes. This logic already works in the pipeline phases — we're just surfacing it in the tree.

**R2: `--fresh` typed confirmation is friction.**
*Mitigation*: Intentional. `--fresh` is the nuclear option. The friction IS the feature. Users who need it know they need it.

**R3: Mini-tree is noisy for projects with 200+ framework files.**
*Mitigation*: Default reinstall only shows files with changes (new/updated/removed). Unchanged files are counted but not listed: "14 files unchanged" as a footer line. `--fresh` shows all files since all will be overwritten — but that's the point.

**R4: Removing the mode menu breaks `--non-interactive` scripts that pass a mode.**
*Mitigation*: `--non-interactive` already skips the menu. The default behavior (auto-infer) is what non-interactive callers want. `--fresh` and `--reconfigure` flags work in non-interactive mode without a menu.

