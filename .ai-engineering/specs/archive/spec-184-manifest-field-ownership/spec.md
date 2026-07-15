---
spec: spec-184
slug: manifest-field-ownership
title: spec-184 — Field-level manifest ownership + framework version-drift UX
status: approved
effort: large
branch: main
target_dispatch: /ai-autopilot
summary: Give manifest.yml field-level ownership (system keys the framework maintains vs user keys it never touches), wire ai-eng update to advance framework_version, then detect and surface project-vs-installed framework drift with a differentiated UX (◈ package upgrade vs ⟳ project update).
---

## Summary

ai-engineering has TWO distinct version-staleness axes, and only one is
covered today:

1. **Package vs PyPI** — the installed `ai-eng` binary is behind the
   latest published release. WELL COVERED: an inline `◈ ai-engineering
   {installed} → {latest} · run ai-eng version upgrade` notice fires
   post-command / on bare `ai-eng` / in `ai-eng version`, backed by a
   24h-TTL background PyPI poll (`version-check.json`), fail-open.
2. **Project vs installed** — the framework files applied into a
   consumer project (`.ai-engineering/`) are behind the installed
   `ai-eng`. COMPLETELY ABSENT: no surface compares the project's applied
   framework version against the installed `__version__`, `ai-eng update`
   gives no signal it is even needed, and running it leaves no version
   trace.

Root cause of axis 2: `.ai-engineering/manifest.yml` is classified
whole-file `TEAM_MANAGED / FrameworkUpdatePolicy.DENY`, so `ai-eng
update` skips it entirely (`skip-denied`). Its `framework_version` key —
the one datum meant to record "which framework version wrote these
files" — is therefore frozen at the install-time value forever, and
nothing advances it. Ownership is expressed only at the FILE level; a
single file cannot say "this key is mine to maintain, that key is the
team's."

The fix is narrow because the machinery already exists but is not wired
together: the framework already ships a per-key role map
(`control_plane.manifest_field_roles`: `descriptive_metadata` +
`generated_projection` = system, `canonical_input` = user) AND a
comment-preserving field-level writer (`update_manifest_field`, ruamel
round-trip) the installer already uses to patch `name` / `surfaces` /
`providers` post-copy. This spec (a) makes manifest ownership
FIELD-level using that role map, (b) wires `ai-eng update` to advance the
system-owned `framework_version` via that writer while never touching
user keys, and (c) detects and surfaces project-vs-installed drift with a
UX that is visually distinct from the PyPI-upgrade notice — a different
mark (`⟳`) and a different verb (`ai-eng update`, not `ai-eng version
upgrade`) so the two axes are never confused.

All claims below were verified against live code by three parallel
`/ai-explore` sweeps this session; file:line evidence is in References.

## Goals

### Phase 1 — Field-level ownership + framework_version advancement (foundation)

1. Manifest ownership becomes FIELD-level for `manifest.yml` ONLY (not a
   generic any-file primitive — D-184-01). The existing
   `control_plane.manifest_field_roles` map is promoted from documentation
   to enforcement: `descriptive_metadata` / `generated_projection` keys are
   FRAMEWORK-owned (the framework may write them), `canonical_input` keys
   are TEAM-owned (the framework must never write them).

2. `ai-eng update` advances the framework-owned `framework_version` key in
   the project's `manifest.yml` to the installed package `__version__` it
   applied, via the existing `update_manifest_field` (ruamel round-trip:
   comments, blank lines, quotes, and key order preserved). ONLY
   `framework_version` is advanced in v1 (D-184-02); all `canonical_input`
   (user) keys are left byte-untouched. A missing-key insert fallback
   handles slim / hand-trimmed manifests that omit `framework_version`.

3. `schema_version` is NOT advanced in v1 (deferred — D-184-02): advancing
   it without a matching `ManifestConfig` model migration would validate a
   schema the installed package does not understand. It remains
   framework-owned in the role map; a future spec adds the migration path.

4. A structured "applied framework version" datum is now reliably
   maintained: after `ai-eng update`, `manifest.framework_version` equals
   the package version that wrote the files. This is the SSOT the drift
   check reads.

### Phase 2 — Drift detection + differentiated UX

5. Project-framework drift is detected by comparing (project
   `manifest.framework_version`) against (installed `__version__`) via
   PEP 440 (`is_newer`). Drift = installed is newer than applied. The
   check is ADVISE-ONLY — it never blocks a command or changes an exit
   code (D-184-03), mirroring the stack-drift banner's advisory default.

6. The drift signal is visually DISTINCT from the existing PyPI-upgrade
   notice (D-184-04): the PyPI notice keeps `◈ … → … · run ai-eng version
   upgrade` (upgrade the TOOL); the new drift signal uses a different mark
   `⟳` and the verb `ai-eng update` (apply the tool's files to the
   PROJECT). Two axes, two marks, two verbs — never conflated. Panel/label
   TEXT is the primary signal; the mark and colour are reinforcement only.

7. Drift surfaces across the CLI, each reusing an existing pattern
   (D-184-05):
   - **`ai-eng status`** — a new "Framework" row (status shows zero
     version today): `project {applied} · installed {installed}` + state
     (up to date / `⟳ behind — run ai-eng update`).
   - **`ai-eng doctor`** — a new `framework-drift` `CheckResult` sibling to
     the existing stack-drift check (WARN on drift; `--fix` runs update).
   - **`/ai-start` dashboard** — a conditional `⚠ Framework drift` block
     mirroring the existing `⚠ Compatibility` block.
   - **Drift banner** — an optional advisory banner mirroring the
     stack-drift `WARNING / detail rows / Recovery: ai-eng update` shape,
     emitted to stderr, gated so it does not spam (see D-184-06).

8. All output paths remain honest: the drift signal is stderr-only where
   it is a banner (never pollutes stdout / JSON), suppressed in `--json`
   mode, and fail-open (any error in the drift check is swallowed so the
   hot path never breaks).

## Non-Goals

1. No generic file-level→field-level ownership primitive for arbitrary
   files (D-184-01) — this spec adds field-level resolution for
   `manifest.yml` only, driven by its existing role map. A generic
   per-key ownership engine is YAGNI until a second file needs it.
2. No advancement of `schema_version`, `skills`, `agents`, or any
   `generated_projection` key by `ai-eng update` in v1 — only
   `framework_version`. Advancing generated projections and schema
   migration are separate follow-ups (Open Questions).
3. No blocking on drift, and no new strict/regulated exit code for it —
   advise-only (D-184-03). An opt-in strict mode may be a later addition.
4. No rewrite of the PyPI-update notice mechanism — it is well-homed and
   stays; this spec only ensures the NEW drift signal is visually
   differentiated from it, and may lightly refine wording for the pairing.
5. No change to the whole-file DENY posture for OTHER team-managed files —
   only `manifest.yml` gains field-level resolution.
6. No completion of the full field-role map's MIXED leaf-level
   classification (telemetry, brainstorm, work_items discovery IDs, etc.)
   this release — v1 only needs `framework_version` framework-owned and
   everything else team-owned/untouched. Full map completion is captured in
   Open Questions.

## Decisions

### D-184-01 — Field-level ownership for manifest.yml only, not a generic primitive

**Choice**: Add per-key ownership resolution for `manifest.yml` alone,
driven by the existing `control_plane.manifest_field_roles` map. Do NOT
build a generic "any file declares per-key policy" engine in the control
plane.
**Rationale**: Operator decision (2026-07-14). `manifest.yml` is the only
file today that mixes framework-bookkeeping keys with user config, and it
already ships a per-key role map + a comment-preserving field writer. A
generic per-key ownership engine (new schema in `skill_domain`, updater
changes for every file) is a large blast radius with no second consumer —
KISS/YAGNI. Scope the enforcement to the one file that needs it; generalise
only if a second file ever does.

### D-184-02 — v1 advances framework_version only; schema_version deferred

**Choice**: `ai-eng update` advances ONLY `framework_version` in v1.
`schema_version` stays framework-owned in the role map but is not written
by update until a migration story exists.
**Rationale**: Operator decision (2026-07-14). `framework_version` is a
free-form string — safe to set to the installed `__version__` with no
downstream validation risk. `schema_version` gates `ManifestConfig`
validation (`loader.py:88`): advancing it without a corresponding model
migration would make the installed package validate a schema it does not
understand. Narrow v1 to the safe, high-value key; gate schema migration
behind its own follow-up.

### D-184-03 — Drift is advise-only, never blocks

**Choice**: The project-framework-drift check reports (banner + status +
doctor + dashboard) but never blocks a command, changes an exit code, or
introduces a strict/regulated failure mode.
**Rationale**: Operator decision (2026-07-14). A stale project framework
version is not a security or integrity breach — it is a "you could
refresh your governance files" nudge. The stack-drift banner's advisory
default is the precedent to mirror. Blocking on it would punish users for
routine lag and conflicts with the framework's fail-open plumbing posture.
An opt-in strict mode can be added later if real demand appears.

### D-184-04 — Two axes, two marks, two verbs (differentiated UX)

**Choice**: Keep the PyPI-package notice as `◈ … → … · run ai-eng version
upgrade` (upgrade the TOOL). Give the project-drift signal a DISTINCT mark
`⟳` and the verb `ai-eng update` (apply the tool's files to the PROJECT).
Panel/label text is always the primary signal; mark + colour reinforce.
**Rationale**: The two staleness axes are genuinely different actions —
`ai-eng version upgrade` updates the pip/uv package from PyPI; `ai-eng
update` re-applies the installed package's templates into the project.
Today only the first exists and both would use the same `◈` brand mark,
risking confusion in a redesign. A distinct mark + verb makes the mental
model self-evident: `◈` = get a newer tool, `⟳` = sync this project to the
tool you have. Never carry meaning in colour alone (accessibility).

### D-184-05 — Reuse existing surface patterns, add a Framework row to status

**Choice**: Surface drift through: a new "Framework" row in `ai-eng
status` (which shows no version today), a `framework-drift` `CheckResult`
in `ai-eng doctor` (sibling to the stack-drift check), a `⚠ Framework
drift` block in the `/ai-start` dashboard (mirroring `⚠ Compatibility`),
and an optional advisory banner mirroring the stack-drift
`WARNING/detail/Recovery` shape.
**Rationale**: Each surface already has a proven visual idiom; matching
them keeps the CLI cohesive rather than inventing a new widget. `ai-eng
status` is the natural home because it is the "install posture" surface
and currently shows zero version at all — the clearest empty slot for the
project-vs-installed line.

### D-184-06 — Advance framework_version via update_manifest_field (ruamel), restricted to the descriptive_metadata allowlist

**Choice**: `ai-eng update` writes `framework_version` through the existing
`update_manifest_field` (ruamel round-trip), NOT the whole-file
`write_bytes` path and NOT the source-repo regex path. The write is
strictly restricted to the `descriptive_metadata` (framework-owned)
allowlist so no `canonical_input` (user) key is ever touched.
**Rationale**: `update_manifest_field` is the established,
comment/order-preserving field writer already used by the installer to
patch user keys post-copy — reusing it (not a third writer) is DRY and
low-risk. Restricting the write to the framework-owned allowlist makes the
field-level DENY carve-out safe: user config is provably untouched, and
overwriting a user's hand-edit to a framework-owned key like
`framework_version` is by-design (it is not theirs to hand-edit).

### D-184-07 — One spec: ownership foundation + drift UX ship together

**Choice**: The ownership fix, the `framework_version` advancement, the
drift detection, and the UX surfaces are one spec, not two.
**Rationale**: Operator decision (2026-07-14). They are tightly coupled:
the ownership carve-out is what makes `framework_version` advanceable;
shipping the UX without it means the drift warning never clears (permanent
false drift); shipping the ownership fix without the UX leaves the newly
reliable datum invisible. The value is only realised end-to-end. Splitting
would double the delivery ceremony for a change whose parts are useless in
isolation.

## Risks

### R-184-01 — Field-write clobbers a user hand-edit to a framework-owned key

**Risk**: A user who hand-edits `framework_version` in `manifest.yml`
loses that edit when `ai-eng update` overwrites it.
**Mitigation**: By design — `framework_version` is framework-owned
bookkeeping, not a user datum; the manifest header already states
framework sections are framework-maintained. The write is strictly
restricted to the `descriptive_metadata` allowlist so no `canonical_input`
(user) key is ever at risk. Document the ownership split so the boundary
is explicit.

### R-184-02 — KeyError / crash on a slim or hand-trimmed manifest

**Risk**: `update_manifest_field` errors if `framework_version` (or the
parent path) is absent, which is legal for a slim manifest relying on
framework-injected defaults.
**Mitigation**: The updater uses a setdefault/insert fallback — if
`framework_version` is missing it is inserted (in the descriptive-metadata
region), not patched in place. The whole drift/advance path is fail-open:
any error is swallowed and logged, never breaking `ai-eng update`.

### R-184-03 — Comment / ordering loss when writing the manifest

**Risk**: A naive YAML dump would strip the manifest's comments and
reorder keys, corrupting a user-owned file.
**Mitigation**: Use `update_manifest_field`'s ruamel round-trip
(`YAML(typ="rt")`, `preserve_quotes=True`) which preserves comments, blank
lines, quotes, and key order. Never use the comment-losing PyYAML dump
path (nothing writes the manifest via PyYAML today; keep it that way).

### R-184-04 — Drift false-positive confuses or annoys the user

**Risk**: If the drift check fires when there is no real drift (e.g. a
consumer install whose `framework_version` legitimately equals the
package), or nags on every command, it erodes trust.
**Mitigation**: Advise-only (D-184-03), and the banner is gated/throttled
like the PyPI notice (once-per-window, suppressed in JSON, exempt on
`update`/`doctor`/`version` themselves). The signal always names the exact
recovery (`ai-eng update`). After a successful update the datum advances
(Phase 1) so the signal clears — no permanent false drift.

### R-184-05 — Two update surfaces (◈ vs ⟳) read as noise together

**Risk**: A user badly out of date on both axes sees the PyPI notice AND
the drift banner at once, which could feel like clutter.
**Mitigation**: Distinct marks/verbs make the two actionable and
non-redundant (upgrade the tool, then update the project — a natural
2-step). Coordinate their gating so they compose rather than stack
noisily; the drift banner is exempt on the same automation/hot-path set as
the PyPI notice.

## References

- doc: src/ai_engineering/config/framework_defaults.py:41-65 (`manifest_field_roles`: descriptive_metadata / generated_projection / canonical_input — the field-role backbone)
- doc: src/ai_engineering/config/loader.py:106-159 (`update_manifest_field` — ruamel round-trip, comment/order-preserving field writer)
- doc: src/ai_engineering/state/control_plane.py:66-68 (`.ai-engineering/manifest.yml` classified whole-file TEAM_MANAGED/DENY; rules are path-glob triples only)
- doc: tools/skill_domain/state_models.py:41-52,115-198 (OwnershipLevel / FrameworkUpdatePolicy enums; OwnershipEntry keys on a path pattern; is_update_allowed / has_deny_rule)
- doc: src/ai_engineering/updater/service.py:876-950 (`_evaluate_file_change`: skip-denied on DENY; whole-file byte-compare) + :504-520 (`write_bytes` whole-file apply) + :961-1001 (team-managed-update-protected)
- doc: src/ai_engineering/cli_commands/core.py:1102-1139 (update_cmd → run_update_workflow → update — the apply-phase call site to add the framework_version advance)
- doc: src/ai_engineering/config/manifest.py:387,196-198,403 (ManifestConfig.framework_version; VersionCheckConfig defaults enabled/ttl_hours/source)
- doc: src/ai_engineering/config/loader.py:73,84-88 (PyYAML safe_load read path; "user-supplied values always win" default injection)
- doc: .ai-engineering/manifest.yml:1-11 ("This file holds USER configuration only" header; framework_version + schema_version values)
- doc: src/ai_engineering/cli_ui.py:377-465 (`_render_update_notice` — the ◈ PyPI notice, the pattern the ⟳ drift signal must differentiate from) + :468-503 (render_version_status)
- doc: src/ai_engineering/version/latest.py:49-64 + version/compare.py:16-25 (resolve_latest_known SSOT; is_newer PEP 440 — reuse for the drift comparison)
- doc: src/ai_engineering/cli_factory.py:292-351 (`_stack_drift_middleware` — the WARNING/detail/Recovery banner shape a drift banner should mirror; exempt set)
- doc: src/ai_engineering/cli_commands/status.py + cli_commands/_render_config.py:33-61 (status shows Surfaces/Stacks/Policy + Next steps, zero version — the home for the Framework row)
- doc: src/ai_engineering/cli_commands/core.py doctor_cmd + doctor/runtime/version.py + doctor/phases/detect.py:173 (doctor lifecycle version check; _check_stack_drift — the sibling for a framework-drift CheckResult)
- doc: .claude/skills/ai-start/SKILL.md + session_bootstrap.py `_version_status` / `⚠ Compatibility` block (dashboard version line + conditional-warning pattern)
- doc: src/ai_engineering/maintenance/report.py:352 (install_manifest_version — the only surface reading project framework_version today; compares vs registry lifecycle, unreliable)
- doc: src/ai_engineering/validator/categories/manifest_coherence.py:59-78,187-248 (mirror of the role map; _check_source_repo_framework_versions — framework-vs-package check that runs in the SOURCE checkout only, absent for consumers)
- doc: src/ai_engineering/release/version_bump.py:170-208 (_update_framework_manifest_version regex + _sync_framework_manifests — the source-repo-only writer NOT to reuse for consumer update)
- doc: docs/persistence-doctrine.md (files-only SSOT posture for the manifest)

## Open Questions

1. **Full field-role map completion.** The `manifest_field_roles` map omits
   the injected knowledge-base keys (`prereqs`, `required_tools`,
   `python_env`, `tooling`, `control_plane` itself) and three real policy
   keys present in the file but absent from schema AND map (`audit_policy`,
   `build`, `security`). MIXED keys (telemetry, brainstorm, hot_path_slos,
   contexts.precedence) need LEAF-level ownership, and `work_items`
   discovery-generated IDs need a "machine-written, do-not-hand-edit"
   marker; `ownership.framework`/`root_entry_points` are mislabelled
   `canonical_input` but are framework-authored. v1 does not need these
   (only `framework_version` is advanced), but a follow-up should complete
   the map before `update` advances any further system key.
2. **schema_version migration.** Advancing `schema_version` needs a
   `ManifestConfig` model-migration path (deferred per D-184-02). Recommend
   a dedicated follow-up: a versioned manifest-migration mechanism that
   advances `schema_version` and transforms the file in lockstep.
3. **generated_projection advancement.** Should `ai-eng update` also
   re-derive `skills` / `agents` counts (generated_projection) into the
   manifest, or are those better left to `/ai-scaffold` + sync? Out of v1
   scope; revisit once the field-write path is proven on `framework_version`.
4. **Consumer-side coherence gate.** `_check_source_repo_framework_versions`
   only runs in the framework checkout. Adding the drift check is the moment
   to consider a consumer-side coherence validator so drift is caught in CI,
   not just surfaced interactively.
