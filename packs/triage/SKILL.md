---
name: ai-triage
description: >-
  Reads one GitHub or Azure DevOps backlog, explains what to work on first, and writes a
  complete report without changing remote items. Use for backlog triage, not debugging one
  failure, filing an issue, reviewing a diff, or deciding what to build.
license: Apache-2.0
---

# ai-triage — read the backlog, rank it, touch nothing

Use one provider-specific procedure for one backlog at a time. Do not combine repositories,
organizations, projects, teams, or boards in one report.

## Routing

- When no URL is supplied, list remotes with `git remote` and collect each URL with
  `git remote get-url --all <name>`. Pass the URLs and any explicit URL to the exported
  `resolveTarget` function in `scripts/resolve-target.mjs`; an explicit URL takes
  precedence over remotes.
- If the resolver returns `needs-answer`, ask for the missing or conflicting provider,
  project, team, board, or backlog selection before any work-item read. Keep the answer
  only for that run; do not save it in configuration. Stop on `unsupported`.
- Use only bare allowlisted CLI names from the trusted `PATH`; never use path-qualified
  executables, environment-prefixed commands, or shell wrappers. Do not inspect active
  Azure CLI defaults.
- For a GitHub target, follow the complete [GitHub procedure](references/github.md). It
  preserves the existing issue and pull-request inventory, ranking, evidence, and report.
- For Azure DevOps, follow the [Azure procedure](references/azure-devops.md). Route the
  resolved target through `resolveTargetAndRead`; its callback is the only place to call
  `collectAzureBacklog` with the scoped `createAzureDevOpsInvoker` adapter and
  **`includeSignals: true` on every normal Azure run**. This explicitly enables comments,
  dates, direct-parent context and selected-team iteration evidence; inventory-only
  compatibility defaults are not the triage procedure. If the selected
  scope is not ready or collection is incomplete, stop without writing.
- After collection returns `complete: true`, create exactly one analysis record per
  inventoried work-item ID. Keep no more than five per-item analyses in flight; record
  `UNASSESSED` explicitly when an item cannot be assessed. Pass the complete inventory
  and an `analyzeItem` lookup keyed by item ID to `writeAzureTriageReport` in
  `scripts/render-report.mjs`. It validates and renders everything before writing
  `.ai-engineering/triage.html`; an ambiguity, incomplete inventory, missing/invalid
  analysis, unsafe link, or render failure must leave the prior report untouched. Parent
  and child links are context, never inventory.
- Read each Azure item's `signals` and revision-linked `sources` during analysis.
  Respect complete, absent, partial and inaccessible signal coverage and its next
  action; limited discussion never proves no blockers. Creation/change ages are
  elapsed times, not continuously-open duration or urgency. Native Priority/Severity
  stay unchanged; parent dates and sprint end are context, not inherited deadlines.
- An assessed Azure record must include a nonempty summary and structured `claims`
  from the [semantic extraction contract](references/azure-devops.md#semantic-claims-and-chronology).
  Use exact source IDs/excerpts/values, blocker identity, current-work status and
  matching parent/date linkage; use `claims: []` when unsupported. Do not classify
  by keywords or generate a second priority score. Board evidence is team-reported,
  not code-verified merely because it links to HTTPS. Pair delivery/dependency
  claims by the source-backed issue identity, not shared dates alone. Include
  completed, withdrawn and unknown counterclaims, even in older-created comments
  edited later. Compare creation and edit timestamps together; overlapping edits
  require clarification, not promotion. Reconcile current child dependency before
  using a parent commitment and retain its supporting comment references. Incomplete
  chronology cannot establish a current blocker or commitment. The writer validates claims, preserves
  the native band and derives Recommendation/Why now independently of Analysis.
- Include `summary`, `whyNow`, `confidence` (`HIGH`, `MEDIUM`, or `LOW`), and
  `confidenceBasis` in each assessed record. With signals, the report uses its
  independently derived recommendation rationale and coverage-based confidence;
  without signals, it shows the assessment's `whyNow` and confidence basis. Keep
  those explanations distinct. Recent-comment context is the fixed latest-five
  window; it is separate from the full selected-item discussion used for chronology.
  Direct same-project parents/children are context only, and comments are not
  verified facts.
- Remote GitHub and Azure work-item links open in a new tab; Azure item links target the
  Azure Boards work-item page, not a REST API endpoint.
- The report uses the shared shell in `templates/triage.html.tpl` and follows
  [artifact-design.md](../ai-brainstorm/references/artifact-design.md); preserve the
  existing GitHub report sections and output contract.
- If the provider or target is unclear, ask before reading anything.

## Read-only boundary

Never create, edit, label, assign, comment on, close, merge, review, or delete remote items.
The report is the only output artifact. Keep all inventoried items visible, including any
that could not be assessed; never present a partial inventory as complete.

## Lifecycle

Lane: light
Writes: `.ai-engineering/triage.html` for GitHub and Azure DevOps
Read by: the human deciding what to work on next; ai-brainstorm when an item becomes work
Dies: replaced by the next triage of the same repository
Next: ai-brainstorm when the human picks an item to build; none when the report only closes items

Source: ai-engineering (own), Apache-2.0.
