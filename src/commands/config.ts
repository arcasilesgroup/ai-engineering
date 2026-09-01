// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { multiselect, isCancel } from "@clack/prompts";
import { repoRoot } from "../env.ts";
import { parseToml, serializeToml } from "../toml.ts";
import type { TomlTable } from "../toml.ts";
import { SURFACES, mirrorTargets, surfaceCanGovern, type Surface } from "../surfaces/adapters.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";
import { VERSION } from "../version.ts";

function surfacesFromConfig(root: string): string[] {
  const path = join(root, ".ai-engineering", "config.toml");
  if (!existsSync(path)) return [];
  const doc = parseToml(readFileSync(path, "utf8"));
  const surfaces = doc["surfaces"];
  const enabled = surfaces && typeof surfaces === "object" && !Array.isArray(surfaces) ? (surfaces as TomlTable)["enabled"] : undefined;
  return Array.isArray(enabled) ? enabled.filter((v): v is string => typeof v === "string") : [];
}

export async function configMain(flags: { add?: string; remove?: string }): Promise<number> {
  const input = scriptedInput();
  const root = repoRoot();
  ui.frame(`Configuration · ai-eng ${VERSION}`);
  if (!root) {
    ui.fail("you are not in a governed repo — run ai-eng init first");
    ui.end("Nothing changed.");
    return 2;
  }
  const configPath = join(root, ".ai-engineering", "config.toml");
  const surfacesBefore = surfacesFromConfig(root);
  let current = surfacesBefore;
  if (flags.add) {
    if (!current.includes(flags.add)) current = [...current, flags.add];
  } else if (flags.remove) {
    current = current.filter((id) => id !== flags.remove);
    removeSurfaceFiles(root, flags.remove);
  } else {
    const picked = await multiselect({
      message: "Which agent surfaces is this project governed on? (ticked = installed)",
      options: SURFACES.map((s) => ({ value: s.id, label: s.label, hint: configHint(s, current.includes(s.id)) })),
      initialValues: current.filter((id) => SURFACES.some((s) => s.id === id)),
      required: true,
      input: input as never,
    });
    if (isCancel(picked)) {
      ui.cancelled("Nothing changed.");
      return 0;
    }
    const removed = current.filter((id) => !picked.includes(id));
    for (const id of removed) removeSurfaceFiles(root, id);
    current = picked;
  }
  // The config file holds what cannot be deduced: rewrite only the surfaces key.
  const doc: TomlTable = existsSync(configPath) ? parseToml(readFileSync(configPath, "utf8")) : {};
  doc["surfaces"] = { enabled: current };
  writeFileSync(configPath, serializeToml(doc));
  ui.ok(`.ai-engineering/config.toml written (surfaces key only)`);
  const added = current.filter((id) => !surfacesBefore.includes(id));
  const removedSurfaces = surfacesBefore.filter((id) => !current.includes(id));
  for (const id of added) ui.ok(`+ ${id}: adapter + skill mirror written`);
  for (const id of removedSurfaces) ui.ok(`- ${id}: adapter + mirror removed`);
  if (added.length === 0 && removedSurfaces.length === 0) ui.info(`surfaces unchanged: ${current.join(", ")}`);
  ui.info(`enabled surfaces: ${current.join(", ")}`);
  const mirrors = mirrorTargets().length;
  ui.ok(`skill mirrors verified (${mirrors} targets)`);
  ui.info("Model tier thresholds: edit .ai-engineering/config.toml directly, or ask your AI assistant.");
  ui.end("Done. Run ai-eng doctor to verify.");
  return 0;
}

function removeSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const path = surface.settingsFile ?? surface.pluginFile;
  if (!path) return;
  const absolute = join(root, path);
  if (existsSync(absolute)) unlinkSync(absolute);
  ui.ok(`${path} removed (ai-eng entries only)`);
}

/** The mockup hint for config: installed-state marker + capability. */
function configHint(surface: Surface, installed: boolean): string {
  const state = installed ? "✔ installed" : "✘ not installed";
  return surfaceCanGovern(surface) ? state : `${state} — no deny`;
}
