import { describe, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { llm } from "../llm.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const writeManifest = (root: string, body: unknown): void => {
  const dir = join(root, ".ai-engineering");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "manifest.json"), JSON.stringify(body, null, 2), "utf8");
};

describe("llm list-providers — happy path", () => {
  test("default piggyback provider when manifest missing", async () => {
    await withTmpCwd("ai-eng-llm-default-", async () => {
      const result = await capture(() => llm(["list-providers"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/claude-code/);
      expect(result.stdout).toMatch(/piggyback/);
    });
  });

  test("--json emits the configured shape", async () => {
    await withTmpCwd("ai-eng-llm-json-", async (root) => {
      writeManifest(root, {
        llm: {
          mode: "byok",
          privacy_tier: "regulated",
          providers: [{ id: "anthropic", method: "byok" }],
        },
      });
      const result = await capture(() => llm(["list-providers", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.mode).toBe("byok");
      expect(parsed.providers[0].id).toBe("anthropic");
    });
  });
});

describe("llm route show / cost report / test — stubs", () => {
  test("route show returns 0", async () => {
    await withTmpCwd("ai-eng-llm-route-", async () => {
      const result = await capture(() => llm(["route", "show"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/route show/);
    });
  });

  test("cost report returns 0 (stub)", async () => {
    await withTmpCwd("ai-eng-llm-cost-", async () => {
      const result = await capture(() => llm(["cost", "report"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/cost report/);
    });
  });

  test("test returns 0 (stub)", async () => {
    await withTmpCwd("ai-eng-llm-test-", async () => {
      const result = await capture(() => llm(["test"]));
      expect(result.exitCode).toBe(0);
    });
  });
});

describe("llm — error paths", () => {
  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-llm-unknown-", async () => {
      const result = await capture(() => llm(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown/i);
    });
  });

  test("route without 'show' returns exit 1", async () => {
    await withTmpCwd("ai-eng-llm-route-bad-", async () => {
      const result = await capture(() => llm(["route", "stuff"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });

  test("cost without 'report' returns exit 1", async () => {
    await withTmpCwd("ai-eng-llm-cost-bad-", async () => {
      const result = await capture(() => llm(["cost", "blah"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });

  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-llm-noargs-", async () => {
      const result = await capture(() => llm([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
