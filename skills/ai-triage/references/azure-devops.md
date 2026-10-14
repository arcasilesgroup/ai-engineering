# Azure DevOps Services collection

This collector reads one explicitly selected team backlog level. It never uses
WIQL, `az boards query`, pagination guesses, or relationships to widen inventory.
Only the selected backlog's work-item references form the inventory; parent and
child relations on returned items remain context.
The documented backlog-membership operation has no continuation, `$top`, or
`$skip` parameter; do not invent paging or substitute WIQL.

## Scoped read allowlist

Every request carries the resolved organization, project, team/backlog where the
route requires them, and API version `7.1` except comments (`7.1-preview.4`).
The collector permits only these
method/route pairs:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/{project}/{team}/_apis/work/backlogs` | Find the selected level and its `workItemCountLimit`. |
| `GET` | `/{project}/{team}/_apis/work/backlogs/{backlogId}/workItems` | Read exact membership in the selected level. |
| `GET` | `/_apis/projects/{project}` | Resolve the selected project ID to scope linked work-item URLs. |
| `POST` | `/{project}/_apis/wit/workitemsbatch` | Read selected-item details and hierarchy relations in batches of at most 200 IDs. |
| `POST` | `/{project}/_apis/wit/workitemsbatch` | Read type, state, and title for directly related items as context only. |
| `POST` | `/{project}/_apis/wit/workitemsbatch` | Separately enrich distinct same-project direct parents with metadata-validated standard priority, severity and date fields. |
| `GET` | `/{project}/_apis/wit/workItems/{selectedItemId}/comments` | Read every selected item's discussion for signal chronology, at `7.1-preview.4`. |
| `GET` | `/{project}/_apis/wit/workItems/{workItemId}/comments` | Read the fixed latest-five context window for selected items and verified same-project direct parent/child relations, at `7.1-preview.4`. |
| `GET` | `/{project}/_apis/wit/fields` | Read project field definitions once. |
| `GET` | `/{project}/{team}/_apis/work/teamsettings/iterations` | Read the selected team's configured iterations once. |

These routes follow the Azure DevOps Services REST API 7.1 documentation:
[backlog levels](https://learn.microsoft.com/en-us/rest/api/azure/devops/work/backlogs/list?view=azure-devops-rest-7.1),
[backlog-level membership](https://learn.microsoft.com/en-us/rest/api/azure/devops/work/backlogs/get-backlog-level-work-items?view=azure-devops-rest-7.1),
[project details](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/get?view=azure-devops-rest-7.1),
and [batch work-item reads](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-items-batch?view=azure-devops-rest-7.1).
Comment reads use the documented
[Get Comments](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/comments/get-comments?view=azure-devops-rest-7.1)
route at API version `7.1-preview.4`, with the fixed query `$top=5&order=desc`.
The fixed context request is `$top=5&order=desc`. In inventory-only mode it
provides each selected item's recent window; in signal-enabled mode selected
items also receive a separate full, paginated discussion read for chronology.
When that full read is partial, the collector uses the fixed latest-five request
for recent context rather than labeling an oldest-first partial page as newest.
The context read also covers verified same-project direct parents and children,
without adding related items to the inventory. Optional related-comment failures
remain explicit coverage gaps. The collector keeps only comment ID, plain-text
body, and creation date in recent context; identities and links from comment
metadata are discarded. Comment text is escaped and credentials are redacted
before it appears in the local report.
The backlog-membership response stores each work-item ID at
`workItems[].target.id`; the collector reads that documented shape. Batch reads
request `$expand: "Relations"` so each story or bug carries its parent/child links;
without it the API returns no relations. The collector verifies the linked URL's
project ID against the selected project before reading type, state, and title for
same-project relation targets, so Feature parents and Task children are identifiable.
These linked items are context only, not additional backlog inventory or analysis rows.
The batch API documents a maximum of 200 IDs and `Fail`/`Omit` error policies; this
collector always requests `Fail` and rejects a response whose IDs do not exactly match
the requested mandatory batch. A missing optional parent detail is instead an explicit
coverage gap; it never removes the already validated minimal hierarchy context.

Additional documented reads:
[comments](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/comments/get-comments?view=azure-devops-rest-7.1),
[project fields](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/fields/list?view=azure-devops-rest-7.1),
and [team iterations](https://learn.microsoft.com/en-us/rest/api/azure/devops/work/iterations/list?view=azure-devops-rest-7.1).

## Completeness and states

The backlog-level `workItemCountLimit` is the only completion boundary. A
missing, invalid, or unknown limit, or a reference count at or above that limit,
raises an incomplete-inventory error and returns no success inventory. Below a
known limit, every selected backlog member is retained, including items in completed
or removed states; no state-based filtering or normalization is applied.

State values come directly from each work item's `System.State` field. Azure boards
can use different state names, so the collector preserves the exact value rather than
classifying it through shared state metadata.

## Triage priority

The report ranks from Azure's standard `Microsoft.VSTS.Common.Priority` and
`Microsoft.VSTS.Common.Severity` fields, not from workflow state or a generated
assessment score. Native Priority 1 is highest and 4 is lowest; Severity maps
Critical, High, Medium, and Low to P0, P1, P2, and P3. The strongest populated
signal determines the displayed P0-P4 band; items with neither recognized field
are P5 and appear last. This is a deterministic ordering aid, not a replacement
for a team's configured board policy. Work-item state stays verbatim and does
not imply urgency: an advanced state can mean work is closer to completion, not
that it is more important.

The native band is never rewritten by analysis. For assessed items the separate
recommendation order is native P0 first, then one attention group for validated
current blockers or outstanding commitments overdue, today or within seven UTC
calendar days, then native order. Both native band and original inventory order
break ties within each group. Explicit UNASSESSED items retain inventory order
at the end. With no grounded current reason, this is the legacy native ordering.
Critical risk and calendar commitments remain visible as competing reasons.

## Scoped CLI adapter

Use `createAzureDevOpsInvoker` from `scripts/collect-azure.mjs` as the collector's
request adapter. It issues the exact allowlisted REST URLs through `az rest`, with
the explicit Azure DevOps resource ID
`499b84ac-1321-427f-aa17-267ca6975798`, API version `7.1`, and the selected
organization, project, team, and backlog. It uses API version `7.1-preview.4`
only for comments; every other route uses API version `7.1`. The adapter
validates every request
against that scope before invoking `az`; it passes arguments directly without a
shell and sends the batch body as JSON. `az rest` uses the existing CLI sign-in
and does not write or persist credentials.

Do not use `az devops invoke` for these routes: the extension selects a resource
by area and resource name, but Azure registers two `work/backlogs` locations
(list and membership); the CLI selects the list location even when given a
backlog ID. That returns backlog metadata rather than `workItems`. `az rest`
uses the documented route directly, avoiding that ambiguous CLI mapping.

No credentials, active CLI defaults, or Azure responses belong in this
repository. Authentication, unknown CLI failures and mandatory reads stop collection;
no partial inventory is reported as complete. Optional reads downgrade only recognized,
anchored HTTP reason prefixes: Forbidden is inaccessible, known 429/5xx reasons and
buffer/timeout interruptions are partial. An exit code is not an HTTP status, and a
keyword inside an error body is not a permission decision. Raw stderr/bodies are discarded.
The CLI adapter uses a 60-second timeout and a 20 MiB output limit per call.

## Signal collection and compatibility

Normal Azure triage always opts in:

```js
const inventory = await collectAzureBacklog({
  ...scope,
  invoke: createAzureDevOpsInvoker(scope),
  includeSignals: true,
});
```

For existing API callers, omitting both `includeSignals` and `observedAt` preserves
the exact inventory-only output and legacy reads. Supplying `observedAt` explicitly
also enables signals for a reproducible run; `includeSignals: false` overrides that
choice. Without an injected clock, enriched runs take one observation timestamp
for the entire inventory. No new persistent configuration or field mapping exists.

Enrichment starts only after membership, selected details and mandatory hierarchy
context are proven complete. `complete: true` still means inventory completeness,
not evidence completeness. Each selected item gains `signals`, with `observedAt`,
`sources`, per-signal coverage and overall `sufficient`, `limited` or
`not-assessable` coverage. Parent evidence remains separate and cannot add rows.

- **Discussion:** request `$top=200`, `order=asc`, `includeDeleted=true`; 200 is the
  requested page size, not a documented service maximum. Follow opaque tokens via
  `URLSearchParams` on the same validated selected-item route. Never execute
  `nextPage`. Its project-name or project-GUID route must match the selected
  organization and item; accept a GUID only after the selected project's identity
  read verifies it (reuse the hierarchy lookup, otherwise read it once).
  Counts, item linkage, id/commentId aliases, versions, dates, unique
  IDs/tokens and stable totals must reconcile at a terminal page. Tombstones count
  toward totals but retain no body/source claim. No authors, mentions or reactions
  are retained. Incoherent/interrupted reads retain known evidence as partial.
  A terminal reconciled zero alone establishes absent discussion.
  Buffering beyond 20 MiB or 1,000 pages yields explicit partial coverage.
- **Ages:** `System.CreatedDate` and `System.ChangedDate` retain raw values and
  revision-linked sources. Whole elapsed days use timezone-qualified instants,
  not local calendar subtraction. Missing, unset, invalid, future and
  changed-before-created dates have distinct reasons and next actions. These are
  age since creation and time since last change, never time continuously open,
  reopen history, or urgency.
- **Delivery:** only `Microsoft.VSTS.Scheduling.DueDate` and
  `Microsoft.VSTS.Scheduling.TargetDate` with `dateTime` metadata gain due and
  forecast semantics. Unsupported, unreturned, unset and invalid values stay
  distinct. Returned custom dates and StartDate/FinishDate remain unrecognized
  context without delivery meaning; display names never decide semantics.
  Unavailable metadata cannot grant date meaning or erase returned custom
  reference names, raw values and revision-linked sources. Without a definition,
  retain returned `Custom.*` fields as unrecognized context with explicit metadata
  coverage and a next action; do not guess their types.
- **Direct parent:** reuse selected parents; cache other distinct same-project
  direct parents in separate batches of at most 200. The projection starts with
  type/state/title, then admits only metadata-validated Priority, Severity,
  CreatedDate, ChangedDate, DueDate and TargetDate. No custom projection, ancestor,
  sibling, cross-project or child-calendar read is allowed. Parent importance
  validates integer Priority and string Severity against metadata and exposes
  each field's coverage under `parent.importance`. Missing, unset, malformed or
  unverified importance limits parent and overall coverage without discarding
  known parent dates or delivery context. Only validated importance populates
  `parent.priority`/`parent.severity`; raw values remain in linked sources.
  Priority and dates are context, never automatically inherited.
- **Iteration:** match exact `System.IterationPath` within the one selected team's
  cached list; no name, integer/UUID ID or current-sprint fallback. Only explicit
  `value`/`values` list envelopes are accepted, without conflicting lists or
  duplicate matches. UTC-midnight start/finish dates become inclusive calendar
  boundaries. Unmatched paths, unset dates and invalid/reversed ranges are gaps,
  not deadlines. No `$timeframe`, guessed paging or alternate-team discovery.

Stable source IDs are `field:{itemId}:r{revision}:{referenceName}` and
`comment:{itemId}:{commentId}:v{version}`, plus `iteration:{iterationId}` for
the exact path-matched planning metadata and original UTC timestamps.
Preserve their raw values, timestamps
and linkage when explaining evidence. Deleted content never supplies a source.
Limited discussion cannot prove that a blocker remains active or that none exists.
Each absent, partial or inaccessible signal records a reason and concrete next
action; it must not be silently replaced with an empty, sufficient assessment.

## Report handoff

Only after `collectAzureBacklog` returns `complete: true`, analyze every returned work
item exactly once. Keep no more than five analyses in flight. Each analysis must return a
record for that item's ID, or an explicit `UNASSESSED` record; a missing or invalid record
stops the run.

Pass the complete inventory and its per-item analysis records to
`writeAzureTriageReport` in `scripts/render-report.mjs` through an `analyzeItem` lookup
keyed by work-item ID. Each assessed record has `status: "ASSESSED"`, a nonempty
`summary`, a `claims` array (empty when nothing is supported), `whyNow`,
`confidence` (`HIGH`, `MEDIUM`, or `LOW`), and `confidenceBasis`. An unavailable
assessment is explicitly `{ status: "UNASSESSED" }`; missing records are fatal.
The writer calls `validateAzureClaims` and `buildAzureRecommendation` from
`scripts/azure-signals.mjs` before rendering.
With signals, the report derives Recommendation, its Why now rationale, and
confidence from validated signals and their coverage, independently of
assessment prose; without signals it displays the assessment's Why now and
confidence basis. Use recent comments on the item and direct parent/child context
to explain timing or dependencies, but distinguish a comment's claim from
verified facts. The writer uses the shared
`templates/triage.html.tpl` shell and the Azure-specific scope, ranked work-item,
type/state and method sections. Each ranked item's expanded details renders its parent,
the backlog item and any children as a hierarchy, with connectors and one indentation
level per parent-to-item and item-to-child edge; related items remain context and never
become inventory rows. Expanded details show the full selected-item discussion
and chronology in the Discussion signal row, separately from the fixed latest-five
context for the selected item and each verified direct related parent or child.
Recent context includes dates, available counts, and explicit partial/inaccessible
status.
Read descriptions as analysis input, but do not display a separate
Description row. The Analysis summary must explain what the item changes, why it matters,
and the next decision in plain language. “Why now” names the concrete timing signal;
confidence has a qualitative level and a short evidence-based reason. Use `**bold**` for key decisions, `*italics*`
for caveats, backticks for code or paths, and `[label](https://...)` for verified links
when useful; use blank lines to separate paragraphs. Keep formatting inline and
non-nested. `renderAnalysis` escapes raw HTML, redacts credentials, and renders only
these formats; unsafe analysis links fail the render and leave the prior report untouched.
The writer finishes validation and rendering before
atomically replacing `.ai-engineering/triage.html`; ambiguity, collection, analysis,
validation, rendering or writing failures must leave an existing report byte-for-byte
unchanged. Never include authentication fields or values in the analysis records or report.

Work-item and relationship links use the Azure Boards work-item page
(`/{project}/_workitems/edit/{id}`), never the REST API URL. All links leaving the
report open in a new tab with `rel="noreferrer noopener"`. The ranked row shows
the work-item type and exact state; expanded details show the parent, backlog
item, and child links as a hierarchy.

## Semantic claims and chronology

Extract claims from meaning, not keywords, comment counts, model scores, state
names or parent rank. Analysis explains the work once; Why now is separately
derived from validated structured claims and normalized facts, not copied prose.
Every claim uses the actual item's `signals.sources` IDs, the exact supporting
comment `excerpt` and/or field `value`, and `provenance`. Do not invent quotations,
versions, dates or parent IDs. Claims support these closed types:

| Type | Required support |
| --- | --- |
| `blocker` | Exact comment excerpt describing a specific unresolved dependency; stable `issueId` identifies it. |
| `blocker-resolved` | Exact comment excerpt explicitly resolving that same `issueId`. Unrelated resolutions do not count. |
| `commitment` | Exact comment excerpt establishing delivery status and a cited metadata-recognized DueDate/TargetDate equal to `date`; use a stable `issueId` for that specific delivery. `isOutstanding` is true, false or omitted when unknown. |
| `parent-dependency` | Exact child comment excerpt requiring, withdrawing or questioning this child's dependency for its direct `parentId`; cite the actual parent's field source and use the matching delivery `issueId`. Set `isOutstanding` only when supported. |
| `context` | Exact excerpt or field value describing evidence without implying urgency. Parent sources require the matching `parentId`. |

Example for one synthetic item (substitute only actual collected IDs and text):

```js
{
  status: "ASSESSED",
  summary: "Preparation makes the work usable by the delivery stage.",
  claims: [{
    type: "commitment",
    sourceIds: [
      "field:202:r6:Microsoft.VSTS.Scheduling.DueDate",
      "comment:202:21:v1",
    ],
    excerpt: "The package is unfinished and still due tomorrow.",
    issueId: "delivery-package",
    date: "2026-10-09T00:00:00Z",
    isOutstanding: true,
    provenance: "team-reported",
  }],
}
```

Board fields and comments are **team-reported**, never code-verified. An ordinary
HTTPS URL cannot upgrade their provenance. The collected source contract contains
no independently verified code sources, so code-verified claims are rejected
rather than manufactured; verified code links may be supplied separately in
Analysis/evidence only after inspecting the identified repository at a pinned
commit. No repository identification or inspection means no code-verification
assertion. Any supplied claim URL must pass the existing raw/decoded credential
and HTTPS boundary, even when the claim would not change order.

Pair blockers and resolutions by `issueId`. For deliveries, derive the stable
identity from what the cited excerpts describe, not keywords or a shared date:
two packages due on the same day are not the same commitment. Match parent
dependencies to the same direct parent and delivery identity. Include explicit
false and unknown status claims as well as true ones; never omit counterclaims.
Legacy commitments without an identity are reconciled conservatively by parent
and date. Separate-comment parent dependency support needs matching identities;
legacy claims can share the same supporting comment, but sharing a parent date
field alone is not enough. Missing linkage asks for clarification without promotion.

Use both creation and modification timestamps, not array order or modification
time alone. An unedited counterclaim created strictly after the earlier report's
last modification supersedes it. An unedited older counterclaim cannot withdraw
a newer report. If the counterclaim was created earlier or simultaneously but
edited at or after the report, retain both as a conflict. Likewise, a later edited
counterclaim or an earlier report edited at or after the counterclaim requires
clarification: the API exposes the current comment version, not when its asserted
event occurred. Apply this rule to blockers, completed/unknown commitments and
withdrawn/unknown parent dependencies. A later unedited renewal of the same
identity supersedes earlier reports whose last modification precedes it; their
historical conflict pairs must not override current evidence. An unknown edited
before a renewed confirmation is historical, while an edit overlapping or
following that confirmation still requires clarification. Preserve references
for unresolved conflicts in Why now, not superseded historical pairs.
Partial discussion cannot establish current outstanding work, a current blocker
or absence of blockers; complete those reads first. Independent native critical
fields remain usable with visibly limited coverage.

DueDate records a scheduling commitment, not proof of unfinished work or a
guaranteed contract. It needs current outstanding-work evidence to promote.
TargetDate is a forecast unless an explicit current commitment grounds it. Keep
both raw dates visible; conflicting current commitments require clarification
without promotion. A parent's current commitment affects its child only with a
matching explicit outstanding dependency. Parent Priority alone never promotes.
Reconcile all matching dependency statuses before admitting the parent commitment.
A later unambiguous withdrawal removes the child promotion; ambiguous edits or
unknown dependency status ask for clarification in native order. A promotion
includes the actual dependency comment sources in Why now, even when the
dependency and parent commitment are reported in separate comments.

At 30 elapsed days without change, recommend relevance review without promoting
rank. An expired sprint suggests updating planning, not overdue delivery. Fresh
activity, workflow state and comment count supply no urgency. Retain absent,
partial and inaccessible signals with each reason and next action. Inventory
completeness and evidence coverage are independent.

The four Azure sections retain every selected member once. Expanded items show
Recommendation, Why now, Analysis, Created / Changed, Delivery dates, Discussion,
Iteration / sprint, Parent signals, Area, Coverage and Evidence, alongside native
Azure priority and hierarchy. Comment evidence links use the documented Board
item URL with comment ID/version/timestamp labels, never guessed deep links.
Remote comment markup is inert escaped text. Legacy callers without `signals`
keep native behavior; the normal skill always explicitly requests `includeSignals`.
