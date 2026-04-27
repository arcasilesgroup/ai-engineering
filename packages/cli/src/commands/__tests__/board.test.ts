import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { board } from "../board.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

describe("board discover — fail-open", () => {
  test("returns 0 even when provider absent", async () => {
    await withTmpCwd("ai-eng-board-disc-", async () => {
      const result = await capture(() => board(["discover"]));
      expect(result.exitCode).toBe(0);
      // Either we detected gh or we report none — both are exit 0.
      expect(result.stdout).toMatch(/board discover/);
    });
  });

  test("--json emits provider field", async () => {
    await withTmpCwd("ai-eng-board-disc-json-", async () => {
      const result = await capture(() => board(["discover", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed).toHaveProperty("provider");
      expect(parsed).toHaveProperty("ghOnPath");
    });
  });
});

describe("board sync — happy path", () => {
  test("queues an event to board-events.ndjson", async () => {
    await withTmpCwd("ai-eng-board-sync-", async (root) => {
      const result = await capture(() => board(["sync", "impl", "spec-099"]));
      expect(result.exitCode).toBe(0);
      const path = join(root, ".ai-engineering", "state", "board-events.ndjson");
      expect(existsSync(path)).toBe(true);
      const lines = readFileSync(path, "utf8")
        .split("\n")
        .filter((l) => l.length > 0);
      expect(lines.length).toBe(1);
      const evt = JSON.parse(lines[0] ?? "");
      expect(evt.type).toBe("board.sync_intent");
      expect(evt.phase).toBe("impl");
      expect(evt.ref).toBe("spec-099");
    });
  });

  test("--json reports queued status", async () => {
    await withTmpCwd("ai-eng-board-sync-json-", async () => {
      const result = await capture(() => board(["sync", "spec", "spec-101", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.status).toBe("queued");
    });
  });
});

describe("board sync — error paths", () => {
  test("missing args returns exit 1", async () => {
    await withTmpCwd("ai-eng-board-sync-missing-", async () => {
      const result = await capture(() => board(["sync"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });

  test("invalid phase returns exit 1", async () => {
    await withTmpCwd("ai-eng-board-sync-bad-", async () => {
      const result = await capture(() => board(["sync", "fictional", "spec-1"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/invalid phase/i);
    });
  });
});

describe("board status / map — fail-open stubs", () => {
  test("status without manifest prints (not configured)", async () => {
    await withTmpCwd("ai-eng-board-status-", async () => {
      const result = await capture(() => board(["status"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/not configured/i);
    });
  });

  test("map without manifest prints (not configured)", async () => {
    await withTmpCwd("ai-eng-board-map-", async () => {
      const result = await capture(() => board(["map"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/not configured/i);
    });
  });
});

describe("board — error paths", () => {
  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-board-unknown-", async () => {
      const result = await capture(() => board(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage|unknown/i);
    });
  });

  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-board-noargs-", async () => {
      const result = await capture(() => board([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });
});
