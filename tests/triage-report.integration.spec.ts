import { randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { describe, expect, test } from "bun:test";
import {
  atomicWriteReport,
  writeAzureTriageReport,
} from "../skills/ai-triage/scripts/render-report.mjs";

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
  };
  relations?: Array<{ rel: string; url: string }>;
};

function createSyntheticInventory() {
  const itemIds = [201, 202, 203, 204, 205, 206, 207, 208];
  const items: SyntheticWorkItem[] = itemIds.map((id, index) => ({
    id,
    fields: {
      "System.WorkItemType": index % 2 === 0 ? "Feature" : "Task",
      "System.State": index % 2 === 0 ? "Ready for planning" : "In progress",
      "System.Title":
        index === 2 ? "<img src=x onerror=alert(1)>" : `Synthetic backlog item ${id}`,
      "System.Description":
        index === 3
          ? "</span><script>window.syntheticAttack=true</script>"
          : `Synthetic description for item ${id}`,
      "System.AreaPath": "Synthetic Project\\Delivery",
    },
    ...(index === 0
      ? {
          relations: [
            {
              rel: "System.LinkTypes.Hierarchy-Reverse",
              url: `${syntheticOrganization}/synthetic-project/_apis/wit/workItems/901`,
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
          summary: `Synthetic analysis for item ${item.id}`,
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
    expect(generatedReport).toMatch(/<h[2-3][^>]*>[^<]*related/i);
    expect(generatedReport).toMatch(/<h[2-3][^>]*>[^<]*method/i);
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
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_workitems/edit/201"',
    );
    expect(generatedReport).toContain(
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_apis/wit/workItems/201"',
    );
    expect(generatedReport).not.toContain(
      "<img src=x onerror=alert(1)>",
    );
    expect(generatedReport).not.toContain(
      "</span><script>window.syntheticAttack=true</script>",
    );
    expect(generatedReport).toContain(
      "&lt;img src=x onerror=alert(1)&gt; [redacted]",
    );
    expect(generatedReport).not.toContain("<img src=x onerror=alert(1)>");
    expect(generatedReport).not.toContain(syntheticToken);
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
      'href="https://dev.azure.com/synthetic-org/synthetic-project/_apis/wit/workItems/201"',
    );
    for (const linkMatch of generatedReport.matchAll(/\bhref="([^"]*)"/g)) {
      expect(linkMatch[1] ?? "").not.toContain(syntheticToken);
    }
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
        'href="https://dev.azure.com/synthetic-org/synthetic-project/_apis/wit/workItems/201"',
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
        'href="https://dev.azure.com/synthetic-org/synthetic-project/_apis/wit/workItems/201"',
      );
    },
  );

  test.each(["write", "replace"] as const)(
    "preserves previous report bytes when temporary %s fails",
    async (failureStage) => {
      const directory = `.ai-engineering/triage-report-test-${randomUUID()}`;
      const reportPath = `${directory}/triage.html`;
      const previousBytes = Buffer.from(existingReport);
      await mkdir(directory);

      try {
        await writeFile(reportPath, previousBytes);
        const operations: NonNullable<Parameters<typeof atomicWriteReport>[2]> =
          failureStage === "write"
            ? {
                writeTemporaryFile: async (handle) => {
                  await handle.writeFile("partial synthetic report", "utf8");
                  throw new Error("Synthetic temporary write failure");
                },
              }
            : {
                replaceFile: async () => {
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
        expect(await readdir(directory)).toEqual(["triage.html"]);
      } finally {
        await rm(directory, { recursive: true, force: true });
      }
    },
  );

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

  test("does not replace the existing report when rendering rejects an unsafe link", async () => {
    const inventory = createSyntheticInventory();
    const firstItem = inventory.items[0];
    if (firstItem === undefined) throw new Error("Expected a synthetic work item");
    const invalidLinkInventory = {
      ...inventory,
      items: [
        {
          ...firstItem,
          relations: [
            {
              rel: "System.LinkTypes.Hierarchy-Reverse",
              url: "javascript:alert(1)",
            },
          ],
        },
        ...inventory.items.slice(1),
      ],
    };
    const reportWriter = createMemoryReportWriter();

    await expectNoSuccessShapedResult(() =>
      writeAzureTriageReport({
        scope: createSyntheticScope(),
        inventory: invalidLinkInventory,
        analyzeItem: async () => ({ status: "ASSESSED" }),
        writeFile: reportWriter.writeFile,
      }),
    );

    expect(reportWriter.reports.get(targetReport)).toBe(existingReport);
    expect(reportWriter.writes).toEqual([]);
  });

  test("does not write or expose a rejected evidence URL with bearer credentials", async () => {
    const reportWriter = createMemoryReportWriter();
    const syntheticToken = "github_pat_syntheticToken1234567890";
    const unsafeUrl =
      `https://evidence.example.test/items/42?view=Bearer%2520${syntheticToken}`;

    await expectNoSuccessShapedResult(() =>
      writeAzureTriageReport({
        scope: createSyntheticScope(),
        inventory: createSyntheticInventory(),
        analyzeItem: async (item: SyntheticWorkItem) => ({
          status: "ASSESSED",
          priority: "P2",
          summary: `Synthetic analysis for item ${item.id}`,
          evidence: [{ label: "Synthetic evidence", url: unsafeUrl }],
        }),
        writeFile: reportWriter.writeFile,
      }),
    );

    expect(reportWriter.reports.get(targetReport)).toBe(existingReport);
    expect(reportWriter.writes).toEqual([]);
    expect(
      [...reportWriter.reports.values()].some((report) => report.includes(unsafeUrl)),
    ).toBe(false);
  });
});
