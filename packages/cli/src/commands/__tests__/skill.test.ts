import { describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { skill } from "../skill.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const writeSkill = (
  root: string,
  name: string,
  frontmatter: Readonly<Record<string, string>>,
): void => {
  const dir = join(root, "skills", "catalog", name);
  mkdirSync(dir, { recursive: true });
  const body = [
    "---",
    `name: ${frontmatter.name ?? name}`,
    `description: ${frontmatter.description ?? "x"}`,
    `effort: ${frontmatter.effort ?? "medium"}`,
    `tier: ${frontmatter.tier ?? "core"}`,
    "---",
    "",
    "body",
    "",
  ].join("\n");
  writeFileSync(join(dir, "SKILL.md"), body, "utf8");
};

describe("skill list — happy path", () => {
  test("prints all skills with frontmatter metadata", async () => {
    await withTmpCwd("ai-eng-skill-list-", async (root) => {
      writeSkill(root, "alpha", {
        description: "Alpha skill",
        effort: "high",
        tier: "core",
      });
      writeSkill(root, "beta", {
        description: "Beta skill",
        effort: "low",
        tier: "regulated",
      });
      const result = await capture(() => skill(["list"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/alpha/);
      expect(result.stdout).toMatch(/beta/);
      expect(result.stdout).toMatch(/regulated/);
    });
  });

  test("--json emits structured list", async () => {
    await withTmpCwd("ai-eng-skill-list-json-", async (root) => {
      writeSkill(root, "alpha", { description: "A" });
      const result = await capture(() => skill(["list", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.skills).toBeInstanceOf(Array);
      expect(parsed.skills[0].name).toBe("alpha");
    });
  });

  test("empty catalog returns 0 with friendly message", async () => {
    await withTmpCwd("ai-eng-skill-list-empty-", async () => {
      const result = await capture(() => skill(["list"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/no skills/i);
    });
  });
});

describe("skill new — happy path", () => {
  test("scaffolds SKILL.md from template", async () => {
    await withTmpCwd("ai-eng-skill-new-", async (root) => {
      const result = await capture(() => skill(["new", "my-skill"]));
      expect(result.exitCode).toBe(0);
      const path = join(root, "skills", "catalog", "my-skill", "SKILL.md");
      expect(existsSync(path)).toBe(true);
      const body = readFileSync(path, "utf8");
      expect(body).toMatch(/name: my-skill/);
      expect(body).toMatch(/effort: medium/);
    });
  });

  test("rejects existing skill", async () => {
    await withTmpCwd("ai-eng-skill-new-dupe-", async (root) => {
      writeSkill(root, "exists", {});
      const result = await capture(() => skill(["new", "exists"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/already exists/);
    });
  });

  test("rejects invalid name", async () => {
    await withTmpCwd("ai-eng-skill-new-invalid-", async () => {
      const result = await capture(() => skill(["new", "InvalidName"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/invalid skill name/);
    });
  });

  test("missing name returns exit 1", async () => {
    await withTmpCwd("ai-eng-skill-new-missing-", async () => {
      const result = await capture(() => skill(["new"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});

describe("skill audit — happy path", () => {
  test("valid skills return 0 with all OK", async () => {
    await withTmpCwd("ai-eng-skill-audit-ok-", async (root) => {
      writeSkill(root, "good", {
        description: "Good skill",
        effort: "high",
        tier: "core",
      });
      const result = await capture(() => skill(["audit"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/\[OK\]/);
    });
  });

  test("invalid manifest returns exit 2", async () => {
    await withTmpCwd("ai-eng-skill-audit-fail-", async (root) => {
      const dir = join(root, "skills", "catalog", "broken");
      mkdirSync(dir, { recursive: true });
      writeFileSync(
        join(dir, "SKILL.md"),
        ["---", "name: broken", "---", "", "body", ""].join("\n"),
        "utf8",
      );
      const result = await capture(() => skill(["audit"]));
      expect(result.exitCode).toBe(2);
      expect(result.stdout).toMatch(/FAIL/);
    });
  });

  test("--json emits structured entries", async () => {
    await withTmpCwd("ai-eng-skill-audit-json-", async (root) => {
      writeSkill(root, "good", {
        description: "x",
        effort: "high",
        tier: "core",
      });
      const result = await capture(() => skill(["audit", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.entries[0].status).toBe("pass");
    });
  });
});

describe("skill — error paths", () => {
  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-skill-unknown-", async () => {
      const result = await capture(() => skill(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown/i);
    });
  });

  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-skill-noargs-", async () => {
      const result = await capture(() => skill([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
