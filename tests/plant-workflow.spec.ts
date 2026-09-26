// tests/plant-workflow.spec.ts — plant-if-absent standing workflow files.

import { afterEach, describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { plantWorkflowFiles } from "../src/commands/plant-workflow.ts";

const roots: string[] = [];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-plant-"));
  roots.push(root);
  return root;
}

const PLANTED = [
  "LEARNINGS.md",
  "FILEMAP.md",
  "PERMISSIONS.md",
  "CHANGELOG.md",
  ".ai-engineering/PRD.html",
  ".ai-engineering/workflow/checkpoints/viewer.html",
] as const;

describe("plantWorkflowFiles", () => {
  test("creates standing files when absent", () => {
    const root = tempRoot();
    plantWorkflowFiles(root);

    for (const relative of PLANTED) {
      const absolute = join(root, relative);
      expect(statSync(absolute).isFile()).toBe(true);
    }

    const changelog = readFileSync(join(root, "CHANGELOG.md"), "utf8");
    expect(changelog).toContain("Keep a Changelog");
    expect(changelog).toContain("## [Unreleased]");

    const permissions = readFileSync(join(root, "PERMISSIONS.md"), "utf8");
    expect(permissions.toLowerCase()).toContain("n/a");

    const viewer = readFileSync(join(root, ".ai-engineering/workflow/checkpoints/viewer.html"), "utf8");
    expect(viewer).toContain("#001E2B");
    expect(viewer).toContain("#00ED64");
    expect(viewer).toContain("setInterval");
    expect(viewer).not.toContain("fonts.googleapis.com");
  });

  test("does not change existing DECISIONS.md or CHANGELOG.md bytes", () => {
    const root = tempRoot();
    const decisions = "# DECISIONS\ncustom-marker-decisions-xyz\n";
    const changelog = "# Changelog\ncustom-marker-changelog-xyz\n";
    writeFileSync(join(root, "DECISIONS.md"), decisions);
    writeFileSync(join(root, "CHANGELOG.md"), changelog);

    plantWorkflowFiles(root);

    expect(readFileSync(join(root, "DECISIONS.md"), "utf8")).toBe(decisions);
    expect(readFileSync(join(root, "CHANGELOG.md"), "utf8")).toBe(changelog);
    expect(statSync(join(root, "LEARNINGS.md")).isFile()).toBe(true);
  });

  test("a second call does not rewrite files it already created", () => {
    const root = tempRoot();
    plantWorkflowFiles(root);

    const before = new Map(
      PLANTED.map((relative) => [relative, readFileSync(join(root, relative), "utf8")] as const),
    );

    const learningsPath = join(root, "LEARNINGS.md");
    writeFileSync(learningsPath, `${before.get("LEARNINGS.md")}\n<!-- touched -->\n`);
    const touched = readFileSync(learningsPath, "utf8");

    plantWorkflowFiles(root);

    expect(readFileSync(learningsPath, "utf8")).toBe(touched);
    for (const relative of PLANTED) {
      if (relative === "LEARNINGS.md") continue;
      const prior = before.get(relative) ?? "";
      expect(prior.length).toBeGreaterThan(0);
      expect(readFileSync(join(root, relative), "utf8")).toBe(prior);
    }
  });
});
