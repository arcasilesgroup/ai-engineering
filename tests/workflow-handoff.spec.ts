import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");

function lifecycle(path: string): string {
  const text = readFileSync(join(root, path), "utf8");
  const block = text.split("## Lifecycle")[1] ?? "";
  return block.split("\n## ")[0] ?? "";
}

describe("workflow kit — feature work hands off to ai-orchestrator", () => {
  test("ai-brainstorm Lifecycle names ai-orchestrator", () => {
    expect(lifecycle("skills/ai-brainstorm/SKILL.md")).toContain("ai-orchestrator");
  });

  test("ai-orchestrator owns the approve stop", () => {
    const block = lifecycle("skills/ai-orchestrator/SKILL.md");
    expect(block).toContain("Stop: approve");
    expect(block).toContain("approve");
  });
});
