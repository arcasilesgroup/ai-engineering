import { describe, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { governance } from "../governance.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const writeManifest = (root: string, body: unknown): void => {
  const dir = join(root, ".ai-engineering");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "manifest.json"), JSON.stringify(body, null, 2), "utf8");
};

describe("governance audit — happy path", () => {
  test("valid skill manifest returns 0 with OK output", async () => {
    await withTmpCwd("ai-eng-gov-ok-", async (root) => {
      writeManifest(root, {
        name: "specify",
        description: "Use when designing a feature.",
        effort: "high",
        tier: "core",
      });
      const result = await capture(() => governance(["audit"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/governance audit/);
      expect(result.stdout).toMatch(/\[OK\]/);
    });
  });

  test("--json emits structured findings", async () => {
    await withTmpCwd("ai-eng-gov-json-", async (root) => {
      writeManifest(root, {
        name: "specify",
        description: "x",
        effort: "high",
        tier: "core",
      });
      const result = await capture(() => governance(["audit", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.findings).toBeInstanceOf(Array);
      expect(parsed.findings[0].status).toBe("pass");
    });
  });

  test("no manifest at all returns 0 (nothing to audit)", async () => {
    await withTmpCwd("ai-eng-gov-empty-", async () => {
      const result = await capture(() => governance(["audit"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/no manifests/i);
    });
  });
});

describe("governance audit — error paths", () => {
  test("invalid manifest returns exit 2 with FAIL marker", async () => {
    await withTmpCwd("ai-eng-gov-bad-", async (root) => {
      writeManifest(root, {
        // missing required fields
        description: "x",
      });
      const result = await capture(() => governance(["audit"]));
      expect(result.exitCode).toBe(2);
      expect(result.stdout).toMatch(/FAIL/);
    });
  });

  test("malformed JSON returns exit 2", async () => {
    await withTmpCwd("ai-eng-gov-malformed-", async (root) => {
      const dir = join(root, ".ai-engineering");
      mkdirSync(dir, { recursive: true });
      writeFileSync(join(dir, "manifest.json"), "{not json", "utf8");
      const result = await capture(() => governance(["audit"]));
      expect(result.exitCode).toBe(2);
      expect(result.stdout).toMatch(/FAIL/);
    });
  });

  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-gov-unknown-", async () => {
      const result = await capture(() => governance(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown/i);
    });
  });

  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-gov-noargs-", async () => {
      const result = await capture(() => governance([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
