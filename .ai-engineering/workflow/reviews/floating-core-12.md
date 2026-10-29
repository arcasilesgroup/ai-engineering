# Checkpoint 12 review

## Goal

Fresh installs get 23 core skills and ceremony agents by default; optional skills live in packs and install only when selected, and uninstall removes packs.

## Acceptance

- Init without packs installs 23 skills and every ceremony agent; the ceremony contract passes without packs.
- `ai-code-review` is merged into `ai-verify`; the full ceremony stays in core.
- Uninstall removes installed packs along with core.
- Pack content is moved, not deleted.

## changed_files

- `.snyk`, `FILEMAP.md`, `package.json`
- `scripts/gen-assets.ts`, `scripts/.embed/`
- `skills/ai-code-review/SKILL.md`, `skills/ai-audit-design/`, `skills/ai-design-md-planner/`, `skills/ai-stress-test/`, `skills/ai-triage/`, `skills/ai-verify/SKILL.md`, `skills/ai-verify/VERIFICATION-SETUP-GUIDE.md`, `skills/ai-verify/evals/`, `skills/ai-verify/tiers/`, `skills/ai-visual-recap/`, `skills/ai-writing-behavior/`, `packs/`
- `src/assets.ts`, `src/commands/config.ts`, `src/commands/doctor.ts`, `src/commands/init-shared.ts`, `src/commands/init.ts`, `src/commands/uninstall.ts`, `src/embed.ts`, `src/env.ts`, `src/surfaces/adapters.ts`, `templates/config.toml.tpl`
- `tests/carriers-install.spec.ts`, `tests/ceremony-contract.spec.ts`, `tests/embed-canon.spec.ts`, `tests/fixtures/triage-azure-signals-preview.mjs`, `tests/generated-payload.test.ts`, `tests/init-command.spec.ts`, `tests/npm-manifest.spec.ts`, `tests/skills-eval-score.spec.ts`, `tests/skills.spec.ts`, `tests/triage-azure-signals.integration.spec.ts`, `tests/triage-azure-signals.unit.spec.ts`, `tests/triage-azure.integration.spec.ts`, `tests/triage-azure.unit.spec.ts`, `tests/triage-github.spec.ts`, `tests/triage-report.integration.spec.ts`, `tests/triage-report.unit.spec.ts`, `tests/triage-routing.integration.spec.ts`, `tests/triage-routing.unit.spec.ts`, `tests/uninstall-command.spec.ts`

## Verify

- `bun test tests/skills-eval-score.spec.ts`
- `bun test ./tests/triage-azure-signals.integration.spec.ts ./tests/triage-azure-signals.unit.spec.ts ./tests/triage-azure.integration.spec.ts ./tests/triage-azure.unit.spec.ts ./tests/triage-github.spec.ts ./tests/triage-report.integration.spec.ts ./tests/triage-report.unit.spec.ts ./tests/triage-routing.integration.spec.ts ./tests/triage-routing.unit.spec.ts`
- `bun test tests/init-command.spec.ts`
- `bun test ./tests/adversarial/init-recovery.test.ts`
- `bun test tests/uninstall-command.spec.ts`
- `bun test ./tests/ceremony-contract.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun test tests/agents-canon.spec.ts`
- `bun test tests/carriers-install.spec.ts`
- `bun test tests/npm-manifest.spec.ts`
- `bun test tests/generated-payload.test.ts`

## Round 1 — Critic

### F1 · Major · Open
- **Location:** `src/embed.ts:35-48`; `skills/ai-verify/VERIFICATION-SETUP-GUIDE.md:522`
- **Finding:** `packSkills()` installs each verify-tier skill under `skills/<frontmatter-name>/`, not under `skills/ai-verify/tiers/`. The retained setup guide still tells users to copy `$VERIFY/tiers/2-embedded/second-opinion`, where `VERIFY` is the `ai-verify` skill directory. After this move that source path is absent, so the documented setup command fails; other guide references to `tiers/` are stale for the same reason.
- **Evidence:** `canonSkills(["verify-tiers"])` contains `skills/verify-feature/SKILL.md` but not `skills/ai-verify/tiers/1-standalone/verify-feature/SKILL.md`; existing pack tests assert the flattened install inventory but not the guide's documented paths.
- **Required fix:** Update the guide to use the pack's actual source/install paths and add a test that verifies its referenced paths exist after selection.

**Verdict:** FAIL
**Blocker/major remains:** Major (F1).

## Fixer response · F1 · Round 1
**Fixer:** fixed — updated the copy instructions to the selected `skills/second-opinion/` install and the read references to pack source paths; the focused path contract passes.
**ROOT CAUSE:** The guide still assumed verify-tier files lived under `skills/ai-verify/tiers/` after the pack moved them.
**FIX:** Pointed copy instructions to the selected `skills/second-opinion/` install and source references to `packs/verify-tiers/tiers/`; added a test that resolves every documented pack/install path against the source and selected payload.
**LESSON:** Keep setup paths tied to the pack source and installed inventory, and assert both against the selected payload.
**Verify:** `bun test ./tests/embed-canon.spec.ts -t 'verify setup guide paths'` — 1 pass, 0 fail; `git diff --check` passed.

## Round 2 — Critic

The round 1 fix resolves F1. The setup guide's source references resolve in the embedded `verify-tiers` pack, its installed `skills/...` references resolve in `canonSkills(["verify-tiers"])`, and the `VERIFY`/copy instructions map to the selected `second-opinion` skill. No stale pre-move `tiers/...` paths remain. The embedded-canon, init, ceremony-contract, uninstall, carrier-install, and skills checks pass; no core/optional regression found.

**Verdict:** PASS
**Findings:** None. F1 resolved.
**Blocker/major remains:** No.
