import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { type ManifestKind, isErr, validateManifest } from "@ai-engineering/runtime";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng governance audit` — manifest integrity check.
 *
 * Reads the canonical manifests at the repo root and runs each through the
 * appropriate JSON schema via `validateManifest`. Output is a deterministic
 * audit summary the policy engine can consume; the LLM never enters this
 * path (Constitution III, dual-plane).
 *
 * Manifests audited:
 *   - `.ai-engineering/manifest.toml` — project-level (skill-shaped overlay)
 *   - `ai-engineering.toml`           — framework-level (skill-shaped overlay)
 *
 * Both files are TOML on disk. We do not ship a TOML parser at this layer;
 * we accept JSON-equivalents (`.ai-engineering/manifest.json` /
 * `ai-engineering.json`) as the audit's primary input when present so the
 * use case can run in CI without an extra dep. If only the TOML form
 * exists, we surface that as a "skipped" finding rather than failing,
 * matching the Phase 4.1 guidance that manifest parsing lands later.
 */
interface AuditFinding {
  readonly file: string;
  readonly kind: ManifestKind | "unknown";
  readonly status: "pass" | "fail" | "skipped";
  readonly message?: string;
}

const MANIFEST_TARGETS: ReadonlyArray<{
  readonly relPath: string;
  readonly kind: ManifestKind;
}> = Object.freeze([
  { relPath: ".ai-engineering/manifest.json", kind: "skill" },
  { relPath: "ai-engineering.json", kind: "skill" },
]);

const TOML_FALLBACKS: ReadonlyArray<string> = Object.freeze([
  ".ai-engineering/manifest.toml",
  "ai-engineering.toml",
]);

const auditFile = (absPath: string, relPath: string, kind: ManifestKind): AuditFinding => {
  let raw: string;
  try {
    raw = readFileSync(absPath, "utf8");
  } catch (e) {
    return {
      file: relPath,
      kind,
      status: "fail",
      message: `read failed: ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    return {
      file: relPath,
      kind,
      status: "fail",
      message: `invalid JSON: ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  const result = validateManifest(parsed, kind);
  if (isErr(result)) {
    return {
      file: relPath,
      kind,
      status: "fail",
      message: result.error.message,
    };
  }
  return { file: relPath, kind, status: "pass" };
};

const runAudit = (cwd: string): ReadonlyArray<AuditFinding> => {
  const findings: AuditFinding[] = [];
  for (const target of MANIFEST_TARGETS) {
    const abs = join(cwd, target.relPath);
    if (existsSync(abs)) {
      findings.push(auditFile(abs, target.relPath, target.kind));
    }
  }
  for (const fallback of TOML_FALLBACKS) {
    const abs = join(cwd, fallback);
    const jsonAbs = abs.replace(/\.toml$/, ".json");
    if (existsSync(abs) && !existsSync(jsonAbs)) {
      findings.push({
        file: fallback,
        kind: "unknown",
        status: "skipped",
        message: "TOML manifest detected; JSON twin not present (audit skipped)",
      });
    }
  }
  return findings;
};

const renderHuman = (findings: ReadonlyArray<AuditFinding>): string => {
  if (findings.length === 0) {
    return "[ai-eng] governance audit: no manifests found at canonical paths.\n";
  }
  const lines = ["[ai-eng] governance audit"];
  for (const f of findings) {
    const mark = f.status === "pass" ? "OK" : f.status === "skipped" ? "..." : "FAIL";
    const detail = f.message !== undefined ? ` -- ${f.message}` : "";
    lines.push(`  [${mark}] ${f.file} (${f.kind})${detail}`);
  }
  return `${lines.join("\n")}\n`;
};

const auditHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const findings = runAudit(process.cwd());
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ findings }, null, 2)}\n`);
  } else {
    process.stdout.write(renderHuman(findings));
  }
  const failed = findings.some((f) => f.status === "fail");
  return failed ? 2 : 0;
};

const usage = (): void => {
  process.stderr.write("usage: ai-eng governance <audit> [--json]\n");
};

export const governance: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "audit") {
    return auditHandler(rest);
  }
  process.stderr.write(`unknown governance subcommand: ${sub}\n`);
  usage();
  return 1;
};
