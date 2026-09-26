/**
 * Workflow kit checkpoint 7 — doctor tells the truth about Zed vs denying surfaces.
 *
 * Red until checkpoint-gate-report exists and names Zed gate unenforced while at
 * least one denying carrier (claude-code or cursor) that still runs ai-eng chain
 * reports chain active. Also pins the viewer poll loop.
 */
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { checkpointGateReportLines } from "../src/commands/checkpoint-gate-report.ts";

const ROOT = join(import.meta.dir, "..");

type SurfaceRow = {
  id: string;
  carriers: unknown[];
  can: { deny: boolean | "throw" | "host-only" };
};

const TEMPLATE_BY_SURFACE: Record<string, string> = {
  "claude-code": "settings.claude.json.tpl",
  cursor: "settings.cursor.json.tpl",
  codex: "settings.codex.json.tpl",
  "copilot-cli": "settings.copilot.cli.json.tpl",
  opencode: "plugin.opencode.ts.tpl",
  "oh-my-pi": "plugin.omp.ts.tpl",
  pi: "plugin.pi.ts.tpl",
};

describe("workflow kit — doctor surface truth for checkpoint gate", () => {
  test("report lines: Zed unenforced and a denying surface still chain active", () => {
    const catalog = JSON.parse(readFileSync(join(ROOT, "src", "surfaces", "surfaces.json"), "utf8")) as {
      surfaces: SurfaceRow[];
    };
    const templates: Record<string, string> = {};
    for (const [id, file] of Object.entries(TEMPLATE_BY_SURFACE)) {
      templates[id] = readFileSync(join(ROOT, "templates", file), "utf8");
    }

    const lines = checkpointGateReportLines(catalog.surfaces, templates);
    const joined = lines.join("\n");

    expect(joined).toMatch(/checkpoint gate unenforced/i);
    expect(joined).toMatch(/Zed/i);
    expect(joined).toMatch(/chain active/i);
    expect(joined).toMatch(/claude-code|cursor/i);
  });

  test("viewer still polls with setInterval(tick", () => {
    const viewer = readFileSync(
      join(ROOT, ".ai-engineering", "workflow", "checkpoints", "viewer.html"),
      "utf8",
    );
    expect(viewer).toContain("setInterval(tick");
  });
});
