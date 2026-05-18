---
spec: spec-142
slug: surface-aware-dashboard
title: Surface-aware /ai-start dashboard header — render correctly on all 7 surfaces
status: approved
effort: medium
summary: Rework `session_bootstrap.py` so the `/ai-start` header renders project name, skill/agent counts, and hooks status correctly on every supported surface (claude-code, codex, gemini-cli, github-copilot, opencode, cursor, antigravity), and make `ai-eng install` generate `hooks-manifest.json` so fresh installs are not stuck in `hooks: unknown`.
branch: claude/review-spec-drafts-DX2pD
source_brief: ""
target_dispatch: /ai-plan
chains_after: spec-141
---

## Summary

The `/ai-start` dashboard is the first artifact every operator sees on a
new session. Today it renders three incorrect fields in any install whose
surface is not `claude-code` (e.g. `/Users/soydachi/repos/test/`, surface
`github-copilot`):

1. **`(unnamed)`** instead of the project name — the script reads
   `.ai-engineering/manifest.yml` with `yaml.safe_load`, but a fresh
   install with no `pyproject.toml` has no `pyyaml` in the venv. The
   recently-landed defensive `import yaml` (this branch) makes the script
   *run*, but the name still cannot be resolved.
2. **`0 skills, 0 agents`** even though 18 skills live under
   `.github/skills/` and N agents under `.github/agents/`. Cause:
   `_count_skills` and `_count_agents` in `session_bootstrap.py` hard-code
   `.claude/skills/` and `.claude/agents/` and never consult
   `surfaces.enabled` from the manifest. The framework already has the
   canonical surface→path map in
   `src/ai_engineering/config/mirror_inventory.py` (`_PROVIDER_TREE_MAPS`),
   but that module is part of the pip package and cannot be imported by
   a stdlib-only script.
3. **`hooks: unknown`** because `.ai-engineering/state/hooks-manifest.json`
   does not exist. Root cause is an installer gap, not a surface mismatch:
   the framework documents `regenerate-hooks-manifest.py` as a manual
   one-shot (`CONSTITUTION.md` template line 153,
   `doctor/phases/scripts.py:24`) and `ai-eng install` never invokes it.
   Every fresh install of every surface starts with `hooks: unknown` until
   the operator runs the script by hand.

The dashboard is the canonical cross-IDE contract (per `ai-start/SKILL.md`
line 45-47, the same bytes render in Claude Code, Codex, Gemini CLI,
Copilot). Today it is a Claude-Code-only artifact masquerading as a
cross-IDE one.

## Goals

1. `session_bootstrap.py` reads the project name from `manifest.yml`
   without requiring `pyyaml` to be installed — a stdlib mini-parser
   covers the two fields the dashboard actually needs (`name`,
   `surfaces.enabled`). When `pyyaml` *is* available it remains the
   preferred path; the mini-parser is only the fallback.
2. `_count_skills` and `_count_agents` dispatch on the primary surface
   from `surfaces.enabled[0]`, mapping to the correct directory for each
   of the 7 supported surfaces. For the test repo the count rises from
   `0/0` to the real `.github/skills/` and `.github/agents/` totals.
3. `_hooks_health` reports an actionable state in every install:
   `ok`, `drift(N)`, or `unverified — run regenerate-hooks-manifest`
   (when scripts exist on disk but the manifest is missing). `unknown`
   is reserved for the genuinely-unreadable case (manifest exists but
   is corrupt).
4. `ai-eng install` (and any subcommand that finalizes an install)
   invokes `regenerate-hooks-manifest.py` as a final step so every new
   project leaves the installer with `hooks: ok` on first `/ai-start`.
5. Schema-version 1 of the JSON output stays additive — every new field
   is optional, every renamed field keeps its old name as an alias for
   one release. Existing IDE renderers (Claude Code, Codex, Gemini,
   Copilot) parse the new payload without modification.
6. Wall-clock budget stays under 3 s cold-path (per the existing
   docstring). The mini-parser path is ~5 ms; the installer hook step
   runs ~50 ms at install time and is not on the dashboard hot path.

## Non-Goals

- No rewrite of the rest of the markdown dashboard (Active Work, Recent,
  Recent Lessons, Board, footer). Only the header (lines ~797-840 of
  `session_bootstrap.py`) is in scope.
- No change to the `pyyaml` dependency contract of *other* scripts. The
  recently-landed defensive `import yaml` in `markdown_render.py` and
  `manifest_reader.py` stays — those raise typed errors as before.
- No change to the `uv run python …` invocation form in
  `ai-start/SKILL.md` line 30. PEP 723 inline metadata is rejected
  because it would require updating `hooks-manifest.json` `trustedArgvs`
  (D-131-12) for every surface mirror.
- No new external dependency. The mini-parser is regex + string-contains;
  `session_bootstrap.py` remains stdlib-only.
- No general health-check across surface mirrors (parity, drift
  detection). That belongs in a separate `ai-eng doctor` spec.
- No fix for `(no commits)` in the `Recent` section when the repo has
  zero commits — accurate today, low-value to dress up.
- No rename of `events 7d: N` or `N pending review` strings. They are
  technically correct; UX clarity is a future spec.

## Decisions

**D-142-01 — stdlib mini-parser for `manifest.yml`, gated by pyyaml
fallback.** When `pyyaml` is importable, `_read_yaml` keeps using
`yaml.safe_load` for the full manifest. When `pyyaml` is *not*
importable, `session_bootstrap.py` calls a new internal function
`_read_manifest_minimal(path) -> dict` that scans the file with a small
regex set to extract `name: <string>` and `surfaces.enabled: [<list>]`
only. Rationale: keeps the script stdlib-only, restores the two
header-critical fields in every install, and accepts the maintenance
burden of a 2-field parser (≤ 30 LOC). The mini-parser is intentionally
narrow — adding new fields to it is an explicit cost, which is the
right pressure to keep the dashboard surface lean.

**D-142-02 — surface→path map inlined in `session_bootstrap.py`.** The
canonical map `_PROVIDER_TREE_MAPS` lives in
`src/ai_engineering/config/mirror_inventory.py` (pip package). The
stdlib script cannot import it without breaking the stdlib-only
contract. Instead, `session_bootstrap.py` carries a small inline
constant `_SURFACE_DIRS` covering all 7 surfaces:

```python
_SURFACE_DIRS = {
    "claude-code":    (".claude/skills",   ".claude/agents"),
    "codex":          (".codex/skills",    ".codex/agents"),
    "gemini-cli":     (".gemini/skills",   ".gemini/agents"),
    "github-copilot": (".github/skills",   ".github/agents"),
    "opencode":       (".opencode/skills", ".opencode/agents"),
    "cursor":         (".cursor/skills",   ".cursor/agents"),
    "antigravity":    (".agent/skills",    ".agent/agents"),
}
```

A CI test (`tests/unit/scripts/test_session_bootstrap_surface_map.py`)
asserts `_SURFACE_DIRS` keys equal the canonical surface enum, so drift
between the inline map and the pip-package source of truth is caught at
test time, not at user runtime. Rationale: small duplication beats the
import cycle, and the CI guard makes the duplication safe.

**D-142-03 — primary-surface counting.** When `surfaces.enabled`
contains multiple entries (e.g. `[claude-code, github-copilot]`),
`_count_skills` / `_count_agents` count from the first entry only.
Rationale: mirror trees are byte-equivalent regenerations
(CLAUDE.md §12 "byte-equivalent regenerations"), so counts are
identical across surfaces. Counting from the primary is correct,
single-numbered, and keeps the header one line. Drift between mirrors
is a doctor-phase concern, not a dashboard concern.

**D-142-04 — `_hooks_health` reports `unverified` when scripts exist
but manifest is missing.** Today, missing manifest → `unknown`. New
behaviour: if `.ai-engineering/state/hooks-manifest.json` is missing
*and* `.ai-engineering/scripts/hooks/` exists with at least one file,
return `"unverified"`; the markdown rendering surfaces this as
`hooks: unverified — run regenerate-hooks-manifest`. The genuine
unreadable case (manifest present but malformed JSON or empty `hooks`
mapping) keeps `unknown`. Rationale: distinguishes "install incomplete"
(actionable) from "filesystem error" (investigate).

**D-142-05 — `ai-eng install` finalizes by generating
`hooks-manifest.json`.** The install command runs
`regenerate-hooks-manifest.py` as a final step before exiting. The
hook script already runs in O(seconds) (74 files × sha256). If it
fails (permission error, missing scripts dir), the install warns but
does not abort — the dashboard's `unverified` state remains the
fallback. Rationale: the manual one-shot has been documented since
spec-122, but nothing closes the loop in practice. Auto-generating
costs ~50 ms at install time and prevents the entire class of
`hooks: unknown` dashboard reports for new installs. Existing installs
still show `unverified` until the operator runs the command (D-142-04
makes the path discoverable).

**D-142-06 — JSON schema additive contract.** The JSON payload gains
no new top-level fields. `hooks_health` already exists; its set of
accepted string values expands to include `"unverified"`. The
`schema_version: 1` integer is unchanged. Rationale: cross-IDE
renderers (which are markdown-only consumers) parse the embedded
`markdown` field anyway; the JSON contract only matters for tooling
that already accepts new enum members defensively.

**D-142-07 — manifest mini-parser owns its grammar, not yaml's.** The
mini-parser does *not* attempt to handle arbitrary YAML. It supports:
- `name: <unquoted-or-double-quoted-string>` at top level,
- `surfaces:\n  enabled:\n  - <surface>` (block list) and
  `surfaces.enabled: [<surface>, …]` (flow list) at top level.
Anything else (anchors, multi-line strings, nested mappings) falls
through to "field unresolved" and the dashboard shows `(unnamed)` /
empty surface list — same as today, no regression. Rationale: the
manifest schema is stable per spec-133; we own the parser scope.

## Risks

- **R-142-01 — mini-parser drift from manifest schema.** If a future
  spec changes the manifest layout for `name` or `surfaces.enabled`
  (e.g. moves them under a new top-level key), the mini-parser silently
  returns empty. *Mitigation:* a CI test parses the actual repo
  manifest with the mini-parser and asserts the result equals
  `yaml.safe_load`. Lives at `tests/unit/scripts/test_minimal_manifest_parse.py`.
  Any schema change that breaks the dashboard is then a red CI build,
  not a silent UX regression.

- **R-142-02 — `_SURFACE_DIRS` diverges from `_PROVIDER_TREE_MAPS`.**
  New surface added in `mirror_inventory.py`, inline map forgotten.
  *Mitigation:* CI test in D-142-02 enforces equality. Operator who
  adds a new surface gets a red test pointing them to the inline map
  with a one-line fix.

- **R-142-03 — `regenerate-hooks-manifest.py` slows the install.**
  On a cold machine the script enumerates ~74 files and hashes them.
  Benchmark on the framework repo today: ~120 ms. *Mitigation:* fits
  inside the install command's overall budget (install already does
  filesystem writes). If a future benchmark shows it crossing 500 ms
  on cold installs, gate behind `--skip-hooks-manifest` or move to a
  post-install async step.

- **R-142-04 — counter drift on installs that copy raw mirrors and
  symlinks.** If a surface's skill directory is a symlink (e.g.
  `.claude/hooks → ../../.ai-engineering/scripts/hooks` per CLAUDE.md
  line 165), `is_dir()` / `iterdir()` still works but symlink loops
  could in theory slow the count. *Mitigation:* the count is one
  shallow `iterdir` plus an `is_file()` check per entry, no recursion.
  The function already caps work at one directory level.

- **R-142-05 — installs without `surfaces.enabled` field at all.**
  Older manifests or hand-edited ones may omit the field. *Mitigation:*
  fallback to `claude-code` as the implicit primary (matches the legacy
  hardcoded behaviour) and log a single-line warning to stderr. The
  manifest schema itself defaults to `claude-code` as the first
  surface (per spec-133 D-133-16), so this fallback aligns with the
  framework's own default.

- **R-142-06 — operator on a surface beyond the 7 enum entries.**
  Today the enum is closed (claude-code, codex, gemini-cli,
  github-copilot, opencode, cursor, antigravity). If a future surface
  is added, the inline `_SURFACE_DIRS` returns no entry and the count
  falls back to `0`. *Mitigation:* the JSON output gains an optional
  `surface_resolved: <surface-or-null>` field (one-line addition under
  D-142-06's additive contract) so tooling can detect the unknown
  surface. CI test in D-142-02 still gates the inline map vs. enum.

## References

- doc: src/ai_engineering/config/mirror_inventory.py — canonical surface→path map (`_PROVIDER_TREE_MAPS`)
- doc: .ai-engineering/scripts/regenerate-hooks-manifest.py — one-shot hooks-manifest generator
- doc: .ai-engineering/scripts/session_bootstrap.py — script being reworked (lines 282-346, 797-840)
- doc: .claude/skills/ai-start/SKILL.md — dashboard contract surface
- doc: CLAUDE.md §12 — "byte-equivalent regenerations" cross-surface invariant
- doc: spec-133 D-133-16 — closed enum of 7 surfaces, first-entry primary
- doc: spec-131 D-131-12 — trusted-argv lane (why we do NOT change the invocation)

## Open Questions

None blocking. Items deferred to plan-time:
- Whether `unverified` markdown rendering should also include a one-line
  install-completion hint (e.g. "this install is partial").
- Whether `surface_resolved: null` (R-142-06) should trigger a
  stderr warning at all, or remain silent for tooling integrations
  that intentionally pre-resolve.
