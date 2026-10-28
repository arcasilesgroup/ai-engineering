/** Workflow kit checkpoints 5 and 7 — install artifacts and viewer poll loop. */
import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { materializeScripts } from "../src/embed.ts";

const ROOT = join(import.meta.dir, "..");

describe("workflow kit — install artifacts and viewer poll loop", () => {
  test("install materializes no Python checkpoint-gate script", () => {
    const scriptsDir = mkdtempSync(join(import.meta.dir, ".workflow-doctor-scripts-"));
    try {
      materializeScripts(scriptsDir);
      expect(existsSync(join(scriptsDir, "checkpoint-gate.py"))).toBe(false);
    } finally {
      rmSync(scriptsDir, { recursive: true, force: true });
    }
  });

  test("viewer still polls with setInterval(tick", () => {
    const viewer = readFileSync(
      join(ROOT, ".ai-engineering", "workflow", "checkpoints", "viewer.html"),
      "utf8",
    );
    expect(viewer).toContain("setInterval(tick");
  });
});
