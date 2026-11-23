// The CI templates install a pinned release of the governor, and that pin has to name the
// version package.json ships. A bump that leaves it behind points every generated pipeline
// at the previous release, and nobody remembers a step at release time, so the bump and the
// pin are one act: `bun run version-packages` (changesets first, then this) is what
// .github/workflows/version.yml runs, so the pin rides in the same Version Packages PR.
//
// Usage: bun scripts/sync-ci-template-pins.ts [root]   (root defaults to this repository)
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { releaseFlags } from "./release-flags.ts";

const KEY = "AI_ENG_VERSION";
const TEMPLATES = ["templates/ci.yml.tpl", "templates/azure-pipelines.yml.tpl"];

// Only the value moves: the indentation, the key and every other byte of the file stay as
// they are, so the pin is a one-value edit and not a reformat of hand-written YAML.
function pinLine(): RegExp {
  return new RegExp(`^([ \\t]*${KEY}:[ \\t]*)v\\S+$`, "gm");
}

export function syncPinText(text: string, pin: string, file: string): string {
  if (!pinLine().test(text)) {
    throw new Error(`${file} has no "${KEY}: vX.Y.Z" line to rewrite: a template without the pin ships a pipeline that cannot find its binary.`);
  }
  return text.replace(pinLine(), (_line, prefix: string) => `${prefix}${pin}`);
}

// Every template that pins the version, rewritten from package.json. Returns only what
// changed, so a rerun of an already-synced tree writes nothing and reports nothing.
export function syncCiTemplatePins(root: string): { file: string; pin: string }[] {
  const { version } = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as { version: string };
  const { tag: pin } = releaseFlags(version);
  const changed: { file: string; pin: string }[] = [];
  for (const file of TEMPLATES) {
    const path = join(root, file);
    const before = readFileSync(path, "utf8");
    const after = syncPinText(before, pin, file);
    if (after === before) continue;
    writeFileSync(path, after);
    changed.push({ file, pin });
  }
  return changed;
}

if (import.meta.main) {
  try {
    const changed = syncCiTemplatePins(resolve(process.argv[2] ?? join(import.meta.dir, "..")));
    for (const { file, pin } of changed) process.stdout.write(`${file}: ${KEY} ${pin}\n`);
    if (changed.length === 0) process.stdout.write(`${KEY}: every template already pins this version\n`);
  } catch (error) {
    process.stderr.write(`sync-ci-template-pins: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  }
}
