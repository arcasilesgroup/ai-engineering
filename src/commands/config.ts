// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { PassThrough } from "node:stream";
import { install, stripSharedText } from "../install.ts";
import { join } from "node:path";
import { multiselect, isCancel } from "@clack/prompts";
import { canonicalSurfaceId, repoRoot, enabledSurfaces, isGoverned } from "../env.ts";
import { SURFACES, mirrorTargets, surfaceCanGovern, repoCarrier, machineCarrier, installMachineCarriers, type Surface } from "../surfaces/adapters.ts";
import { hasAdapter, planEntries, refuseLine, SURFACE_PICK_MESSAGE, surfaceOptions } from "./init-shared.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";
import { VERSION } from "../version.ts";

type ResolveResult =
  | { kind: "continue"; current: string[]; addedNow: string | null }
  | { kind: "exit"; code: number };

/** Resolve the new surface list by mutating branch. The two early exits — no adapter
 *  on `--add`, and a cancelled picker — are folded into the result so the caller can
 *  return their exit code without duplicating the message or the side-effect order. */
async function resolveSurfaces(
  input: NodeJS.ReadStream | PassThrough,
  flags: { add?: string; remove?: string },
  root: string,
  surfacesBefore: string[],
): Promise<ResolveResult> {
  let addedNow: string | null = null;
  let current = surfacesBefore;
  if (flags.add) {
    flags.add = canonicalSurfaceId(flags.add);
    // Same rule as the picker: no adapter, no declaration.
    if (!hasAdapter(flags.add)) {
      ui.fail(`"${flags.add}" has no adapter in this release — nothing would enforce its guards.`);
      ui.end("Nothing changed.");
      return { kind: "exit", code: 2 };
    }
    if (!current.includes(flags.add)) {
      current = [...current, flags.add];
      addedNow = flags.add;
    }
  } else if (flags.remove) {
    flags.remove = canonicalSurfaceId(flags.remove);
    current = current.filter((id) => id !== flags.remove);
    removeSurfaceFiles(root, flags.remove);
  } else {
    const picked = await pickSurfaces(input, current, root);
    if (picked === null) return { kind: "exit", code: 0 };
    current = picked;
  }
  return { kind: "continue", current, addedNow };
}

/** The interactive multiselect (no flags). Returns null when the user cancels
 *  (the cancellation message is printed here, exactly as before). */
async function pickSurfaces(
  input: NodeJS.ReadStream | PassThrough,
  current: string[],
  root: string,
): Promise<string[] | null> {
  const picked = await multiselect({
    message: SURFACE_PICK_MESSAGE,
    options: surfaceOptions().map((s) => ({ value: s.id, label: s.label, hint: configHint(s, current.includes(s.id)) })),
    initialValues: current.filter((id) => SURFACES.some((s) => s.id === id)),
    required: true,
    input: input as never,
  });
  if (isCancel(picked)) {
    ui.cancelled("Nothing changed.");
    return null;
  }
  const removed = current.filter((id) => !picked.includes(id));
  for (const id of removed) removeSurfaceFiles(root, id);
  return picked;
}

/** The "Surfaces changed" rows: one per added surface, one per removed surface. */
function deltaRows(added: string[], removedSurfaces: string[]): ui.Row[] {
  return [
    ...added.map((id): ui.Row => ({ mark: "ok", text: `+ ${id}`, dim: "adapter + skill mirror written" })),
    ...removedSurfaces.map((id): ui.Row => ({ mark: "ok", text: `- ${id}`, dim: "off in this repo; the machine carrier stays — it serves every governed repo" })),
  ];
}

function writeConfigSurfaces(configPath: string, surfaces: string[]): void {
  // The config file holds what cannot be deduced: rewrite only the surfaces key,
  // in place — the comments and the [models]/[guards]/[gc] blocks the template
  // ships are the user's, and a re-serialize would delete them.
  const raw = existsSync(configPath) ? readFileSync(configPath, "utf8") : "";
  const list = `[${surfaces.map((id) => `"${id}"`).join(", ")}]`;
  writeFileSync(configPath, withSurfacesEnabled(raw, list));
}

function installNewSurfaces(root: string, current: string[], before: string[], addedNow: string | null): void {
  // Declaring a surface and leaving it without a carrier is a governed repo that is not
  // governed on that host. The carriers are written right here, by the same code init uses.
  for (const id of current) {
    if (!before.includes(id) || id === addedNow) installSurfaceFiles(root, id);
  }
}

function showSurfaceDelta(current: string[], before: string[]): void {
  const added = current.filter((id) => !before.includes(id));
  const removed = before.filter((id) => !current.includes(id));
  const delta = deltaRows(added, removed);
  if (delta.length === 0) {
    ui.section("surfaces unchanged", [{ mark: "muted", text: current.join(", ") }], `${current.length} enabled`);
  } else {
    ui.section("Surfaces changed", delta, `${current.length} enabled: ${current.join(", ")}`);
  }
}

export async function configMain(flags: { add?: string; remove?: string }): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Configuration · ai-eng ${VERSION}`);
  const root = repoRoot();
  // The gate, not "there is a .git above us": `config --add` in a bare repo would die
  // on writeFileSync with a raw ENOENT instead of telling the human to run init.
  if (root === null || !isGoverned(root)) {
    ui.fail("you are not in a governed repo — run ai-eng init first");
    ui.end("Nothing changed.");
    return 2;
  }
  // Governed means the declaration parsed, so enabledSurfaces() cannot be guessing here.
  const surfacesBefore = enabledSurfaces();
  const resolved = await resolveSurfaces(input, flags, root, surfacesBefore);
  if (resolved.kind === "exit") return resolved.code;
  const { current, addedNow } = resolved;
  writeConfigSurfaces(join(root, ".ai-engineering", "config.toml"), current);
  installNewSurfaces(root, current, surfacesBefore, addedNow);
  showSurfaceDelta(current, surfacesBefore);
  const mirrors = mirrorTargets().length;
  ui.section("Mirrors verified", [{ mark: "ok", text: `${mirrors} targets` }], "model tier thresholds: edit .ai-engineering/config.toml directly, or ask your AI assistant");
  ui.end("Done. Run ai-eng doctor to verify.");
  return 0;
}

function removeSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const placement = repoCarrier(surface);
  if (!placement) return;
  const absolute = join(root, placement.path);
  if (existsSync(absolute)) {
    if (placement.kind === "module") {
      unlinkSync(absolute);
      ui.ok(`${placement.path} removed`);
    } else {
      // A settings carrier is a file the user also owns: ours come out by marker, exactly
      // as uninstall does it. A bare unlink here deleted their hooks and told them only
      // our entries were removed — the two verbs disagreeing about one file.
      const stripped = stripSharedText(readFileSync(absolute, "utf8"));
      if (stripped === null) {
        ui.warn(`${placement.path} left alone — not JSON this installer can rewrite without reformatting it`);
      } else if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
        unlinkSync(absolute);
        ui.ok(`${placement.path} removed (it held only ai-eng entries)`);
      } else {
        writeFileSync(absolute, stripped);
        ui.ok(`${placement.path}: ai-eng entries removed, yours kept`);
      }
    }
  }
  if (placement.chain) {
    const chainPath = join(root, placement.chain);
    if (existsSync(chainPath)) {
      unlinkSync(chainPath);
      ui.ok(`${placement.chain} removed (chain module)`);
    }
  }
}

/** Rewrite the surfaces key in place, and never grow a second `[surfaces]` table.
 *
 *  Two shapes would do exactly that, at exit 0: an `enabled` key indented under an
 *  existing table (valid TOML a blind `/^enabled\s*=/m` misses) and a `[surfaces]`
 *  table that has no `enabled` key yet. Each appends a fresh header, which makes the
 *  file unparseable — `declaration()` then reports the repository as undeclared and the
 *  command that manages governance silently turns it off. That is the one class of bug
 *  this product exists to prevent (§09.2), so the rewrite is table-aware: the key is
 *  scoped to `[surfaces]` (a bare `enabled =` also matched the `[notices]` key of the
 *  same name), and a file with no table gets one, at the end. */
function withSurfacesEnabled(raw: string, list: string): string {
  const lines = raw.split("\n");
  const header = lines.findIndex((line) => /^\s*\[surfaces\]\s*$/.test(line));
  if (header >= 0) {
    for (let i = header + 1; i < lines.length; i += 1) {
      const line = lines[i] ?? "";
      if (/^\s*\[/.test(line)) break; // the next table: `enabled` belongs to it, not to us
      if (/^\s*enabled\s*=/.test(line)) {
        lines[i] = `enabled = ${list}`;
        return lines.join("\n");
      }
    }
    lines.splice(header + 1, 0, `enabled = ${list}`);
    return lines.join("\n");
  }
  const body = raw.trim() === "" ? "" : `${raw.trimEnd()}\n\n`;
  return `${body}[surfaces]\nenabled = ${list}\n`;
}

/** Write the carriers a surface needs, wherever it reads them. A `config --add` that
 *  only declared the surface would leave config.toml claiming governance while the host
 *  had no hook at all — with the summary still saying the adapter was written. */
function installSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const machine = machineCarrier(surface);
  if (machine !== null) {
    const report = installMachineCarriers([id]);
    for (const path of report.written) ui.ok(`${path} written (machine carrier)`);
    for (const refused of report.refused) ui.warn(refuseLine(refused));
    if (report.written.length === 0 && report.refused.length === 0 && report.untouched.length > 0) ui.info(`${machine.path} was already current`);
  }
  const repo = repoCarrier(surface);
  if (repo !== null) {
    const report = install(root, planEntries([id]).filter((entry) => entry.path === repo.path || entry.path === repo.chain));
    for (const path of report.written) ui.ok(`${path} written (repo carrier)`);
    for (const refused of report.refused) ui.warn(refuseLine(refused));
  }
}

/** The config hint: the ticked checkbox already says installed; the hint
 *  carries only the one thing a tick cannot say — this surface cannot block
 *  a tool call, so the live guards will not run on it. */
function configHint(surface: Surface, installed: boolean): string {
  if (surfaceCanGovern(surface)) return "";
  return installed ? "can't block tool calls — the guards will not run here" : "can't block tool calls";
}
