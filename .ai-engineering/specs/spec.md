---
spec: spec-159
title: Installer source-of-truth parity — wheel content + sync_mirrors drift + fail-loud guards
status: approved
effort: medium
summary: Fix the real external-install reliability bug — update_cmd now finalizes hooks-manifest so enforce-mode stops killing hooks after ai-eng update; add sync_mirrors hook/agent/hooks.json parity, drop cursor from the dogfood manifest, keep an explicit wheel allowlist + content guard (launchers were already shipped — verified), and add fail-loud CI drift+wheel guards; ship as 0.9.1.
---

# spec-159 — Installer source-of-truth parity

## Summary

`ai-eng install`/`update` diverge from the dogfood repo and silently break
**external** (non-editable `pip install` / `uv tool install`) projects. A
15-agent diagnosis workflow (adversarial-verified, live-file confirmed) found a
single recurring failure shape: a surface or file is added/edited in one place,
but the pipeline step that would propagate it into the packaged install template
(the updater's comparison baseline) was never written.

The **real external-install reliability bug** is hook-integrity staleness on
update. `update_cmd` never finalizes `hooks-manifest.json`, so after any
`ai-eng update` ships new hook bytes the pinned sha256 values go stale; the
default integrity mode is `enforce` (`integrity.py:43`, fail-closed), so on the
next session **every hook is killed** (`sys.exit(2)`) — the "install doesn't work
well after update" symptom. `install_cmd` finalizes the manifest
(`cli_commands/core.py:237`); `update_cmd` did not. This is the headline fix.

> **Empirical correction (recorded for honesty).** An earlier draft framed the
> headline breakage as a wheel-packaging gap — that
> `[tool.hatch.build.targets.wheel].include` listed only `*.{md,yml,json}` and
> therefore the 52 `.sh/.ps1/.ts/.rego` launchers (incl. `run-hook.sh`) were
> **absent from every published wheel**. **This was disproven by building the
> wheel.** `packages = ["src/ai_engineering"]` makes hatchling ship the entire
> template tree regardless of the `include` list; a wheel built *with and
> without* the launcher globs contains all 52 files and `run-hook.sh` both
> times. The published 0.9.0 wheel already contains them. The diagnosis had
> reasoned from the `include` list without building an artifact. The `include`
> globs and the wheel-content test are retained as an **explicit allowlist +
> regression guard** (defence against a future hatchling default change), not as
> a fix for a non-existent gap.

Three drift gaps make `ai-eng update` in the dogfood repo report ~94 phantom
changes and mean the framework cannot self-detect drift: (1) the
`hooks-manifest.json` staleness above; (2) `scripts/sync_mirrors/core.py` has no
sync step for `scripts/hooks/` so 16 hook `.py` files perpetually drift, and
hand-maintains `.github/hooks/hooks.json` in two divergent copies (122 vs 101
lines).

> **Two "drift" items that turned out to be by-design (not bugs), corrected
> after CI feedback:** (a) the specialist-agent `.claude` *install templates*
> carry governed provenance frontmatter that the authored canonical
> `.claude/agents/*` lack — this is **intentional** and enforced by
> `validator/_check_claude_specialist_agents_mirror`; the dogfood
> `ai-eng update --preview` "updated" delta on those 10 files is the expected
> canonical-vs-generated-template difference, not drift. (b) The dogfood
> `manifest.yml` enables `cursor` and ships 64 `.cursor` templates for external
> Cursor clients but materializes no live `.cursor/` working dir (the team
> doesn't edit with Cursor) — so `update --preview` lists 64 `.cursor` "new",
> also cosmetic + by-design. An earlier draft tried to "fix" both (write the
> template verbatim; drop `cursor` from the manifest); the first broke the
> mirror-sync governance contract, the second made the product README undercount
> supported surfaces (5 vs 6). Both were reverted.

This spec fixes the genuine drift — hooks-manifest staleness, the missing
hook-scripts sync step, and the dual-maintained `hooks.json` — and adds
**fail-loud** CI guards so this failure class cannot silently recur. It ships as
a `0.9.1` patch so external users receive the hooks-manifest fix in `update_cmd`.

## Goals

- **G1 (real fix):** After `ai-eng update`,
  `.ai-engineering/state/hooks-manifest.json` sha256 entries match the deployed
  hook bytes, so hooks survive the default `AIENG_HOOK_INTEGRITY_MODE=enforce`
  on the next session (no more post-update hook kill).
- **G1b (regression guard):** A built wheel contains `run-hook.sh`,
  `resolve-python.sh`, every `copilot-*.sh`/`copilot-*.ps1`, the `.ts` bridge,
  and all `.rego` policies under `ai_engineering/templates/` — verified by a CI
  test that builds and inspects the **actual wheel** (not `REPO_ROOT`). This
  guards the already-correct packaging against a future regression; it is not a
  fix for a pre-existing gap (none exists — confirmed empirically).
- **G3:** `ai-eng dev sync` propagates `scripts/hooks/**` (incl. `_lib/`) into
  the install-template tree; the 16 currently-drifted hook files resync to
  byte-identical.
- **G4 (corrected — by design, no change):** the specialist `.claude/agents/*`
  **install templates** carry governed provenance frontmatter (canonical body +
  provenance), matching `validator/_check_claude_specialist_agents_mirror`. The
  authored canonical source stays provenance-free. `ai-eng check` mirror-sync
  passes. (No verbatim rewrite — that draft was reverted.)
- **G5:** `.github/hooks/hooks.json` is generated from a single
  event→script source and dual-written to repo root + template tree; the two
  copies are byte-identical.
- **G6 (corrected — cursor stays enabled):** `cursor` remains in `manifest.yml`
  `surfaces.enabled` (= a surface the repo *produces* for external clients);
  the product README correctly reports **6 surfaces** and `ai-eng check`
  counter-accuracy passes. The dogfood repo materializes no live `.cursor/`
  working dir, so `update --preview` lists 64 `.cursor` "new" — cosmetic and
  by-design, not drift.
- **G7:** CI **blocks** (fails the build) on (a) any wheel missing the required
  launcher/policy extensions, and (b) any framework-managed surface drifting
  from its install template. Both guards name the regen command in the failure
  message.
- **G8:** `ai-eng check` reports 7/7 categories passing (mirror-sync,
  counter-accuracy, etc.) and `ai-eng dev sync --check` is clean — the genuine
  drift (hooks `.py`, `hooks.json`) is eliminated. Remaining
  `ai-eng update --preview` deltas in dogfood are the by-design
  canonical-vs-generated-template artifacts of G4/G6 only.
- **G9:** Delivered as a `0.9.1` release so external pip/uv consumers receive the
  `update_cmd` hooks-manifest fix via republish.

## Non-Goals

- The spec-157 version-update notice / banner staleness — already fixed
  operationally this session (editable dist-info regenerated, cache cleared,
  notice render proven). Not re-touched here.
- Making `cursor` a **live** dogfood surface (the dual-write path) — explicitly
  rejected; dogfood does not run Cursor IDE.
- Retroactively repairing already-broken external installs beyond shipping the
  corrected wheel and the `update_cmd` manifest fix (users still run
  `pip install -U` / `ai-eng update` to adopt).
- Re-architecting the updater reconciler, ownership model, or control-plane
  rules.
- Antigravity surface — already correct (`.agents/` = 157 live files via
  existing dual-write); used only as the reference pattern.
- Changing hook runtime behavior, integrity-mode defaults, or the py3.11
  resolver logic itself (spec-154/158 scope).

## Decisions

1. **D-159-01 — Make the wheel launcher/policy allowlist explicit.** Add `.sh`,
   `.ps1`, `.ts`, `.rego` to `[tool.hatch.build.targets.wheel].include`.
   *Rationale:* hatchling already ships these via `packages = ["src/ai_engineering"]`
   (verified: a wheel built with **and** without these globs contains all 52
   launchers + `run-hook.sh`), so this is **not** a fix for a missing-file gap —
   the earlier "absent from every wheel" claim was disproven by building the
   artifact. The explicit globs make the intent auditable and pin the launchers
   so a future change to hatchling's package-data defaults cannot silently drop
   them. Harmless and defensive; kept deliberately.
2. **D-159-02 — Wheel-content CI test inspects the built artifact (regression
   guard).** Add a test that builds the wheel, opens it as a zip, and asserts the
   launcher/policy files exist under packaged `templates/`.
   *Rationale:* the existing `test_hook_interpreter_resolution.py` reads
   `REPO_ROOT` and so could never observe what the external user actually
   receives. This guard inspects the real wheel, locking in the (already-correct)
   packaging so a future regression turns CI red instead of silently shipping
   dead hooks.
3. **D-159-03 — `update_cmd` finalizes the hooks manifest.** Call
   `_finalize_hooks_manifest(root)` from `update_cmd` after the workflow
   completes, matching `install_cmd`.
   *Rationale:* deploying new hook bytes without re-pinning their sha256 makes
   `enforce` mode kill the very hooks the update just shipped — a self-inflicted
   outage on every upgrade.
4. **D-159-04 — Add a `sync_mirrors` hook-scripts sync step.** Add a surface
   step that copies `scripts/hooks/**/*.py` (incl. `_lib/`) into the
   install-template tree, modeled on the existing `scripts/skills/` step.
   *Rationale:* hook scripts had no propagation path at all; every hook edit
   silently drifted the template. Closing the gap makes `dev sync` the single
   regen command for hook parity.
5. **D-159-05 (REVERTED — keep provenance on specialist `.claude` templates).**
   The specialist-agent `.claude` *install templates* keep their governed
   provenance frontmatter (canonical body + provenance); only the authored
   canonical `.claude/agents/*` source is provenance-free.
   *Rationale:* an earlier draft wrote the template verbatim to silence the
   dogfood `update --preview` "updated" delta — but
   `validator/_check_claude_specialist_agents_mirror` *requires* provenance on
   that generated mirror (governance for generated surfaces, `ai-eng check`
   mirror-sync). The verbatim form failed CI. The "updated" delta is the
   intended canonical-vs-generated-template difference, not drift; no fix is
   warranted. Reverted.
6. **D-159-06 — Generate `.github/hooks/hooks.json` from one source.** Add a
   generator that builds the file from the canonical hook event→script mapping
   and dual-writes repo root + template tree (mirroring the codex hooks
   generator).
   *Rationale:* two hand-maintained copies already drifted by 21 lines; a single
   generated source is the only durable fix and matches existing precedent.
7. **D-159-07 (REVERTED — keep `cursor` in `manifest.yml`).** `cursor` stays in
   `surfaces.enabled`.
   *Rationale:* `manifest.enabled` lists surfaces the repo *produces* for
   external clients (cursor ships 64 templates), and the product README +
   `ai-eng check` counter-accuracy derive the "6 surfaces" claim from it.
   Dropping cursor conflated "the team doesn't edit with Cursor" with "we don't
   support Cursor" — it made the README undercount to 5 and failed
   counter-accuracy. The 64 `.cursor` "new" in dogfood `update --preview` is a
   cosmetic by-design artifact (no live `.cursor/` working dir), not drift.
   Reverted.
8. **D-159-08 — CI drift + wheel guards are fail-loud (blocking).** The
   surface-drift guard fails the build on any framework-managed surface that
   differs from its install template; the wheel-content guard fails on any
   missing launcher/policy file. Failure messages name the regen command
   (`ai-eng dev sync` / rebuild).
   *Rationale:* this whole bug class survived precisely because nothing ever
   failed. Fail-loud matches the repo's Hard-Rule doctrine and converts silent
   drift into an actionable red build.
9. **D-159-09 — Deliver as a `0.9.1` patch release.** Bundle the code fixes with
   a version bump + release.
   *Rationale:* the `update_cmd` hooks-manifest fix lives in the package, so it
   only reaches external users when they upgrade to a republished version;
   landing it on `main` without a release leaves downstream `ai-eng update` runs
   still killing hooks under `enforce`.

## Risks

- **R1 — Wheel allowlist over/under-includes.** Adding extensions could ship
  unintended files or still miss an asset type. *Mitigation:* explicit
  per-extension list + D-159-02 test asserting the exact expected file set
  (presence and, for a sample, that no stray cache/editor files appear).
- **R2 — `hooks.json` generator must reproduce current behavior exactly.** A
  generated file that drops the `copilot-runtime-stop` block (present only in the
  122-line repo copy) would regress Copilot. *Mitigation:* golden-file test
  diffing generated output against a reviewed known-good snapshot before
  replacing either copy.
- **R3 — Dropping provenance frontmatter may break a consumer.** Some tool might
  read `canonical_source`/`edit_policy`. *Mitigation:* grep all surfaces for
  readers of those keys before removal; if any exist, relocate provenance out of
  frontmatter rather than deleting the data.
- **R4 — Blocking CI drift guard causes friction on intentional changes.**
  *Mitigation:* the guard compares only framework-managed (non-protected)
  surfaces and always prints `ai-eng dev sync` as the one-line remedy; operator
  surfaces are exempt by the existing ownership map.
- **R5 — 0.9.1 release carries the usual release gotchas** (local-tag bug,
  TestPyPI propagation rerun, gate `ty` blind spot, Snyk pip-CVE gate).
  *Mitigation:* follow the documented release runbook and staged/resume flow;
  treat release as the final delivery step, not mid-build.
- **R6 — Resyncing 16 hook files + agent templates produces a large diff.** Risk
  of burying a real semantic change in mechanical churn. *Mitigation:* land the
  pure `dev sync` resync as its own commit, separate from logic changes, so
  review can verify the resync is byte-mechanical.

## References

- pr: arcasilesgroup/ai-engineering#559 (spec-158 — `run-hook.sh` / resolver origin)
- pr: arcasilesgroup/ai-engineering#554 (spec-154 — ≥3.11 interpreter resolver)
- doc: src/ai_engineering/installer/templates.py (surface tree maps, wheel template root)
- doc: scripts/sync_mirrors/core.py (mirror generation; antigravity dual-write reference pattern)
- doc: pyproject.toml `[tool.hatch.build.targets.wheel]` (the P0 include allowlist)
