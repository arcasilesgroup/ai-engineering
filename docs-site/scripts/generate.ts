#!/usr/bin/env bun
/*
 * docs-site/scripts/generate.ts
 *
 * Reads the source-of-truth files in the repo and emits Markdown index
 * pages under `src/content/docs/`. Run with `bun scripts/generate.ts`.
 *
 * Inputs:
 *   - skills/catalog/<name>/SKILL.md       (29 core)
 *   - skills/regulated/<name>/SKILL.md     ( 4 regulated)
 *   - agents/<name>/AGENT.md               ( 7)
 *   - docs/adr/*.md                        (10)
 *
 * Outputs:
 *   - src/content/docs/skills/index.md
 *   - src/content/docs/agents/index.md
 *   - src/content/docs/adr/index.md
 *
 * The generator is intentionally dependency-free: no remark, no
 * gray-matter, no globby. We parse YAML frontmatter ourselves because
 * the catalog uses a tiny, predictable subset (no nested objects beyond
 * one level, no multi-line scalars beyond `description:`).
 */

import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", "..");
const OUT = resolve(HERE, "..", "src", "content", "docs");

// ---------------------------------------------------------------------------
// Tiny, defensive frontmatter parser.
// ---------------------------------------------------------------------------

interface Frontmatter {
  [key: string]: string | string[] | boolean | number | undefined;
}

function coerceScalar(value: string): string | string[] | boolean {
  if (value.startsWith("[") && value.endsWith("]")) {
    return value
      .slice(1, -1)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  if (value === "true") return true;
  if (value === "false") return false;
  // Strip wrapping quotes if present.
  return value.replace(/^["'](.*)["']$/, "$1");
}

type ParsedLine =
  | { kind: "blank" }
  | { kind: "nested" }
  | { kind: "parent"; key: string }
  | { kind: "scalar"; key: string; value: string }
  | { kind: "noop" };

function parseFmLine(line: string, parentKey: string | null): ParsedLine {
  if (line.trim().length === 0) return { kind: "blank" };
  // Nested key (two-space indent) — skip when we're inside a parent.
  if (parentKey && /^ {2}[A-Za-z_]/.test(line)) return { kind: "nested" };
  const top = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
  if (!top?.[1]) return { kind: "noop" };
  const key = top[1];
  // Strip inline `# comment` tails. The catalog uses these on a few
  // scalar values (e.g. `write_access: limited   # only writes…`).
  const value = (top[2] ?? "").replace(/\s+#.*$/, "").trim();
  if (value.length === 0) return { kind: "parent", key };
  return { kind: "scalar", key, value };
}

function parseFrontmatter(raw: string): { fm: Frontmatter; body: string } {
  // Match a leading --- ... --- block.
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return { fm: {}, body: raw };

  const fmRaw = match[1] ?? "";
  const body = match[2] ?? "";
  const fm: Frontmatter = {};

  // Line-by-line: handle `key: value`, lists `[a, b]`, and one level of
  // nested mapping (`governance:\n  blocking: true`). The catalog YAML
  // is hand-written and follows these rules; if a SKILL.md ever needs
  // richer YAML, swap this for `yaml` package.
  let parentKey: string | null = null;
  for (const line of fmRaw.split(/\r?\n/)) {
    const parsed = parseFmLine(line, parentKey);
    if (parsed.kind === "blank") parentKey = null;
    else if (parsed.kind === "parent") parentKey = parsed.key;
    else if (parsed.kind === "scalar") {
      parentKey = null;
      fm[parsed.key] = coerceScalar(parsed.value);
    }
  }
  return { fm, body };
}

// ---------------------------------------------------------------------------
// Helpers.
// ---------------------------------------------------------------------------

function readDirSafe(path: string): string[] {
  try {
    return readdirSync(path);
  } catch {
    return [];
  }
}

function isDir(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

function ensureDir(path: string): void {
  mkdirSync(path, { recursive: true });
}

function escapeMd(value: string): string {
  // Light escape so a raw `|` or trailing `\` does not break a table cell.
  return value.replace(/\|/g, "\\|").replace(/\n/g, " ").trim();
}

function repoLink(relPath: string): string {
  return `https://github.com/soydachi/ai-engineering/blob/main/${relPath}`;
}

// ---------------------------------------------------------------------------
// Skills index.
// ---------------------------------------------------------------------------

interface SkillRow {
  name: string;
  description: string;
  effort: string;
  tier: string;
  sourcePath: string;
}

function readSkillDir(rootKey: "catalog" | "regulated"): SkillRow[] {
  const root = join(REPO, "skills", rootKey);
  if (!isDir(root)) return [];
  const rows: SkillRow[] = [];
  for (const name of readDirSafe(root).sort()) {
    const dir = join(root, name);
    if (!isDir(dir)) continue;
    const file = join(dir, "SKILL.md");
    let raw: string;
    try {
      raw = readFileSync(file, "utf8");
    } catch {
      continue;
    }
    const { fm } = parseFrontmatter(raw);
    rows.push({
      name: String(fm.name ?? name),
      description: String(fm.description ?? "").trim(),
      effort: String(fm.effort ?? ""),
      tier: String(fm.tier ?? rootKey),
      sourcePath: `skills/${rootKey}/${name}/SKILL.md`,
    });
  }
  return rows;
}

function generateSkills(): void {
  const core = readSkillDir("catalog");
  const regulated = readSkillDir("regulated");

  const lines: string[] = [];
  lines.push("---");
  lines.push("title: Skills catalog");
  lines.push(
    "description: Auto-generated index of every SKILL.md (29 core + 4 regulated). Source of truth lives under skills/.",
  );
  lines.push("sidebar:");
  lines.push("  order: 1");
  lines.push("---");
  lines.push("");
  lines.push(
    "Skills are the framework's named workflows. Each is a single",
    "Markdown file under `skills/catalog/<name>/SKILL.md` (or",
    "`skills/regulated/<name>/SKILL.md`). The `ai-eng sync-mirrors`",
    "command regenerates IDE-specific copies under `.claude/`,",
    "`.cursor/`, `.codex/`, `.github/`, `.gemini/`, and `.agent/`.",
    "",
    "_This page is auto-generated by `docs-site/scripts/generate.ts`._",
    "",
  );

  const renderTable = (rows: SkillRow[]): string[] => {
    const out: string[] = [];
    out.push("| Skill | Effort | Description |");
    out.push("|-------|--------|-------------|");
    for (const r of rows) {
      const cmd = `\`/ai-${r.name}\``;
      const link = `[${cmd}](${repoLink(r.sourcePath)})`;
      out.push(`| ${link} | \`${r.effort}\` | ${escapeMd(r.description)} |`);
    }
    return out;
  };

  lines.push(`## Core (${core.length})`, "");
  lines.push(...renderTable(core));
  lines.push("", `## Regulated (${regulated.length})`, "");
  lines.push(
    "Activated by `ai-eng install --profile banking|healthcare|fintech|airgapped`.",
    "Dormant otherwise.",
    "",
  );
  lines.push(...renderTable(regulated));
  lines.push("");

  const out = join(OUT, "skills", "index.md");
  ensureDir(dirname(out));
  writeFileSync(out, lines.join("\n"));
  process.stdout.write(`wrote ${out} (${core.length} core + ${regulated.length} regulated)\n`);
}

// ---------------------------------------------------------------------------
// Agents index.
// ---------------------------------------------------------------------------

interface AgentRow {
  name: string;
  role: string;
  writeAccess: string;
  description: string;
  sourcePath: string;
}

function generateAgents(): void {
  const root = join(REPO, "agents");
  const rows: AgentRow[] = [];
  for (const name of readDirSafe(root).sort()) {
    const dir = join(root, name);
    if (!isDir(dir)) continue;
    const file = join(dir, "AGENT.md");
    let raw: string;
    try {
      raw = readFileSync(file, "utf8");
    } catch {
      continue;
    }
    const { fm, body } = parseFrontmatter(raw);
    // First non-heading paragraph is our description.
    const desc = (() => {
      const blocks = body
        .split(/\r?\n\r?\n/)
        .map((b) => b.trim())
        .filter(Boolean);
      for (const block of blocks) {
        if (block.startsWith("#")) continue;
        return block.replace(/\r?\n/g, " ");
      }
      return "";
    })();
    rows.push({
      name: String(fm.name ?? name),
      role: String(fm.role ?? ""),
      writeAccess: String(fm.write_access ?? "false"),
      description: desc,
      sourcePath: `agents/${name}/AGENT.md`,
    });
  }

  const lines: string[] = [];
  lines.push("---");
  lines.push("title: Agents");
  lines.push(
    "description: Auto-generated index of the 7 agent role definitions. Source of truth lives under agents/.",
  );
  lines.push("sidebar:");
  lines.push("  order: 1");
  lines.push("---");
  lines.push("");
  lines.push(
    "Agents are the actors that execute skills. Only the `builder`",
    "agent has write permissions; the others orchestrate, research,",
    "review, or scan. Source of truth lives under `agents/<name>/AGENT.md`.",
    "",
    "_This page is auto-generated by `docs-site/scripts/generate.ts`._",
    "",
  );
  lines.push("| Agent | Role | Write access | Description |");
  lines.push("|-------|------|--------------|-------------|");
  for (const r of rows) {
    const link = `[\`${r.name}\`](${repoLink(r.sourcePath)})`;
    lines.push(
      `| ${link} | ${escapeMd(r.role)} | \`${r.writeAccess}\` | ${escapeMd(r.description)} |`,
    );
  }
  lines.push("");

  const out = join(OUT, "agents", "index.md");
  ensureDir(dirname(out));
  writeFileSync(out, lines.join("\n"));
  process.stdout.write(`wrote ${out} (${rows.length} agents)\n`);
}

// ---------------------------------------------------------------------------
// ADRs index.
// ---------------------------------------------------------------------------

interface AdrRow {
  id: string;
  title: string;
  status: string;
  date: string;
  context: string;
  sourcePath: string;
}

function findFirstH1(lines: readonly string[]): string {
  for (const line of lines) {
    if (line.startsWith("# ")) return line.replace(/^#\s+/, "").trim();
  }
  return "";
}

function findHeaderField(lines: readonly string[], field: "Status" | "Date"): string {
  const re = new RegExp(`\\*\\*${field}\\*\\*:\\s*(.+)$`);
  for (const line of lines.slice(0, 12)) {
    const m = line.match(re);
    if (m?.[1]) return m[1].trim();
  }
  return "";
}

function extractContextParagraph(lines: readonly string[]): string {
  const ctxIdx = lines.findIndex((l) => l.trim().toLowerCase() === "## context");
  if (ctxIdx < 0) return "";
  const buf: string[] = [];
  for (let i = ctxIdx + 1; i < lines.length; i++) {
    const line = lines[i] ?? "";
    if (line.startsWith("## ")) break;
    if (line.trim().length === 0) {
      if (buf.length > 0) break;
      continue;
    }
    buf.push(line.trim());
  }
  let context = buf.join(" ").replace(/\s+/g, " ");
  if (context.length > 280) context = `${context.slice(0, 277).trimEnd()}…`;
  return context;
}

function parseAdr(raw: string): {
  title: string;
  status: string;
  date: string;
  context: string;
} {
  const lines = raw.split(/\r?\n/);
  return {
    title: findFirstH1(lines),
    status: findHeaderField(lines, "Status"),
    date: findHeaderField(lines, "Date"),
    context: extractContextParagraph(lines),
  };
}

function readAdrRows(): AdrRow[] {
  const root = join(REPO, "docs", "adr");
  const rows: AdrRow[] = [];
  for (const file of readDirSafe(root).sort()) {
    if (!file.endsWith(".md")) continue;
    const path = join(root, file);
    let raw: string;
    try {
      raw = readFileSync(path, "utf8");
    } catch {
      continue;
    }
    const parsed = parseAdr(raw);
    rows.push({
      id: file.replace(/\.md$/, ""),
      ...parsed,
      sourcePath: `docs/adr/${file}`,
    });
  }
  return rows;
}

function renderAdrTable(rows: readonly AdrRow[]): string[] {
  const out: string[] = ["| ID | Title | Status | Date |", "|----|-------|--------|------|"];
  for (const r of rows) {
    const link = `[${r.id}](${repoLink(r.sourcePath)})`;
    const cleanTitle = escapeMd(r.title.replace(/^ADR-\d+\s*[—-]\s*/i, ""));
    out.push(`| ${link} | ${cleanTitle} | ${escapeMd(r.status)} | ${escapeMd(r.date)} |`);
  }
  return out;
}

function renderAdrContextEntry(r: AdrRow): string[] {
  const out: string[] = [];
  // The H1 inside each ADR already reads "ADR-NNNN — Title", so we do
  // not prepend the file ID a second time here.
  out.push(`### [${escapeMd(r.title)}](${repoLink(r.sourcePath)})`, "");
  if (r.status || r.date) {
    const parts: string[] = [];
    if (r.status) parts.push(`**Status**: ${r.status}`);
    if (r.date) parts.push(`**Date**: ${r.date}`);
    out.push(parts.join(" · "), "");
  }
  if (r.context) out.push(r.context, "");
  return out;
}

function generateAdrs(): void {
  const rows = readAdrRows();
  const lines: string[] = [
    "---",
    "title: Architecture decision records",
    "description: Auto-generated index of all ADRs. Source of truth lives in docs/adr/.",
    "sidebar:",
    "  order: 1",
    "---",
    "",
    "ADRs document the WHY for every framework-level choice. They live",
    "in `docs/adr/` next to the code they describe so changes are",
    "visible in the same diff.",
    "",
    "_This page is auto-generated by `docs-site/scripts/generate.ts`._",
    "",
  ];
  lines.push(...renderAdrTable(rows));
  lines.push("", "## Context summaries", "");
  for (const r of rows) lines.push(...renderAdrContextEntry(r));

  const out = join(OUT, "adr", "index.md");
  ensureDir(dirname(out));
  writeFileSync(out, lines.join("\n"));
  process.stdout.write(`wrote ${out} (${rows.length} ADRs)\n`);
}

// ---------------------------------------------------------------------------
// Entry point.
// ---------------------------------------------------------------------------

function main(): void {
  ensureDir(OUT);
  generateSkills();
  generateAgents();
  generateAdrs();
  process.stdout.write("docs-site/scripts/generate.ts complete\n");
}

main();
