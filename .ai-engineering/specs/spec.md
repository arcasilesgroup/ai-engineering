---
spec: spec-151
slug: antigravity-gemini-cli-retirement
title: Antigravity-only Google surface after Gemini CLI retirement
status: approved
effort: large
summary: "Replace the legacy Gemini CLI surface with a single Antigravity Google surface, generating AGENTS/.agents assets, probing agy, and removing GEMINI/.gemini/gemini-cli from pre-release support."
---

# Antigravity-only Google surface after Gemini CLI retirement

## Summary

Google's May 19, 2026 transition moves the consumer Google terminal path from Gemini CLI to Antigravity CLI. ai-engineering currently gives the old `gemini-cli` surface first-class registry, install, mirror, hook, and audit treatment while Antigravity remains mirror-only under stale `.agent/` and `GEMINI.md` assumptions. Before public release, the framework should hard-delete `gemini-cli` support and ship exactly one Google agent surface: `antigravity`, covering the Antigravity app plus `agy` CLI runtime with `AGENTS.md`, `.agents/`, and deterministic diagnostics.

## Goals

- **G1** — Remove `gemini-cli` from the supported surface enum, dogfood manifest, installer choices, docs matrices, generated mirrors, and tests that exist only for the retired Google CLI.
- **G2** — Promote `antigravity` to the only Google agent surface, with one surface id for app/IDE and CLI runtimes; do not introduce `antigravity-cli`.
- **G3** — Generate Antigravity workspace assets under `.agents/` and use `AGENTS.md` as the root context file; do not generate `GEMINI.md` or `.gemini/` for Google support.
- **G4** — Add `agy`/`agy.exe` detection and diagnostics so selected Antigravity installs can report whether the CLI runtime is available.
- **G5** — Update installer/update/autodetect/ownership/capability/validator paths so `.agents/` is framework-owned and governed consistently.
- **G6** — Regenerate mirrors/templates so stale `.gemini`, `GEMINI.md`, npm `gemini`, and `gemini-cli` references are removed from generated Google support, except historical changelog/migration notes.
- **G7** — Keep audit claims honest: do not mark Antigravity audit as full until hook payload fixtures prove the bridge; if hook schema remains undocumented, expose partial/diagnostic support rather than a false full-audit claim.

## Non-Goals

- Not retaining enterprise/API-key Gemini CLI carveouts in the first public release. A future enterprise-only Gemini revival requires a separate approved spec.
- Not creating a second `antigravity-cli` surface. CLI behavior is a runtime capability of `antigravity`.
- Not writing user-home global Antigravity files such as `~/.gemini/antigravity-cli/` during project install.
- Not promising non-interactive CI execution for `agy` until the CLI exposes and we verify a headless contract.
- Not hand-editing generated mirror files without re-running the canonical mirror generator.

## Decisions

- **D-151-01 — One Google surface.** Model Antigravity app and Antigravity CLI as one `antigravity` surface with runtime capabilities.
  **Rationale**: the operator explicitly wants the same product model as Codex/Claude Code, where app and terminal entry points share a surface contract.
- **D-151-02 — Hard-delete `gemini-cli` pre-release.** Remove `gemini-cli` from generated support before public launch rather than preserving enterprise/API-key carveouts.
  **Rationale**: carrying a discontinued consumer CLI before first release adds legacy complexity and duplicated context with little user value.
- **D-151-03 — `AGENTS.md` is the Antigravity root context.** Antigravity support emits `AGENTS.md`; it does not require or generate `GEMINI.md`.
  **Rationale**: Antigravity CLI reads `AGENTS.md`, and the project SSOT rule forbids duplicating the same canonical payload through `GEMINI.md` when Gemini CLI is removed.
- **D-151-04 — `.agents/` replaces `.agent/` with no shim.** New generated Antigravity assets live under `.agents/`; legacy `.agent/` generated paths are deleted.
  **Rationale**: Google docs now default to `.agents/skills`, and the constitution forbids compatibility shims for renamed/generated content.
- **D-151-05 — `agy` probe is diagnostic, not an execution gate.** Missing `agy` is surfaced by doctor/status/install diagnostics, but non-CLI app users can still install Antigravity workspace files.
  **Rationale**: the desktop app and CLI are one surface with separate runtime availability.
- **D-151-06 — Audit capability upgrades only with evidence.** Antigravity may move beyond mirror-only via workspace assets and CLI diagnostics, but `audit_capability` stays `partial` unless a tested hook fixture proves full event coverage.
  **Rationale**: Antigravity migration docs say hooks exist, but public docs available during this spec do not define a complete workspace hook payload schema.
- **D-151-07 — Generated mirrors remain derived.** Delete/regenerate `.gemini/` and Antigravity mirror outputs from canonical `.claude/` sources via `scripts/sync_mirrors/core.py`; do not dual-write manual copies.
  **Rationale**: mirror parity and SSOT-PD require one generator path.

## Acceptance Criteria

- **AC1** — `SURFACE_IDS` no longer contains `gemini-cli`; `get_surface("gemini-cli")` raises `SurfaceUnknownError`; `get_surface("antigravity")` returns tree `.agents/`, instruction file `AGENTS.md`, and non-`none` diagnostics/audit posture consistent with D-151-06.
- **AC2** — The dogfood manifest and install docs list `antigravity` but not `gemini-cli`; generated Antigravity installs contain `AGENTS.md` and `.agents/` and do not contain `GEMINI.md` or `.gemini/` because of Google support.
- **AC3** — Installer template maps, autodetect, updater, ownership defaults, write-scope classification, and mirror inventory classify `.agents/` as the Antigravity tree and stop treating `.agent/` as current generated output.
- **AC4** — Mirror sync generates Antigravity skills/agents under `.agents/` with Antigravity-native comments/docs and removes root/template `.gemini` generation from the supported surface set.
- **AC5** — `ai-eng doctor`/surface diagnostics or an equivalent deterministic helper can detect `agy`/`agy.exe`, report version when present, and fail-soft when absent.
- **AC6** — Tests cover registry shape, invalid `gemini-cli`, Antigravity install matrix, `.agents/` autodetect, mirror generation, stale Gemini reference policy, and `agy` detection.
- **AC7** — CHANGELOG documents the breaking removal of `gemini-cli`, `GEMINI.md`, `.gemini/`, and `.agent/` generated Antigravity output.

## Affected Surfaces

- Domain registry: `src/ai_engineering/domain/surface.py`.
- Manifest/default configuration: `.ai-engineering/manifest.yml`, `src/ai_engineering/config/*`.
- Installer/update/autodetect: `src/ai_engineering/installer/*`, `src/ai_engineering/updater/service.py`.
- Mirrors/templates: `scripts/sync_mirrors/*`, `src/ai_engineering/templates/project/*`, root generated mirror directories.
- Validators and IDE audit docs: `src/ai_engineering/validator/*`, `.claude/skills/ai-ide-audit/**` plus generated mirrors.
- Tests: unit/integration suites for surfaces, manifest schema, installer matrix, mirror sync, and diagnostics.

## Risks

- **R1 — Google docs are still moving.** Mitigation: encode only stable workspace facts (`AGENTS.md`, `.agents/skills`, `agy`) and gate hook-audit claims behind fixtures.
- **R2 — Deleting `.gemini/` is a large generated diff.** Mitigation: perform deterministic mirror regeneration/deletion in one wave and verify with mirror-sync tests.
- **R3 — Existing docs mention Gemini historically.** Mitigation: allow historical changelog/migration references but remove current support matrices and generated instructions.
- **R4 — Antigravity hook schema may remain undocumented.** Mitigation: ship partial audit/diagnostic posture and explicit docs rather than claiming full hook parity.
- **R5 — Broad surface enum removal can break config compatibility tests.** Mitigation: update tests RED-first and let unknown `gemini-cli` fail loudly per hard-delete policy.

## References

- research: `.ai-engineering/specs/drafts/antigravity-app-cli-support-brief.md`
- doc: Google Developers Blog, "An important update: Transitioning Gemini CLI to Antigravity CLI", 2026-05-19 — https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- doc: Antigravity CLI migration — https://antigravity.google/docs/gcli-migration
- doc: Antigravity skills — https://antigravity.google/docs/skills
- doc: Persistence doctrine — `docs/persistence-doctrine.md`

## Open Questions

- **OQ1** — What exact Antigravity hook payload schema should upgrade `audit_capability` from `partial` to `full`? If no public schema is available during implementation, keep full audit as a future spec.
- **OQ2** — Does `agy` expose a non-interactive JSON/headless mode suitable for CI? If not, diagnostics stay interactive/runtime-only.
