---
id: spec-064
title: "Install Flow Redesign: Guided Wizard + Template Parity + Phase Pipeline"
status: draft
created: 2026-03-24
refs: []
---

# spec-064: Install Flow Redesign

## Problem

The `ai-eng install` flow has three categories of defects that prevent it from being production-ready:

1. **Template drift**: The template ships a fraction of the hook scripts that the live dogfooding project uses. The `.claude/settings.json` template has 3 hook groups; live has 7. Downstream installations get a skeleton, not the framework. The full Python hook library, Copilot hook set, and advanced hooks (prompt-injection-guard, auto-format, cost-tracker, instinct-extract, observe, mcp-health, strategic-compact) are missing from the template.

2. **Bugs**: `vcs_provider` is never passed to `copy_project_templates()` — GitHub templates (CODEOWNERS, dependabot.yml, PR template) are never copied. Stacks and IDEs are not interactively prompted (silent defaults to `["python"]`/`["terminal"]`). A dead path exists at `project/.ai-engineering/`. A naming inconsistency (`context/` singular vs `contexts/` plural) prevents 2 product contract files from materializing.

3. **UX gaps**: No step-by-step explanations. No progress indicators. No re-install detection. No robust update path for existing installations. Auto-tool-install hidden behind undiscoverable env var. Branch policy checks hardcoded. A user cannot tell what happened or what to do next.

The install is the framework's front door. If it doesn't work flawlessly, nothing else matters.

## Solution

Redesign `ai-eng install` as a **composable phase pipeline** with a **guided wizard UX**:

- **6 phases**, each an independent module: detect, governance, ide-config, hooks, state, tools
- Each phase exposes `plan()` -> `execute()` -> `verify()` — the wizard orchestrates them
- **Dry-run transversal**: every phase produces a serializable plan (JSON) that can be shown in the wizard, exported for CI (`--dry-run`), or imported for reproducibility (`--plan`)
- **Template parity**: close ALL gaps between template and live dogfooding (hooks, settings.json, instructions, product contracts)
- **Intelligent merge**: `settings.json` merge adds missing hooks without overwriting user customizations
- **Re-install detection**: when installation exists, offer 4 options (fresh/repair/reconfigure/cancel)
- **Update flow**: `ai-eng update` always runs dry-run first, shows diff, user applies with `--apply`. Overwrites framework-owned files; preserves team and system ownership. Migrates the existing `updater/service.py` to use the phase pipeline
- **Auto-detection**: VCS provider, auth status, installed tools — detected automatically, confirmed by user
- **Rich progress UI**: numbered steps with spinner, checkmarks, warnings, and a summary panel with next actions. Falls back to plain text if `rich` is unavailable
- **Non-atomic pipeline**: each phase is independent and idempotent. If a phase fails, subsequent phases are skipped. Repair mode fills the gaps

## Scope

### In Scope

**A) Template Parity (close all gaps)**

1. Add ALL hook scripts from `scripts/hooks/` to `templates/project/scripts/hooks/` — the template count MUST match the live count exactly (verified at implementation time via `find scripts/hooks -type f -not -path '*__pycache__*' | wc -l`). No hardcoded counts.
2. Update `templates/project/.claude/settings.json` to match the full live hook configuration (all hook groups, all Python script references)
3. Fix `context/` -> `contexts/` naming inconsistency: rename template path, add migration step for existing installations that have `context/product/` on disk (move contents to `contexts/product/`, remove empty `context/` tree), update all internal references in template files
4. Remove dead path `templates/project/.ai-engineering/`
5. Verify `.github/instructions/*.instructions.md` files are deployed when `github_copilot` is a provider (template count MUST match `find templates/project/instructions -type f | wc -l`)

**B) Bug Fixes**

6. Pass `vcs_provider` to `copy_project_templates()` in `service.py` — wire `_VCS_TEMPLATE_TREES`
7. Add interactive prompts for stacks and IDEs when flags are absent
8. Fix `already_installed` detection — use `install-manifest.json` existence as authoritative signal, not heuristic

**C) Phase Pipeline Architecture**

9. Create `installer/phases/` package with 6 phase modules:
   - `detect.py` — auto-detect VCS (git remote), providers (existing files), tools (which/where), auth status. Detect and migrate legacy paths (`context/` -> `contexts/`)
   - `governance.py` — copy `.ai-engineering/` tree (exclude team + system ownership)
   - `ide_config.py` — copy IDE-specific files based on detected/selected providers
   - `hooks.py` — copy hook scripts + install git hooks + merge settings.json
   - `state.py` — generate/update state files (manifest, ownership, decisions)
   - `tools.py` — verify/install required tools, check auth, apply branch policy
10. Each phase implements `PhaseProtocol`: `plan(context) -> PhasePlan`, `execute(plan) -> PhaseResult`, `verify(result) -> PhaseVerdict`
11. `PhasePlan` is JSON-serializable: list of actions with type (create/overwrite/merge/skip), source, destination, rationale. All destination paths MUST be relative to the target root. Absolute paths and path traversal (`../`) MUST be rejected.
12. Refactor `installer/service.py` to orchestrate phases via the pipeline, not inline logic
13. Extract template map resolution into a public function (e.g., `resolve_template_maps()`) that both the installer phases and updater consume. Remove direct imports of `_PROJECT_TEMPLATE_MAP` and `_PROJECT_TEMPLATE_TREES` from `updater/service.py`.

**D) Wizard UX**

14. Numbered step progress UI with `rich`: `[1/6] Phase Name    Description...    checkmark N files`. Static description per phase (hardcoded). If `rich` is unavailable, fall back to plain text with no spinners.
15. Auto-detection phase at start: detect VCS, providers, tools, auth — show what was detected, confirm with user. Wizard MUST ask at most 3 interactive questions in the default flow (providers, VCS, stacks). All other values are auto-detected. Total questions including re-install option MUST NOT exceed 5.
16. Undetectable config delegated to `ai-eng setup <platform>` with clear guidance in summary
17. Summary panel at end: files created, hooks installed, warnings, pending setup commands, next steps
18. Re-install detection: check `install-manifest.json` -> offer 4 options:
    - `fresh` — overwrite all framework-owned files, regenerate `install-manifest.json` and `ownership-map.json`, preserve team-owned files (`contexts/team/**`) and append-only files (`state/audit-log.ndjson`, `state/decision-store.json`)
    - `repair` — fill missing files without overwriting existing
    - `reconfigure` — re-run wizard to change providers/VCS/stacks. Adding a provider adds its files. Removing a provider removes its files (using existing `remove_provider_templates` logic). Shared files (e.g., `AGENTS.md`) preserved if any active provider still requires them. `install-manifest.json` updated to reflect new configuration.
    - `cancel` — exit without changes

**E) Update Flow**

19. Migrate `updater/service.py` to use the phase pipeline. The existing backup/rollback, ownership-checking, and audit-logging logic MUST be preserved or replicated in the new architecture. `updater/service.py` is retired — its public functions are replaced by the pipeline orchestrator.
20. `ai-eng update` always executes dry-run first: compare template vs installed, show diff (new/changed/removed)
21. `ai-eng update --apply` executes the plan: overwrite framework-owned, preserve team + system
22. Ownership boundaries enforced via `ownership-map.json`: framework files overwritten; team-owned files (`contexts/team/**`) and append-only state files (`audit-log.ndjson`, `decision-store.json`) never touched. `install-manifest.json` and `ownership-map.json` are regenerated (they are framework infrastructure).
23. Maintain existing CLI interface: `ai-eng update` shows diff, `ai-eng update --apply` writes. Internal implementation changes are transparent to callers.

**F) settings.json Intelligent Merge**

24. Merge strategy: parse source and destination as JSON, merge hook arrays (add missing hooks, preserve user-added hooks), merge permission arrays (add missing deny rules, preserve user-added rules), preserve user-added top-level keys
25. Conflict detection: if a hook with the same matcher exists in both, preserve destination version (user wins)
26. Define a minimal structural schema for `.claude/settings.json` covering `permissions`, `hooks`, and expected top-level keys. Validate both source template and merged output against this schema.
27. Malformed destination file: fall back to template copy with warning (do not fail the install)

**G) Dry-Run / CI Support**

28. `ai-eng install --dry-run` outputs the full plan as JSON to stdout (no files touched)
29. `ai-eng install --plan plan.json` replays a saved plan (reproducible installs). Plan validation: all destination paths MUST be relative to the target root. Absolute paths and path traversal (`../`) MUST be rejected. Plans MUST include a `schema_version` field; mismatched versions MUST be rejected. Plans MUST NOT execute arbitrary commands — only file operations (create/overwrite/merge/skip).
30. `--non-interactive` mode uses auto-detected values + defaults (no prompts, no confirmation)

**H) Testing**

31. Unit tests per phase: `plan()`, `execute()`, `verify()` tested in isolation with fixture directories
32. Integration test matrix: single-provider combinations (claude_code, github_copilot, gemini, codex) x (github, azure_devops) = 8 combinations PLUS at least 2 multi-provider combinations: `[claude_code, github_copilot]` x github and `[claude_code, gemini]` x github. Minimum 10 combinations.
33. Update/merge tests: verify framework files overwritten, team/system preserved, settings.json merged correctly
34. Re-install scenario tests: fresh/repair/reconfigure paths (including provider addition and removal in reconfigure)
35. Backward-compatibility test: existing `update_cmd` invocation patterns produce equivalent results before and after migration
36. Update `install-smoke.yml` CI workflow to cover new wizard with `--non-interactive`
37. On Windows CI, installed `.ps1` hook scripts MUST be validated as syntactically valid PowerShell
38. Phase failure resilience test: if the hooks phase fails (e.g., git not initialized), all preceding phases complete successfully, the summary shows the failure, and a subsequent repair install completes the hooks phase

### Out of Scope

- New skills or agents (no new SKILL.md or agent files)
- Changes to hook script behavior (only adding them to template — the scripts themselves are unchanged)
- CI pipeline changes beyond install-smoke.yml updates
- `ai-eng setup` improvements (existing commands remain as-is)
- Manifest schema changes (manifest.yml structure stays the same)
- CLI help text/docs rewrite (only install-related command help)
- New rollback design — the existing `updater/service.py` backup/rollback mechanism is preserved as-is

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Phase pipeline with plan/execute/verify protocol | Enables isolated testing, reuse between install/update/repair, and dry-run serialization |
| D2 | All hooks in template as standard (count verified dynamically) | The hooks ARE the framework value. Shipping a skeleton undermines the product. Dynamic count verification prevents spec-to-code drift |
| D3 | settings.json merge (user wins on conflicts) | Users customize permissions; framework adds hooks. Merge preserves both. User-modified hooks are treated as intentional |
| D4 | Auto-detect + confirm, max 3 questions in default flow | Detect VCS from remote, tools from PATH, auth from CLI status. Only ask what cannot be inferred. Bounded question count prevents wizard fatigue |
| D5 | Ownership-based overwrite boundaries with granular state handling | `framework` = overwritable. `team` (`contexts/team/**`) = protected. State files split: `install-manifest.json` + `ownership-map.json` = regenerated; `audit-log.ndjson` + `decision-store.json` = append-only, never overwritten |
| D6 | Dry-run as serializable JSON plan with security validation | CI can validate install plans without side effects. Path traversal and absolute paths rejected. Plans are versioned and command-free |
| D7 | `install-manifest.json` as authoritative install signal | Replaces fragile heuristic. If manifest exists, installation is present. Version field enables upgrade detection |
| D8 | Re-install offers 4 explicit options (fresh/repair/reconfigure/cancel) | "fresh" covers upgrades and resets. "repair" fills gaps without risk. "reconfigure" adapts to changed needs (add/remove providers). "cancel" is always safe |
| D9 | Update = mandatory dry-run before apply | Prevents surprise overwrites. User sees exactly what will change before committing |
| D10 | Delegate undetectable config to `ai-eng setup` | Install is files + hooks. Platform credentials, tokens, and branch policy are `setup` territory. Clear boundary |
| D11 | Phase pipeline is NOT atomic — idempotent and recoverable | Each phase is independent. If a phase fails, subsequent phases are skipped. Summary reports which phases succeeded/failed. Repair mode fills gaps. Partial installation is recoverable, not catastrophic |
| D12 | Public template map API replaces private imports | Both installer phases and updater consume `resolve_template_maps()`. Eliminates coupling to private `_PROVIDER_*` variables. Single source of truth for what gets installed |

## Acceptance Criteria

### Template Parity
- [ ] AC1: `ai-eng install` in a clean repo creates ALL files matching the live dogfooding project. Template hook count MUST equal `find scripts/hooks -type f -not -path '*__pycache__*' | wc -l`.
- [ ] AC2: `ai-eng install --provider claude copilot` creates both Claude Code and GitHub Copilot files; `--provider gemini` creates only Gemini files
- [ ] AC3: `ai-eng install` with GitHub remote auto-detects VCS=github and copies CODEOWNERS, dependabot.yml, PR template
- [ ] AC4: `ai-eng install` with Azure DevOps remote auto-detects VCS=azure_devops and skips GitHub-specific templates
- [ ] AC5: When provider includes `github_copilot`, instruction files are deployed to `.github/instructions/`. Count MUST match template source.

### Re-install
- [ ] AC6: Re-running `ai-eng install` on an existing installation shows 4 options (fresh/repair/reconfigure/cancel)
- [ ] AC7: "fresh" overwrites all files where `ownership-map.json` classifies ownership as `framework`. `install-manifest.json` and `ownership-map.json` are regenerated. `contexts/team/**` and append-only state files (`audit-log.ndjson`, `decision-store.json`) are preserved.
- [ ] AC8: "repair" creates only missing files, overwrites nothing
- [ ] AC9: "reconfigure" from `[claude_code]` to `[claude_code, github_copilot]` adds all Copilot files. From `[claude_code, github_copilot]` to `[claude_code]` removes Copilot files. Shared files preserved if any active provider requires them. `install-manifest.json` updated.

### settings.json Merge
- [ ] AC10: Merge adds missing hooks from template without removing user-added hooks
- [ ] AC11: Merge adds missing deny rules from template without removing user-added permission rules
- [ ] AC12: User-added top-level keys in destination are preserved after merge
- [ ] AC13: Malformed destination settings.json falls back to template copy with warning

### Dry-Run / CI
- [ ] AC14: `ai-eng install --dry-run` outputs a JSON plan to stdout and creates zero files
- [ ] AC15: `ai-eng install --plan plan.json` reproduces the exact same file operations as the original install
- [ ] AC16: `ai-eng install --plan` with a plan containing `../../../etc/passwd` as a destination MUST fail with a path traversal error
- [ ] AC17: Plan JSON MUST include `schema_version`; mismatched versions MUST be rejected

### Update Flow
- [ ] AC18: `ai-eng update` shows dry-run diff; `ai-eng update --apply` executes it respecting ownership boundaries
- [ ] AC19: Existing `ai-eng update` invocation patterns produce equivalent results after migration (backward compatibility)

### Wizard UX
- [ ] AC20: Install progress shows numbered steps `[N/6]` with static description per phase, spinner during execution, and checkmark or warning icon on completion
- [ ] AC21: Summary panel shows: files created, hooks installed, warnings, pending `ai-eng setup` commands, and ordered next steps
- [ ] AC22: `--non-interactive` mode completes without prompts using auto-detected values + defaults
- [ ] AC23: Wizard asks at most 3 questions in default flow (providers, VCS, stacks). Total including re-install option MUST NOT exceed 5.
- [ ] AC24: If `rich` is unavailable, wizard falls back to plain text output with no spinners

### Migration / Cleanup
- [ ] AC25: Dead template path `templates/project/.ai-engineering/` is removed
- [ ] AC26: `context/product/` renamed to `contexts/product/`. Existing installations with `context/product/` are migrated during install repair or update.

### Testing
- [ ] AC27: Each phase (detect, governance, ide_config, hooks, state, tools) has independent unit tests with fixture directories
- [ ] AC28: Integration test matrix: 8 single-provider + 2 multi-provider combinations = minimum 10 combinations verified
- [ ] AC29: Re-install scenario tests cover fresh/repair/reconfigure paths including provider add/remove
- [ ] AC30: `install-smoke.yml` CI passes on ubuntu, macos, and windows with `--non-interactive`
- [ ] AC31: On Windows, `.ps1` hook scripts are validated as syntactically valid PowerShell
- [ ] AC32: Phase failure resilience: hooks phase failure does not prevent preceding phases from completing; subsequent repair completes the failed phase
- [ ] AC33: Test coverage for `installer/` package >= 80%

## Assumptions

- ASSUMPTION: The hook scripts in the live project are stable and ready for distribution (no pending refactors beyond spec-063)
- ASSUMPTION: The ownership map in manifest.yml correctly classifies all framework vs team vs system files
- ASSUMPTION: `--non-interactive` mode is sufficient for CI — no special CI-only flags needed

## Risks

| Risk | Mitigation |
|------|-----------|
| settings.json merge produces invalid JSON | Validate merged output against structural schema before writing; on validation failure, fall back to template copy with warning |
| Fresh install overwrites user customizations in framework-owned files | Ownership map is the contract: framework-owned = overwritable by design. Summary panel warns before executing. Cancel option always available |
| Phase pipeline adds abstraction without proportional value | Each phase is independently testable and reusable across install/update/repair — the abstraction pays for itself in test coverage and DRY |
| Dry-run plan becomes a security surface (path traversal) | All plan paths MUST be relative. Absolute paths and `../` rejected. Plans contain only file operations, never commands. Schema versioned |
| Hook script paths in settings.json break on different OS | Use relative paths from project root. Validate paths in verify() phase |
| `ai-eng update` has existing users — changing behavior is breaking | Maintain existing CLI interface exactly. `ai-eng update` shows diff, `--apply` writes. Internal changes are transparent. Backward-compatibility test enforced |
| No published schema for `.claude/settings.json` | Derive minimal structural schema from observed structure. Maintain manually. Schema validates structure, not semantics |
| Partial installation on phase failure | Pipeline is non-atomic by design. Each phase is idempotent. Summary reports failures. Repair mode fills gaps. Documented in D11 |

## Dependencies

- spec-063 (Observability & Integrity Remediation) MUST land first — it fixes hook scripts that this spec will template-ize
- Existing `installer/templates.py` provider maps are the foundation — this spec refactors but does not replace the routing logic
- `hooks/manager.py` git hook generation is unchanged — this spec only adds scripts to the template, not new git hook types
- `updater/service.py` backup/rollback mechanism is preserved and migrated to the phase pipeline
