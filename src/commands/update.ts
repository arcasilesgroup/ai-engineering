// `ai-eng update` — re-install this repo's assets from the installed binary. ZERO
// network: the payload leaves the binary the user already installed (§14.3). What
// is the user's (AGENTS.md, DECISIONS.md, spec/plan, arch.rules) is never touched.
// It refreshes BOTH halves ai-eng installed: the machine side (the global canon and
// its mirrors) and this repo's assets. cli-ux-14 work point 04: compute the sync
// plan first, show it, resolve conflicts with the human (keep-yours default),
// confirm Apply, then write — never the reverse. Human-facing lines go through
// src/ui.ts.

import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { select, confirm, isCancel } from "@clack/prompts";
import { install, buildLock, lockText, parseLock, sha256, mergeSharedText } from "../install.ts";
import type { PlanEntry } from "../install.ts";
import { repoRoot, enabledSurfaces, home, isGoverned } from "../env.ts";
import { canonDrift, type CanonDrift } from "../embed.ts";
import { installCanon, installMachineCarriers, machineStateFile, rememberTemplateDir, sweepMovedRepoCarriers } from "../surfaces/adapters.ts";
import { installTemplateDir } from "../floor/template.ts";
import { planEntries, refuseLine } from "./init-shared.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";

export type SyncPlan = {
  current: string[]; // byte-identical to what this binary installs
  updates: string[]; // previous version of ours on disk → safe update
  fresh: string[]; // not on disk yet
  conflicts: string[]; // user-edited AND ours changed since their install
  verbatim: string[]; // subset of current that byte-matches ours — provably ours
};
export function syncPlan(entries: PlanEntry[], root: string, previousAssets: Record<string, string>): SyncPlan {
  const plan: SyncPlan = { current: [], updates: [], fresh: [], conflicts: [], verbatim: [] };
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
    // A file we share with the user is never a conflict and never "yours, untouched":
    // install() merges our entries into it by marker, so the merge IS the update —
    // and a settings file the user already had before init is exactly the file that
    // must receive our hooks, not the one to walk past (§03). Planned as an update
    // only when the merge would really change it, so a second update says nothing.
    if (entry.merge === true) {
      const merged = mergeSharedText(readFileSync(absolute, "utf8"), entry.ours);
      if (!("refused" in merged) && merged.changed) plan.updates.push(entry.path);
      else plan.current.push(entry.path);
      continue;
    }
    const recorded = previousAssets[entry.path];
    if (!recorded) {
      plan.current.push(entry.path); // we never installed it: the user's own
      continue;
    }
    if (currentHash === recorded) {
      plan.updates.push(entry.path); // exact previous version: safe update
      continue;
    }
    plan.conflicts.push(entry.path);
  }
  return plan;
}

/** The machine half of an update: the global canon, the declared surfaces' carriers, the
 *  carriers that moved out of the repo in this release, and the git floor. None of it is
 *  a repo-side asset, so none of it shows up in the sync plan — and that is exactly why
 *  it must not sit behind the plan's early returns. `doctor` sends a machine that lost
 *  its carrier here ("→ ai-eng update"); a repo whose own assets are current is the
 *  normal shape of that machine, and returning before this made the remedy a no-op.
 *
 *  Every part reports, changed or not. A half that stays silent about the canon it just
 *  verified reads as a half that never looked, and "all 7 assets current" then buries the
 *  only question the run was asked. The rows carry the outcome, so there is no need for
 *  two kinds of proof: `written` for a change, `muted` for a part that checked out. */
function installMachineSide(root: string, canon: CanonDrift, canonRepair: string[]): { rows: ui.Row[]; written: number } {
  const rows: ui.Row[] = [];
  let written = 0;
  if (canonRepair.length > 0) {
    written += 1;
    const counts: Array<[number, string]> = [[canon.drift, "drifted"], [canon.missing, "missing"], [canon.stale, "stale"]];
    const why = counts.filter(([count]) => count > 0).map(([count, word]) => `${count} ${word}`).join(" · ");
    rows.push({ mark: "ok", text: "global canon outdated or incomplete — re-installed", dim: why });
    rows.push(...canonRepair.map((line): ui.Row => ({ mark: "sub", text: line.replace(/^✓ /, "") })));
  } else {
    rows.push({ mark: "muted", text: `global canon · ${canon.verified} files match ai-eng ${VERSION}` });
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
  const template = installTemplateDir();
  if (template.status !== "failed") rememberTemplateDir(template.previous, template.ours);
  if (template.status === "created" || template.status === "joined") {
    written += 1;
    rows.push({ mark: "ok", text: template.line });
  } else if (template.status === "current") {
    rows.push({ mark: "muted", text: template.line });
  } else {
    rows.push({ mark: "warn", text: template.line });
  }
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
  const entries: PlanEntry[] = planEntries(surfaces);
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
  if (pending.length === 0 && plan.conflicts.length === 0) {
    // The repo half reports what it holds, not only how many: "all 7 assets current"
    // is exactly the phrase that hid the gap this block exists to close, and a count
    // cannot say whether anything was verified (cli-ux-14).
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
  // Concept blocks, not line-spam (§14.3 mockup): one block per idea. And a
  // question only appears when there is a real decision left to make:
  // sync-plan when files change, ONE conflict decision, Apply only when
  // something will actually be written.
  if (pending.length > 0) {
    const rows: ui.Row[] = [
      ...plan.updates.map((path): ui.Row => ({ mark: "ok", text: path, dim: `new version from binary ${VERSION}` })),
      ...plan.fresh.map((path): ui.Row => ({ mark: "ok", text: path, dim: "new asset" })),
    ];
    if (plan.current.length > 0) {
      rows.push({ mark: "sub", text: ui.pathList(plan.current) }, { mark: "muted", text: `${plan.current.length} already current or yours — untouched` });
    }
    ui.section("What needs to sync", rows, [
      plan.updates.length > 0 ? `${plan.updates.length} update${plan.updates.length === 1 ? "" : "s"}` : "",
      plan.fresh.length > 0 ? `${plan.fresh.length} new` : "",
    ].filter((part) => part.length > 0).join(" · "));
  }

  // Conflict resolution BEFORE any write: ONE decision for the whole set —
  // the same question N times is noise, and keep-yours is the default:
  // deleting what the user edited is the worst class of bug a governance
  // tool can have. The file list rides inside the question itself.
  let takeAll = false;
  if (plan.conflicts.length > 0) {
    // --yes resolves conservatively: keep-yours. Unattended recovery may install
    // what is absent but never overwrites what the human edited.
    const choice = opts.yes === true ? "keep" : await select({
      message: `${plan.conflicts.length === 1 ? "A file" : `${plan.conflicts.length} files`} patched by you also changed in binary ${VERSION}. What wins?\n${ui.pathList(plan.conflicts)}`,
      options: [
        { value: "keep", label: "Keep mine everywhere", hint: "your patches stay; the new version is one git revert away" },
        { value: "take", label: "Take the new version everywhere", hint: "your edits survive in git history" },
      ],
      input: input as never,
    });
    if (isCancel(choice)) {
      ui.cancelled("Nothing written.");
      return 0;
    }
    takeAll = choice === "take";
  }
  const takeCount = takeAll ? plan.conflicts.length : 0;
  const writeCount = pending.length + takeCount;
  if (writeCount === 0) {
    // Keep-mine everywhere with nothing else pending: the repo is already
    // exactly as you left it. Say so and close — no lock rewrite, no commit.
    // The machine half runs anyway: it is not part of the plan, so "the repo needs
    // nothing" is not the same question as "the machine needs nothing".
    ui.section("Kept", [{ mark: "info", text: "your patches stay", dim: ui.pathList(plan.conflicts) }, { mark: "muted", text: "nothing written — the repo is exactly as you left it" }]);
    const machine = installMachineSide(root, canon, canonRepair);
    machineSection(machine);
    ui.end(
      machine.written === 0
        ? `Nothing written — the repo and the machine already match ai-eng ${VERSION} · Next: ai-eng doctor`
        : `Machine side updated to ai-eng ${VERSION} · your patches stayed · Next: ai-eng doctor`,
    );
    return 0;
  }
  const apply = opts.yes === true ? true : await confirm({ message: `Apply? ${writeCount} write${writeCount === 1 ? "" : "s"}${plan.conflicts.length > 0 && takeCount === 0 ? " · your patches stay untouched" : ""}`, initialValue: true, input: input as never });
  if (isCancel(apply) || apply === false) {
    ui.cancelled("Nothing written.");
    return 0;
  }
  // Writes: keep-yours means install() must not touch the conflict at all — the
  // entry comes out of the plan AND out of the lock (a kept file is the user's;
  // recording our hash for it would make the NEXT update overwrite their edit in
  // silence). take means install() writes ours over the edit: that is the force
  // channel — only a human decision reaches it.
  const take = () => takeAll;
  const writable = takeAll ? entries : entries.filter((entry) => !plan.conflicts.includes(entry.path));
  const report = install(root, writable, (path) => {
    const hash = previous.assets[path];
    return hash ? `sha256:${hash}` : null;
  }, take);
  // Freshly written git shims must stay executable or git silently ignores them.
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(root, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  const keptPaths = takeAll ? [] : plan.conflicts;
  const keptCount = keptPaths.length;
  const resultRows: ui.Row[] = [
    { mark: "ok", text: `${report.written.length} asset${report.written.length === 1 ? "" : "s"} synced`, dim: "sha256 recorded in ai-eng.lock" },
    ...(keptCount > 0 ? [{ mark: "info", text: "kept yours", dim: keptPaths.join("  ·  ") } satisfies ui.Row] : []),
    ...report.refused.map((refused): ui.Row => ({ mark: "warn", text: refuseLine(refused).replace(/^⚠ /, "") })),
  ];
  ui.section("Synced", resultRows, plan.conflicts.length > 0
    ? `${plan.conflicts.length} conflict${plan.conflicts.length === 1 ? "" : "s"} resolved · 0 files of yours touched otherwise`
    : "nothing of yours touched");
  machineSection(installMachineSide(root, canon, canonRepair));
  // The lock is the ownership ledger: it may only claim files this run actually
  // made ours — written now, taken over by explicit human resolution, or
  // already byte-identical to ours (verbatim). A MERGED file is ours by entry, not by
  // hash: the merge is what puts our hooks in it, and uninstall is what takes them back
  // out, so the lock has to carry the path or the sweep never finds it. A file we could
  // not merge (not JSON) is not ours and is not claimed. "current" also holds files
  // install() calls untouched/user's (the no-lock recovery state): recording those make
  // the next update report a false conflict and uninstall strip a file the binary never
  // owned.
  const refused = new Set(report.refused.map((entry) => entry.path));
  const merged = entries.filter((entry) => entry.merge === true && !refused.has(entry.path)).map((entry) => entry.path);
  const oursNow = new Set([...report.written, ...plan.verbatim, ...merged]);
  const lock = buildLock(
    entries.filter((entry) => (takeAll || !plan.conflicts.includes(entry.path)) && oursNow.has(entry.path)),
    VERSION,
    { spec_sha256: previous.spec_sha256, base_sha: previous.base_sha },
  );
  writeFileSync(lockPath, lockText(lock));
  let commitLine = "commit skipped — nothing staged or git refused (your call to commit by hand)";
  try {
    spawnSync("git", ["-C", root, "add", "-A"]);
    const committed = spawnSync("git", ["-C", root, "commit", "-q", "-m", `chore(ai-eng): assets → ${VERSION}`, "--no-verify", "--no-gpg-sign"]);
    if (committed.status === 0) commitLine = `chore(ai-eng): assets → ${VERSION} · git revert is the rollback`;
  } catch {
    /* git absent or refused — the hand-commit note above stands */
  }
  ui.section("Recorded", [{ mark: "ok", text: `ai-eng.lock · ${Object.keys(lock.assets).length} assets with sha256` }, { mark: "ok", text: `commit: ${commitLine}` }]);
  ui.end(`Repo and machine now match ai-eng ${VERSION} · Next: ai-eng doctor — verify the chain responds`);
  return 0;
}
