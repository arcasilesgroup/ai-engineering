import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");
const skillRoot = join(root, "skills");
const frontmatterPattern = /^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/;
const skillFiles = readdirSync(skillRoot, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && existsSync(join(skillRoot, entry.name, "SKILL.md")))
  .map((entry) => join(skillRoot, entry.name, "SKILL.md"));

if (skillFiles.length === 0) throw new Error("no core skill files found");

const frontmatterBytes = skillFiles.reduce((total, path) => {
  const frontmatter = frontmatterPattern.exec(readFileSync(path, "utf8"));
  if (!frontmatter) throw new Error(`missing skill frontmatter: ${path}`);
  return total + Buffer.byteLength(frontmatter[0], "utf8");
}, 0);
const templateBytes = Buffer.byteLength(readFileSync(join(root, "templates", "AGENTS.md.tpl"), "utf8"));

console.log(`core skill frontmatter: ${frontmatterBytes / 4} tokens`);
console.log(`AGENTS.md template: ${templateBytes / 4} tokens`);
