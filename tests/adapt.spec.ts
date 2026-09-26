// tests/adapt.spec.ts — ai-eng adapt apply and the manual skill contract.
// Identity comes from the temp repo's local git config. GIT_CONFIG_GLOBAL points
// at an empty file so the developer's ~/.gitconfig cannot satisfy user.name.

import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { adaptApply, proposalHtml } from "../src/commands/adapt.ts";

const previousGlobal = process.env["GIT_CONFIG_GLOBAL"];
const roots: string[] = [];

afterEach(() => {
  if (previousGlobal === undefined) delete process.env["GIT_CONFIG_GLOBAL"];
  else process.env["GIT_CONFIG_GLOBAL"] = previousGlobal;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function repo(): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-adapt-"));
  roots.push(root);
  const global = join(root, "empty-gitconfig");
  writeFileSync(global, "");
  process.env["GIT_CONFIG_GLOBAL"] = global;
  spawnSync("git", ["init", "-q"], { cwd: root });
  mkdirSync(join(root, ".ai-engineering"), { recursive: true });
  return root;
}

function identify(root: string, name = "Ada Lovelace", email = "ada@example.com"): void {
  spawnSync("git", ["config", "user.name", name], { cwd: root });
  spawnSync("git", ["config", "user.email", email], { cwd: root });
}

function kitRules(): string {
  return `${JSON.stringify({ layers: { kit: "kit/src/**" }, rules: [], bootstrap: "allow-empty-while-files==0" }, null, 2)}\n`;
}

describe("adapt apply", () => {
  test("skill contract", () => {
    const text = readFileSync(join(import.meta.dir, "..", "skills", "ai-config-to-project", "SKILL.md"), "utf8");
    expect(text).toContain("disable-model-invocation: true");
    expect(text).toContain("If the person did not invoke this skill by name, stop.");
    expect(text).toContain("ai-eng adapt apply");
    expect(text).toContain("Security, Lifecycle, Anti-drift, Voice");
    expect(text).not.toContain("Cursor honors");
    expect(text).not.toContain("Pi honors");
    expect(text).not.toContain("Codex honors");
  });

  test("refuses an empty git name", () => {
    const root = repo();
    writeFileSync(join(root, ".ai-engineering", "config-proposal.html"), proposalHtml({ "AGENTS.md": "# x\n" }));
    const errors: string[] = [];
    const original = process.stderr.write;
    process.stderr.write = ((chunk: unknown) => {
      errors.push(String(chunk));
      return true;
    }) as typeof process.stderr.write;
    try {
      expect(adaptApply(root)).toBe(2);
    } finally {
      process.stderr.write = original;
    }
    expect(errors.join("")).toContain("user.name");
  });

  test("refuses an override without until", () => {
    const root = repo();
    identify(root);
    const overrides = '[[guard.off]]\nname = "loop"\nreason = "batch"\n';
    writeFileSync(
      join(root, ".ai-engineering", "config-proposal.html"),
      proposalHtml({ ".ai-engineering/overrides.toml": overrides }),
    );
    const errors: string[] = [];
    const original = process.stderr.write;
    process.stderr.write = ((chunk: unknown) => {
      errors.push(String(chunk));
      return true;
    }) as typeof process.stderr.write;
    try {
      expect(adaptApply(root)).toBe(2);
    } finally {
      process.stderr.write = original;
    }
    expect(errors.join("")).toContain("until");
    expect(readFileSync(join(root, ".ai-engineering", "config-proposal.html"), "utf8").length).toBeGreaterThan(0);
  });

  test("refuses a changed proposal", () => {
    const root = repo();
    identify(root);
    const html = proposalHtml({ ".ai-engineering/arch.rules.json": kitRules() }).replace("kit/src/**", "kit/src/** ");
    writeFileSync(join(root, ".ai-engineering", "config-proposal.html"), html);
    const errors: string[] = [];
    const original = process.stderr.write;
    process.stderr.write = ((chunk: unknown) => {
      errors.push(String(chunk));
      return true;
    }) as typeof process.stderr.write;
    try {
      expect(adaptApply(root)).toBe(2);
    } finally {
      process.stderr.write = original;
    }
    expect(errors.join("")).toContain("sha256");
  });

  test("commits Approved-by", () => {
    const root = repo();
    identify(root);
    writeFileSync(
      join(root, ".ai-engineering", "config-proposal.html"),
      proposalHtml({ ".ai-engineering/arch.rules.json": kitRules() }),
    );
    expect(adaptApply(root)).toBe(0);
    const log = spawnSync("git", ["log", "-1", "--format=%B"], { cwd: root, encoding: "utf8" });
    expect(log.stdout).toContain("Approved-by: Ada Lovelace <ada@example.com>");
  });

  test("commit goes through the hook", () => {
    const root = repo();
    identify(root);
    const hook = join(root, ".git", "hooks", "commit-msg");
    mkdirSync(join(root, ".git", "hooks"), { recursive: true });
    writeFileSync(hook, "#!/bin/sh\nexit 1\n");
    chmodSync(hook, 0o755);
    writeFileSync(
      join(root, ".ai-engineering", "config-proposal.html"),
      proposalHtml({ ".ai-engineering/arch.rules.json": kitRules() }),
    );
    expect(adaptApply(root)).toBe(2);
    const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" });
    expect(head.status).not.toBe(0);
  });

  test("second apply keeps project layers", () => {
    const root = repo();
    identify(root);
    writeFileSync(
      join(root, ".ai-engineering", "config-proposal.html"),
      proposalHtml({ ".ai-engineering/arch.rules.json": kitRules() }),
    );
    expect(adaptApply(root)).toBe(0);
    expect(adaptApply(root)).toBe(0);
    const rules = JSON.parse(readFileSync(join(root, ".ai-engineering", "arch.rules.json"), "utf8")) as {
      layers: Record<string, string>;
    };
    expect(rules.layers["kit"]).toBe("kit/src/**");
    expect(rules.layers["cli"]).toBeUndefined();
  });
});
