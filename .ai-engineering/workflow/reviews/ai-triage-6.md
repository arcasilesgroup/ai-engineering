# Checkpoint 6 · Render complete Azure reports safely

Goal: A complete Azure inventory becomes a full `.ai-engineering/triage.html` report using the shared artifact shell, Azure-appropriate sections, escaped untrusted content and validated HTTPS evidence; failures leave the previous report untouched.

Acceptance:
- A complete synthetic Azure inventory renders all rows/counts/linkages using Azure-specific sections in the shared artifact shell.
- All remote text/attributes are escaped; only validated HTTPS links render; authentication values never render.
- Incomplete collection or render/write failure leaves the previous report unchanged.
- Per-item analysis is bounded to five concurrent agents; no live tenant or private report is used in tests.

Changed files:
- `skills/ai-triage/SKILL.md`
- `skills/ai-triage/references/azure-devops.md`
- `skills/ai-triage/scripts/render-report.d.mts`
- `skills/ai-triage/scripts/render-report.mjs`
- `templates/triage.html.tpl`
- `tests/triage-report.unit.spec.ts`
- `tests/triage-report.integration.spec.ts`

Verify:
- `bun test tests/triage-report.unit.spec.ts`
- `bun test tests/triage-report.integration.spec.ts`
- `bun test tests/artifact-layout.spec.ts`
- `bun test tests/artifact-scroll-spy.spec.ts`
- `bun test tests/artifact-brand.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Round 1 findings

- **F1 · P1 — Authentication redaction is bypassed in shell metadata** (`skills/ai-triage/scripts/render-report.mjs:462–477`). `visibleText()` redacts recognized credentials, but `{{repo}}`, `{{title}}`, and `{{meta}}` are substituted with `escapeHtml()` alone. A credential-like value in the untrusted backlog/project/team labels is HTML-escaped but still rendered in the page title/header/footer, contrary to the no-auth-values acceptance. Redact these substitutions too and assert a synthetic credential is absent from the complete report.
- **F2 · P2 — Write-failure preservation has no regression coverage** (`tests/triage-report.integration.spec.ts:217–259`, `skills/ai-triage/scripts/render-report.mjs:485–524`). The previous-report assertions cover only failures before the write callback; none exercise a write failure or prove the default temp-write/rename path preserves existing bytes. Add a synthetic failure test for the write path and verify the previous report remains byte-for-byte unchanged.

## Response

- **F1:** Root cause was shell placeholders using HTML escaping without the shared authentication redaction. All shell/header/footer substitutions now use the same redact-then-escape path as report content. The integration fixture includes hostile markup and a synthetic GitHub-token-shaped value and asserts the markup is escaped and token is absent from the complete report.
- **F2:** The atomic writer now tracks ownership before deleting its temp file, so a failed exclusive open cannot remove another file. Integration coverage injects partial-temp-write and replacement failures through the real writer and checks previous bytes and temp cleanup.

## Round 2 verdict

- **FAIL**
- **F1 · P1 remains open** (`skills/ai-triage/scripts/render-report.mjs:264–273, 282`): Shell placeholders now redact, but a token-shaped `scope.project` is included in generated work-item `href`s. URL validation permits that path and HTML escaping does not redact it. A synthetic GitHub-token-shaped project value appeared in the complete report; reject/redact credential-shaped URL path values and cover this in the complete-report assertion.
- **F2 · P2 resolved**: `bun test tests/triage-report.integration.spec.ts` passed 6/6. Injected temp-write and replacement failures preserve previous bytes and clean owned temps; `ownsTemporaryFile` remains false when exclusive open fails, so cleanup cannot unlink a non-owned temp file.

## Round 3 verdict

- **FAIL**
- **F1 · P1 remains open** (`skills/ai-triage/scripts/render-report.mjs:46–65, 490–503`): URL sanitization detects percent-encoded credentials, but shell metadata still uses raw `visibleText()` redaction. A synthetic `%2567ithub_pat_syntheticToken1234567890` in either `scope.project` or the organization URL appeared in the complete report. Apply the encoded-value check to dynamic metadata and assert both cases.
- **F2 · P2 resolved**: `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 13/13; partial-write and replacement failures still preserve prior bytes and clean owned temps.

## Round 4 verdict

- **PASS**
- **F1 · P1 resolved:** Report text now checks raw and safely percent-decoded values before rendering; unsafe scope metadata is replaced, and work-item links fall back to IDs when organization/project values are unsafe. URL validation rejects malformed escapes, encoded credentials, and encoded sensitive query keys without changing safe link identities.
- Synthetic report tests cover encoded token-shaped values and malformed escapes in both `scope.project` and the organization URL. Safe Azure evidence links remain clickable.
- **F2 · P2 remains resolved.**
- Verification: `bun test tests/triage-report.unit.spec.ts` passed 6/6; `bun test tests/triage-report.integration.spec.ts` passed 11/11.

## Fixer response · F1

- **ROOT CAUSE:** Raw-only authentication redaction did not catch percent-encoded credential-shaped values in Azure organization/project scope.
- **FIX:** Check raw and decoded URL values, omit unsafe links, and render safe IDs/text.
- **LESSON:** Validate untrusted URL values before encoding or rendering them.
- **Focused tests:** Unit 6/6; integration 11/11.
