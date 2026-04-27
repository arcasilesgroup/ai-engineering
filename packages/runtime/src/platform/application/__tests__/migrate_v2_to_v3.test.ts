import { describe, expect, test } from "bun:test";

import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { CapturingTelemetry, InMemoryMigrationFs } from "../_fakes.ts";
import {
  type MigrationDeps,
  __TEST_ONLY__,
  migrateV2ToV3,
  rollbackV2ToV3,
} from "../migrate_v2_to_v3.ts";

const ROOT = "/proj";

const seedV2 = (
  fs: InMemoryMigrationFs,
  overrides: {
    manifest?: string;
    decisions?: string;
    skills?: ReadonlyArray<string>;
    mirrors?: ReadonlyArray<string>;
  } = {},
): void => {
  const manifestYaml =
    overrides.manifest ??
    [
      "project: legacy-bank",
      'profile: "banking"',
      "board:",
      "  provider: github",
      "telemetry:",
      "  enabled: true",
      '  ndjson: ".ai-engineering/state/framework-events.ndjson"',
      "llm:",
      '  mode: "piggyback"',
      '  privacy_tier: "standard"',
      "",
    ].join("\n");
  fs.seed(`${ROOT}/.ai-engineering/manifest.yml`, manifestYaml);
  fs.seed(`${ROOT}/.ai-engineering/specs/spec-001-pilot.md`, "# spec-001\nbody\n");
  fs.seed(`${ROOT}/.ai-engineering/LESSONS.md`, "# lessons\n");

  if (overrides.decisions !== undefined) {
    fs.seed(`${ROOT}/.ai-engineering/state/decision-store.json`, overrides.decisions);
  }
  for (const s of overrides.skills ?? []) {
    fs.seed(`${ROOT}/.ai-engineering/skills/${s}/SKILL.md`, "skill\n");
  }
  for (const mirror of overrides.mirrors ?? []) {
    fs.seed(`${ROOT}/${mirror}/example/SKILL.md`, "mirror\n");
  }
};

const makeDeps = (): {
  fs: InMemoryMigrationFs;
  telemetry: CapturingTelemetry;
  deps: MigrationDeps;
} => {
  const fs = new InMemoryMigrationFs();
  const telemetry = new CapturingTelemetry();
  const deps: MigrationDeps = { fs, telemetry };
  return { fs, telemetry, deps };
};

const validDecisionsDoc = (): string =>
  JSON.stringify(
    {
      decisions: [
        {
          id: "DEC-1",
          findingId: "CVE-2026-0001",
          severity: "high",
          justification: "tracked in spec-099",
          owner: "alice@example.com",
          specRef: "spec-099",
          issuedAt: "2026-01-01T00:00:00.000Z",
          expiresAt: "2026-01-31T00:00:00.000Z",
          renewals: 0,
        },
        {
          id: "DEC-2",
          findingId: "CVE-2026-0002",
          severity: "medium",
          justification: "false positive",
          owner: "bob@example.com",
          specRef: "spec-100",
          issuedAt: "2026-02-01T00:00:00.000Z",
          renewals: 1,
        },
      ],
    },
    null,
    2,
  );

const mixedDecisionsDoc = (): string =>
  JSON.stringify(
    {
      decisions: [
        {
          id: "DEC-OK",
          findingId: "CVE-2026-0010",
          severity: "low",
          justification: "audit trail tracked",
          owner: "carol@example.com",
          specRef: "spec-200",
          issuedAt: "2026-03-01T00:00:00.000Z",
          renewals: 0,
        },
        {
          // bad severity (v2 used title-case in some legacy stores)
          id: "DEC-BAD-SEV",
          findingId: "CVE-2026-0011",
          severity: "Critical",
          justification: "x",
          owner: "dave@example.com",
          specRef: "spec-201",
          issuedAt: "2026-03-02T00:00:00.000Z",
        },
        {
          // exceeds max renewals
          id: "DEC-RENEW",
          findingId: "CVE-2026-0012",
          severity: "high",
          justification: "x",
          owner: "erin@example.com",
          specRef: "spec-202",
          issuedAt: "2026-03-03T00:00:00.000Z",
          renewals: 5,
        },
        // total garbage
        { id: "DEC-GARBAGE" },
      ],
    },
    null,
    2,
  );

describe("migrateV2ToV3 — happy path", () => {
  test("backs up, converts manifest, maps skills, validates decisions", async () => {
    const { fs, telemetry, deps } = makeDeps();
    seedV2(fs, {
      decisions: validDecisionsDoc(),
      skills: ["ai-brainstorm", "ai-dispatch", "ai-canvas", "ai-sprint", "ai-debug"],
      mirrors: [".claude/skills", ".codex/skills"],
    });

    const r = await migrateV2ToV3(
      {
        projectRoot: ROOT,
        dryRun: false,
        v2Skills: ["ai-brainstorm", "ai-dispatch", "ai-canvas", "ai-sprint", "ai-debug"],
      },
      deps,
    );
    expect(isOk(r)).toBe(true);
    if (!isOk(r)) return;

    expect(r.value.dryRun).toBe(false);
    expect(r.value.manifestConverted).toBe(true);
    expect(r.value.decisionsValid).toBe(2);
    expect(r.value.decisionsQuarantined).toBe(0);
    expect(r.value.mirrorsRemoved).toContain(".claude/skills");
    expect(r.value.mirrorsRemoved).toContain(".codex/skills");
    expect(r.value.backupPath).toBe("/proj/.ai-engineering.v2.bak");

    // Backup written.
    expect(await fs.exists("/proj/.ai-engineering.v2.bak/manifest.yml")).toBe(true);

    // TOML written.
    const toml = await fs.readText("/proj/.ai-engineering/manifest.toml");
    expect(isOk(toml)).toBe(true);
    if (isOk(toml)) {
      expect(toml.value).toMatch(/schema_version = "1"/);
      expect(toml.value).toMatch(/name = "legacy-bank"/);
      expect(toml.value).toMatch(/profile = "banking"/);
      expect(toml.value).toMatch(/provider = "github"/);
    }

    // Mirrors gone.
    expect(await fs.exists("/proj/.claude/skills")).toBe(false);
    expect(await fs.exists("/proj/.codex/skills")).toBe(false);

    // Skill mapping covers each input.
    const map = r.value.skillsMappedReport;
    expect(map.find((m) => m.v2 === "ai-brainstorm")?.v3).toBe("specify");
    expect(map.find((m) => m.v2 === "ai-dispatch")?.v3).toBe("implement");
    expect(map.find((m) => m.v2 === "ai-canvas")?.v3).toBeNull();
    expect(map.find((m) => m.v2 === "ai-canvas")?.kind).toBe("eliminated");
    expect(map.find((m) => m.v2 === "ai-sprint")?.v3).toBe("pm-pack");
    expect(map.find((m) => m.v2 === "ai-sprint")?.kind).toBe("plugin");
    expect(map.find((m) => m.v2 === "ai-debug")?.v3).toBe("debug");

    // Telemetry trail.
    const types = telemetry.typesEmitted();
    expect(types).toContain("migration.started");
    expect(types).toContain("migration.detected");
    expect(types).toContain("migration.backup_written");
    expect(types).toContain("migration.manifest_converted");
    expect(types).toContain("migration.skills_mapped");
    expect(types).toContain("migration.mirrors_removed");
    expect(types).toContain("migration.decisions_validated");
    expect(types).toContain("migration.completed");

    // Next-steps reminder includes doctor + sync-mirrors.
    const steps = r.value.nextSteps.join("\n");
    expect(steps).toMatch(/doctor --fix/);
    expect(steps).toMatch(/sync-mirrors/);
    expect(steps).toMatch(/migrate rollback/);
  });
});

describe("migrateV2ToV3 — dry-run", () => {
  test("writes nothing and reports planned actions only", async () => {
    const { fs, telemetry, deps } = makeDeps();
    seedV2(fs, {
      decisions: validDecisionsDoc(),
      skills: ["ai-brainstorm"],
      mirrors: [".claude/skills"],
    });

    const r = await migrateV2ToV3(
      { projectRoot: ROOT, dryRun: true, v2Skills: ["ai-brainstorm"] },
      deps,
    );
    expect(isOk(r)).toBe(true);
    if (!isOk(r)) return;

    expect(r.value.dryRun).toBe(true);
    expect(r.value.manifestConverted).toBe(false);
    // The manifest TOML must NOT have been written.
    expect(await fs.exists("/proj/.ai-engineering/manifest.toml")).toBe(false);
    // Backup must NOT have been created.
    expect(await fs.exists("/proj/.ai-engineering.v2.bak")).toBe(false);
    // Mirrors are still present (planned to remove, but dry-run).
    expect(await fs.exists("/proj/.claude/skills")).toBe(true);
    // Plan still reports them as scheduled removals.
    expect(r.value.mirrorsRemoved).toContain(".claude/skills");

    // Telemetry includes the planned-only signals.
    const types = telemetry.typesEmitted();
    expect(types).toContain("migration.backup_skipped");
    expect(types).toContain("migration.manifest_planned");
  });
});

describe("migrateV2ToV3 — error paths", () => {
  test("returns not-v2 when no v2 layout exists", async () => {
    const { deps, telemetry } = makeDeps();
    const r = await migrateV2ToV3({ projectRoot: ROOT, dryRun: false }, deps);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error.reason).toBe("not-v2");
    expect(telemetry.typesEmitted()).toContain("migration.not_v2");
  });

  test("returns manifest-parse-failed when manifest.yml is unparseable", async () => {
    const { fs, deps } = makeDeps();
    fs.seed(`${ROOT}/.ai-engineering/manifest.yml`, "key: value\n  bad-indent: : :");
    const r = await migrateV2ToV3({ projectRoot: ROOT, dryRun: false }, deps);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error.reason).toBe("manifest-parse-failed");
  });
});

describe("migrateV2ToV3 — decision quarantine", () => {
  test("invalid decisions are quarantined and stripped from the migrated store", async () => {
    const { fs, deps } = makeDeps();
    seedV2(fs, { decisions: mixedDecisionsDoc() });
    const r = await migrateV2ToV3({ projectRoot: ROOT, dryRun: false, v2Skills: [] }, deps);
    expect(isOk(r)).toBe(true);
    if (!isOk(r)) return;
    expect(r.value.decisionsValid).toBe(1);
    expect(r.value.decisionsQuarantined).toBe(3);

    // Migrated store retains only the valid one.
    const migrated = await fs.readText(`${ROOT}/.ai-engineering/state/decision-store.json`);
    expect(isOk(migrated)).toBe(true);
    if (isOk(migrated)) {
      const parsed = JSON.parse(migrated.value);
      expect(parsed.decisions).toHaveLength(1);
      expect(parsed.decisions[0].id).toBe("DEC-OK");
    }

    // Quarantine file lists the bad ones.
    const quarantined = await fs.readText(
      `${ROOT}/.ai-engineering/state/decision-store.invalid.json`,
    );
    expect(isOk(quarantined)).toBe(true);
    if (isOk(quarantined)) {
      const parsed = JSON.parse(quarantined.value);
      expect(parsed.decisions).toHaveLength(3);
      const reasons = parsed.decisions.map((e: { reason: string }) => e.reason);
      expect(reasons.some((r: string) => r.includes("severity"))).toBe(true);
    }

    // Warnings include the quarantine notice.
    expect(r.value.warnings.some((w) => w.includes("quarantined"))).toBe(true);
  });

  test("dry-run does not write the quarantine file but still counts entries", async () => {
    const { fs, deps } = makeDeps();
    seedV2(fs, { decisions: mixedDecisionsDoc() });
    const r = await migrateV2ToV3({ projectRoot: ROOT, dryRun: true, v2Skills: [] }, deps);
    expect(isOk(r)).toBe(true);
    if (!isOk(r)) return;
    expect(r.value.decisionsQuarantined).toBe(3);
    expect(await fs.exists(`${ROOT}/.ai-engineering/state/decision-store.invalid.json`)).toBe(
      false,
    );
  });
});

describe("rollbackV2ToV3", () => {
  test("restores .ai-engineering/ from the backup", async () => {
    const { fs, deps } = makeDeps();
    seedV2(fs, { decisions: validDecisionsDoc() });
    const migrate = await migrateV2ToV3({ projectRoot: ROOT, dryRun: false, v2Skills: [] }, deps);
    expect(isOk(migrate)).toBe(true);

    // Simulate user damage: delete the .ai-engineering tree.
    await fs.removeTree(`${ROOT}/.ai-engineering`);
    expect(await fs.exists(`${ROOT}/.ai-engineering`)).toBe(false);

    const r = await rollbackV2ToV3({ projectRoot: ROOT }, deps);
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      expect(r.value.restoredFrom).toBe(`${ROOT}/.ai-engineering.v2.bak`);
    }
    expect(await fs.exists(`${ROOT}/.ai-engineering/manifest.yml`)).toBe(true);
  });

  test("returns rollback-no-backup when no backup directory exists", async () => {
    const { deps } = makeDeps();
    const r = await rollbackV2ToV3({ projectRoot: ROOT }, deps);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error.reason).toBe("rollback-no-backup");
  });
});

describe("migrateV2ToV3 — pure helpers", () => {
  test("buildSkillMap covers renamed/absorbed/plugin/eliminated cases", () => {
    const map = __TEST_ONLY__.buildSkillMap([
      "ai-brainstorm",
      "ai-instinct",
      "ai-write",
      "ai-canvas",
      "ai-test",
      "totally-unknown",
    ]);
    expect(map).toHaveLength(6);
    const byName = (n: string) => map.find((m) => m.v2 === n);
    expect(byName("ai-brainstorm")?.kind).toBe("renamed");
    expect(byName("ai-instinct")?.kind).toBe("absorbed");
    expect(byName("ai-write")?.kind).toBe("plugin");
    expect(byName("ai-write")?.v3).toBe("content-pack");
    expect(byName("ai-canvas")?.kind).toBe("eliminated");
    expect(byName("ai-canvas")?.v3).toBeNull();
    expect(byName("ai-test")?.v3).toBe("test");
    expect(byName("totally-unknown")?.kind).toBe("eliminated");
  });

  test("renderManifestToml renders all known fields with sensible defaults", () => {
    const out = __TEST_ONLY__.renderManifestToml(
      {
        project: { name: "demo" },
        profile: "fintech",
        telemetry: { enabled: false },
      },
      "fallback",
    );
    expect(out).toMatch(/name = "demo"/);
    expect(out).toMatch(/profile = "fintech"/);
    expect(out).toMatch(/enabled = false/);
    expect(out).toMatch(/mode = "piggyback"/);
    expect(out).toMatch(/privacy_tier = "standard"/);
  });

  test("splitDecisions partitions valid vs invalid raw entries", () => {
    const r = __TEST_ONLY__.splitDecisions([
      {
        id: "DEC-1",
        findingId: "F-1",
        severity: "low",
        justification: "ok",
        owner: "x@y",
        specRef: "spec-1",
        issuedAt: "2026-01-01T00:00:00Z",
      },
      { id: "DEC-2", severity: "high" },
      "not-an-object",
    ]);
    expect(r.valid).toHaveLength(1);
    expect(r.invalid).toHaveLength(2);
  });
});
