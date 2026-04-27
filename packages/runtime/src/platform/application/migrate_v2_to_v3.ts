import * as yaml from "js-yaml";

import {
  type Decision,
  type Severity,
  createDecision,
} from "../../governance/domain/decision.ts";
import { DecisionId } from "../../shared/kernel/branded.ts";
import type { IOError } from "../../shared/kernel/errors.ts";
import { type Result, err, isErr, ok } from "../../shared/kernel/result.ts";
import type { TelemetryPort } from "../../shared/ports/telemetry.ts";

/**
 * MigrateV2ToV3 — convert a legacy v2 ai-engineering project layout to v3.
 *
 * v3 plan §11 Phase 8 + master-plan row 8: a deterministic, idempotent
 * migrator with mandatory backup and rollback. The use case is pure
 * orchestration — every filesystem operation goes through `MigrationFsPort`
 * so the same pipeline runs against `node:fs/promises` in production and an
 * in-memory fake under test.
 *
 * Steps (each emits telemetry):
 *   1. Detect v2 layout (`.ai-engineering/manifest.yml` MUST exist).
 *   2. Backup `.ai-engineering/` → `.ai-engineering.v2.bak/` (skipped on dry-run).
 *   3. Convert `manifest.yml` → `manifest.toml` mapping known fields.
 *   4. Build a v2→v3 skill mapping report (deprecated, plugin-relocated, 1:1).
 *   5. Delete IDE skill mirrors (`.claude/skills`, `.codex/skills`,
 *      `.gemini/skills`); they regenerate via `ai-eng sync-mirrors`.
 *   6. Re-validate every entry in `decision-store.json` against the v3
 *      Decision schema; quarantine invalid entries to
 *      `decision-store.invalid.json`.
 *   7. Surface a "run `ai-eng doctor --fix`" warning for hooks.
 *   8. Return MigrationReport summarising work done (or planned, in dry-run).
 *
 * The use case never throws. All errors flow through Result so callers can
 * map them to exit codes deterministically.
 */

// -----------------------------------------------------------------------------
// Ports
// -----------------------------------------------------------------------------

/**
 * MigrationFsPort — minimal filesystem surface needed by the migrator.
 *
 * `FilesystemPort` is file-scoped (read/write/exists/list/remove). Migration
 * needs tree ops (recursive copy, recursive remove, mkdir-p), so we expose a
 * dedicated port. Real adapter wraps node:fs/promises; tests use the
 * in-memory fake in `_fakes.ts`.
 */
export interface MigrationFsPort {
  exists(path: string): Promise<boolean>;
  readText(path: string): Promise<Result<string, IOError>>;
  writeText(path: string, content: string): Promise<Result<void, IOError>>;
  mkdirp(path: string): Promise<Result<void, IOError>>;
  copyTree(from: string, to: string): Promise<Result<void, IOError>>;
  removeTree(path: string): Promise<Result<void, IOError>>;
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------

export type MigrationErrorReason =
  | "not-v2"
  | "backup-failed"
  | "manifest-parse-failed"
  | "manifest-write-failed"
  | "decisions-read-failed"
  | "mirrors-cleanup-failed"
  | "rollback-failed"
  | "rollback-no-backup";

export class MigrationError extends Error {
  constructor(
    message: string,
    public readonly reason: MigrationErrorReason,
  ) {
    super(message);
    this.name = "MigrationError";
  }
}

// -----------------------------------------------------------------------------
// Skill mapping (v2 → v3)
// -----------------------------------------------------------------------------

export type SkillMapKind =
  | "renamed"
  | "absorbed"
  | "merged"
  | "plugin"
  | "eliminated";

export interface SkillMapEntry {
  readonly v2: string;
  readonly v3: string | null; // null when eliminated
  readonly kind: SkillMapKind;
  readonly warning?: string;
}

const PLUGIN_RELOCATIONS: ReadonlyArray<readonly [string, string]> =
  Object.freeze([
    ["ai-animation", "creative-pack"],
    ["ai-sprint", "pm-pack"],
    ["ai-standup", "pm-pack"],
    ["ai-write", "content-pack"],
    ["ai-market", "content-pack"],
    ["ai-skill-evolve", "meta-pack"],
    ["ai-prompt", "meta-pack"],
    ["ai-create", "meta-pack"],
  ]);

const ELIMINATED_V2: ReadonlyArray<string> = Object.freeze([
  "ai-canvas",
  "ai-slides",
  "ai-video-editing",
]);

const RENAMED_V2: ReadonlyArray<readonly [string, string]> = Object.freeze([
  ["ai-brainstorm", "specify"],
  ["ai-dispatch", "implement"],
  ["ai-board-discover", "board"],
  ["ai-board-sync", "board"],
  ["ai-resolve-conflicts", "resolve"],
  ["ai-schema", "data"],
]);

const ABSORBED_V2: ReadonlyArray<readonly [string, string]> = Object.freeze([
  ["ai-code", "implement"],
  ["ai-instinct", "learn"],
]);

/**
 * v3 catalog skill names. Used to confirm that v2 skills which look like 1:1
 * matches (with `ai-` prefix dropped) actually exist in v3.
 */
const V3_CATALOG: ReadonlySet<string> = new Set([
  "board",
  "bootstrap",
  "commit",
  "constitution",
  "data",
  "debug",
  "docs",
  "eval",
  "explain",
  "governance",
  "guide",
  "hotfix",
  "implement",
  "learn",
  "migrate",
  "note",
  "plan",
  "postmortem",
  "pr",
  "release-gate",
  "resolve",
  "review",
  "risk-accept",
  "security",
  "simplify",
  "specify",
  "start",
  "test",
  "verify",
]);

interface SkillMapTables {
  readonly renamed: ReadonlyMap<string, string>;
  readonly absorbed: ReadonlyMap<string, string>;
  readonly plugin: ReadonlyMap<string, string>;
  readonly eliminated: ReadonlySet<string>;
}

const SKILL_MAP_TABLES: SkillMapTables = Object.freeze({
  renamed: new Map(RENAMED_V2),
  absorbed: new Map(ABSORBED_V2),
  plugin: new Map(PLUGIN_RELOCATIONS),
  eliminated: new Set(ELIMINATED_V2),
});

const classifyByTable = (
  name: string,
  tables: SkillMapTables,
): SkillMapEntry | null => {
  if (tables.eliminated.has(name)) {
    return {
      v2: name,
      v3: null,
      kind: "eliminated",
      warning: `${name} is eliminated in v3 (no replacement)`,
    };
  }
  const renamedTarget = tables.renamed.get(name);
  if (renamedTarget !== undefined) {
    const isMerged = name === "ai-board-discover" || name === "ai-board-sync";
    return {
      v2: name,
      v3: renamedTarget,
      kind: isMerged ? "merged" : "renamed",
    };
  }
  const absorbedTarget = tables.absorbed.get(name);
  if (absorbedTarget !== undefined) {
    return {
      v2: name,
      v3: absorbedTarget,
      kind: "absorbed",
      warning: `${name} absorbed into ${absorbedTarget}`,
    };
  }
  const pluginTarget = tables.plugin.get(name);
  if (pluginTarget !== undefined) {
    return {
      v2: name,
      v3: pluginTarget,
      kind: "plugin",
      warning: `${name} relocated to plugin ${pluginTarget}`,
    };
  }
  return null;
};

const classifyByCatalog = (name: string): SkillMapEntry => {
  const stripped = name.startsWith("ai-") ? name.slice(3) : name;
  if (V3_CATALOG.has(stripped)) {
    return { v2: name, v3: stripped, kind: "renamed" };
  }
  return {
    v2: name,
    v3: null,
    kind: "eliminated",
    warning: `${name} has no v3 mapping (no entry in v3 catalog)`,
  };
};

const buildSkillMap = (
  v2Skills: ReadonlyArray<string>,
): ReadonlyArray<SkillMapEntry> => {
  const out: SkillMapEntry[] = [];
  for (const raw of v2Skills) {
    const name = raw.trim();
    if (name.length === 0) continue;
    const classified =
      classifyByTable(name, SKILL_MAP_TABLES) ?? classifyByCatalog(name);
    out.push(classified);
  }
  return Object.freeze(out);
};

// -----------------------------------------------------------------------------
// Manifest conversion
// -----------------------------------------------------------------------------

interface V2Manifest {
  readonly project?: string | { name?: string };
  readonly profile?: string;
  readonly board?: { provider?: string };
  readonly telemetry?: { enabled?: boolean; ndjson?: string };
  readonly llm?: { mode?: string; privacy_tier?: string };
}

const renderTomlString = (s: string): string => `"${s.replace(/"/g, '\\"')}"`;

const renderTomlBool = (b: boolean): string => (b ? "true" : "false");

const renderManifestToml = (
  input: V2Manifest,
  fallbackName: string,
): string => {
  const projectName =
    typeof input.project === "string"
      ? input.project
      : (input.project?.name ?? fallbackName);
  const profile = input.profile ?? "default";
  const llmMode = input.llm?.mode ?? "piggyback";
  const privacyTier = input.llm?.privacy_tier ?? "standard";
  const telemetryEnabled = input.telemetry?.enabled ?? true;
  const ndjson =
    input.telemetry?.ndjson ?? ".ai-engineering/state/framework-events.ndjson";
  const boardProvider = input.board?.provider;

  const lines: string[] = [
    "# Project-level ai-engineering manifest (migrated from v2 manifest.yml).",
    "# Regenerate via `ai-eng bootstrap` if you need a fresh template.",
    "",
    'schema_version = "1"',
    "",
    "[project]",
    `name = ${renderTomlString(projectName)}`,
    `profile = ${renderTomlString(profile)}`,
    "",
    "[ides]",
    "# Run `ai-eng sync-mirrors` to materialize IDE mirrors from skills/catalog/.",
    "detected = []",
    "",
    "[llm]",
    `mode = ${renderTomlString(llmMode)}`,
    `privacy_tier = ${renderTomlString(privacyTier)}`,
    "",
    "[telemetry]",
    `enabled = ${renderTomlBool(telemetryEnabled)}`,
    `ndjson = ${renderTomlString(ndjson)}`,
  ];
  if (boardProvider !== undefined) {
    lines.push("", "[board]", `provider = ${renderTomlString(boardProvider)}`);
  }
  lines.push("");
  return lines.join("\n");
};

// -----------------------------------------------------------------------------
// Decision validation
// -----------------------------------------------------------------------------

interface RawDecision {
  readonly id?: unknown;
  readonly findingId?: unknown;
  readonly finding_id?: unknown;
  readonly severity?: unknown;
  readonly justification?: unknown;
  readonly owner?: unknown;
  readonly specRef?: unknown;
  readonly spec_ref?: unknown;
  readonly issuedAt?: unknown;
  readonly issued_at?: unknown;
  readonly renewals?: unknown;
}

const SEVERITIES: ReadonlySet<Severity> = new Set([
  "critical",
  "high",
  "medium",
  "low",
]);

const isString = (v: unknown): v is string =>
  typeof v === "string" && v.length > 0;

interface NormalizedDecisionRaw {
  readonly id: string;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAtDate: Date;
  readonly renewals: number;
}

const normalizeRaw = (
  raw: RawDecision,
): Result<NormalizedDecisionRaw, string> => {
  const id = raw.id;
  if (!isString(id)) return err("missing or invalid id");
  const findingId = raw.findingId ?? raw.finding_id;
  if (!isString(findingId)) return err("missing or invalid findingId");
  const sev = raw.severity;
  if (!isString(sev) || !SEVERITIES.has(sev as Severity)) {
    return err(
      `invalid severity (must be one of critical|high|medium|low, got ${String(sev)})`,
    );
  }
  const just = raw.justification;
  if (!isString(just)) return err("missing or invalid justification");
  const owner = raw.owner;
  if (!isString(owner)) return err("missing or invalid owner");
  const specRef = raw.specRef ?? raw.spec_ref;
  if (!isString(specRef)) return err("missing or invalid specRef");
  const issuedAt = raw.issuedAt ?? raw.issued_at;
  if (!isString(issuedAt)) {
    return err("missing or invalid issuedAt (ISO 8601 string required)");
  }
  const issuedAtDate = new Date(issuedAt);
  if (Number.isNaN(issuedAtDate.getTime())) {
    return err(`issuedAt is not a parseable date: ${issuedAt}`);
  }
  const renewals = typeof raw.renewals === "number" ? raw.renewals : 0;
  if (renewals < 0 || renewals > 2) {
    return err(`renewals out of range [0,2]: ${renewals}`);
  }
  return ok({
    id,
    findingId,
    severity: sev as Severity,
    justification: just,
    owner,
    specRef,
    issuedAtDate,
    renewals,
  });
};

const validateOneDecision = (raw: RawDecision): Result<Decision, string> => {
  const norm = normalizeRaw(raw);
  if (isErr(norm)) return norm;
  const created = createDecision({
    id: DecisionId(norm.value.id),
    findingId: norm.value.findingId,
    severity: norm.value.severity,
    justification: norm.value.justification,
    owner: norm.value.owner,
    specRef: norm.value.specRef,
    issuedAt: norm.value.issuedAtDate,
    renewals: norm.value.renewals,
  });
  if (isErr(created)) return err(created.error.message);
  return ok(created.value);
};

interface DecisionValidationOutcome {
  readonly valid: ReadonlyArray<Decision>;
  readonly invalid: ReadonlyArray<{
    readonly raw: unknown;
    readonly reason: string;
  }>;
}

const splitDecisions = (
  raw: ReadonlyArray<unknown>,
): DecisionValidationOutcome => {
  const valid: Decision[] = [];
  const invalid: Array<{ raw: unknown; reason: string }> = [];
  for (const r of raw) {
    if (r === null || typeof r !== "object") {
      invalid.push({ raw: r, reason: "decision entry is not an object" });
      continue;
    }
    const result = validateOneDecision(r as RawDecision);
    if (isErr(result)) {
      invalid.push({ raw: r, reason: result.error });
    } else {
      valid.push(result.value);
    }
  }
  return Object.freeze({
    valid: Object.freeze(valid),
    invalid: Object.freeze(invalid),
  });
};

// -----------------------------------------------------------------------------
// Use case
// -----------------------------------------------------------------------------

export interface MigrationInput {
  readonly projectRoot: string;
  readonly dryRun: boolean;
  /** Optional explicit list of v2 skills to consider; defaults to scanning. */
  readonly v2Skills?: ReadonlyArray<string>;
  readonly now?: Date;
}

export interface MigrationDeps {
  readonly fs: MigrationFsPort;
  readonly telemetry: TelemetryPort;
}

export interface MigrationReport {
  readonly projectRoot: string;
  readonly dryRun: boolean;
  readonly backupPath: string;
  readonly manifestConverted: boolean;
  readonly skillsMappedReport: ReadonlyArray<SkillMapEntry>;
  readonly decisionsValid: number;
  readonly decisionsQuarantined: number;
  readonly mirrorsRemoved: ReadonlyArray<string>;
  readonly warnings: ReadonlyArray<string>;
  readonly nextSteps: ReadonlyArray<string>;
}

const join = (a: string, b: string): string => {
  if (a.endsWith("/")) return `${a}${b}`;
  return `${a}/${b}`;
};

const V2_MANIFEST_REL = ".ai-engineering/manifest.yml";
const V3_MANIFEST_REL = ".ai-engineering/manifest.toml";
const BACKUP_REL = ".ai-engineering.v2.bak";
const V2_ROOT_REL = ".ai-engineering";
const SKILLS_DIR_REL = ".ai-engineering/skills";
const DECISION_STORE_REL = ".ai-engineering/state/decision-store.json";
const DECISION_QUARANTINE_REL =
  ".ai-engineering/state/decision-store.invalid.json";
const IDE_MIRROR_DIRS: ReadonlyArray<string> = Object.freeze([
  ".claude/skills",
  ".codex/skills",
  ".gemini/skills",
]);

interface DecisionPersistShape {
  readonly decisions: ReadonlyArray<Record<string, unknown>>;
}

const decisionToPersisted = (d: Decision): Record<string, unknown> => ({
  id: d.id,
  findingId: d.findingId,
  severity: d.severity,
  justification: d.justification,
  owner: d.owner,
  specRef: d.specRef,
  issuedAt: d.issuedAt.toISOString(),
  expiresAt: d.expiresAt.toISOString(),
  renewals: d.renewals,
});

const inferProjectName = (projectRoot: string): string => {
  const trimmed = projectRoot.replace(/[\\/]+$/, "");
  const idx = Math.max(trimmed.lastIndexOf("/"), trimmed.lastIndexOf("\\"));
  const tail = idx === -1 ? trimmed : trimmed.slice(idx + 1);
  return tail.length > 0 ? tail : "my-project";
};

const detectV2Skills = async (
  fs: MigrationFsPort,
  projectRoot: string,
): Promise<ReadonlyArray<string>> => {
  const dir = join(projectRoot, SKILLS_DIR_REL);
  if (!(await fs.exists(dir))) return Object.freeze([]);
  // The migrator does not list directories through the port (we want to keep
  // the port surface minimal). Callers that need to drive skill mapping from
  // disk listings supply `v2Skills` explicitly via the input.
  return Object.freeze([]);
};

// -----------------------------------------------------------------------------
// Stage helpers (extract complexity from the top-level orchestrator).
// -----------------------------------------------------------------------------

const stepDetect = async (
  root: string,
  fs: MigrationFsPort,
  telemetry: TelemetryPort,
): Promise<Result<void, MigrationError>> => {
  const v2ManifestPath = join(root, V2_MANIFEST_REL);
  if (!(await fs.exists(v2ManifestPath))) {
    await telemetry.emit({
      level: "warn",
      type: "migration.not_v2",
      attributes: { projectRoot: root },
    });
    return err(
      new MigrationError(
        `No v2 layout detected at ${root} (missing ${V2_MANIFEST_REL})`,
        "not-v2",
      ),
    );
  }
  await telemetry.emit({
    level: "info",
    type: "migration.detected",
    attributes: { projectRoot: root },
  });
  return ok(undefined);
};

const stepBackup = async (
  root: string,
  dryRun: boolean,
  backupPath: string,
  fs: MigrationFsPort,
  telemetry: TelemetryPort,
): Promise<Result<void, MigrationError>> => {
  if (dryRun) {
    await telemetry.emit({
      level: "info",
      type: "migration.backup_skipped",
      attributes: { reason: "dry-run", backupPath },
    });
    return ok(undefined);
  }
  if (await fs.exists(backupPath)) {
    const removed = await fs.removeTree(backupPath);
    if (isErr(removed)) {
      return err(
        new MigrationError(
          `Failed to clear existing backup at ${BACKUP_REL}: ${removed.error.message}`,
          "backup-failed",
        ),
      );
    }
  }
  const copied = await fs.copyTree(join(root, V2_ROOT_REL), backupPath);
  if (isErr(copied)) {
    return err(
      new MigrationError(
        `Backup copy failed: ${copied.error.message}`,
        "backup-failed",
      ),
    );
  }
  await telemetry.emit({
    level: "audit",
    type: "migration.backup_written",
    attributes: { backupPath },
  });
  return ok(undefined);
};

const parseV2Yaml = (raw: string): Result<V2Manifest, MigrationError> => {
  try {
    const loaded = yaml.load(raw);
    if (loaded === null || typeof loaded !== "object") {
      return ok({});
    }
    return ok(loaded as V2Manifest);
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : String(cause);
    return err(
      new MigrationError(
        `Failed to parse ${V2_MANIFEST_REL}: ${message}`,
        "manifest-parse-failed",
      ),
    );
  }
};

const stepConvertManifest = async (
  root: string,
  dryRun: boolean,
  fs: MigrationFsPort,
  telemetry: TelemetryPort,
): Promise<Result<boolean, MigrationError>> => {
  const v2ManifestPath = join(root, V2_MANIFEST_REL);
  const yamlRead = await fs.readText(v2ManifestPath);
  if (isErr(yamlRead)) {
    return err(
      new MigrationError(
        `Failed to read ${V2_MANIFEST_REL}: ${yamlRead.error.message}`,
        "manifest-parse-failed",
      ),
    );
  }
  const parsedRes = parseV2Yaml(yamlRead.value);
  if (isErr(parsedRes)) return parsedRes;
  const tomlBody = renderManifestToml(parsedRes.value, inferProjectName(root));
  if (dryRun) {
    await telemetry.emit({
      level: "info",
      type: "migration.manifest_planned",
      attributes: { from: V2_MANIFEST_REL, to: V3_MANIFEST_REL },
    });
    return ok(false);
  }
  const written = await fs.writeText(join(root, V3_MANIFEST_REL), tomlBody);
  if (isErr(written)) {
    return err(
      new MigrationError(
        `Failed to write ${V3_MANIFEST_REL}: ${written.error.message}`,
        "manifest-write-failed",
      ),
    );
  }
  await telemetry.emit({
    level: "audit",
    type: "migration.manifest_converted",
    attributes: { from: V2_MANIFEST_REL, to: V3_MANIFEST_REL },
  });
  return ok(true);
};

const stepMapSkills = async (
  v2Skills: ReadonlyArray<string>,
  telemetry: TelemetryPort,
): Promise<ReadonlyArray<SkillMapEntry>> => {
  const report = buildSkillMap(v2Skills);
  await telemetry.emit({
    level: "info",
    type: "migration.skills_mapped",
    attributes: {
      total: report.length,
      eliminated: report.filter((s) => s.kind === "eliminated").length,
      relocated: report.filter((s) => s.kind === "plugin").length,
    },
  });
  return report;
};

const stepRemoveMirrors = async (
  root: string,
  dryRun: boolean,
  fs: MigrationFsPort,
  telemetry: TelemetryPort,
): Promise<Result<ReadonlyArray<string>, MigrationError>> => {
  const removed: string[] = [];
  for (const rel of IDE_MIRROR_DIRS) {
    const abs = join(root, rel);
    if (!(await fs.exists(abs))) continue;
    if (!dryRun) {
      const r = await fs.removeTree(abs);
      if (isErr(r)) {
        return err(
          new MigrationError(
            `Failed to remove ${rel}: ${r.error.message}`,
            "mirrors-cleanup-failed",
          ),
        );
      }
    }
    removed.push(rel);
  }
  if (removed.length > 0) {
    await telemetry.emit({
      level: "audit",
      type: "migration.mirrors_removed",
      attributes: { removed, dryRun },
    });
  }
  return ok(Object.freeze(removed));
};

const parseDecisionsArray = (raw: string): ReadonlyArray<unknown> => {
  try {
    const obj = JSON.parse(raw);
    if (obj && typeof obj === "object" && Array.isArray(obj.decisions)) {
      return obj.decisions as ReadonlyArray<unknown>;
    }
  } catch {
    /* fall through */
  }
  return [];
};

interface DecisionsStepOutcome {
  readonly valid: number;
  readonly quarantined: number;
  readonly warnings: ReadonlyArray<string>;
}

const writeQuarantine = async (
  root: string,
  outcome: ReturnType<typeof splitDecisions>,
  fs: MigrationFsPort,
): Promise<Result<void, MigrationError>> => {
  const quarantineDoc: DecisionPersistShape = {
    decisions: outcome.invalid.map(
      (i): Record<string, unknown> => ({ entry: i.raw, reason: i.reason }),
    ),
  };
  const written = await fs.writeText(
    join(root, DECISION_QUARANTINE_REL),
    `${JSON.stringify(quarantineDoc, null, 2)}\n`,
  );
  if (isErr(written)) {
    return err(
      new MigrationError(
        `Failed to write quarantine file: ${written.error.message}`,
        "decisions-read-failed",
      ),
    );
  }
  return ok(undefined);
};

const writeMigratedDecisions = async (
  decisionsPath: string,
  outcome: ReturnType<typeof splitDecisions>,
  fs: MigrationFsPort,
): Promise<Result<void, MigrationError>> => {
  const migratedDoc: DecisionPersistShape = {
    decisions: outcome.valid.map(decisionToPersisted),
  };
  const wrote = await fs.writeText(
    decisionsPath,
    `${JSON.stringify(migratedDoc, null, 2)}\n`,
  );
  if (isErr(wrote)) {
    return err(
      new MigrationError(
        `Failed to rewrite migrated ${DECISION_STORE_REL}: ${wrote.error.message}`,
        "decisions-read-failed",
      ),
    );
  }
  return ok(undefined);
};

const stepValidateDecisions = async (
  root: string,
  dryRun: boolean,
  fs: MigrationFsPort,
  telemetry: TelemetryPort,
): Promise<Result<DecisionsStepOutcome, MigrationError>> => {
  const decisionsPath = join(root, DECISION_STORE_REL);
  if (!(await fs.exists(decisionsPath))) {
    return ok({ valid: 0, quarantined: 0, warnings: Object.freeze([]) });
  }
  const dRead = await fs.readText(decisionsPath);
  if (isErr(dRead)) {
    return err(
      new MigrationError(
        `Failed to read ${DECISION_STORE_REL}: ${dRead.error.message}`,
        "decisions-read-failed",
      ),
    );
  }
  const parsedDecisions = parseDecisionsArray(dRead.value);
  const outcome = splitDecisions(parsedDecisions);
  const warnings: string[] = [];
  if (!dryRun && outcome.invalid.length > 0) {
    const wq = await writeQuarantine(root, outcome, fs);
    if (isErr(wq)) return wq;
    const wm = await writeMigratedDecisions(decisionsPath, outcome, fs);
    if (isErr(wm)) return wm;
  }
  await telemetry.emit({
    level: "audit",
    type: "migration.decisions_validated",
    attributes: {
      valid: outcome.valid.length,
      quarantined: outcome.invalid.length,
      dryRun,
    },
  });
  if (outcome.invalid.length > 0) {
    warnings.push(
      `${outcome.invalid.length} invalid decision(s) quarantined to ${DECISION_QUARANTINE_REL}`,
    );
  }
  return ok({
    valid: outcome.valid.length,
    quarantined: outcome.invalid.length,
    warnings: Object.freeze(warnings),
  });
};

const NEXT_STEPS: ReadonlyArray<string> = Object.freeze([
  "Run `ai-eng doctor --fix` to refresh git hooks for v3.",
  "Run `ai-eng sync-mirrors` to regenerate IDE skill mirrors.",
  `Backup retained at ${BACKUP_REL} (90-day window). Run \`ai-eng migrate rollback\` to restore.`,
]);

export const migrateV2ToV3 = async (
  input: MigrationInput,
  deps: MigrationDeps,
): Promise<Result<MigrationReport, MigrationError>> => {
  const { fs, telemetry } = deps;
  const root = input.projectRoot;
  const dryRun = input.dryRun;
  const backupPath = join(root, BACKUP_REL);

  await telemetry.emit({
    level: "audit",
    type: "migration.started",
    attributes: { projectRoot: root, dryRun },
  });

  const detect = await stepDetect(root, fs, telemetry);
  if (isErr(detect)) return detect;

  const backup = await stepBackup(root, dryRun, backupPath, fs, telemetry);
  if (isErr(backup)) return backup;

  const manifest = await stepConvertManifest(root, dryRun, fs, telemetry);
  if (isErr(manifest)) return manifest;
  const manifestConverted = manifest.value;

  const v2Skills =
    input.v2Skills !== undefined && input.v2Skills.length > 0
      ? input.v2Skills
      : await detectV2Skills(fs, root);
  const skillsMappedReport = await stepMapSkills(v2Skills, telemetry);

  const mirrors = await stepRemoveMirrors(root, dryRun, fs, telemetry);
  if (isErr(mirrors)) return mirrors;
  const mirrorsRemoved = mirrors.value;

  const decisions = await stepValidateDecisions(root, dryRun, fs, telemetry);
  if (isErr(decisions)) return decisions;

  const warnings: string[] = [];
  for (const e of skillsMappedReport) {
    if (e.warning !== undefined) warnings.push(e.warning);
  }
  for (const w of decisions.value.warnings) warnings.push(w);

  await telemetry.emit({
    level: "audit",
    type: "migration.completed",
    attributes: {
      dryRun,
      backupPath,
      manifestConverted,
      skillsMappedCount: skillsMappedReport.length,
      decisionsValid: decisions.value.valid,
      decisionsQuarantined: decisions.value.quarantined,
      mirrorsRemovedCount: mirrorsRemoved.length,
    },
  });

  return ok(
    Object.freeze({
      projectRoot: root,
      dryRun,
      backupPath,
      manifestConverted,
      skillsMappedReport,
      decisionsValid: decisions.value.valid,
      decisionsQuarantined: decisions.value.quarantined,
      mirrorsRemoved,
      warnings: Object.freeze(warnings),
      nextSteps: NEXT_STEPS,
    }),
  );
};

// -----------------------------------------------------------------------------
// Rollback
// -----------------------------------------------------------------------------

export interface RollbackInput {
  readonly projectRoot: string;
}

export interface RollbackReport {
  readonly projectRoot: string;
  readonly restoredFrom: string;
}

export const rollbackV2ToV3 = async (
  input: RollbackInput,
  deps: MigrationDeps,
): Promise<Result<RollbackReport, MigrationError>> => {
  const { fs, telemetry } = deps;
  const root = input.projectRoot;
  const backup = join(root, BACKUP_REL);
  const target = join(root, V2_ROOT_REL);

  if (!(await fs.exists(backup))) {
    await telemetry.emit({
      level: "warn",
      type: "migration.rollback_no_backup",
      attributes: { projectRoot: root, backup },
    });
    return err(
      new MigrationError(
        `No backup directory found at ${BACKUP_REL}; nothing to roll back`,
        "rollback-no-backup",
      ),
    );
  }

  if (await fs.exists(target)) {
    const removed = await fs.removeTree(target);
    if (isErr(removed)) {
      return err(
        new MigrationError(
          `Failed to clear ${V2_ROOT_REL} before rollback: ${removed.error.message}`,
          "rollback-failed",
        ),
      );
    }
  }
  const copied = await fs.copyTree(backup, target);
  if (isErr(copied)) {
    return err(
      new MigrationError(
        `Rollback copy failed: ${copied.error.message}`,
        "rollback-failed",
      ),
    );
  }

  await telemetry.emit({
    level: "audit",
    type: "migration.rollback_completed",
    attributes: { projectRoot: root, restoredFrom: backup },
  });

  return ok(
    Object.freeze({
      projectRoot: root,
      restoredFrom: backup,
    }),
  );
};

// -----------------------------------------------------------------------------
// Test-only exports (for unit tests of pure helpers).
// -----------------------------------------------------------------------------
export const __TEST_ONLY__ = Object.freeze({
  buildSkillMap,
  renderManifestToml,
  splitDecisions,
});
