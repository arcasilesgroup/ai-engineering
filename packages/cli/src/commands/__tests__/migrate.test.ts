import { describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { migrate } from "../migrate.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const seedV2Layout = (
  root: string,
  overrides: { decisions?: string; mirrors?: ReadonlyArray<string> } = {},
): void => {
  const v2 = join(root, ".ai-engineering");
  mkdirSync(join(v2, "specs"), { recursive: true });
  mkdirSync(join(v2, "state"), { recursive: true });
  writeFileSync(
    join(v2, "manifest.yml"),
    ["project: legacy-app", 'profile: "default"', "telemetry:", "  enabled: true", ""].join("\n"),
    "utf8",
  );
  writeFileSync(join(v2, "specs", "spec-001.md"), "# spec\n", "utf8");
  if (overrides.decisions !== undefined) {
    writeFileSync(join(v2, "state", "decision-store.json"), overrides.decisions, "utf8");
  }
  for (const mirror of overrides.mirrors ?? []) {
    const dir = join(root, mirror, "example");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "SKILL.md"), "mirror\n", "utf8");
  }
};

const validDecisions = JSON.stringify(
  {
    decisions: [
      {
        id: "DEC-1",
        findingId: "F-1",
        severity: "low",
        justification: "tracked",
        owner: "x@y.com",
        specRef: "spec-1",
        issuedAt: "2026-01-01T00:00:00.000Z",
        renewals: 0,
      },
    ],
  },
  null,
  2,
);

const mixedDecisions = JSON.stringify(
  {
    decisions: [
      {
        id: "DEC-OK",
        findingId: "F-OK",
        severity: "low",
        justification: "tracked",
        owner: "x@y.com",
        specRef: "spec-1",
        issuedAt: "2026-01-01T00:00:00.000Z",
        renewals: 0,
      },
      // garbage entry
      { id: "DEC-BAD", severity: "Critical" },
    ],
  },
  null,
  2,
);

describe("migrate v2-to-v3 — dry-run", () => {
  test("prints human-readable summary and returns 0", async () => {
    await withTmpCwd("ai-eng-migrate-dry-", async (root) => {
      seedV2Layout(root, { decisions: validDecisions });
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/migrate v2-to-v3/);
      expect(result.stdout).toMatch(/dry-run\s+yes/);
      expect(result.stdout).toMatch(/manifest converted\s+\(planned\)/);
      expect(result.stdout).toMatch(/Next steps:/);
      // No file mutation occurred.
      expect(existsSync(join(root, ".ai-engineering.v2.bak"))).toBe(false);
      expect(existsSync(join(root, ".ai-engineering", "manifest.toml"))).toBe(false);
    });
  });

  test("--json emits a structured report with plan", async () => {
    await withTmpCwd("ai-eng-migrate-json-", async (root) => {
      seedV2Layout(root);
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout) as {
        ok: boolean;
        report: {
          dryRun: boolean;
          manifestConverted: boolean;
          skillsMappedReport: unknown[];
        };
        telemetry: string[];
      };
      expect(parsed.ok).toBe(true);
      expect(parsed.report.dryRun).toBe(true);
      expect(parsed.report.manifestConverted).toBe(false);
      expect(parsed.telemetry).toContain("migration.started");
      expect(parsed.telemetry).toContain("migration.completed");
    });
  });
});

describe("migrate v2-to-v3 — execution", () => {
  test("--yes performs the migration and writes the v3 manifest + backup", async () => {
    await withTmpCwd("ai-eng-migrate-run-", async (root) => {
      seedV2Layout(root, {
        decisions: validDecisions,
        mirrors: [".claude/skills"],
      });
      const result = await capture(() => migrate(["v2-to-v3", "--yes", "--json"]));
      expect(result.exitCode).toBe(0);
      const parsed = JSON.parse(result.stdout) as {
        ok: boolean;
        report: { manifestConverted: boolean; backupPath: string };
      };
      expect(parsed.ok).toBe(true);
      expect(parsed.report.manifestConverted).toBe(true);
      // Files actually mutated.
      expect(existsSync(join(root, ".ai-engineering", "manifest.toml"))).toBe(true);
      expect(existsSync(join(root, ".ai-engineering.v2.bak", "manifest.yml"))).toBe(true);
      // Mirrors removed.
      expect(existsSync(join(root, ".claude", "skills"))).toBe(false);
    });
  });

  test("quarantines invalid decisions and writes the invalid file on --yes", async () => {
    await withTmpCwd("ai-eng-migrate-quarantine-", async (root) => {
      seedV2Layout(root, { decisions: mixedDecisions });
      const result = await capture(() => migrate(["v2-to-v3", "--yes"]));
      expect(result.exitCode).toBe(0);
      const invalidPath = join(root, ".ai-engineering", "state", "decision-store.invalid.json");
      expect(existsSync(invalidPath)).toBe(true);
      const parsed = JSON.parse(readFileSync(invalidPath, "utf8")) as {
        decisions: Array<{ reason: string }>;
      };
      expect(parsed.decisions.length).toBeGreaterThan(0);
    });
  });

  test("without --yes or --dry-run rejects with exit 1", async () => {
    await withTmpCwd("ai-eng-migrate-noconfirm-", async (root) => {
      seedV2Layout(root);
      const result = await capture(() => migrate(["v2-to-v3"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/--yes|dry-run/i);
      // No mutations.
      expect(existsSync(join(root, ".ai-engineering.v2.bak"))).toBe(false);
    });
  });
});

describe("migrate v2-to-v3 — error paths", () => {
  test("returns exit code 2 when no v2 layout exists", async () => {
    await withTmpCwd("ai-eng-migrate-empty-", async () => {
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run"]));
      expect(result.exitCode).toBe(2);
    });
  });

  test("--json on missing layout still emits structured payload", async () => {
    await withTmpCwd("ai-eng-migrate-empty-json-", async () => {
      const result = await capture(() => migrate(["v2-to-v3", "--dry-run", "--json"]));
      expect(result.exitCode).toBe(2);
      const parsed = JSON.parse(result.stdout) as {
        ok: boolean;
        reason: string;
      };
      expect(parsed.ok).toBe(false);
      expect(parsed.reason).toBe("not-v2");
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

describe("migrate rollback", () => {
  test("restores .ai-engineering/ from backup", async () => {
    await withTmpCwd("ai-eng-migrate-rollback-", async (root) => {
      seedV2Layout(root);
      // Run the migration to produce a backup.
      const r1 = await capture(() => migrate(["v2-to-v3", "--yes"]));
      expect(r1.exitCode).toBe(0);
      expect(existsSync(join(root, ".ai-engineering.v2.bak", "manifest.yml"))).toBe(true);
      // Damage the live tree.
      writeFileSync(join(root, ".ai-engineering", "manifest.yml"), "garbage", "utf8");
      // Roll back.
      const r2 = await capture(() => migrate(["rollback", "--yes"]));
      expect(r2.exitCode).toBe(0);
      const restored = readFileSync(join(root, ".ai-engineering", "manifest.yml"), "utf8");
      expect(restored).toMatch(/legacy-app/);
    });
  });

  test("returns exit 2 when no backup exists", async () => {
    await withTmpCwd("ai-eng-migrate-rollback-empty-", async () => {
      const result = await capture(() => migrate(["rollback", "--yes"]));
      expect(result.exitCode).toBe(2);
      expect(result.stderr).toMatch(/no.*backup|rollback/i);
    });
  });

  test("requires --yes confirmation", async () => {
    await withTmpCwd("ai-eng-migrate-rollback-confirm-", async (root) => {
      seedV2Layout(root);
      // Manually create a backup directory so we exercise the confirmation
      // gate before the use case is invoked.
      mkdirSync(join(root, ".ai-engineering.v2.bak"), { recursive: true });
      const result = await capture(() => migrate(["rollback"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/--yes/);
    });
  });
});
