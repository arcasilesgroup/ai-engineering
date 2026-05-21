---
title: "Antigravity App and CLI Support After Gemini CLI Transition"
status: draft
audience: /ai-brainstorm
branch: spec-147-wave-1
length_estimate: "~220 lines"
authoring_style: "Staff Architect — evidence-anchored, source-current as of 2026-05-20, no implementation"
principles_required: [KISS, YAGNI, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Cross-surface refactor with hard rename, no shims, deterministic tests before mirror regeneration"
mantra: "Support the product Google now ships: Antigravity app plus Antigravity CLI, while preserving Gemini CLI only where Google still preserves it."
---

> READ FIRST. This brief is an intake artifact for `/ai-brainstorm`. It does not implement the change. It answers the operator's question from May 20, 2026: after Google's May 19, 2026 announcement that Gemini CLI transitions to Antigravity CLI, is ai-engineering correctly supported for both the Antigravity app and the new CLI?
>
> Short answer: no. Gemini CLI is substantially supported. Antigravity exists in the framework, but it is modeled as mirror-only, not enabled in the dogfood manifest, not wired to `agy`, and generated under legacy `.agent/` paths with Gemini-shaped content. Google's current docs say Antigravity now supports the core primitives we need: `AGENTS.md`/`GEMINI.md` context, skills, plugins, MCP, hooks, subagents, permissions, and a terminal CLI. The spec phase should promote Antigravity from advisory mirror to first-class app plus CLI integration.

---

## 1. Vision

ai-engineering should treat Google's coding-agent surface as two active Antigravity products: the Antigravity desktop app/IDE surface and the Antigravity CLI terminal surface. The framework should still preserve Gemini CLI support for enterprise/API-key users during Google's transition window, but the default Google terminal path for consumer users should move to `agy`.

The target state is simple: an operator can enable Antigravity support and receive the right workspace files, hooks, skills, MCP config, permission model, and audit bridge for both the app and CLI without stale `.gemini` assumptions leaking into Antigravity-only installs.

## 2. Scope Boundary

### In scope

| Area | Included work |
|------|---------------|
| Surface model | Decide whether `antigravity` represents the app only and whether to add `antigravity-cli`, or whether to model a single Antigravity family with app/CLI capabilities. |
| Workspace layout | Move generated Antigravity workspace assets to Google's current `.agents/` layout and stop generating new Antigravity installs primarily under `.agent/`. |
| CLI integration | Add `agy`/`agy.exe` detection, capability probing, installer checks, docs, and surface diagnostics. |
| Hooks and audit | Map Antigravity hook events into canonical `framework-events.ndjson`; update hook engine and audit capability once verified. |
| Mirror generation | Generate Antigravity-native skills, agents/subagents, plugins, and references without `.gemini` path leakage. |
| Gemini transition | Keep `gemini-cli` valid for enterprise/API-key workflows; do not hard-delete Gemini on a consumer deadline alone. |
| Validation | Extend mirror, ownership, installer, update, and IDE-audit validators to include the Antigravity layout. |

### Explicitly NOT in scope

| Area | Exclusion |
|------|-----------|
| Implementing this brief | `/ai-brainstorm` must approve the spec before edits. |
| Removing Gemini CLI immediately | Google preserves enterprise/API-key paths after June 18, 2026; hard deletion is premature. |
| User-home writes by default | The installer should not write `~/.gemini/antigravity-cli/` or `~/.gemini/antigravity/` unless an explicit user-scope command is designed. |
| Solving undocumented headless parity | Antigravity CLI headless/CI parity with Gemini CLI is unclear in public docs; capture as an open decision. |

## 3. Diagnostic Snapshot

Current Gemini CLI support is first-class in the framework registry: `gemini-cli` has `GEMINI.md`, `.gemini/`, native hooks, and full audit capability (`src/ai_engineering/domain/surface.py:96-103`). The dogfood manifest already enables both `gemini-cli` and `antigravity` under `surfaces.enabled` (`.ai-engineering/manifest.yml:28-36`), but the framework treats Antigravity as mirror-only due to the registry configuration.

Current Antigravity support is explicitly mirror-only: the registry points to `GEMINI.md` plus `AGENTS.md`, writes a `.agent/` tree, and declares `hook_engine="none"` plus `audit_capability="none"` (`src/ai_engineering/domain/surface.py:132-140`). The unit contract freezes that posture by asserting Antigravity is mirror-only (`tests/unit/domain/test_surface.py:75-78`).

Current installer template maps know Antigravity as a closed enum but still write the legacy `.agent` tree: root files are `GEMINI.md` and `AGENTS.md` (`src/ai_engineering/installer/templates.py:58-61`), and the tree map copies `.agent` to `.agent` (`src/ai_engineering/installer/templates.py:208-210`). Autodetection also looks for `.agent/`, not `.agents/` (`src/ai_engineering/installer/autodetect.py:222-251`).

Current mirror generation emits Antigravity from the Gemini generator: `scripts/sync_mirrors/core.py:1809-1819` copies Gemini-shaped skills and agents into `.agent/`, and the Antigravity target module describes the surface as "MIRROR-ONLY" with no hook adapter (`scripts/sync_mirrors/antigravity_target.py:1-9`, `scripts/sync_mirrors/antigravity_target.py:26-33`). This is stale against Google's May 2026 Antigravity CLI docs, which now document hooks, plugins, MCP, subagents, and permissions for Antigravity.

Current installer CLI text advertises `antigravity` as a selectable surface (`src/ai_engineering/cli_commands/core.py:105-113`), and manifest parsing accepts it (`tests/unit/config/test_manifest_surface_schema.py:62-71`). However, the public install matrix only tests the older single-provider cases through Gemini, Codex, Claude, and Copilot (`tests/integration/test_install_matrix.py:11-25`), leaving Antigravity install behavior less exercised than first-class surfaces.

Current ownership defaults include `.agent/**` as framework-owned (`src/ai_engineering/config/framework_defaults.py:71-84`), but write-scope classification treats `.claude/`, `.codex/`, `.gemini/`, and selected `.github/` paths as mirrors without including `.agent/` or `.agents/` (`src/ai_engineering/state/capabilities.py:293-298`). That split increases the chance that Antigravity assets are generated but not governed consistently.

Current historical notes record the original Antigravity decision as "mirror-only, no hooks upstream" (`CHANGELOG.md:1481-1483`). Google's public position changed on May 19, 2026: Antigravity CLI is available, supports most Gemini CLI workflow-defining features, and becomes the consumer Google terminal path after a June 18, 2026 cutoff for free/Pro/Ultra Gemini Code Assist serving.

## 4. Architecture

The spec should deliver a four-layer integration:

1. **Surface registry layer.** Represent Antigravity app and Antigravity CLI capabilities under a single consolidated `antigravity` surface with capability flags (rather than splitting into two separate surfaces). The registry must stop saying `hook_engine="none"` once the hook bridge is proven.
2. **Workspace artifact layer.** Generate Antigravity-native assets under Google's standard `.agents/` workspace layout (skills, agents/subagents, hooks, MCP config, rules, and optional plugin bundle metadata). Keep root `AGENTS.md` and `GEMINI.md` where Antigravity CLI docs say both are read. Update the dashboard mapping script `session_bootstrap.py` to point to `.agents/` layout instead of legacy `.agent/`.
3. **Runtime bridge layer.** Add an Antigravity hook bridge that normalizes Antigravity events (`PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`) into the canonical hook contract and emits `framework-events.ndjson`.
4. **CLI probe layer.** Detect `agy`/`agy.exe`, capture version and auth-state limitations, warn on missing binary for `antigravity-cli`, and document that auth may remain interactive.

The design should reuse the existing Surface abstraction and template resolver rather than introduce a separate provider axis. The current repo already hard-cut to `surfaces.enabled` as the canonical axis (`CHANGELOG.md:1462-1468`), so Antigravity should fit that model instead of reviving `ai_providers.enabled` or `providers.ides`.

## 5. Evidence Catalog

| # | Finding | Evidence |
|---|---------|----------|
| E-1 | Gemini CLI is first-class and audited. | `src/ai_engineering/domain/surface.py:96-103` |
| E-2 | Dogfood enables both Gemini CLI and Antigravity. | `.ai-engineering/manifest.yml:28-36` |
| E-3 | Antigravity registry is mirror-only, no hooks or audit. | `src/ai_engineering/domain/surface.py:132-140` |
| E-4 | Tests freeze Antigravity as mirror-only. | `tests/unit/domain/test_surface.py:75-78` |
| E-5 | Antigravity installer root files are only `GEMINI.md` and `AGENTS.md`. | `src/ai_engineering/installer/templates.py:58-61` |
| E-6 | Antigravity installer tree is `.agent`, not `.agents`. | `src/ai_engineering/installer/templates.py:208-210` |
| E-7 | Autodetect keys off `.agent`, not `.agents`. | `src/ai_engineering/installer/autodetect.py:222-251` |
| E-8 | Mirror sync writes `.agent` with Gemini-shaped content. | `scripts/sync_mirrors/core.py:1809-1819` |
| E-9 | Antigravity target module explicitly says no hook adapter. | `scripts/sync_mirrors/antigravity_target.py:1-9` |
| E-10 | Antigravity generation only smoke-tests skill text. | `tests/integration/sync_mirrors/test_new_surface_targets.py:96-105` |
| E-11 | CLI exposes Antigravity as a surface option. | `src/ai_engineering/cli_commands/core.py:105-113` |
| E-12 | Manifest schema accepts Antigravity. | `tests/unit/config/test_manifest_surface_schema.py:62-71` |
| E-13 | Install matrix omits Antigravity first-class cases. | `tests/integration/test_install_matrix.py:11-25` |
| E-14 | Ownership includes `.agent/**`, but capability mirror classification omits `.agent` and `.agents`. | `src/ai_engineering/config/framework_defaults.py:71-84`, `src/ai_engineering/state/capabilities.py:293-298` |
| E-15 | Historical decision says Antigravity is mirror-only. | `CHANGELOG.md:1481-1483` |

## 6. Roadmap

### Milestone 1 — Decide the surface contract

Acceptance gates:

- The spec records that the new terminal target is modeled under a single consolidated `antigravity` surface with capability flags.
- `SURFACE_IDS` and docs use one naming contract.
- Gemini CLI remains valid for enterprise/API-key users until a later approved removal spec.

### Milestone 2 — Move Antigravity workspace layout to `.agents/`

Acceptance gates:

- New Antigravity installs generate `.agents/skills/<skill>/SKILL.md`.
- Welcome dashboard path mappings in `.ai-engineering/scripts/session_bootstrap.py` are updated from `.agent` to `.agents`.
- Root `AGENTS.md` and `GEMINI.md` are still generated when Antigravity is enabled.
- Generated Antigravity content contains no stale `.gemini/agents` references.
- `.agent/` is hard-deleted from generated templates in favor of `.agents/` to satisfy Rule 3 (No compatibility shims).

### Milestone 3 — Add Antigravity CLI probe and installer diagnostics

Acceptance gates:

- `ai-eng doctor` or equivalent surface diagnostics detect `agy`/`agy.exe`.
- Missing `agy` is a clear warning or blocker depending on selected surface.
- Install docs cite Google install commands for macOS/Linux, PowerShell, and CMD.

### Milestone 4 — Add Antigravity hook/audit bridge

Acceptance gates:

- Antigravity `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, and `Stop` events map to canonical hook events.
- At least one integration test writes a valid `framework-events.ndjson` row from an Antigravity hook fixture.
- The registry audit capability is upgraded only after this proof exists.

### Milestone 5 — Extend validators, ownership, and IDE audit

Acceptance gates:

- Mirror validators in `src/ai_engineering/validator/categories/mirror_sync.py` and `src/ai_engineering/config/mirror_inventory.py` include `.agents/` and any chosen Antigravity plugin layout.
- The path reference validator in `src/ai_engineering/validator/categories/file_existence.py` includes `.agents` under its `fallback_roots`.
- Ownership/control-plane defaults classify Antigravity assets consistently.
- `/ai-ide-audit` report templates and evidence collection include Antigravity app and CLI.
- Install/update/orphan-cleanup tests cover Antigravity.

## 7. Definition of Done

- Antigravity app support is not merely "mirror-only": it has native workspace layout, validated skills, documented hooks/MCP/permissions support, and IDE-audit coverage.
- Antigravity CLI support is keyed to `agy`/`agy.exe`, not to the Node/npm `gemini` CLI.
- Gemini CLI remains supported where Google still supports it, with docs explaining the May 19, 2026 announcement and June 18, 2026 consumer cutoff.
- No generated Antigravity-only install references missing `.gemini` paths.
- Tests cover registry shape, install matrix, mirror sync, hook bridge, doctor/probe behavior, ownership classification, and docs links.
- CHANGELOG records the breaking layout rename if `.agent/` is retired.

## 8. Quality Stamps

| Principle | Application |
|-----------|-------------|
| §10.1 KISS | One Google terminal path for consumers: `agy`; no parallel Antigravity template trees. |
| §10.2 YAGNI | Do not implement unsupported headless/CI behavior until Google documents it or a local probe proves it. |
| §10.5 TDD | Add failing tests for `.agents/` generation, `agy` probing, hook event normalization, and stale `.gemini` references before code changes. |
| §10.6 SDD | Promote this brief through `/ai-brainstorm`; no implementation from the draft. |
| §10.7 Clean Code | Keep Surface as the domain primitive; do not resurrect provider/IDE split logic. |
| §10.8 Hexagonal Architecture | Treat `agy` probing and hook envelopes as adapters behind the existing deterministic governance port. |

## 9. Open Decisions

1. **Surface identity:** Resolved: Use a single consolidated `antigravity` surface with app/CLI capability flags.
2. **`.agent` handling:** Resolved: `.agent/` will be hard-deleted from generated templates in favor of `.agents/` (Google's current standard layout) to follow Rule 3 (No compatibility shims).
3. **Plugin packaging:** Should ai-engineering ship Antigravity customizations as raw `.agents/skills` plus hooks, or as a workspace plugin under `.agents/plugins/ai-engineering/`?
4. **Hook confidence:** What exact Antigravity hook payloads must be fixture-captured before upgrading audit capability from `none` to `full` or `partial`?
5. **Headless mode:** Does `agy` have a non-interactive `-p`/JSON-output equivalent, or should CI automation remain explicitly unsupported?
6. **Enterprise Gemini:** How long should `gemini-cli` remain first-class after June 18, 2026 for paid Gemini and enterprise API-key usage?

## 10. Migration

This is a breaking integration migration, not a compatibility shim:

- Keep existing `gemini-cli` as a supported surface for enterprise/API-key workflows.
- Introduce or redefine Antigravity support using Google's current `.agents/` workspace convention.
- Hard-rename generated Antigravity template output from `.agent/` to `.agents/` if the spec chooses the default-current path.
- Remove stale mirror references that label Antigravity as Gemini or point Antigravity-only users to `.gemini/`.
- Document manual migration steps for existing consumers that already installed `.agent/` trees.
- Update CHANGELOG with the breaking path movement and the Google transition rationale.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Google docs are still changing quickly after the May 19 launch. | High | Medium | Pin facts to access date; design probes and tests so docs drift is visible. |
| `agy` lacks documented headless mode. | Medium | High | Do not claim CI automation until proven; model CLI support as interactive/TUI first. |
| `.agents/` hard rename breaks users of the existing `.agent/` template. | Medium | Medium | CHANGELOG breakage, migration instructions, no silent dual-write. |
| Antigravity hook payload differs from Gemini/Codex assumptions. | Medium | High | Fixture-capture real Antigravity hook envelopes before declaring full audit support. |
| Gemini enterprise support outlives consumer support. | High | Medium | Preserve `gemini-cli`; document support classes separately. |
| Global path differences between app and CLI cause false confidence. | Medium | Medium | Limit repo install to workspace paths; user-home global installs require an explicit command. |

## 12. References

External sources accessed on 2026-05-20:

- Google Developers Blog, "An important update: Transitioning Gemini CLI to Antigravity CLI", published 2026-05-19: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- Antigravity docs, "Antigravity CLI Overview": https://antigravity.google/docs/cli-overview
- Antigravity docs, "Getting Started with Antigravity CLI": https://antigravity.google/docs/cli-getting-started
- Antigravity docs, "Migrating from Gemini CLI": https://antigravity.google/docs/gcli-migration
- Antigravity docs, "Using AGY CLI": https://antigravity.google/docs/cli-using
- Antigravity docs, "Antigravity CLI Features": https://antigravity.google/docs/cli-features
- Antigravity docs, "Agent Skills": https://antigravity.google/docs/skills
- Antigravity docs, "Plugins": https://antigravity.google/docs/plugins
- Antigravity docs, "Hooks": https://antigravity.google/docs/hooks
- Antigravity docs, "MCP": https://antigravity.google/docs/mcp
- Antigravity docs, "Permissions": https://antigravity.google/docs/permissions
- Antigravity docs, "Subagents": https://antigravity.google/docs/subagents

Repo evidence is cited in sections 3 and 5 with `file:line` references.

## 13. Glossary

| Term | Meaning |
|------|---------|
| Antigravity app | Google's standalone Antigravity desktop/IDE agent platform. |
| Antigravity CLI | Google's `agy` terminal/TUI surface introduced as the Gemini CLI transition target. |
| Gemini CLI | The earlier Google terminal agent surface, still relevant for enterprise/API-key carveouts. |
| Surface | ai-engineering's canonical abstraction combining provider and IDE/runtime integration. |
| Hook bridge | Adapter that normalizes host hook events into ai-engineering canonical audit and gate events. |
| `.agents/` | Current Antigravity workspace customization directory in Google's docs. |
| `.agent/` | Legacy Antigravity workspace customization directory currently generated by ai-engineering. |
| Plugin | Antigravity bundle that can include skills, rules, MCP servers, hooks, and related metadata. |

## 14. Acceptance

- [ ] `/ai-brainstorm --consume antigravity-app-cli-support-brief.md` promotes a spec that resolves the surface identity decision.
- [ ] The spec distinguishes Antigravity app, Antigravity CLI, and Gemini CLI enterprise/API-key support.
- [ ] The accepted plan adds or updates tests before changing mirror generation.
- [ ] New Antigravity installs use the approved workspace layout and do not require `.gemini` assets.
- [ ] `agy` detection and diagnostics are documented and tested.
- [ ] Antigravity hooks emit canonical audit events before audit capability is upgraded.
- [ ] IDE-audit and installer/update validators include Antigravity.
- [ ] CHANGELOG captures breaking path changes and Google transition context.
