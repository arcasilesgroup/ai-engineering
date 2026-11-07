// src/surfaces/adapters.ts — generators per surface: JSON-stdio (Claude/Cursor/Codex/Copilot)
// or TS module (OpenCode/OMP). Surface = ~150 LOC of adapter + its proof (§13).

import surfacesJson from "./surfaces.json";
import { randomBytes } from "node:crypto";
import { closeSync, constants, existsSync, fstatSync, ftruncateSync, linkSync, lstatSync, mkdirSync, openSync, readFileSync, readlinkSync, readdirSync, realpathSync, renameSync, rmdirSync, statSync, symlinkSync, unlinkSync, writeFileSync, type Stats } from "node:fs";
import { hostname } from "node:os";
import { basename, join, dirname, relative, resolve, sep, isAbsolute } from "node:path";
import { home, versionFile, machineBase } from "../env.ts";
import { mergeSharedText, stripSharedText, sha256 } from "../install.ts";
import { VERSION } from "../version.ts";
import {
  materializeSkills, materializeAgents, materializeScripts, embeddedTemplate, embeddedChainBundle, removeStaleCanonFiles,
  recordCanonOwnership, unprovenCanonText, isVersionCacheRecord, safeProjectPath, readProjectFileSnapshot, unlinkProjectPath, writeProjectFile,
  refusedStaleCanonText, refusedChangeText, isFilesystemRefusal,
} from "../embed.ts";
import type { Dialect } from "../chain/dialect.ts";

export type Surface = {
  readonly id: string;
  readonly label: string;
  readonly tier: "core" | "experimental" | "best-effort" | "skills-only";
  /** The host's denial vocabulary in the chain (chain/dialect.ts). Absent for the
   *  hosts that run the chain in-process — their template turns the outcome into
   *  throw/block itself. */
  readonly dialect?: Dialect;
  readonly can: {
    /** `true` we deny · `"throw"` we deny by throwing (in-process hosts) · `"host-only"`
     *  the HOST can deny through its own permissions and we have no hook to run in — the
     *  two are different facts, and collapsing them made the picker print "can't block
     *  tool calls" about a host that can. */
    readonly deny: boolean | "throw" | "host-only";
    readonly rewriteOut: boolean | "total-replacement";
    /** The native goal loop (§20.3) — "unverified" means plausible but never
     *  measured with a receipt, "none" that the human loop is the honest mode
     *  there (Pi: extensions only; Zed: skills-only). Nothing is "native" until
     *  a receipt says so, and the field never guesses upward. */
    readonly loop: "native" | "unverified" | "none";
    /** The measurement behind `loop` — the installed version and the flag that
     *  grants it. A claim about a surface carries its evidence or it is a guess:
     *  the registry test refuses `native` and `none` without one (§20.3). */
    readonly loopEvidence?: string;
  };
  readonly carriers: readonly Carrier[];
  readonly note?: string;
};

/** Where a host READS its carrier, and the evidence for it. A path claimed from memory
 *  is the failure this table exists to end: ai-engineering wrote the OMP carrier into
 *  `.agents/hooks/`, which OMP never reads, and doctor called it green (§13.2). Every
 *  path here carries its source and the date it was read, so a stale claim is a delta
 *  against a recorded measurement instead of against somebody's memory. */
export type Carrier = {
  /** `machine` = the user's home, written once per machine; `repo` = inside the
   *  governed repo, for the readers that only exist there. */
  readonly scope: "repo" | "machine";
  /** `settings` files may already belong to the user and are MERGED into by marker;
   *  `module` files are ours whole. */
  readonly kind: "settings" | "module";
  /** Home-relative when scope is machine, repo-relative when repo. Never absolute:
   *  a machine path in a versioned file is a leak. */
  readonly path: string;
  /** The chain bundle that must sit beside an in-process carrier. */
  readonly chain?: string;
  /** The environment variable this host resolves its agent directory from (omp and pi:
   *  PI_CODING_AGENT_DIR). A relocatable agent dir is not a detail — the carrier has to
   *  land where the host will look, or it is the `.agents/hooks/` bug again. */
  readonly agentDirEnv?: string;
  readonly source: string;
  readonly measured: string;
};

export const SURFACES: Surface[] = (surfacesJson as { surfaces: Surface[] }).surfaces;

/** The carrier this surface keeps in the repo (Cursor and Copilot, whose cloud readers
 *  only see the checkout). Null for everything else. */
export function repoCarrier(surface: Surface): Carrier | null {
  return surface.carriers.find((carrier) => carrier.scope === "repo") ?? null;
}

/** The carrier this surface keeps on the machine. Null for a host that only reads repo
 *  files. */
export function machineCarrier(surface: Surface): Carrier | null {
  return surface.carriers.find((carrier) => carrier.scope === "machine") ?? null;
}

/** Where a carrier's path is rooted: the machine base, unless this host resolves its
 *  agent directory from an environment variable that IS set — then that, because that is
 *  where the host will look. Installing a carrier the host never reads is the bug this
 *  whole table exists to end, and a relocatable agent dir is the same bug wearing a hat. */
export function carrierBase(placement: Carrier): string {
  if (placement.scope === "machine" && placement.agentDirEnv !== undefined) {
    const override = process.env[placement.agentDirEnv];
    if (override !== undefined && override.length > 0) return override;
  }
  return machineBase();
}

/** The absolute path of a carrier file (the entry, or its chain bundle). One function for
 *  the installer, the remover and doctor: two resolutions of the same path is how a
 *  carrier gets written somewhere and checked somewhere else. */
export function carrierPath(placement: Carrier, relative?: string): string {
  const rel = relative ?? placement.path;
  const base = carrierBase(placement);
  if (base === machineBase()) return join(base, rel);
  // The host's agent dir already IS the `.omp/agent` (or `.pi/agent`) the path names.
  return join(base, rel.replace(/^\.(omp|pi)\/agent\//, ""));
}

/** surface id → the entry template and whether the host needs the chain bundle
 *  beside it. Copilot fails CLOSED on a missing binary, in both scopes, so its one
 *  template guards the call per shell (`bash` and `powershell`). Null for a surface
 *  with no generator (§13: no adapter, no offer). */
const CARRIER_TEMPLATES: Record<string, { main: string; chain: boolean }> = {
  "claude-code": { main: "settings.claude.json.tpl", chain: false },
  "oh-my-pi": { main: "plugin.omp.ts.tpl", chain: true },
  opencode: { main: "plugin.opencode.ts.tpl", chain: true },
  pi: { main: "plugin.pi.ts.tpl", chain: true },
  codex: { main: "settings.codex.json.tpl", chain: false },
  cursor: { main: "settings.cursor.json.tpl", chain: false },
  copilot: { main: "settings.copilot.json.tpl", chain: false },
};

/** The launcher name a hook line must call on this machine. On Windows a bare `ai-eng`
 *  resolves, in PowerShell, to npm's `ai-eng.ps1` — and the Restricted execution policy a
 *  fresh Windows laptop ships with refuses to load it, so every hook errors and the
 *  fail-closed hosts deny every tool call. The `.exe` (bun) or `.cmd` (npm) shim beside it
 *  runs under any policy, in PowerShell, cmd and Git Bash alike. First hit in PATH order,
 *  the way the shell will resolve it; `.cmd` when nothing is on PATH yet (npm's shim). */
export function hookLauncher(platform: NodeJS.Platform = process.platform, path: string = process.env["PATH"] ?? process.env["Path"] ?? ""): string {
  if (platform !== "win32") return "ai-eng";
  for (const dir of path.split(";").filter(Boolean)) {
    for (const name of ["ai-eng.exe", "ai-eng.cmd"]) if (existsSync(join(dir, name))) return name;
  }
  return "ai-eng.cmd";
}

/** A settings template with its hook lines calling `launcher`. Only the call is renamed:
 *  the `command -v ai-eng` / `Get-Command ai-eng` probes look for any form of it. */
export function withLauncher(template: string, launcher: string = hookLauncher()): string {
  return launcher === "ai-eng" ? template : template.replaceAll("ai-eng chain ", `${launcher} chain `);
}

export function carrierFiles(id: string, scope: Carrier["scope"] = "machine"): { main: string; chain: string | null } | null {
  // The surface id is copilot-cli; the template row kept the short name.
  const row = CARRIER_TEMPLATES[id] ?? (id === "copilot-cli" ? CARRIER_TEMPLATES["copilot"] : undefined);
  if (!row) return null;
  const template = embeddedTemplate(row.main);
  // Only this machine's own files name this machine's launcher. A repo file is committed
  // and read on every teammate's OS: `ai-eng.cmd` there is "command not found" on a Mac.
  // Module carriers run the chain in-process: there is no hook line to rename.
  const main = scope === "machine" && row.main.endsWith(".json.tpl") ? withLauncher(template) : template;
  return { main, chain: row.chain ? embeddedChainBundle() : null };
}

/** What the chain must write when this surface denies. Default: claude. */
export function surfaceDialect(id: string | undefined): Dialect {
  return SURFACES.find((s) => s.id === id)?.dialect ?? "claude";
}

/** init aborts if the chosen surface cannot carry a required guard: better not to
 *  promise than to promise falsely (§13). */
export function surfaceCanGovern(surface: Surface): boolean {
  // Only the hosts that RUN us can be governed: a host that denies on its own, without
  // calling our chain, has nowhere for a guard to stand.
  return surface.can.deny === true || surface.can.deny === "throw";
}

/** The tier headers for the grouped surface multiselect (init + config share
 *  them): the group carries the capability class, the option hint the delta. */
/** The picker's group headers. Each one states what holds for EVERY row under it — the
 *  per-row degradation belongs to the row, from the measured fields beside it. research/003
 *  puts the rule: "the label is the promise; the fields are the measurement. They are
 *  allowed to disagree — but not silently". */
export const SURFACE_TIERS: ReadonlyArray<readonly [string, string]> = [
  ["core", "core — deny + rewrite"],
  ["experimental", "experimental — deny yes; the row names what degrades"],
  ["best-effort", "best-effort — deny yes; what survives is the host's deployment"],
  ["skills-only", "skills only — no guards in hot-path"],
];

type MirrorTarget = { dir: string; label: string };

/** Re-exported for the callers that already know the surfaces layer: the definition is
 *  in env.ts, where the guards can reach it without dragging the templates in. */

/** Where each surface discovers skills (§08): one canon, three mirrors beside the
 *  canon. Without the override the base is the physical home and the paths are
 *  exactly §08's. */
export function mirrorTargets(): MirrorTarget[] {
  const base = machineBase();
  return [
    { dir: join(base, ".claude", "skills"), label: "~/.claude/skills" },
    { dir: join(base, ".agents", "skills"), label: "~/.agents/skills" },
    { dir: join(base, ".config", "opencode", "skill"), label: "~/.config/opencode/skill" },
  ];
}

/** Install the global canon once per machine, then symlink the mirrors (junction or
 *  verified copy on Windows — symlinks where the OS supports them).
 *
 *  The carriers are NOT here: they follow the declared surfaces, not the canon, and
 *  `installMachineCarriers()` owns them (§13.2). */
export function installCanon(version: string, preserveSkills: readonly string[] = []): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  // The command bodies the previous install rendered, read before this one rewrites the canon:
  // a shim still holding one of them is ours to refresh.
  const earlierCommands = renderCommands(canonDir);
  lines.push(...warningsOf(materializeSkills(canonDir, preserveSkills)));
  const swept = removeStaleCanonFiles(home());
  if (swept.removed.length > 0) lines.push(`✓ swept ${swept.removed.length} file(s) this binary no longer ships: ${swept.removed.join(", ")}`);
  if (swept.refused.length > 0) lines.push(`⚠ ${refusedStaleCanonText(swept.refused)}`);
  if (swept.kept.length > 0) lines.push(`✓ kept ${swept.kept.length} user file(s) — not shipped by this binary and not provably written by ai-eng, so never deleted: ${swept.kept.join(", ")}`);
  if (swept.unproven.length > 0) lines.push(`⚠ ${unprovenCanonText(swept.unproven)}`);
  const recordRefusal = recordCanonOwnership(home(), swept.unproven, swept.refused);
  if (recordRefusal !== null) lines.push(`⚠ ${recordRefusal}`);
  lines.push(...refusalAsLines(canonDir, () => {
    const entries = readdirSync(canonDir, { withFileTypes: true }).filter((e) => e.isDirectory() && !e.name.startsWith("."));
    return [`✓ ${home()}/skills/ — ${entries.length} skills installed`];
  }));
  // Seeds the 24h notice cache (§14.0). Health never reads this file: init and
  // doctor byte-compare the canon against the payload (canonDrift) — this same
  // path also carries the REGISTRY version after a notice check.
  lines.push(...refusalAsLines(versionFile(), () => writeVersionCache(version)));
  for (const target of mirrorTargets()) {
    lines.push(...refusalAsLines(target.dir, () => {
      mkdirSync(target.dir, { recursive: true });
      const mirrored = linkSkills(canonDir, target.dir);
      const kept = mirrored.kept.length === 0 ? [] : [`⚠ ${target.label}: ${mirrored.kept.length} link(s) of yours under a skill's name point elsewhere — kept, never repointed: ${mirrored.kept.join(", ")}`];
      return [`✓ Symlink → ${target.label} (${mirrored.count} skills)`, ...kept];
    }));
  }
  lines.push(...installCommands(canonDir, earlierCommands));
  lines.push(...refusalAsLines(join(machineBase(), ".claude", "agents"), installAgentsCanon));
  const scriptLines = materializeScripts(join(home(), "scripts"));
  if (scriptLines.some((line) => line.startsWith("materialized "))) lines.push(`✓ ~/.ai-engineering/scripts/ — checkpoint gate`);
  lines.push(...warningsOf(scriptLines));
  return lines;
}

/** version.json is created, or refreshed only while it is a single-named regular file holding
 *  the `{ version, ts }` record ai-eng writes; a link or anything else there is kept. */
function writeVersionCache(version: string): string[] {
  const path = versionFile();
  const record = JSON.stringify({ version, ts: Date.now() });
  const done = ["✓ ~/.ai-engineering/version.json — version + 24h cache"];
  if (!pathEntryExists(path)) {
    writeFileSync(path, record, { flag: "wx" });
    return done;
  }
  const directory = dirname(path);
  const absolute = safeProjectPath(directory, basename(path));
  const snapshot = absolute === null ? null : readProjectFileSnapshot(directory, absolute);
  if (absolute === null || snapshot === null || !isVersionCacheRecord(snapshot.content.toString("utf8"))) {
    return [`⚠ ${path} is a link, not a regular file, or not ai-eng's version cache — left as it is; the 24h notice cache was not refreshed`];
  }
  if (writeProjectFile(directory, absolute, snapshot, record)) return done;
  return [`⚠ ${path} — changed meanwhile, shared with another name, or the filesystem refused; left as it is, the 24h notice cache was not refreshed`];
}

function warningsOf(lines: readonly string[]): string[] {
  return lines.filter((line) => line.startsWith("⚠ "));
}

/** One install step whose filesystem refusal becomes a warning naming the path, so the rest
 *  of the install, and the lock the calling command writes after it, still happen. */
function refusalAsLines(path: string, step: () => string[]): string[] {
  try {
    return step();
  } catch (error) {
    if (!isFilesystemRefusal(error)) throw error;
    return [`⚠ ${refusedChangeText(error.path ?? path, error)}`];
  }
}

/** Materialize ~/.ai-engineering/agents and mirror it at ~/.claude/agents (symlink, or copy).
 *  The mirror is ours only as the exact link this installer writes (`<home>/agents`, the F10
 *  rule) or, in a real folder, as files holding ai-eng's bytes; a link or a file of the user's
 *  is kept and named, never repointed or overwritten.
 *  Exported so tests can drive the mirror under AI_ENG_HOME without writing the real home. */
export function installAgentsCanon(): string[] {
  const agentsCanon = join(home(), "agents");
  // The bytes the previous install wrote, read before this one replaces them: a mirror copy
  // still equal to them is ours to refresh.
  const earlier = readAgentFiles(agentsCanon);
  const materialized = warningsOf(materializeAgents(agentsCanon));
  const agentFiles = readdirSync(agentsCanon).filter((name) => name.endsWith(".md"));
  const lines = [`✓ ~/.ai-engineering/agents/ — ${agentFiles.length} agents installed`, ...materialized];
  const agentsMirror = join(machineBase(), ".claude", "agents");
  mkdirSync(dirname(agentsMirror), { recursive: true });
  let mirror: Stats | null = null;
  try {
    mirror = lstatSync(agentsMirror);
  } catch (error) {
    if (!isFilesystemRefusal(error) || error.code !== "ENOENT") throw error;
  }
  if (mirror?.isSymbolicLink() === true) {
    const target = readlinkSync(agentsMirror);
    if (resolve(dirname(agentsMirror), target) === resolve(agentsCanon)) return [...lines, "✓ Symlink → ~/.claude/agents"];
    return [...lines, `⚠ ~/.claude/agents is a link of yours (→ ${target}), not ai-eng's — left as it is; ai-eng's agents are not mirrored there`];
  }
  if (mirror !== null && !mirror.isDirectory()) {
    return [...lines, "⚠ ~/.claude/agents is a file, not a folder — left as it is; ai-eng's agents are not mirrored there"];
  }
  if (mirror === null) {
    try {
      symlinkSync(agentsCanon, agentsMirror, "dir");
      return [...lines, "✓ Symlink → ~/.claude/agents"];
    } catch {
      mkdirSync(agentsMirror, { recursive: true });
    }
  }
  return [...lines, ...copyAgentsInto(agentsMirror, agentsCanon, agentFiles, earlier)];
}

/** The regular agent files in a folder, by name; links and anything unreadable are skipped. */
function readAgentFiles(directory: string): Map<string, Buffer> {
  const files = new Map<string, Buffer>();
  let names: string[];
  try {
    names = readdirSync(directory).filter((name) => name.endsWith(".md"));
  } catch {
    return files;
  }
  for (const name of names) {
    const absolute = safeProjectPath(directory, name);
    const snapshot = absolute === null ? null : readProjectFileSnapshot(directory, absolute);
    if (snapshot !== null) files.set(name, snapshot.content);
  }
  return files;
}

/** Copy the agents into a real mirror folder: a missing file is created, a file still holding
 *  this or the previous install's bytes is refreshed, anything else is the user's and stays. */
function copyAgentsInto(mirror: string, canon: string, names: readonly string[], earlier: ReadonlyMap<string, Buffer>): string[] {
  const kept: string[] = [];
  const refused: string[] = [];
  for (const name of names) {
    const outcome = copyAgentFile(mirror, name, readFileSync(join(canon, name)), earlier.get(name));
    if (outcome === "kept") kept.push(name);
    if (outcome === "refused") refused.push(join(mirror, name));
  }
  const lines = ["✓ Copy → ~/.claude/agents (copy)"];
  if (kept.length > 0) lines.push(`⚠ ${kept.length} file(s) in ~/.claude/agents are yours (they differ from ai-eng's agent of the same name) — kept: ${kept.join(", ")}. Delete or rename one to receive ai-eng's version`);
  if (refused.length > 0) lines.push(`⚠ ${refused.length} agent file(s) not written — changed meanwhile, or the filesystem refused; left as they are: ${refused.join(", ")}`);
  return lines;
}

function copyAgentFile(mirror: string, name: string, ours: Buffer, earlier: Buffer | undefined): "written" | "current" | "kept" | "refused" {
  if (!pathEntryExists(join(mirror, name))) {
    try {
      // wx: never through a link or over a file that appeared since the check.
      writeFileSync(join(mirror, name), ours, { flag: "wx" });
      return "written";
    } catch (error) {
      if (!isFilesystemRefusal(error)) throw error;
      return "refused";
    }
  }
  const absolute = safeProjectPath(mirror, name);
  const snapshot = absolute === null ? null : readProjectFileSnapshot(mirror, absolute);
  if (absolute === null || snapshot === null) return "kept";
  if (snapshot.content.equals(ours)) return "current";
  if (earlier === undefined || !snapshot.content.equals(earlier)) return "kept";
  return writeProjectFile(mirror, absolute, snapshot, ours.toString("utf8")) ? "written" : "refused";
}

/** The pre-2.2.0 repo paths of the carriers that now live on the machine, keyed to the
 *  surface that owned them. The refresh sweeps these so an old install does not keep
 *  ghost carriers — a hook file nobody reads is the exact bug 2.2.0 exists to end. This
 *  map is history, not a second source of truth: nothing current is computed from it. */
const MOVED_REPO_CARRIERS: Record<string, string> = {
  ".claude/settings.json": "claude-code",
  ".opencode/plugins/ai-eng.ts": "opencode",
  ".opencode/plugins/ai-eng-chain.ts": "opencode",
  ".agents/hooks/ai-eng.ts": "oh-my-pi",
  ".agents/hooks/ai-eng-chain.ts": "oh-my-pi",
  ".codex/hooks.json": "codex",
  ".pi/extensions/ai-eng.ts": "pi",
  ".pi/extensions/ai-eng-chain.ts": "pi",
};

/** Take the moved-out carriers out of a repo that still has them, and say what went. An
 *  edited file is kept and named — the same rule as uninstall: ours goes only when the
 *  bytes are still ours. A linked path is kept too: rewriting through it would change the
 *  file it points at, which can be the user's own settings in their home. A carrier still
 *  ours whose delete or rewrite failed is `refused`: ours, not the user's, and swept by the
 *  next update. */
export function sweepMovedRepoCarriers(root: string): { removed: string[]; kept: string[]; refused: string[] } {
  const removed: string[] = [];
  const kept: string[] = [];
  const refused: string[] = [];
  for (const [rel, owner] of Object.entries(MOVED_REPO_CARRIERS)) {
    const outcome = sweepMovedRepoCarrier(root, rel, owner);
    if (outcome === "removed") removed.push(rel);
    if (outcome === "kept") kept.push(rel);
    if (outcome === "refused") refused.push(rel);
  }
  return { removed, kept, refused };
}

function sweepMovedRepoCarrier(root: string, rel: string, owner: string): "removed" | "kept" | "refused" | "absent" {
  if (!pathEntryExists(join(root, rel))) return "absent";
  const absolute = safeProjectPath(root, rel);
  const snapshot = absolute === null ? null : readProjectFileSnapshot(root, absolute);
  if (absolute === null || snapshot === null) return "kept";
  if (!rel.endsWith(".json")) {
    // A module is ours whole only while it is byte for byte a carrier this binary ships.
    const isShipped = shippedCarrierModules(owner).some((shipped) => snapshot.content.equals(Buffer.from(shipped)));
    if (!isShipped) return "kept";
    return unlinkProjectPath(root, absolute, snapshot) ? "removed" : "refused";
  }
  // A settings file we merged into is stripped, not deleted: the user's own keys are in it.
  // One that never held an entry of ours is the repo's own (Claude Code project settings):
  // nothing to sweep and nothing to say.
  const current = snapshot.content.toString("utf8");
  if (!holdsAiEngEntries(current)) return "absent";
  const stripped = stripSharedText(current);
  if (stripped === null) return "kept";
  let isOnlyOurs: boolean;
  try {
    isOnlyOurs = Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0;
  } catch {
    return "kept";
  }
  if (isOnlyOurs) return unlinkProjectPath(root, absolute, snapshot) ? "removed" : "refused";
  // A second name (a hard link from the user's home) would receive the rewrite: not ours to change.
  if (snapshot.nlink !== 1) return "kept";
  return writeProjectFile(root, absolute, snapshot, stripped) ? "removed" : "refused";
}

/** Whether a JSON settings text carries anything the strip would take out. Judged on a
 *  2-space rendering so a layout this installer cannot rewrite (a compact one-liner, tabs)
 *  is still read; text that is not JSON cannot be judged and counts as holding ours. */
function holdsAiEngEntries(current: string): boolean {
  let parsed: unknown;
  try {
    parsed = JSON.parse(current);
  } catch {
    return true;
  }
  const rendered = `${JSON.stringify(parsed, null, 2)}\n`;
  return stripSharedText(rendered) !== rendered;
}

function shippedCarrierModules(owner: string): string[] {
  const files = carrierFiles(owner);
  if (files === null) return [];
  return files.chain === null ? [files.main] : [files.main, files.chain];
}

/** Whether anything — a file, a directory, a dangling link — has this name. A path that
 *  cannot be inspected counts as present, so it is judged instead of treated as absent. */
function pathEntryExists(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (error) {
    return !(missingPath(error) || (typeof error === "object" && error !== null && "code" in error && error.code === "ENOTDIR"));
  }
}

export type MachineReport = { written: string[]; untouched: string[]; refused: Array<{ path: string; reason: string }> };
const SETTINGS_MUTATION_REFUSED = "identity-bound-settings-mutation-unavailable";
const SETTINGS_UNREADABLE = "settings-unreadable";
const CARRIER_UNWRITABLE = "carrier-path-unwritable";
const CARRIER_EDITED = "carrier-edited";
const REMOVAL_REFUSED = "removal-refused";

/** What the machine side remembers: which version wrote each surface's carrier, keyed by
 *  surface id, and the sha256 of the definition it wrote. Two questions depend on it and
 *  neither can be answered from the files themselves:
 *   - a DOWNGRADE. The carrier is the new binary's; the chain it calls would be the old
 *     one, which has no gate, and the policy would fall back onto repos that never asked
 *     (F7). Doctor needs to know the binary is older than the record.
 *   - Codex's trust. Its approval is a hash of the hook DEFINITION, and a definition that
 *     changed re-asks in /hooks. Comparing the shipped bytes against what was recorded is
 *     the only way to know the change happened. */
export type MachineState = {
  version: string;
  carriers: Record<string, string>;
  /** Legacy state retained so uninstall can restore settings written by older versions. */
  templateDir?: { previous: string | null; ours: string | null };
};

export function machineStateFile(): string {
  return join(home(), "machine.json");
}

export function readMachineState(): MachineState {
  try {
    return parseMachineState(readFileSync(machineStateFile(), "utf8"));
  } catch {
    return { version: "", carriers: {} };
  }
}

function parseMachineState(text: string): MachineState {
  try {
    const doc = JSON.parse(text) as Partial<MachineState>;
    const carriers: Record<string, string> = {};
    if (doc.carriers !== null && typeof doc.carriers === "object") {
      for (const [id, hash] of Object.entries(doc.carriers as Record<string, unknown>)) if (typeof hash === "string") carriers[id] = hash;
    }
    const state: MachineState = { version: typeof doc.version === "string" ? doc.version : "", carriers };
    const templateDir = doc.templateDir;
    if (templateDir !== null && typeof templateDir === "object") {
      const record = templateDir as Record<string, unknown>;
      state.templateDir = {
        previous: typeof record["previous"] === "string" ? record["previous"] : null,
        ours: typeof record["ours"] === "string" ? record["ours"] : null,
      };
    }
    return state;
  } catch {
    return { version: "", carriers: {} };
  }
}

type MachineSettingsDirectory = {
  path: string;
  requestedPath: string;
  dev: number;
  ino: number;
  link: { dev: number; ino: number; target: string } | null;
};
type MachineSettingsFile = { stat: Stats; content: Buffer };
type MachineSettingsSnapshot = {
  sourceParent: MachineSettingsDirectory;
  sourceName: string;
  targetParent: MachineSettingsDirectory;
  targetName: string;
  targetPath: string | null;
  link: { stat: Stats; target: string } | null;
  file: MachineSettingsFile | null;
};

function missingPath(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
}

function machineSettingsDirectory(path: string): MachineSettingsDirectory {
  const requestedEntry = lstatSync(path);
  const canonicalPath = realpathSync(path);
  const stat = lstatSync(canonicalPath);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error("Machine settings parent is not a directory");
  return {
    path: canonicalPath,
    requestedPath: path,
    dev: stat.dev,
    ino: stat.ino,
    link: requestedEntry.isSymbolicLink()
      ? { dev: requestedEntry.dev, ino: requestedEntry.ino, target: readlinkSync(path) }
      : null,
  };
}

function withMachineSettingsDirectory<T>(directory: MachineSettingsDirectory, action: () => T): T | null {
  const previousDirectory = process.cwd();
  let changedDirectory = false;
  try {
    try {
      if (realpathSync(directory.requestedPath) !== directory.path) return null;
      if (directory.link !== null) {
        const requestedEntry = lstatSync(directory.requestedPath);
        if (
          !requestedEntry.isSymbolicLink()
          || requestedEntry.dev !== directory.link.dev
          || requestedEntry.ino !== directory.link.ino
          || readlinkSync(directory.requestedPath) !== directory.link.target
        ) {
          return null;
        }
      }
      process.chdir(directory.path);
      changedDirectory = true;
      const currentStat = lstatSync(".");
      if (
        realpathSync(".") !== directory.path
        || !currentStat.isDirectory()
        || currentStat.dev !== directory.dev
        || currentStat.ino !== directory.ino
      ) {
        return null;
      }
    } catch {
      return null;
    }
    return action();
  } finally {
    if (changedDirectory) process.chdir(previousDirectory);
  }
}

function sameMachineSettingsStat(left: Stats, right: Stats): boolean {
  return left.isFile() === right.isFile()
    && left.isSymbolicLink() === right.isSymbolicLink()
    && left.dev === right.dev
    && left.ino === right.ino
    && left.size === right.size
    && left.mtimeMs === right.mtimeMs
    && left.ctimeMs === right.ctimeMs
    && left.mode === right.mode;
}

function machineSettingsEntry(name: string): Stats | null {
  try {
    return lstatSync(name);
  } catch (error) {
    if (missingPath(error)) return null;
    throw error;
  }
}

function readMachineSettingsFile(name: string, expected?: Stats): MachineSettingsFile | null {
  let descriptor: number | null = null;
  let file: MachineSettingsFile | null = null;
  try {
    const entry = lstatSync(name);
    if (entry.isFile() && (!expected || sameMachineSettingsStat(entry, expected))) {
      descriptor = openSync(name, constants.O_RDONLY | constants.O_NOFOLLOW);
      const opened = fstatSync(descriptor);
      if (sameMachineSettingsStat(entry, opened)) {
        const content = readFileSync(descriptor);
        const afterRead = fstatSync(descriptor);
        if (
          sameMachineSettingsStat(opened, afterRead)
          && sameMachineSettingsStat(afterRead, lstatSync(name))
          && content.length === afterRead.size
        ) {
          file = { stat: afterRead, content };
        }
      }
    }
  } catch {
    file = null;
  }
  if (descriptor !== null) {
    try {
      closeSync(descriptor);
    } catch {
      return null;
    }
  }
  return file;
}

function sameMachineSettingsFile(left: MachineSettingsFile | null, right: MachineSettingsFile): boolean {
  return left !== null
    && sameMachineSettingsStat(left.stat, right.stat)
    && left.content.equals(right.content);
}

function snapshotMachineSettings(absolute: string): MachineSettingsSnapshot {
  let snapshot: MachineSettingsSnapshot | null = null;
  try {
    const sourceParent = machineSettingsDirectory(dirname(absolute));
    const sourceName = basename(absolute);
    const didSnapshot = withMachineSettingsDirectory(sourceParent, () => {
      const entry = machineSettingsEntry(sourceName);
      if (entry === null) {
        snapshot = {
          sourceParent, sourceName, targetParent: sourceParent, targetName: sourceName,
          targetPath: null, link: null, file: null,
        };
        return true;
      }
      if (entry.isSymbolicLink()) {
        const target = readlinkSync(sourceName);
        const targetPath = realpathSync(sourceName);
        const targetParent = machineSettingsDirectory(dirname(targetPath));
        const targetName = basename(targetPath);
        const file = withMachineSettingsDirectory(targetParent, () => readMachineSettingsFile(targetName));
        const currentEntry = machineSettingsEntry(sourceName);
        if (
          file === null
          || currentEntry === null
          || !sameMachineSettingsStat(entry, currentEntry)
          || readlinkSync(sourceName) !== target
          || realpathSync(sourceName) !== targetPath
        ) {
          return false;
        }
        snapshot = {
          sourceParent, sourceName, targetParent, targetName, targetPath,
          link: { stat: entry, target }, file,
        };
        return true;
      }
      if (!entry.isFile()) return false;
      const file = readMachineSettingsFile(sourceName, entry);
      if (file === null) return false;
      snapshot = {
        sourceParent, sourceName, targetParent: sourceParent, targetName: sourceName,
        targetPath: join(sourceParent.path, sourceName), link: null, file,
      };
      return true;
    });
    if (didSnapshot !== true || snapshot === null) throw new Error("the file, link, or target changed while being read");
    return snapshot;
  } catch (error) {
    throw new Error(`Unable to safely snapshot machine settings: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/** A settings path that cannot be read as one regular file — unreadable, a dangling link, a
 *  directory, or changing while read — is refused instead of aborting the whole command. */
function readableMachineSettings(absolute: string): MachineSettingsSnapshot | null {
  try {
    return snapshotMachineSettings(absolute);
  } catch {
    return null;
  }
}

function machineSettingsSnapshotMatches(snapshot: MachineSettingsSnapshot): boolean {
  try {
    const matches = withMachineSettingsDirectory(snapshot.sourceParent, () => {
      const entry = machineSettingsEntry(snapshot.sourceName);
      if (snapshot.file === null) return entry === null;
      if (snapshot.link === null) {
        return entry !== null
          && sameMachineSettingsFile(readMachineSettingsFile(snapshot.sourceName, entry), snapshot.file);
      }
      if (
        entry === null
        || !sameMachineSettingsStat(entry, snapshot.link.stat)
        || readlinkSync(snapshot.sourceName) !== snapshot.link.target
        || realpathSync(snapshot.sourceName) !== snapshot.targetPath
      ) {
        return false;
      }
      const targetMatches = withMachineSettingsDirectory(snapshot.targetParent, () =>
        sameMachineSettingsFile(readMachineSettingsFile(snapshot.targetName), snapshot.file!));
      const entryAfter = machineSettingsEntry(snapshot.sourceName);
      return targetMatches === true
        && entryAfter !== null
        && sameMachineSettingsStat(entry, entryAfter)
        && readlinkSync(snapshot.sourceName) === snapshot.link.target
        && realpathSync(snapshot.sourceName) === snapshot.targetPath;
    });
    return matches === true;
  } catch {
    return false;
  }
}

function machineSettingsAliasMachineState(snapshot: MachineSettingsSnapshot): boolean | null {
  if (snapshot.file === null) return false;
  try {
    if (snapshot.targetPath === realpathSync(machineStateFile())) return true;
  } catch (error) {
    if (!missingPath(error)) return null;
  }
  try {
    const stateFile = statSync(machineStateFile());
    return stateFile.isFile()
      && stateFile.dev === snapshot.file.stat.dev
      && stateFile.ino === snapshot.file.stat.ino;
  } catch (error) {
    return missingPath(error) ? false : null;
  }
}

type MachineSettingsSurfaceSnapshot = {
  id: string;
  path: string;
  absolute: string;
  snapshot: MachineSettingsSnapshot | null;
  aliasesMachineState: boolean;
  failed: boolean;
};

function snapshotMachineSettingsSurfaces(): MachineSettingsSurfaceSnapshot[] {
  const snapshots: MachineSettingsSurfaceSnapshot[] = [];
  for (const surface of SURFACES) {
    const placement = machineCarrier(surface);
    if (!placement || placement.kind !== "settings") continue;
    const absolute = carrierPath(placement);
    const path = `~/${placement.path}`;
    try {
      try {
        lstatSync(dirname(absolute));
      } catch (error) {
        if (missingPath(error)) {
          snapshots.push({ id: surface.id, path, absolute, snapshot: null, aliasesMachineState: false, failed: false });
          continue;
        }
        throw error;
      }
      const snapshot = snapshotMachineSettings(absolute);
      const alias = machineSettingsAliasMachineState(snapshot);
      snapshots.push({
        id: surface.id,
        path,
        absolute,
        snapshot,
        aliasesMachineState: alias === true,
        failed: alias === null,
      });
    } catch {
      snapshots.push({ id: surface.id, path, absolute, snapshot: null, aliasesMachineState: false, failed: true });
    }
  }
  return snapshots;
}

function machineSettingsMutationRefusals(initial: MachineSettingsSurfaceSnapshot[]): Array<{ path: string; reason: string }> {
  const currentBySurface = new Map(snapshotMachineSettingsSurfaces().map((entry) => [entry.id, entry]));
  const refused: Array<{ path: string; reason: string }> = [];
  for (const before of initial) {
    const current = currentBySurface.get(before.id);
    if (
      current === undefined
      || before.absolute !== current.absolute
      || before.aliasesMachineState
      || current.aliasesMachineState
      || before.failed
      || current.failed
      || (before.snapshot === null
        ? current.snapshot !== null
        : current.snapshot === null || !machineSettingsSnapshotMatches(before.snapshot))
    ) {
      const isUnreadable = before.failed || current?.failed === true;
      refused.push({ path: before.path, reason: isUnreadable ? SETTINGS_UNREADABLE : SETTINGS_MUTATION_REFUSED });
    }
  }
  return refused;
}

const MACHINE_STATE_REFUSED = "machine-state-identity-unverified";
const MACHINE_STATE_BUSY = "machine-state-busy";
const MACHINE_STATE_LOCK_STALE = "machine-state-lock-stale";
const MACHINE_STATE_KEPT_ASIDE = "machine-state-kept-aside";
const MACHINE_STATE_STRANDED = "machine-state-stranded";
const MACHINE_STATE_COPY_KEPT = "machine-state-copy-kept";
const MACHINE_STATE_UNREADABLE = "machine-state-unreadable";
const MACHINE_STATE_NAME = "machine.json";
/** Held for the whole commit, so a second run never reads the claim window's absence as
 *  "no state" and links a fresh record over the user's. It names its owner, so a lock
 *  left by a run that was killed can be told apart from one that is still working. */
const MACHINE_STATE_LOCK = `.${MACHINE_STATE_NAME}.lock`;
type MachineRefusal = { path: string; reason: string };

export function machineStateLockFile(): string {
  return join(home(), MACHINE_STATE_LOCK);
}

type MachineStateFile = { dev: number; ino: number; content: Buffer };
type OwnedMachineEntry = { name: string; dev: number; ino: number };
type MachineStateLockScope = { bootId: string | null; pidNamespace: string | null };
type MachineStateLockOwner = MachineStateLockScope & { pid: number; hostname: string; startedAt: string };
type MachineStateLock = { dev: number; ino: number; content: Buffer; owner: MachineStateLockOwner | null };
/** The state file as this run read it, bound to the directory that holds it. `unsafe`
 *  means another path could see its bytes: a link, not a regular file, or a second name.
 *  `stranded` means machine.json is gone and an interrupted run's copies could not be put
 *  back; `copies` on `ready` are such copies kept beside a machine.json that exists. */
type MachineStateRecord =
  | { kind: "no-home" }
  | { kind: "unsafe" }
  | { kind: "busy" }
  | { kind: "stranded"; copies: string[] }
  | { kind: "ready"; directory: MachineSettingsDirectory; file: MachineStateFile | null; copies: string[] };

/** The bytes behind a descriptor, only while that inode has exactly one name. */
function soleMachineStateFile(descriptor: number): MachineStateFile | null {
  const before = fstatSync(descriptor);
  if (!before.isFile() || before.nlink !== 1) return null;
  const content = readFileSync(descriptor);
  const after = fstatSync(descriptor);
  const isUnchanged = after.nlink === 1
    && after.dev === before.dev
    && after.ino === before.ino
    && after.mtimeMs === before.mtimeMs
    && after.size === content.length;
  return isUnchanged ? { dev: after.dev, ino: after.ino, content } : null;
}

function readOwnMachineStateFile(): MachineStateFile | "unsafe" | null {
  const entry = machineSettingsEntry(MACHINE_STATE_NAME);
  if (entry === null) return null;
  if (!entry.isFile()) return "unsafe";
  const descriptor = openSync(MACHINE_STATE_NAME, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    return soleMachineStateFile(descriptor) ?? "unsafe";
  } finally {
    closeSync(descriptor);
  }
}

function readMachineStateRecord(): MachineStateRecord {
  let directory: MachineSettingsDirectory;
  try {
    directory = machineSettingsDirectory(home());
  } catch (error) {
    return missingPath(error) ? { kind: "no-home" } : { kind: "unsafe" };
  }
  try {
    const read = withMachineSettingsDirectory(directory, () => {
      const recovery = recoverInterruptedCommit();
      return { ...recovery, file: readOwnMachineStateFile() };
    });
    if (read === null || read.file === "unsafe") return { kind: "unsafe" };
    if (read.isBusy) return { kind: "busy" };
    const copies = read.copies.map((name) => join(directory.path, name));
    if (read.file === null && copies.length > 0) return { kind: "stranded", copies };
    return { kind: "ready", directory, file: read.file, copies };
  } catch {
    return { kind: "unsafe" };
  }
}

/** Why readMachineState() is not the whole truth right now, or null when it is: a lock (a
 *  run mid-commit, or one that stopped there), an interrupted run's copy while machine.json
 *  is missing, or a machine.json that cannot be read. Read-only: the next init, update,
 *  config or uninstall is what recovers. A read failure is not absence (R8). */
export function machineStateUnavailable(): MachineRefusal | null {
  const directory = home();
  let names: string[];
  try {
    names = readdirSync(directory);
  } catch (error) {
    return missingPath(error) ? null : { path: machineStateFile(), reason: MACHINE_STATE_UNREADABLE };
  }
  if (names.includes(MACHINE_STATE_LOCK)) {
    const held = readMachineStateLock(machineStateLockFile());
    const isStale = held !== null && isLockOwnerGone(held.owner);
    return { path: machineStateLockFile(), reason: isStale ? MACHINE_STATE_LOCK_STALE : MACHINE_STATE_BUSY };
  }
  if (!names.includes(MACHINE_STATE_NAME)) {
    const copies = names.filter(isClaimName).sort((left, right) => left.localeCompare(right)).map((name) => join(directory, name));
    return copies.length === 0 ? null : { path: copies.join(", "), reason: MACHINE_STATE_STRANDED };
  }
  try {
    JSON.parse(readFileSync(machineStateFile(), "utf8"));
    return null;
  } catch {
    return { path: machineStateFile(), reason: MACHINE_STATE_UNREADABLE };
  }
}

function isClaimName(name: string): boolean {
  return name.startsWith(`.${MACHINE_STATE_NAME}.`) && name.endsWith(".claim");
}

/** A run stopped inside the commit (Ctrl-C, a kill, a crash) leaves its lock, and maybe the
 *  original machine.json under a private claim name. Under the lock — a provably dead
 *  owner's is reclaimed, never anyone else's — a lone claim goes back under its real name
 *  while that name is free; every other copy is kept and returned to be named. Busy while
 *  a live, foreign-host or unreadable lock is held. Runs inside the machine home. */
function recoverInterruptedCommit(): { isBusy: boolean; copies: string[] } {
  if (!pathEntryExists(MACHINE_STATE_LOCK) && readdirSync(".").filter(isClaimName).length === 0) {
    return { isBusy: false, copies: [] };
  }
  const lock = acquireMachineStateLock();
  if (lock === null) return { isBusy: true, copies: [] };
  try {
    return { isBusy: false, copies: restoreLoneClaim() };
  } finally {
    removeOwnedMachineEntry(lock);
  }
}

function restoreLoneClaim(): string[] {
  const claims = readdirSync(".").filter(isClaimName).sort();
  if (claims.length !== 1 || pathEntryExists(MACHINE_STATE_NAME)) return claims;
  const name = claims[0]!;
  try {
    const stat = lstatSync(name);
    if (restoreClaimedMachineState({ name, dev: stat.dev, ino: stat.ino })) return [];
  } catch {
    /* not restorable: kept and named below */
  }
  return claims;
}

function acquireMachineStateLock(): OwnedMachineEntry | null {
  return createMachineStateLock() ?? (reclaimStaleMachineStateLock() ? createMachineStateLock() : null);
}

/** The lock appears whole: its owner record is staged under a private name and linked in,
 *  and a link never replaces a name that exists, so no run ever sees an empty lock. */
function createMachineStateLock(): OwnedMachineEntry | null {
  const processStart = new Date(Date.now() - process.uptime() * 1000).toISOString();
  const owner: MachineStateLockOwner = { pid: process.pid, hostname: hostname(), startedAt: processStart, ...machineStateLockScope() };
  const staged = stageMachineState(`${JSON.stringify(owner)}\n`);
  if (staged === null) return null;
  try {
    linkSync(staged.name, MACHINE_STATE_LOCK);
    return { name: MACHINE_STATE_LOCK, dev: staged.dev, ino: staged.ino };
  } catch {
    return null;
  } finally {
    removeOwnedMachineEntry(staged);
  }
}

/** A lock is taken back only from an owner provably gone: written on this host by a pid
 *  that no longer exists. It is moved aside first and deleted only while it is still the
 *  exact lock judged stale; anything else is linked back under its name, never replacing
 *  a lock that took the name meanwhile. */
function reclaimStaleMachineStateLock(): boolean {
  const held = readMachineStateLock(MACHINE_STATE_LOCK);
  if (held === null || !isLockOwnerGone(held.owner)) return false;
  const aside = privateMachineStateName("stale-lock");
  try {
    renameSync(MACHINE_STATE_LOCK, aside);
  } catch {
    return false;
  }
  const moved = readMachineStateLock(aside);
  const isJudgedLock = moved !== null && moved.dev === held.dev && moved.ino === held.ino && moved.content.equals(held.content);
  try {
    if (isJudgedLock) {
      unlinkSync(aside);
      return true;
    }
    linkSync(aside, MACHINE_STATE_LOCK);
    unlinkSync(aside);
  } catch {
    /* the lock that holds the name wins; the moved one stays under its private name */
  }
  return isJudgedLock;
}

function readMachineStateLock(path: string): MachineStateLock | null {
  let descriptor: number | null = null;
  try {
    if (!lstatSync(path).isFile()) return null;
    descriptor = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    const stat = fstatSync(descriptor);
    if (!stat.isFile()) return null;
    const content = readFileSync(descriptor);
    return { dev: stat.dev, ino: stat.ino, content, owner: parseLockOwner(content.toString("utf8")) };
  } catch {
    return null;
  } finally {
    if (descriptor !== null) closeSync(descriptor);
  }
}

function parseLockOwner(text: string): MachineStateLockOwner | null {
  try {
    const owner = JSON.parse(text) as Partial<MachineStateLockOwner> | null;
    if (owner === null || typeof owner !== "object") return null;
    const { pid, hostname: host, startedAt, bootId = null, pidNamespace = null } = owner;
    if (typeof pid !== "number" || !Number.isInteger(pid) || pid <= 0) return null;
    if (typeof host !== "string" || typeof startedAt !== "string") return null;
    if (!isOptionalName(bootId) || !isOptionalName(pidNamespace)) return null;
    return { pid, hostname: host, startedAt, bootId, pidNamespace };
  } catch {
    return null;
  }
}

function isOptionalName(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

/** The boot and the pid namespace this run's pids belong to, where the kernel names them
 *  (Linux /proc); null elsewhere. A container that shares the host name and this home sees
 *  other pids than the host, so a pid it cannot find is not proof the owner is gone. */
export function machineStateLockScope(): MachineStateLockScope {
  return {
    bootId: readKernelName(() => readFileSync("/proc/sys/kernel/random/boot_id", "utf8").trim()),
    pidNamespace: readKernelName(() => readlinkSync("/proc/self/ns/pid")),
  };
}

function readKernelName(read: () => string): string | null {
  try {
    const name = read();
    return name.length > 0 ? name : null;
  } catch {
    return null;
  }
}

/** Only ESRCH from this host, this boot and this pid namespace proves the owner gone: a
 *  live pid (even another user's, which answers EPERM), another host's, boot's or
 *  namespace's pid, a Linux run that cannot read its own scope, or a lock we cannot parse
 *  all stay held. */
function isLockOwnerGone(owner: MachineStateLockOwner | null): boolean {
  if (owner === null || owner.hostname !== hostname()) return false;
  const scope = machineStateLockScope();
  if (owner.bootId !== scope.bootId || owner.pidNamespace !== scope.pidNamespace) return false;
  if (process.platform === "linux" && (scope.bootId === null || scope.pidNamespace === null)) return false;
  try {
    process.kill(owner.pid, 0);
    return false;
  } catch (error) {
    return typeof error === "object" && error !== null && "code" in error && error.code === "ESRCH";
  }
}

/** The copies an interrupted run left that this run kept, each named in the report. */
function interruptedCopyRefusals(record: MachineStateRecord): MachineRefusal[] {
  if (record.kind === "stranded") return record.copies.map((path) => ({ path, reason: MACHINE_STATE_STRANDED }));
  if (record.kind === "ready") return record.copies.map((path) => ({ path, reason: MACHINE_STATE_COPY_KEPT }));
  return [];
}

function machineStateFromRecord(record: MachineStateRecord): MachineState {
  if (record.kind !== "ready" || record.file === null) return { version: "", carriers: {} };
  return parseMachineState(record.file.content.toString("utf8"));
}

function privateMachineStateName(purpose: "tmp" | "claim" | "stale-lock"): string {
  return `.${MACHINE_STATE_NAME}.${process.pid}.${randomBytes(6).toString("hex")}.${purpose}`;
}

function stageMachineState(content: string): OwnedMachineEntry | null {
  const name = privateMachineStateName("tmp");
  let descriptor: number;
  try {
    descriptor = openSync(name, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o666);
  } catch {
    return null;
  }
  let entry: OwnedMachineEntry | null = null;
  try {
    const stat = fstatSync(descriptor);
    entry = { name, dev: stat.dev, ino: stat.ino };
    writeFileSync(descriptor, content);
    return entry;
  } catch {
    if (entry !== null) removeOwnedMachineEntry(entry);
    return null;
  } finally {
    closeSync(descriptor);
  }
}

function claimedMachineStateMatches(name: string, file: MachineStateFile): boolean {
  if (!lstatSync(name).isFile()) return false;
  const descriptor = openSync(name, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const claimed = soleMachineStateFile(descriptor);
    return claimed !== null && claimed.dev === file.dev && claimed.ino === file.ino && claimed.content.equals(file.content);
  } finally {
    closeSync(descriptor);
  }
}

/** Move whatever is named machine.json right now to a private name, so the identity check
 *  judges exactly the entry the mutation will act on instead of a pathname that can change. */
function claimMachineState(file: MachineStateFile): { entry: OwnedMachineEntry; isOurs: boolean } | null {
  const name = privateMachineStateName("claim");
  try {
    renameSync(MACHINE_STATE_NAME, name);
  } catch {
    return null;
  }
  // From here the original lives under `name`: every outcome must name it, never drop it.
  try {
    const stat = lstatSync(name);
    return { entry: { name, dev: stat.dev, ino: stat.ino }, isOurs: claimedMachineStateMatches(name, file) };
  } catch {
    return { entry: { name, dev: -1, ino: -1 }, isOurs: false };
  }
}

/** Put a claimed entry back without replacing anything that took its name meanwhile; when
 *  that is impossible the bytes stay under the claim name rather than being lost, and the
 *  caller has to say where. */
function restoreClaimedMachineState(entry: OwnedMachineEntry): boolean {
  try {
    const stat = lstatSync(entry.name);
    if (stat.dev !== entry.dev || stat.ino !== entry.ino) return false;
    if (stat.isFile()) linkSync(entry.name, MACHINE_STATE_NAME);
    else if (stat.isSymbolicLink()) symlinkSync(readlinkSync(entry.name), MACHINE_STATE_NAME);
    else return false;
    unlinkSync(entry.name);
    return true;
  } catch {
    return false;
  }
}

function removeOwnedMachineEntry(entry: OwnedMachineEntry): void {
  try {
    const stat = lstatSync(entry.name);
    if (stat.dev === entry.dev && stat.ino === entry.ino) unlinkSync(entry.name);
  } catch {
    /* already gone or replaced: not ours to remove */
  }
}

/** Replace (content) or remove (null) machine.json without ever writing an existing inode:
 *  under the commit lock the old file is claimed and verified as the single-named bytes this
 *  run read, a new file is linked in only where no name exists, and anything unproven is put
 *  back. Returns null on success, or what was refused and where the original now lives. */
function commitMachineState(record: MachineStateRecord, content: string | null): MachineRefusal | null {
  if (record.kind === "no-home") return null;
  if (record.kind === "unsafe") return { path: machineStateFile(), reason: MACHINE_STATE_REFUSED };
  if (record.kind === "busy") return { path: machineStateLockFile(), reason: MACHINE_STATE_BUSY };
  // machine.json is gone and its copies are named by interruptedCopyRefusals: writing a
  // fresh record now would bury the user's recorded state, so nothing is written.
  if (record.kind === "stranded") return null;
  const { directory, file } = record;
  if (content === null && file === null) return null;
  const lock = withMachineSettingsDirectory(directory, acquireMachineStateLock);
  if (lock === null) return { path: machineStateLockFile(), reason: MACHINE_STATE_BUSY };
  try {
    return commitLockedMachineState(directory, file, content);
  } finally {
    withMachineSettingsDirectory(directory, () => {
      removeOwnedMachineEntry(lock);
      return true;
    });
  }
}

function commitLockedMachineState(
  directory: MachineSettingsDirectory,
  file: MachineStateFile | null,
  content: string | null,
): MachineRefusal | null {
  const refused: MachineRefusal = { path: machineStateFile(), reason: MACHINE_STATE_REFUSED };
  const staged = content === null ? null : withMachineSettingsDirectory(directory, () => stageMachineState(content));
  if (content !== null && staged === null) return refused;
  const claim = file === null ? null : withMachineSettingsDirectory(directory, () => claimMachineState(file));
  const isClaimed = file === null || (claim !== null && claim.isOurs);
  // With the state claimed, any settings path still reaching its name is an alias.
  const isCommitted = isClaimed
    && !snapshotMachineSettingsSurfaces().some((entry) => entry.failed || entry.aliasesMachineState)
    && linkStagedMachineState(directory, staged);
  const isOriginalInPlace = withMachineSettingsDirectory(directory, () => {
    if (staged !== null) removeOwnedMachineEntry(staged);
    if (claim === null) return true;
    if (isCommitted) {
      removeOwnedMachineEntry(claim.entry);
      return true;
    }
    return restoreClaimedMachineState(claim.entry);
  }) === true;
  if (isCommitted) return null;
  if (claim !== null && !isOriginalInPlace) {
    return { path: join(directory.path, claim.entry.name), reason: MACHINE_STATE_KEPT_ASIDE };
  }
  return refused;
}

/** linkSync never replaces an existing name: a machine.json that appeared meanwhile wins. */
function linkStagedMachineState(directory: MachineSettingsDirectory, staged: OwnedMachineEntry | null): boolean {
  try {
    return withMachineSettingsDirectory(directory, () => {
      if (staged !== null) linkSync(staged.name, MACHINE_STATE_NAME);
      return true;
    }) === true;
  } catch {
    return false;
  }
}

function serializeMachineState(state: MachineState): string {
  return `${JSON.stringify(state, null, 2)}\n`;
}

/** Write the machine-side carriers of the declared surfaces, once per machine.
 *
 *  This is the inversion the milestone makes on purpose, said out loud: until now only
 *  `--global` wrote outside the repo, and every governed repo carried eight to ten hook
 *  files that aged with the repo instead of with the binary. A surface whose host reads
 *  from the user's home now gets its carrier there; the repo keeps only the carriers
 *  whose readers live in the repo (§13.2).
 *
 *  A `settings` carrier can be user-owned. A missing one is created exclusively from our
 *  template; an existing one gets our entries merged in by marker and is replaced only
 *  while it is still the file that was read (replaceMachineSettings, DECISIONS.md D-007). */
export function installMachineCarriers(surfaceIds: string[]): MachineReport {
  const stateRecord = readMachineStateRecord();
  const report: MachineReport = { written: [], untouched: [], refused: interruptedCopyRefusals(stateRecord) };
  const state = machineStateFromRecord(stateRecord);
  const settingsSnapshots = snapshotMachineSettingsSurfaces();
  let mayWriteMachineState = !settingsSnapshots.some((entry) => entry.aliasesMachineState || entry.failed);
  state.version = VERSION;
  for (const id of surfaceIds) {
    const surface = SURFACES.find((s) => s.id === id);
    const placement = surface ? machineCarrier(surface) : null;
    const files = carrierFiles(id);
    if (!surface || !placement || !files) continue;
    const absolute = carrierPath(placement);
    const definition = sha256(files.main);
    if (placement.kind === "module") {
      // A module carrier is ours whole — never merged into — but rewriting the bytes
      // already there is not an install. Reporting it as `written` is how an update that
      // changed nothing came back with a line claiming the machine side was the work
      // (cli-ux-14): the count has to mean something or the report cannot.
      const chainPath = placement.chain ? carrierPath(placement, placement.chain) : null;
      // Ours to rewrite: this binary's bytes, or the bytes whose hash the last install recorded.
      // The bundle is ours with its entry: both are written together, and only the entry's
      // hash is recorded. Anything else is an edit of the user's, kept and named (R28).
      const recorded = state.carriers[id];
      const entry = carrierFileOwner(absolute, files.main, (content) => recorded !== undefined && sha256(content) === recorded);
      const isEntryOurs = entry === "current" || entry === "ours";
      const chain = chainPath === null || !files.chain ? "current" : carrierFileOwner(chainPath, files.chain, () => isEntryOurs);
      if (entry === "current" && chain === "current") {
        state.carriers[id] = definition;
        report.untouched.push(`~/${placement.path}`);
        continue;
      }
      if (entry === "blocked" || chain === "blocked") {
        report.refused.push({ path: `~/${entry === "blocked" ? placement.path : placement.chain ?? ""}`, reason: CARRIER_UNWRITABLE });
        continue;
      }
      if (entry === "theirs" || chain === "theirs") {
        report.refused.push({ path: `~/${entry === "theirs" ? placement.path : placement.chain ?? ""}`, reason: CARRIER_EDITED });
        continue;
      }
      // The bundle first: an entry written beside a missing bundle imports nothing.
      const isWritten = (files.chain === null || chainPath === null || writeCarrierModule(chainPath, files.chain))
        && writeCarrierModule(absolute, files.main);
      if (!isWritten) {
        report.refused.push({ path: `~/${placement.path}`, reason: CARRIER_UNWRITABLE });
        continue;
      }
      state.carriers[id] = definition;
      report.written.push(`~/${placement.path}`);
      continue;
    }
    try {
      mkdirSync(dirname(absolute), { recursive: true });
    } catch {
      report.refused.push({ path: `~/${placement.path}`, reason: CARRIER_UNWRITABLE });
      continue;
    }
    const snapshot = readableMachineSettings(absolute);
    if (snapshot === null) {
      mayWriteMachineState = false;
      report.refused.push({ path: `~/${placement.path}`, reason: SETTINGS_UNREADABLE });
      continue;
    }
    if (machineSettingsAliasMachineState(snapshot) !== false) {
      mayWriteMachineState = false;
      report.refused.push({
        path: `~/${placement.path}`,
        reason: SETTINGS_MUTATION_REFUSED,
      });
      continue;
    }
    if (snapshot.file === null) {
      const created = createMachineSettings(snapshot, absolute, files.main);
      if (created === null) {
        report.refused.push({ path: `~/${placement.path}`, reason: CARRIER_UNWRITABLE });
        continue;
      }
      // The re-check before machine.json is written compares against this file now: it is
      // the one this run created, not a change that appeared behind the snapshot.
      const settingsEntry = settingsSnapshots.find((entry) => entry.id === id);
      if (settingsEntry !== undefined) settingsEntry.snapshot = created;
      state.carriers[id] = definition;
      report.written.push(`~/${placement.path}`);
      continue;
    }
    const merged = mergeSharedText(snapshot.file.content.toString("utf8"), files.main);
    if ("refused" in merged) {
      report.refused.push({ path: `~/${placement.path}`, reason: merged.refused });
      continue;
    }
    if (!merged.changed) {
      if (machineSettingsSnapshotMatches(snapshot)) {
        state.carriers[id] = definition;
        report.untouched.push(`~/${placement.path}`);
      } else {
        report.refused.push({
          path: `~/${placement.path}`,
          reason: "settings-changed-after-validation",
        });
      }
      continue;
    }
    const replaced = replaceMachineSettings(snapshot, absolute, merged.text);
    if (replaced === null) {
      report.refused.push({ path: `~/${placement.path}`, reason: SETTINGS_MUTATION_REFUSED });
      continue;
    }
    // The end-of-run re-check compares against the file this run wrote, not the one it read.
    const settingsEntry = settingsSnapshots.find((entry) => entry.id === id);
    if (settingsEntry !== undefined) settingsEntry.snapshot = replaced;
    state.carriers[id] = definition;
    report.written.push(`~/${placement.path}`);
  }
  for (const refusal of machineSettingsMutationRefusals(settingsSnapshots)) {
    mayWriteMachineState = false;
    if (!report.refused.some((entry) => entry.path === refusal.path)) report.refused.push(refusal);
  }
  const stateRefusal = mayWriteMachineState ? commitMachineState(stateRecord, serializeMachineState(state)) : null;
  if (stateRefusal !== null) report.refused.push(stateRefusal);
  return report;
}

/** Whose a module carrier file is: absent, already this binary's bytes, ai-eng's by `isOurs`,
 *  the user's (any other bytes), or blocked (a link, a non-file, or unreadable). */
function carrierFileOwner(path: string, ours: string, isOurs: (content: string) => boolean): "absent" | "current" | "ours" | "theirs" | "blocked" {
  if (!pathEntryExists(path)) return "absent";
  let content: string;
  try {
    if (!lstatSync(path).isFile()) return "blocked";
    content = readFileSync(path, "utf8");
  } catch {
    return "blocked";
  }
  if (content === ours) return "current";
  return isOurs(content) ? "ours" : "theirs";
}

/** A module carrier is ours whole, but only as a regular file: never through a link, into a
 *  directory, or by blocking on a FIFO. */
/** Create a missing machine settings file from our template. Exclusive creation inside the
 *  validated directory is the one settings write that binds to an identity: the kernel
 *  refuses it if any name — a file, a link, a dangling link — appeared there, so nothing
 *  of the user's can be replaced. Returns the snapshot of the file this call created, or
 *  null when creation was refused or the name no longer holds exactly that file. */
function createMachineSettings(snapshot: MachineSettingsSnapshot, absolute: string, content: string): MachineSettingsSnapshot | null {
  const created = withMachineSettingsDirectory(snapshot.sourceParent, () => {
    let descriptor: number | null = null;
    try {
      descriptor = openSync(snapshot.sourceName, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o644);
      writeFileSync(descriptor, content);
      return fstatSync(descriptor);
    } catch {
      return null;
    } finally {
      if (descriptor !== null) closeSync(descriptor);
    }
  });
  if (created === null) return null;
  const after = readableMachineSettings(absolute);
  const isOurs = after?.link === null
    && after.file !== null
    && after.file.stat.dev === created.dev
    && after.file.stat.ino === created.ino
    && after.file.content.toString("utf8") === content;
  return isOurs ? after : null;
}

/** Replace a settings file the person owns with `content` — only while it is still the very
 *  file that was read, and only through its one name (a hard link's second name would be
 *  left on the old bytes). Staged beside it with O_EXCL, never through a link, then renamed
 *  over it: the host never reads half a file, and a failure leaves the original. A link to
 *  a dotfiles repo stays a link; its target is what gets replaced.
 *
 *  The last check and the rename are two calls, so a file swapped in between them is
 *  replaced. Whoever can do that inside your home already owns your editor's settings.
 *  Refusing every existing settings file instead (3.0.0) left every existing user with no
 *  hooks at all. */
function replaceMachineSettings(snapshot: MachineSettingsSnapshot, absolute: string, content: string): MachineSettingsSnapshot | null {
  const original = snapshot.file;
  if (original === null || original.stat.nlink !== 1 || !machineSettingsSnapshotMatches(snapshot)) return null;
  const parent = snapshot.link === null ? snapshot.sourceParent : snapshot.targetParent;
  const name = snapshot.link === null ? snapshot.sourceName : snapshot.targetName;
  const staged = `.${name}.ai-eng-${randomBytes(6).toString("hex")}`;
  const isReplaced = withMachineSettingsDirectory(parent, () => {
    let descriptor: number | null = null;
    try {
      descriptor = openSync(staged, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, original.stat.mode & 0o777);
      writeFileSync(descriptor, content);
      closeSync(descriptor);
      descriptor = null;
      if (!sameMachineSettingsFile(readMachineSettingsFile(name), original)) throw new Error("changed while staged");
      renameSync(staged, name);
      return true;
    } catch {
      if (descriptor !== null) closeSync(descriptor);
      try {
        unlinkSync(staged);
      } catch {
        // Never staged, or already renamed: nothing of ours is left to sweep.
      }
      return false;
    }
  });
  if (isReplaced !== true) return null;
  const after = readableMachineSettings(absolute);
  return after?.file?.content.toString("utf8") === content ? after : null;
}

/** Remove a settings file that held only ai-eng's entries, while it is still the file read. */
function unlinkMachineSettings(snapshot: MachineSettingsSnapshot): boolean {
  const original = snapshot.file;
  if (original === null || snapshot.link !== null || original.stat.nlink !== 1) return false;
  return withMachineSettingsDirectory(snapshot.sourceParent, () => {
    if (!sameMachineSettingsFile(readMachineSettingsFile(snapshot.sourceName), original)) return false;
    unlinkSync(snapshot.sourceName);
    return true;
  }) === true;
}

function writeCarrierModule(path: string, content: string): boolean {
  let descriptor: number | null = null;
  try {
    mkdirSync(dirname(path), { recursive: true });
    descriptor = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_NOFOLLOW | constants.O_NONBLOCK, 0o644);
    if (!fstatSync(descriptor).isFile()) return false;
    ftruncateSync(descriptor, 0);
    writeFileSync(descriptor, content);
    return true;
  } catch {
    return false;
  } finally {
    if (descriptor !== null) closeSync(descriptor);
  }
}

/** Take the machine carriers back out. Our entries out of a shared settings file by
 *  marker, our module and its bundle away whole — and nothing else: a name that merely
 *  looks like ours is not evidence, so a settings file we cannot rewrite is left alone
 *  and said. A hook line left behind once the package is gone errors on every call, so
 *  our entries do come out of a file the person owns (replaceMachineSettings, D-007). */
export function removeMachineCarriers(surfaceIds: string[]): { lines: string[]; refused: MachineRefusal[] } {
  const lines: string[] = [];
  const stateRecord = readMachineStateRecord();
  const refused: MachineRefusal[] = interruptedCopyRefusals(stateRecord);
  const state = machineStateFromRecord(stateRecord);
  const settingsSnapshots = snapshotMachineSettingsSurfaces();
  let mayMutateMachineState = !settingsSnapshots.some((entry) => entry.aliasesMachineState || entry.failed);
  for (const id of surfaceIds) {
    const surface = SURFACES.find((s) => s.id === id);
    const placement = surface ? machineCarrier(surface) : null;
    if (!surface || !placement) continue;
    const absolute = carrierPath(placement);
    if (placement.kind === "module") {
      const outcome = removeCarrierModule(id, placement);
      refused.push(...outcome.kept);
      if (outcome.isEntryKept) continue;
      delete state.carriers[id];
      if (outcome.isEntryRemoved) lines.push(`~/${placement.path} removed`);
      continue;
    }
    if (!pathEntryExists(absolute)) {
      delete state.carriers[id];
      continue;
    }
    const snapshot = readableMachineSettings(absolute);
    if (snapshot === null) {
      mayMutateMachineState = false;
      refused.push({ path: `~/${placement.path}`, reason: SETTINGS_UNREADABLE });
      continue;
    }
    if (machineSettingsAliasMachineState(snapshot) !== false) {
      mayMutateMachineState = false;
      refused.push({ path: `~/${placement.path}`, reason: SETTINGS_MUTATION_REFUSED });
      continue;
    }
    if (snapshot.file === null) {
      delete state.carriers[id];
      continue;
    }
    const current = snapshot.file.content.toString("utf8");
    const stripped = stripSharedText(current);
    if (stripped === null) {
      refused.push({ path: `~/${placement.path}`, reason: REMOVAL_REFUSED });
      continue;
    }
    if (stripped === current) {
      delete state.carriers[id];
      continue;
    }
    const settingsEntry = settingsSnapshots.find((entry) => entry.id === id);
    if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0 && unlinkMachineSettings(snapshot)) {
      // The absent file is what the end-of-run re-check must find, not a null snapshot.
      if (settingsEntry !== undefined) settingsEntry.snapshot = readableMachineSettings(absolute);
      delete state.carriers[id];
      lines.push(`~/${placement.path} removed (it held only ai-eng entries)`);
      continue;
    }
    const replaced = replaceMachineSettings(snapshot, absolute, stripped);
    if (replaced === null) {
      refused.push({ path: `~/${placement.path}`, reason: SETTINGS_MUTATION_REFUSED });
      continue;
    }
    if (settingsEntry !== undefined) settingsEntry.snapshot = replaced;
    delete state.carriers[id];
    lines.push(`~/${placement.path}: ai-eng entries removed, yours kept`);
  }
  for (const refusal of machineSettingsMutationRefusals(settingsSnapshots)) {
    mayMutateMachineState = false;
    if (!refused.some((entry) => entry.path === refusal.path)) refused.push(refusal);
  }
  // The record of what wrote what goes with the carriers: an empty machine.json is a
  // leftover that would make the next doctor read a version that is no longer there.
  // Nothing left to remember and no file there means nothing to write either.
  const isStateEmpty = Object.keys(state.carriers).length === 0 && state.templateDir === undefined;
  const nextState = isStateEmpty ? null : serializeMachineState(state);
  const stateRefusal = mayMutateMachineState ? commitMachineState(stateRecord, nextState) : null;
  if (stateRefusal !== null) refused.push(stateRefusal);
  return { lines, refused };
}

/** A module carrier and its bundle leave only while they are byte for byte what this
 *  binary writes; an edited entry is the user's now and is kept and named, together with
 *  the bundle it imports. */
function removeCarrierModule(id: string, placement: Carrier): { isEntryRemoved: boolean; isEntryKept: boolean; kept: MachineRefusal[] } {
  const files = carrierFiles(id);
  const entry = removeExactFile(carrierPath(placement), files?.main ?? null);
  if (entry === "kept" || entry === "refused") {
    return { isEntryRemoved: false, isEntryKept: true, kept: [{ path: `~/${placement.path}`, reason: carrierKeptReason(entry) }] };
  }
  const chain = placement.chain === undefined ? "absent" : removeExactFile(carrierPath(placement, placement.chain), files?.chain ?? null);
  const kept = chain === "kept" || chain === "refused" ? [{ path: `~/${placement.chain}`, reason: carrierKeptReason(chain) }] : [];
  return { isEntryRemoved: entry === "removed", isEntryKept: false, kept };
}

function carrierKeptReason(outcome: "kept" | "refused"): string {
  return outcome === "refused" ? REMOVAL_REFUSED : CARRIER_EDITED;
}

/** Remove one file through its checked parent, only while it holds exactly `expected`.
 *  `refused` is a file still exactly ours whose delete failed: not the user's edit. */
function removeExactFile(absolute: string, expected: string | null): "removed" | "kept" | "refused" | "absent" {
  if (!pathEntryExists(absolute)) return "absent";
  const root = dirname(absolute);
  const checked = safeProjectPath(root, basename(absolute));
  const snapshot = checked === null ? null : readProjectFileSnapshot(root, checked);
  if (checked === null || snapshot === null || expected === null || !snapshot.content.equals(Buffer.from(expected))) return "kept";
  return unlinkProjectPath(root, checked, snapshot) ? "removed" : "refused";
}

/** Everything installCanon wrote OUTSIDE the canon home, removed on uninstall's
 *  "everything" scope: the mirrors would otherwise point into a deleted canon and the
 *  command shims and machine hook would survive as orphans.
 *  Only ai-eng's own entries go — a real directory a person put in a mirror stays, and so
 *  does a link of theirs into the canon under another name or written another way. An
 *  entry still ours whose delete the filesystem refused is added to `refused`, by path. */
export function removeMachineArtifacts(refused: string[] = []): number {
  const base = machineBase();
  const canonDir = join(home(), "skills");
  // Resolved on both sides: macOS tmpdir() hands out /var/... while the symlink
  // resolves to /private/var/..., and a raw startsWith silently kept every link.
  const canonical = (path: string): string => {
    try {
      return realpathSync(path);
    } catch {
      return path;
    }
  };
  const canonReal = canonical(canonDir);
  let removed = 0;
  const names = (dir: string): string[] => {
    try {
      return readdirSync(dir);
    } catch {
      return [];
    }
  };
  const isCanonPath = (candidate: string): boolean => {
    const pathFromCanon = relative(canonReal, candidate);
    return pathFromCanon === "" || (
      pathFromCanon !== ".." && !pathFromCanon.startsWith(`..${sep}`) && !isAbsolute(pathFromCanon)
    );
  };
  const removeCanonLink = (directory: string, name: string): boolean => {
    const link = join(directory, name);
    const originalStat = lstatSync(link);
    if (!originalStat.isSymbolicLink()) return false;
    const originalTarget = readlinkSync(link);
    // Only the exact pair linkSkills writes is ours; any other name or target is a user's alias.
    if (name.startsWith(".") || originalTarget !== join(canonDir, name)) return false;
    const originalCanonical = canonical(link);
    if (!isCanonPath(originalCanonical)) return false;
    const verifiedStat = lstatSync(link);
    if (verifiedStat.dev !== originalStat.dev || verifiedStat.ino !== originalStat.ino || readlinkSync(link) !== originalTarget) {
      return false;
    }

    const parent = canonical(directory);
    const previousDirectory = process.cwd();
    try {
      process.chdir(parent);
      if (realpathSync(".") !== parent) return false;
      const currentStat = lstatSync(name);
      if (
        !currentStat.isSymbolicLink()
        || currentStat.dev !== originalStat.dev
        || currentStat.ino !== originalStat.ino
        || readlinkSync(name) !== originalTarget
        || canonical(name) !== originalCanonical
      ) {
        return false;
      }
      try {
        unlinkSync(name);
      } catch (error) {
        if (isFilesystemRefusal(error)) refused.push(link);
        return false;
      }
      return true;
    } finally {
      process.chdir(previousDirectory);
    }
  };
  for (const target of mirrorTargets()) {
    for (const name of names(target.dir)) {
      try {
        if (removeCanonLink(target.dir, name)) removed += 1;
      } catch {
        /* not ours or not readable: leave it */
      }
    }
    pruneIfEmpty(target.dir);
  }
  const commandsDir = join(base, ".config", "opencode", "commands");
  for (const name of names(canonDir)) {
    // Ours only while it is exactly the body installCommands renders: an edited one stays.
    const command = join(commandsDir, `${name}.md`);
    const outcome = removeExactFile(command, commandBody(canonDir, name));
    if (outcome === "removed") removed += 1;
    if (outcome === "refused") refused.push(command);
  }
  pruneIfEmpty(commandsDir);
  return removed;
}

/** Remove a directory only when it is empty — our sweep emptied it, and an empty
 *  scaffold is noise. A mirror still holding someone else's skills stays. */
function pruneIfEmpty(dir: string): void {
  try {
    if (readdirSync(dir).length === 0) rmdirSync(dir);
  } catch {
    /* absent or not empty: nothing to prune */
  }
}

/** OpenCode loads skills but does not list them as `/name`; a command file per skill
 *  does it, `$ARGUMENTS` carrying the human's text. Derived from the canon, so a new
 *  skill is a command the day it ships — never a second list to keep in sync.
 *  Cursor, Copilot CLI and Copilot Chat in VS Code read the mirrors themselves
 *  (.agents/skills, .claude/skills) and need no shim. */
function installCommands(canonDir: string, earlier: ReadonlyMap<string, string>): string[] {
  const dir = join(machineBase(), ".config", "opencode", "commands");
  let count = 0;
  const kept: string[] = [];
  const refused: string[] = [];
  let bodies: Map<string, string>;
  try {
    bodies = renderCommands(canonDir, true);
  } catch (error) {
    if (!isFilesystemRefusal(error)) throw error;
    return [`⚠ ${refusedChangeText(canonDir, error)}`];
  }
  for (const [name, body] of bodies) {
    const outcome = writeOwnedText(dir, `${name}.md`, body, earlier.get(name));
    if (outcome === "written" || outcome === "current") count += 1;
    if (outcome === "kept") kept.push(`${name}.md`);
    if (outcome === "refused") refused.push(join(dir, `${name}.md`));
  }
  kept.sort((a, b) => a.localeCompare(b, "en"));
  const lines = count > 0 ? [`✓ ~/.config/opencode/commands/ — ${count} slash commands (/<skill-name>)`] : [];
  if (kept.length > 0) lines.push(`⚠ ${kept.length} slash command(s) in ~/.config/opencode/commands are yours (a link, or edited since ai-eng wrote them) — kept: ${kept.join(", ")}. Delete one to receive ai-eng's version`);
  if (refused.length > 0) lines.push(`⚠ ${refused.length} slash command(s) not written — changed meanwhile, or the filesystem refused; left as they are: ${refused.join(", ")}`);
  return lines;
}

/** Every skill's command body as the canon renders it now, by skill name. An unreadable canon
 *  is no earlier render (empty) unless the caller needs to know (`isStrict`). */
function renderCommands(canonDir: string, isStrict = false): Map<string, string> {
  const bodies = new Map<string, string>();
  let names: string[];
  try {
    names = readdirSync(canonDir);
  } catch (error) {
    if (isStrict) throw error;
    return bodies;
  }
  for (const name of names) {
    const body = commandBody(canonDir, name);
    if (body !== null) bodies.set(name, body);
  }
  return bodies;
}

/** Write a file only ai-eng owns: a missing one is created (`wx`, never through a link); an
 *  existing one is refreshed only while it is a single-named regular file holding ai-eng's
 *  current bytes or the bytes it wrote last time. A link or anything else is the user's. */
function writeOwnedText(dir: string, name: string, ours: string, earlier: string | undefined): "written" | "current" | "kept" | "refused" {
  const path = join(dir, name);
  if (!pathEntryExists(path)) {
    try {
      mkdirSync(dir, { recursive: true });
      writeFileSync(path, ours, { flag: "wx" });
      return "written";
    } catch (error) {
      if (!isFilesystemRefusal(error)) throw error;
      return "refused";
    }
  }
  const absolute = safeProjectPath(dir, name);
  const snapshot = absolute === null ? null : readProjectFileSnapshot(dir, absolute);
  if (absolute === null || snapshot === null) return "kept";
  const current = snapshot.content.toString("utf8");
  if (current === ours) return "current";
  if (earlier === undefined || current !== earlier) return "kept";
  return writeProjectFile(dir, absolute, snapshot, ours) ? "written" : "refused";
}

/** The one rendering of a skill's slash command: install writes it, uninstall removes only
 *  a file that still equals it. Null when the name is not a skill with a SKILL.md. */
function commandBody(canonDir: string, name: string): string | null {
  if (name.startsWith(".")) return null;
  let description: string;
  try {
    description = skillDescription(readFileSync(join(canonDir, name, "SKILL.md"), "utf8"));
  } catch {
    return null;
  }
  return `---\ndescription: ${description}\n---\n\nLoad the \`${name}\` skill via the skill tool, then execute it for this request:\n\n$ARGUMENTS\n`;
}

/** One palette line out of a SKILL.md description: folded YAML collapsed to a single
 *  string, cut at a word boundary so the list stays readable. */
function skillDescription(markdown: string): string {
  const block = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? "";
  const raw = (Bun.YAML.parse(block) as { description?: unknown } | null)?.description;
  const text = typeof raw === "string" ? raw.replace(/\s+/g, " ").trim() : "";
  return text.length <= 200 ? text : `${text.slice(0, 200).replace(/\s\S*$/, "")}…`;
}

function isLinkTo(link: string, target: string): boolean {
  try {
    return resolve(dirname(link), readlinkSync(link)) === resolve(target);
  } catch {
    return false;
  }
}

/** Link each skill into a mirror. Only the exact link ai-eng writes (`<name> -> <canon>/<name>`,
 *  live or dangling) is ours and is left as is; a link of the user's under that name is kept and
 *  named, and a real directory there is theirs too. */
function linkSkills(canonDir: string, mirrorDir: string): { count: number; kept: string[] } {
  let count = 0;
  const kept: string[] = [];
  for (const name of readdirSync(canonDir)) {
    if (name.startsWith(".")) continue; // the canon's dot-entries are payload, not skills
    const linkPath = join(mirrorDir, name);
    let entry: Stats | null = null;
    try {
      entry = lstatSync(linkPath);
    } catch {
      /* absent: create */
    }
    if (entry !== null) {
      if (!entry.isSymbolicLink()) continue; // a real directory there is not ours to replace
      if (isLinkTo(linkPath, join(canonDir, name))) count += 1;
      else kept.push(name);
      continue;
    }
    try {
      symlinkSync(join(canonDir, name), linkPath, "dir");
      count += 1;
    } catch {
      /* FS refused: leave absent, doctor reports the mirror gap */
    }
  }
  return { count, kept };
}
