# Permissions

Who can call what. This is the authorization spec: any change to access must update this file in the same commit, and the adversarial reviewer checks endpoints against it.

`ai-engineering` has no hosted API or product server. This table covers the
outbound Azure DevOps reads made by the optional triage adapter through the
existing Azure CLI sign-in. Azure DevOps enforces the signed-in user's
permissions; the adapter does not grant access. The optional version notice
separately reads package metadata and does not download install assets.

| Azure DevOps REST read | Triage agent | Scope and permission boundary |
|---|---|---|
| `GET /{project}/{team}/_apis/work/backlogs` | Allowed | Explicit selected organization, project and team; REST 7.1. |
| `GET /{project}/{team}/_apis/work/backlogs/{backlogId}/workItems` | Allowed | Exact selected backlog membership; unknown/reached cap is fatal. |
| `GET /_apis/projects/{project}` | Allowed | Selected project ID for validating related-item scope and comment-continuation GUID aliases; REST 7.1. Reuse the hierarchy read, otherwise one optional identity read for enrichment. |
| `POST /{project}/_apis/wit/workitemsbatch` | Read only | At most 200 distinct positive IDs, `Fail`; selected details with Relations, mandatory direct hierarchy type/state/title, or separate metadata-validated direct-parent standard fields. No mutation body. |
| `GET /{project}/_apis/wit/workItems/{id}/comments` | Optional read | Full paged discussion is limited to selected backlog members (`$top=200`, `order=asc`, `includeDeleted=true`, opaque continuation tokens). The recent-comment window may also read selected items and their direct, same-project `Hierarchy-Forward` or `Hierarchy-Reverse` relation targets. Those reads use exactly `$top=5` and `order=desc`; other relation types and cross-project targets are denied. 7.1-preview.4. |
| `GET /{project}/_apis/wit/fields` | Optional read | Selected project metadata only; REST 7.1, no query/projection. |
| `GET /{project}/{team}/_apis/work/teamsettings/iterations` | Optional read | Selected team only; REST 7.1, no `$timeframe` or undocumented paging. |
| Any other route, method, query, body or scope | Denied | Rejected before CLI execution. |

Optional confirmed Forbidden reads produce explicit inaccessible/partial
evidence with a next action. Unauthorized, unknown CLI failures and mandatory
inventory/hierarchy failures stop without replacing the report. No credentials,
CLI defaults, raw diagnostics, comment identities, or private fixtures are stored.
Signal enrichment is explicitly enabled for normal Azure triage runs; legacy
inventory-only API callers retain their original read surface.
Continuation URLs never authorize requests: validate their organization, item
and name/verified-GUID project identity, then reconstruct the original selected
route with only the opaque token. An unverified GUID is denied.

Recommendations authorize no additional reads or remote writes. Source-linked
claims are validated before publishing; unknown/cross-item evidence, unsafe claim
URLs and unsupported code-verification assertions fail closed. Optional gaps
remain visible and cannot establish current blockers or commitments.
`tests/fixtures/triage-azure-signals-preview.mjs` is gate support only: it serves
synthetic complete/limited/empty writer output from memory on `127.0.0.1:8773`,
plus `/health`. It neither reads nor overwrites the private triage artifact,
contacts Azure, nor creates an authenticated browser session.
