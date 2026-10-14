# Checkpoint 3 · Regenerate and verify the embedded skill payload

Goal: Generated assets include the shared skill and GitHub provider reference and no retired skill payload.

Acceptance:
- `bun test tests/embed-canon.spec.ts` proves the new skill and provider reference are embedded and the retired skill payload is absent.
- `bun run typecheck` and `bun run lint` pass with restored locked dependencies.
- The GitHub contract test uses explicit narrowing without weakening its assertions.

Changed files:
- `src/assets.ts`
- `tests/triage-github.spec.ts`

Verify:
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Adversarial review · round 1

VERDICT: PASS

Findings: none. The asset map embeds the current `ai-triage` skill and `references/github.md`, with no retired `ai-github-triage` path. The type-narrowing diff adds fail-closed guards and safely narrows regex captures without weakening the contract assertions.
