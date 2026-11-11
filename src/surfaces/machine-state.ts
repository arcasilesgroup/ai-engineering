// src/surfaces/machine-state.ts — custody of machine.json: the machine-side record of what
// wrote each carrier. Three guards depend on it, none of which the files themselves answer:
// a DOWNGRADE (an old binary's chain without the gate), Codex's definition hash and the
// doctor's "read failure is not absence" (R8). The bytes are staged under a private name and
// linked in only where no name exists, never written through an existing inode, and the
// commit is held under a lock whose owner a dead run proves gone. The settings snapshot
// machinery lives here too: an install or a removal must act on the exact bytes it read,
// and refuse instead of guessing when the file changed, or the path could reach it.

import { constants, closeSync, fstatSync, linkSync, lstatSync, openSync, readFileSync, readlinkSync, readdirSync, realpathSync, renameSync, statSync, symlinkSync, unlinkSync, writeFileSync, type Stats } from "node:fs";
import { randomBytes } from "node:crypto";
import { hostname } from "node:os";
import { basename, dirname, join } from "node:path";
import { home } from "../env.ts";
import { SURFACES, carrierPath, machineCarrier } from "./adapters.ts";
/** Whether anything — a file, a directory, a dangling link — has this name. A path that
 *  cannot be inspected counts as present, so it is judged instead of treated as absent. */
export function pathEntryExists(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (error) {
    return !(missingPath(error) || (typeof error === "object" && error !== null && "code" in error && error.code === "ENOTDIR"));
  }
}

export const SETTINGS_MUTATION_REFUSED = "identity-bound-settings-mutation-unavailable";
export const SETTINGS_UNREADABLE = "settings-unreadable";

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
export type MachineSettingsSnapshot = {
  sourceParent: MachineSettingsDirectory;
  sourceName: string;
  targetParent: MachineSettingsDirectory;
  targetName: string;
  targetPath: string | null;
  link: { stat: Stats; target: string } | null;
  file: MachineSettingsFile | null;
};

export function missingPath(error: unknown): boolean {
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

export function withMachineSettingsDirectory<T>(directory: MachineSettingsDirectory, action: () => T): T | null {
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

export function readMachineSettingsFile(name: string, expected?: Stats): MachineSettingsFile | null {
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

export function sameMachineSettingsFile(left: MachineSettingsFile | null, right: MachineSettingsFile): boolean {
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
export function readableMachineSettings(absolute: string): MachineSettingsSnapshot | null {
  try {
    return snapshotMachineSettings(absolute);
  } catch {
    return null;
  }
}

export function machineSettingsSnapshotMatches(snapshot: MachineSettingsSnapshot): boolean {
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

export function machineSettingsAliasMachineState(snapshot: MachineSettingsSnapshot): boolean | null {
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

export type MachineSettingsSurfaceSnapshot = {
  id: string;
  path: string;
  absolute: string;
  snapshot: MachineSettingsSnapshot | null;
  aliasesMachineState: boolean;
  failed: boolean;
};

export function snapshotMachineSettingsSurfaces(): MachineSettingsSurfaceSnapshot[] {
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

export function machineSettingsMutationRefusals(initial: MachineSettingsSurfaceSnapshot[]): Array<{ path: string; reason: string }> {
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
export type { MachineRefusal };

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

export function readMachineStateRecord(): MachineStateRecord {
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
export function interruptedCopyRefusals(record: MachineStateRecord): MachineRefusal[] {
  if (record.kind === "stranded") return record.copies.map((path) => ({ path, reason: MACHINE_STATE_STRANDED }));
  if (record.kind === "ready") return record.copies.map((path) => ({ path, reason: MACHINE_STATE_COPY_KEPT }));
  return [];
}

export function machineStateFromRecord(record: MachineStateRecord): MachineState {
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
export function commitMachineState(record: MachineStateRecord, content: string | null): MachineRefusal | null {
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

export function serializeMachineState(state: MachineState): string {
  return `${JSON.stringify(state, null, 2)}\n`;
}
