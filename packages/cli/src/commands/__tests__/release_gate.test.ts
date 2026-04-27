import { describe, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { releaseGate } from "../release_gate.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const writeOutcomes = (root: string, outcomes: ReadonlyArray<Record<string, unknown>>): void => {
  const dir = join(root, ".ai-engineering", "state");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "gate-outcomes.json"), JSON.stringify({ outcomes }, null, 2), "utf8");
};

describe("release-gate — happy path", () => {
  test("all-pass outcomes → GO and exit 0", async () => {
    await withTmpCwd("ai-eng-rg-go-", async (root) => {
      writeOutcomes(root, [
        {
          gateId: "ruff",
          verdict: "pass",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 10,
          findings: [],
        },
        {
          gateId: "pytest",
          verdict: "pass",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 200,
          findings: [],
        },
      ]);
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/GO/);
    });
  });

  test("--json emits structured aggregate", async () => {
    await withTmpCwd("ai-eng-rg-json-", async (root) => {
      writeOutcomes(root, [
        {
          gateId: "ruff",
          verdict: "pass",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 10,
          findings: [],
        },
      ]);
      const result = await capture(() => releaseGate(["--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout);
      expect(parsed.verdict).toBe("GO");
      expect(parsed.totals.pass).toBe(1);
    });
  });

  test("warn outcome → CONDITIONAL and exit 1", async () => {
    await withTmpCwd("ai-eng-rg-cond-", async (root) => {
      writeOutcomes(root, [
        {
          gateId: "ruff",
          verdict: "pass",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 10,
          findings: [],
        },
        {
          gateId: "semgrep",
          verdict: "warn",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 100,
          findings: [
            {
              findingId: "S-1",
              severity: "low",
              message: "warn finding",
            },
          ],
        },
      ]);
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(1);
      expect(result.stdout).toMatch(/CONDITIONAL/);
    });
  });

  test("fail with critical finding → NO-GO and exit 2", async () => {
    await withTmpCwd("ai-eng-rg-nogo-", async (root) => {
      writeOutcomes(root, [
        {
          gateId: "pytest",
          verdict: "fail",
          executedAt: "2026-04-27T00:00:00Z",
          durationMs: 100,
          findings: [
            {
              findingId: "BAD-1",
              severity: "critical",
              message: "critical fail",
            },
          ],
        },
      ]);
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(2);
      expect(result.stdout).toMatch(/NO-GO/);
    });
  });
});

describe("release-gate — error paths", () => {
  test("missing outcomes file returns exit 1 with friendly message", async () => {
    await withTmpCwd("ai-eng-rg-missing-", async () => {
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/no gate outcomes/i);
    });
  });

  test("malformed JSON in outcomes file returns exit 1", async () => {
    await withTmpCwd("ai-eng-rg-bad-json-", async (root) => {
      const dir = join(root, ".ai-engineering", "state");
      mkdirSync(dir, { recursive: true });
      writeFileSync(join(dir, "gate-outcomes.json"), "{not json", "utf8");
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/parse|invalid/i);
    });
  });

  test("empty outcomes array returns exit 1 (use case rejects)", async () => {
    await withTmpCwd("ai-eng-rg-empty-", async (root) => {
      writeOutcomes(root, []);
      const result = await capture(() => releaseGate([]));
      expect(result.exitCode).toBe(1);
    });
  });
});
