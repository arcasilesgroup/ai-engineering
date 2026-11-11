// src/surfaces/canon-install.ts — install the global canon once per machine (~/.ai-engineering)
// and mirror it into the hosts' skill folders: the skills, the agents, the per-skill slash
// commands and the links that point from ~/.claude/skills, ~/.agents/skills and OpenCode's
// skill dir into the canon. The mirror rule everywhere is the same: ai-eng writes or rewrites
// only what is provably its own; a link or a file of the user's is kept and named, never
// repointed or removed. `removeMachineArtifacts` (uninstall's "everything" scope) lives with
// the carrier side but borrows this module's mirror and command helpers.

import { cpSync, lstatSync, mkdirSync, readdirSync, readFileSync, readlinkSync, rmSync, symlinkSync, writeFileSync, type Stats } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { home, machineBase, versionFile } from "../env.ts";
import {
  materializeSkills, materializeAgents, materializeScripts, removeStaleCanonFiles,
  recordCanonOwnership, recordedMachinePaths, removeMachineEntry, embeddedUnder, isVersionCacheRecord, safeProjectPath, readProjectFileSnapshot, writeProjectFile,
  refusedStaleCanonText, refusedChangeText, isFilesystemRefusal,
} from "../embed.ts";
import { pathEntryExists } from "./machine-state.ts";
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

/** Install the global canon once per machine, then mirror it (symlink, junction or verified
 *  copy on Windows — symlinks where the OS supports them).
 *
 *  The carriers are NOT here: they follow the declared surfaces, not the canon, and
 *  `installMachineCarriers()` owns them (§13.2). */
export function installCanon(version: string): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  // Read before this run changes the canon: the skills whose slash commands the previous
  // install wrote (a skill gone since leaves a command to take out), and the agents ai-eng
  // retires now (a copy of one in ~/.claude/agents goes with it).
  const earlierCommands = renderCommands(canonDir);
  const shippedAgents = new Set(shippedAgentNames());
  const retiredAgents = recordedMachinePaths(home()).filter((key) => key.startsWith("agents/")).map((key) => basename(key)).filter((name) => !shippedAgents.has(name));
  const aiEngSkills = aiEngSkillNames(home());
  // Everything ai-eng shipped is rewritten, edited or not, and everything it no longer ships
  // is swept: a skill folder of ours is ai-eng's whole, so it always equals this binary.
  lines.push(...warningsOf(materializeSkills(canonDir)));
  const swept = removeStaleCanonFiles(home());
  if (swept.removed.length > 0) lines.push(`✓ swept ${swept.removed.length} path(s) this binary no longer ships: ${swept.removed.join(", ")}`);
  if (swept.refused.length > 0) lines.push(`⚠ ${refusedStaleCanonText(swept.refused)}`);
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
      if (mirrored.copies === 0) return [`✓ Symlink → ${target.label} (${mirrored.count} skills)`, ...kept];
      const linked = mirrored.count === 0 ? [] : [`✓ Symlink → ${target.label} (${mirrored.count} skills)`];
      return [...linked, `✓ Copy → ${target.label} (${mirrored.copies} skills)`, ...kept];
    }));
  }
  lines.push(...installCommands(canonDir, earlierCommands, aiEngSkills));
  const agentsMirror = join(machineBase(), ".claude", "agents");
  lines.push(...refusalAsLines(agentsMirror, () => installAgentsCanon(retiredAgents)));
  // Written last: a retired agent whose mirror copy could not be removed stays recorded, so
  // the next run retries it instead of forgetting it was ai-eng's.
  const leftInMirror = retiredAgents.filter((name) => isRegularFile(join(agentsMirror, name))).map((name) => `agents/${name}`);
  const commandsDir = join(machineBase(), ".config", "opencode", "commands");
  const leftCommands = [...aiEngSkills]
    .filter((name) => !pathEntryExists(join(canonDir, name)) && isRegularFile(join(commandsDir, `${name}.md`)))
    .map((name) => `skills/${name}`);
  const recordRefusal = recordCanonOwnership(home(), [...leftInMirror, ...leftCommands]);
  if (recordRefusal !== null) lines.push(`⚠ ${recordRefusal}`);
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
 *  The mirror is ours as the exact link this installer writes (`<home>/agents`, the F10
 *  rule) or, in a real folder, as the files named after ai-eng's agents: those always hold
 *  ai-eng's bytes, and a retired one goes. A link of the user's at the mirror, and every
 *  other agent in the folder, is theirs and never touched.
 *  Exported so tests can drive the mirror under AI_ENG_HOME without writing the real home. */
export function installAgentsCanon(retired: readonly string[] = []): string[] {
  const agentsCanon = join(home(), "agents");
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
  return [...lines, ...copyAgentsInto(agentsMirror, agentsCanon, shippedAgentNames(), retired)];
}

/** The agent files this binary ships, by file name. */
function shippedAgentNames(): string[] {
  return [...embeddedUnder("agents/").keys()].map((path) => path.slice("agents/".length)).filter((name) => name.endsWith(".md"));
}

/** Copy the agents into a real mirror folder: each of ai-eng's agents always holds ai-eng's
 *  bytes, and a retired one goes. A link at one of those names is the user's and stays. */
function copyAgentsInto(mirror: string, canon: string, names: readonly string[], retired: readonly string[]): string[] {
  const kept: string[] = [];
  const refused: string[] = [];
  for (const name of names) {
    const outcome = copyAgentFile(mirror, name, readFileSync(join(canon, name)));
    if (outcome === "kept") kept.push(name);
    if (outcome === "refused") refused.push(join(mirror, name));
  }
  for (const name of retired) {
    if (!isRegularFile(join(mirror, name)) || removeMachineEntry(mirror, name)) continue;
    refused.push(join(mirror, name));
  }
  const lines = ["✓ Copy → ~/.claude/agents (copy)"];
  if (kept.length > 0) lines.push(`⚠ ${kept.length} link(s) of yours in ~/.claude/agents under the name of an ai-eng agent — kept, never written through: ${kept.join(", ")}. Move one aside to receive ai-eng's agent`);
  if (refused.length > 0) lines.push(`⚠ ${refused.length} agent file(s) not written or removed — changed meanwhile, or the filesystem refused; left as they are: ${refused.join(", ")}`);
  return lines;
}

/** A plain file at the path (a link, a folder or nothing is not). */
function isRegularFile(path: string): boolean {
  try {
    return lstatSync(path).isFile();
  } catch {
    return false;
  }
}

function copyAgentFile(mirror: string, name: string, ours: Buffer): "written" | "current" | "kept" | "refused" {
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
  return writeProjectFile(mirror, absolute, snapshot, ours.toString("utf8")) ? "written" : "refused";
}

/** OpenCode loads skills but does not list them as `/name`; a command file per skill
 *  does it, `$ARGUMENTS` carrying the human's text. Derived from the canon, so a new
 *  skill is a command the day it ships — never a second list to keep in sync.
 *  Cursor, Copilot CLI and Copilot Chat in VS Code read the mirrors themselves
 *  (.agents/skills, .claude/skills) and need no shim. */
function installCommands(canonDir: string, earlier: ReadonlyMap<string, string>, aiEngSkills: ReadonlySet<string>): string[] {
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
  // A command of an ai-eng skill is ai-eng's whatever it holds; one ai-eng wrote for a skill
  // of yours in the canon is ai-eng's only while it still holds what ai-eng wrote.
  const isOurs = (name: string) => (current: string): boolean => aiEngSkills.has(name) || current === earlier.get(name);
  for (const [name, body] of bodies) {
    const outcome = writeOwnedText(dir, `${name}.md`, body, isOurs(name));
    if (outcome === "written" || outcome === "current") count += 1;
    if (outcome === "kept") kept.push(`${name}.md`);
    if (outcome === "refused") refused.push(join(dir, `${name}.md`));
  }
  // A command ai-eng wrote for a skill that is gone from the canon goes with the skill.
  // An ai-eng skill's command goes whatever it holds (the record keeps naming a retired skill
  // while its command is left, so a refused removal is retried); a command ai-eng wrote for a
  // skill of yours goes only while it still holds what ai-eng wrote.
  for (const file of listCommandFiles(dir)) {
    const name = file.slice(0, -".md".length);
    const command = join(dir, file);
    if (bodies.has(name) || !isRegularFile(command)) continue;
    let current: string;
    try {
      current = readFileSync(command, "utf8");
    } catch {
      continue; // unreadable: not judged, so not removed
    }
    if (!isOurs(name)(current)) continue;
    if (!removeMachineEntry(dir, file)) refused.push(command);
  }
  kept.sort((a, b) => a.localeCompare(b, "en"));
  const lines = count > 0 ? [`✓ ~/.config/opencode/commands/ — ${count} slash commands (/<skill-name>)`] : [];
  if (kept.length > 0) lines.push(`⚠ ${kept.length} slash command(s) in ~/.config/opencode/commands are yours (a link, or your own command under a skill's name) — kept: ${kept.join(", ")}. Move one aside to receive ai-eng's command`);
  if (refused.length > 0) lines.push(`⚠ ${refused.length} slash command(s) not written — changed meanwhile, or the filesystem refused; left as they are: ${refused.join(", ")}`);
  return lines;
}

/** The skills ai-eng ships or shipped on this machine (its ownership record), by name. */
export function aiEngSkillNames(homeDir: string): Set<string> {
  return new Set(recordedMachinePaths(homeDir).filter((key) => key.startsWith("skills/")).map((key) => key.slice("skills/".length)));
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

/** Write a file ai-eng owns: a missing one is created (`wx`, never through a link); an
 *  existing one receives ai-eng's bytes while `isOurs` says so and it is a single-named
 *  regular file. A link or a second name is somebody else's and is never written through. */
function writeOwnedText(dir: string, name: string, ours: string, isOurs: (current: string) => boolean): "written" | "current" | "kept" | "refused" {
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
  if (snapshot.nlink !== 1 || !isOurs(current)) return "kept";
  return writeProjectFile(dir, absolute, snapshot, ours) ? "written" : "refused";
}

/** The one rendering of a skill's slash command: install writes it, uninstall removes only
 *  a file that still equals it. Null when the name is not a skill with a SKILL.md. */
export function commandBody(canonDir: string, name: string): string | null {
  if (name.startsWith(".")) return null;
  let description: string;
  try {
    description = skillDescription(readFileSync(join(canonDir, name, "SKILL.md"), "utf8"));
  } catch {
    return null;
  }
  return `---\ndescription: ${description}\n---\n\nLoad the \`${name}\` skill via the skill tool, then execute it for this request:\n\n$ARGUMENTS\n`;
}

/** The `.md` files in the commands folder; none when it cannot be read. */
function listCommandFiles(dir: string): string[] {
  try {
    return readdirSync(dir).filter((name) => name.endsWith(".md") && !name.startsWith("."));
  } catch {
    return [];
  }
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
 *  named, and a real directory there is theirs too — unless it is byte for byte a copy of the
 *  canon skill, which only ai-eng's own fallback copy is.
 *  When the OS refuses the link (Windows without developer mode refuses `dir` symlinks), a
 *  junction is tried — it needs no privilege — and only when even that is refused does a
 *  verified copy take over, so a stock Windows `init --global` still leaves every mirror usable. */
function linkSkills(canonDir: string, mirrorDir: string): { count: number; kept: string[]; copies: number } {
  let count = 0;
  let copies = 0;
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
      if (entry.isSymbolicLink()) {
        if (isLinkTo(linkPath, join(canonDir, name))) count += 1;
        else kept.push(name);
      } else if (entry.isDirectory() && sameDirectory(join(canonDir, name), linkPath)) {
        copies += 1; // a verified copy from an earlier link-less run, still current
      }
      continue;
    }
    try {
      symlinkSync(join(canonDir, name), linkPath, "dir");
      count += 1;
      continue;
    } catch {
      /* the OS refused the link: fall through to the junction, then the copy */
    }
    if (process.platform === "win32") {
      try {
        symlinkSync(join(canonDir, name), linkPath, "junction");
        count += 1;
        continue;
      } catch {
        /* junction refused too: fall through to the verified copy */
      }
    }
    if (copySkillInto(join(canonDir, name), linkPath)) copies += 1;
    /* a copy the filesystem refused is swept or left absent: doctor reports the mirror gap */
  }
  // The exact link ai-eng writes, to a skill no longer in the canon: ours, and now dangling.
  for (const name of readdirSync(mirrorDir)) {
    const linkPath = join(mirrorDir, name);
    if (name.startsWith(".") || pathEntryExists(join(canonDir, name))) continue;
    try {
      if (lstatSync(linkPath).isSymbolicLink() && readlinkSync(linkPath) === join(canonDir, name)) removeMachineEntry(mirrorDir, name);
    } catch {
      /* not ours, or the filesystem refused: doctor reports a dangling mirror entry */
    }
  }
  return { count, kept, copies };
}

/** Copy one skill folder into a mirror — the fallback when no form of link is possible.
 *  The copy is only accepted when every file byte-equals the canon afterwards, the same
 *  judgment the removal side later uses to tell ai-eng's copy from the user's folder. */
function copySkillInto(canonSkill: string, mirrorPath: string): boolean {
  try {
    cpSync(canonSkill, mirrorPath, { recursive: true, errorOnExist: true, force: false });
  } catch (error) {
    // EEXIST: the name was taken meanwhile — never ours to touch. Any other refusal half-landed
    // a copy of ours, which is swept so the next run can retry it.
    if (isFilesystemRefusal(error) && error.code === "EEXIST") return false;
    try {
      if (lstatSync(mirrorPath).isDirectory() && !lstatSync(mirrorPath).isSymbolicLink()) rmSync(mirrorPath, { recursive: true });
    } catch {
      /* keep whatever landed: doctor reports the mirror gap */
    }
    return false;
  }
  return sameDirectory(canonSkill, mirrorPath);
}

/** Byte-for-byte equality of two skill folders: same entries, same kinds, same bytes. A
 *  symlink, a socket, or anything unreadable is never equal — the doubt always keeps the folder. */
export function sameDirectory(left: string, right: string): boolean {
  const names = (directory: string): string[] | null => {
    try {
      return readdirSync(directory).sort();
    } catch {
      return null;
    }
  };
  const leftNames = names(left);
  const rightNames = names(right);
  if (leftNames === null || rightNames === null || leftNames.length !== rightNames.length) return false;
  for (const name of leftNames) {
    if (!rightNames.includes(name)) return false;
    let leftEntry: Stats | null = null;
    let rightEntry: Stats | null = null;
    try {
      leftEntry = lstatSync(join(left, name));
      rightEntry = lstatSync(join(right, name));
    } catch {
      return false;
    }
    if (leftEntry.isDirectory() !== rightEntry.isDirectory() || (!leftEntry.isDirectory() && !leftEntry.isFile())) return false;
    if (leftEntry.isDirectory()) {
      if (!sameDirectory(join(left, name), join(right, name))) return false;
      continue;
    }
    try {
      if (!readFileSync(join(left, name)).equals(readFileSync(join(right, name)))) return false;
    } catch {
      return false;
    }
  }
  return true;
}
