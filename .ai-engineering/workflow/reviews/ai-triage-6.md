# Checkpoint 6 · Render complete Azure reports safely

Replanned scope: checkpoint 6 now covers Azure-specific report rendering, complete rows/counts/linkage, HTML and URL sanitization, and shared-shell compatibility. Atomic publication/write-failure behavior is split into checkpoint 7; its existing tests still run, but it is no longer an acceptance criterion for this review.

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

## Round 1 after replan · verdict

- **FAIL**
- **F1 · P1 — Bearer credentials in URL query parameters render** (`skills/ai-triage/scripts/render-report.mjs:99–108, 153`). `sanitizeEvidenceUrl("https://evidence.example.test/item?bearer=synthetic-secret")` accepts the URL because `bearer` is absent from the sensitive-query-key check; accepted evidence and relation URLs are rendered as links. Reject bearer-style credential keys and cover the complete report output.
- **F2 · P2 — Dollar replacement tokens corrupt the shared shell** (`skills/ai-triage/scripts/render-report.mjs:546–548`). `replaceAll` interprets replacement tokens in escaped remote labels: a synthetic backlog name of `$`` produced four document roots, titles, and hero headers. Use a replacement callback (or equivalent literal substitution) and test `$&`/`$`` labels against the generated shell.
- Verification: the report unit/integration and shared-shell test set passed 27/27; the two synthetic probes above reproduced F1 and F2.

## Fixer response · F1/F2

- **ROOT CAUSE:** URL validation did not classify `bearer` as a credential query key, and sequential template substitutions rescanned dynamic report content.
- **FIX:** Reject bearer and credential-like query values after URL parsing, including encoded forms. Substitute nav, report content, and shell placeholders once from the original template via a callback.
- **LESSON:** Validate every decoded URL query value, and never run template passes over inserted untrusted text.
- **Focused tests:** Report unit and integration tests cover reserved query keys, encoded bearer values, safe GitHub/Azure links, no URL leakage, and inert placeholder/replacement-token labels with one intact shell.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 20/20.

## Round 2 verdict

- **FAIL**
- **F1 · P1 remains open — Bearer credentials in URL fragments render** (`skills/ai-triage/scripts/render-report.mjs:148–153`). The sanitizer checks query keys in `searchParams`, but the fragment-key check does not include `bearer`; a synthetic `https://evidence.example.test/item#bearer=abcDEF987654321` passes sanitization and appears in the complete report's `href`. Reject bearer-style fragment parameters, including encoded keys, without exposing the rejected URL.
- **F2 · P2 resolved:** Shell substitutions now run once against the original template via a callback; the integration fixture confirms literal placeholder/replacement tokens and a single intact shell.
- Verification: report and shared-shell tests passed 30/30; a synthetic complete-report probe reproduced F1. No Azure/GitHub access.

## CP6 fresh adversarial review

- **FAIL**
- **F3 · P1 — Credential markers bypass URL checks** (`skills/ai-triage/scripts/render-report.mjs:46–65, 99–108, 148–153`): fragment `bearer=` (including `%62earer=`), query values `view=token%3D...`, and path `token%3D...` are accepted into `href`; reproduced through complete report rendering. Reject credentials in all URL components after decoding.
- **F4 · P1 — Generic token assignment leaks from shell metadata** (`skills/ai-triage/scripts/render-report.mjs:46–65, 163–178, 498–533`): `backlogName: "token=synthetic-secret"` appears four times in generated shell/report because redaction omits bare `token=`. GitHub-PAT-shaped project metadata and encoded scope credentials are redacted correctly.
- **F5 · P2 — Unsafe evidence does not fall back to safe text** (`skills/ai-triage/scripts/render-report.mjs:244–254, 287–294`): invalid evidence/relation URLs throw before rendering instead of showing the safe label/ID without an anchor; previous report is preserved, but the requested fallback behavior is absent. Scope-derived item links do fall back to ID text.
- **PASS checks:** Template substitution is one-pass; safe Azure/GitHub URLs remain intact; atomic write/replacement failure tests preserve previous bytes and clean the owned temp. Focused unit/integration tests: 20/20 passed.

## Fixer response · CP6 F3-F5

- **ROOT CAUSE:** URL validation did not recognize generic `token=`/`bearer=` assignments after decoding, metadata redaction omitted bare `token=`, and invalid evidence/relationship URLs aborted normalization.
- **FIX:** Redact generic token and bearer assignments everywhere dynamic text is rendered; reject them in URL components; render unsafe or unvalidated evidence/relationship references as escaped plain-text labels.
- **LESSON:** Apply credential detection after decoding at every output boundary, and make unsafe links a display fallback rather than a report failure.
- **Synthetic coverage:** Encoded fragment keys/values, metadata assignments, malformed evidence, unsafe and unvalidated relationships; safe HTTPS links remain checked.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (156 assertions).

## Final review · CP6

- **VERDICT: FAIL**
- **Resolved: 9 · Open: 1** (prior report-safety findings and CP6 F3/F5 resolved; F4 remains incomplete).
- **Open F4 residual · P1 — bare `auth=` credentials leak through dynamic text** (`/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/ai-triage/skills/ai-triage/scripts/render-report.mjs:50,163-176,520-528`): a synthetic backlog name `Synthetic backlog auth=synthetic-secret` renders its value in the complete report. The assignment redactor recognizes `authorization` but not `auth`; `visibleText` therefore falls through to HTML escaping. Add `auth`/`auth[_-]?token` aliases and a full-report regression.
- **F3 resolved:** URL credentials/assignments are rejected after repeated percent decoding across URL components, query, and fragment.
- **F5 resolved:** unsafe/malformed evidence falls back to escaped label text; unsafe or unvalidated relationships fall back to plain text without aborting the report.
- **Prior safety checks resolved:** scope/link redaction, safe Azure/GitHub HTTPS links, one-pass shell substitution, and failed atomic-write preservation verified.
- **Verification:** focused unit and integration tests passed 24/24 (156 assertions); an in-memory synthetic render probe confirmed the open leak. No live provider calls or private report used.

## Fixer response · final review F4 (Round 1)

- **STATUS: FIXED**
- **ROOT CAUSE:** The credential-assignment redactor recognized `authorization` but not the `auth` alias.
- **FIX:** Redact `auth`, `authtoken`, `auth_token`, and `auth-token` assignments in dynamic report text.
- **LESSON:** Treat short authentication aliases as credentials at every rendered-text boundary.
- **Regression:** The complete synthetic report asserts that `auth=` backlog metadata and `auth_token=` team metadata are redacted.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (157 assertions). No live provider calls or private report used.

## Fixer response · final review F4 residual (Round 2)

- **STATUS: FIXED**
- **FIX:** Added exact assignment aliases for `oauth_token`, `x_auth_token`, and `client_auth` (also accepting hyphen separators); no broad auth-substring matching.
- **Regression:** The complete synthetic report asserts these three secret values are absent while benign `authored_by`, `client_author`, and `oauth_provider` metadata remains unchanged.
- **LESSON:** Match credential aliases as complete assignment keys, not arbitrary auth-containing substrings.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (163 assertions). No live provider calls or private report used.

## Fixer response · final review F4 residual (Round 3)

- **STATUS: FIXED**
- **FIX:** Added the exact `oauth2[_-]?access[_-]?token` assignment alias; no broad OAuth/auth matching.
- **Regression:** The complete synthetic report asserts the `oauth2_access_token` value is absent and preserves the benign near-match `oauth2_access_policy` alongside existing benign metadata.
- **LESSON:** Add credential variants as exact key patterns and pin neighboring benign keys against over-redaction.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (165 assertions). No live provider calls or private report used.

## Round 4 final review

- **VERDICT: FAIL**
- **Round 4 resolved/open: 1/1** — `oauth2_access_token` is now redacted in the complete report; `oauth2_access_policy` and the existing benign near-match fields remain intact.
- **Open F6 · P1 — Compound credential assignment keys still leak** (`/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/ai-triage/skills/ai-triage/scripts/render-report.mjs:50`): synthetic `scope.team` values `azure_devops_token=synthetic-secret` and `bearer_token=synthetic-secret` both appear in the generated report. The matcher covers exact aliases but misses these credential keys when prefixed.
- **Verification:** report unit/integration tests passed 24/24 (165 assertions); synthetic full-report probes confirmed both residual leaks. No live calls; no source edits.
- **Cumulative:** 12 resolved · 1 open.

## CP6 resumed adversarial review · Round 1

- **VERDICT: FAIL**
- **Resolved/open: 1/1** — F6 is resolved: `azure_devops_token=` and `bearer_token=` are redacted in the complete report; neighboring policy/owner metadata remains visible.
- **F7 · P1 — Common PAT assignment aliases still leak** (`skills/ai-triage/scripts/render-report.mjs:50`): synthetic `personal_access_token=synthetic-personal-token`, `ado_pat=synthetic-ado-pat`, and `azure_devops_ext_pat=synthetic-extension-pat` all appeared in a full generated report.
- The generic `access_token` match has no word boundary after the underscore in `personal_access_token`; `pat` aliases are not recognized. `personal_access_token_owner` remained visible, so any fix must preserve benign near-matches.
- **Verification:** unit and integration tests passed 24/24 (169 assertions), but do not exercise these aliases. Synthetic in-memory report probe only; no live provider calls.
- No other high-confidence safety defects found in this slice.

## Fixer response · CP6 F7 (Round 1)

- **STATUS: FIXED**
- **ROOT CAUSE:** The exact assignment matcher recognized `access_token` only at a word boundary and omitted the `ado_pat` and `azure_devops_ext_pat` aliases.
- **FIX:** Added those three exact assignment-key patterns at the shared authentication-redaction boundary; keys must still be followed by `=` or `:`, preserving benign suffixed metadata.
- **REGRESSION:** Full synthetic report coverage verifies all three secret values are absent and `personal_access_token_owner`, `ado_pat_owner`, and `azure_devops_ext_pat_owner` remain unchanged.
- **LESSON:** Match credential aliases as complete assignment keys and retain neighboring safe metadata in full-output assertions.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (175 assertions); `git diff --check` passed. Synthetic values only; no live provider calls.

## CP6 resumed adversarial review · Round 2

- **VERDICT: FAIL**
- **Resolved/open: 1/1** — F7 is resolved: the complete report redacts `personal_access_token=`, `ado_pat=`, and `azure_devops_ext_pat=`; the tested owner/policy near-matches remain visible.
- **F8 · P1 — Other common token assignments still leak** (`skills/ai-triage/scripts/render-report.mjs:50`): a full synthetic report retained `azure_devops_pat=synthetic-azure-pat`, `github_token=synthetic-github-token`, and `system_access_token=synthetic-system-token`.
- The full report also preserved benign `azure_devops_pat_owner` and `github_token_owner` metadata.
- **Verification:** focused unit/integration tests passed 24/24 (175 assertions), but omit these keys. In-memory synthetic report probe only; no live provider calls.
- No other high-confidence safety defects found in this slice.

## Fixer response · CP6 F8 (Round 2)

- **VERDICT: FIXED**
- **ROOT CAUSE:** The shared authentication-assignment redactor omitted `azure_devops_pat`, `github_token`, and `system_access_token`.
- **FIX:** Added those exact aliases at the shared rendering boundary and extended the complete synthetic-report test to assert all three values are absent while preserving benign `*_owner` metadata.
- **LESSON:** Cover provider credential aliases at the shared output boundary while asserting neighboring metadata remains visible.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (181 assertions); `git diff --check` passed.
- Synthetic credentials only; no live Azure/GitHub calls and no credentials written or emitted.

## CP6 resumed adversarial review · Round 3

- **VERDICT: FAIL**
- **Resolved/open: 1/1** — F8 is resolved: the complete report redacts `azure_devops_pat=`, `github_token=`, and `system_access_token=`; corresponding `*_owner` metadata remains visible.
- **F9 · P1 — Other common token assignment aliases still leak** (`skills/ai-triage/scripts/render-report.mjs:50`): full synthetic reports retained `api_token=`, `github_pat=`, `gh_token=`, `azdo_pat=`, `ado_token=`, and `azure_pat=` values.
- The complete-report integration tests pass but do not cover these aliases.
- **Verification:** focused unit/integration tests passed 24/24 (181 assertions); separate in-memory synthetic report probe reproduced each leak and confirmed owner metadata remains visible. No live provider calls.
- No other high-confidence safety defects found in this slice.

## Fixer response · CP6 F9 (Round 3)

- **VERDICT: FIXED**
- **ROOT CAUSE:** The shared assignment redactor depended on a finite list of provider-specific aliases.
- **FIX:** Normalize assignment keys and redact credential-bearing suffix families (`token`, `pat`, `auth`, `secret`, and related terms), rather than matching arbitrary `token` substrings; full-report regressions cover F9, prior aliases, and safe owner/count/policy metadata.
- **LESSON:** Classify credential assignment keys by semantic suffix, not a growing provider alias list or arbitrary keyword containment.
- **Verification:** `bun test tests/triage-report.unit.spec.ts tests/triage-report.integration.spec.ts` passed 24/24 (194 assertions); `git diff --check` passed.
- Synthetic values only; no live Azure/GitHub calls and no credentials written or emitted.

## CP6 resumed adversarial review · Round 4 (final)

- **VERDICT: FAIL**
- **Resolved/open: 1/1** — F9 is resolved: all 14 reported aliases are absent from the full report, and tested owner/count/policy metadata remains visible.
- **F10 · P1 — Established credential forms still leak** (`skills/ai-triage/scripts/render-report.mjs:46–51`): synthetic full-report probes retained `SYSTEM_ACCESSTOKEN=`, `private_key=`, `access_key=`, and `secret_access_key=` values.
- `SYSTEM_ACCESSTOKEN` has no separator for the semantic suffix matcher to recognize; the matcher also lacks a generic `key` credential suffix.
- **Verification:** focused unit/integration tests passed 24/24 (194 assertions), but omit these forms. In-memory synthetic probes only; no live provider calls.
- Final-round review leaves F10 open; no other high-confidence defects found.
