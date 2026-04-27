import { describe, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { migrate } from "../migrate.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

describe("migrate v2-to-v3 — happy path", () => {
  test("dry-run prints planned moves and returns 0", async () => {
    await withTmpCwd("ai-eng-migrate-", async (root) => {
      // create a v2-style sentinel
      const v2 = join(root, ".ai-engineering");
      mkdirSync(v2, { recursive: true });
      writeFileSync(join(v2, "manifest.yml"), "name: legacy\n", "utf8");
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/dry-run/);
      expect(result.stdout).toMatch(/manifest\.yml/);
    });
  });

  test("--json emits structured plan", async () => {
    await withTmpCwd("ai-eng-migrate-json-", async () => {
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.plan).toBeInstanceOf(Array);
      expect(parsed.plan.length).toBeGreaterThan(0);
    });
  });
});

describe("migrate v2-to-v3 — error paths", () => {
  test("without --dry-run returns exit 1", async () => {
    await withTmpCwd("ai-eng-migrate-nodry-", async () => {
      const result = await capture(() => migrate(["v2-to-v3"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/not yet implemented|dry-run/i);
    });
  });

  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-migrate-unknown-", async () => {
      const result = await capture(() => migrate(["v9-to-v10"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown/i);
    });
  });

  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-migrate-noargs-", async () => {
      const result = await capture(() => migrate([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
