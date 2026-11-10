// `ai-eng uninstall` — two scopes, stated plainly: "This project" sweeps EVERY file the lock declares
// ai-eng's (hooks, settings entries, adapters, CI workflow, config, lock) and
// prunes the dirs that end up empty — nothing that depends on ai-eng is left
// behind. "Everything" ALSO removes the machine side (~/.ai-engineering: the
// global skill canon and mirrors). What ai-eng wrote goes, edited or not (git keeps
// only a committed edit); what it never wrote stays. Seeded config the project edited is the
// project's and stays, contract files survive "This project", and "Everything" asks
// twice.

import { spawnSync } from "node:child_process";
import { existsSync, unlinkSync, readdirSync, rmSync, lstatSync, rmdirSync, realpathSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { MOVED_REPO_CARRIERS, SURFACES, machineStateUnavailable, removeMachineArtifacts, removeMachineCarriers, repoCarrier, readMachineState } from "../surfaces/adapters.ts";
import { restoreTemplateDir } from "../floor/template.ts";
import { repoRoot, home, enabledSurfaces, isGoverned } from "../env.ts";
import { parseLock, sha256, stripSharedText, SEEDED_CONFIG, type PlanEntry } from "../install.ts";
import { hashFile } from "../install.ts";
import {
  embeddedTemplate, isFilesystemRefusal, isRemovableCanonOwnershipRecord, recordedMachinePaths, removeMachinePath, isVersionCacheRecord, pruneEmptyDirectoryWithin,
  readProjectFileSnapshot, refusedChangeText, safeProjectPath, unlinkProjectPath, withSafeProjectParent, writeProjectFile,
  CANON_OWNERSHIP_NAME, type ProjectFileSnapshot,
} from "../embed.ts";
import { planEntries, refuseLine } from "./init-shared.ts";
import { select, isCancel } from "@clack/prompts";
import * as ui from "../ui.ts";
import { VERSION } from "../version.ts";
import { scriptedInput } from "../ui.ts";

/** Why a file ai-eng meant to remove or rewrite is still there: it changed under the run,
 *  or the filesystem refused (a read-only, locked or busy folder). Either way it stays. */
const PRESERVED = "file changed during this run, or the filesystem refused the change — preserved";
/** A settings file with a second name: never written through, so ai-eng's entries stay
 *  until it has one name. Its lock entry stays too, or no later run would strip them. */
const HARD_LINKED = "a file with a second name (a hard link) — never written through; ai-eng's entries stay until it has one name, and the next run strips them";

/** Read the declared surfaces and build the asset map from the lock, falling
 *  back to the binary's own file list when the lock is missing or empty. The
 *  declaration must be read ONCE, before anything removes config.toml. */
function readAssetsFromLock(
  root: string,
  declared: string[],
  removed: ui.Row[],
): { assets: Record<string, string>; isLockRecorded: boolean; hasLock: boolean; lockSnapshot: ProjectFileSnapshot | null } {
  // The lock is the ownership register; when it is gone (a half-finished
  // uninstall, a hand-deletion), the binary's own planEntries list is the
  // fallback — same paths, hashes recomputed from the payload it installs.
  // Never a hardcoded subset, never a file it did not install.
  const lockRel = ".ai-engineering/ai-eng.lock";
  const lockPath = safeProjectPath(root, lockRel);
  const hasLock = lockPath !== null && existsSync(lockPath);
  if (lockPath === null && existsSync(join(root, lockRel))) {
    removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: "linked path — not ai-eng's" });
  }
  const lockSnapshot = hasLock && lockPath !== null ? readProjectFileSnapshot(root, lockPath) : null;
  if (hasLock && lockSnapshot === null) {
    removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: PRESERVED });
    return { assets: {}, isLockRecorded: false, hasLock: false, lockSnapshot: null };
  }
  let assets: Record<string, string> = lockSnapshot === null ? {} : parseLock(lockSnapshot.content.toString("utf8")).assets;
  const isLockRecorded = Object.keys(assets).length !== 0;
  if (!isLockRecorded) {
    assets = Object.fromEntries(
      planEntries(declared).map((entry) => [entry.path, sha256(entry.ours)]),
    );
    removed.push({ mark: "muted", text: "no lock — swept by the binary's own file list" });
  }
  return { assets, isLockRecorded, hasLock, lockSnapshot };
}

/** Sweep every declared asset from the project tree and prune empty dirs. */
function sweepProjectSide(
  root: string,
  declared: string[],
  removed: ui.Row[],
): void {
  const { assets, isLockRecorded, hasLock, lockSnapshot } = readAssetsFromLock(root, declared, removed);
  const settingsByPath = collectSettingsByPath();
  for (const rel of Object.keys(assets)) {
    sweepAsset(root, rel, assets, isLockRecorded, settingsByPath, removed);
  }
  if (hasLock) {
    const lockPath = safeProjectPath(root, ".ai-engineering/ai-eng.lock");
    if (lockPath === null || lockSnapshot === null || !unlinkProjectPath(root, lockPath, lockSnapshot)) {
      removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: PRESERVED });
    } else {
      removed.push({ mark: "ok", text: "ai-eng.lock deleted", dim: `${Object.keys(assets).length} owned files swept` });
    }
  } else {
    removed.push({ mark: "muted", text: `${Object.keys(assets).length} owned files swept` });
  }
  pruneCreatedDirs(root, removed);
}

/** Show the scope picker and the "are you sure?" confirmation. Returns the
 *  chosen scope, or null when the user cancelled. */
async function confirmUninstall(input: unknown): Promise<"project" | "everything" | null> {
  ui.section("Two scopes", [
    { mark: "info", text: "This project", dim: "sweeps every file the lock says ai-eng owns: hooks, settings entries, adapters, CI workflow, config, lock. Keeps AGENTS.md, DECISIONS.md, spec/plan." },
    { mark: "warn", text: "Everything", dim: `the project side ABOVE, plus the machine side: deletes ${home()} (global skills, mirrors, caches); files of yours inside it stay. Asks twice.` },
  ]);
  const scope = await pickScope(input);
  if (scope === null) {
    ui.cancelled("Nothing removed.");
    return null;
  }
  // Default is No: uninstall is destructive, a bare Enter must not raze the repo.
  const confirmed = await ui.confirmDefault("Confirm?", false, input as never);
  if (confirmed === false) {
    ui.cancelled("Nothing removed.");
    return null;
  }
  return scope;
}

/** Remove a directory only when it is empty — ai-eng created it, the sweep
 *  emptied it, and an empty scaffold is noise. */
function pruneIfEmpty(root: string, rel: string): boolean {
  const dir = safeProjectPath(root, rel);
  if (dir === null) return false;
  try {
    return withSafeProjectParent(root, dir, (name) => {
      rmdirSync(name);
      return true;
    });
  } catch {
    /* absent, non-empty, or unreadable: nothing to prune */
  }
  return false;
}

async function pickScope(input: unknown): Promise<"project" | "everything" | null> {
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "project", label: "This project" },
      { value: "everything", label: "Everything" },
      { value: "cancel", label: "Cancel" },
    ],
    input: input as never,
  });
  if (isCancel(scope)) return null;
  if (scope === "cancel") return null;
  if (scope === "everything") return "everything";
  return "project";
}

/** Every repo settings file ai-eng merged into, now or in an earlier release: the user's
 *  file with our entries in it, so it is stripped by marker and never deleted whole. */
function collectSettingsByPath(): Map<string, string> {
  const settingsByPath = new Map<string, string>();
  for (const surface of SURFACES) {
    const placement = repoCarrier(surface);
    if (placement?.kind === "settings") settingsByPath.set(placement.path, surface.label);
  }
  for (const [path, owner] of Object.entries(MOVED_REPO_CARRIERS)) {
    if (path.endsWith(".json")) settingsByPath.set(path, owner);
  }
  return settingsByPath;
}

/** The paths a lock records that this run does not write: retired by a release, or of a
 *  surface left out. Still ai-eng's, so they go — init and update share this one rule. */
export function retiredPaths(assets: Record<string, string>, shipped: readonly PlanEntry[]): string[] {
  return Object.keys(assets).filter((path) => !shipped.some((entry) => entry.path === path));
}

/** Remove each retired path by the same rules as uninstall. Returns the ones still ai-eng's
 *  that could not be removed: their lock entry has to stay, or the next run never retries them. */
export function sweepRetiredAssets(root: string, paths: readonly string[], assets: Record<string, string>, removed: ui.Row[]): string[] {
  const settingsByPath = collectSettingsByPath();
  return paths.filter((rel) => {
    const before = removed.length;
    sweepAsset(root, rel, assets, true, settingsByPath, removed);
    return removed.slice(before).some((row) => "dim" in row && (row.dim === PRESERVED || row.dim === HARD_LINKED));
  });
}

/** The Apply plan's note for a retired path: what the sweep will do to it, or null when the
 *  sweep leaves it as it is. Same decision the sweep acts on, so the plan cannot promise a
 *  removal the sweep will not make (a settings file is stripped, a linked path is kept). */
export function retiredPlanNote(root: string, rel: string, assets: Record<string, string>): string | null {
  const step = decideSweep(root, rel, assets, true, collectSettingsByPath());
  if (step.kind === "leave") return null;
  return step.kind === "rewrite" ? "ai-eng's entries stripped, your keys kept" : "removed";
}

/** What the sweep does with one recorded path. Decided before anything is touched, so the
 *  update plan and the sweep itself read the one answer. `row` is what a done step reports. */
type SweepStep =
  | { kind: "leave"; row?: ui.Row }
  | { kind: "unlink"; absolute: string; snapshot: ProjectFileSnapshot; row: ui.Row }
  | { kind: "rewrite"; absolute: string; snapshot: ProjectFileSnapshot; text: string; row: ui.Row };

function sweepAsset(
  root: string,
  rel: string,
  assets: Record<string, string>,
  isLockRecorded: boolean,
  settingsByPath: Map<string, string>,
  removed: ui.Row[],
): void {
  const step = decideSweep(root, rel, assets, isLockRecorded, settingsByPath);
  if (step.kind === "leave") {
    if (step.row !== undefined) removed.push(step.row);
    return;
  }
  const isDone = step.kind === "unlink"
    ? unlinkProjectPath(root, step.absolute, step.snapshot)
    : writeProjectFile(root, step.absolute, step.snapshot, step.text);
  removed.push(isDone ? step.row : { mark: "warn", text: `${rel} kept`, dim: PRESERVED });
}

function decideSweep(
  root: string,
  rel: string,
  assets: Record<string, string>,
  isLockRecorded: boolean,
  settingsByPath: Map<string, string>,
): SweepStep {
  // The lock is untrusted input: a crafted key can point outside the repo —
  // a lock entry escaping to $HOME with a matching hash makes the sweep
  // delete it. A path that escapes root is not ours, no matter what the lock
  // claims: skip it, keep the sweep honest.
  const absolute = resolve(root, rel);
  if (absolute !== root && !absolute.startsWith(root + sep)) {
    return { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: "lock path escapes this repo — not ai-eng's" } };
  }
  if (!existsSync(absolute)) return { kind: "leave" };
  const safeAbsolute = safeProjectPath(root, rel);
  if (safeAbsolute === null) {
    return { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: "linked path — not ai-eng's" } };
  }
  const snapshot = readProjectFileSnapshot(root, safeAbsolute);
  if (snapshot === null) {
    return { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: PRESERVED } };
  }
  const unlink = (row: ui.Row): SweepStep => ({ kind: "unlink", absolute: safeAbsolute, snapshot, row });
  if (settingsByPath.has(rel)) {
    // Unedited: the whole file is ai-eng's template — it goes. Edited: the
    // user's keys stay, only our hook entries come out. The marker logic lives in
    // install.ts beside its inverse, so what init merges in and what uninstall takes
    // out can never drift apart. Unparseable: never rewrite what you cannot read.
    if (snapshot.hash === assets[rel]) return unlink({ mark: "ok", text: `${rel} removed`, dim: "still the template ai-eng installed" });
    const stripped = stripSharedText(snapshot.content.toString("utf8"));
    if (stripped === null) {
      return { kind: "leave", row: { mark: "warn", text: `${rel} not rewritten — not JSON this installer can rewrite without reformatting it (review by hand)` } };
    }
    if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
      return unlink({ mark: "ok", text: `${rel} removed`, dim: "it held only ai-eng entries" });
    }
    // A second name would receive the rewrite too, so the write would refuse: leave it now,
    // or the plan promises a strip the sweep never makes and the lock retries it forever.
    if (snapshot.nlink !== 1) {
      return { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: HARD_LINKED } };
    }
    return { kind: "rewrite", absolute: safeAbsolute, snapshot, text: stripped, row: { mark: "ok", text: `${rel}: removed the ai-eng hook entries, kept yours` } };
  }
  // Git shims are judged by their marker (the only test that survives a user re-chmod):
  // a hook the user wrote over ours is no longer ai-eng's shim. Seeded config the project
  // edited is the project's. Every other file the lock names is ai-eng's, edited or not.
  if (rel.startsWith(".git/hooks/")) {
    return snapshot.content.includes(Buffer.from("ai-eng git floor shim"))
      ? unlink({ mark: "ok", text: `${rel} removed`, dim: "marker-matched — never by name alone" })
      : { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: "no ai-eng marker: it is yours now" } };
  }
  if (SEEDED_CONFIG.has(rel) && snapshot.hash !== assets[rel]) {
    return { kind: "leave", row: { mark: "ok", text: `${rel} kept`, dim: "config you edited — yours" } };
  }
  // Without a lock the path is only one the binary would ship, not proof ai-eng wrote
  // this file: only bytes identical to ai-eng's own say so.
  if (!isLockRecorded && snapshot.hash !== assets[rel]) {
    return { kind: "leave", row: { mark: "warn", text: `${rel} kept`, dim: "no lock records it and its bytes are not ai-eng's — yours" } };
  }
  return unlink(snapshot.hash === assets[rel]
    ? { mark: "ok", text: `${rel} removed` }
    : { mark: "ok", text: `${rel} removed`, dim: "edited since install — ai-eng's file all the same" });
}

function pruneCreatedDirs(root: string, removed: ui.Row[]): void {
  // Dirs ai-eng created are pruned only when the sweep left them empty.
  for (const dir of [".ai-engineering", ".claude", ".cursor", ".codex", ".copilot", ".opencode/plugins", ".agents/hooks", ".pi/extensions", ".github/workflows"]) {
    if (pruneIfEmpty(root, dir)) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
  for (const dir of [".opencode", ".agents", ".pi", ".github"]) {
    if (pruneIfEmpty(root, dir)) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
}

function pruneEmptyDirectory(directory: string): boolean {
  try {
    if (readdirSync(directory).length !== 0) return false;
    rmdirSync(directory);
    return true;
  } catch {
    return false;
  }
}

/** Remove every machine path ai-eng installed — each skill folder it ships or shipped
 *  (whole), its agents and its scripts — edited or not: they are ai-eng's. A skill of your
 *  own, in a folder of its own name, and any agent or script ai-eng never shipped stay. */
function removeMachinePayload(machineDir: string, refused: string[]): number {
  // The real spelling: the prune binds each folder to its realpath, and a home under a
  // linked folder (macOS /var → /private/var) would otherwise never be pruned.
  let canonicalMachineDir: string;
  try {
    canonicalMachineDir = realpathSync(machineDir);
  } catch {
    return 0;
  }
  let removed = 0;
  for (const key of recordedMachinePaths(machineDir)) {
    try {
      // Only a skill key names a folder; an agent or script was written as a file, so a
      // real folder at that name is not what ai-eng wrote, and it stays.
      const entry = lstatSync(join(canonicalMachineDir, key));
      if (entry.isDirectory() && !key.startsWith("skills/")) continue;
    } catch {
      continue; // absent: nothing to remove
    }
    const left = removeMachinePath(machineDir, key);
    if (left.length === 0) removed += 1;
    else refused.push(...left.map((path) => join(canonicalMachineDir, path)));
  }
  for (const folder of ["skills", "agents", "scripts"]) pruneEmptyDirectoryWithin(machineDir, join(canonicalMachineDir, folder));
  return removed;
}

/** The two small records installCanon and the notice check write into the machine home.
 *  Each goes only while it still has the exact shape this installer writes, so a home
 *  holding nothing else of the user's can be removed whole. The ownership record also
 *  stays while any file it vouches for remains: it is the only proof a later run has. */
const INSTALLER_RECORDS: ReadonlyArray<{ name: string; isRemovable: (machineDir: string, text: string) => boolean }> = [
  { name: "version.json", isRemovable: (_machineDir, text) => isVersionCacheRecord(text) },
  { name: CANON_OWNERSHIP_NAME, isRemovable: isRemovableCanonOwnershipRecord },
];

function removeInstallerRecords(machineDir: string, refused: string[]): number {
  let removed = 0;
  // A path refused outside the home (a slash command, a mirror entry) has only the ownership
  // record to prove it ai-eng's, so the record stays while anything was refused.
  const isAnythingRefused = refused.length > 0;
  for (const record of INSTALLER_RECORDS) {
    if (isAnythingRefused && record.name === CANON_OWNERSHIP_NAME) continue;
    const absolute = safeProjectPath(machineDir, record.name);
    const snapshot = absolute === null ? null : readProjectFileSnapshot(machineDir, absolute);
    if (absolute === null || snapshot === null || !record.isRemovable(machineDir, snapshot.content.toString("utf8"))) continue;
    if (unlinkProjectPath(machineDir, absolute, snapshot)) removed += 1;
    else refused.push(absolute);
  }
  return removed;
}

function machineRefusalText(refused: { path: string; reason: string }): string {
  if (refused.reason === "identity-bound-settings-mutation-unavailable") {
    return `${refused.path} left alone — it changed while ai-eng was removing its entries, or it is a hard link with a second name; remove the ai-eng chain lines by hand`;
  }
  if (refused.reason === "machine-state-identity-unverified") {
    return `${refused.path} left alone — it is linked, changed, or shared with another path`;
  }
  return refuseLine(refused).replace(/^⚠ /, "");
}

/** Restore git `init.templateDir` from the machine state. State that cannot be read now
 *  (a held lock, an interrupted run's copy) is never read as "nothing recorded": the
 *  restore is skipped out loud, with the path that blocks it. */
function restoreRecordedTemplateDir(): ui.Row | null {
  const unavailable = machineStateUnavailable();
  if (unavailable !== null) {
    return { mark: "warn", text: `git init.templateDir not restored — ${refuseLine(unavailable).replace(/^⚠ /, "")}` };
  }
  const floorState = readMachineState().templateDir;
  if (floorState === undefined) return null;
  return { mark: "ok", text: restoreTemplateDir(floorState.previous, floorState.ours) };
}

async function removeEverything(root: string, input: unknown, declared: string[]): Promise<ui.Row[]> {
  const extra: ui.Row[] = [];
  const agents = join(root, "AGENTS.md");
  const decisions = join(root, "DECISIONS.md");
  const confirmedAll = await ui.confirmDefault("Delete this project's AGENTS.md, DECISIONS.md, .gitignore and .ai-engineering/ too? They hold your work.", false, input as never);
  if (confirmedAll) {
    const refusals: ui.Row[] = [];
    // A refused delete is named and the sweep goes on: the machine side is still to come.
    const attempt = (path: string, remove: () => void): void => {
      try {
        remove();
      } catch (error) {
        if (!isFilesystemRefusal(error)) throw error;
        refusals.push({ mark: "warn", text: refusedChangeText(path, error) });
      }
    };
    if (existsSync(agents)) attempt(agents, () => unlinkSync(agents));
    if (existsSync(decisions)) attempt(decisions, () => unlinkSync(decisions));
    // A .gitignore is the one scaffold file a project very often already owned before
    // init: ours goes only while it is byte-identical to the template — an edited one
    // holds the user's rules and stays, named.
    const gitignore = join(root, ".gitignore");
    const ours = existsSync(gitignore) && hashFile(gitignore) === sha256(embeddedTemplate("gitignore.tpl"));
    if (ours) attempt(gitignore, () => unlinkSync(gitignore));
    const projectHome = join(root, ".ai-engineering");
    attempt(projectHome, () => rmSync(projectHome, { recursive: true, force: true }));
    extra.push({ mark: "warn", text: refusals.length === 0 ? "project contract files removed (your choice)" : "project contract files removed (your choice), except the ones named below", dim: `AGENTS.md · DECISIONS.md${ours ? " · .gitignore" : ""} · .ai-engineering/` });
    extra.push(...refusals);
  } else {
    extra.push({ mark: "ok", text: "kept: AGENTS.md, DECISIONS.md, .gitignore, .ai-engineering/" });
  }
  // The machine side: the global canon this binary installed.
  const machineDir = home();
  const confirmedMachine = await ui.confirmDefault(`Delete the machine side ${machineDir} (global skills, mirrors)?`, false, input as never);
  if (confirmedMachine) {
    // The carriers first, and by the table: they live in the HOSTS' directories, not
    // inside the canon home, so removing the canon would leave them behind pointing at a
    // chain that no longer exists — orphans with a marker.
    const carriers = removeMachineCarriers(declared);
    // The git floor first: the recorded state lives inside the canon home this scope is
    // about to delete, so reading it afterwards would restore nothing.
    const floor = restoreRecordedTemplateDir();
    const refusedPaths: string[] = [];
    const swept = removeMachineArtifacts(refusedPaths);
    const canonAssetsRemoved = removeMachinePayload(machineDir, refusedPaths) + removeInstallerRecords(machineDir, refusedPaths);
    pruneEmptyDirectory(machineDir);
    const userFilesRemain = existsSync(machineDir);
    const cleanup = `${canonAssetsRemoved} ai-eng path(s) removed · ${swept} machine artifacts swept`;
    extra.push(userFilesRemain
      ? { mark: "ok", text: `${machineDir} kept`, dim: `${cleanup} · other files kept` }
      : { mark: "warn", text: `${machineDir} deleted`, dim: cleanup });
    if (floor !== null) extra.push(floor);
    for (const path of refusedPaths) extra.push({ mark: "warn", text: `${path} kept`, dim: "still ai-eng's, but it changed during uninstall or the filesystem refused the change — preserved" });
    for (const line of carriers.lines) extra.push({ mark: "ok", text: line });
    for (const refused of carriers.refused) extra.push({ mark: "warn", text: machineRefusalText(refused) });
  } else {
    extra.push({ mark: "ok", text: `kept: ${machineDir}`, dim: "global skills stay installed" });
  }
  return extra;
}

export async function uninstallMain(): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Uninstall · ai-eng ${VERSION}`);
  const root = repoRoot();
  if (root === null || !isGoverned(root)) {
    ui.fail("you are not in a governed repo — nothing of this project to remove");
    ui.end("Nothing done.");
    return 2;
  }
  const scope = await confirmUninstall(input);
  if (scope === null) return 0;

  // Read the declaration ONCE, before anything removes it. The machine sweep runs after
  // the project side has deleted config.toml, and `enabledSurfaces()` then reports the
  // no-config fallback (["claude-code"]): a repo declaring any other surface kept that
  // host's carrier behind as an orphan pointing at a chain nothing serves.
  const declared = enabledSurfaces();
  // ── project side ──────────────────────────────────────────────
  const removed: ui.Row[] = [];
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  removed.push({ mark: "ok", text: "git: core.hooksPath reverted to default" });
  sweepProjectSide(root, declared, removed);
  // Rendered as one block: what went, at a glance.
  ui.section("Removed", removed);
  if (scope === "everything") {
    const extra = await removeEverything(root, input, declared);
    ui.section("Everything scope — the extra sweep", extra);
  }
  ui.end(scope === "everything" ? "ai-eng removed from this machine as far as you chose. Your work survives unless you said otherwise." : "ai-eng is no longer active in this repo. Your contract files remain.");
  return 0;
}
