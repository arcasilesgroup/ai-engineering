---
title: "Antigravity App and CLI Support After Gemini CLI Retirement"
status: draft
audience: /ai-brainstorm
branch: spec-147-wave-1
length_estimate: "~220 lines"
authoring_style: "Staff Architect — evidence-anchored, source-current as of 2026-05-22, no implementation"
principles_required: [KISS, YAGNI, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Cross-surface refactor with hard rename, no shims, deterministic tests before mirror regeneration"
mantra: "Support the product Google now ships: Antigravity app plus Antigravity CLI; delete the retired Gemini CLI surface before public release."
---

> READ FIRST. This brief is an intake artifact for `/ai-brainstorm`. It does not implement the change. It answers the operator's question from May 20, 2026 and the follow-up decision on May 22, 2026: after Google's May 19, 2026 announcement that Gemini CLI transitions to Antigravity CLI, should ai-engineering support Antigravity app plus CLI and remove the legacy Gemini CLI surface before public release?
>
> Short answer: no. The repo currently supports the old `gemini-cli` surface better than the replacement Google product. Antigravity exists in the framework, but it is modeled as mirror-only, not wired to `agy`, and generated under legacy `.agent/` paths with Gemini-shaped content. Google's current docs say Antigravity now supports the core primitives we need: `AGENTS.md` workspace context, skills, plugins, MCP, hooks, subagents, permissions, and a terminal CLI. The spec phase should promote Antigravity from advisory mirror to first-class app plus CLI integration and hard-delete `gemini-cli` from this pre-release product line. `GEMINI.md` should not be generated for Antigravity; if the `gemini-cli` surface is removed, `GEMINI.md` leaves the generated contract too.

---

## 1. Vision

ai-engineering should treat Google's coding-agent surface as one Antigravity surface with two runtimes: the desktop app/IDE runtime and the `agy` terminal runtime. This should mirror how the framework thinks about Claude Code or Codex: the terminal/app entry points may differ, but the governance surface is one product contract. Because this framework has not shipped publicly yet, it should not carry a legacy `gemini-cli` surface for the first release; Antigravity becomes the only Google agent integration.

The target state is simple: an operator can enable Antigravity support and receive the right workspace files, hooks, skills, MCP config, permission model, and audit bridge for both the app and CLI without any stale `.gemini`, `GEMINI.md`, npm `gemini`, or `gemini-cli` assumptions leaking into generated installs.

## 2. Scope Boundary

### In scope

| Area | Included work |
|------|---------------|
| Surface model | Model one `antigravity` surface with app/CLI runtime capabilities; do not add a separate `antigravity-cli` surface. |
| Workspace layout | Move generated Antigravity workspace assets to Google's current `.agents/` layout and stop generating new Antigravity installs primarily under `.agent/`. |
| Root context | Use `AGENTS.md` as the Antigravity root context; do not require or generate `GEMINI.md` for the Google integration. |
| CLI integration | Add `agy`/`agy.exe` detection, capability probing, installer checks, docs, and surface diagnostics. |
| Hooks and audit | Map Antigravity hook events into canonical `framework-events.ndjson`; update hook engine and audit capability once verified. |
| Mirror generation | Generate Antigravity-native skills, agents/subagents, plugins, and references without `.gemini` path leakage. |
| Gemini retirement | Remove `gemini-cli` as a generated/supported surface before public release; migrate Google integration docs, registry, tests, templates, and diagnostics to `antigravity` plus `agy`. |
| Validation | Extend mirror, ownership, installer, update, and IDE-audit validators to include the Antigravity layout. |

### Explicitly NOT in scope

| Area | Exclusion |
|------|-----------|
| Implementing this brief | `/ai-brainstorm` must approve the spec before edits. |
| Enterprise Gemini retention | This product will not retain a first-class `gemini-cli` surface for enterprise/API-key carveouts before launch; any future enterprise-only revival requires a separate approved spec. |
| User-home writes by default | The installer should not write `~/.gemini/antigravity-cli/` or `~/.gemini/antigravity/` unless an explicit user-scope command is designed. |
| Solving undocumented headless parity | Antigravity CLI headless/CI parity with Gemini CLI is unclear in public docs; capture as an open decision. |

## 3. Diagnostic Snapshot

Current Gemini CLI support is first-class in the framework registry even though it is now legacy for this product direction: `gemini-cli` has `GEMINI.md`, `.gemini/`, native hooks, and full audit capability (`src/ai_engineering/domain/surface.py:96-103`). The dogfood manifest already enables both `gemini-cli` and `antigravity` under `surfaces.enabled` (`.ai-engineering/manifest.yml:28-36`), but the target state should remove `gemini-cli` from enabled/default surfaces and make Antigravity the only Google agent surface.

Current Antigravity support is explicitly mirror-only and over-declares root context files: the registry points to `GEMINI.md` plus `AGENTS.md`, writes a `.agent/` tree, and declares `hook_engine="none"` plus `audit_capability="none"` (`src/ai_engineering/domain/surface.py:132-140`). The unit contract freezes that posture by asserting Antigravity is mirror-only (`tests/unit/domain/test_surface.py:75-78`). Because the canonical root mirrors carry equivalent payload, Antigravity-only installs should prefer `AGENTS.md` and avoid duplicating the same datum through `GEMINI.md`.

Current installer template maps know Antigravity as a closed enum but still write redundant root context plus the legacy `.agent` tree: root files are `GEMINI.md` and `AGENTS.md` (`src/ai_engineering/installer/templates.py:58-61`), and the tree map copies `.agent` to `.agent` (`src/ai_engineering/installer/templates.py:208-210`). Autodetection also looks for `.agent/`, not `.agents/` (`src/ai_engineering/installer/autodetect.py:222-251`).

Current mirror generation emits Antigravity from the Gemini generator: `scripts/sync_mirrors/core.py:1809-1819` copies Gemini-shaped skills and agents into `.agent/`, and the Antigravity target module describes the surface as "MIRROR-ONLY" with no hook adapter (`scripts/sync_mirrors/antigravity_target.py:1-9`, `scripts/sync_mirrors/antigravity_target.py:26-33`). This is stale against Google's May 2026 Antigravity CLI docs, which now document hooks, plugins, MCP, subagents, and permissions for Antigravity.

Current installer CLI text advertises `antigravity` as a selectable surface (`src/ai_engineering/cli_commands/core.py:105-113`), and manifest parsing accepts it (`tests/unit/config/test_manifest_surface_schema.py:62-71`). However, the public install matrix only tests the older single-provider cases through Gemini, Codex, Claude, and Copilot (`tests/integration/test_install_matrix.py:11-25`), leaving Antigravity install behavior less exercised than first-class surfaces.

Current ownership defaults include `.agent/**` as framework-owned (`src/ai_engineering/config/framework_defaults.py:71-84`), but write-scope classification treats `.claude/`, `.codex/`, `.gemini/`, and selected `.github/` paths as mirrors without including `.agent/` or `.agents/` (`src/ai_engineering/state/capabilities.py:293-298`). That split increases the chance that Antigravity assets are generated but not governed consistently.

Current historical notes record the original Antigravity decision as "mirror-only, no hooks upstream" (`CHANGELOG.md:1481-1483`). Google's public position changed on May 19, 2026: Antigravity CLI is available, supports most Gemini CLI workflow-defining features, and becomes the consumer Google terminal path after a June 18, 2026 cutoff for free/Pro/Ultra Gemini Code Assist serving. The announcement still preserves paid enterprise/API-key access, but this framework's pre-release product decision is to delete the `gemini-cli` surface rather than ship a legacy Google integration.

## 4. Architecture

The spec should deliver a four-layer integration:

1. **Surface registry layer.** Represent Antigravity app and Antigravity CLI capabilities under a single consolidated `antigravity` surface with capability flags (rather than splitting into two separate surfaces). The registry must stop saying `hook_engine="none"` once the hook bridge is proven.
2. **Workspace artifact layer.** Generate Antigravity-native assets under Google's standard `.agents/` workspace layout (skills, agents/subagents, hooks, MCP config, rules, and optional plugin bundle metadata). Use root `AGENTS.md` as the Antigravity workspace context file; do not generate `GEMINI.md` because the `gemini-cli` surface is removed from the target product. Update the dashboard mapping script `session_bootstrap.py` to point to `.agents/` layout instead of legacy `.agent/`.
3. **Runtime bridge layer.** Add an Antigravity hook bridge that normalizes Antigravity events (`PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`) into the canonical hook contract and emits `framework-events.ndjson`.
4. **CLI probe layer.** Detect `agy`/`agy.exe`, capture version and auth-state limitations, warn when the CLI runtime is selected but the binary is missing, and document that auth may remain interactive.

The design should reuse the existing Surface abstraction and template resolver rather than introduce a separate provider axis. The current repo already hard-cut to `surfaces.enabled` as the canonical axis (`CHANGELOG.md:1462-1468`), so Antigravity should fit that model instead of reviving `ai_providers.enabled` or `providers.ides`. The same cleanup should remove `gemini-cli` from `SURFACE_IDS`, installer enums, docs matrices, template maps, mirror inventory, and tests instead of leaving a hidden deprecated path.

## 5. Evidence Catalog

| # | Finding | Evidence |
|---|---------|----------|
| E-1 | Gemini CLI is first-class and audited. | `src/ai_engineering/domain/surface.py:96-103` |
| E-2 | Dogfood enables both Gemini CLI and Antigravity. | `.ai-engineering/manifest.yml:28-36` |
| E-3 | Antigravity registry is mirror-only, no hooks or audit. | `src/ai_engineering/domain/surface.py:132-140` |
| E-4 | Tests freeze Antigravity as mirror-only. | `tests/unit/domain/test_surface.py:75-78` |
| E-5 | Antigravity installer currently emits both `GEMINI.md` and `AGENTS.md`, duplicating root context that should be `AGENTS.md`-only for Antigravity-only installs. | `src/ai_engineering/installer/templates.py:58-61` |
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

### Milestone 1 — Record the single Google surface contract

Acceptance gates:

- The spec records that the new terminal target is modeled under a single consolidated `antigravity` surface with capability flags.
- `SURFACE_IDS` and docs use one naming contract.
- `gemini-cli` is explicitly marked for hard deletion in this spec, not deferred to a later removal spec.

### Milestone 2 — Move Antigravity workspace layout to `.agents/`

Acceptance gates:

- New Antigravity installs generate `.agents/skills/<skill>/SKILL.md`.
- Welcome dashboard path mappings in `.ai-engineering/scripts/session_bootstrap.py` are updated from `.agent` to `.agents`.
- Root `AGENTS.md` is generated when Antigravity is enabled.
- `GEMINI.md` is not generated by the new Google integration because `gemini-cli` is removed from the supported surface set.
- Generated Antigravity content contains no stale `.gemini/`, `GEMINI.md`, `gemini`, or `gemini-cli` references except historical changelog or migration notes.
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
- Gemini CLI is removed from generated support despite Google's enterprise/API-key carveouts; docs explain this as a pre-release product-scope decision and point Google users to Antigravity/`agy`.
- No generated Google/Antigravity install references missing `.gemini` paths, `GEMINI.md`, npm `gemini`, or the retired `gemini-cli` surface.
- Tests cover registry shape, install matrix, mirror sync, hook bridge, doctor/probe behavior, ownership classification, and docs links.
- CHANGELOG records the breaking layout rename if `.agent/` is retired and the hard removal of `gemini-cli`.

## 8. Quality Stamps

| Principle | Application |
|-----------|-------------|
| §10.1 KISS | One Google terminal path for consumers: `agy`; no parallel Antigravity template trees. |
| §10.2 YAGNI | Do not implement unsupported headless/CI behavior until Google documents it or a local probe proves it. |
| §10.5 TDD | Add failing tests for `.agents/` generation, `agy` probing, hook event normalization, and stale `.gemini`/`gemini-cli` references before code changes. |
| §10.6 SDD | Promote this brief through `/ai-brainstorm`; no implementation from the draft. |
| §10.7 Clean Code | Keep Surface as the domain primitive; do not resurrect provider/IDE split logic. |
| §10.8 Hexagonal Architecture | Treat `agy` probing and hook envelopes as adapters behind the existing deterministic governance port. |

## 9. Open Decisions

Settled by the operator on 2026-05-22: Antigravity app and Antigravity CLI are one framework surface, like Codex or Claude Code. The spec must model CLI/app differences as capabilities of `antigravity`, not as separate manifest surface IDs. Also settled on 2026-05-22: because Google is transitioning the consumer CLI path to Antigravity and this framework is still pre-release, remove the `gemini-cli` surface outright before public launch rather than preserving an enterprise carveout.

1. **`.agent` handling:** Should `.agent/` be hard-deleted from generated templates in favor of `.agents/`, or retained only because Google's app still claims backward support? The project no-shim rule prefers a hard rename, but this is distinct from the app/CLI surface identity decision.
2. **Plugin packaging:** Should ai-engineering ship Antigravity customizations as raw `.agents/skills` plus hooks, or as a workspace plugin under `.agents/plugins/ai-engineering/`?
3. **Hook confidence:** What exact Antigravity hook payloads must be fixture-captured before upgrading audit capability from `none` to `full` or `partial`?
4. **Headless mode:** Does `agy` have a non-interactive `-p`/JSON-output equivalent, or should CI automation remain explicitly unsupported?
5. **Enterprise Gemini:** Removed as an open decision for this product release. Any future enterprise-only Gemini support must come through a new approved spec, not this Antigravity migration.

## 10. Migration

This is a breaking integration migration, not a compatibility shim:

- Remove existing `gemini-cli` as a supported/generated surface, including registry entries, default manifest enablement, installer choices, mirror targets, docs matrices, hook scripts, and tests that exist solely for the old surface.
- Introduce or redefine Antigravity support using Google's current `.agents/` workspace convention.
- Hard-rename generated Antigravity template output from `.agent/` to `.agents/` if the spec resolves the layout decision that way.
- Remove stale mirror references that label Antigravity as Gemini or point Google users to `.gemini/`, `GEMINI.md`, npm `gemini`, or `gemini-cli`.
- Document manual migration steps for existing dogfood/internal users that already installed `.agent/` or `.gemini/` trees.
- Update CHANGELOG with the breaking path movement, `gemini-cli` removal, and the Google transition rationale.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Google docs are still changing quickly after the May 19 launch. | High | Medium | Pin facts to access date; design probes and tests so docs drift is visible. |
| `agy` lacks documented headless mode. | Medium | High | Do not claim CI automation until proven; model CLI support as interactive/TUI first. |
| `.agents/` hard rename breaks users of the existing `.agent/` template. | Medium | Medium | CHANGELOG breakage, migration instructions, no silent dual-write. |
| Antigravity hook payload differs from Gemini/Codex assumptions. | Medium | High | Fixture-capture real Antigravity hook envelopes before declaring full audit support. |
| Gemini enterprise support outlives consumer support. | High | Medium | Accept as product-scope tradeoff before public release; document that ai-engineering targets Antigravity only and that future enterprise support requires a new spec. |
| Global path differences between app and CLI cause false confidence. | Medium | Medium | Limit repo install to workspace paths; user-home global installs require an explicit command. |

## 12. References

External sources accessed on 2026-05-20 and re-checked on 2026-05-22:

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
| Gemini CLI | The earlier Google terminal agent surface. Google still has enterprise/API-key carveouts, but ai-engineering will remove it before public release. |
| Surface | ai-engineering's canonical abstraction combining provider and IDE/runtime integration. |
| Hook bridge | Adapter that normalizes host hook events into ai-engineering canonical audit and gate events. |
| `.agents/` | Current Antigravity workspace customization directory in Google's docs. |
| `.agent/` | Legacy Antigravity workspace customization directory currently generated by ai-engineering. |
| Plugin | Antigravity bundle that can include skills, rules, MCP servers, hooks, and related metadata. |

## 14. Acceptance

- [ ] `/ai-brainstorm --consume antigravity-app-cli-support-brief.md` promotes a spec that preserves the single `antigravity` surface decision.
- [ ] The spec distinguishes Antigravity app runtime and Antigravity CLI runtime without retaining `gemini-cli` or creating a separate `antigravity-cli` surface.
- [ ] The accepted plan adds or updates tests before changing mirror generation.
- [ ] New Antigravity installs use the approved workspace layout, emit `AGENTS.md`, and do not generate or require `GEMINI.md` or `.gemini` assets.
- [ ] `agy` detection and diagnostics are documented and tested.
- [ ] Antigravity hooks emit canonical audit events before audit capability is upgraded.
- [ ] IDE-audit and installer/update validators include Antigravity.
- [ ] CHANGELOG captures breaking path changes, `gemini-cli` removal, and Google transition context.
