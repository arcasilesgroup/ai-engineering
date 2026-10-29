import { normalizeAzureSignals } from "../../skills/ai-triage/scripts/azure-signals.mjs";
import { writeAzureTriageReport } from "../../skills/ai-triage/scripts/render-report.mjs";

const observedAt = "2026-10-08T10:00:00Z";
const dueReference = "Microsoft.VSTS.Scheduling.DueDate";
const targetReference = "Microsoft.VSTS.Scheduling.TargetDate";
const scope = {
  provider: "azure-devops",
  organization: "https://dev.azure.com/synthetic-org",
  project: "synthetic-project",
  team: "platform-team",
  backlogId: "stories",
  backlogName: "Story backlog",
};
const currentPath = "synthetic-project\\Iteration 4";
const oldPath = "synthetic-project\\Iteration 2";
const fieldMetadata = {
  status: "complete",
  fields: [
    { referenceName: "Microsoft.VSTS.Common.Priority", type: "integer" },
    { referenceName: "Microsoft.VSTS.Common.Severity", type: "string" },
    { referenceName: "System.CreatedDate", type: "dateTime" },
    { referenceName: "System.ChangedDate", type: "dateTime" },
    { referenceName: dueReference, type: "dateTime" },
    { referenceName: targetReference, type: "dateTime" },
  ],
};
const iterations = {
  status: "complete",
  response: {
    value: [
      {
        id: "synthetic-current", name: "Iteration 4", path: currentPath,
        attributes: { startDate: "2026-10-05T00:00:00Z", finishDate: "2026-10-16T00:00:00Z", timeFrame: "current" },
      },
      {
        id: "synthetic-old", name: "Iteration 2", path: oldPath,
        attributes: { startDate: "2026-08-10T00:00:00Z", finishDate: "2026-08-21T00:00:00Z", timeFrame: "past" },
      },
    ],
  },
};
const parent = {
  id: 901, rev: 2,
  fields: {
    "System.WorkItemType": "Feature", "System.Title": "Prepare release capability",
    "System.State": "In progress", "Microsoft.VSTS.Common.Priority": 1,
    "Microsoft.VSTS.Common.Severity": "2 - High",
    "System.CreatedDate": "2026-09-01T10:00:00Z", "System.ChangedDate": "2026-10-07T10:00:00Z",
    [dueReference]: "2026-10-15T00:00:00Z",
    [targetReference]: "2026-10-15T00:00:00Z",
  },
};
const items = [
  {
    id: 201, rev: 4,
    fields: {
      "System.WorkItemType": "Bug", "System.Title": "Prevent lost writes", "System.State": "Needs investigation",
      "Microsoft.VSTS.Common.Priority": 1, "Microsoft.VSTS.Common.Severity": "1 - Critical",
      "System.CreatedDate": "2026-10-01T10:00:00Z", "System.ChangedDate": "2026-10-07T10:00:00Z",
      "System.IterationPath": currentPath,
      [dueReference]: "2026-10-30T00:00:00Z", [targetReference]: "2026-10-30T00:00:00Z",
    },
  },
  {
    id: 202, rev: 6,
    fields: {
      "System.WorkItemType": "Story", "System.Title": "Prepare delivery package", "System.State": "Ready for planning",
      "Microsoft.VSTS.Common.Priority": 3,
      "System.CreatedDate": "2026-10-02T10:00:00Z", "System.ChangedDate": "2026-10-08T10:00:00Z",
      "System.IterationPath": currentPath, [dueReference]: "2026-10-09T00:00:00Z",
      [targetReference]: "2026-10-09T00:00:00Z",
    },
    relations: [{
      rel: "System.LinkTypes.Hierarchy-Reverse",
      url: `${scope.organization}/${scope.project}/_apis/wit/workItems/901`,
      relatedItem: { id: 901, type: "Feature", title: "Prepare release capability", state: "In progress" },
    }],
  },
  {
    id: 203, rev: 3,
    fields: {
      "System.WorkItemType": "Story", "System.Title": "Revisit the archived request", "System.State": "Ready for planning",
      "Microsoft.VSTS.Common.Priority": 2,
      "System.CreatedDate": "2026-07-01T10:00:00Z", "System.ChangedDate": "2026-08-20T10:00:00Z",
      "System.IterationPath": oldPath,
      [dueReference]: "2026-10-30T00:00:00Z", [targetReference]: "2026-10-30T00:00:00Z",
    },
  },
  {
    id: 204, rev: 1,
    fields: {
      "System.WorkItemType": "Task", "System.Title": "Confirm the retained terminal item", "System.State": "Done in this board",
      "System.IterationPath": "synthetic-project\\Unscheduled",
    },
  },
].map((item) => ({ ...item, fields: { "System.AreaPath": "synthetic-project\\Delivery", ...item.fields } }));

function comment(id, workItemId, text, createdDate) {
  return { id, workItemId, version: 1, text, createdDate, modifiedDate: createdDate };
}
const comments = {
  201: [comment(11, 201, "Retries can lose writes.", "2026-10-07T10:00:00Z")],
  202: [comment(21, 202, "The package is unfinished and still due tomorrow.", "2026-10-08T09:00:00Z")],
  203: [
    comment(31, 203, "Blocked on package format.", "2026-08-10T10:00:00Z"),
    comment(32, 203, "Package format is settled; that blocker is resolved.", "2026-08-20T10:00:00Z"),
  ],
};

function analysis(item, state) {
  const summaries = {
    201: "The team reports a write-loss condition during retries. This needs a reproduction before treating the described code path as verified.",
    202: state === "limited"
      ? "The package serves the next delivery stage. A known comment reports unfinished preparation, but unseen later updates may change that report; its current outstanding status is not confirmed."
      : "The package makes the completed work usable by the next delivery stage. The team still needs to finish its preparation; parent priority alone did not determine this advice.",
    203: "An earlier dependency delayed the request, but a later team update reports it cleared. More discussion does not itself make the remaining work urgent.",
  };
  if (item.id === 204) return { status: "UNASSESSED" };
  const evidenceLabels = {
    201: `#${item.id} revision ${item.rev} · Severity / comment #11 v1`,
    202: `#${item.id} revision ${item.rev} · DueDate / comment #21 v1`,
    203: `#${item.id} revision ${item.rev} · ChangedDate / comments #31–32 v1`,
  };
  const evidence = [{
    label: evidenceLabels[item.id],
    url: `${scope.organization}/${scope.project}/_workitems/edit/${item.id}`,
  }];
  if (item.id === 202) evidence.push({
    label: `#${parent.id} revision ${parent.rev} · Priority / TargetDate`,
    url: `${scope.organization}/${scope.project}/_workitems/edit/${parent.id}`,
  });
  const claims = [];
  if (item.id === 202) claims.push({
    type: "commitment", provenance: "team-reported", isOutstanding: true,
    sourceIds: [`field:202:r6:${dueReference}`, "comment:202:21:v1"],
    excerpt: comments[202][0].text, date: "2026-10-09T00:00:00Z",
  });
  if (item.id === 203) claims.push(...comments[203].map((source, index) => ({
    type: index === 0 ? "blocker" : "blocker-resolved", provenance: "team-reported",
    sourceIds: [`comment:203:${source.id}:v1`], excerpt: source.text, issueId: "package-format",
  })));
  return { status: "ASSESSED", summary: summaries[item.id], claims, evidence };
}

async function generateReport(state) {
  const inventory = {
    complete: true, observedAt,
    items: state === "empty" ? [] : items.map((original) => {
      const item = structuredClone(original);
      const itemComments = comments[item.id] ?? [];
      const hasLimitedDiscussion = state === "limited" && item.id === 202;
      const discussion = item.id === 204
        ? { status: "inaccessible", reason: "confirmed permission denial", nextAction: "Request discussion access for this selected item, then reassess." }
        : {
          status: hasLimitedDiscussion ? "partial" : "complete",
          ...(hasLimitedDiscussion ? { reason: "the next comment page failed", nextAction: "Fetch remaining comments before confirming current work." } : {}),
          pages: [{
            count: itemComments.length, totalCount: itemComments.length + (hasLimitedDiscussion ? 1 : 0),
            comments: itemComments,
            ...(hasLimitedDiscussion ? { continuationToken: "synthetic-next" } : {}),
          }],
        };
      item.signals = normalizeAzureSignals({
        item, observedAt, discussion, fieldMetadata,
        iterations: hasLimitedDiscussion
          ? {
            status: "inaccessible", reason: "confirmed selected-team iteration permission denial",
            nextAction: "Request iteration read access; the item path alone supplies no sprint deadline.",
          } : iterations,
        parent: item.id === 202 ? { status: "complete", item: parent } : { status: "absent" },
      });
      return item;
    }),
  };
  let report = "";
  await writeAzureTriageReport({
    scope, inventory, analyzeItem: (item) => analysis(item, state),
    writeFile: (_path, contents) => { report = contents; },
  });
  return report;
}

export async function createPreviewReports() {
  const reports = new Map();
  for (const state of ["complete", "limited", "empty"]) reports.set(state, await generateReport(state));
  return reports;
}

if (import.meta.main) {
  const reports = await createPreviewReports();
  const server = Bun.serve({
    hostname: "127.0.0.1", port: 8773,
    fetch(request) {
      const url = new URL(request.url);
      if (url.pathname === "/health") return new Response("ok");
      if (url.pathname !== "/triage.html") return new Response("Not found", { status: 404 });
      const report = reports.get(url.searchParams.get("state") ?? "complete");
      return report === undefined
        ? new Response("Unknown synthetic state", { status: 400 })
        : new Response(report, { headers: { "Content-Type": "text/html; charset=utf-8" } });
    },
  });
  console.log(`Synthetic triage preview: ${server.url}`);
}
