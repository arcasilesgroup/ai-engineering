// Frontmatter linter for skills canon and behaviors (§11.1 rule 3+5): description
// with usage verbs, ≤1024 chars, single line, strict 3-field YAML, name = folder.
// A broken frontmatter is an invisible skill — that is a FAIL, not a warning.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { join, basename } from "node:path";

export type SkillLint = { skill: string; ok: boolean; problems: string[] };

const USAGE_HINT = /(úsalo|usar|use|trigger|cuando|when|before|antes|para)/i;

export function lintSkill(dir: string): SkillLint {
  const skill = basename(dir);
  const problems: string[] = [];
  const skillMd = join(dir, "SKILL.md");
  if (!existsSync(skillMd)) {
    return { skill, ok: false, problems: ["sin SKILL.md"] };
  }
  const content = readFileSync(skillMd, "utf8");
  const match = /^---\n([\s\S]*?)\n---/.exec(content);
  if (!match) {
    return { skill, ok: false, problems: ["frontmatter ausente"] };
  }
  const body = match[1] ?? "";
  const lines = body.split("\n");
  const fields: Record<string, string> = {};
  const unknown: string[] = [];
  for (const line of lines) {
    const kv = /^([a-zA-Z_-]+):\s*(.*)$/.exec(line);
    if (!kv) {
      if (line.trim().length > 0 && !line.startsWith(" ") && !line.startsWith("-")) unknown.push(line.slice(0, 40));
      continue;
    }
    fields[kv[1]!] = kv[2]!.trim();
  }
  const known = ["name", "description", "license"];
  for (const key of Object.keys(fields)) {
    if (!known.includes(key)) unknown.push(key);
  }
  if (unknown.length > 0) problems.push(`campos extra: ${unknown.join(", ")} — un frontmatter roto es un skill invisible`);
  if (fields["name"] !== skill) problems.push(`name=${fields["name"] ?? ""} ≠ carpeta`);
  const description = fields["description"] ?? "";
  if (description.length === 0) problems.push("description vacía");
  if (description.length > 1024) problems.push(`description ${description.length} > 1024 chars`);
  if (description.includes("\\n")) problems.push("description con salto de línea artificial");
  if (!USAGE_HINT.test(description)) problems.push("description sin verbo de uso (doctor WARN: un skill que no matchea no existe)");
  const license = fields["license"] ?? "";
  const SPDX = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "CC0-1.0"];
  if (!SPDX.includes(license)) problems.push(`license="${license}" no es un identificador SPDX conocido`);
  return { skill, ok: problems.length === 0, problems };
}

export function lintAllSkills(skillsDir: string): SkillLint[] {
  if (!existsSync(skillsDir)) return [];
  return readdirSync(skillsDir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => lintSkill(join(skillsDir, e.name)));
}

export function hashFile(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}
