# Checkpoint 2 · Evidence-led recommendations and Azure report

Goal: show Why now, recommendations, native priority, discussion/date/parent/sprint signals and truthful coverage in the existing Azure report.

Acceptance: critical native risk first; explicit current commitments and unresolved blockers may promote; age/count/parent/sprint alone never urgent; chronology and complete evidence required; source-referenced claims validated; original priority/state/GitHub preserved; every inventory member once; safe atomic output; UI matches eight approved state/viewport pairs.

Changed files: azure-signals.mjs/.d.mts, render-report.mjs/.d.mts and embeds, SKILL.md, Azure reference, template, both signals test suites, synthetic preview fixture, FILEMAP, PERMISSIONS, CHANGELOG, LEARNINGS.

Verify: checkpoint 2 commands in the checkpoint JSON, normal bun test, lint and typecheck. Synthetic preview only, no tenant calls. UI gate already passed with no findings.

## Critic · round 1

### 1. F1 · HIGH · Older-created comments edited later are excluded from current-status chronology

**Status:** resolved in critic round 2.

**Location:** `skills/ai-triage/scripts/azure-signals.mjs:537–543,609–616`; publication through `skills/ai-triage/scripts/render-report.mjs:403–406,851–862`.

**Evidence:** Both chronology filters compare only `createdDate` before considering the opposing claim. The blocker path examines modification conflicts only after a resolution passes that creation filter; the commitment path never examines modification order. Consequently, an older-created comment whose current version was edited after the outstanding report is ignored entirely.

**Reproduction:** Use synthetic item #202 revision 6, native Priority 3, observation `2026-10-08T10:00:00Z`, metadata-recognized DueDate `2026-10-09T00:00:00Z`, and complete normalized discussion:

1. Comment #21 v1: “The October 9 package remains unfinished.” Created/modified `2026-10-06T10:00:00Z`. Extract a `commitment` with `isOutstanding: true`, the exact excerpt, `date` equal to DueDate, and sources `field:202:r6:Microsoft.VSTS.Scheduling.DueDate` / `comment:202:21:v1`.
2. Comment #22 v2: “The October 9 package is delivered; no outstanding work remains.” Created `2026-10-05T10:00:00Z`, modified `2026-10-07T10:00:00Z`. Extract the same dated `commitment` with `isOutstanding: false` and its exact field/comment sources.
3. `validateAzureClaims` accepts both. `buildAzureRecommendation` returns `meet-commitment` / `attention`, citing only the old outstanding comment and field.
4. The same failure occurs with blocker comment #23 v1 created/modified October 6 (“Release remains blocked by dependency alpha.”) and same-`issueId` resolution #24 v2 created October 5, modified October 7 (“Dependency alpha is resolved.”): both claims validate, but the result is `unblock` / `attention`.
5. In both cases, pass inventory `[203, 202]`, where #203 has native Priority 1 and no claims, through the actual writer with an in-memory write callback. It publishes once and renders ranked IDs `[202, 203]`, rather than retaining `[203, 202]` while clarifying the contradictory edited evidence.

All excerpts, versions, timestamps and field references come from `normalizeAzureSignals`; no fabricated source or prose inference is involved. The complete discussion contains the explicit counterclaim, but Why now omits it and presents current urgency as established.

**Minimal fix:** Include matching opposing claims whose modification chronology overlaps or follows the outstanding report, even when their creation timestamp is earlier or equal. Preserve both references and request clarification without promotion when edits leave chronology ambiguous; do not simply substitute modification timestamps as unquestionable event order. Cover both blocker and commitment paths with unit and real-writer ordering assertions.

### 2. F2 · HIGH · A withdrawn child dependency still inherits the parent's current commitment

**Status:** resolved in critic round 2.

**Location:** `skills/ai-triage/scripts/azure-signals.mjs:599–604,639–645`.

**Evidence:** Parent commitment admission asks whether *any* `parent-dependency` claim for that parent has `isOutstanding: true` and one overlapping source ID. It never reconciles a later `isOutstanding: false` dependency. The shared parent date alone satisfies the source intersection. The resulting Why now/source IDs also omit the dependency evidence that was essential to admitting the parent commitment.

**Reproduction:** Normalize synthetic child #202 revision 6, native Priority 3, direct parent #901 revision 2 with recognized DueDate `2026-10-09T00:00:00Z`, observation `2026-10-08T10:00:00Z`, and complete discussion:

1. Child comment #25 v1, created/modified `2026-10-06T10:00:00Z`: “Child #202 is required for parent #901 delivery on October 9.” Extract `parent-dependency`, `parentId: 901`, `isOutstanding: true`, citing its exact comment and `field:901:r2:Microsoft.VSTS.Scheduling.DueDate`.
2. Child comment #26 v1, created/modified `2026-10-07T10:00:00Z`: “Child #202 is no longer required for parent #901; parent delivery is independent.” Extract the matching `parent-dependency` with `isOutstanding: false`, its exact excerpt, and the same parent field plus its own comment source.
3. Child comment #27 v1, created/modified `2026-10-08T09:00:00Z`: “Parent #901 delivery remains unfinished and committed for October 9.” Extract a parent `commitment`, `parentId: 901`, `isOutstanding: true`, `date` matching that field, and the exact parent field/comment sources.
4. All three claims pass `validateAzureClaims`. The recommendation nevertheless becomes `meet-commitment` / `attention`; its source IDs are only the parent's DueDate and `comment:202:27:v1`.
5. The actual writer publishes once and ranks this child before native-Priority-1 item #203 (`[202, 203]` from inventory `[203, 202]`), although the explicit later evidence removes the child-to-parent dependency. The parent's unfinished delivery does not make this child outstanding for that delivery.

**Minimal fix:** Determine the current child dependency per direct parent from all matching true/false/unknown claims and their creation/edit chronology before admitting a parent commitment. A later unambiguous withdrawal must remove that promotion; contradictory or edited dependency chronology must produce clarification in native order. Include the actual supporting dependency references in Why now when a current dependency does justify promotion, and add both separate-comment and withdrawal writer tests.

**Checks:** Focused signal unit/integration and embed-canon suites: 223 pass, 0 fail, 1306 assertions. Lint and typecheck exit 0 (existing warnings). All four signal/writer script and declaration embeds match their canonical files byte-for-byte. Normal SKILL usage explicitly requests signals and structured claims; neither finding asks the verifier to determine arbitrary prose truth. Synthetic callbacks only; no tenant reads, remote mutations, source edits or subagents.

**VERDICT:** FAIL · 2 high · 0 medium · open F1, F2.

## Critic · round 2

### Rulings on F1 and F2

- **F1 resolved.** `outstandingChronology` now examines modification intervals before excluding older-created counterclaims (`skills/ai-triage/scripts/azure-signals.mjs:536–558`). Both blocker and commitment regressions exercise older/equal creation times, retain both comment references, and return clarification in native order (`tests/triage-azure-signals.unit.spec.ts:991–1025`). Actual-writer regressions publish once and rank native-Priority-1 item #203 before #202 (`tests/triage-azure-signals.integration.spec.ts:1060–1097`). An unedited counterclaim older than a new report remains excluded.
- **F2 resolved.** Parent admission now reconciles true, false and unknown dependency claims before admitting a commitment, pairs separate comments by delivery identity rather than shared date alone, and includes supporting dependency comments in Why now (`skills/ai-triage/scripts/azure-signals.mjs:561–567,619–653,687–693`). Unit and actual-writer cases cover current support, explicit withdrawal, unknown status and edited withdrawal (`tests/triage-azure-signals.unit.spec.ts:1051–1096`; `tests/triage-azure-signals.integration.spec.ts:1098–1150`). Only the current supported dependency promotes; unambiguous withdrawal retains native order with explicit withdrawal context, while unknown or edited evidence requests clarification. These are semantic claims backed by exact excerpts, not an assumption that a missing status or withdrawal sets every independent reason's confidence to zero.

### 3. F3 · MEDIUM · Historical dependency uncertainty overrides a later explicit confirmation

**Status:** open.

**Location:** `skills/ai-triage/scripts/azure-signals.mjs:628–635,640–644`.

**Evidence:** The new reconciliation includes every unknown claim from `dependencyChronology.superseded` unconditionally at line 630. The following filter correctly excludes an older unknown when a newer unedited positive report confirms the dependency, but cannot remove the same unknown already included by line 630. Adding an obsolete earlier positive report therefore changes the recommendation even though the latest evidence is identical and unambiguous.

**Reproduction:** Use normalized synthetic child #202 revision 6, native Priority 3 / Low severity, direct parent #901 revision 2, metadata-recognized DueDate `2026-10-09T00:00:00Z`, observation `2026-10-08T10:00:00Z`, complete discussion and sufficient coverage. Every comment below is version 1 and unedited, with identical creation/modification timestamps; every claim cites its exact excerpt, `field:901:r2:Microsoft.VSTS.Scheduling.DueDate`, its normalized comment source, `parentId: 901`, `issueId: package-alpha`, and team-reported provenance.

1. Comment #25 on `2026-10-06T10:00:00Z`: “Child #202 is required for parent #901 package alpha delivery on October 9.” Extract `parent-dependency`, `isOutstanding: true`.
2. Comment #26 on `2026-10-07T10:00:00Z`: “As of October 7, whether child #202 is still required for parent #901 package alpha is unknown.” Extract `parent-dependency` with `isOutstanding` omitted. This is an explicit question about the actual relationship, not a numeric confidence default.
3. Comment #28 on `2026-10-08T08:00:00Z`: “Confirmed October 8: child #202 is still required for parent #901 package alpha delivery on October 9.” Extract `parent-dependency`, `isOutstanding: true`.
4. Comment #27 on `2026-10-08T09:00:00Z`: “Parent #901 package alpha remains unfinished and committed for October 9.” Extract `commitment`, `isOutstanding: true`, `date` matching the cited DueDate.
5. All four claims validate. `buildAzureRecommendation` returns `confirm-evidence` / `native` rather than honoring the later explicit confirmation. The actual writer publishes once and ranks `[203, 202]`, where #203 has native Priority 1 and no claims.
6. Control: remove only obsolete comment/claim #25. The same unknown #26, later confirmation #28 and current commitment #27 all validate; coverage remains sufficient. The recommendation is now `meet-commitment` / `attention`, includes #28 and #27, and the writer publishes once with `[202, 203]`.

The counterclaim's creation and modification both precede the renewed confirmation. No edited interval, identity ambiguity, missing read or independent critical signal justifies asking for clarification. The current-status requirement must be independent of whether an obsolete positive statement happened to precede that resolved uncertainty.

**Minimal fix:** Reconcile uncertainty against later matching explicit confirmations before it can trigger the native-order early return, including unknowns collected through superseded pairs. Preserve genuinely current uncertainty and overlapping edits. Add the four-comment case and its three-comment control to unit and actual-writer tests; assert current supporting references, publication count and order.

**Fresh post-fix gates, run sequentially with stop-on-first-failure:** unit 138 pass / 0 fail / 738 assertions; API 150 pass / 0 fail / 982 assertions; static 72 pass / 0 fail / 485 assertions. Total 360 pass / 0 fail / 2205 assertions. Lint and typecheck both exit 0 with existing warnings. All four canonical signal/writer script and declaration payload pairs match their embeds byte-for-byte. F3 was additionally reproduced directly through normalization, validation, recommendation and the actual writer with memory-only callbacks; the existing passing suites do not cover this renewal case. No source edits, tenant calls, subagents, commits or checkpoint changes.

**VERDICT:** FAIL · round 2 · resolved 2 · withdrawn 0 · arbitrated 0 · open F3 (medium).

## Fixer · round 2 · F3

- **Root cause:** Superseded positive/unknown pairs reintroduced historical uncertainty after the later-confirmation filter had excluded it. Their mixed source list also mislabeled unknown status as an explicit withdrawal.
- **Fix:** Reconcile unknown dependencies against the current positive reports with `outstandingChronology`; preserve edited overlaps as clarification. Derive withdrawal references from explicit false updates only.
- **Regressions:** The four-comment renewal and its three-comment control run in both direct unit and actual-writer tests. Each also has an edited-unknown variant whose modification overlaps the renewed confirmation. Assertions cover sufficient coverage, validated claims, current supporting references, one publication, attention/native order and absence of obsolete withdrawal wording.
- **Proof:** Red: 6 pass, 2 fail; green: 8 pass, 0 fail, 86 assertions. Checkpoint non-UI gates: 142 unit, 154 API, 72 static pass, 2291 assertions; lint/typecheck exit 0 with existing warnings. Four canonical script/declaration payload pairs match after regeneration.
- **Full-suite limitation:** Two unchanged normal `bun test` runs, without TMPDIR overrides, each produced 1256 pass, 1 fail, 5589 assertions. Only the existing chain p95 latency test failed (128.30ms and 166.81ms against its unchanged 50ms budget); that unchanged isolated test passes (1 pass, 2 assertions). No performance fix, design/checkpoint edit, commit, tenant call or nested agent.
- **Lesson/files:** L77 records the chronology lesson. This round changes only the canonical signal script and its embed, both signal test suites, LEARNINGS and this thread. F3 is ready for critic verification; the full-suite gate remains pending.

## Critic · round 3

### F3 · MEDIUM · Partially fixed; historical edited uncertainty still overrides a later explicit confirmation

**Status:** open. F1 and F2 remain resolved; this is a remaining branch of F3, not a new finding.

**Location:** `skills/ai-triage/scripts/azure-signals.mjs:631–637`, especially the unconditional `dependencyChronology.conflicts` inclusion at line 635. The added unit/writer renewal cases cover unedited uncertainty and edits overlapping the renewed confirmation, but not an edit completed before that confirmation.

**Verified fixes:** The original unedited four-comment reproduction and its three-comment control now agree: both produce `meet-commitment` / `attention`, include the current confirmation and commitment sources, omit obsolete unknown/withdrawal context, and publish once with `[202, 203]`. An unknown edited through `2026-10-08T08:30:00Z`, overlapping the `2026-10-08T08:00:00Z` confirmation, correctly produces clarification in native order with both current and uncertain references, regardless of historical positive evidence.

**Independent residual reproduction:** Use the same source-backed #202 revision 6 / native P3 child, direct parent #901 revision 2, recognized October 9 DueDate, `package-alpha` identity, complete discussion, sufficient coverage, and October 8 10:00 observation as F3. Keep the four comments and exact excerpts described in round 2, but change only unknown comment #26 to version 2 with creation `2026-10-07T10:00:00Z` and modification `2026-10-07T11:00:00Z`. The renewed confirmation #28 remains unedited at `2026-10-08T08:00:00Z`; current commitment #27 remains unedited at `2026-10-08T09:00:00Z`.

1. All four claims validate against normalized sources; coverage is sufficient. The historical positive #25 and edited unknown #26 enter `dependencyChronology.conflicts`.
2. The new `unknownDependencyChronology` correctly regards #26 as superseded by #28: the confirmation was created strictly after the unknown's last modification.
3. Nevertheless, the unconditional historical conflict inclusion still forces `confirm-evidence` / `native`. The actual writer publishes once with `[203, 202]`, citing obsolete #25 and #26 along with #28 and #27.
4. Remove only obsolete positive #25 and its claim. The same edited unknown #26, current confirmation #28 and commitment #27 all validate with sufficient coverage. The recommendation becomes `meet-commitment` / `attention`, cites only the parent date, #27 and #28, and publishes once with `[202, 203]`.

No edit interval overlaps the renewed confirmation in this variant. The edit makes the earlier positive/unknown relationship ambiguous, not the later explicit confirmation of the current relationship. Historical evidence still changes current advice when the latest evidence is identical and unambiguous.

**Minimal fix:** Reconcile historical dependency conflict pairs against later matching explicit confirmations before retaining them as current uncertainty. Preserve conflicts whose edit intervals overlap or follow the renewed confirmation, and preserve genuinely current unknown/withdrawn status. Add the pre-confirmation edited-unknown variant with and without obsolete positive history to both unit and actual-writer regressions.

**Independent checks:** Focused renewal/F1/F2 chronology run: 27 pass, 0 fail, 198 assertions. Full synthetic signal unit/integration plus embed-canon run: 249 pass, 0 fail, 1499 assertions. Six additional memory-only normalization → claim validation → recommendation → actual-writer probes confirmed the unedited renewal, pre-confirmation edit discrepancy, and overlapping-edit clarification, each with one publication. All four canonical signal/writer script/declaration payload pairs match byte-for-byte.

**Gate separation:** The unchanged full-suite chain p95 blocker remains pending as reported by the fixer; an isolated pass does not clear the full-suite gate. No full-suite retry, threshold changes, production/test source edits, checkpoint edits, commits, tenant calls or subagents in this review. Only this review thread was edited.

**VERDICT:** FAIL · round 3 · resolved 2 · withdrawn 0 · arbitrated 0 · open 1 (F3, medium) · new 0.

## Fixer · round 3 · F3

- **Root cause:** Historical positive/edited-unknown conflict pairs were retained even after a matching unedited renewal began strictly after the historical positive's last modification. The clarification source list also included all dependencies rather than current unresolved evidence.
- **Fix:** The shared chronology now retires earlier matching reports before pairing counterclaims when an unedited same-identity renewal follows their effective last-update instant. Edits overlapping or following a renewal remain ambiguous; missing identities do not establish supersession. Clarification sources come from unresolved evidence, including prior supporting reports only when unknown dependency status is still unresolved.
- **Regressions:** Six memory-only normalization/validation/recommendation probes and six actual-writer probes cover unedited uncertainty, edits completed before confirmation and edits overlapping confirmation, each with and without obsolete positive history. They assert sufficient coverage, current sources, absence of obsolete positive references, promotion/native order and one publication.
- **Proof:** Before the fix: 8 pass, 4 fail, including the exact pre-confirmation discrepancy and stale references during overlap. Renewal plus F1/F2 safety controls: 29 pass, 0 fail, 259 assertions. Lower checkpoint gates: 144 unit, 156 API, 72 static pass (2357 assertions). Lint and typecheck exit 0 with existing warnings; all four canonical script/declaration payload pairs match after regeneration; whitespace check passes.
- **Full-suite gate:** Normal `bun test` started without TMPDIR overrides or budget changes. The command was moved to background; its result is pending and no full-suite pass is claimed.
- **Lesson/files:** L78 records the whole-timeline lesson. This round changes only the canonical signal script and its embed, both signal test suites, the Azure chronology reference, LEARNINGS and this thread. No commit, checkpoint/design/agent changes, tenant calls or nested agents.

## Critic · round 4 · final

### F3 resolved; F1 and F2 remain resolved

- **Root fix verified:** `outstandingChronology` retires matching historical reports before constructing conflict pairs only when an unedited same-identity renewal starts strictly after the report's last modification (`skills/ai-triage/scripts/azure-signals.mjs:536–566`). Dependency uncertainty then passes through that same chronology against the remaining confirmations; clarification references contain unresolved evidence rather than every historical dependency (`:636–659`). This fixes the residual F3 branch at the shared reconciliation boundary, not by hiding its report.
- **Historical uncertainty:** With and without obsolete positive #25, both unedited unknown #26 and #26 edited through October 7 11:00 are superseded by the October 8 08:00 confirmation #28. Direct recommendations promote the current commitment using exactly the parent date, #27 and #28; the actual writer publishes once with `[202, 203]`. Obsolete #25/#26 and withdrawal wording are absent.
- **Overlapping uncertainty retained:** When #26's edit extends through October 8 08:30, both history configurations still require clarification in native order. Why now retains uncertain #26, current #28, commitment #27 and the parent date, but not obsolete #25. The actual writer publishes once with `[203, 202]`. The strict timestamp comparison also preserves an edit ending exactly at the renewal as a conflict; missing issue identity cannot establish renewal supersession.
- **Fresh proof:** The focused renewal and F1/F2 safety run passed **29 tests, 0 failures, 256 assertions** across the signal unit and integration suites. Twelve renewal cases comprise six direct normalization/validation/recommendation cases and six actual-writer cases: eight establish promotion after supersession, four preserve overlapping-edit clarification. The other seventeen retain edited-counterclaim, withdrawal, unknown-status and identity protections. Regression locations: `tests/triage-azure-signals.unit.spec.ts:1098–1163`; `tests/triage-azure-signals.integration.spec.ts:1150–1207`. All four canonical script/declaration payload pairs match their embeds byte-for-byte; whitespace check passes.
- **Gate separation:** This is the final adversarial ruling on F1/F2/F3, not a full-suite pass. The parent independently collects the existing full-suite run in shell421; this reviewer neither reran it nor changed its latency budget. Only this review thread was edited; no source/checkpoint edits, tenant calls or subagents.

**VERDICT:** PASS · round 4 · closed F1, F2, F3 · resolved 3 · withdrawn 0 · arbitrated 0 · open 0 (0 high, 0 medium) · new 0.

**Next:** Collect shell421's full-suite result before recording checkpoint completion.
