// src/surfaces/carriers-install.ts — write and remove the carriers themselves: the machine-side
// hook or plugin plus the chain bundle beside it, merged into a shared settings file by marker
// or written whole as a module, and the machine.json record updated only when nothing refused
// (machine-state owns the record and its lock). Also here: the sweep of the pre-2.2.0 repo
// carriers, OpenCode's retired scanned bundle, and uninstall's "everything" scope over the
// sugared mirrors and slash commands (removeMachineArtifacts), which borrows the canon
// module's helpers without the canon ever importing the carriers back.

import { constants, closeSync, fchmodSync, fstatSync, ftruncateSync, lstatSync, mkdirSync, openSync, readFileSync, readlinkSync, readdirSync, realpathSync, renameSync, rmSync, rmdirSync, unlinkSync, writeFileSync, type Stats } from "node:fs";
import { randomBytes } from "node:crypto";
import { join, basename, dirname } from "node:path";
import { home, machineBase } from "../env.ts";
import { VERSION } from "../version.ts";
import { pathIsWithin } from "../shared-project-fs.ts";
import { mergeSharedText, stripSharedText } from "../install.ts";
import { safeProjectPath, readProjectFileSnapshot, unlinkProjectPath, writeProjectFile, isFilesystemRefusal } from "../embed.ts";
import { SURFACES, carrierDefinition, carrierFiles, carrierPath, machineCarrier, type Carrier } from "./adapters.ts";
import {
  SETTINGS_MUTATION_REFUSED, SETTINGS_UNREADABLE, type MachineRefusal,
  pathEntryExists, withMachineSettingsDirectory, sameMachineSettingsFile,
  readableMachineSettings, machineSettingsSnapshotMatches, machineSettingsAliasMachineState,
  snapshotMachineSettingsSurfaces, machineSettingsMutationRefusals,
  readMachineStateRecord, machineStateFromRecord, interruptedCopyRefusals,
  commitMachineState, serializeMachineState,
  type MachineSettingsSnapshot, readMachineSettingsFile,
} from "./machine-state.ts";
import { mirrorTargets, aiEngSkillNames, commandBody, sameDirectory } from "./canon-install.ts";
/** The pre-2.2.0 repo paths of the carriers that now live on the machine, keyed to the
 *  surface that owned them. The refresh sweeps these so an old install does not keep
 *  ghost carriers — a hook file nobody reads is the exact bug 2.2.0 exists to end. This
 *  map is history, not a second source of truth: nothing is installed from it, and the lock
 *  sweeps read it only so a settings file among them is stripped by marker, never deleted. */
export const MOVED_REPO_CARRIERS: Readonly<Record<string, string>> = {
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

export type MachineReport = { written: string[]; untouched: string[]; retired: string[]; refused: Array<{ path: string; reason: string }> };
const CARRIER_UNWRITABLE = "carrier-path-unwritable";
const CARRIER_EDITED = "carrier-edited";
const REMOVAL_REFUSED = "removal-refused";

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
  const report: MachineReport = { written: [], untouched: [], retired: [], refused: interruptedCopyRefusals(stateRecord) };
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
    const definition = carrierDefinition(files.main);
    if (placement.kind === "module") {
      // A module carrier is ours whole — never merged into — but rewriting the bytes
      // already there is not an install. Reporting it as `written` is how an update that
      // changed nothing came back with a line claiming the machine side was the work
      // (cli-ux-14): the count has to mean something or the report cannot.
      const chainPath = placement.chain ? carrierPath(placement, placement.chain) : null;
      // Ours to rewrite once ai-eng recorded writing it, edited or not: a carrier is ai-eng's
      // file. The bundle is ours with its entry, or by the record alone (a removal that took
      // the entry and was refused the bundle). A file there that ai-eng never recorded is
      // somebody else's, kept and named (R28).
      const isRecorded = state.carriers[id] !== undefined;
      // 3.0.x wrote the bundle INSIDE OpenCode's plugin scan; the loader imported it as a
      // plugin entry and the host died. Ours by its generated header, so it goes first.
      if (id === "opencode") {
        const retired = retireScannedChain();
        if (retired === "removed") report.retired.push(`~/${RETIRED_SCANNED_CHAIN}`);
        if (retired === "refused") {
          report.refused.push({ path: `~/${RETIRED_SCANNED_CHAIN}`, reason: REMOVAL_REFUSED });
          // The loader still imports that file, so the host stays broken; writing the new
          // pair beside it would report a fix that cannot take effect.
          continue;
        }
      }
      const entry = carrierFileOwner(absolute, files.main, () => isRecorded);
      const isEntryOurs = entry === "current" || entry === "ours";
      const chain = chainPath === null || !files.chain ? "current" : carrierFileOwner(chainPath, files.chain, () => isRecorded || isEntryOurs);
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
      // The umask trims the mode open() was given: a 0664 file would come back 0644.
      if (process.platform !== "win32") fchmodSync(descriptor, original.stat.mode & 0o777);
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
    // A second name (a hard link) would receive the rewrite too: that file is not ai-eng's.
    const opened = fstatSync(descriptor);
    if (!opened.isFile() || opened.nlink !== 1) return false;
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
      if (id === "opencode") {
        const retired = retireScannedChain();
        if (retired === "removed") lines.push(`~/${RETIRED_SCANNED_CHAIN} removed (it sat inside OpenCode's plugin scan)`);
        if (retired === "refused") {
          refused.push({ path: `~/${RETIRED_SCANNED_CHAIN}`, reason: REMOVAL_REFUSED });
          // Keep the record: the leftover is still ours, and the next uninstall retries.
          continue;
        }
      }
      const outcome = removeCarrierModule(id, placement, state.carriers[id] !== undefined);
      refused.push(...outcome.kept);
      if (outcome.isEntryRemoved) lines.push(`~/${placement.path} removed`);
      // The record goes only with the last file: a bundle left unrecorded would be kept forever.
      if (outcome.isEntryKept || outcome.kept.length > 0) continue;
      delete state.carriers[id];
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

/** The chain bundle older releases wrote INSIDE OpenCode's plugin scan. The loader imports
 *  every file there as a plugin entry and takes its default export as a plugin; a bundle is
 *  not one, so the host refused it and its provider config hook failed with it. */
const RETIRED_SCANNED_CHAIN = ".config/opencode/plugins/ai-eng-chain.ts";
const AI_ENG_BUNDLE_HEADER = "// @bun\n";
const AI_ENG_BUNDLE_TRAILER = 'export default "ai-eng-chain";';

/** Remove the retired bundle when it is one of ours, judged by the header and trailer every
 *  generated bundle carries — never by the machine.json record, which says ai-eng wrote the
 *  surface, not this file. A file a person put at that path is kept, before and after the
 *  surface is recorded. Never reported as a write: it is a file leaving, not arriving. */
function retireScannedChain(): "removed" | "kept" | "refused" | "absent" {
  const absolute = join(machineBase(), RETIRED_SCANNED_CHAIN);
  if (!pathEntryExists(absolute)) return "absent";
  try {
    if (!lstatSync(absolute).isFile()) return "kept";
    const content = readFileSync(absolute, "utf8");
    if (!content.startsWith(AI_ENG_BUNDLE_HEADER) || !content.trimEnd().endsWith(AI_ENG_BUNDLE_TRAILER)) return "kept";
    return removeExactFile(absolute, content);
  } catch {
    return "kept";
  }
}

/** A module carrier and its bundle leave when ai-eng recorded writing them, edited or not,
 *  or while they are byte for byte what this binary writes. A file there ai-eng never
 *  recorded is somebody else's and is kept and named, together with the bundle it imports. */
function removeCarrierModule(id: string, placement: Carrier, isRecorded: boolean): { isEntryRemoved: boolean; isEntryKept: boolean; kept: MachineRefusal[] } {
  const files = carrierFiles(id);
  const entry = removeExactFile(carrierPath(placement), isRecorded ? ANY_CONTENT : files?.main ?? null);
  if (entry === "kept" || entry === "refused") {
    return { isEntryRemoved: false, isEntryKept: true, kept: [{ path: `~/${placement.path}`, reason: carrierKeptReason(entry) }] };
  }
  const chain = placement.chain === undefined ? "absent" : removeExactFile(carrierPath(placement, placement.chain), isRecorded ? ANY_CONTENT : files?.chain ?? null);
  const kept = chain === "kept" || chain === "refused" ? [{ path: `~/${placement.chain}`, reason: carrierKeptReason(chain) }] : [];
  return { isEntryRemoved: entry === "removed", isEntryKept: false, kept };
}

function carrierKeptReason(outcome: "kept" | "refused"): string {
  return outcome === "refused" ? REMOVAL_REFUSED : CARRIER_EDITED;
}

/** `removeExactFile`'s answer for a file proven ai-eng's by record: whatever it holds. */
const ANY_CONTENT = Symbol("any content");

/** Remove one regular file through its checked parent, only while it holds exactly
 *  `expected` (or anything, for ANY_CONTENT). `refused` is a file still ours whose delete
 *  failed: not somebody else's. */
function removeExactFile(absolute: string, expected: string | typeof ANY_CONTENT | null): "removed" | "kept" | "refused" | "absent" {
  if (!pathEntryExists(absolute)) return "absent";
  const root = dirname(absolute);
  const checked = safeProjectPath(root, basename(absolute));
  const snapshot = checked === null ? null : readProjectFileSnapshot(root, checked);
  if (checked === null || snapshot === null || expected === null) return "kept";
  if (expected !== ANY_CONTENT && !snapshot.content.equals(Buffer.from(expected))) return "kept";
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
  const isCanonPath = (candidate: string): boolean => pathIsWithin(canonReal, candidate);
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
  /** A verified copy ai-eng's fallback wrote: a plain folder under a canon skill's name that
   *  still holds exactly the canon's bytes. Anything else there — an edited copy, a folder of
   *  yours, a skill retired from the canon whose bytes can no longer be proven ours — stays. */
  const removeCanonCopy = (directory: string, name: string): boolean => {
    const copy = join(directory, name);
    let originalStat: Stats;
    try {
      originalStat = lstatSync(copy);
    } catch {
      return false;
    }
    if (originalStat.isSymbolicLink() || !originalStat.isDirectory()) return false;
    if (!sameDirectory(join(canonDir, name), copy)) return false;
    const parent = canonical(directory);
    const previousDirectory = process.cwd();
    try {
      process.chdir(parent);
      if (realpathSync(".") !== parent) return false;
      const currentStat = lstatSync(name);
      if (currentStat.isSymbolicLink() || !currentStat.isDirectory() || !sameDirectory(join(canonDir, name), name)) {
        return false;
      }
      try {
        rmSync(name, { recursive: true });
      } catch (error) {
        if (isFilesystemRefusal(error)) refused.push(copy);
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
        if (removeCanonLink(target.dir, name) || removeCanonCopy(target.dir, name)) removed += 1;
      } catch {
        /* not ours or not readable: leave it */
      }
    }
    pruneIfEmpty(target.dir);
  }
  const commandsDir = join(base, ".config", "opencode", "commands");
  const aiEngSkills = aiEngSkillNames(home());
  // A retired skill's folder can be gone while its command was left by a refused removal.
  for (const name of new Set([...names(canonDir), ...aiEngSkills])) {
    // An ai-eng skill's command is ai-eng's whatever it holds; one for a skill of yours is
    // ai-eng's only while it is exactly the body installCommands renders.
    const command = join(commandsDir, `${name}.md`);
    const outcome = removeExactFile(command, aiEngSkills.has(name) ? ANY_CONTENT : commandBody(canonDir, name));
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
