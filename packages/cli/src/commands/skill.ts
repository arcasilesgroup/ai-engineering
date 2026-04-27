import { existsSync, readFileSync, readdirSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

import { NodeFilesystemAdapter, SkillId, isErr, registerSkill } from "@ai-engineering/runtime";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng skill <list|new|audit>` — manage the skill catalog.
 *
 * Constitution Article V: skills live ONCE in `skills/catalog/<name>/SKILL.md`.
 * This command is the deterministic adapter for the registration use case;
 * the LLM never enters this path.
 *
 * Subcommands:
 *   - `list`         — print frontmatter summary for every skill in catalog
 *   - `new <name>`   — scaffold `skills/catalog/<name>/SKILL.md` from template
 *   - `audit`        — validate every SKILL.md against the JSON schema
 */
const FRONTMATTER_RE = /^---\s*\n([\s\S]*?)\n---\s*\n/;

const NAME_RE = /^[a-z][a-z0-9-]{0,63}$/;

const catalogPath = (): string => join(process.cwd(), "skills", "catalog");

const listSkillDirs = (catalog: string): string[] => {
  if (!existsSync(catalog)) return [];
  return readdirSync(catalog, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .sort();
};

interface SkillSummary {
  readonly name: string;
  readonly path: string;
  readonly description?: string;
  readonly effort?: string;
  readonly tier?: string;
}

const parseSimpleFrontmatter = (raw: string): Readonly<Record<string, string>> => {
  const out: Record<string, string> = {};
  for (const line of raw.split("\n")) {
    const m = /^([a-zA-Z_-]+):\s*(.+?)\s*$/.exec(line);
    if (m && m[1] !== undefined && m[2] !== undefined) {
      out[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
  return Object.freeze(out);
};

const summariseSkill = (catalog: string, name: string): SkillSummary | null => {
  const skillPath = join(catalog, name, "SKILL.md");
  if (!existsSync(skillPath)) return null;
  const raw = readFileSync(skillPath, "utf8");
  const m = FRONTMATTER_RE.exec(raw);
  if (!m || m[1] === undefined) {
    return { name, path: skillPath };
  }
  const fm = parseSimpleFrontmatter(m[1]);
  return {
    name: fm.name ?? name,
    path: skillPath,
    ...(fm.description !== undefined ? { description: fm.description } : {}),
    ...(fm.effort !== undefined ? { effort: fm.effort } : {}),
    ...(fm.tier !== undefined ? { tier: fm.tier } : {}),
  };
};

const listHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const catalog = catalogPath();
  const dirs = listSkillDirs(catalog);
  const summaries = dirs
    .map((d) => summariseSkill(catalog, d))
    .filter((s): s is SkillSummary => s !== null);
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ skills: summaries }, null, 2)}\n`);
    return 0;
  }
  if (summaries.length === 0) {
    process.stdout.write("[ai-eng] skill list: no skills found under skills/catalog/.\n");
    return 0;
  }
  process.stdout.write(`[ai-eng] skill list (${summaries.length})\n`);
  for (const s of summaries) {
    const tier = s.tier !== undefined ? ` [${s.tier}]` : "";
    const effort = s.effort !== undefined ? ` (effort=${s.effort})` : "";
    const desc =
      s.description !== undefined
        ? `\n      ${s.description.slice(0, 120)}${s.description.length > 120 ? "..." : ""}`
        : "";
    process.stdout.write(`  - ${s.name}${tier}${effort}${desc}\n`);
  }
  return 0;
};

const SKILL_TEMPLATE = (name: string): string =>
  [
    "---",
    `name: ${name}`,
    `description: TODO — describe when to use ${name}.`,
    "effort: medium",
    "tier: core",
    "capabilities: [tool_use]",
    "governance:",
    "  blocking: false",
    "---",
    "",
    `# /ai-${name}`,
    "",
    "TODO: write the body. See existing skills under `skills/catalog/` for examples.",
    "",
    "## When to use",
    "",
    "- TODO",
    "",
    "## Process",
    "",
    "1. TODO",
    "",
    "## Hard rules",
    "",
    "- TODO",
    "",
    "## Common mistakes",
    "",
    "- TODO",
    "",
  ].join("\n");

const newHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const name = parsed.positional[0];
  if (name === undefined || name.length === 0) {
    process.stderr.write("usage: ai-eng skill new <name>\n");
    return 1;
  }
  if (!NAME_RE.test(name)) {
    process.stderr.write(
      `invalid skill name "${name}" (expected lowercase, alphanumeric and hyphens, max 64 chars)\n`,
    );
    return 1;
  }
  const catalog = catalogPath();
  const dst = join(catalog, name, "SKILL.md");
  if (existsSync(dst)) {
    process.stderr.write(`skill already exists at ${dst}\n`);
    return 1;
  }
  await mkdir(join(catalog, name), { recursive: true });
  await writeFile(dst, SKILL_TEMPLATE(name), "utf8");
  process.stdout.write(`[ai-eng] scaffolded skill at ${dst}\n`);
  return 0;
};

interface AuditEntry {
  readonly name: string;
  readonly status: "pass" | "fail";
  readonly message?: string;
}

const auditOne = async (
  catalog: string,
  dir: string,
  fs: NodeFilesystemAdapter,
): Promise<AuditEntry> => {
  const skillPath = join(catalog, dir, "SKILL.md");
  if (!existsSync(skillPath)) {
    return { name: dir, status: "fail", message: "SKILL.md missing" };
  }
  const result = await registerSkill({ id: SkillId(dir), path: skillPath }, fs);
  if (isErr(result)) {
    return { name: dir, status: "fail", message: result.error.message };
  }
  return { name: dir, status: "pass" };
};

const renderAuditHuman = (entries: ReadonlyArray<AuditEntry>): void => {
  if (entries.length === 0) {
    process.stdout.write("[ai-eng] skill audit: no skills found under skills/catalog/.\n");
    return;
  }
  process.stdout.write(`[ai-eng] skill audit (${entries.length})\n`);
  for (const e of entries) {
    const mark = e.status === "pass" ? "OK" : "FAIL";
    const detail = e.message !== undefined ? ` -- ${e.message}` : "";
    process.stdout.write(`  [${mark}] ${e.name}${detail}\n`);
  }
};

const auditHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const catalog = catalogPath();
  const dirs = listSkillDirs(catalog);
  const fs = new NodeFilesystemAdapter();
  const entries: AuditEntry[] = [];
  for (const dir of dirs) {
    entries.push(await auditOne(catalog, dir, fs));
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ entries }, null, 2)}\n`);
  } else {
    renderAuditHuman(entries);
  }
  const failed = entries.filter((e) => e.status === "fail").length;
  return failed > 0 ? 2 : 0;
};

const usage = (): void => {
  process.stderr.write(
    [
      "usage: ai-eng skill <list|new|audit> [args] [--json]",
      "  list             list all skills in skills/catalog/",
      "  new <name>       scaffold a new SKILL.md from template",
      "  audit            validate every SKILL.md against the schema",
      "",
    ].join("\n"),
  );
};

export const skill: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "list") return listHandler(rest);
  if (sub === "new") return newHandler(rest);
  if (sub === "audit") return auditHandler(rest);
  process.stderr.write(`unknown skill subcommand: ${sub}\n`);
  usage();
  return 1;
};
