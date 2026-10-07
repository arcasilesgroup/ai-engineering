# Azure DevOps Services collection

This collector reads one explicitly selected team backlog level. It never uses
WIQL, `az boards query`, pagination guesses, or relationships to widen inventory.
Only the selected backlog's work-item references form the inventory; parent and
child relations on returned items remain context.
The documented backlog-membership operation has no continuation, `$top`, or
`$skip` parameter; do not invent paging or substitute WIQL.

## Scoped read allowlist

Every request carries the resolved organization, project, team/backlog where the
route requires them, and API version `7.1`. The collector permits only these
method/route pairs:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/{project}/{team}/_apis/work/backlogs` | Find the selected level and its `workItemCountLimit`. |
| `GET` | `/{project}/{team}/_apis/work/backlogs/{backlogId}/workItems` | Read exact membership in the selected level. |
| `GET` | `/{project}/_apis/wit/workitemtypes` | Validate the types represented in that membership. |
| `GET` | `/{project}/_apis/wit/workitemtypes/{type}/states` | Resolve state categories for the selected types. |
| `POST` | `/{project}/_apis/wit/workitemsbatch` | Read details in batches of at most 200 IDs with `errorPolicy: "Fail"`. |

These routes follow the Azure DevOps Services REST API 7.1 documentation:
[backlog levels](https://learn.microsoft.com/en-us/rest/api/azure/devops/work/backlogs/list?view=azure-devops-rest-7.1),
[backlog-level membership](https://learn.microsoft.com/en-us/rest/api/azure/devops/work/backlogs/get-backlog-level-work-items?view=azure-devops-rest-7.1),
[work-item types](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-item-types/list?view=azure-devops-rest-7.1),
[work-item type states](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-item-type-states/list?view=azure-devops-rest-7.1),
and [batch work-item reads](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-items-batch?view=azure-devops-rest-7.1).
The batch API documents a maximum of 200 IDs and `Fail`/`Omit` error policies;
this collector always requests `Fail` and rejects a response whose IDs do not
exactly match the requested batch.

## Completeness and states

The backlog-level `workItemCountLimit` is the only completion boundary. A
missing, invalid, or unknown limit, or a reference count at or above that limit,
raises an incomplete-inventory error and returns no success inventory. Below a
known limit, the complete reference list is processed without inventing paging.

State display names are not fixed. The collector matches each returned item to
its type's state metadata and includes categories `Proposed`, `InProgress`, and
`Resolved`; `Completed` and `Removed` are terminal. Missing, ambiguous, or
unknown state metadata fails closed.

## CLI route-mapping boundary

Local `az devops invoke --help` documents `--area`, `--resource`,
`--route-parameters`, `--query-parameters`, `--org`, `--http-method`, and
`--api-version`, and shows examples for Wiki routes. It does not establish the
exact `--area`/`--resource` mapping for the backlog-level
`/{backlogId}/workItems` route. The Microsoft REST documentation establishes
the URL and method, not that CLI mapping. Do not guess those values or invoke
Azure until that exact mapping is verified from authoritative CLI/API metadata.
The collector accepts a scoped request adapter so synthetic tests need no Azure
tenant, credentials, or network access.

No credentials, active CLI defaults, or Azure responses belong in this
repository. Authentication and API failures stop collection; no partial
inventory is reported as complete.

## Report handoff

Only after `collectAzureBacklog` returns `complete: true`, analyze every returned work
item exactly once. Keep no more than five analyses in flight. Each analysis must return a
record for that item's ID, or an explicit `UNASSESSED` record; a missing or invalid record
stops the run.

Pass the complete inventory and its per-item analysis records to
`writeAzureTriageReport` in `scripts/render-report.mjs` through an `analyzeItem` lookup
keyed by work-item ID. The writer uses the shared
`templates/triage.html.tpl` shell and the Azure-specific scope, ranked work-item,
type/state, related-context and method sections. Related parents and children are shown as
context only and never become inventory rows. The writer finishes validation and rendering
before atomically replacing `.ai-engineering/triage.html`; ambiguity, collection,
analysis, validation, rendering or writing failures must leave an existing report
byte-for-byte unchanged. Never include authentication fields or values in the analysis
records or report.
