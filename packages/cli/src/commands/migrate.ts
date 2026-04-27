import { existsSync } from "node:fs";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import {
  IOError,
  type MigrationDeps,
  type MigrationFsPort,
  type MigrationReport,
  type Result,
  type SkillMapEntry,
  err,
  isErr,
  migrateV2ToV3,
  ok,
  rollbackV2ToV3,
} from "@ai-engineering/runtime";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng migrate` — v2-to-v3 migrator (Phase 8).
 *
 * Subcommands:
 *   - `v2-to-v3 [--dry-run] [--yes] [--json]`
 *   - `rollback [--yes] [--json]`
 *
 * The actual logic lives in `runtime/platform/application/migrate_v2_to_v3.ts`;
 * this command is a thin driving adapter that wires the real filesystem and
 * a stdout-only telemetry sink to the use case.
 *
 * Exit codes:
 *   0 — success
 *   1 — user error (missing confirmation, invalid input)
 *   2 — nothing to migrate (no v2 layout detected)
 */

// -----------------------------------------------------------------------------
// node:fs/promises-backed MigrationFsPort
// -----------------------------------------------------------------------------

const wrapFsError =
  (op: string, path: string) =>
  (e: unknown): IOError =>
    new IOError(`${op} failed for ${path}: ${e instanceof Error ? e.message : String(e)}`);

const realFs: MigrationFsPort = {
  async exists(path) {
    return existsSync(path);
  },
  async readText(path) {
    try {
      return ok(await readFile(path, "utf8"));
    } catch (e) {
      return err(wrapFsError("readText", path)(e));
    }
  },
  async writeText(path, content) {
    try {
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, content, "utf8");
      return ok(undefined);
    } catch (e) {
      return err(wrapFsError("writeText", path)(e));
    }
  },
  async mkdirp(path) {
    try {
      await mkdir(path, { recursive: true });
      return ok(undefined);
    } catch (e) {
      return err(wrapFsError("mkdirp", path)(e));
    }
  },
  async copyTree(from, to) {
    try {
      await mkdir(dirname(to), { recursive: true });
      await cp(from, to, { recursive: true });
      return ok(undefined);
    } catch (e) {
      return err(wrapFsError("copyTree", `${from}->${to}`)(e));
    }
  },
  async removeTree(path) {
    try {
      await rm(path, { recursive: true, force: true });
      return ok(undefined);
    } catch (e) {
      return err(wrapFsError("removeTree", path)(e));
    }
  },
};

// -----------------------------------------------------------------------------
// stdout/stderr telemetry adapter (process-local; the real OTel pipeline lives
// in the runtime adapters, but the CLI doesn't need persistence here — every
// event is also surfaced in the human-readable summary).
// -----------------------------------------------------------------------------

class StdoutTelemetry {
  readonly emitted: Array<{
    level: string;
    type: string;
    attributes: Record<string, unknown>;
  }> = [];
  async emit(event: {
    level: string;
    type: string;
    attributes: Record<string, unknown>;
  }): Promise<void> {
    this.emitted.push({
      level: event.level,
      type: event.type,
      attributes: { ...event.attributes },
    });
  }
  startSpan(): never {
    throw new Error("migrate CLI does not use spans");
  }
}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

const requireConfirmation = (
  parsed: ReturnType<typeof parseArgs>,
  prompt: string,
): Result<void, string> => {
  if (hasFlag(parsed, "yes") || hasFlag(parsed, "dry-run")) return ok(undefined);
  return err(prompt);
};

const renderSkillMap = (entries: ReadonlyArray<SkillMapEntry>): string => {
  if (entries.length === 0) return "  (no v2 skills supplied)";
  return entries
    .map((e) => {
      const target = e.v3 ?? "(eliminated)";
      const tag = `[${e.kind}]`.padEnd(13);
      const head = `  ${tag} ${e.v2} -> ${target}`;
      return e.warning !== undefined ? `${head}  // ${e.warning}` : head;
    })
    .join("\n");
};

const renderHumanReport = (
  report: MigrationReport,
  telemetryTypes: ReadonlyArray<string>,
): string => {
  const lines: string[] = [];
  lines.push("[ai-eng] migrate v2-to-v3");
  lines.push(`  dry-run             ${report.dryRun ? "yes" : "no"}`);
  lines.push(`  backup              ${report.backupPath}`);
  lines.push(`  manifest converted  ${report.manifestConverted ? "yes" : "(planned)"}`);
  lines.push(`  skills mapped       ${report.skillsMappedReport.length} entries`);
  lines.push(
    `  decisions valid     ${report.decisionsValid} / quarantined ${report.decisionsQuarantined}`,
  );
  lines.push(
    `  mirrors removed     ${report.mirrorsRemoved.length} (${
      report.mirrorsRemoved.join(", ") || "-"
    })`,
  );
  if (report.skillsMappedReport.length > 0) {
    lines.push("");
    lines.push("Skill mapping:");
    lines.push(renderSkillMap(report.skillsMappedReport));
  }
  if (report.warnings.length > 0) {
    lines.push("");
    lines.push("Warnings:");
    for (const w of report.warnings) lines.push(`  - ${w}`);
  }
  lines.push("");
  lines.push("Next steps:");
  for (const s of report.nextSteps) lines.push(`  - ${s}`);
  lines.push("");
  lines.push(`(${telemetryTypes.length} telemetry events emitted)`);
  lines.push("");
  return lines.join("\n");
};

// -----------------------------------------------------------------------------
// Subcommands
// -----------------------------------------------------------------------------

const v2ToV3Handler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const dryRun = hasFlag(parsed, "dry-run");
  const json = hasFlag(parsed, "json");

  // Confirmation guard before destructive run.
  if (!dryRun) {
    const confirm = requireConfirmation(
      parsed,
      "migrate v2-to-v3 will modify .ai-engineering/. Re-run with --yes to confirm or --dry-run to preview.",
    );
    if (isErr(confirm)) {
      process.stderr.write(`${confirm.error}\n`);
      return 1;
    }
  }

  const cwd = process.cwd();
  const telemetry = new StdoutTelemetry();
  const deps: MigrationDeps = { fs: realFs, telemetry };

  const result = await migrateV2ToV3({ projectRoot: cwd, dryRun }, deps);
  if (isErr(result)) {
    if (result.error.reason === "not-v2") {
      if (json) {
        process.stdout.write(
          `${JSON.stringify(
            {
              ok: false,
              reason: result.error.reason,
              message: result.error.message,
            },
            null,
            2,
          )}\n`,
        );
      } else {
        process.stderr.write(`${result.error.message}\n`);
      }
      return 2;
    }
    if (json) {
      process.stdout.write(
        `${JSON.stringify(
          {
            ok: false,
            reason: result.error.reason,
            message: result.error.message,
          },
          null,
          2,
        )}\n`,
      );
    } else {
      process.stderr.write(
        `migrate v2-to-v3 failed (${result.error.reason}): ${result.error.message}\n`,
      );
    }
    return 1;
  }
  if (json) {
    process.stdout.write(
      `${JSON.stringify(
        {
          ok: true,
          report: result.value,
          telemetry: telemetry.emitted.map((e) => e.type),
        },
        null,
        2,
      )}\n`,
    );
    return 0;
  }
  process.stdout.write(
    renderHumanReport(
      result.value,
      telemetry.emitted.map((e) => e.type),
    ),
  );
  return 0;
};

const rollbackHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const json = hasFlag(parsed, "json");
  const confirm = requireConfirmation(
    parsed,
    "migrate rollback will overwrite .ai-engineering/ from .ai-engineering.v2.bak/. Re-run with --yes to confirm.",
  );
  if (isErr(confirm)) {
    process.stderr.write(`${confirm.error}\n`);
    return 1;
  }

  const cwd = process.cwd();
  const telemetry = new StdoutTelemetry();
  const deps: MigrationDeps = { fs: realFs, telemetry };
  const result = await rollbackV2ToV3({ projectRoot: cwd }, deps);
  if (isErr(result)) {
    if (json) {
      process.stdout.write(
        `${JSON.stringify(
          {
            ok: false,
            reason: result.error.reason,
            message: result.error.message,
          },
          null,
          2,
        )}\n`,
      );
    } else {
      process.stderr.write(
        `migrate rollback failed (${result.error.reason}): ${result.error.message}\n`,
      );
    }
    return result.error.reason === "rollback-no-backup" ? 2 : 1;
  }
  if (json) {
    process.stdout.write(`${JSON.stringify({ ok: true, ...result.value }, null, 2)}\n`);
    return 0;
  }
  process.stdout.write(
    `[ai-eng] migrate rollback: restored .ai-engineering/ from ${result.value.restoredFrom}\n`,
  );
  return 0;
};

// -----------------------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------------------

const usage = (): void => {
  process.stderr.write(
    [
      "usage:",
      "  ai-eng migrate v2-to-v3 [--dry-run] [--yes] [--json]",
      "  ai-eng migrate rollback [--yes] [--json]",
      "",
    ].join("\n"),
  );
};

export const migrate: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "v2-to-v3") return v2ToV3Handler(rest);
  if (sub === "rollback") return rollbackHandler(rest);
  process.stderr.write(`unknown migrate subcommand: ${sub}\n`);
  usage();
  return 1;
};

// Test-only export so a CLI test can verify the helpers stay deterministic
// without spawning subprocesses.
export const __TEST_ONLY__ = Object.freeze({ realFs });
