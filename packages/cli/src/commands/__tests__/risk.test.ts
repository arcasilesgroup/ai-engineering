import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { risk } from "../risk.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

describe("risk accept — happy path", () => {
  test("persists a Decision to .ai-engineering/state/decision-store.json", async () => {
    await withTmpCwd("ai-eng-risk-", async (root) => {
      const result = await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "CVE-2026-1234",
          "--severity",
          "high",
          "--justification",
          "False positive in fixture",
          "--owner",
          "alice@example.com",
          "--spec-ref",
          "spec-099",
        ]),
      );
      expect(result.exitCode).toBe(0);
      const storePath = join(root, ".ai-engineering", "state", "decision-store.json");
      expect(existsSync(storePath)).toBe(true);
      const store = JSON.parse(readFileSync(storePath, "utf8"));
      expect(store).toHaveProperty("decisions");
      expect(Array.isArray(store.decisions)).toBe(true);
      expect(store.decisions).toHaveLength(1);
      expect(store.decisions[0].findingId).toBe("CVE-2026-1234");
      expect(store.decisions[0].severity).toBe("high");
      expect(store.decisions[0].owner).toBe("alice@example.com");
      expect(store.decisions[0].specRef).toBe("spec-099");
    });
  });

  test("emits JSON when --json flag is set", async () => {
    await withTmpCwd("ai-eng-risk-json-", async () => {
      const result = await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "CVE-2026-9",
          "--severity",
          "low",
          "--justification",
          "x",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
          "--json",
        ]),
      );
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.findingId).toBe("CVE-2026-9");
      expect(parsed.severity).toBe("low");
    });
  });

  test("appends to an existing store rather than overwriting it", async () => {
    await withTmpCwd("ai-eng-risk-append-", async (root) => {
      await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "F1",
          "--severity",
          "low",
          "--justification",
          "j1",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
        ]),
      );
      await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "F2",
          "--severity",
          "medium",
          "--justification",
          "j2",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
        ]),
      );
      const storePath = join(root, ".ai-engineering", "state", "decision-store.json");
      const store = JSON.parse(readFileSync(storePath, "utf8"));
      expect(store.decisions).toHaveLength(2);
      expect(store.decisions.map((d: { findingId: string }) => d.findingId).sort()).toEqual([
        "F1",
        "F2",
      ]);
    });
  });
});

describe("risk accept — error paths", () => {
  test("missing required flag returns exit 1", async () => {
    await withTmpCwd("ai-eng-risk-missing-", async () => {
      const result = await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "CVE-1",
          // missing severity
          "--justification",
          "x",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
        ]),
      );
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/severity|required/i);
    });
  });

  test("invalid severity returns exit 1", async () => {
    await withTmpCwd("ai-eng-risk-bad-sev-", async () => {
      const result = await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "CVE-1",
          "--severity",
          "extreme",
          "--justification",
          "x",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
        ]),
      );
      expect(result.exitCode).toBe(1);
    });
  });

  test("empty justification returns exit 1 (domain validation)", async () => {
    await withTmpCwd("ai-eng-risk-empty-", async () => {
      const result = await capture(() =>
        risk([
          "accept",
          "--finding-id",
          "CVE-1",
          "--severity",
          "high",
          "--justification",
          "",
          "--owner",
          "a@b",
          "--spec-ref",
          "spec-1",
        ]),
      );
      expect(result.exitCode).toBe(1);
    });
  });

  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-risk-unknown-", async () => {
      const result = await capture(() => risk(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown|accept/i);
    });
  });

  test("no subcommand prints help and returns 1", async () => {
    await withTmpCwd("ai-eng-risk-empty-args-", async () => {
      const result = await capture(() => risk([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
