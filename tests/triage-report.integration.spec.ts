import { randomUUID } from "node:crypto";
import {
  mkdir,
  readFile,
  readdir,
  rm,
  unlink,
  writeFile,
} from "node:fs/promises";
import { describe, expect, test } from "bun:test";
import {
  atomicWriteReport,
  writeAzureTriageReport,
} from "../packs/triage/scripts/render-report.mjs";

const targetReport = ".ai-engineering/triage.html";
const syntheticOrganization = "https://dev.azure.com/synthetic-org";
const existingReport =
  "<!doctype html><html><body>previous synthetic report ✓</body></html>\n";

type SyntheticWorkItem = {
  id: number;
  fields: {
    "System.WorkItemType": string;
    "System.State": string;
    "System.Title": string;
    "System.Description": string;
    "System.AreaPath": string;
    "Microsoft.VSTS.Common.Priority"?: number | string;
    "Microsoft.VSTS.Common.Severity"?: string;
  };
  comments?: {
    totalCount: number;
    items: Array<{ id: number; text: string; createdDate: string }>;
  };
  relations?: Array<{
    rel: string;
    url: string;
    relatedItem?: {
      id: number;
      type: string;
      state: string;
      title: string;
      comments?: {
        totalCount: number;
        items: Array<{ id: number; text: string; createdDate: string }>;
      };
    };
  }>;
};

function createSyntheticInventory() {
  const itemIds = [201, 202, 203, 204, 205, 206, 207, 208];
  const items: SyntheticWorkItem[] = itemIds.map((id, index) => ({
    id,
    fields: {
      "System.WorkItemType": index % 2 === 0 ? "Feature" : "Task",
      "System.State": index % 2 === 0 ? "Ready for planning" : "In progress",
      ...(index === 0
        ? {
            "Microsoft.VSTS.Common.Priority": 2,
            "Microsoft.VSTS.Common.Severity": "3 - Medium",
          }
        : {}),
      ...(index === 1
        ? {
            "Microsoft.VSTS.Common.Priority": 1,
            "Microsoft.VSTS.Common.Severity": "2 - High",
          }
        : {}),
      "System.Title":
        index === 2 ? "<img src=x onerror=alert(1)>" : `Synthetic backlog item ${id}`,
      "System.Description":
        index === 3
          ? "</span><script>window.syntheticAttack=true</script>"
          : index === 4
            ? "<p>First description line&nbsp;&amp; with spaces</p><p>Second description line</p><ul><li>Alpha</li><li>Beta</li></ul><script>window.syntheticDescriptionScript=true</script>"
          : `Synthetic description for item ${id}`,
      "System.AreaPath": "Synthetic Project\\Delivery",
    },
    ...(index === 0
      ? {
          comments: {
            totalCount: 2,
            items: [
              {
                id: 1201,
                text: "Deployment waits on product sign-off.",
                createdDate: "2026-10-01T10:00:00Z",
              },
              {
                id: 1202,
                text: "Follow-up scheduled for next week.",
                createdDate: "2026-10-02T10:00:00Z",
              },
            ],
          },
        }
      : {}),
    ...(index === 0
      ? {
          relations: [
            {
              rel: "System.LinkTypes.Hierarchy-Reverse",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/901`,
              relatedItem: {
                id: 901,
                type: "Feature",
                state: "Feature in progress",
                title: "Synthetic parent feature",
                comments: {
                  totalCount: 1,
                  items: [
                    {
                      id: 1901,
                      text: "<script>window.commentAttack=true</script> token=synthetic-comment-secret",
                      createdDate: "2026-10-03T10:00:00Z",
                    },
                  ],
                },
              },
            },
          ],
        }
      : {}),
    ...(index === 1
      ? {
          relations: [
            {
              rel: "System.LinkTypes.Hierarchy-Forward",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/902`,
              relatedItem: {
                id: 902,
                type: "Task",
                state: "Ready",
                title: "Synthetic child task",
                comments: {
                  totalCount: 0,
                  items: [],
                },
              },
            },
          ],
        }
      : {}),
  }));

  return { complete: true as const, items };
}

function createSyntheticScope() {
  return {
    provider: "azure-devops" as const,
    organization: syntheticOrganization,
    project: "synthetic-project",
    team: "synthetic-delivery",
    backlogId: "features",
    backlogName: "Synthetic feature backlog",
  };
}

function createMemoryReportWriter() {
  const reports = new Map([[targetReport, existingReport]]);
  const writes: Array<{ path: string; contents: string }> = [];

  return {
    reports,
    writes,
    writeFile: async (path: string, contents: string) => {
      writes.push({ path, contents });
      reports.set(path, contents);
    },
  };
}

function isSuccessShapedResult(result: unknown): boolean {
  if (result === true) return true;
  if (typeof result !== "object" || result === null) return false;

  const resultFields = result as Record<string, unknown>;
  return (
    resultFields.success === true ||
    resultFields.written === true ||
    ["complete", "success", "written"].includes(
      String(resultFields.status ?? "").toLowerCase(),
    )
  );
}

async function expectNoSuccessShapedResult(
  operation: () => Promise<unknown>,
): Promise<void> {
  const outcome = await operation().then(
    (result) => ({ isRejected: false as const, result }),
    (error: unknown) => ({ isRejected: true as const, error }),
  );

  if (outcome.isRejected) {
    expect(outcome.error).toBeInstanceOf(Error);
    return;
  }

  expect(isSuccessShapedResult(outcome.result)).toBe(false);
}

describe("Azure triage report integration", () => {
  test("writes every synthetic item in the shared shell with Azure sections and at most five analyses in flight", async () => {
    const inventory = createSyntheticInventory();
    const scope = createSyntheticScope();
    const syntheticToken = "github_pat_syntheticToken1234567890";
    const inertPlaceholderLabel = "{{date}} {{repo}} $& $`";
    scope.backlogName =
      `<img src=x onerror=alert(1)> ${syntheticToken} ${inertPlaceholderLabel}`;
    const reportWriter = createMemoryReportWriter();
    const analyzedItemIds: number[] = [];
    let activeAnalyses = 0;
    let maxActiveAnalyses = 0;

    await writeAzureTriageReport({
      scope,
      inventory,
      analyzeItem: async (item: SyntheticWorkItem) => {
        activeAnalyses += 1;
        maxActiveAnalyses = Math.max(maxActiveAnalyses, activeAnalyses);
        analyzedItemIds.push(item.id);
        await Promise.resolve();
        activeAnalyses -= 1;

        if (item.id === 208) return { status: "UNASSESSED" };
        return {
          status: "ASSESSED",
          priority: "P2",
          summary: `**Synthetic analysis** for item ${item.id}: *verify* \`pipeline.yml\``,
          whyNow: "A parent comment asks for product sign-off before deployment.",
          confidence: "HIGH",
          confidenceBasis: "The linked parent comment names the pending approval.",
          evidence: [
            {
              label: "Synthetic work item",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/${item.id}`,
            },
          ],
        };
      },
      writeFile: async (path: string, contents: string) => {
        expect(activeAnalyses).toBe(0);
        expect(analyzedItemIds).toHaveLength(inventory.items.length);
        await reportWriter.writeFile(path, contents);
      },
    });

    const generatedReport = reportWriter.reports.get(targetReport);
    if (generatedReport === undefined) {
      throw new Error("The synthetic report writer did not store the target report");
    }
    expect(reportWriter.writes).toHaveLength(1);
    const writtenReport = reportWriter.writes[0];
    if (writtenReport === undefined) {
      throw new Error("The synthetic report writer did not record a write");
    }
    expect(writtenReport.path).toBe(targetReport);
    expect(generatedReport).toBe(writtenReport.contents);
    expect(maxActiveAnalyses).toBeLessThanOrEqual(5);
    expect([...analyzedItemIds].sort((firstId, secondId) => firstId - secondId)).toEqual(
      inventory.items.map((item) => item.id),
    );
    expect(generatedReport).toContain('class="hero"');
    expect(generatedReport.match(/<html\b/g)).toHaveLength(1);
    expect(generatedReport.match(/<\/html>/g)).toHaveLength(1);
    expect(generatedReport.match(/<h1>/g)).toHaveLength(1);
    expect(generatedReport).toContain("{{date}} {{repo}} $&amp; $`");
    expect(generatedReport).toContain("<nav>");
    expect(generatedReport).toContain('<main id="main">');
    expect(generatedReport).toContain('class="container"');
    expect(generatedReport).toContain("<footer>");
    expect(generatedReport).toMatch(/<h[2-3][^>]*>[^<]*Azure DevOps/i);
    expect(generatedReport).toMatch(/<h[2-3][^>]*>[^<]*work item types?/i);
    expect(generatedReport).not.toMatch(/<h[2-3][^>]*>[^<]*related/i);
    expect(generatedReport).toMatch(/<h[2-3][^>]*>[^<]*method/i);
    expect(generatedReport).toContain('<section id="s04">');
    expect(generatedReport).not.toContain('<section id="s05">');
    expect(generatedReport).not.toContain('href="#s04"><b>04</b>Related context');
    expect(generatedReport).not.toMatch(/pull requests/i);
    expect(generatedReport).not.toMatch(/\bgh\s+(?:issue|pr)\s+(?:list|view)\b/i);

    const snapshotStats =
      generatedReport.match(/<div class="stats">([\s\S]*?)<\/div>\s*<\/section>/i)?.[1] ??
      "";
    expect(snapshotStats).toMatch(/<div class="v">8<\/div>/);
    expect(snapshotStats).toMatch(/<div class="l">[^<]*items?/i);
    for (const item of inventory.items) {
      const title = item.fields["System.Title"];
      expect(generatedReport).toContain(
        title === "<img src=x onerror=alert(1)>"
          ? "&lt;img src=x onerror=alert(1)&gt;"
          : title,
      );
    }
    expect(generatedReport.match(/class="item(?:\s|")/g)).toHaveLength(
      inventory.items.length,
    );
    expect(generatedReport).toContain("UNASSESSED");
    expect(generatedReport).toContain("901");
    expect(generatedReport).toContain("902");
    expect(generatedReport).toContain("Deployment waits on product sign-off.");
    expect(generatedReport).toContain("Follow-up scheduled for next week.");
    expect(generatedReport).toContain("2 comments");
    expect(generatedReport).toContain("HIGH · The linked parent comment names the pending approval.");
    expect(generatedReport).toContain("A parent comment asks for product sign-off before deployment.");
    expect(generatedReport).toContain("&lt;script&gt;window.commentAttack=true&lt;/script&gt; [redacted]");
    expect(generatedReport).not.toContain("<script>window.commentAttack=true</script>");
    expect(generatedReport).not.toContain("synthetic-comment-secret");
    expect(generatedReport).toMatch(
      /<span class="type-chip">Feature<\/span> <a\b[^>]*>#901<\/a> <span class="tree-title">Synthetic parent feature/,
    );
    expect(generatedReport).toContain(
      '<span class="tree-state">Feature in progress</span>',
    );
    const parentItem = generatedReport.match(
      /<details class="item" id="i201">([\s\S]*?)<\/details>/,
    )?.[1];
    expect(parentItem).toContain(
      '<span class="tree-role">Parent</span> <span class="type-chip">Feature</span>',
    );
    expect(parentItem).toContain(
      '<div class="tree-branch"><div class="tree-row tree-current">',
    );
    const childItem = generatedReport.match(
      /<details class="item" id="i202">([\s\S]*?)<\/details>/,
    )?.[1];
    expect(childItem).toContain('<div class="tree-children">');
    expect(childItem).toContain('<span class="tree-role">Child</span>');
    expect(generatedReport).not.toContain('id="i901"');
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201"',
    );
    expect(generatedReport).toContain('class="type-chip">Feature</span>');
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201" target="_blank" rel="noreferrer noopener"',
    );
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/901" target="_blank" rel="noreferrer noopener"',
    );
    expect(generatedReport).not.toContain("/_apis/wit/workItems/");
    expect(generatedReport).toContain('class="tree-group"');
    expect(generatedReport).toContain('class="tree-row tree-current"');
    expect(generatedReport).toContain('class="tree-children"');
    expect(generatedReport.indexOf('id="i202"')).toBeLessThan(
      generatedReport.indexOf('id="i201"'),
    );
    for (const anchor of generatedReport.matchAll(/<a\b[^>]*>/g)) {
      if (!anchor[0].includes('href="https:')) continue;
      expect(anchor[0]).toContain('target="_blank"');
      expect(anchor[0]).toContain('rel="noreferrer noopener"');
    }
    expect(generatedReport).not.toContain(
      "<img src=x onerror=alert(1)>",
    );
    expect(generatedReport).not.toContain(
      "</span><script>window.syntheticAttack=true</script>",
    );
    expect(generatedReport).not.toContain('<span class="ilbl">Description</span>');
    expect(generatedReport).not.toContain("First description line");
    expect(generatedReport).toContain(
      '<span class="analysis"><strong>Synthetic analysis</strong> for item 201: <em>verify</em> <code>pipeline.yml</code></span>',
    );
    expect(generatedReport).not.toContain("window.syntheticDescriptionScript");
    expect(generatedReport).not.toContain("<p>First description line");
    expect(generatedReport).toContain(
      "&lt;img src=x onerror=alert(1)&gt; [redacted]",
    );
    expect(generatedReport).not.toContain("<img src=x onerror=alert(1)>");
    expect(generatedReport).not.toContain(syntheticToken);
  });

  test("leaves the previous report untouched when an analysis contains an unsafe link", async () => {
    const reportWriter = createMemoryReportWriter();
    await expectNoSuccessShapedResult(() => writeAzureTriageReport({
      scope: createSyntheticScope(),
      inventory: createSyntheticInventory(),
      analyzeItem: async () => ({
        status: "ASSESSED",
        summary: "[unsafe](javascript:alert)",
        evidence: [],
      }),
      writeFile: reportWriter.writeFile,
    }));
    expect(reportWriter.writes).toHaveLength(0);
    expect(reportWriter.reports.get(targetReport)).toBe(existingReport);
  });

  test("renders a token-shaped project identifier as text instead of linking it", async () => {
    const syntheticToken = "github_pat_syntheticToken1234567890";
    const scope = createSyntheticScope();
    scope.project = syntheticToken;
    const reportWriter = createMemoryReportWriter();

    await writeAzureTriageReport({
      scope,
      inventory: createSyntheticInventory(),
      analyzeItem: async (item: SyntheticWorkItem) => ({
        status: "ASSESSED",
        priority: "P2",
        summary: `Synthetic analysis for item ${item.id}`,
        evidence: [
          {
            label: "Safe synthetic evidence",
            url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/${item.id}`,
          },
        ],
      }),
      writeFile: reportWriter.writeFile,
    });

    const generatedReport = reportWriter.reports.get(targetReport);
    if (generatedReport === undefined) {
      throw new Error("The synthetic report writer did not store the target report");
    }
    expect(generatedReport).not.toContain(syntheticToken);
    expect(generatedReport).toContain('<span class="iid">#201</span>');
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201" target="_blank" rel="noreferrer noopener"',
    );
    for (const linkMatch of generatedReport.matchAll(/\bhref="([^"]*)"/g)) {
      expect(linkMatch[1] ?? "").not.toContain(syntheticToken);
    }
  });

  test("redacts credential assignments in the complete synthetic report", async () => {
    const scope = createSyntheticScope();
    scope.team = [
      "Synthetic team",
      "token=synthetic-team-secret",
      "auth_token=synthetic-auth-token-secret",
      "oauth_token=synthetic-oauth-token-secret",
      "oauth2_access_token=synthetic-oauth2-access-secret",
      "x_auth_token=synthetic-x-auth-token-secret",
      "client_auth=synthetic-client-auth-secret",
      "azure_devops_token=synthetic-azure-devops-token-secret",
      "bearer_token=synthetic-bearer-token-secret",
      "personal_access_token=synthetic-personal-access-token-secret",
      "ado_pat=synthetic-ado-pat-secret",
      "azure_devops_ext_pat=synthetic-azure-devops-ext-pat-secret",
      "azure_devops_pat=synthetic-azure-devops-pat-secret",
      "github_token=synthetic-github-token-secret",
      "system_access_token=synthetic-system-access-token-secret",
      "SYSTEM_ACCESSTOKEN=synthetic-system-accesstoken-secret",
      "SYSTEM-ACCESSTOKEN=synthetic-system-hyphen-accesstoken-secret",
      "SystemAccessToken=synthetic-system-camel-token-secret",
      "api_token=synthetic-api-token-secret",
      "github_pat=synthetic-github-pat-secret",
      "gh_token=synthetic-gh-token-secret",
      "azdo_pat=synthetic-azdo-pat-secret",
      "ado_token=synthetic-ado-token-secret",
      "azure_pat=synthetic-azure-pat-secret",
      "private_key=synthetic-private-key-secret",
      "PRIVATE-KEY=synthetic-uppercase-private-key-secret",
      "privateKey=synthetic-camel-private-key-secret",
      "access_key=synthetic-access-key-secret",
      "access-key=synthetic-hyphen-access-key-secret",
      "accessKey=synthetic-camel-access-key-secret",
      "secret_access_key=synthetic-secret-access-key-secret",
      "secret-access-key=synthetic-hyphen-secret-access-key-secret",
      "secretAccessKey=synthetic-camel-secret-access-key-secret",
      "authored_by=synthetic-maintainer",
      "client_author=synthetic-owner",
      "oauth_provider=synthetic-provider",
      "oauth2_access_policy=synthetic-policy",
      "azure_devops_token_policy=synthetic-token-policy",
      "bearer_token_owner=synthetic-token-owner",
      "personal_access_token_owner=synthetic-personal-token-owner",
      "ado_pat_owner=synthetic-ado-owner",
      "azure_devops_ext_pat_owner=synthetic-extension-owner",
      "azure_devops_pat_owner=synthetic-azure-pat-owner",
      "github_token_owner=synthetic-github-owner",
      "system_access_token_owner=synthetic-system-owner",
      "api_token_owner=synthetic-api-owner",
      "github_pat_owner=synthetic-github-pat-owner",
      "gh_token_count=4",
      "azdo_pat_owner=synthetic-azdo-owner",
      "ado_token_count=6",
      "azure_pat_owner=synthetic-azure-owner",
      "api_token_count=8",
      "private_key_owner=synthetic-private-key-owner",
      "access_key_count=3",
      "secret_access_key_policy=synthetic-key-policy",
      'team_owner="Synthetic maintainer token=synthetic-nested-token-secret"',
    ].join(" ");
    scope.backlogName = "Synthetic backlog auth=synthetic-backlog-secret";
    const reportWriter = createMemoryReportWriter();

    await writeAzureTriageReport({
      scope,
      inventory: createSyntheticInventory(),
      analyzeItem: async () => ({ status: "UNASSESSED" }),
      writeFile: reportWriter.writeFile,
    });

    const generatedReport = reportWriter.reports.get(targetReport);
    if (generatedReport === undefined) {
      throw new Error("The synthetic report writer did not store the target report");
    }
    expect(generatedReport).not.toContain("synthetic-team-secret");
    expect(generatedReport).not.toContain("synthetic-nested-token-secret");
    expect(generatedReport).not.toContain("synthetic-auth-token-secret");
    expect(generatedReport).not.toContain("synthetic-oauth-token-secret");
    expect(generatedReport).not.toContain("synthetic-oauth2-access-secret");
    expect(generatedReport).not.toContain("synthetic-x-auth-token-secret");
    expect(generatedReport).not.toContain("synthetic-client-auth-secret");
    expect(generatedReport).not.toContain("synthetic-azure-devops-token-secret");
    expect(generatedReport).not.toContain("synthetic-bearer-token-secret");
    expect(generatedReport).not.toContain("synthetic-personal-access-token-secret");
    expect(generatedReport).not.toContain("synthetic-ado-pat-secret");
    expect(generatedReport).not.toContain("synthetic-azure-devops-ext-pat-secret");
    expect(generatedReport).not.toContain("synthetic-azure-devops-pat-secret");
    expect(generatedReport).not.toContain("synthetic-github-token-secret");
    expect(generatedReport).not.toContain("synthetic-system-access-token-secret");
    expect(generatedReport).not.toContain("synthetic-system-accesstoken-secret");
    expect(generatedReport).not.toContain(
      "synthetic-system-hyphen-accesstoken-secret",
    );
    expect(generatedReport).not.toContain("synthetic-system-camel-token-secret");
    expect(generatedReport).not.toContain("synthetic-api-token-secret");
    expect(generatedReport).not.toContain("synthetic-github-pat-secret");
    expect(generatedReport).not.toContain("synthetic-gh-token-secret");
    expect(generatedReport).not.toContain("synthetic-azdo-pat-secret");
    expect(generatedReport).not.toContain("synthetic-ado-token-secret");
    expect(generatedReport).not.toContain("synthetic-azure-pat-secret");
    expect(generatedReport).not.toContain("synthetic-private-key-secret");
    expect(generatedReport).not.toContain(
      "synthetic-uppercase-private-key-secret",
    );
    expect(generatedReport).not.toContain("synthetic-camel-private-key-secret");
    expect(generatedReport).not.toContain("synthetic-access-key-secret");
    expect(generatedReport).not.toContain("synthetic-hyphen-access-key-secret");
    expect(generatedReport).not.toContain("synthetic-camel-access-key-secret");
    expect(generatedReport).not.toContain("synthetic-secret-access-key-secret");
    expect(generatedReport).not.toContain(
      "synthetic-hyphen-secret-access-key-secret",
    );
    expect(generatedReport).not.toContain(
      "synthetic-camel-secret-access-key-secret",
    );
    expect(generatedReport).not.toContain("synthetic-backlog-secret");
    expect(generatedReport).toContain(
      "Synthetic team [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted] [redacted]",
    );
    expect(generatedReport).toContain(
      "team_owner=&quot;Synthetic maintainer [redacted]&quot;",
    );
    expect(generatedReport).toContain("authored_by=synthetic-maintainer");
    expect(generatedReport).toContain("client_author=synthetic-owner");
    expect(generatedReport).toContain("oauth_provider=synthetic-provider");
    expect(generatedReport).toContain("oauth2_access_policy=synthetic-policy");
    expect(generatedReport).toContain("azure_devops_token_policy=synthetic-token-policy");
    expect(generatedReport).toContain("bearer_token_owner=synthetic-token-owner");
    expect(generatedReport).toContain(
      "personal_access_token_owner=synthetic-personal-token-owner",
    );
    expect(generatedReport).toContain("ado_pat_owner=synthetic-ado-owner");
    expect(generatedReport).toContain(
      "azure_devops_ext_pat_owner=synthetic-extension-owner",
    );
    expect(generatedReport).toContain(
      "azure_devops_pat_owner=synthetic-azure-pat-owner",
    );
    expect(generatedReport).toContain("github_token_owner=synthetic-github-owner");
    expect(generatedReport).toContain(
      "system_access_token_owner=synthetic-system-owner",
    );
    expect(generatedReport).toContain("api_token_owner=synthetic-api-owner");
    expect(generatedReport).toContain(
      "github_pat_owner=synthetic-github-pat-owner",
    );
    expect(generatedReport).toContain("gh_token_count=4");
    expect(generatedReport).toContain("azdo_pat_owner=synthetic-azdo-owner");
    expect(generatedReport).toContain("ado_token_count=6");
    expect(generatedReport).toContain("azure_pat_owner=synthetic-azure-owner");
    expect(generatedReport).toContain("api_token_count=8");
    expect(generatedReport).toContain(
      "private_key_owner=synthetic-private-key-owner",
    );
    expect(generatedReport).toContain("access_key_count=3");
    expect(generatedReport).toContain(
      "secret_access_key_policy=synthetic-key-policy",
    );
    expect(generatedReport).toContain("Synthetic backlog [redacted]");
  });

  test.each(["project", "organization"] as const)(
    "omits percent-encoded credentials from %s metadata and links",
    async (scopeField) => {
      const encodedToken = "%2567ithub_pat_syntheticToken1234567890";
      const scope = createSyntheticScope();
      if (scopeField === "project") {
        scope.project = encodedToken;
      } else {
        scope.organization = `https://dev.azure.com/${encodedToken}`;
      }
      const reportWriter = createMemoryReportWriter();

      await writeAzureTriageReport({
        scope,
        inventory: createSyntheticInventory(),
        analyzeItem: async (item: SyntheticWorkItem) => ({
          status: "ASSESSED",
          priority: "P2",
          summary: `Synthetic analysis for item ${item.id}`,
          evidence: [
            {
              label: "Safe synthetic evidence",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/${item.id}`,
            },
          ],
        }),
        writeFile: reportWriter.writeFile,
      });

      const generatedReport = reportWriter.reports.get(targetReport);
      if (generatedReport === undefined) {
        throw new Error("The synthetic report writer did not store the target report");
      }
      for (const unsafeValue of [
        encodedToken,
        decodeURIComponent(encodedToken),
        decodeURIComponent(decodeURIComponent(encodedToken)),
      ]) {
        expect(generatedReport).not.toContain(unsafeValue);
      }
      expect(generatedReport).toContain('<span class="iid">#201</span>');
      expect(generatedReport).toContain(
        'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201" target="_blank" rel="noreferrer noopener"',
      );
    },
  );

  test.each(["project", "organization"] as const)(
    "omits malformed percent escapes from %s metadata and links",
    async (scopeField) => {
      const malformedValue = "synthetic-malformed%ZZ";
      const scope = createSyntheticScope();
      if (scopeField === "project") {
        scope.project = malformedValue;
      } else {
        scope.organization = `https://dev.azure.com/${malformedValue}`;
      }
      const reportWriter = createMemoryReportWriter();

      await writeAzureTriageReport({
        scope,
        inventory: createSyntheticInventory(),
        analyzeItem: async (item: SyntheticWorkItem) => ({
          status: "ASSESSED",
          priority: "P2",
          summary: `Synthetic analysis for item ${item.id}`,
          evidence: [
            {
              label: "Safe synthetic evidence",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/${item.id}`,
            },
          ],
        }),
        writeFile: reportWriter.writeFile,
      });

      const generatedReport = reportWriter.reports.get(targetReport);
      if (generatedReport === undefined) {
        throw new Error("The synthetic report writer did not store the target report");
      }
      expect(generatedReport).not.toContain(malformedValue);
      expect(generatedReport).toContain('<span class="iid">#201</span>');
      expect(generatedReport).toContain(
        'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201" target="_blank" rel="noreferrer noopener"',
      );
    },
  );

  test.each(["write", "replace"] as const)(
    "preserves previous report bytes when temporary %s fails",
    async (failureStage) => {
      const directory = `.ai-engineering/triage-report-test-${randomUUID()}`;
      const reportPath = `${directory}/triage.html`;
      const otherWriterPath = `${reportPath}.other-writer.tmp`;
      const previousBytes = Buffer.from(existingReport);
      const otherWriterBytes = Buffer.from("temporary file owned by another writer");
      await mkdir(directory);

      try {
        await writeFile(reportPath, previousBytes);
        await writeFile(otherWriterPath, otherWriterBytes);
        const operations: NonNullable<Parameters<typeof atomicWriteReport>[2]> =
          failureStage === "write"
            ? {
                writeTemporaryFile: async (handle) => {
                  await handle.writeFile("partial synthetic report", "utf8");
                  throw new Error("Synthetic temporary write failure");
                },
              }
            : {
                  beforeReplace: async () => {
                  throw new Error("Synthetic report replacement failure");
                },
              };

        await expectNoSuccessShapedResult(() =>
          writeAzureTriageReport({
            scope: createSyntheticScope(),
            inventory: createSyntheticInventory(),
            analyzeItem: async () => ({ status: "UNASSESSED" }),
            writeFile: async (path, contents) => {
              expect(path).toBe(targetReport);
              await atomicWriteReport(reportPath, contents, operations);
            },
          }),
        );

        expect(await readFile(reportPath)).toEqual(previousBytes);
        expect(await readFile(otherWriterPath)).toEqual(otherWriterBytes);
        expect((await readdir(directory)).sort()).toEqual([
          "triage.html",
          "triage.html.other-writer.tmp",
        ]);
      } finally {
        await rm(directory, { recursive: true, force: true });
      }
    },
  );

  test.each(["cleanup", "replacement"] as const)(
    "preserves the old report and foreign bytes after temporary-path substitution before %s",
    async (stage) => {
      const directory = `.ai-engineering/triage-report-test-${randomUUID()}`;
      const reportPath = `${directory}/triage.html`;
      const previousBytes = Buffer.from(existingReport);
      const foreignBytes = Buffer.from("temporary file owned by another writer");
      let foreignTemporaryPath: string | undefined;
      await mkdir(directory);

      try {
        await writeFile(reportPath, previousBytes);
        await expectNoSuccessShapedResult(() =>
          writeAzureTriageReport({
            scope: createSyntheticScope(),
            inventory: createSyntheticInventory(),
            analyzeItem: async () => ({ status: "UNASSESSED" }),
            writeFile: async (path, contents) => {
              expect(path).toBe(targetReport);
              await atomicWriteReport(
                reportPath,
                contents,
                stage === "cleanup"
                  ? {
                      writeTemporaryFile: async (handle, _contents, temporaryPath) => {
                        foreignTemporaryPath = temporaryPath;
                        await handle.writeFile("partial synthetic report", "utf8");
                        await unlink(temporaryPath);
                        await writeFile(temporaryPath, foreignBytes);
                        throw new Error("Synthetic failure after temporary substitution");
                      },
                    }
                  : {
                      beforeReplace: async (temporaryPath) => {
                        foreignTemporaryPath = temporaryPath;
                        await unlink(temporaryPath);
                        await writeFile(temporaryPath, foreignBytes);
                      },
                    },
              );
            },
          }),
        );

        expect(await readFile(reportPath)).toEqual(previousBytes);
        if (foreignTemporaryPath === undefined) {
          throw new Error("The synthetic substitution did not run");
        }
        expect(await readFile(foreignTemporaryPath)).toEqual(foreignBytes);
      } finally {
        await rm(directory, { recursive: true, force: true });
      }
    },
  );

  test("publishes the complete synthetic report after successful replacement", async () => {
    const directory = `.ai-engineering/triage-report-test-${randomUUID()}`;
    const reportPath = `${directory}/triage.html`;
    const previousBytes = Buffer.from(existingReport);
    const inventory = createSyntheticInventory();
    let completeReport: string | undefined;
    await mkdir(directory);

    try {
      await writeFile(reportPath, previousBytes);

      await writeAzureTriageReport({
        scope: createSyntheticScope(),
        inventory,
        analyzeItem: async () => ({ status: "UNASSESSED" }),
        writeFile: async (path, contents) => {
          expect(path).toBe(targetReport);
          completeReport = contents;
          await atomicWriteReport(reportPath, contents);
        },
      });

      if (completeReport === undefined) {
        throw new Error("The synthetic report writer did not provide the complete report");
      }
      expect(completeReport.match(/class="item(?:\s|")/g)).toHaveLength(
        inventory.items.length,
      );
      expect(completeReport).toContain("Synthetic backlog item 208");
      expect(completeReport).toContain("</html>");
      expect(await readFile(reportPath)).toEqual(Buffer.from(completeReport));
      expect(await readFile(reportPath)).not.toEqual(previousBytes);
      expect(await readdir(directory)).toEqual(["triage.html"]);
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  test.each([
    {
      label: "an explicitly incomplete inventory",
      inventory: { complete: false, items: createSyntheticInventory().items },
    },
    {
      label: "an inventory with unknown completeness",
      inventory: { items: createSyntheticInventory().items },
    },
  ])("does not replace the existing report for $label", async ({ inventory }) => {
    const reportWriter = createMemoryReportWriter();

    await expectNoSuccessShapedResult(() =>
      writeAzureTriageReport({
        scope: createSyntheticScope(),
        inventory,
        analyzeItem: async () => ({ status: "ASSESSED" }),
        writeFile: reportWriter.writeFile,
      }),
    );

    expect(reportWriter.reports.get(targetReport)).toBe(existingReport);
    expect(reportWriter.writes).toEqual([]);
  });

  test.each([
    {
      label: "evidence URL with a bearer fragment",
      kind: "evidence",
      url: "https://evidence.example.test/items/42#%62earer%3Dsynthetic-secret",
    },
    {
      label: "malformed evidence URL",
      kind: "evidence",
      url: "https://evidence.example.test/items/%ZZ",
    },
    {
      label: "unsafe relationship URL",
      kind: "relationship",
      url: "javascript:alert(1)",
    },
    {
      label: "unvalidated relationship URL",
      kind: "relationship",
      url: "https://evidence.example.test/not-a-work-item",
    },
  ] as const)(
    "preserves the report with a plain-text fallback for $label",
    async ({ kind, url }) => {
      const inventory = createSyntheticInventory();
      if (kind === "relationship") {
        const firstItem = inventory.items[0];
        if (firstItem === undefined) throw new Error("Expected a synthetic work item");
        firstItem.relations = [
          { rel: "System.LinkTypes.Hierarchy-Reverse", url },
        ];
      }
      const reportWriter = createMemoryReportWriter();

      await writeAzureTriageReport({
        scope: createSyntheticScope(),
        inventory,
        analyzeItem: async (item: SyntheticWorkItem) => ({
          status: "ASSESSED",
          priority: "P2",
          summary: `Synthetic analysis for item ${item.id}`,
          evidence:
            kind === "evidence"
              ? [{ label: "Synthetic evidence label", url }]
              : [],
        }),
        writeFile: reportWriter.writeFile,
      });

      const generatedReport = reportWriter.reports.get(targetReport);
      if (generatedReport === undefined) {
        throw new Error("The synthetic report writer did not store the target report");
      }
      expect(reportWriter.writes).toHaveLength(1);
      expect(generatedReport).not.toContain(url);
      expect(generatedReport).not.toContain("synthetic-secret");
      expect(generatedReport).toContain(
        'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201"',
      );
      expect(generatedReport).toContain('target="_blank" rel="noreferrer noopener"');
      if (kind === "evidence") {
        expect(generatedReport).toContain("Synthetic evidence label");
      } else {
        expect(generatedReport).toContain('class="tree-row tree-parent"');
        expect(generatedReport).toContain(" work item</div>");
      }
    },
  );

  test("ranks Azure priority and severity ahead of workflow state and analysis guesses", async () => {
    const inventory = createSyntheticInventory();
    inventory.items[0]!.fields["System.State"] = "Resolved";
    inventory.items[1]!.fields["System.State"] = "Backlog";
    inventory.items[2]!.fields["Microsoft.VSTS.Common.Priority"] = 4;
    inventory.items[2]!.fields["Microsoft.VSTS.Common.Severity"] = "1 - Critical";
    const reportWriter = createMemoryReportWriter();

    await writeAzureTriageReport({
      scope: createSyntheticScope(),
      inventory,
      analyzeItem: async (item: SyntheticWorkItem) => ({
        status: "ASSESSED",
        priority: item.id === 201 ? "P0" : "P5",
        summary: `Synthetic analysis for item ${item.id}`,
      }),
      writeFile: reportWriter.writeFile,
    });

    const report = reportWriter.reports.get(targetReport);
    if (report === undefined) throw new Error("The synthetic report was not written");
    const rankedSection = report.match(/<section id="s02">([\s\S]*?)<\/section>/)?.[1] ?? "";
    const rankedIds = [...rankedSection.matchAll(/id="i(\d+)"/g)].map((match) => match[1]);
    expect(rankedIds.slice(0, 3)).toEqual(["203", "202", "201"]);
    expect(rankedSection).toContain('<span class="band band-p0">P0</span>');
    expect(rankedSection).toContain('<span class="band band-p1">P1</span>');
    expect(rankedSection).toContain('<span class="band band-p2">P2</span>');
  });
});
