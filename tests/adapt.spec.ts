// tests/adapt.spec.ts — the human review contract for project proposals.

import { describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { adaptApply, adaptMain, proposalHtml } from "../src/commands/adapt.ts";

describe("adapt apply", () => {
  test("skill contract", () => {
    const text = readFileSync(join(import.meta.dir, "..", "skills", "ai-config-to-project", "SKILL.md"), "utf8");
    expect(text).toContain("disable-model-invocation: true");
    expect(text).toContain("If the person did not invoke this skill by name, stop.");
    expect(text).toContain("Security, Lifecycle, Anti-drift, Voice");
    expect(text).toContain("The person applies the approved changes manually outside the governed agent session.");
    expect(text).toContain("`ai-eng adapt apply` is intentionally disabled");
    expect(text).not.toContain("Cursor honors");
    expect(text).not.toContain("Pi honors");
    expect(text).not.toContain("Codex honors");
  });

  test("a valid self-hashed proposal cannot write protected files through any entry point", () => {
    const root = mkdtempSync(join(tmpdir(), "ai-eng-adapt-"));
    const configPath = join(root, ".ai-engineering", "config.toml");
    const proposalPath = join(root, ".ai-engineering", "config-proposal.html");
    const originalConfig = '[surfaces]\nenabled = ["claude-code"]\n';
    mkdirSync(join(root, ".ai-engineering"), { recursive: true });
    writeFileSync(configPath, originalConfig);
    writeFileSync(proposalPath, proposalHtml({ ".ai-engineering/config.toml": "# governance removed\n" }));

    const previousCwd = process.cwd();
    const errors: string[] = [];
    const originalStderr = process.stderr.write;
    process.chdir(root);
    process.stderr.write = ((chunk: unknown) => {
      errors.push(String(chunk));
      return true;
    }) as typeof process.stderr.write;
    try {
      expect(adaptApply(root)).toBe(2);
      expect(adaptMain(["apply"])).toBe(2);
      expect(readFileSync(configPath, "utf8")).toBe(originalConfig);
      expect(existsSync(proposalPath)).toBe(true);
    } finally {
      process.stderr.write = originalStderr;
      process.chdir(previousCwd);
      rmSync(root, { recursive: true, force: true });
    }

    expect(errors.join("")).toContain("hash cannot prove human approval");
  });
});
