// src/surfaces/adapters.ts — generators per surface: JSON-stdio (Claude/Cursor/Codex/Copilot)
// or TS module (OpenCode/OMP). Surface = ~150 LOC of adapter + its proof (§13).

import surfacesJson from "./surfaces.json";
import { writeFileSync, mkdirSync, symlinkSync, unlinkSync, readdirSync, lstatSync, existsSync, readFileSync, rmSync, realpathSync, rmdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { home, versionFile, machineBase } from "../env.ts";
import { mergeSharedText, stripSharedText, sha256 } from "../install.ts";
import { VERSION } from "../version.ts";
import { materializeSkills, embeddedTemplate, embeddedChainBundle, removeStaleCanonFiles } from "../embed.ts";
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

/** The bytes of one surface's carrier at one placement: the entry file and, for the
 *  in-process hosts, the chain bundle that must sit beside it. Null for a surface with
 *  no generator (§13: no adapter, no offer). */
export function carrierFiles(id: string, scope: Carrier["scope"]): { main: string; chain: string | null } | null {
  switch (id) {
    case "claude-code":
      return { main: embeddedTemplate("settings.claude.json.tpl"), chain: null };
    case "oh-my-pi":
      return { main: embeddedTemplate("plugin.omp.ts.tpl"), chain: embeddedChainBundle() };
    case "opencode":
      return { main: embeddedTemplate("plugin.opencode.ts.tpl"), chain: embeddedChainBundle() };
    case "pi":
      return { main: embeddedTemplate("plugin.pi.ts.tpl"), chain: embeddedChainBundle() };
    case "codex":
      return { main: embeddedTemplate("settings.codex.json.tpl"), chain: null };
    case "cursor":
      return { main: embeddedTemplate("settings.cursor.json.tpl"), chain: null };
    case "copilot":
      // The CLI reads the machine file and never the repo one, and it fails CLOSED on
      // a missing binary — so the machine template guards the call with `command -v`.
      return {
        main: embeddedTemplate(scope === "machine" ? "settings.copilot.cli.json.tpl" : "settings.copilot.json.tpl"),
        chain: null,
      };
    default:
      return null;
  }
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
 *  per-row degradation belongs to the row, from the measured fields beside it.
 *
 *  This used to read "experimental — rewrite may be partial", which was true of neither
 *  row under it (Cursor has no rewrite at all, Codex replaces the whole input) and
 *  "best-effort — cloud FS: receipts may not survive", vaguer than the measurement behind
 *  it. research/003 puts the rule: "the label is the promise; the fields are the
 *  measurement. They are allowed to disagree — but not silently". */
export const SURFACE_TIERS: ReadonlyArray<readonly [string, string]> = [
  ["core", "core — deny + rewrite"],
  ["experimental", "experimental — deny yes; the row names what degrades"],
  ["best-effort", "best-effort — deny yes; what survives is the host's deployment"],
  ["skills-only", "skills only — no guards in hot-path"],
];

export type MirrorTarget = { dir: string; label: string };

/** Re-exported for the callers that already know the surfaces layer: the definition is
 *  in env.ts, where the guards can reach it without dragging the templates in. */
export { machineBase } from "../env.ts";

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
export function installCanon(version: string): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  materializeSkills(canonDir);
  const swept = removeStaleCanonFiles(home());
  if (swept.length > 0) lines.push(`✓ swept ${swept.length} file(s) this binary no longer ships: ${swept.join(", ")}`);
  const entries = readdirSync(canonDir, { withFileTypes: true }).filter((e) => e.isDirectory() && !e.name.startsWith("."));
  lines.push(`✓ ${home()}/skills/ — ${entries.length} ai-* skills installed`);
  // Seeds the 24h notice cache (§14.0). Health never reads this file: init and
  // doctor byte-compare the canon against the payload (canonDrift) — this same
  // path also carries the REGISTRY version after a notice check.
  writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() }));
  lines.push("✓ ~/.ai-engineering/version.json — version + 24h cache");
  for (const target of mirrorTargets()) {
    mkdirSync(target.dir, { recursive: true });
    const count = linkSkills(canonDir, target.dir);
    lines.push(`✓ Symlink → ${target.label} (${count} skills)`);
  }
  const commands = installCommands(canonDir);
  if (commands.count > 0) lines.push(`✓ ~/.config/opencode/commands/ — ${commands.count} slash commands (/ai-*)`);
  return lines;
}

/** Carriers that moved from the repo to the machine in 2.2.0, by the path they used to
 *  have. A repo governed before the move still carries them — and a hook file nobody
 *  reads is the exact bug this release exists to end, so the refresh has to take them
 *  out rather than leave them behind as ghosts with our marker in them. This is history,
 *  not a second source of truth: nothing current is computed from it. */
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
 *  bytes are still ours. */
export function sweepMovedRepoCarriers(root: string): { removed: string[]; kept: string[] } {
  const removed: string[] = [];
  const kept: string[] = [];
  for (const rel of Object.keys(MOVED_REPO_CARRIERS)) {
    const absolute = join(root, rel);
    if (!existsSync(absolute)) continue;
    // A settings file we merged into is stripped, not deleted: the user's own keys are in
    // it. Anything else carries our marker or is not ours to touch.
    if (rel.endsWith(".json")) {
      const stripped = stripSharedText(readFileSync(absolute, "utf8"));
      if (stripped === null) {
        kept.push(rel);
        continue;
      }
      if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
        rmSync(absolute, { force: true });
        removed.push(rel);
        continue;
      }
      writeFileSync(absolute, stripped);
      removed.push(rel);
      continue;
    }
    const current = readFileSync(absolute, "utf8");
    if (!current.includes("ai-eng")) {
      kept.push(rel);
      continue;
    }
    rmSync(absolute, { force: true });
    removed.push(rel);
  }
  return { removed, kept };
}

export type MachineReport = { written: string[]; untouched: string[]; refused: Array<{ path: string; reason: string }> };

/** What the machine side remembers: which version wrote each surface's carrier, keyed by
 *  surface id, and the sha256 of the definition it wrote. Two questions depend on it and
 *  neither can be answered from the files themselves:
 *   - a DOWNGRADE. The carrier is the new binary's; the chain it calls would be the old
 *     one, which has no gate, and the policy would fall back onto repos that never asked
 *     (F7). Doctor needs to know the binary is older than the record.
 *   - Codex's trust. Its approval is a hash of the hook DEFINITION, and a definition that
 *     changed re-asks in /hooks. Comparing the shipped bytes against what was recorded is
 *     the only way to know the change happened. */
export type MachineState = { version: string; carriers: Record<string, string>; templateDir?: { previous: string | null; ours: string | null } };

export function machineStateFile(): string {
  return join(home(), "machine.json");
}

export function readMachineState(): MachineState {
  try {
    const doc = JSON.parse(readFileSync(machineStateFile(), "utf8")) as Partial<MachineState>;
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

/** Remember what the git floor did to `init.templateDir`, so uninstall can undo exactly
 *  that: the value it replaced, and the directory this install owns (null when we joined
 *  one the user already had). */
export function rememberTemplateDir(previous: string | null, ours: string | null): void {
  const state = readMachineState();
  state.version = VERSION;
  state.templateDir = { previous, ours };
  writeMachineState(state);
}

function writeMachineState(state: MachineState): void {
  try {
    writeFileSync(machineStateFile(), `${JSON.stringify(state, null, 2)}\n`);
  } catch {
    /* an unwritable state file is a missing warning, never a broken install */
  }
}

/** Write the machine-side carriers of the declared surfaces, once per machine.
 *
 *  This is the inversion the milestone makes on purpose, said out loud: until now only
 *  `--global` wrote outside the repo, and every governed repo carried eight to ten hook
 *  files that aged with the repo instead of with the binary. A surface whose host reads
 *  from the user's home now gets its carrier there; the repo keeps only the carriers
 *  whose readers live in the repo (§13.2).
 *
 *  A `settings` carrier goes through the same merge as any other shared file: it can be
 *  one the user already owns, and nothing of theirs is touched or reformatted. */
export function installMachineCarriers(surfaceIds: string[]): MachineReport {
  const report: MachineReport = { written: [], untouched: [], refused: [] };
  const state = readMachineState();
  state.version = VERSION;
  for (const id of surfaceIds) {
    const surface = SURFACES.find((s) => s.id === id);
    const placement = surface ? machineCarrier(surface) : null;
    const files = carrierFiles(id, "machine");
    if (!surface || !placement || !files) continue;
    const absolute = carrierPath(placement);
    const definition = sha256(files.main);
    if (placement.kind === "module") {
      // A module carrier is ours whole — never merged into — but rewriting the bytes
      // already there is not an install. Reporting it as `written` is how an update that
      // changed nothing came back with a line claiming the machine side was the work
      // (cli-ux-14): the count has to mean something or the report cannot.
      const chainPath = placement.chain ? carrierPath(placement, placement.chain) : null;
      let identical = false;
      try {
        identical =
          readFileSync(absolute, "utf8") === files.main &&
          (chainPath === null || !files.chain || readFileSync(chainPath, "utf8") === files.chain);
      } catch {
        identical = false; // unreadable is not ours to call current — write it
      }
      state.carriers[id] = definition;
      if (identical) {
        report.untouched.push(`~/${placement.path}`);
        continue;
      }
      mkdirSync(dirname(absolute), { recursive: true });
      writeFileSync(absolute, files.main);
      if (files.chain && chainPath) {
        mkdirSync(dirname(chainPath), { recursive: true });
        writeFileSync(chainPath, files.chain);
      }
      report.written.push(`~/${placement.path}`);
      continue;
    }
    if (!existsSync(absolute)) {
      mkdirSync(dirname(absolute), { recursive: true });
      writeFileSync(absolute, files.main);
      state.carriers[id] = definition;
      report.written.push(`~/${placement.path}`);
      continue;
    }
    const merged = mergeSharedText(readFileSync(absolute, "utf8"), files.main);
    if ("refused" in merged) {
      report.refused.push({ path: `~/${placement.path}`, reason: merged.refused });
      continue;
    }
    state.carriers[id] = definition;
    if (!merged.changed) {
      report.untouched.push(`~/${placement.path}`);
      continue;
    }
    writeFileSync(absolute, merged.text);
    report.written.push(`~/${placement.path}`);
  }
  writeMachineState(state);
  return report;
}

/** Take the machine carriers back out. Our entries out of a shared settings file by
 *  marker, our module and its bundle away whole — and nothing else: a name that merely
 *  looks like ours is not evidence, so a settings file we cannot rewrite is left alone
 *  and said. Returns what it did, for the uninstall report. */
export function removeMachineCarriers(surfaceIds: string[]): { lines: string[]; refused: string[] } {
  const lines: string[] = [];
  const refused: string[] = [];
  const state = readMachineState();
  for (const id of surfaceIds) {
    const surface = SURFACES.find((s) => s.id === id);
    const placement = surface ? machineCarrier(surface) : null;
    if (!surface || !placement) continue;
    delete state.carriers[id];
    const absolute = carrierPath(placement);
    if (!existsSync(absolute)) continue;
    if (placement.kind === "module") {
      unlinkSync(absolute);
      if (placement.chain) {
        const chainPath = carrierPath(placement, placement.chain);
        if (existsSync(chainPath)) unlinkSync(chainPath);
      }
      lines.push(`~/${placement.path} removed`);
      continue;
    }
    const stripped = stripSharedText(readFileSync(absolute, "utf8"));
    if (stripped === null) {
      refused.push(`~/${placement.path}`);
      continue;
    }
    if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
      unlinkSync(absolute);
      lines.push(`~/${placement.path} removed (it held only ai-eng entries)`);
      continue;
    }
    writeFileSync(absolute, stripped);
    lines.push(`~/${placement.path}: ai-eng entries removed, yours kept`);
  }
  // The record of what wrote what goes with the carriers: an empty machine.json is a
  // leftover that would make the next doctor read a version that is no longer there.
  const keepsTemplateDir = state.templateDir !== undefined;
  if (Object.keys(state.carriers).length === 0 && !keepsTemplateDir && existsSync(machineStateFile())) unlinkSync(machineStateFile());
  else writeMachineState(state);
  return { lines, refused };
}

/** Everything installCanon wrote OUTSIDE the canon home, removed on uninstall's
 *  "everything" scope: the mirrors would otherwise point into a deleted canon and the
 *  command shims and machine hook would survive as orphans.
 *  Only ai-eng's own entries go — a real directory a person put in a mirror stays. */
export function removeMachineArtifacts(): number {
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
  for (const target of mirrorTargets()) {
    for (const name of names(target.dir)) {
      const link = join(target.dir, name);
      try {
        if (lstatSync(link).isSymbolicLink() && canonical(link).startsWith(canonReal)) {
          unlinkSync(link);
          removed += 1;
        }
      } catch {
        /* not ours or not readable: leave it */
      }
    }
    pruneIfEmpty(target.dir);
  }
  for (const name of names(canonDir)) {
    const command = join(base, ".config", "opencode", "commands", `${name}.md`);
    try {
      if (readFileSync(command, "utf8").includes(`Load the \`${name}\` skill`)) {
        unlinkSync(command);
        removed += 1;
      }
    } catch {
      /* absent or not ours */
    }
  }
  pruneIfEmpty(join(base, ".config", "opencode", "commands"));
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
function installCommands(canonDir: string): { count: number } {
  const dir = join(machineBase(), ".config", "opencode", "commands");
  let count = 0;
  for (const name of readdirSync(canonDir)) {
    if (name.startsWith(".")) continue;
    const skillFile = join(canonDir, name, "SKILL.md");
    if (!existsSync(skillFile)) continue;
    const description = skillDescription(readFileSync(skillFile, "utf8"));
    const body = `---\ndescription: ${description}\n---\n\nLoad the \`${name}\` skill via the skill tool, then execute it for this request:\n\n$ARGUMENTS\n`;
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, `${name}.md`), body);
    count += 1;
  }
  return { count };
}

/** One palette line out of a SKILL.md description: folded YAML collapsed to a single
 *  string, cut at a word boundary so the list stays readable. */
function skillDescription(markdown: string): string {
  const block = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? "";
  const first = /^description:[ \t]*(.*)$/m.exec(block);
  const head = (first?.[1] ?? "").trim();
  const folded = head === "" || /^[>|]-?$/.test(head);
  // A folded value (`description: >-`) lives in the indented lines after the key, up
  // to the next unindented line — the next frontmatter key.
  const continuation = folded
    ? block.slice((first?.index ?? 0) + (first?.[0].length ?? 0)).split(/\n(?=\S)/)[0]!.replace(/\n\s*/g, " ")
    : head;
  const text = continuation.replace(/\s+/g, " ").trim();
  return text.length <= 200 ? text : `${text.slice(0, 200).replace(/\s\S*$/, "")}…`;
}

function linkSkills(canonDir: string, mirrorDir: string): number {
  let count = 0;
  for (const name of readdirSync(canonDir)) {
    if (name.startsWith(".")) continue; // the canon's dot-entries are payload, not skills
    const linkPath = join(mirrorDir, name);
    try {
      if (lstatSync(linkPath).isSymbolicLink()) {
        unlinkSync(linkPath);
      } else {
        continue; // a real directory there is not ours to replace
      }
    } catch {
      /* absent: create */
    }
    try {
      symlinkSync(join(canonDir, name), linkPath, "dir");
      count += 1;
    } catch {
      /* FS refused: leave absent, doctor reports the mirror gap */
    }
  }
  return count;
}
