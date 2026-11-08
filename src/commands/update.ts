// `ai-eng update` — re-install this repo's assets from the installed binary. ZERO
// network: the payload leaves the binary the user already installed (§14.3). What
// What ai-eng wrote is ai-eng's and always receives this binary's bytes, edited or not
// (git keeps an edit); what it never wrote, and seeded config the project edited, is the
// project's and is never rewritten.
// It refreshes BOTH halves ai-eng installed: the machine side (the global canon and
// its mirrors) and this repo's assets. cli-ux-14 work point 04: compute the sync
// plan first, show it, confirm Apply, then write — never the reverse. Human-facing lines go through
// src/ui.ts.

import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { confirm, isCancel } from "@clack/prompts";
import { install, buildLock, lockText, parseLock, sha256, mergeSharedText, SEEDED_CONFIG } from "../install.ts";
import type { PlanEntry } from "../install.ts";
import { repoRoot, enabledSurfaces, home, isGoverned } from "../env.ts";
import { canonDrift, isFilesystemRefusal, refusedChangeText, type CanonDrift } from "../embed.ts";
import { installCanon, installMachineCarriers, machineStateFile, retireNpmPowerShellShim, sweepMovedRepoCarriers } from "../surfaces/adapters.ts";
import { runGit } from "../git/run.ts";
import { installLineRow, planEntries, refuseLine } from "./init-shared.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";

export type SyncPlan = {
  current: string[]; // byte-identical to what this binary installs, or a merge with nothing to add
  updates: string[]; // ai-eng's, holding other bytes (an older release, or an edit): rewritten
  fresh: string[]; // not on disk yet
  yours: string[]; // the project's: never written by ai-eng, or seeded config it edited
  verbatim: string[]; // subset of current that byte-matches ours — provably ours
};
export function syncPlan(entries: PlanEntry[], root: string, previousAssets: Record<string, string>): SyncPlan {
  const plan: SyncPlan = { current: [], updates: [], fresh: [], yours: [], verbatim: [] };
  for (const entry of entries) {
    const absolute = join(root, entry.path);
    if (!existsSync(absolute)) {
      plan.fresh.push(entry.path);
      continue;
    }
    const currentHash = sha256(readFileSync(absolute, "utf8"));
    if (currentHash === sha256(entry.ours)) {
      plan.current.push(entry.path);
      plan.verbatim.push(entry.path);
      continue;
    }
    // A file we share with the user is never written whole: install() merges our entries
    // into it by marker, so the merge IS the update — and a settings file the user already
    // had before init is exactly the file that must receive our hooks (§03). Planned as an
    // update only when the merge would really change it, so a second update says nothing.
    if (entry.merge === true) {
      const merged = mergeSharedText(readFileSync(absolute, "utf8"), entry.ours);
      if (!("refused" in merged) && merged.changed) plan.updates.push(entry.path);
      else plan.current.push(entry.path);
      continue;
    }
    const recorded = previousAssets[entry.path];
    if (!recorded || (SEEDED_CONFIG.has(entry.path) && currentHash !== recorded)) {
      plan.yours.push(entry.path); // never ai-eng's, or seeded config the project made its own
      continue;
    }
    plan.updates.push(entry.path); // ai-eng's: an older release, or an edit — rewritten
  }
  return plan;
}

/** The machine half of an update: the global canon, the declared surfaces' carriers,
 *  the sweep of pre-2.2.0 repo carriers, and the git floor. Carriers live on the
 *  machine — at the home path each host actually reads (the carrier table in
 *  surfaces/adapters.ts), not in the repo checkout — so none of it is a repo-side
 *  asset, and that is exactly why it must not sit behind the plan's early returns.
 *  `doctor` sends a machine that lost its carrier here ("→ ai-eng update"); a repo
 *  whose own assets are current is the normal shape of that machine, and returning
 *  before this made the remedy a no-op.
 *
 *  Every part reports, changed or not. A half that stays silent about the canon it just
 *  verified reads as a half that never looked, and "all 7 assets current" then buries the
 *  only question the run was asked. The rows carry the outcome, so there is no need for
 *  two kinds of proof: `written` for a change, `muted` for a part that checked out. */
function installMachineSide(
  root: string,
  canon: CanonDrift,
  canonRepair: string[],
): { rows: ui.Row[]; written: number } {
  const rows: ui.Row[] = [];
  let written = 0;
  if (canonRepair.length > 0) {
    written += 1;
    const counts: Array<[number, string]> = [[canon.drift, "drifted"], [canon.missing, "missing"], [canon.stale, "stale"]];
    const why = counts.filter(([count]) => count > 0).map(([count, word]) => `${count} ${word}`).join(" · ");
    rows.push({
      mark: "ok",
      text: "global canon outdated or incomplete — re-installed",
      dim: why,
    });
    rows.push(...canonRepair.map((line) => installLineRow(line, "sub")));
  } else {
    rows.push({ mark: "muted", text: `global canon · ${canon.verified} files match ai-eng ${VERSION}` });
  }
  // Every update, healthy canon or not: npm writes the .ps1 back on a reinstall of the same version.
  const retiredShim = retireNpmPowerShellShim();
  if (retiredShim !== null) {
    rows.push(installLineRow(retiredShim));
    if (retiredShim.startsWith("✓")) written += 1;
  }
  const machineReport = installMachineCarriers(enabledSurfaces());
  written += machineReport.written.length;
  rows.push(...machineReport.written.map((path): ui.Row => ({ mark: "ok", text: path, dim: "machine carrier · written" })));
  rows.push(...machineReport.untouched.map((path): ui.Row => ({ mark: "muted", text: `${path} · machine carrier already current` })));
  rows.push(...machineReport.refused.map((refused): ui.Row => ({ mark: "warn", text: refuseLine(refused).replace(/^⚠ /, "") })));
  const moved = sweepMovedRepoCarriers(root);
  written += moved.removed.length;
  rows.push(...moved.removed.map((path): ui.Row => ({ mark: "ok", text: path, dim: "moved to the machine — removed from the repo" })));
  rows.push(...moved.kept.map((path): ui.Row => ({ mark: "warn", text: `${path} kept`, dim: "not ours any more — review by hand" })));
  rows.push(...moved.refused.map((path): ui.Row => ({ mark: "warn", text: `${path} kept`, dim: "still ai-eng's, but it could not be removed or rewritten (changed meanwhile, or a read-only, locked or busy folder) — the next ai-eng update retries" })));
  // The ledger this half is written into: version + the hash of every carrier. Named
  // because it is the file a later `uninstall` reads, and an unreported write is the
  // question this report exists to answer.
  rows.push({ mark: "muted", text: `${machineStateFile()} · version + carrier hashes` });
  return { rows, written };
}

/** The block the machine half prints as — the same one in every path, so "nothing to
 *  write" and "3 written" are the same sentence with a different count. */
function machineSection(machine: { rows: ui.Row[]; written: number }): void {
  ui.section("Machine side", machine.rows, machine.written === 0 ? "nothing to write" : `${machine.written} written`);
}

export async function updateMain(opts: { yes?: boolean } = {}): Promise<number> {
  const input = scriptedInput();
  const root = repoRoot();
  if (root === null || !isGoverned(root)) {
    process.stderr.write("update: you are not in a governed repo.\n");
    return 2;
  }
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  // A missing lock is a recoverable state, not an abort: `uninstall` (project
  // scope) deletes the lock but keeps config.toml, and init then hands off here
  // — "no lock, run init" is a deadlock. Empty
  // previous assets = nothing recorded as ours: absent files install fresh, any
  // file on disk is treated as the user's, and the lock is rebuilt at the end.
  const previous = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : { version: "", assets: {} };
  const surfaces = enabledSurfaces();
  // Config is user-owned; update must not rewrite legacy keys or their bytes.
  const entries: PlanEntry[] = planEntries(surfaces).filter((entry) => entry.path !== ".ai-engineering/config.toml");
  const plan = syncPlan(entries, root, previous.assets);
  const pending = [...plan.updates, ...plan.fresh];

  // The frame states the repo's state in plain words: "unknown" would be a fallback
  // lying about a recoverable state, and no internal verb reaches a user anyway.
  const origin = !existsSync(lockPath)
    ? "no ai-eng.lock here yet: ai-eng will create its files fresh"
    : previous.version
      ? `previous install by ai-eng ${previous.version}`
      : "previous install by an older ai-eng";
  ui.frame(`ai-eng ${VERSION} · ${origin}`);
  // The machine side travels with the repo side. The canon is what a surface
  // actually reads, and it drifts the moment the binary ships different skills —
  // twenty stale skills reported as "all assets current" is the gap, and
  // repairing it by hand means knowing that `init --global` does it. Same
  // predicate init and doctor use: health is a measurement.
  //
  // Repaired here, reported with the rest of the machine half: one block, printed
  // once. A canon section of its own printed before the questions left the run
  // looking like two unrelated commands (cli-ux-14).
  const canon = canonDrift(home());
  const canonRepair = canon.drift === 0 && canon.missing === 0 && canon.stale === 0 ? [] : installCanon(VERSION);
  if (pending.length === 0) {
    // The repo half reports what it holds, not only how many: a bare "all 7 assets
    // current" cannot say whether anything was verified (cli-ux-14).
    ui.section("Repo assets", [
      { mark: "muted", text: `all ${plan.current.length} assets current — nothing to sync` },
      ...(plan.current.length > 0 ? [{ mark: "sub", text: ui.pathList(plan.current) } satisfies ui.Row] : []),
    ]);
    const machine = installMachineSide(root, canon, canonRepair);
    machineSection(machine);
    ui.end(
      machine.written === 0
        ? `Nothing written — the repo and the machine already match ai-eng ${VERSION} · Next: ai-eng doctor`
        : `Machine side updated to ai-eng ${VERSION} · the repo already matched · Next: ai-eng doctor`,
    );
    return 0;
  }
  // Concept blocks, not line-spam (§14.3 mockup): one block per idea, and Apply only
  // when something will actually be written. There is no decision to ask about: a file
  // ai-eng wrote takes this binary's bytes, and a file of the project's is never touched.
  const rows: ui.Row[] = [
    ...plan.updates.map((path): ui.Row => ({
      mark: "ok",
      text: path,
      dim: isEditedSinceWritten(root, path, previous.assets) ? `edited since ai-eng wrote it — ai-eng's file, rewritten to ${VERSION} (git keeps the edit)` : `new version from binary ${VERSION}`,
    })),
    ...plan.fresh.map((path): ui.Row => ({ mark: "ok", text: path, dim: "new asset" })),
  ];
  if (plan.current.length > 0) {
    rows.push({ mark: "sub", text: ui.pathList(plan.current) }, { mark: "muted", text: `${plan.current.length} already current — untouched` });
  }
  if (plan.yours.length > 0) {
    rows.push({ mark: "sub", text: ui.pathList(plan.yours) }, { mark: "muted", text: `${plan.yours.length} yours (not written by ai-eng, or config you edited) — untouched` });
  }
  ui.section("What needs to sync", rows, [
    plan.updates.length > 0 ? `${plan.updates.length} update${plan.updates.length === 1 ? "" : "s"}` : "",
    plan.fresh.length > 0 ? `${plan.fresh.length} new` : "",
  ].filter((part) => part.length > 0).join(" · "));
  const writeCount = pending.length;
  const apply = opts.yes === true ? true : await confirm({ message: `Apply? ${writeCount} write${writeCount === 1 ? "" : "s"}`, initialValue: true, input: input as never });
  if (isCancel(apply) || apply === false) {
    ui.cancelled("Nothing written.");
    return 0;
  }
  const report = install(root, entries, (path) => {
    const hash = previous.assets[path];
    return hash ? `sha256:${hash}` : null;
  });
  // Freshly written git shims must stay executable or git silently ignores them.
  const shimRefusals: ui.Row[] = [];
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(root, ".git", "hooks", shim);
    try {
      if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
    } catch (error) {
      if (!isFilesystemRefusal(error)) throw error;
      shimRefusals.push({ mark: "warn", text: refusedChangeText(shimPath, error) });
    }
  }
  const resultRows: ui.Row[] = [
    { mark: "ok", text: `${report.written.length} asset${report.written.length === 1 ? "" : "s"} synced`, dim: "sha256 recorded in ai-eng.lock" },
    ...report.refused.map((refused): ui.Row => ({ mark: "warn", text: refuseLine(refused).replace(/^⚠ /, "") })),
    ...shimRefusals,
  ];
  ui.section("Synced", resultRows, report.yours.length > 0 ? `${report.yours.length} file${report.yours.length === 1 ? "" : "s"} of yours untouched` : "nothing of yours touched");
  machineSection(installMachineSide(root, canon, canonRepair));
  // The lock is the ownership ledger: it may only claim files this run actually
  // made ours — written now, or already byte-identical to ours (verbatim). A MERGED
  // file is ours by entry, not by hash: the merge is what puts our hooks in it, and
  // uninstall is what takes them back out, so the lock has to carry the path or the sweep
  // never finds it. A file we could not merge (not JSON) is not ours and is not claimed.
  // A file of the project's is never claimed: recording it would make the next update
  // overwrite it and uninstall delete it, and the binary never owned it.
  const refused = new Set(report.refused.map((entry) => entry.path));
  const merged = entries.filter((entry) => entry.merge === true && !refused.has(entry.path)).map((entry) => entry.path);
  const oursNow = new Set([...report.written, ...plan.verbatim, ...merged]);
  const lock = buildLock(
    entries.filter((entry) => oursNow.has(entry.path)),
    VERSION,
    { spec_sha256: previous.spec_sha256, base_sha: previous.base_sha },
  );
  // A recorded file this run could not write (read-only, or a link now at its name) is still
  // ai-eng's: it keeps its previous entry, so the next update retries it and uninstall knows it.
  for (const entry of entries) {
    const recorded = previous.assets[entry.path];
    if (entry.merge !== true && refused.has(entry.path) && recorded !== undefined) lock.assets[entry.path] = recorded;
  }
  try {
    writeFileSync(lockPath, lockText(lock));
  } catch (error) {
    if (!isFilesystemRefusal(error)) throw error;
    ui.section("Recorded", [{ mark: "warn", text: `ai-eng.lock not written — ${refusedChangeText(lockPath, error)}` }]);
    ui.end("The ownership ledger was not recorded · Next: make .ai-engineering/ writable, then ai-eng update");
    return 1;
  }
  ui.section("Recorded", [{ mark: "ok", text: `ai-eng.lock · ${Object.keys(lock.assets).length} assets with sha256` }]);
  const status = runGit(["status", "--porcelain"], { cwd: root });
  const changesAreVisible = status.status !== 0 || status.stdout.trim().length > 0;
  ui.end(`${changesAreVisible ? "Changes are waiting for your review" : "Nothing to commit"}; nothing was committed · Next: ai-eng doctor — verify the chain responds`);
  return 0;
}

/** Whether a file ai-eng wrote no longer holds the bytes the lock recorded for it. */
function isEditedSinceWritten(root: string, path: string, recorded: Record<string, string>): boolean {
  const hash = recorded[path];
  return hash !== undefined && sha256(readFileSync(join(root, path), "utf8")) !== hash;
}
