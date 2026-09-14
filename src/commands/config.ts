// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { groupMultiselect, isCancel } from "@clack/prompts";
import { repoRoot, enabledSurfaces, isGoverned } from "../env.ts";
import { SURFACES, mirrorTargets, surfaceCanGovern, repoCarrier, carrierFiles, type Surface } from "../surfaces/adapters.ts";
import { hasAdapter, surfaceOptions } from "./init-shared.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";
import { VERSION } from "../version.ts";

export async function configMain(flags: { add?: string; remove?: string }): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Configuration · ai-eng ${VERSION}`);
  const root = repoRoot();
  // The gate, not "there is a .git above us": `config --add` in a bare repo used to
  // die on writeFileSync with a raw ENOENT instead of telling the human to run init.
  if (root === null || !isGoverned(root)) {
    ui.fail("you are not in a governed repo — run ai-eng init first");
    ui.end("Nothing changed.");
    return 2;
  }
  const configPath = join(root, ".ai-engineering", "config.toml");
  // Governed means the declaration parsed, so enabledSurfaces() cannot be guessing here.
  const surfacesBefore = enabledSurfaces();
  let current = surfacesBefore;
  if (flags.add) {
    // Same rule as the picker: no adapter, no declaration.
    if (!hasAdapter(flags.add)) {
      ui.fail(`"${flags.add}" has no adapter in this release — nothing would enforce its guards.`);
      ui.end("Nothing changed.");
      return 2;
    }
    if (!current.includes(flags.add)) current = [...current, flags.add];
  } else if (flags.remove) {
    current = current.filter((id) => id !== flags.remove);
    removeSurfaceFiles(root, flags.remove);
  } else {
    const picked = await groupMultiselect({
      message: "Which agent surfaces is this project governed on? (ticked = installed)",
      options: Object.fromEntries(surfaceOptions().map((group) => [group.title, group.items.map((s) => ({ value: s.id, label: s.label, hint: configHint(s, current.includes(s.id)) }))])),
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
  // The config file holds what cannot be deduced: rewrite only the surfaces key,
  // in place — the comments and the [models]/[guards]/[gc] blocks the template
  // ships are the user's, and a re-serialize would delete them.
  const raw = existsSync(configPath) ? readFileSync(configPath, "utf8") : "";
  const list = `[${current.map((id) => `"${id}"`).join(", ")}]`;
  const next = /^enabled\s*=.*$/m.test(raw)
    ? raw.replace(/^enabled\s*=.*$/m, `enabled = ${list}`)
    : `${raw.trim() === "" ? "" : `${raw.trimEnd()}\n\n`}[surfaces]\nenabled = ${list}\n`;
  writeFileSync(configPath, next);
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
  const placement = repoCarrier(surface);
  const files = carrierFiles(id, "repo");
  if (!placement || !files) return;
  const absolute = join(root, placement.path);
  if (existsSync(absolute)) {
    unlinkSync(absolute);
    ui.ok(`${placement.path} removed (ai-eng entries only)`);
  }
  if (placement.chain) {
    const chainPath = join(root, placement.chain);
    if (existsSync(chainPath)) {
      unlinkSync(chainPath);
      ui.ok(`${placement.chain} removed (chain module)`);
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
