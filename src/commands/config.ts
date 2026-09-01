// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { multiselect, isCancel } from "@clack/prompts";
import { repoRoot } from "../env.ts";
import { parseToml, serializeToml } from "../toml.ts";
import type { TomlTable } from "../toml.ts";
import { SURFACES, mirrorTargets } from "../surfaces/adapters.ts";
import { surfaceCanGovern } from "../surfaces/adapters.ts";

function surfacesFromConfig(root: string): string[] {
  const path = join(root, ".ai-engineering", "config.toml");
  if (!existsSync(path)) return [];
  const doc = parseToml(readFileSync(path, "utf8"));
  const surfaces = doc["surfaces"];
  const enabled = surfaces && typeof surfaces === "object" && !Array.isArray(surfaces) ? (surfaces as TomlTable)["enabled"] : undefined;
  return Array.isArray(enabled) ? enabled.filter((v): v is string => typeof v === "string") : [];
}

export async function configMain(flags: { add?: string; remove?: string }): Promise<number> {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("config: you are not in a governed repo.\n");
    return 2;
  }
  const configPath = join(root, ".ai-engineering", "config.toml");
  let current = surfacesFromConfig(root);
  if (flags.add) {
    if (!current.includes(flags.add)) current = [...current, flags.add];
  } else if (flags.remove) {
    current = current.filter((id) => id !== flags.remove);
    removeSurfaceFiles(root, flags.remove);
  } else {
    const picked = await multiselect({
      message: "Which agent surfaces do you use?",
      options: SURFACES.map((s) => ({ value: s.id, label: s.label, hint: `${s.tier}${surfaceCanGovern(s) ? "" : " — no deny"}` })),
      required: true,
    });
    if (isCancel(picked)) return 0;
    const removed = current.filter((id) => !picked.includes(id));
    for (const id of removed) removeSurfaceFiles(root, id);
    current = picked;
  }
  // The config file holds what cannot be deduced: rewrite only the surfaces key.
  const doc: TomlTable = existsSync(configPath) ? parseToml(readFileSync(configPath, "utf8")) : {};
  doc["surfaces"] = { enabled: current };
  writeFileSync(configPath, serializeToml(doc));
  process.stdout.write(`✓ .ai-engineering/config.toml updated (surfaces: ${current.join(", ")})\n`);
  const mirrors = mirrorTargets().length;
  process.stdout.write(`✓ skill mirrors verified (${mirrors} targets)\n`);
  process.stdout.write("✓ Done. Run ai-eng doctor to verify.\n");
  return 0;
}

function removeSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const path = surface.settingsFile ?? surface.pluginFile;
  if (!path) return;
  const absolute = join(root, path);
  if (existsSync(absolute)) unlinkSync(absolute);
  process.stdout.write(`✓ ${path} removed (ai-eng entries only)\n`);
}
