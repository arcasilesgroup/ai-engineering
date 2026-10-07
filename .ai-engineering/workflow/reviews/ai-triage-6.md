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
