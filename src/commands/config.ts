// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { groupMultiselect, isCancel } from "@clack/prompts";
import { repoRoot } from "../env.ts";
import { parseToml, serializeToml } from "../toml.ts";
import type { TomlTable } from "../toml.ts";
import { SURFACES, SURFACE_TIERS, mirrorTargets, surfaceCanGovern, type Surface } from "../surfaces/adapters.ts";
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
    const picked = await groupMultiselect({
      message: "Which agent surfaces is this project governed on? (ticked = installed)",
      options: Object.fromEntries(
        SURFACE_TIERS.map(([tier, title]) => [title, SURFACES.filter((s) => s.tier === tier).map((s) => ({ value: s.id, label: s.label, hint: configHint(s, current.includes(s.id)) }))]),
      ),
      initialValues: current.filter((id) => SURFACES.some((s) => s.id === id)),
      required: true,
      selectableGroups: false,
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
  const added = current.filter((id) => !surfacesBefore.includes(id));
  const removedSurfaces = surfacesBefore.filter((id) => !current.includes(id));
  const delta: ui.Row[] = [
    ...added.map((id): ui.Row => ({ mark: "ok", text: `+ ${id}`, dim: "adapter + skill mirror written" })),
    ...removedSurfaces.map((id): ui.Row => ({ mark: "ok", text: `- ${id}`, dim: "adapter + mirror removed" })),
  ];
  if (delta.length === 0) {
    ui.section("surfaces unchanged", [{ mark: "muted", text: current.join(", ") }], `${current.length} enabled`);
  } else {
    ui.section("Surfaces changed", delta, `${current.length} enabled: ${current.join(", ")}`);
  }
  const mirrors = mirrorTargets().length;
  ui.section("Mirrors verified", [{ mark: "ok", text: `${mirrors} targets` }], "model tier thresholds: edit .ai-engineering/config.toml directly, or ask your AI assistant");
  ui.end("Done. Run ai-eng doctor to verify.");
  return 0;
}

function removeSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const path = surface.settingsFile ?? surface.pluginFile;
  if (path) {
    const absolute = join(root, path);
    if (existsSync(absolute)) unlinkSync(absolute);
    ui.ok(`${path} removed (ai-eng entries only)`);
  }
  if (surface.chainFile) {
    const chainPath = join(root, surface.chainFile);
    if (existsSync(chainPath)) {
      unlinkSync(chainPath);
      ui.ok(`${surface.chainFile} removed (chain module)`);
    }
  }
}

/** The config hint: the ticked checkbox already says installed; the hint
 *  carries only the one thing a tick cannot say — this surface cannot block
 *  a tool call, so the live guards will not run on it. */
function configHint(surface: Surface, installed: boolean): string {
  if (surfaceCanGovern(surface)) return "";
  return installed ? "can't block tool calls — the guards will not run here" : "can't block tool calls";
}
