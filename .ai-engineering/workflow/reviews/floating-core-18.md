# Checkpoint 18 review

## Goal
All installable skill sources live under `skills/<skill-name>`. Evaluation fixtures remain test-only, and generated/package inventories contain installable assets only.

## Acceptance
- Every installable skill and resource has one source under `skills/<skill-name>`; no active `packs/` source fallback remains.
- Evaluation sources and development fixtures live under `tests/fixtures/verify-tiers/evals/` and are absent from generated and installable assets.
- Generated assets and the package include the unified skills root, omit `packs/`, and exclude test-only evaluation fixtures.
- Moved skill links and source references resolve from the unified skills tree.

## Changed files
`.snyk`, `FILEMAP.md`, `package.json`, `packs/`, `scripts/.embed/`, `scripts/gen-assets.ts`, `skills/`, `src/assets.ts`, `src/embed.ts`, `tests/fixtures/verify-tiers/evals/`, `tests/embed-canon.spec.ts`, `tests/generated-payload.test.ts`, `tests/npm-manifest.spec.ts`, `tests/skills-eval-score.spec.ts`, `tests/skills.spec.ts`, `tests/triage-azure.integration.spec.ts`, `tests/triage-routing.integration.spec.ts`, `tests/triage-routing.unit.spec.ts`, `tests/triage-azure-signals.integration.spec.ts`, `tests/triage-report.unit.spec.ts`, `tests/triage-azure.unit.spec.ts`, `tests/triage-azure-signals.unit.spec.ts`, `tests/triage-github.spec.ts`, `tests/triage-report.integration.spec.ts`, `tests/fixtures/triage-azure-signals-preview.mjs`, `LEARNINGS.md`.

## Verify
- `bun test tests/skills-eval-score.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `bun test tests/npm-manifest.spec.ts`
- `bun test tests/skills.spec.ts`
- `bun test tests/triage-azure.integration.spec.ts`
- `bun test tests/triage-routing.integration.spec.ts`
- `bun test tests/triage-routing.unit.spec.ts`
- `bun test tests/triage-azure-signals.integration.spec.ts`
- `bun test tests/triage-report.unit.spec.ts`
- `bun test tests/triage-azure.unit.spec.ts`
- `bun test tests/triage-azure-signals.unit.spec.ts`
- `bun test tests/triage-github.spec.ts`
- `bun test tests/triage-report.integration.spec.ts`
- `bun run build`
- `bun run lint`
- `bun run typecheck`
- `bun test tests/arch.spec.ts`

## Round 1

VERDICT: PASS

No code findings. The embedded payload and package tests' assertions passed; 57 relative Markdown links resolve, and all six moved eval text mirrors match their source bytes. The generator walks `skills/`, not the test fixtures, and materialization copies assets without executing skill content.

Verification note: focused suites were blocked at teardown by pre-existing `tests/.worktree-lifecycle-*` folders (`tests/preload.ts:46`); the arch suite also reports `.DS_Store` outside this checkpoint. Build passed with `TMPDIR` set to `scripts/`; lint and typecheck passed. The checkpoint records all 18 verification commands passing on a clean clone.
