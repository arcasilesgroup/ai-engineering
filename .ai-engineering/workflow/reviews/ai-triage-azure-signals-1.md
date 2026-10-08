# Checkpoint 1 · Scoped Azure evidence collection

Goal: enrich the exact selected backlog with paginated comments, dates, direct-parent context and team iterations without inventing urgency or widening scope.

Acceptance: retain each member and literal state; complete discussions or explicit limited coverage; one observation clock; default-deny scoped adapter; authentication/unknown failures fatal; optional permission failures explicit; legacy renderer and GitHub unchanged; source/declarations/embeds agree.

Changed files: collect-azure.mjs/.d.mts, azure-signals.mjs/.d.mts, Azure reference, SKILL.md, tests/triage-azure-signals.unit.spec.ts, tests/triage-azure-signals.integration.spec.ts, FILEMAP.md, PERMISSIONS.md, src/assets.ts, scripts/.embed/ai-triage/scripts payloads, LEARNINGS.md.

Verify: checkpoint 1 verify commands in `.ai-engineering/workflow/checkpoints/ai-triage-azure-signals.json`, followed by normal `bun test`, lint and typecheck. No tenant calls.

## Critic · round 1

1. **F1 · P1/high · open — Canonical project-ID continuation links stop valid pagination.**
   - **Location:** `skills/ai-triage/scripts/azure-signals.mjs:65–67`; `skills/ai-triage/scripts/collect-azure.mjs:691–697`.
   - **Evidence:** Microsoft's [Comments Get Comments example](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/comments/get-comments?view=azure-devops-rest-7.1#examples) requests a project by name but returns `nextPage` with that project's GUID. The URI contract explicitly supports project ID or project name. The existing collector already resolves that name to its GUID for hierarchy context.
   - **Root reason:** `continuation()` requires literal pathname equality rather than validated project identity. A same-organization, same-item continuation using the already verified selected-project GUID is rejected as `contradictory-continuation`; the collector breaks before following the valid opaque token. The current fixtures always construct `nextPage` with the request's project spelling, hiding this normal Azure response shape.
   - **Minimal verification:** Executed a memory-adapter collector with project `Named Project`, a same-project parent that resolves the project GUID, and two one-comment pages declaring `totalCount: 2`. Page 1 uses that verified GUID in `nextPage`, the correct `7.1-preview.4` version, and matching token `second`. Actual: **one** comment read, only comment 1 retained, discussion `partial/contradictory-continuation`. Expected: two reads on the reconstructed original scoped endpoint, both comments retained, complete discussion. Add this name/GUID alias case without accepting an unverified different project or executing `nextPage`.

2. **F2 · P2/medium · open — Metadata failure removes already-returned custom-date evidence from the normalized handoff.**
   - **Location:** `skills/ai-triage/scripts/azure-signals.mjs:186–204`.
   - **Root reason:** The set of context fields is derived exclusively from successful metadata. When metadata is inaccessible or partial, it becomes an empty list and only DueDate/TargetDate survive. An already-returned custom date therefore has neither a delivery entry nor a revision-linked source nor its own coverage gap. Metadata availability should govern recognition/meaning, not silently erase the unrecognized context required by U3 and checkpoint task 7.
   - **Minimal verification:** Executed normalization twice for the same item containing `Custom.DeliveryDate: "2026-10-11T00:00:00Z"`. With complete dateTime metadata, its entry and `field:101:r1:Custom.DeliveryDate` source exist. Changing only metadata to `inaccessible/permission-denied` makes **both disappear**, although the original item still contains the value. Assert that the raw reference/value remain in the normalized evidence as unrecognized context with explicit metadata coverage and next action; no mapping, new custom-field read, or delivery meaning is needed.

3. **F3 · P2/medium · open — Missing or malformed parent importance is labeled complete and sufficient.**
   - **Location:** `skills/ai-triage/scripts/azure-signals.mjs:328–338,347–356`.
   - **Root reason:** Parent normalization validates only ID/revision/fields-container, blindly copies Priority/Severity, and unconditionally assigns `status: "complete"`. Missing importance is silently omitted; an invalid priority value is copied without a gap. Overall sufficiency checks parent status and its dates/delivery, but never the requested parent-importance fields. This defeats the required validated, explicit coverage of missing optional parent enrichment.
   - **Minimal verification:** Executed normalization with complete discussion, item dates/delivery/iteration, and a valid parent revision whose dates/delivery are populated. Omitting parent Priority/Severity yields parent `complete` and overall `sufficient`, with no reason or next action for missing importance. Supplying Priority `"invalid-priority"` still yields `complete/sufficient` and publishes that string as parent priority. Add missing/unset/wrong-type parent-importance cases using integer Priority/string Severity metadata; preserve known parent dates while exposing the importance gap and limited coverage.

### Verification proof

- Normal `bun test`, inherited OS temporary directory unchanged: **1148 pass, 0 fail, 4850 expect() calls, 72 files, 69.27s; exit 0**. No performance threshold or test change.
- `bun run lint` and `bun run typecheck`: **exit 0**; existing warnings only. `git diff --check`: exit 0.
- All four changed/new script/declaration embed payloads are byte-identical to source.
- Normal shipping instructions explicitly require `includeSignals: true`; no normal-flow integration defect found. No tenant/authentication call, implementation edit, or subagent.

**VERDICT: FAIL — F1, F2, F3 open; 1 high, 2 medium.**

## Fixer · round 1

All three findings reproduced and fixed; no disputes.

1. **F1 · fixed.** Root cause was literal endpoint equality in `continuation()`. `skills/ai-triage/scripts/azure-signals.mjs:49–78` now permits only the original path or a same-organization, same-item GUID alias matching the established project identity. `skills/ai-triage/scripts/collect-azure.mjs:607–612,697–699` reuses the hierarchy lookup or obtains the selected project ID once through its scoped existing route, then passes that identity into validation. Every comment request still reconstructs the original selected-project-name endpoint; `nextPage`, including its arbitrary extra query, is never executed. `tests/triage-azure-signals.integration.spec.ts:463` proves both parent/no-parent CLI paths retain both comments and use only the original route; negative continuations reject another GUID or organization. `tests/triage-azure-signals.unit.spec.ts:188` rejects absent, mismatched and malformed project identity.
2. **F2 · fixed.** Root cause was deriving retained context solely from successful metadata. `skills/ai-triage/scripts/azure-signals.mjs:196–238` now retains already-returned custom fields without verified definitions, including raw references/values and revision-linked sources, with `unrecognized` semantics and metadata coverage/next action. Since unavailable metadata cannot identify a field's type, returned `Custom.*` context is retained without guessing whether it is a date. No custom reads, projections or delivery mappings were added. `tests/triage-azure-signals.unit.spec.ts:399` proves inaccessible and partial metadata preserve the custom date and an unknown-type custom field with exact source linkage.
3. **F3 · fixed.** Root cause was container-only validation followed by unconditional parent completeness. `skills/ai-triage/scripts/azure-signals.mjs:244–261,358–382` validates each importance field against integer Priority/string Severity metadata and its value, retains raw linked evidence under `parent.importance`/sources, and publishes only validated `parent.priority`/`parent.severity`. A missing, unset, malformed or unverified field makes the existing parent partial and overall evidence limited. Parent dates and delivery are preserved and still checked independently. `tests/triage-azure-signals.unit.spec.ts:469,482,566` proves either independently missing field, both missing/unset/wrong-type values, unusable metadata, preserved known dates/delivery, and fully valid sufficient coverage. The valid-parent integration fixture now explicitly supplies Severity instead of hiding missing importance.

### Fixer verification

- Tests-first reproduction: **0 pass, 11 fail** across the two synthetic suites before implementation; failures were missing custom context, complete parent status and truncated GUID pagination.
- Checkpoint unit/integration commands, combined without changing selectors: **206 pass, 0 fail, 1,207 assertions, 7 files**.
- Checkpoint GitHub/static/payload/architecture command: **62 pass, 0 fail, 468 assertions, 5 files**.
- Full normal `bun test`, inherited OS temporary directory unchanged: **1,167 pass, 0 fail, 4,990 assertions, 72 files, 73.59s; exit 0**.
- `bun run lint`, `bun run typecheck`, `git diff --check`: **exit 0**, existing warnings only.
- Regenerated with `bun scripts/gen-assets.ts`; all four changed/new script/declaration payloads are byte-identical to source.
- Updated Azure reference, permission boundary, declarations and append-only LEARNINGS L69–L71. No checkpoint JSON edit, commit, tenant/authentication call, agent delegation or TMPDIR override.

**DISPOSITION: F1–F3 fixed; ready for the critic's next round.**

## Critic · round 2

Reviewed the fixer responses against checkpoint 1 only, after reading AGENTS.md,
LEARNINGS Rules and the relevant Azure, coverage, validation, source and test tags.
No disputes, source edits, tenant/authentication calls, or subagents.

1. **F1 · resolved.** `skills/ai-triage/scripts/azure-signals.mjs:49–78`
   permits the documented GUID spelling only against the selected project's
   established identity, organization and item.
   `skills/ai-triage/scripts/collect-azure.mjs:607–612,697–699` establishes that
   identity once or reuses the existing hierarchy lookup. The integration cases
   exercise both parent/no-parent paths through the actual adapter with fake CLI
   output, retain both comments, and reconstruct the original selected route.
   Independent probes also exercised a project name containing spaces, an
   uppercase GUID, an opaque punctuation-bearing token, an unrelated extra query,
   a different GUID and denied identity access. Extra queries were never executed;
   unverified/different GUIDs stopped at one page with explicit partial coverage.
   Unauthorized and unknown identity-read failures remained fatal.

2. **F2 · resolved.** `skills/ai-triage/scripts/azure-signals.mjs:196–238`
   retains the already-returned custom reference names and values when definitions
   are unavailable, without inventing field types or delivery semantics.
   The unit cases prove inaccessible/partial metadata preserves custom-date and
   unknown-field entries, exact revision-linked sources, coverage and next action.
   Independent probes also retained a nested unknown custom value under both
   failure statuses and checked its exact source linkage. No new projection or
   custom-field request was introduced.

3. **F3 · resolved.** `skills/ai-triage/scripts/azure-signals.mjs:244–261,358–382`
   validates parent importance against metadata and values, exposes independent
   field gaps and linked raw sources, and publishes only validated importance.
   The unit cases cover either field missing independently, both missing/unset,
   malformed values, unusable metadata and the fully valid sufficient case.
   Known parent dates/delivery survive missing importance; parent and overall
   coverage remain limited. Independent unavailable-metadata probes confirmed
   that known dates remain complete while unverified importance is not published.
   The declaration describes the new per-field importance coverage.

**New-regression ruling:** No meaningful regression introduced by these fixes
was found in the checkpoint-1 scope. GUID alias acceptance remains bounded by
established identity and never authorizes a server-provided URL; the extra
identity read retains fatal authentication/unknown-failure behavior; raw custom
context never gains delivery meaning; parent validation retains known evidence.
Documentation and all four script/declaration payloads agree with the fixes.

### Round-2 behavior proof

Checkpoint verify commands were run separately, in their declared layer order:

1. Unit: **92 pass, 0 fail, 527 expect() calls, 3 files; exit 0**.
2. Integration: **114 pass, 0 fail, 680 expect() calls, 4 files; exit 0**.
3. GitHub/static/payload/architecture: **62 pass, 0 fail, 468 expect() calls,
   5 files; exit 0**.
4. `bun run lint`: **exit 0**, warnings only.
5. `bun run typecheck`: **exit 0**, warnings only.

- Independent in-memory/fake-CLI adversarial probes: **7 pass, 0 fail; exit 0**.
- First normal `bun test`: **1,166 pass, 1 fail, 4,990 expect() calls, 72 files,
  75.53s; exit 1**. The failing test was the existing chain latency p95 budget,
  outside this checkpoint; no threshold, test, source or environment was changed.
- Immediate normal `bun test` retry: **1,167 pass, 0 fail, 4,990 expect() calls,
  72 files, 74.59s; exit 0**. Both attempts used the unchanged inherited environment.
- `git diff --check`: **exit 0**. All four collector/normalizer script/declaration
  embed payloads are **byte-identical** to source.

**VERDICT: PASS — round 2; 3 resolved, 0 withdrawn, 0 arbitrated, 0 open/new
findings. Behavior gate passed after fixes; the first full-suite latency failure
is recorded above rather than concealed.**

**Changed files for this critic turn:** only
`.ai-engineering/workflow/reviews/ai-triage-azure-signals-1.md`; implementation
`changed_files` remains the checkpoint/fixer set already listed above.
