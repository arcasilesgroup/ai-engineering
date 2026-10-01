// tests/git-cleanup-pass.spec.ts — document check of the rewritten ai-git-cleanup skill
// (git-worktree-flow test plan, cli layer, checkpoint 4; C15-C18). This pins the prose the
// rewrite must carry, reading SKILL.md as a document — it drives no script, because the
// script the old skill shipped is deleted and no executable code remains behind the verb.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const skill = readFileSync(join(import.meta.dir, "..", "skills", "ai-git-cleanup", "SKILL.md"), "utf8");

describe("ai-git-cleanup skill — the one-pass, name-free rewrite", () => {
  test("documents the merged-branch delete with the explicit main ref", () => {
    expect(skill).toContain("git branch --delete-merged refs/heads/main");
  });

  test("documents the --merged main + -d fallback for branches without that upstream", () => {
    expect(skill).toContain("git branch --merged main");
  });

  test("never force-deletes: -D appears nowhere in the skill", () => {
    expect(skill).not.toContain("-D");
  });

  test("asks for no name and has no interactive question", () => {
    // The old prompt words must be gone...
    expect(skill).not.toContain("asks you once");
    expect(skill).not.toMatch(/the one ask/i);
    // ...and the rewrite must say it never asks.
    expect(skill).toMatch(/never asks|no name is ever asked|asks for no name|no interactive question/i);
  });

  test("keeps a Lifecycle block", () => {
    expect(skill).toContain("## Lifecycle");
  });
});
